"""
Crestron_ts1070_plugin.py - Crestron TS-1070 Touch Panel Plugin for Edge Collector
"""

import json
import time
import re
import requests
import logging
from requests.auth import HTTPDigestAuth

from .base import ManualPlatformPlugin

logger = logging.getLogger(__name__)

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class CrestronTS1070Plugin(ManualPlatformPlugin):
    """Crestron TS-1070 Touch Panel Plugin for Edge Collector."""

    name = "crestron_ts1070"
    display_name = "Crestron TS-1070 Touch Panel"
    description = "Crestron TS-1070 Touch Panel Manager"
    supports_display_id = False
    supports_port = False
    default_port = 443
    SUPPORTED_MODELS = [
        "TS-1070", "TS-1070-B-S", "TS-1070-B-TK", "TS-1070-W-S", "TS-1070-W-TK",
        "TST-1080", "TSW-1070", "TS-1542", "TS-1542-C", "TS-1542-L", "TS-770",
        "TSS-1070", "TSS-1070-B-S", "TSS-1070-B-TK", "TSS-1070-W-S", "TSS-1070-W-TK",
        "TSS-770", "TSS-752", "TSS-1060",
    ]

    def __init__(self, config=None):
        super().__init__(config)
        self.username = self.config.get("username") if self.config else None
        self.password = self.config.get("password") if self.config else None
        self.session = None
        self._xsrf_token = None
        logger.info(f"[CrestronTS1070] Initialized")

    def _login(self, ip):
        """Login and return session with proper XSRF token handling"""
        if not self.username or not self.password:
            raise Exception("Missing credentials")
            
        base_url = f"https://{ip}"
        login_url = f"{base_url}/userlogin.html"
        session = requests.Session()
        session.verify = False
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        r = session.get(login_url, timeout=8)
        r.raise_for_status()
        trackid = session.cookies.get("TRACKID")
        if not trackid:
            raise Exception("TRACKID cookie not found on login page.")

        r2 = session.post(
            login_url,
            headers={
                "Cookie": f"TRACKID={trackid}",
                "Origin": base_url,
                "Referer": login_url,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"login": self.username, "passwd": self.password},
            timeout=10,
        )

        if r2.status_code == 403:
            raise Exception("Invalid credentials (403).")
        if r2.status_code != 200:
            raise Exception(f"Login failed (HTTP {r2.status_code})")

        xsrf = r2.headers.get("CREST-XSRF-TOKEN")
        if xsrf:
            session.headers.update({
                "CREST-XSRF-TOKEN": xsrf,
                "X-CREST-XSRF-TOKEN": xsrf,
            })
            self._xsrf_token = xsrf

        logger.info(f"[CrestronTS1070] Login successful for {ip}")
        return session

    def _get(self, session, ip, path):
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
        url = f"https://{ip}{path}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._xsrf_token:
            headers["CREST-XSRF-TOKEN"] = self._xsrf_token
            headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token
        
        r = session.post(url, json=payload, headers=headers, timeout=15)
        
        if r.status_code == 403:
            logger.warning("[CrestronTS1070] Session expired, re-authenticating...")
            session = self._login(ip)
            if self._xsrf_token:
                headers["CREST-XSRF-TOKEN"] = self._xsrf_token
                headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token
            r = session.post(url, json=payload, headers=headers, timeout=15)
        
        r.raise_for_status()
        try:
            return r.json()
        except:
            return {"status": r.status_code}

    @staticmethod
    def _clean_network_value(value):
        if value is None:
            return None
        value = str(value).strip()
        if not value or value in {"-", "—", "â€”"}:
            return None
        return value

    # ========== DEVICE INFO ==========
    
    def get_device_info(self, ip, port=443, display_id=None):
        """Get device information"""
        if not self.username or not self.password:
            return {
                "ip_address": ip,
                "make": "Crestron",
                "device_type": "Crestron TS-1070",
                "current_status": "Offline",
                "error": "Missing credentials",
            }

        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/DeviceInfo")
            di = (data.get("Device") or {}).get("DeviceInfo") or data.get("DeviceInfo") or {}
            
            return {
                "ip_address": ip,
                "make": "Crestron",
                "device_name": di.get("Name") or di.get("Model") or "TS-1070",
                "model": di.get("Model"),
                "serial_number": di.get("SerialNumber"),
                "mac_address": di.get("MacAddress"),
                "firmware": di.get("DeviceVersion"),
                "build_date": di.get("BuildDate"),
                "device_type": "Crestron TS-1070",
                "current_status": "Online",
            }
        except Exception as e:
            logger.error(f"[CrestronTS1070] get_device_info failed: {e}")
            return {
                "ip_address": ip,
                "make": "Crestron",
                "device_type": "Crestron TS-1070",
                "current_status": "Offline",
                "error": str(e),
            }
        finally:
            if session:
                session.close()

    # ========== ETHERNET INFO ==========
    
    def get_ethernet_info(self, ip, port=443):
        """Get Ethernet/IP settings"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/Ethernet")
            
            if not isinstance(data, dict):
                return {"current_ip": ip}
                
        except Exception as e:
            logger.warning(f"[CrestronTS1070] get_ethernet_info failed: {e}")
            return {"current_ip": ip}
        finally:
            if session:
                session.close()

        eth_root = (data.get("Device") or {}).get("Ethernet", {})
        hostname = eth_root.get("HostName", "")
        domain = eth_root.get("DomainName", "")
        
        adapters = eth_root.get("Adapters", [])
        lan_ip = ip
        lan_subnet = ""
        lan_gateway = ""
        lan_mac = ""
        
        for adapter in adapters:
            if adapter.get("Type") == "EthernetLan":
                ipv4 = adapter.get("IPv4", {})
                addresses = ipv4.get("Addresses", [])
                if addresses and addresses[0].get("Address"):
                    lan_ip = addresses[0].get("Address")
                    lan_subnet = addresses[0].get("SubnetMask", "")
                lan_gateway = ipv4.get("DefaultGateway", "")
                lan_mac = adapter.get("MacAddress", "")
                break
        
        return {
            "hostname": self._clean_network_value(hostname),
            "domain": self._clean_network_value(domain),
            "current_ip": lan_ip,
            "subnet_mask": lan_subnet,
            "gateway": lan_gateway,
            "mac_address": lan_mac,
        }

    # ========== WIFI INFO ==========
    
    def get_wifi_info(self, ip, port=443):
        """Get WiFi information including discovered access points"""
        session = None
        try:
            session = self._login(ip)
            
            # Try multiple endpoints
            endpoints = ["/Device/WiFi", "/Device/NetworkAdapters"]
            wifi_data = {}
            
            for endpoint in endpoints:
                try:
                    data = self._get(session, ip, endpoint)
                    if isinstance(data, dict):
                        if "WiFi" in data.get("Device", {}):
                            wifi_data = data["Device"]["WiFi"]
                        elif "NetworkAdapters" in data.get("Device", {}):
                            adapters = data["Device"]["NetworkAdapters"].get("Adapters", {})
                            wifi_data = adapters.get("Wifi", {})
                        logger.info(f"[CrestronTS1070] Got WiFi data from {endpoint}")
                        break
                except Exception as e:
                    logger.debug(f"[CrestronTS1070] Endpoint {endpoint} failed: {e}")
                    continue
            
            if not wifi_data:
                logger.warning(f"[CrestronTS1070] No valid WiFi data found")
                return {
                    "is_enabled": False,
                    "active_access_point": "",
                    "access_points": {},
                    "discovered_aps": {},
                    "current_ip": "0.0.0.0",
                    "subnet_mask": "0.0.0.0",
                    "gateway": "0.0.0.0",
                    "dhcp_enabled": True,
                }
                    
        except Exception as e:
            logger.warning(f"[CrestronTS1070] get_wifi_info failed: {e}")
            return {"is_enabled": False, "access_points": {}, "discovered_aps": {}}
        finally:
            if session:
                session.close()

        # Get discovered access points
        discovered_aps = wifi_data.get("DiscoveredAccessPoints", {})
        if not discovered_aps:
            discovered_aps = wifi_data.get("ScanResults", {})
        
        # Get configured access points
        configured_aps = wifi_data.get("AccessPoints", {})
        
        # Format discovered access points
        discovered_list = {}
        for ssid, details in discovered_aps.items():
            if ssid and ssid.strip() and ssid not in ["", "None", "null"]:
                discovered_list[ssid] = {
                    "ssid": ssid,
                    "encryption": details.get("EncryptionType", details.get("Security", "WPA2")),
                    "signal": details.get("SignalStrength", details.get("RSSI", 0)),
                    "configured": ssid in configured_aps
                }
        
        # Format configured access points
        access_points = {}
        for ssid, details in configured_aps.items():
            if ssid and ssid.strip():
                access_points[ssid] = {
                    "ssid": ssid,
                    "encryption": details.get("EncryptionType", "WPA2"),
                    "configured": True
                }
        
        # Get IPv4 settings
        ipv4 = wifi_data.get("IPv4", {})
        addresses = ipv4.get("Addresses", [])
        current_ip = addresses[0].get("Address", "0.0.0.0") if addresses else "0.0.0.0"
        subnet = addresses[0].get("SubnetMask", "0.0.0.0") if addresses else "0.0.0.0"
        gateway = ipv4.get("DefaultGateway", "0.0.0.0")
        dhcp_enabled = ipv4.get("IsDhcpEnabled", True)
        
        return {
            "is_enabled": wifi_data.get("IsEnabled", False),
            "active_access_point": wifi_data.get("ActiveAccessPoint", ""),
            "access_points": access_points,
            "discovered_aps": discovered_list,
            "preferred_access_point": wifi_data.get("PreferredAccessPoint", ""),
            "current_ip": current_ip,
            "subnet_mask": subnet,
            "gateway": gateway,
            "dhcp_enabled": dhcp_enabled,
        }

    def scan_wifi(self, ip, port=443):
        """Trigger WiFi scan and return discovered access points"""
        session = None
        try:
            session = self._login(ip)
            
            # Try to trigger scan
            scan_payloads = [
                {"Device": {"WiFi": {"ScanAccessPoints": True}}},
                {"WiFi": {"ScanAccessPoints": True}},
            ]
            
            scan_success = False
            for scan_payload in scan_payloads:
                try:
                    result = self._post(session, ip, "/Device/WiFi", scan_payload)
                    if "error" not in result:
                        scan_success = True
                        logger.info("[CrestronTS1070] Scan triggered successfully")
                        break
                except Exception as e:
                    logger.debug(f"[CrestronTS1070] Scan attempt failed: {e}")
                    continue
            
            if not scan_success:
                logger.warning("[CrestronTS1070] Could not trigger WiFi scan")
                return {"success": True, "access_points": [], "count": 0}
            
            # Wait for scan to complete
            logger.info("[CrestronTS1070] Waiting for WiFi scan to complete...")
            time.sleep(8)
            
            # Get scan results
            wifi_info = self.get_wifi_info(ip, port)
            discovered = wifi_info.get("discovered_aps", {})
            
            # Format for frontend
            ap_list = []
            for ssid, details in discovered.items():
                ap_list.append({
                    "ssid": ssid,
                    "encryption": details.get("encryption", "WPA2"),
                    "signal": details.get("signal", 0),
                    "configured": details.get("configured", False)
                })
            
            # Sort by signal strength (strongest first)
            ap_list.sort(key=lambda x: x.get("signal", 0), reverse=True)
            
            logger.info(f"[CrestronTS1070] WiFi scan completed, found {len(ap_list)} networks")
            
            return {
                "success": True,
                "access_points": ap_list,
                "count": len(ap_list),
            }
            
        except Exception as e:
            logger.error(f"[CrestronTS1070] scan_wifi failed: {e}")
            return {"success": False, "error": str(e), "access_points": []}
        finally:
            if session:
                session.close()

    def connect_to_wifi(self, ip, ssid, password, encryption_type="WPA2", port=443):
        """Connect to a WiFi network"""
        session = None
        try:
            session = self._login(ip)
            
            # Build payload for adding access point
            payload = {
                "Device": {
                    "WiFi": {
                        "AccessPoints": {
                            ssid: {
                                "WirelessNetworkPassword": password,
                                "EncryptionType": encryption_type
                            }
                        },
                        "PreferredAccessPoint": ssid
                    }
                }
            }
            
            result = self._post(session, ip, "/Device/WiFi", payload)
            
            if "error" not in result:
                time.sleep(3)
                return {"success": True, "message": f"Connected to {ssid}", "ssid": ssid}
            return {"success": False, "error": str(result)}
            
        except Exception as e:
            logger.error(f"[CrestronTS1070] connect_to_wifi failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if session:
                session.close()

    def set_wifi_dhcp(self, ip, enabled, port=443):
        """Enable/Disable DHCP on WiFi adapter"""
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "NetworkAdapters": {
                        "Adapters": {
                            "Wifi": {
                                "IPv4": {
                                    "IsDhcpEnabled": enabled
                                }
                            }
                        }
                    }
                }
            }
            return self._post(session, ip, "/Device/NetworkAdapters", payload)
        finally:
            if session:
                session.close()

    def set_wifi_static_ip(self, ip, ip_address, subnet_mask, gateway, port=443):
        """Set static IP on WiFi adapter"""
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "NetworkAdapters": {
                        "Adapters": {
                            "Wifi": {
                                "IPv4": {
                                    "IsDhcpEnabled": False,
                                    "StaticAddresses": [
                                        {
                                            "Address": ip_address,
                                            "SubnetMask": subnet_mask
                                        }
                                    ],
                                    "StaticDefaultGateway": gateway
                                }
                            }
                        }
                    }
                }
            }
            return self._post(session, ip, "/Device/NetworkAdapters", payload)
        finally:
            if session:
                session.close()

    # ========== PROXIMITY ==========
    
    def get_proximity_info(self, ip, port=443):
        """Get proximity sensor information"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/ProximitySensor")
            
            if not isinstance(data, dict):
                return {"is_wake_on_proximity_enabled": False}
                
        except Exception as e:
            logger.warning(f"[CrestronTS1070] get_proximity_info failed: {e}")
            return {"is_wake_on_proximity_enabled": False}
        finally:
            if session:
                session.close()

        proximity = (data.get("Device") or {}).get("ProximitySensor", {})
        
        return {
            "is_wake_on_proximity_enabled": proximity.get("IsWakeOnProximityEnabled", False),
        }

    def set_wake_on_proximity(self, ip, enabled, port=443):
        """Enable/disable wake on proximity"""
        session = None
        try:
            session = self._login(ip)
            
            payload = {
                "Device": {
                    "ProximitySensor": {
                        "IsWakeOnProximityEnabled": enabled
                    }
                }
            }
            
            logger.info(f"[CrestronTS1070] Setting wake on proximity to: {enabled}")
            result = self._post(session, ip, "/Device/ProximitySensor", payload)
            
            time.sleep(1)
            verify_data = self._get(session, ip, "/Device/ProximitySensor")
            verify_proximity = (verify_data.get("Device") or {}).get("ProximitySensor", {})
            current_state = verify_proximity.get("IsWakeOnProximityEnabled", False)
            
            if current_state == enabled:
                return {"success": True, "message": f"Wake on proximity {'enabled' if enabled else 'disabled'} successfully"}
            else:
                return {"success": True, "message": f"Wake on proximity {'enabled' if enabled else 'disabled'} (may need reboot)"}
                
        except Exception as e:
            logger.error(f"[CrestronTS1070] set_wake_on_proximity failed: {e}")
            return {"success": False, "message": str(e)}
        finally:
            if session:
                session.close()

    # ========== NETWORK CONFIGURATION ==========
    
    def enable_dhcp(self, ip, port=443):
        """Enable DHCP on primary LAN"""
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "Ethernet": {
                        "Adapters": [
                            {
                                "Name": "FEC1",
                                "IPv4": {"IsDhcpEnabled": True}
                            }
                        ]
                    }
                }
            }
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                session.close()

    def set_static_ip(self, ip, ip_address, subnet_mask, gateway, dns1="8.8.8.8", dns2="8.8.4.4", port=443):
        """Set static IP configuration"""
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "Ethernet": {
                        "Adapters": [
                            {
                                "Name": "FEC1",
                                "IPv4": {
                                    "IsDhcpEnabled": False,
                                    "StaticAddresses": [{"Address": ip_address, "SubnetMask": subnet_mask}],
                                    "StaticDefaultGateway": gateway,
                                    "StaticDns": [dns1, dns2],
                                }
                            }
                        ]
                    }
                }
            }
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                session.close()

    def set_hostname(self, ip, hostname, port=443):
        """Set device hostname"""
        try:
            if not re.match(r'^[A-Z0-9]([A-Z0-9-]*[A-Z0-9])?$', hostname.upper()):
                raise Exception("Invalid hostname format")
            
            hostname_upper = hostname.upper()
            
            session = None
            try:
                session = self._login(ip)
                payload = {"Device": {"Ethernet": {"HostName": hostname_upper}}}
                self._post(session, ip, "/Device/Ethernet", payload)
                time.sleep(1)
                return {"success": True, "message": f"Hostname set to '{hostname_upper}'"}
            finally:
                if session:
                    session.close()
        except Exception as e:
            logger.error(f"[CrestronTS1070] set_hostname failed: {e}")
            raise

    def set_domain(self, ip, domain, port=443):
        """Set device domain name"""
        try:
            session = None
            try:
                session = self._login(ip)
                payload = {"Device": {"Ethernet": {"DomainName": domain}}}
                self._post(session, ip, "/Device/Ethernet", payload)
                return {"success": True, "message": f"Domain set to '{domain}'"}
            finally:
                if session:
                    session.close()
        except Exception as e:
            logger.error(f"[CrestronTS1070] set_domain failed: {e}")
            raise

    # ========== REBOOT ==========
    
    def reboot_via_ssh(self, ip):
        """Reboot via SSH"""
        if not PARAMIKO_AVAILABLE:
            return {"success": False, "message": "Paramiko not installed"}
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=self.username, password=self.password, timeout=10)
            ssh.exec_command("reboot")
            ssh.close()
            return {"success": True, "message": "SSH reboot command sent"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def reboot_device(self, ip, port=443):
        return self.reboot_via_ssh(ip)

    # ========== QUERY STATUS ==========
    
    def query_status(self, ip, port=443, display_id=None):
        """Quick status query - returns full device data for frontend"""
        try:
            logger.info(f"[CrestronTS1070] query_status called for {ip}")
            
            device_info = self.get_device_info(ip, port, display_id)
            eth_info = self.get_ethernet_info(ip, port)
            wifi_info = self.get_wifi_info(ip, port)
            proximity_info = self.get_proximity_info(ip, port)
            
            result = {
                "reachable": device_info.get("current_status") == "Online",
                "power": "ON",
                "device_name": device_info.get("device_name"),
                "model": device_info.get("model"),
                "serial_number": device_info.get("serial_number"),
                "firmware": device_info.get("firmware"),
                "current_ip": eth_info.get("current_ip", ip),
                "mac_address": device_info.get("mac_address"),
                "hostname": eth_info.get("hostname", ""),
                "domain": eth_info.get("domain", ""),
                "subnet_mask": eth_info.get("subnet_mask", ""),
                "gateway": eth_info.get("gateway", ""),
                "wifi": {
                    "is_enabled": wifi_info.get("is_enabled", False),
                    "active_access_point": wifi_info.get("active_access_point", ""),
                    "access_points": wifi_info.get("access_points", {}),
                    "discovered_aps": wifi_info.get("discovered_aps", {}),
                    "preferred_ap": wifi_info.get("preferred_access_point", ""),
                    "current_ip": wifi_info.get("current_ip", "0.0.0.0"),
                    "subnet_mask": wifi_info.get("subnet_mask", "0.0.0.0"),
                    "gateway": wifi_info.get("gateway", "0.0.0.0"),
                    "dhcp_enabled": wifi_info.get("dhcp_enabled", True),
                },
                "proximity": {
                    "wake_on_proximity_enabled": proximity_info.get("is_wake_on_proximity_enabled", False),
                },
                "device_info": {
                    "Model": device_info.get("model"),
                    "Name": device_info.get("device_name"),
                    "SerialNumber": device_info.get("serial_number"),
                    "MacAddress": device_info.get("mac_address"),
                    "DeviceVersion": device_info.get("firmware"),
                    "BuildDate": device_info.get("build_date"),
                    "Manufacturer": "Crestron",
                },
                "ethernet_info": eth_info,
            }
            
            return result
            
        except Exception as e:
            logger.error(f"[CrestronTS1070] query_status failed: {e}")
            return {
                "reachable": False,
                "error": str(e),
                "device_info": {},
                "ethernet_info": {"current_ip": ip},
                "wifi": {},
                "proximity": {"wake_on_proximity_enabled": False},
            }

    # ========== SEND COMMAND ==========
    
    def send_command(self, ip, port, display_id, command, params=None):
        """Handle all TS-1070 commands."""
        if not self.username or not self.password:
            return False, "Missing credentials"

        logger.info(f"[CrestronTS1070] Command: {command} to {ip}, params: {params}")
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

            elif command == "get_proximity_info":
                result = self.get_proximity_info(ip, port)
                return True, json.dumps(result)

            elif command == "get_wifi_info":
                result = self.get_wifi_info(ip, port)
                return True, json.dumps(result)

            # ========== WiFi Commands ==========
            elif command == "scan_wifi":
                result = self.scan_wifi(ip, port)
                return True, json.dumps(result)

            elif command == "connect_wifi":
                ssid = cmd_params.get('ssid', '')
                password = cmd_params.get('password', '')
                encryption = cmd_params.get('encryption_type', 'WPA2')
                if not ssid:
                    return False, "Missing SSID"
                result = self.connect_to_wifi(ip, ssid, password, encryption, port)
                if result.get("success"):
                    return True, json.dumps(result)
                else:
                    return False, result.get("error", "Failed to connect to WiFi")

            elif command == "set_wifi_dhcp":
                enabled = cmd_params.get('enabled', True)
                result = self.set_wifi_dhcp(ip, enabled, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_wifi_static_ip":
                ip_address = cmd_params.get('ip_address', cmd_params.get('address', '0.0.0.0'))
                subnet_mask = cmd_params.get('mask', '255.255.255.0')
                gateway = cmd_params.get('gateway', '0.0.0.0')
                result = self.set_wifi_static_ip(ip, ip_address, subnet_mask, gateway, port)
                return True, json.dumps({"success": True, "result": result})

            # ========== Proximity Commands ==========
            elif command == "set_wake_on_proximity":
                enabled = cmd_params.get('enabled', False)
                result = self.set_wake_on_proximity(ip, enabled, port)
                if result.get("success"):
                    return True, json.dumps(result)
                else:
                    return False, result.get("message", "Failed to set wake on proximity")

            # ========== Network Commands ==========
            elif command == "set_hostname":
                hostname = cmd_params.get('hostname', '')
                if not hostname:
                    return False, "Missing hostname"
                result = self.set_hostname(ip, hostname, port)
                return True, json.dumps(result)

            elif command == "set_domain":
                domain = cmd_params.get('domain', '')
                if not domain:
                    return False, "Missing domain"
                result = self.set_domain(ip, domain, port)
                return True, json.dumps(result)

            elif command == "enable_dhcp":
                result = self.enable_dhcp(ip, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_static_ip":
                ip_address = cmd_params.get('ip_address', cmd_params.get('address', ''))
                subnet_mask = cmd_params.get('subnet_mask', cmd_params.get('mask', '255.255.254.0'))
                gateway = cmd_params.get('gateway', '')
                dns1 = cmd_params.get('dns1', '8.8.8.8')
                dns2 = cmd_params.get('dns2', '8.8.4.4')
                result = self.set_static_ip(ip, ip_address, subnet_mask, gateway, dns1, dns2, port)
                return True, json.dumps({"success": True, "result": result})

            # ========== Reboot Commands ==========
            elif command == "reboot":
                result = self.reboot_device(ip, port)
                return result.get("success", False), result.get("message", "")

            else:
                return False, f"Unknown command: {command}"

        except Exception as e:
            logger.error(f"[CrestronTS1070] Command failed: {e}")
            return False, str(e)


def get_plugin(config=None):
    return CrestronTS1070Plugin(config)