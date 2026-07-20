

import re
import subprocess
import time
import json
import logging

import requests
from requests.auth import HTTPDigestAuth

from .base import ManualPlatformPlugin

# Setup logger
logger = logging.getLogger(__name__)

# Optional SSH support
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class CrestronSSHPlugin(ManualPlatformPlugin):
    """Crestron CP4N / AM-3200 via authenticated Crestron web API."""

    name = "crestron_ssh"
    display_name = "Crestron SSH"
    description = "Crestron CP4N and AM-3200 via Crestron web API"
    supports_display_id = False
    supports_port = False
    default_port = 22
    SUPPORTED_MODELS = [
        "CP4N",
        "DM NVX",
        "DM NAX",
        "HD-HDNXM (Switchers)",
        "HD-PS (Presentation)",
        "4 Series (Control)",
    ]

    COMMANDS = {}
    QUERY_COMMANDS = {}

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    def _normalize_mac(self, raw_mac):
        if not raw_mac:
            return None
        raw_value = str(raw_mac).strip()
        if raw_value.startswith("<") and raw_value.endswith(">"):
            return None
        cleaned = re.sub(r"[^0-9A-Fa-f]", "", str(raw_mac))
        if len(cleaned) < 12:
            return str(raw_mac).replace(".", ":")
        cleaned = cleaned[:12]
        return ":".join(cleaned[i:i + 2] for i in range(0, 12, 2)).lower()

    def _clean_value(self, value):
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        if value.startswith("<") and value.endswith(">"):
            return None
        return value

    @staticmethod
    def _normalize_slot(slot):
        """Accept '1' or 'DeviceSlot1' — always return 'DeviceSlot1'."""
        slot = slot.strip()
        if slot.isdigit():
            return f"DeviceSlot{slot}"
        return slot

    def _get_credentials(self):
        """Get credentials from config"""
        username = self.config.get("username") if self.config else None
        password = self.config.get("password") if self.config else None
        return username, password

    # ========== Helper methods for session management ==========
    
    def _login(self, ip):
        """Helper to get authenticated session"""
        username, password = self._get_credentials()
        if not username or not password:
            raise Exception("Missing credentials")
        return self._crestron_login(ip, username, password)
    
    def _post(self, session, ip, path, payload):
        """Helper for POST requests"""
        return self._post_json(session, ip, path, payload)

    # ──────────────────────────────────────────────
    # Authentication
    # ──────────────────────────────────────────────

    def _crestron_login(self, ip, username, password):
        base_url = f"https://{ip}"
        login_url = f"{base_url}/userlogin.html"
        session = requests.Session()
        session.verify = False

        headers = {"User-Agent": "Mozilla/5.0"}
        r = session.get(login_url, headers=headers, timeout=8)
        r.raise_for_status()
        
        trackid = session.cookies.get("TRACKID")
        if not trackid:
            raise Exception("TRACKID not found on login page")

        login_headers = {
            "Cookie": f"TRACKID={trackid}",
            "Origin": base_url,
            "Referer": login_url,
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        }
        payload = {"login": username, "passwd": password}
        r2 = session.post(login_url, headers=login_headers, data=payload, timeout=10)

        if r2.status_code == 403:
            raise Exception("Invalid credentials (403). Check username and password.")
        if r2.status_code != 200:
            raise Exception(f"Login failed (HTTP {r2.status_code})")

        xsrf = r2.headers.get("CREST-XSRF-TOKEN")
        if xsrf:
            session.headers.update({"CREST-XSRF-TOKEN": xsrf})

        logger.info(f"[CP4N] Login successful for {ip}")
        return session

    def _fetch_json(self, session, ip, path):
        url = f"https://{ip}{path}"
        resp = session.get(url, timeout=8)
        resp.raise_for_status()
        return resp.json()

    def _post_json(self, session, ip, path, payload):
        url = f"https://{ip}{path}"
        resp = session.post(
            url,
            json=payload,  # Use json= instead of data=json.dumps()
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

    def _extract_ipv4_network_details(self, adapter):
        """Flatten the current adapter's IPv4 settings into UI-friendly fields."""
        ipv4 = (adapter or {}).get("IPv4", {}) or {}
        addresses = ipv4.get("Addresses") or ipv4.get("StaticAddresses") or []
        primary = addresses[0] if addresses else {}
        dns_servers = ipv4.get("DnsServers") or ipv4.get("StaticDns") or []
        cleaned_dns = []
        for dns in dns_servers:
            if not dns:
                continue
            cleaned_dns.append(str(dns).split("(", 1)[0].strip())

        return {
            "adapter_name": (adapter or {}).get("Name"),
            "dhcp_enabled": ipv4.get("IsDhcpEnabled"),
            "current_ip": primary.get("Address"),
            "subnet_mask": primary.get("SubnetMask"),
            "gateway": ipv4.get("DefaultGateway") or ipv4.get("StaticDefaultGateway"),
            "dns_servers": cleaned_dns,
        }

    def _is_config_write_success(self, result):
        """Interpret Crestron config-write responses instead of assuming success."""
        if not isinstance(result, dict):
            return False, "Unexpected empty response from device"

        status_code = result.get("status") or result.get("StatusCode") or result.get("http_status")
        try:
            status_code = int(status_code)
        except (TypeError, ValueError):
            status_code = None

        if status_code in {200, 202, 204}:
            return True, result.get("message") or f"Configuration updated (HTTP {status_code})"

        text = result.get("text")
        if isinstance(text, str) and text.strip():
            lowered_text = text.lower()
            if "<!doctype html" in lowered_text or "<html" in lowered_text:
                if "device administration" in lowered_text or "login failed" in lowered_text:
                    return False, "Device returned login page instead of applying the change"
                return False, "Device returned HTML instead of a configuration response"

        if result.get("success") is True:
            return True, result.get("message") or "Configuration updated"

        status_text = str(result.get("status") or result.get("Status") or "").strip().lower()
        if status_text in {"ok", "success"}:
            return True, result.get("message") or "Configuration updated"

        if result.get("error"):
            return False, str(result.get("error"))

        message = result.get("message") or result.get("Message")
        if isinstance(message, str) and message.strip():
            lowered = message.strip().lower()
            if lowered in {"ok", "success"}:
                return True, message
            return False, message

        if isinstance(text, str) and text.strip():
            lowered = text.strip().lower()
            if lowered in {"ok", "success"}:
                return True, text
            return False, text

        return False, json.dumps(result)

    def _extract(self, text, pattern):
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    # ──────────────────────────────────────────────
    # Core: Device Info
    # ──────────────────────────────────────────────

    def get_device_info(self, ip, port=22, display_id=None):
        username, password = self._get_credentials()

        if not username or not password:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "Crestron Device",
                "current_status": "Offline",
                "error": "Missing credentials: username and password are required.",
            }

        session = None
        try:
            session = self._crestron_login(ip, username, password)
            info_payload = self._fetch_json(session, ip, "/Device/DeviceInfo")
            device_info = ((info_payload or {}).get("Device") or {}).get("DeviceInfo") or {}
        except Exception as e:
            logger.error(f"[CP4N] get_device_info failed: {e}")
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "Crestron Device",
                "current_status": "Offline",
                "error": str(e),
            }
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass

        model = device_info.get("Model")
        device_name = device_info.get("Name") or model or "Crestron Device"
        serial = self._clean_value(device_info.get("SerialNumber"))
        mac = self._normalize_mac(device_info.get("MacAddress") or device_info.get("DeviceId"))
        firmware = (
            self._clean_value(device_info.get("DeviceVersion"))
            or self._clean_value(device_info.get("Version"))
        )
        device_type = "Crestron Device"
        if model and "cp4n" in model.lower():
            device_type = "Crestron CP4N"
        elif model and "am-3200" in model.lower():
            device_type = "Crestron AM-3200"

        return {
            "ip_address": ip,
            "port": port,
            "display_id": display_id,
            "make": device_info.get("Manufacturer", "Crestron"),
            "device_name": device_name,
            "model": model,
            "serial_number": serial or mac,
            "mac_address": mac,
            "firmware": firmware,
            "build_date": device_info.get("BuildDate"),
            "device_id": device_info.get("DeviceId"),
            "device_type": device_type,
            "category": device_info.get("Category"),
            "puf_version": device_info.get("PufVersion"),
            "reboot_reason": device_info.get("RebootReason"),
            "device_key": device_info.get("Devicekey"),
            "api_version": device_info.get("Version"),
            "current_status": "Online",
            "raw_data": info_payload,
        }

    # ──────────────────────────────────────────────
    # Ethernet / IP info
    # ──────────────────────────────────────────────

    def get_ethernet_info(self, ip, port=22):
        """
        Fetch Ethernet/IP settings from /Device/Ethernet.
        Returns a dict with host-level fields and a list of adapter dicts.
        """
        username, password = self._get_credentials()
        session = None
        try:
            session = self._crestron_login(ip, username, password)
            data = self._fetch_json(session, ip, "/Device/Ethernet")
        except Exception as e:
            logger.error(f"[CP4N] get_ethernet_info failed: {e}")
            return {"error": str(e)}
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass

        eth = (data.get("Device") or {}).get("Ethernet", {})
        adapters = eth.get("Adapters", [])
        preferred_adapter = next(
            (
                adapter for adapter in adapters
                if str(adapter.get("Name", "")).strip().lower() == "lan"
            ),
            adapters[0] if adapters else {},
        )
        network = self._extract_ipv4_network_details(preferred_adapter)

        return {
            "hostname": eth.get("HostName"),
            "domain": eth.get("DomainName"),
            "ssh_enabled": eth.get("IsSshEnabled"),
            "icmp_ping_enabled": eth.get("IsIcmpPingEnabled"),
            "adapter_name": network.get("adapter_name"),
            "dhcp_enabled": network.get("dhcp_enabled"),
            "current_ip": network.get("current_ip"),
            "subnet_mask": network.get("subnet_mask"),
            "gateway": network.get("gateway"),
            "dns_servers": network.get("dns_servers"),
            "adapters": adapters,
            "raw_data": data,
        }

    # ========== Hostname and Domain Methods (Using Digest Auth) ==========
    
    def set_hostname_digest(self, ip, hostname, port=22):
        """Set hostname using Digest Authentication (more reliable)"""
        username, password = self._get_credentials()
        
        if not username or not password:
            raise Exception("Missing credentials")
        
        # FIX: Add trailing slash to match API endpoint
        url = f"https://{ip}/Device/Ethernet/"
        
        # Build payload
        payload = {
            "Device": {
                "Ethernet": {
                    "HostName": hostname
                }
            }
        }
        
        logger.info(f"[CP4N] Setting hostname to: {hostname} via Digest Auth")
        logger.debug(f"[CP4N] URL: {url}")
        logger.debug(f"[CP4N] Payload: {json.dumps(payload)}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                auth=HTTPDigestAuth(username, password),
                verify=False,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=15
            )
            
            logger.info(f"[CP4N] set_hostname response status: {response.status_code}")
            
            if response.status_code in [200, 202, 204]:
                try:
                    return response.json()
                except Exception:
                    return {"status": response.status_code, "text": response.text}
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[CP4N] Connection error: {e}")
            raise Exception(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"[CP4N] set_hostname error: {e}")
            raise

    def set_domain_digest(self, ip, domain, port=22):
        """Set domain using Digest Authentication (more reliable)"""
        username, password = self._get_credentials()
        
        if not username or not password:
            raise Exception("Missing credentials")
        
        # FIX: Add trailing slash to match API endpoint
        url = f"https://{ip}/Device/Ethernet/"
        
        # Build payload
        payload = {
            "Device": {
                "Ethernet": {
                    "DomainName": domain
                }
            }
        }
        
        logger.info(f"[CP4N] Setting domain to: {domain} via Digest Auth")
        logger.debug(f"[CP4N] URL: {url}")
        logger.debug(f"[CP4N] Payload: {json.dumps(payload)}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                auth=HTTPDigestAuth(username, password),
                verify=False,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=15
            )
            
            logger.info(f"[CP4N] set_domain response status: {response.status_code}")
            
            if response.status_code in [200, 202, 204]:
                try:
                    return response.json()
                except Exception:
                    return {"status": response.status_code, "text": response.text}
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[CP4N] Connection error: {e}")
            raise Exception(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"[CP4N] set_domain error: {e}")
            raise

    # Fallback methods using session auth
    def set_hostname_session(self, ip, hostname, port=22):
        """Set hostname using session authentication"""
        session = None
        try:
            session = self._login(ip)
            payload = {"Device": {"Ethernet": {"HostName": hostname}}}
            result = self._post_json(session, ip, "/Device/Ethernet", payload)
            logger.info(f"[CP4N] Hostname set to: {hostname} via Session")
            return result
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

    def set_domain_session(self, ip, domain, port=22):
        """Set domain using session authentication"""
        session = None
        try:
            session = self._login(ip)
            payload = {"Device": {"Ethernet": {"DomainName": domain}}}
            result = self._post_json(session, ip, "/Device/Ethernet", payload)
            logger.info(f"[CP4N] Domain set to: {domain} via Session")
            return result
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

    def set_static_ip(self, ip, adapter_name, new_ip, subnet_mask,
                      gateway, dns_primary, dns_secondary, port=22):
        """
        Apply a static IP configuration to a named adapter.
        Returns the API response dict.
        """
        username, password = self._get_credentials()
        session = None
        try:
            session = self._crestron_login(ip, username, password)
            payload = {
                "Device": {
                    "Ethernet": {
                        "Adapters": [
                            {
                                "Name": adapter_name,
                                "IPv4": {
                                    "IsDhcpEnabled": False,
                                    "StaticAddresses": [
                                        {"Address": new_ip, "SubnetMask": subnet_mask}
                                    ],
                                    "StaticDefaultGateway": gateway,
                                    "StaticDns": [dns_primary, dns_secondary],
                                },
                            }
                        ]
                    }
                }
            }
            return self._post_json(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass

    def set_dhcp(self, ip, adapter_name, port=22):
        """
        Enable DHCP on a named adapter.
        Returns the API response dict.
        """
        username, password = self._get_credentials()
        session = None
        try:
            session = self._crestron_login(ip, username, password)
            payload = {
                "Device": {
                    "Ethernet": {
                        "Adapters": [
                            {
                                "Name": adapter_name,
                                "IPv4": {"IsDhcpEnabled": True},
                            }
                        ]
                    }
                }
            }
            return self._post_json(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass

    # ──────────────────────────────────────────────
    # Programs info & IP table
    # ──────────────────────────────────────────────

    def get_programs_info(self, ip, port=22):
        """
        Fetch program slot info from /Device/Programs.
        Returns a dict with counts and a ProgramInstanceLibrary dict.
        """
        username, password = self._get_credentials()
        session = None
        try:
            session = self._crestron_login(ip, username, password)
            data = self._fetch_json(session, ip, "/Device/Programs")
        except Exception as e:
            logger.error(f"[CP4N] get_programs_info failed: {e}")
            return {"error": str(e)}
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass

        p = (data.get("Device") or {}).get("Programs") or data.get("Programs") or {}
        
        slots = {}
        for slot, prog in p.get("ProgramInstanceLibrary", {}).items():
            d = prog.get("ProgramDetails", {})
            slots[slot] = {
                "Status": prog.get("Status", "—"),
                "RegistrationStatus": prog.get("RegistrationStatus", "—"),
                "FriendlyName": d.get("FriendlyName", "—"),
                "ProgramFileName": d.get("ProgramFileName", "—"),
                "Programmer": d.get("Programmer", "—"),
                "CompiledOn": d.get("CompiledOn", "—"),
            }

        return {
            "running_count": p.get("ProgramsRunningCount", 0),
            "registered_count": p.get("ProgramsRegisteredCount", 0),
            "licensed_count": p.get("ProgramsLicensedCount", 0),
            "slots": slots,
            "raw_data": data,
        }

    def get_ip_table(self, ip, slot="DeviceSlot1", port=22):
        """
        Fetch the IP table for a given program slot.
        Slot may be '1', '2', ... or 'DeviceSlot1', 'DeviceSlot2', etc.
        Returns a list of entry dicts sorted by IP ID.
        """
        slot = self._normalize_slot(slot)
        username, password = self._get_credentials()
        session = None
        try:
            session = self._crestron_login(ip, username, password)
            data = self._fetch_json(
                session, ip,
                f"/Device/Programs/ProgramInstanceLibrary/{slot}/IpTable"
            )
        except Exception as e:
            logger.error(f"[CP4N] get_ip_table failed: {e}")
            return {"error": str(e), "slot": slot, "entries": []}
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass

        entries = (
            (data.get("Device") or {})
            .get("Programs", {})
            .get("ProgramInstanceLibrary", {})
            .get(slot, {})
            .get("IpTable", {})
            .get("Entries") or {}
        )

        def _sort_key(k):
            try:
                return (0, int(k, 16))
            except Exception:
                return (1, k)

        sorted_entries = [e for _, e in sorted(entries.items(), key=lambda x: _sort_key(x[0]))]
        return {"slot": slot, "entries": sorted_entries, "raw_data": data}

    # ──────────────────────────────────────────────
    # Program slot commands
    # ──────────────────────────────────────────────

    VALID_PROGRAM_COMMANDS = {"Start", "Stop", "Restart", "Register", "Unregister"}

    def send_program_command(self, ip, command, slot="DeviceSlot1", port=22):
        """
        Send a lifecycle command to a program slot.
        command must be one of: Start, Stop, Restart, Register, Unregister.
        Returns the API response dict, or raises ValueError for invalid commands.
        """
        if command not in self.VALID_PROGRAM_COMMANDS:
            raise ValueError(
                f"Invalid command '{command}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_PROGRAM_COMMANDS))}"
            )

        slot = self._normalize_slot(slot)
        username, password = self._get_credentials()
        session = None
        try:
            session = self._crestron_login(ip, username, password)
            payload = {
                "Device": {
                    "Programs": {
                        "ProgramInstanceLibrary": {slot: {command: True}}
                    }
                }
            }
            return self._post_json(
                session, ip,
                f"/Device/Programs/ProgramInstanceLibrary/{slot}",
                payload
            )
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass

    # ──────────────────────────────────────────────
    # Reboot (SSH-first with API fallback)
    # ──────────────────────────────────────────────

    def _reboot_via_ssh(self, ip, username, password):
        """Reboot via SSH using paramiko. Returns a result dict."""
        if not PARAMIKO_AVAILABLE:
            return {
                "success": False,
                "method": "ssh",
                "message": "Paramiko not installed. Run: pip install paramiko",
            }
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password, timeout=10)
            ssh.exec_command("reboot")
            ssh.close()
            return {"success": True, "method": "ssh", "message": "SSH reboot command sent"}
        except paramiko.AuthenticationException:
            return {"success": False, "method": "ssh", "message": "SSH authentication failed"}
        except paramiko.SSHException as e:
            return {"success": False, "method": "ssh", "message": f"SSH error: {e}"}
        except Exception as e:
            return {"success": False, "method": "ssh", "message": str(e)}

    def _reboot_via_api(self, ip, username, password):
        """Reboot via REST API with Digest Auth. Returns a result dict."""
        reboot_url = f"https://{ip}/Device/DeviceOperations/"
        payload = {"Device": {"DeviceOperations": {"Reboot": True}}}
        try:
            response = requests.post(
                reboot_url,
                json=payload,
                auth=HTTPDigestAuth(username, password),
                verify=False,
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if response.status_code in [200, 202, 204]:
                return {"success": True, "method": "api", "message": "API reboot command accepted"}
            if response.status_code == 401:
                return {"success": False, "method": "api", "message": "Authentication failed (401)"}
            if response.status_code == 403:
                return {"success": False, "method": "api", "message": "API access forbidden (403)"}
            return {
                "success": False,
                "method": "api",
                "message": f"Unexpected HTTP {response.status_code}",
            }
        except requests.exceptions.ConnectTimeout:
            return {
                "success": True,
                "method": "api",
                "message": "Connection timeout — device likely rebooting",
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": True,
                "method": "api",
                "message": "Connection lost — device likely rebooting",
            }
        except Exception as e:
            return {"success": False, "method": "api", "message": str(e)}

    def reboot_device(self, ip, port=22):
        """
        Smart reboot: tries SSH first (if paramiko is available), then falls back to API.
        Returns a result dict: {"success": bool, "method": str, "message": str}
        """
        username, password = self._get_credentials()

        if not username or not password:
            return {
                "success": False,
                "method": "none",
                "message": "Missing credentials: username and password are required.",
            }

        if PARAMIKO_AVAILABLE:
            result = self._reboot_via_ssh(ip, username, password)
            if result["success"]:
                return result

        return self._reboot_via_api(ip, username, password)

    def check_ping(self, ip):
        """Return True if the device responds to a single ping."""
        try:
            response = subprocess.run(
                ["ping", "-c", "1", "-W", "1", ip],
                capture_output=True,
                timeout=3,
            )
            return response.returncode == 0
        except Exception:
            return False

    def wait_for_reboot(self, ip, wait_time=180):
        """
        Block until the device goes offline then comes back online.
        Returns True if the device came back within wait_time seconds, False otherwise.
        """
        offline_detected = False
        start = time.time()
        while time.time() - start < 30:
            if not self.check_ping(ip):
                offline_detected = True
                break
            time.sleep(1)

        if not offline_detected:
            return False

        time.sleep(3)

        online_detected = False
        start = time.time()
        while time.time() - start < wait_time:
            if self.check_ping(ip):
                online_detected = True
                break
            time.sleep(2)

        if not online_detected:
            return False

        time.sleep(5)
        start = time.time()
        while time.time() - start < 60:
            for scheme in ("https", "http"):
                try:
                    r = requests.get(f"{scheme}://{ip}", timeout=3, verify=False)
                    if r.status_code in [200, 401, 403]:
                        return True
                except Exception:
                    pass
            time.sleep(2)

        return True

    # ──────────────────────────────────────────────
    # Main Command Handler
    # ──────────────────────────────────────────────

    def send_command(self, ip, port, display_id, command, params=None):
        """
        Handle all CP4N commands.
        This is the main entry point called by cloud_connector.py
        """
        username, password = self._get_credentials()
        
        if not username or not password:
            return False, "Missing credentials"

        logger.info(f"[CP4N] Sending command: {command} to {ip}, params: {params}")
        
        # Handle params as dictionary (preferred method from frontend via cloud)
        if params and isinstance(params, dict):
            action = command
            cmd_params = params
        else:
            # Handle legacy string format with colon separation
            if isinstance(command, str) and ':' in command:
                action, param_str = command.split(':', 1)
                cmd_params = {'params': param_str.split(',')}
            else:
                action = command
                cmd_params = {}

        try:
            # ========== Status Commands ==========
            if action == "get_status" or action == "get_device_info":
                device_info = self.get_device_info(ip, port, display_id)
                eth_info = self.get_ethernet_info(ip, port)
                programs_info = self.get_programs_info(ip, port)
                
                result = {
                    "reachable": True,
                    "device_info": device_info,
                    "ethernet_info": eth_info,
                    "programs_info": programs_info,
                    "current_ip": eth_info.get("current_ip") if isinstance(eth_info, dict) else None,
                    "mac_address": device_info.get("mac_address"),
                    "model": device_info.get("model"),
                    "serial_number": device_info.get("serial_number"),
                    "firmware": device_info.get("firmware"),
                    "api_version": device_info.get("api_version"),
                    "build_date": device_info.get("build_date"),
                    "category": device_info.get("category"),
                    "puf_version": device_info.get("puf_version"),
                    "device_key": device_info.get("device_key"),
                    "hostname": eth_info.get("hostname") if isinstance(eth_info, dict) else None,
                    "domain": eth_info.get("domain") if isinstance(eth_info, dict) else None,
                }
                return True, json.dumps(result)

            elif action == "get_ethernet":
                result = self.get_ethernet_info(ip, port)
                return True, json.dumps(result)

            elif action == "get_programs":
                result = self.get_programs_info(ip, port)
                return True, json.dumps(result)

            elif action == "get_iptable":
                if isinstance(cmd_params, dict):
                    slot = cmd_params.get('slot', 'DeviceSlot1')
                else:
                    slot = "DeviceSlot1"
                logger.info(f"[CP4N] Getting IP table for slot: {slot}")
                result = self.get_ip_table(ip, slot, port)
                return True, json.dumps(result)

            # ========== Network Commands ==========
            elif action == "set_static_ip":
                if isinstance(cmd_params, dict):
                    adapter = cmd_params.get('adapter', 'LAN')
                    address = cmd_params.get('address', '')
                    mask = cmd_params.get('mask', '255.255.255.0')
                    gateway = cmd_params.get('gateway', '')
                    dns1 = cmd_params.get('dns1', '8.8.8.8')
                    dns2 = cmd_params.get('dns2', '8.8.4.4')
                else:
                    params_list = cmd_params.get('params', [])
                    adapter = params_list[0] if len(params_list) > 0 else "LAN"
                    address = params_list[1] if len(params_list) > 1 else ""
                    mask = params_list[2] if len(params_list) > 2 else "255.255.255.0"
                    gateway = params_list[3] if len(params_list) > 3 else ""
                    dns1 = params_list[4] if len(params_list) > 4 else "8.8.8.8"
                    dns2 = params_list[5] if len(params_list) > 5 else "8.8.4.4"
                
                result = self.set_static_ip(ip, adapter, address, mask, gateway, dns1, dns2, port)
                ok, message = self._is_config_write_success(result)
                payload = {
                    "success": ok,
                    "message": message,
                    "result": result,
                }
                return ok, json.dumps(payload)

            elif action == "set_dhcp":
                if isinstance(cmd_params, dict):
                    adapter = cmd_params.get('adapter', 'LAN')
                else:
                    params_list = cmd_params.get('params', [])
                    adapter = params_list[0] if params_list else "LAN"
                
                result = self.set_dhcp(ip, adapter, port)
                ok, message = self._is_config_write_success(result)
                payload = {
                    "success": ok,
                    "message": message,
                    "result": result,
                }
                return ok, json.dumps(payload)

            # ========== Hostname and Domain Commands (Using Digest Auth) ==========
            elif action == "set_hostname":
                if isinstance(cmd_params, dict):
                    hostname = cmd_params.get('hostname', '')
                else:
                    hostname = cmd_params.get('params', [''])[0] if cmd_params.get('params') else ''
                
                if hostname:
                    # Validate hostname format
                    import re
                    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', hostname):
                        return False, json.dumps({
                            "success": False,
                            "message": "Invalid hostname format. Use only letters, numbers, and hyphens. Cannot start or end with hyphen."
                        })
                    
                    try:
                        result = self.set_hostname_digest(ip, hostname, port)
                        ok, message = self._is_config_write_success(result)
                        if not ok:
                            # Try session auth as fallback
                            logger.warning(f"[CP4N] Digest auth failed, trying session auth: {message}")
                            result = self.set_hostname_session(ip, hostname, port)
                            ok, message = self._is_config_write_success(result)
                    except Exception as e:
                        logger.warning(f"[CP4N] Digest auth failed, trying session auth: {e}")
                        try:
                            result = self.set_hostname_session(ip, hostname, port)
                            ok, message = self._is_config_write_success(result)
                        except Exception as e2:
                            return False, json.dumps({
                                "success": False,
                                "message": f"Failed to set hostname: {str(e2)}"
                            })
                    
                    payload = {
                        "success": ok,
                        "message": message if ok else f"Failed to set hostname: {message}",
                        "result": result,
                    }
                    return ok, json.dumps(payload)
                return False, json.dumps({"success": False, "message": "Missing hostname"})

            elif action == "set_domain":
                if isinstance(cmd_params, dict):
                    domain = cmd_params.get('domain', '')
                else:
                    domain = cmd_params.get('params', [''])[0] if cmd_params.get('params') else ''
                
                if domain:
                    try:
                        result = self.set_domain_digest(ip, domain, port)
                        ok, message = self._is_config_write_success(result)
                        if not ok:
                            # Try session auth as fallback
                            logger.warning(f"[CP4N] Digest auth failed, trying session auth: {message}")
                            result = self.set_domain_session(ip, domain, port)
                            ok, message = self._is_config_write_success(result)
                    except Exception as e:
                        logger.warning(f"[CP4N] Digest auth failed, trying session auth: {e}")
                        try:
                            result = self.set_domain_session(ip, domain, port)
                            ok, message = self._is_config_write_success(result)
                        except Exception as e2:
                            return False, json.dumps({
                                "success": False,
                                "message": f"Failed to set domain: {str(e2)}"
                            })
                    
                    payload = {
                        "success": ok,
                        "message": message if ok else f"Failed to set domain: {message}",
                        "result": result,
                    }
                    return ok, json.dumps(payload)
                return False, json.dumps({"success": False, "message": "Missing domain"})

            # ========== Security Commands ==========
            elif action == "set_ping":
                enabled = cmd_params.get('enabled', True) if isinstance(cmd_params, dict) else True
                session = self._login(ip)
                result = self._post_json(session, ip, "/Device/Ethernet", {"Device": {"Ethernet": {"IsIcmpPingEnabled": enabled}}})
                session.close()
                return True, json.dumps(result)

            elif action == "set_ssh":
                enabled = cmd_params.get('enabled', True) if isinstance(cmd_params, dict) else True
                session = self._login(ip)
                result = self._post_json(session, ip, "/Device/Ethernet", {"Device": {"Ethernet": {"IsSshEnabled": enabled}}})
                session.close()
                return True, json.dumps(result)

            elif action == "set_igmp":
                version = cmd_params.get('version', 'v2') if isinstance(cmd_params, dict) else "v2"
                session = self._login(ip)
                result = self._post_json(session, ip, "/Device/Ethernet", {"Device": {"Ethernet": {"IgmpVersion": version}}})
                session.close()
                return True, json.dumps(result)

            # ========== Program Commands ==========
            elif action == "program_command":
                if isinstance(cmd_params, dict):
                    command_name = cmd_params.get('command', '')
                    slot = cmd_params.get('slot', 'DeviceSlot1')
                else:
                    params_list = cmd_params.get('params', [])
                    command_name = params_list[0] if len(params_list) > 0 else ""
                    slot = params_list[1] if len(params_list) > 1 else "DeviceSlot1"
                
                if command_name:
                    result = self.send_program_command(ip, command_name, slot, port)
                    return True, json.dumps(result)
                return False, "Missing program command"

            # ========== Reboot Commands ==========
            elif action == "reboot":
                result = self.reboot_device(ip, port)
                return result.get("success", False), result.get("message", "")

            elif action == "wait_reboot":
                wait_time = cmd_params.get('wait_time', 180) if isinstance(cmd_params, dict) else 180
                result = self.wait_for_reboot(ip, wait_time)
                return result, "Reboot completed" if result else "Reboot timeout"

            else:
                return False, f"Unknown command: {action}"

        except Exception as e:
            logger.error(f"[CP4N] Command failed: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)

    def query_status(self, ip, port=22, display_id=None):
        """Quick status query for device list"""
        try:
            device_info = self.get_device_info(ip, port, display_id)
            eth_info = self.get_ethernet_info(ip, port)
            
            return {
                "reachable": device_info.get("current_status") == "Online",
                "device_name": device_info.get("device_name"),
                "model": device_info.get("model"),
                "serial_number": device_info.get("serial_number"),
                "firmware": device_info.get("firmware"),
                "current_ip": eth_info.get("current_ip") if isinstance(eth_info, dict) else None,
                "hostname": eth_info.get("hostname") if isinstance(eth_info, dict) else None,
                "domain": eth_info.get("domain") if isinstance(eth_info, dict) else None,
                "error": device_info.get("error"),
            }
        except Exception as e:
            logger.error(f"[CP4N] query_status failed: {e}")
            return {
                "reachable": False,
                "error": str(e),
            }