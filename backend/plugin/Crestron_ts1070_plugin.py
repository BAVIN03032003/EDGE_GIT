#!/usr/bin/env python3
"""
Manual Platform Plugin: Crestron TS-1070 Touch Panel Plugin
Crestron TS-1070 with WiFi management, network config, proximity sensor, and occupancy detection
"""

import re
import time
import urllib3
import requests
import subprocess
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from .base import ManualPlatformPlugin
from .crestron_firmware_mixin import CrestronFirmwareMixin

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CrestronTS1070Plugin(CrestronFirmwareMixin, ManualPlatformPlugin):
    """Crestron TS-1070 Touch Panel Plugin with full control capabilities"""

    name = "crestron_ts1070"
    display_name = "Crestron TS-1070 Touch Panel"
    description = "Crestron TS-1070 with WiFi management, network config, proximity sensor, and occupancy detection"
    supports_display_id = False
    supports_port = False
    default_port = 443
    SUPPORTED_MODELS = [
        "TS-1070",
        "TS-1070-B-S",
        "TS-1070-B-TK",
        "TS-1070-W-S",
        "TS-1070-W-TK",
        "TST-1080",
        "TSW-1070",
        "TS-1542",
        "TS-1542-C",
        "TS-1542-L",
        "TS-770",
        "TSS-1070",
        "TSS-1070-B-S",
        "TSS-1070-B-TK",
        "TSS-1070-W-S",
        "TSS-1070-W-TK",
        "TSS-770",
        "TSS-752",
        "TSS-1060",
    ]
    SUPPORTED_FIRMWARE_MODELS = {
        "TS-1070": {"extensions": [".puf"]},
        "TS-1070-B-S": {"extensions": [".puf"]},
        "TS-1070-B-TK": {"extensions": [".puf"]},
        "TS-1070-W-S": {"extensions": [".puf"]},
        "TS-1070-W-TK": {"extensions": [".puf"]},
        "TST-1080": {"extensions": [".puf"]},
        "TSW-1070": {"extensions": [".puf"]},
        "TS-1542": {"extensions": [".puf"]},
        "TS-1542-C": {"extensions": [".puf"]},
        "TS-1542-L": {"extensions": [".puf"]},
        "TS-770": {"extensions": [".puf"]},
        "TSS-1070": {"extensions": [".puf"]},
        "TSS-1070-B-S": {"extensions": [".puf"]},
        "TSS-1070-B-TK": {"extensions": [".puf"]},
        "TSS-1070-W-S": {"extensions": [".puf"]},
        "TSS-1070-W-TK": {"extensions": [".puf"]},
        "TSS-770": {"extensions": [".puf"]},
        "TSS-752": {"extensions": [".puf"]},
        "TSS-1060": {"extensions": [".puf"]},
    }

    # Command definitions for the UI
    COMMANDS = {
        # Device Operations
        "reboot": {
            "description": "Reboot the device",
            "params": [{"name": "wait_for_reboot", "type": "bool", "default": False}],
        },
        
        # Hostname & Domain
        "set_hostname": {
            "description": "Set device hostname",
            "params": [{"name": "hostname", "type": "str", "required": True}],
        },
        "set_domain": {
            "description": "Set device domain name",
            "params": [{"name": "domain", "type": "str", "required": True}],
        },
        
        # Network Configuration
        "set_static_ip": {
            "description": "Set static IP configuration",
            "params": [
                {"name": "ip_address", "type": "str", "required": True},
                {"name": "subnet_mask", "type": "str", "required": True},
                {"name": "gateway", "type": "str", "required": True},
                {"name": "dns1", "type": "str", "default": "8.8.8.8"},
                {"name": "dns2", "type": "str", "default": "8.8.4.4"},
            ],
        },
        "enable_dhcp": {
            "description": "Enable DHCP on primary LAN",
            "params": [],
        },
        
        # WiFi Management
        "scan_wifi": {
            "description": "Scan for available WiFi networks",
            "params": [],
        },
        "connect_wifi": {
            "description": "Connect to a WiFi network",
            "params": [
                {"name": "ssid", "type": "str", "required": True},
                {"name": "password", "type": "str", "required": False},
                {"name": "encryption_type", "type": "str", "default": "WPA2", "options": ["WPA2", "WPA", "WEP", "None", "Open"]},
            ],
        },
        "remove_wifi": {
            "description": "Remove a configured WiFi network",
            "params": [{"name": "ssid", "type": "str", "required": True}],
        },
        "set_preferred_wifi": {
            "description": "Set preferred WiFi network",
            "params": [{"name": "ssid", "type": "str", "required": True}],
        },
        
        # Proximity Sensor
        "get_proximity_info": {
            "description": "Get proximity sensor status",
            "params": [],
        },
        "set_wake_on_proximity": {
            "description": "Enable/disable wake on proximity",
            "params": [{"name": "enabled", "type": "bool", "required": True}],
        },
        
        # Occupancy Detection (NEW)
        "get_occupancy_status": {
            "description": "Get current room occupancy status",
            "params": [],
        },
        "monitor_occupancy": {
            "description": "Monitor room occupancy in real-time",
            "params": [{"name": "duration", "type": "int", "default": 60, "min": 10, "max": 3600}],
        },
        
        # Refresh status
        "refresh_status": {
            "description": "Refresh device status",
            "params": [],
        },
    }

    QUERY_COMMANDS = {
        "device_info": "get_device_info",
        "network_info": "get_network_info",
        "wifi_info": "get_wifi_info",
        "proximity_info": "get_proximity_info",
        "occupancy_status": "get_occupancy_status",
        "system_versions": "get_system_versions",
        "full_status": "get_full_status",
    }

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._xsrf_token = None
        self._session = None
        self._authenticated = False

    def _crestron_login(self, ip, username, password):
        """Authenticate with the Crestron TS-1070 device"""
        base_url = f"https://{ip}"
        login_url = f"{base_url}/userlogin.html"
        
        if self._session:
            self._session.close()
        
        session = requests.Session()
        session.verify = False
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        self._xsrf_token = None
        self._authenticated = False

        # Step 1: GET login page to receive TRACKID cookie
        r = session.get(login_url, timeout=8)
        r.raise_for_status()
        trackid = session.cookies.get("TRACKID")
        if not trackid:
            raise Exception("TRACKID cookie not received from device")

        # Step 2: POST credentials
        login_headers = {
            "User-Agent": "Mozilla/5.0",
            "Cookie": f"TRACKID={trackid}",
            "Origin": base_url,
            "Referer": login_url,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        payload = f"login={username}&passwd={password}"
        login_response = session.post(
            login_url,
            headers=login_headers,
            data=payload,
            timeout=10,
        )

        if login_response.status_code == 403:
            raise Exception("Invalid credentials")
        if login_response.status_code != 200:
            raise Exception(f"Login failed (HTTP {login_response.status_code})")

        # Capture XSRF token
        self._xsrf_token = login_response.headers.get("CREST-XSRF-TOKEN")
        if self._xsrf_token:
            session.headers.update({
                "CREST-XSRF-TOKEN": self._xsrf_token,
                "X-CREST-XSRF-TOKEN": self._xsrf_token,
            })

        self._session = session
        self._authenticated = True
        return session

    def _make_request(self, ip, method: str, endpoint: str, data: dict = None, timeout: int = None) -> dict:
        """Make an authenticated API request"""
        username = self.config.get("username")
        password = self.config.get("password")

        if not username or not password:
            return {"error": "Missing credentials"}

        try:
            if not self._authenticated or not self._session:
                self._crestron_login(ip, username, password)

            url = f"https://{ip}{endpoint}"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            }
            
            if self._xsrf_token:
                headers["CREST-XSRF-TOKEN"] = self._xsrf_token
                headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token

            def _do_request():
                if method == "GET":
                    return self._session.get(url, headers=headers, timeout=timeout or 10, verify=False)
                elif method == "POST":
                    return self._session.post(url, headers=headers, json=data, timeout=timeout or 30, verify=False)
                else:
                    raise Exception(f"Unsupported HTTP method: {method}")

            response = _do_request()

            if response.status_code in (401, 403):
                self._crestron_login(ip, username, password)
                response = _do_request()

            if response.status_code not in (200, 202, 204):
                return {
                    "error": f"HTTP {response.status_code}",
                    "message": response.text[:300],
                }

            if not response.content or not response.content.strip():
                return {"success": True}
            
            try:
                return response.json()
            except ValueError:
                return {"success": True, "_raw": response.text.strip()}

        except requests.exceptions.ConnectTimeout:
            return {"error": "Connection timeout — check device IP and network"}
        except requests.exceptions.ConnectionError:
            return {"error": "Connection refused — check device IP and network"}
        except requests.exceptions.Timeout:
            return {"error": "Request timed out"}
        except Exception as e:
            return {"error": str(e)}

    def _unwrap(self, data, *keys):
        """Unwrap nested dictionary data"""
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
                if result is None:
                    return None
            else:
                return None
        return result

    # ========== DEVICE INFO METHODS ==========

    def get_device_info(self, ip, port=443, display_id=None) -> dict:
        """Get device information"""
        username = self.config.get("username")
        password = self.config.get("password")

        if not username or not password:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "TS-1070 Touch Panel",
                "current_status": "Offline",
                "error": "Missing credentials: username and password are required."
            }

        try:
            result = self._make_request(ip, "GET", "/Device/DeviceInfo/")
            device_info = self._unwrap(result, "Device", "DeviceInfo") or {}
            model = device_info.get("Model", "TS-1070")
            device_type = "Room Scheduling Panel" if model.upper().startswith("TSS-") else "Touch Panel"
            
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_name": device_info.get("Name", model),
                "model": model,
                "model_id": device_info.get("ModelId", ""),
                "serial_number": device_info.get("SerialNumber", "Unknown"),
                "mac_address": device_info.get("MacAddress", "Unknown"),
                "firmware": device_info.get("DeviceVersion", "Unknown"),
                "build_date": device_info.get("BuildDate", ""),
                "device_id": device_info.get("DeviceId", ""),
                "device_type": device_type,
                "category": device_info.get("Category", "Touch Panel"),
                "reboot_reason": device_info.get("RebootReason", "Unknown"),
                "version": device_info.get("Version", ""),
                "current_status": "Online",
            }
        except Exception as e:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "TS-1070 Touch Panel",
                "current_status": "Offline",
                "error": str(e),
            }

    def get_system_versions(self, ip, port=443, display_id=None) -> dict:
        """Get system versions/components"""
        try:
            result = self._make_request(ip, "GET", "/Device/SystemVersions/")
            versions = self._unwrap(result, "Device", "SystemVersions") or {}
            return versions
        except Exception as e:
            return {"error": str(e)}

    def get_network_info(self, ip, port=443, display_id=None) -> dict:
        """Get network configuration"""
        try:
            result = self._make_request(ip, "GET", "/Device/Ethernet/")
            eth = self._unwrap(result, "Device", "Ethernet") or {}
            
            network_info = {
                "hostname": eth.get("HostName", ""),
                "domain_name": eth.get("DomainName", ""),
                "icmp_enabled": eth.get("IsIcmpPingEnabled", False),
                "adapters": []
            }
            
            for adapter in eth.get("Adapters", []):
                ipv4 = adapter.get("IPv4", {})
                addresses = ipv4.get("Addresses", [])
                network_info["adapters"].append({
                    "name": adapter.get("Name", "Unknown"),
                    "type": adapter.get("Type", "Unknown"),
                    "dhcp_enabled": ipv4.get("IsDhcpEnabled", True),
                    "ip_address": addresses[0].get("Address", "") if addresses else "",
                    "subnet_mask": addresses[0].get("SubnetMask", "") if addresses else "",
                    "default_gateway": ipv4.get("DefaultGateway", ""),
                    "dns_servers": ipv4.get("DnsServers", []),
                })
            
            return network_info
        except Exception as e:
            return {"error": str(e)}

    def get_wifi_info(self, ip, port=443, display_id=None) -> dict:
        """Get WiFi configuration and status"""
        try:
            result = self._make_request(ip, "GET", "/Device/WiFi/")
            wifi = self._unwrap(result, "Device", "WiFi") or {}
            
            # Parse configured access points
            access_points = {}
            for ssid, details in wifi.get("AccessPoints", {}).items():
                if details:
                    access_points[ssid] = {
                        "encryption_type": details.get("EncryptionType", "Unknown"),
                    }
            
            return {
                "is_enabled": wifi.get("IsEnabled", False),
                "active_access_point": wifi.get("ActiveAccessPoint", ""),
                "active_details": {
                    "signal_strength": wifi.get("ActiveAccessPointDetails", {}).get("SignalStrength", 0),
                    "channel": wifi.get("ActiveAccessPointDetails", {}).get("Channel", 0),
                    "frequency_band": wifi.get("ActiveAccessPointDetails", {}).get("FrequencyBand", ""),
                },
                "access_points": access_points,
                "configured_count": len(access_points),
                "max_access_points": 4,
            }
        except Exception as e:
            return {"error": str(e)}

    def scan_wifi(self, ip) -> dict:
        """Scan for available WiFi networks"""
        try:
            # Trigger scan
            scan_payload = {"Device": {"WiFi": {"ScanAccessPoints": True}}}
            self._make_request(ip, "POST", "/Device/WiFi/", data=scan_payload)
            
            # Wait for scan to complete
            time.sleep(5)
            
            # Get scan results
            result = self._make_request(ip, "GET", "/Device/WiFi/")
            wifi = self._unwrap(result, "Device", "WiFi") or {}
            discovered = wifi.get("DiscoveredAccessPoints", {})
            
            # Format discovered networks
            access_points = {}
            for ssid, details in discovered.items():
                if ssid and ssid.strip():
                    access_points[ssid] = {
                        "EncryptionType": details.get("EncryptionType", "Unknown"),
                        "SignalStrength": details.get("SignalStrength", 0),
                        "Channel": details.get("Channel", 0),
                        "FrequencyBand": details.get("FrequencyBand", ""),
                    }
            
            return {
                "success": True,
                "access_points": access_points,
                "count": len(access_points),
            }
        except Exception as e:
            return {"success": False, "message": str(e), "access_points": {}}

    def connect_wifi(self, ip, ssid: str, password: str = "", encryption_type: str = "WPA2") -> dict:
        """Connect to a WiFi network"""
        try:
            # Get current WiFi config to check max APs
            result = self._make_request(ip, "GET", "/Device/WiFi/")
            wifi = self._unwrap(result, "Device", "WiFi") or {}
            current_aps = wifi.get("AccessPoints", {})
            
            # Check max AP limit (max 4)
            if len(current_aps) >= 4 and ssid not in current_aps:
                return {
                    "success": False, 
                    "message": f"Maximum 4 access points can be configured. Currently have {len(current_aps)}"
                }
            
            # Map encryption type
            enc_type = encryption_type
            if encryption_type == "Open":
                enc_type = "None"
            
            # Build access point config
            ap_config = {
                "WirelessNetworkPassword": password,
                "EncryptionType": enc_type
            }
            
            # Build payload
            payload = {
                "Device": {
                    "WiFi": {
                        "AccessPoints": {
                            ssid: ap_config
                        },
                        "PreferredAccessPoint": ssid
                    }
                }
            }
            
            result = self._make_request(ip, "POST", "/Device/WiFi/", data=payload)
            
            if "error" in result:
                return {"success": False, "message": result.get("error", "Failed to connect")}
            
            # Wait for connection
            time.sleep(5)
            
            return {"success": True, "message": f"Connected to {ssid}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def remove_wifi(self, ip, ssid: str) -> dict:
        """Remove a configured WiFi network"""
        try:
            payload = {
                "Device": {
                    "WiFi": {
                        "AccessPoints": {
                            ssid: None
                        }
                    }
                }
            }
            result = self._make_request(ip, "POST", "/Device/WiFi/", data=payload)
            
            if "error" in result:
                return {"success": False, "message": result.get("error", "Failed to remove network")}
            
            return {"success": True, "message": f"Removed {ssid}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def set_preferred_wifi(self, ip, ssid: str) -> dict:
        """Set preferred WiFi network"""
        try:
            payload = {
                "Device": {
                    "WiFi": {
                        "PreferredAccessPoint": ssid
                    }
                }
            }
            result = self._make_request(ip, "POST", "/Device/WiFi/", data=payload)
            
            if "error" in result:
                return {"success": False, "message": result.get("error", "Failed to set preferred network")}
            
            return {"success": True, "message": f"'{ssid}' set as preferred"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_proximity_info(self, ip, port=443, display_id=None) -> dict:
        """Get proximity sensor information"""
        try:
            result = self._make_request(ip, "GET", "/Device/ProximitySensor/")
            proximity = self._unwrap(result, "Device", "ProximitySensor") or {}
            
            return {
                "is_wake_on_proximity_enabled": proximity.get("IsWakeOnProximityEnabled", False),
                "version": proximity.get("Version", "Unknown"),
            }
        except Exception as e:
            return {"error": str(e)}

    def set_wake_on_proximity(self, ip, enabled: bool) -> dict:
        """Set wake on proximity setting"""
        try:
            payload = {"Device": {"ProximitySensor": {"IsWakeOnProximityEnabled": enabled}}}
            result = self._make_request(ip, "POST", "/Device/ProximitySensor/", data=payload)
            
            if "error" in result:
                return {"success": False, "message": result.get("error", "Failed to set proximity")}
            
            state = "enabled" if enabled else "disabled"
            return {"success": True, "message": f"Wake on proximity {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_occupancy_status(self, ip, port=443, display_id=None) -> dict:
        """Get current room occupancy status"""
        try:
            # Try primary occupancy endpoint
            result = self._make_request(ip, "GET", "/Device/Occupancy/")
            occupancy = self._unwrap(result, "Device", "Occupancy") or {}
            
            if occupancy:
                return {
                    "is_occupied": occupancy.get("IsOccupied", False),
                    "detection_method": "ultrasonic_pir",
                    "last_motion": occupancy.get("LastMotionDetected", ""),
                    "confidence": occupancy.get("OccupancyConfidence", 0),
                    "timeout_seconds": occupancy.get("OccupancyTimeout", 300),
                }
        except:
            pass
        
        # Fallback to proximity sensor
        try:
            proximity = self.get_proximity_info(ip, port, display_id)
            wake_enabled = proximity.get("is_wake_on_proximity_enabled", False)
            return {
                "is_occupied": wake_enabled,
                "detection_method": "proximity",
                "last_motion": datetime.now().isoformat() if wake_enabled else None,
                "confidence": 50,
                "timeout_seconds": 60,
            }
        except:
            return {
                "is_occupied": None,
                "detection_method": "unknown",
                "error": "Unable to determine occupancy"
            }

    def monitor_occupancy(self, ip, duration: int = 60) -> dict:
        """Monitor room occupancy for specified duration (seconds)"""
        results = {
            "samples": [],
            "occupied_count": 0,
            "total_samples": 0,
            "occupancy_percentage": 0,
            "state_changes": 0,
            "monitoring_duration": duration,
        }
        
        last_state = None
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                status = self.get_occupancy_status(ip)
                is_occupied = status.get("is_occupied", False)
                
                results["samples"].append({
                    "timestamp": datetime.now().isoformat(),
                    "occupied": is_occupied
                })
                
                if is_occupied:
                    results["occupied_count"] += 1
                
                if last_state is not None and last_state != is_occupied:
                    results["state_changes"] += 1
                
                last_state = is_occupied
                results["total_samples"] += 1
                
                time.sleep(2)  # Sample every 2 seconds
            
            if results["total_samples"] > 0:
                results["occupancy_percentage"] = (results["occupied_count"] / results["total_samples"]) * 100
            
            return results
        except Exception as e:
            return {"error": str(e), "results": results}

    def set_hostname(self, ip, hostname: str) -> dict:
        """Set device hostname"""
        if not re.match(r'^[A-Z0-9]([A-Z0-9-]*[A-Z0-9])?$', hostname.upper()):
            return {"success": False, "message": "Invalid hostname format. Use A-Z, 0-9, hyphens only."}
        if len(hostname) > 63:
            return {"success": False, "message": "Hostname too long. Max 63 characters"}
        
        hostname_upper = hostname.upper()
        payload_eth = {"Device": {"Ethernet": {"HostName": hostname_upper}}}
        payload_net = {"Device": {"NetworkAdapters": {"HostName": hostname_upper}}}
        
        try:
            self._make_request(ip, "POST", "/Device/Ethernet/", data=payload_eth)
            self._make_request(ip, "POST", "/Device/NetworkAdapters/", data=payload_net)
            return {"success": True, "message": f"Hostname set to '{hostname_upper}'"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def set_domain(self, ip, domain: str) -> dict:
        """Set device domain"""
        if domain and len(domain) > 127:
            return {"success": False, "message": "Domain too long. Max 127 characters"}
        
        domain_upper = domain.upper() if domain else ""
        payload = {"Device": {"Ethernet": {"DomainName": domain_upper}}}
        
        try:
            self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
            return {"success": True, "message": f"Domain set to '{domain_upper}'"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def set_static_ip(self, ip, ip_address: str, subnet_mask: str, gateway: str, 
                      dns1: str = "8.8.8.8", dns2: str = "8.8.4.4") -> dict:
        """Set static IP configuration"""
        payload = {
            "Device": {
                "Ethernet": {
                    "Adapters": [{
                        "Name": "FEC1",
                        "IPv4": {
                            "IsDhcpEnabled": False,
                            "StaticAddresses": [{"Address": ip_address, "SubnetMask": subnet_mask}],
                            "StaticDefaultGateway": gateway,
                            "StaticDns": [dns1, dns2]
                        }
                    }]
                }
            }
        }
        try:
            self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
            return {"success": True, "message": f"Static IP {ip_address} configured"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def enable_dhcp(self, ip) -> dict:
        """Enable DHCP"""
        payload = {
            "Device": {
                "Ethernet": {
                    "Adapters": [{
                        "Name": "FEC1",
                        "IPv4": {"IsDhcpEnabled": True}
                    }]
                }
            }
        }
        try:
            self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
            return {"success": True, "message": "DHCP enabled"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def reboot_device(self, ip, wait_for_reboot=False) -> dict:
        """Reboot via SSH"""
        username = self.config.get("username", "admin")
        password = self.config.get("password", "")
        
        if not PARAMIKO_AVAILABLE:
            return {"success": False, "message": "SSH not available. Install paramiko: pip install paramiko"}
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                ip,
                username=username,
                password=password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )
            
            ssh.exec_command("reboot")
            ssh.close()
            
            if wait_for_reboot:
                time.sleep(60)
            
            return {"success": True, "message": "Reboot command sent successfully"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_full_status(self, ip, port=443, display_id=None) -> dict:
        """Get complete device status"""
        device_info = self.get_device_info(ip, port, display_id)
        is_scheduler = device_info.get("model", "").upper().startswith("TSS-")
        
        status = {
            "device_info": device_info,
            "network_info": self.get_network_info(ip, port, display_id),
            "wifi_info": self.get_wifi_info(ip, port, display_id),
            "proximity_info": self.get_proximity_info(ip, port, display_id),
            "occupancy_status": self.get_occupancy_status(ip, port, display_id),
            "is_scheduler": is_scheduler,
            "timestamp": time.time(),
        }
        
        return status

    # ========== COMMAND HANDLER ==========

    def send_command(self, ip, port, display_id, command, params=None):
        """Execute a command on the device"""
        username = self.config.get("username")
        password = self.config.get("password")

        if not username or not password:
            return False, "Missing credentials: username and password are required."

        params = params or {}

        try:
            # Device Operations
            if command == "reboot":
                wait = params.get("wait_for_reboot", False)
                result = self.reboot_device(ip, wait)
                return result["success"], result["message"]

            # Refresh Status
            elif command == "refresh_status":
                result = self.get_full_status(ip, port, display_id)
                if "error" in result:
                    return False, result.get("error", "Failed to refresh status")
                return True, json.dumps(result)

            # Hostname & Domain
            elif command == "set_hostname":
                hostname = params.get("hostname", "")
                if not hostname:
                    return False, "Hostname is required"
                result = self.set_hostname(ip, hostname)
                return result["success"], result["message"]

            elif command == "set_domain":
                domain = params.get("domain", "")
                if not domain:
                    return False, "Domain is required"
                result = self.set_domain(ip, domain)
                return result["success"], result["message"]

            # Network Configuration
            elif command == "set_static_ip":
                ip_address = params.get("ip_address", "")
                subnet_mask = params.get("subnet_mask", "")
                gateway = params.get("gateway", "")
                dns1 = params.get("dns1", "8.8.8.8")
                dns2 = params.get("dns2", "8.8.4.4")
                
                if not ip_address or not subnet_mask or not gateway:
                    return False, "IP address, subnet mask, and gateway are required"
                
                result = self.set_static_ip(ip, ip_address, subnet_mask, gateway, dns1, dns2)
                return result["success"], result["message"]

            elif command == "enable_dhcp":
                result = self.enable_dhcp(ip)
                return result["success"], result["message"]

            # WiFi Management
            elif command == "scan_wifi":
                result = self.scan_wifi(ip)
                if result.get("success"):
                    return True, json.dumps({
                        "success": True,
                        "access_points": result.get("access_points", {}),
                        "count": result.get("count", 0)
                    })
                return False, result.get("message", "Scan failed")

            elif command == "connect_wifi":
                ssid = params.get("ssid", "")
                password = params.get("password", "")
                encryption_type = params.get("encryption_type", "WPA2")
                
                if not ssid:
                    return False, "SSID is required"
                
                result = self.connect_wifi(ip, ssid, password, encryption_type)
                return result["success"], result["message"]

            elif command == "remove_wifi":
                ssid = params.get("ssid", "")
                if not ssid:
                    return False, "SSID is required"
                result = self.remove_wifi(ip, ssid)
                return result["success"], result["message"]

            elif command == "set_preferred_wifi":
                ssid = params.get("ssid", "")
                if not ssid:
                    return False, "SSID is required"
                result = self.set_preferred_wifi(ip, ssid)
                return result["success"], result["message"]

            # Proximity Sensor
            elif command == "get_proximity_info":
                result = self.get_proximity_info(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "set_wake_on_proximity":
                enabled = params.get("enabled", False)
                result = self.set_wake_on_proximity(ip, enabled)
                return result["success"], result["message"]

            # Occupancy Detection
            elif command == "get_occupancy_status":
                result = self.get_occupancy_status(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "monitor_occupancy":
                duration = params.get("duration", 60)
                result = self.monitor_occupancy(ip, duration)
                if "error" in result:
                    return False, result["error"]
                return True, json.dumps(result)

            else:
                return False, f"Unknown command: {command}"

        except Exception as e:
            return False, str(e)

    # ========== QUERY METHODS ==========

    def query_status(self, ip, port=443, display_id=None):
        """Query device status for polling"""
        status = self.get_full_status(ip, port, display_id)
        
        network_info = status.get("network_info", {})
        adapters = network_info.get("adapters", [])
        eth = next((a for a in adapters if a.get("type") == "EthernetLan"), {})
        wifi_info = status.get("wifi_info", {})
        proximity_info = status.get("proximity_info", {})
        occupancy_status = status.get("occupancy_status", {})
        
        return {
            "reachable": status.get("device_info", {}).get("current_status") == "Online",
            "device_info": status.get("device_info"),
            "network_info": network_info,
            "wifi_info": wifi_info,
            "proximity_info": proximity_info,
            "occupancy_status": occupancy_status,
            "is_scheduler": status.get("is_scheduler", False),
            "current_ip": eth.get("ip_address", ""),
            "subnet_mask": eth.get("subnet_mask", ""),
            "gateway": eth.get("default_gateway", ""),
            "is_dhcp": eth.get("dhcp_enabled", True),
            "hostname": network_info.get("hostname", ""),
            "domain": network_info.get("domain_name", ""),
            "wifi_enabled": wifi_info.get("is_enabled", False),
            "active_wifi": wifi_info.get("active_access_point", ""),
            "wifi_signal": wifi_info.get("active_details", {}).get("signal_strength", 0),
            "wake_on_proximity": proximity_info.get("is_wake_on_proximity_enabled", False),
            "is_room_occupied": occupancy_status.get("is_occupied", False),
            "occupancy_confidence": occupancy_status.get("confidence", 0),
            "last_motion": occupancy_status.get("last_motion", ""),
            "configured_wifi_count": wifi_info.get("configured_count", 0),
            "max_wifi_networks": 4,
        }


# Helper function to check if SSH is available
def is_ssh_available():
    """Check if SSH reboot support is available"""
    return PARAMIKO_AVAILABLE