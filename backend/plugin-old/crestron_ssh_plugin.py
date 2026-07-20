
"""
crestron_ssh_plugin.py - Crestron CP4N Edge Collector Plugin
Fixed to properly return device information for frontend
"""

import json
import time
import subprocess
import re
import requests
import logging
from requests.auth import HTTPDigestAuth

# Import the base class - THIS IS CRITICAL
from .base import ManualPlatformPlugin

# Setup logger
logger = logging.getLogger(__name__)

# Try to import paramiko for SSH support
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class CrestronCP4NPlugin(ManualPlatformPlugin):  # MUST inherit from ManualPlatformPlugin
    """Crestron CP4N Full Management Plugin for Edge Collector."""

    name = "crestron_ssh"
    display_name = "Crestron CP4N"
    description = "Crestron CP4N Control System Manager"
    default_port = 443
    SUPPORTED_MODELS = ["CP4N", "CP4", "CP3", "MC4", "AV4", "4-Series"]

    def __init__(self, config=None):
        # Call parent constructor
        super().__init__(config)
        self.username = self.config.get("username") if self.config else None
        self.password = self.config.get("password") if self.config else None
        self.session = None
        self._xsrf_token = None
        logger.info(f"[CrestronSSH] Initialized with username: {self.username}")

    # ──────────────────────────────────────────────
    # Authentication
    # ──────────────────────────────────────────────

    def _login(self, ip):
        """Login and return session with proper XSRF token handling"""
        if not self.username or not self.password:
            raise Exception("Missing credentials")
            
        base_url = f"https://{ip}"
        login_url = f"{base_url}/userlogin.html"
        session = requests.Session()
        session.verify = False
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        # Step 1: Get login page to capture TRACKID
        r = session.get(login_url, timeout=8)
        r.raise_for_status()
        trackid = session.cookies.get("TRACKID")
        if not trackid:
            raise Exception("TRACKID cookie not found on login page.")

        # Step 2: POST credentials
        r2 = session.post(
            login_url,
            headers={
                "Cookie": f"TRACKID={trackid}",
                "Origin": base_url,
                "Referer": login_url,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0",
            },
            data={"login": self.username, "passwd": self.password},
            timeout=10,
        )

        if r2.status_code == 403:
            raise Exception("Invalid credentials (403).")
        if r2.status_code != 200:
            raise Exception(f"Login failed (HTTP {r2.status_code})")

        # Step 3: Capture XSRF token from headers
        xsrf = r2.headers.get("CREST-XSRF-TOKEN")
        if xsrf:
            session.headers.update({
                "CREST-XSRF-TOKEN": xsrf,
                "X-CREST-XSRF-TOKEN": xsrf,
            })
            self._xsrf_token = xsrf

        logger.info(f"[CrestronSSH] Login successful for {ip}")
        return session

    def _get(self, session, ip, path):
        """GET request with session"""
        url = f"https://{ip}{path}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }
        if self._xsrf_token:
            headers["CREST-XSRF-TOKEN"] = self._xsrf_token
            headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token
        
        r = session.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def _post(self, session, ip, path, payload):
        """POST request with session"""
        url = f"https://{ip}{path}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }
        if self._xsrf_token:
            headers["CREST-XSRF-TOKEN"] = self._xsrf_token
            headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token
        
        r = session.post(url, json=payload, headers=headers, timeout=10)
        
        if r.status_code == 403:
            # Try to re-login and retry once
            logger.warning("[CrestronSSH] Session expired, re-authenticating...")
            session = self._login(ip)
            if self._xsrf_token:
                headers["CREST-XSRF-TOKEN"] = self._xsrf_token
                headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token
            r = session.post(url, json=payload, headers=headers, timeout=10)
        
        r.raise_for_status()
        try:
            return r.json()
        except:
            return {"status": r.status_code, "text": r.text}

    @staticmethod
    def _clean_network_value(value):
        """Normalize blank or placeholder network values."""
        if value is None:
            return None
        value = str(value).strip()
        if not value or value in {"-", "—", "â€”"}:
            return None
        return value

    @staticmethod
    def _normalize_slot(slot):
        """Accept '1' or 'DeviceSlot1' — always return 'DeviceSlot1'"""
        slot = str(slot).strip()
        if slot.isdigit():
            return f"DeviceSlot{slot}"
        return slot

    # ──────────────────────────────────────────────
    # Device Information Methods
    # ──────────────────────────────────────────────

    def get_device_info(self, ip, port=443, display_id=None):
        """Get device information - returns full device info for frontend"""
        if not self.username or not self.password:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "Crestron CP4N",
                "current_status": "Offline",
                "error": "Missing credentials",
            }

        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/DeviceInfo")
            di = (data.get("Device") or {}).get("DeviceInfo") or data.get("DeviceInfo") or {}
            
            # Get ethernet info as well
            eth_data = {}
            current_ip = ip
            hostname = ""
            domain = ""
            try:
                eth_data = self._get(session, ip, "/Device/Ethernet")
                ethernet = (eth_data.get("Device") or {}).get("Ethernet", {})
                hostname = ethernet.get("HostName", "")
                domain = ethernet.get("DomainName", "")
                adapters = ethernet.get("Adapters", [])
                if adapters:
                    ipv4 = adapters[0].get("IPv4", {})
                    addresses = ipv4.get("Addresses", [])
                    if addresses and addresses[0].get("Address"):
                        current_ip = addresses[0].get("Address")
            except Exception as e:
                logger.warning(f"[CrestronSSH] Could not fetch ethernet info: {e}")
            
            logger.info(f"[CrestronSSH] Device info retrieved: Model={di.get('Model')}, Serial={di.get('SerialNumber')}")
            logger.info(f"[CrestronSSH] Hostname from ethernet: {hostname}")
            
            return {
                "ip_address": current_ip,
                "port": port,
                "display_id": display_id,
                "make": di.get("Manufacturer", "Crestron"),
                "device_name": di.get("Name") or di.get("Model") or "Crestron CP4N",
                "model": di.get("Model"),
                "serial_number": di.get("SerialNumber"),
                "mac_address": di.get("MacAddress") or di.get("DeviceId"),
                "firmware": di.get("DeviceVersion"),
                "puf_version": di.get("PufVersion"),
                "api_version": di.get("Version"),
                "build_date": di.get("BuildDate"),
                "category": di.get("Category"),
                "reboot_reason": di.get("RebootReason"),
                "device_id": di.get("DeviceId"),
                "device_key": di.get("Devicekey"),
                "hostname": self._clean_network_value(hostname),
                "domain": self._clean_network_value(domain),
                "device_type": "Crestron CP4N",
                "current_status": "Online",
                "raw_data": data,
            }
        except Exception as e:
            logger.error(f"[CrestronSSH] get_device_info failed: {e}")
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "Crestron CP4N",
                "current_status": "Offline",
                "error": str(e),
            }
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

    def get_ethernet_info(self, ip, port=443):
        """Get Ethernet/IP settings - returns full ethernet info for frontend"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/Ethernet")
        except Exception as e:
            logger.error(f"[CrestronSSH] get_ethernet_info failed: {e}")
            return {"error": str(e)}
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

        eth_root = (data.get("Device") or {}).get("Ethernet", {})
        adapters = eth_root.get("Adapters", [])
        
        current_ip = None
        # Get fresh hostname directly from API response
        hostname = eth_root.get("HostName", "")
        domain = eth_root.get("DomainName", "")
        ssh_enabled = eth_root.get("IsSshEnabled", False)
        icmp_enabled = eth_root.get("IsIcmpPingEnabled", False)
        
        logger.info(f"[CrestronSSH] Raw ethernet response - HostName: '{hostname}', DomainName: '{domain}'")
        
        adapter_list = []
        for adapter in adapters:
            ipv4 = adapter.get("IPv4", {})
            addresses = ipv4.get("Addresses", [])
            if addresses and addresses[0].get("Address"):
                current_ip = addresses[0].get("Address")
            
            adapter_list.append({
                "name": adapter.get("Name", "Unknown"),
                "type": adapter.get("Type", "Unknown"),
                "mac_address": adapter.get("MacAddress", ""),
                "link_status": adapter.get("LinkStatus", False),
                "is_enabled": adapter.get("IsAdapterEnabled", False),
                "dhcp_enabled": ipv4.get("IsDhcpEnabled", False),
                "ip_address": addresses[0].get("Address", "") if addresses else "",
                "subnet_mask": addresses[0].get("SubnetMask", "") if addresses else "",
                "default_gateway": ipv4.get("DefaultGateway", ""),
                "dns_servers": ipv4.get("DnsServers", []),
            })

        return {
            "hostname": self._clean_network_value(hostname),
            "domain": self._clean_network_value(domain),
            "domain_name": self._clean_network_value(domain),
            "ssh_enabled": ssh_enabled,
            "icmp_ping_enabled": icmp_enabled,
            "current_ip": current_ip or ip,
            "adapters": adapter_list,
            "raw_data": data,
        }

    def get_programs_info(self, ip, port=443):
        """Get programs information - returns programs_info with raw_data for frontend"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/Programs")
        except Exception as e:
            logger.error(f"[CrestronSSH] get_programs_info failed: {e}")
            return {"error": str(e)}
        finally:
            if session:
                try:
                    session.close()
                except:
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
            "raw_data": data,  # Required for IP table
        }

    def get_ip_table(self, ip, slot="DeviceSlot1", port=443):
        """Get IP table for a slot"""
        slot = self._normalize_slot(slot)
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, f"/Device/Programs/ProgramInstanceLibrary/{slot}/IpTable")
        except Exception as e:
            logger.error(f"[CrestronSSH] get_ip_table failed: {e}")
            return {"error": str(e), "slot": slot, "entries": []}
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

        entries = (
            (data.get("Device") or {})
            .get("Programs", {})
            .get("ProgramInstanceLibrary", {})
            .get(slot, {})
            .get("IpTable", {})
            .get("Entries")
        )

        if not entries:
            return {"slot": slot, "entries": []}

        sorted_entries = []
        for ip_id, entry in entries.items():
            sorted_entries.append({
                "IpId": entry.get("IpId", ip_id),
                "Address": entry.get("Address", ""),
                "Port": entry.get("Port", ""),
                "ConnectionType": entry.get("ConnectionType", ""),
                "Status": entry.get("Status", ""),
                "Model": entry.get("Model", ""),
                "Description": entry.get("Description", ""),
            })
        
        try:
            sorted_entries.sort(key=lambda x: int(x.get("IpId", "0"), 16))
        except:
            pass
        
        return {"slot": slot, "entries": sorted_entries, "raw_data": data}

    # ──────────────────────────────────────────────
    # Command Methods - UPDATED with verification
    # ──────────────────────────────────────────────

    def set_hostname(self, ip, hostname, port=443):
        """Set the device hostname with proper session handling"""
        try:
            import re
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', hostname):
                raise Exception("Invalid hostname format")
            if len(hostname) > 63:
                raise Exception("Hostname too long")
            
            # Use session-based approach instead of direct requests
            session = None
            try:
                session = self._login(ip)
                
                # First, get current ethernet config
                current_eth = self._get(session, ip, "/Device/Ethernet")
                logger.info(f"[CrestronSSH] Current ethernet config before change: {json.dumps(current_eth, indent=2)}")
                
                # Build the payload - use PATCH style update
                payload = {
                    "Device": {
                        "Ethernet": {
                            "HostName": hostname
                        }
                    }
                }
                
                logger.info(f"[CrestronSSH] Sending hostname update payload: {json.dumps(payload)}")
                
                # Send the update using the same session
                result = self._post(session, ip, "/Device/Ethernet", payload)
                logger.info(f"[CrestronSSH] POST result: {json.dumps(result, indent=2)}")
                
                # Wait for the change to propagate
                time.sleep(3)
                
                # Verify using the SAME session
                verify_data = self._get(session, ip, "/Device/Ethernet")
                eth_root = (verify_data.get("Device") or {}).get("Ethernet", {})
                current_hostname = eth_root.get("HostName", "")
                
                logger.info(f"[CrestronSSH] Verified hostname after update: '{current_hostname}' (expected '{hostname}')")
                
                # Also check if there's any pending changes
                device_ops = self._get(session, ip, "/Device/DeviceOperations")
                logger.info(f"[CrestronSSH] Device operations: {json.dumps(device_ops, indent=2)}")
                
                if current_hostname == hostname:
                    return {"success": True, "message": f"Hostname successfully set to '{hostname}'", "verified": True}
                else:
                    # Try one more time with a different approach
                    logger.warning(f"[CrestronSSH] First verification failed, trying alternative method...")
                    
                    # Alternative: Use Digest Auth directly
                    url = f"https://{ip}/Device/Ethernet/"
                    alt_payload = {"Ethernet": {"HostName": hostname}}
                    
                    alt_response = requests.patch(
                        url,
                        json=alt_payload,
                        auth=HTTPDigestAuth(self.username, self.password),
                        verify=False,
                        headers={"Content-Type": "application/json"},
                        timeout=15
                    )
                    
                    if alt_response.status_code in [200, 202, 204]:
                        time.sleep(2)
                        # Verify again
                        verify_session = self._login(ip)
                        final_verify = self._get(verify_session, ip, "/Device/Ethernet")
                        verify_session.close()
                        
                        final_hostname = (final_verify.get("Device") or {}).get("Ethernet", {}).get("HostName", "")
                        if final_hostname == hostname:
                            return {"success": True, "message": f"Hostname successfully set to '{hostname}'", "verified": True}
                    
                    return {"success": True, "message": f"Hostname set to '{hostname}'. A device reboot may be required for the change to take effect.", "verified": False, "needs_reboot": True}
                    
            finally:
                if session:
                    try:
                        session.close()
                    except:
                        pass
                    
        except Exception as e:
            logger.error(f"[CrestronSSH] set_hostname failed: {e}")
            import traceback
            traceback.print_exc()
            raise



    def set_domain(self, ip, domain, port=443):
        """Set the device domain with verification"""
        try:
            url = f"https://{ip}/Device/Ethernet/"
            payload = {"Device": {"Ethernet": {"DomainName": domain}}}
            
            logger.info(f"[CrestronSSH] Setting domain to '{domain}' on {ip}")
            
            response = requests.post(
                url,
                json=payload,
                auth=HTTPDigestAuth(self.username, self.password),
                verify=False,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code not in [200, 202, 204]:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
            
            # Wait for the change to propagate
            time.sleep(2)
            
            # Verify the change
            try:
                verify_session = self._login(ip)
                verify_data = self._get(verify_session, ip, "/Device/Ethernet")
                verify_session.close()
                
                eth_root = (verify_data.get("Device") or {}).get("Ethernet", {})
                current_domain = eth_root.get("DomainName", "")
                
                logger.info(f"[CrestronSSH] Verified domain: '{current_domain}' (expected '{domain}')")
                
                if current_domain == domain:
                    return {"success": True, "message": f"Domain successfully set to '{domain}'", "verified": True}
                else:
                    return {"success": True, "message": f"Domain set to '{domain}' (may need reboot to fully apply)", "verified": False}
            except Exception as e:
                logger.warning(f"[CrestronSSH] Could not verify domain: {e}")
            
            return {"success": True, "message": f"Domain set to '{domain}'"}
        except Exception as e:
            logger.error(f"[CrestronSSH] set_domain failed: {e}")
            raise

    def set_static_ip(self, ip, adapter_name, new_ip, subnet_mask, gateway, dns1, dns2, port=443):
        """Set static IP configuration"""
        session = None
        try:
            session = self._login(ip)
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
                                    "StaticDns": [dns1, dns2],
                                },
                            }
                        ]
                    }
                }
            }
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

    def set_dhcp(self, ip, adapter_name, port=443):
        """Enable DHCP"""
        session = None
        try:
            session = self._login(ip)
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
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

    def send_program_command(self, ip, command, slot="DeviceSlot1", port=443):
        """Send program command (Start, Stop, Restart, Register, Unregister)"""
        valid_commands = {"Start", "Stop", "Restart", "Register", "Unregister"}
        if command not in valid_commands:
            raise ValueError(f"Invalid command: {command}")

        slot = self._normalize_slot(slot)
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "Programs": {
                        "ProgramInstanceLibrary": {slot: {command: True}}
                    }
                }
            }
            return self._post(session, ip, f"/Device/Programs/ProgramInstanceLibrary/{slot}", payload)
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

    def reboot_via_ssh(self, ip):
        """Reboot via SSH"""
        if not PARAMIKO_AVAILABLE:
            return {"success": False, "method": "ssh", "message": "Paramiko not installed"}
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=self.username, password=self.password, timeout=10)
            ssh.exec_command("reboot")
            ssh.close()
            return {"success": True, "method": "ssh", "message": "SSH reboot command sent"}
        except Exception as e:
            return {"success": False, "method": "ssh", "message": str(e)}

    def reboot_via_api(self, ip):
        """Reboot via API"""
        reboot_url = f"https://{ip}/Device/DeviceOperations/"
        payload = {"Device": {"DeviceOperations": {"Reboot": True}}}
        try:
            response = requests.post(
                reboot_url,
                json=payload,
                auth=HTTPDigestAuth(self.username, self.password),
                verify=False,
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if response.status_code in [200, 202, 204]:
                return {"success": True, "method": "api", "message": "API reboot accepted"}
            return {"success": False, "method": "api", "message": f"HTTP {response.status_code}"}
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            return {"success": True, "method": "api", "message": "Connection lost - rebooting"}
        except Exception as e:
            return {"success": False, "method": "api", "message": str(e)}

    def reboot_device(self, ip, port=443):
        """Smart reboot - tries SSH first, then API"""
        if PARAMIKO_AVAILABLE:
            result = self.reboot_via_ssh(ip)
            if result["success"]:
                return result
        return self.reboot_via_api(ip)

    # ──────────────────────────────────────────────
    # Main Query and Command Handlers - UPDATED
    # ──────────────────────────────────────────────

    def query_status(self, ip, port=443, display_id=None):
        """Quick status query - returns full device data for frontend"""
        try:
            logger.info(f"[CrestronSSH] query_status called for {ip}:{port}")
            
            # ALWAYS fetch fresh data directly from device
            device_info = self.get_device_info(ip, port, display_id)
            eth_info = self.get_ethernet_info(ip, port)
            programs_info = self.get_programs_info(ip, port)
            
            # Get fresh hostname and domain from ethernet info
            fresh_hostname = eth_info.get("hostname", "")
            fresh_domain = eth_info.get("domain", "")
            
            logger.info(f"[CrestronSSH] Fresh hostname from device: '{fresh_hostname}'")
            
            # Check if hostname needs reboot
            expected_hostname = getattr(self, '_pending_hostname', None)
            needs_reboot = False
            if expected_hostname and expected_hostname != fresh_hostname:
                needs_reboot = True
                logger.warning(f"[CrestronSSH] Hostname mismatch: expected '{expected_hostname}', got '{fresh_hostname}'")
            
            # Build the response
            result = {
                "reachable": device_info.get("current_status") == "Online",
                "power": "ON",
                "device_name": fresh_hostname or device_info.get("device_name"),
                "model": device_info.get("model"),
                "serial_number": device_info.get("serial_number"),
                "firmware": device_info.get("firmware"),
                "current_ip": eth_info.get("current_ip", ip),
                "mac_address": device_info.get("mac_address"),
                "hostname": fresh_hostname,
                "domain": fresh_domain,
                "ssh_enabled": eth_info.get("ssh_enabled", False),
                "icmp_ping_enabled": eth_info.get("icmp_ping_enabled", False),
                "needs_reboot": needs_reboot,  # Add this flag
                "device_info": {
                    "Model": device_info.get("model"),
                    "Name": fresh_hostname or device_info.get("device_name"),
                    "SerialNumber": device_info.get("serial_number"),
                    "MacAddress": device_info.get("mac_address"),
                    "DeviceVersion": device_info.get("firmware"),
                    "PufVersion": device_info.get("puf_version"),
                    "Version": device_info.get("api_version"),
                    "BuildDate": device_info.get("build_date"),
                    "Category": device_info.get("category"),
                    "Manufacturer": device_info.get("make"),
                    "DeviceId": device_info.get("device_id"),
                },
                "ethernet_info": {
                    "hostname": fresh_hostname,
                    "domain": fresh_domain,
                    "domain_name": fresh_domain,
                    "ssh_enabled": eth_info.get("ssh_enabled", False),
                    "icmp_ping_enabled": eth_info.get("icmp_ping_enabled", False),
                    "current_ip": eth_info.get("current_ip", ip),
                    "host_name": fresh_hostname,
                },
                "programs_info": {
                    "running_count": programs_info.get("running_count", 0),
                    "registered_count": programs_info.get("registered_count", 0),
                    "licensed_count": programs_info.get("licensed_count", 0),
                    "slots": programs_info.get("slots", {}),
                    "raw_data": programs_info.get("raw_data"),
                },
                "error": device_info.get("error"),
            }
            
            return result
            
        except Exception as e:
            logger.error(f"[CrestronSSH] query_status failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "reachable": False,
                "error": str(e),
                "device_info": {},
                "ethernet_info": {},
                "programs_info": {"slots": {}, "raw_data": None}
            }

    def send_command(self, ip, port, display_id, command, params=None):
        """
        Handle all CP4N commands.
        This is the main entry point called by cloud_connector.py
        """
        if not self.username or not self.password:
            return False, "Missing credentials"

        logger.info(f"[CrestronSSH] Sending command: {command} to {ip}, params: {params}")
        
        cmd_params = params or {}

        try:
            # ========== Status Commands ==========
            if command == "get_status":
                result = self.query_status(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_device_info":
                result = self.get_device_info(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_ethernet_info":
                result = self.get_ethernet_info(ip, port)
                return True, json.dumps(result)

            elif command == "get_programs":
                result = self.get_programs_info(ip, port)
                return True, json.dumps(result)

            elif command == "get_iptable":
                slot = cmd_params.get('slot', 'DeviceSlot1')
                result = self.get_ip_table(ip, slot, port)
                return True, json.dumps(result)

            # ========== Network Commands ==========
            elif command == "set_static_ip":
                adapter = cmd_params.get('adapter', 'LAN')
                address = cmd_params.get('address', '')
                mask = cmd_params.get('mask', '255.255.255.0')
                gateway = cmd_params.get('gateway', '')
                dns1 = cmd_params.get('dns1', '8.8.8.8')
                dns2 = cmd_params.get('dns2', '8.8.4.4')
                
                result = self.set_static_ip(ip, adapter, address, mask, gateway, dns1, dns2, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_dhcp":
                adapter = cmd_params.get('adapter', 'LAN')
                result = self.set_dhcp(ip, adapter, port)
                return True, json.dumps({"success": True, "result": result})

            # ========== Hostname and Domain Commands ==========
            # Add this at the beginning of send_command method when handling set_hostname
            elif command == "set_hostname":
                hostname = cmd_params.get('hostname', '')
                if not hostname:
                    return False, "Missing hostname"
                try:
                    # Store pending hostname for status queries
                    self._pending_hostname = hostname
                    result = self.set_hostname(ip, hostname, port)
                    if result.get("success"):
                        # Wait and then verify
                        time.sleep(2)
                        # Force a fresh status query to verify
                        status_result = self.query_status(ip, port, display_id)
                        if status_result.get("hostname") == hostname:
                            result["verified"] = True
                            result["message"] = f"Hostname successfully set to '{hostname}'"
                        else:
                            result["needs_reboot"] = True
                    return True, json.dumps(result)
                except Exception as e:
                    return False, str(e)

            elif command == "set_domain":
                domain = cmd_params.get('domain', '')
                if not domain:
                    return False, "Missing domain"
                try:
                    result = self.set_domain(ip, domain, port)
                    if result.get("success"):
                        time.sleep(1)
                    return True, json.dumps(result)
                except Exception as e:
                    return False, str(e)

            # ========== Program Commands ==========
            elif command == "program_command":
                cmd_name = cmd_params.get('command', '')
                slot = cmd_params.get('slot', 'DeviceSlot1')
                if not cmd_name:
                    return False, "Missing program command"
                result = self.send_program_command(ip, cmd_name, slot, port)
                return True, json.dumps({"success": True, "result": result})

            # ========== Reboot Commands ==========
            elif command == "reboot":
                result = self.reboot_device(ip, port)
                return result.get("success", False), result.get("message", "")

            else:
                return False, f"Unknown command: {command}"

        except Exception as e:
            logger.error(f"[CrestronSSH] Command failed: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)


# Helper function for plugin discovery
def get_plugin(config=None):
    """Factory function for plugin discovery"""
    return CrestronCP4NPlugin(config)