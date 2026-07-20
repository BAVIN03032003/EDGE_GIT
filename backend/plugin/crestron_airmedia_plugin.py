# # """
# # crestron_airmedia_plugin.py - Crestron AirMedia Series 3 Plugin for Edge Collector
# # """

# # import json
# # import time
# # import re
# # import requests
# # import logging
# # from typing import Optional, Dict, Any, List

# # from .base import ManualPlatformPlugin

# # logger = logging.getLogger(__name__)

# # urllib3 = None
# # try:
# #     import urllib3
# #     urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# # except ImportError:
# #     pass


# # class CrestronAirMediaPlugin(ManualPlatformPlugin):
# #     """Crestron AirMedia Series 3 Plugin for Edge Collector."""

# #     name = "crestron_airmedia"
# #     display_name = "Crestron AirMedia Series 3"
# #     description = "Crestron AirMedia Series 3 with full control capabilities"
# #     supports_display_id = False
# #     supports_port = False
# #     default_port = 443
    
# #     SUPPORTED_MODELS = [
# #         "AM-3000-WF-I",
# #         "AM-3200",
# #         "AM-3200-WF",
# #         "AM-3200-WF-I",
# #         "AirMedia Series 3",
# #         "AM-TX3-100-I",
# #     ]

# #     def __init__(self, config=None):
# #         super().__init__(config)
# #         self.username = self.config.get("username") if self.config else None
# #         self.password = self.config.get("password") if self.config else None
# #         self._xsrf_token = None
# #         self._session = None
# #         self._authenticated = False
# #         logger.info(f"[CrestronAirMedia] Initialized")

# #     def _login(self, ip):
# #         """Authenticate with the Crestron AirMedia device"""
# #         if not self.username or not self.password:
# #             raise Exception("Missing credentials")
        
# #         base_url = f"https://{ip}"
# #         login_url = f"{base_url}/userlogin.html"
        
# #         if self._session:
# #             self._session.close()
        
# #         session = requests.Session()
# #         session.verify = False
# #         session.headers.update({"User-Agent": "Mozilla/5.0"})
# #         self._xsrf_token = None
# #         self._authenticated = False

# #         # Step 1: GET login page to receive TRACKID cookie
# #         r = session.get(login_url, timeout=8)
# #         r.raise_for_status()
# #         trackid = session.cookies.get("TRACKID")
# #         if not trackid:
# #             raise Exception("TRACKID cookie not received from device")

# #         # Step 2: POST credentials
# #         login_headers = {
# #             "User-Agent": "Mozilla/5.0",
# #             "Cookie": f"TRACKID={trackid}",
# #             "Origin": base_url,
# #             "Referer": login_url,
# #             "Content-Type": "application/x-www-form-urlencoded",
# #         }

# #         payload = f"login={self.username}&&passwd={self.password}"
# #         login_response = session.post(
# #             login_url,
# #             headers=login_headers,
# #             data=payload,
# #             timeout=10,
# #         )

# #         if login_response.status_code == 403:
# #             raise Exception("Invalid credentials")
# #         if login_response.status_code != 200:
# #             raise Exception(f"Login failed (HTTP {login_response.status_code})")

# #         self._xsrf_token = login_response.headers.get("CREST-XSRF-TOKEN")
# #         if self._xsrf_token:
# #             session.headers.update({
# #                 "CREST-XSRF-TOKEN": self._xsrf_token,
# #                 "X-CREST-XSRF-TOKEN": self._xsrf_token,
# #             })

# #         self._session = session
# #         self._authenticated = True
# #         logger.info(f"[CrestronAirMedia] Login successful for {ip}")
# #         return session

# #     def _make_request(self, ip, method: str, endpoint: str, data: dict = None, timeout: int = None) -> dict:
# #         """Make an authenticated API request"""
# #         try:
# #             if not self._authenticated or not self._session:
# #                 self._login(ip)

# #             url = f"https://{ip}{endpoint}"
# #             headers = {
# #                 "User-Agent": "Mozilla/5.0",
# #                 "Accept": "application/json",
# #                 "Content-Type": "application/json",
# #             }
            
# #             if self._xsrf_token:
# #                 headers["CREST-XSRF-TOKEN"] = self._xsrf_token
# #                 headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token

# #             def _do_request():
# #                 if method == "GET":
# #                     return self._session.get(url, headers=headers, timeout=timeout or 10, verify=False)
# #                 elif method == "POST":
# #                     return self._session.post(url, headers=headers, json=data, timeout=timeout or 30, verify=False)
# #                 else:
# #                     raise Exception(f"Unsupported HTTP method: {method}")

# #             response = _do_request()

# #             if response.status_code in (401, 403):
# #                 self._login(ip)
# #                 response = _do_request()

# #             if response.status_code not in (200, 204):
# #                 return {
# #                     "error": f"HTTP {response.status_code}",
# #                     "message": response.text[:300],
# #                 }

# #             if not response.content or not response.content.strip():
# #                 return {}
# #             try:
# #                 return response.json()
# #             except ValueError:
# #                 return {"_raw": response.text.strip()}

# #         except requests.exceptions.ConnectTimeout:
# #             return {"error": "Connection timeout — check device IP and network"}
# #         except requests.exceptions.ConnectionError:
# #             return {"error": "Connection refused — check device IP and network"}
# #         except requests.exceptions.Timeout:
# #             return {"error": "Request timed out"}
# #         except Exception as e:
# #             return {"error": str(e)}

# #     def _unwrap(self, data, *keys):
# #         """Unwrap nested dictionary data"""
# #         result = data
# #         for key in keys:
# #             if isinstance(result, dict):
# #                 result = result.get(key)
# #                 if result is None:
# #                     return None
# #             else:
# #                 return None
# #         return result

# #     # ========== DEVICE INFO ==========
    
# #     def get_device_info(self, ip, port=443, display_id=None) -> dict:
# #         """Get device information"""
# #         if not self.username or not self.password:
# #             return {
# #                 "ip_address": ip,
# #                 "port": port,
# #                 "display_id": display_id,
# #                 "make": "Crestron",
# #                 "device_type": "AirMedia Series 3",
# #                 "current_status": "Offline",
# #                 "error": "Missing credentials: username and password are required."
# #             }

# #         try:
# #             result = self._make_request(ip, "GET", "/Device/DeviceInfo/")
# #             device_info = self._unwrap(result, "Device", "DeviceInfo") or {}
            
# #             return {
# #                 "ip_address": ip,
# #                 "port": port,
# #                 "display_id": display_id,
# #                 "make": device_info.get("Manufacturer", "unknown"),
# #                 "device_name": device_info.get("Name", "unknown"),
# #                 "model": device_info.get("Model", "unknown"),
# #                 "serial_number": device_info.get("SerialNumber", "Unknown"),
# #                 "mac_address": device_info.get("MacAddress", "Unknown"),
# #                 "firmware": device_info.get("DeviceVersion", "Unknown"),
# #                 "build_date": device_info.get("BuildDate", ""),
# #                 "device_id": device_info.get("DeviceId", ""),
# #                 "device_type": "Crestron AirMedia Series 3",
# #                 "category": device_info.get("Category", "unknown"),
# #                 "reboot_reason": device_info.get("RebootReason", "Unknown"),
# #                 "current_status": "Online",
# #             }
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] get_device_info failed: {e}")
# #             return {
# #                 "ip_address": ip,
# #                 "port": port,
# #                 "display_id": display_id,
# #                 "make": "Crestron",
# #                 "device_type": "AirMedia Series 3",
# #                 "current_status": "Offline",
# #                 "error": str(e),
# #             }

# #     # ========== AIRMEDIA STATUS ==========
    
# #     def get_airmedia_status(self, ip, port=443, display_id=None) -> dict:
# #         """Get AirMedia status"""
# #         try:
# #             result = self._make_request(ip, "GET", "/Device/AirMedia/")
# #             am = self._unwrap(result, "Device", "AirMedia") or {}
            
# #             return {
# #                 "is_enabled": am.get("IsEnabled", False),
# #                 "login_code_mode": am.get("LoginCodeMode", "Unknown"),
# #                 "active_login_code": am.get("ActiveLoginCode", "None"),
# #                 "show_login_code": am.get("ShowLoginCode", False),
# #                 "system_mode": am.get("SystemMode", "OptimizedForMultiplePresentations"),
# #                 "is_canvas_enabled": am.get("IsCanvasEnabled", False),
# #                 "canvas_options": am.get("CanvasOptions", "AllSources"),
# #                 "is_web_download_enabled": am.get("IsWebApplicationDownloadEnabled", False),
# #             }
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] get_airmedia_status failed: {e}")
# #             return {"error": str(e)}

# #     # ========== NETWORK CONFIGURATION ==========
    
# #     def get_network_config(self, ip, port=443, display_id=None) -> dict:
# #         """Get network configuration"""
# #         try:
# #             result = self._make_request(ip, "GET", "/Device/Ethernet/")
# #             eth = self._unwrap(result, "Device", "Ethernet") or {}
# #             comm = self._make_request(ip, "GET", "/Device/CommunicationConfigurations/")
# #             comm_data = self._unwrap(comm, "Device", "CommunicationConfigurations") or {}
            
# #             network_info = {
# #                 "hostname": eth.get("HostName", ""),
# #                 "domain_name": eth.get("DomainName", ""),
# #                 "ssh_enabled": comm_data.get("IsSshEnabled", False),
# #                 "icmp_ping_enabled": eth.get("IsIcmpPingEnabled", False),
# #                 "auto_negotiation": eth.get("AutoNegotiationEnabled", True),
# #                 "igmp_version": eth.get("IgmpVersion", "v2"),
# #                 "adapters": []
# #             }
            
# #             for adapter in eth.get("Adapters", []):
# #                 ipv4 = adapter.get("IPv4", {})
# #                 addresses = ipv4.get("Addresses", [])
                
# #                 network_info["adapters"].append({
# #                     "name": adapter.get("Name", "Unknown"),
# #                     "internal_name": adapter.get("InternalName", ""),
# #                     "mac_address": adapter.get("MacAddress", ""),
# #                     "link_status": adapter.get("LinkStatus", False),
# #                     "enabled": adapter.get("IsAdapterEnabled", True),
# #                     "dhcp_enabled": ipv4.get("IsDhcpEnabled", True),
# #                     "ip_address": addresses[0].get("Address", "") if addresses else "",
# #                     "subnet_mask": addresses[0].get("SubnetMask", "") if addresses else "",
# #                     "default_gateway": ipv4.get("DefaultGateway", ""),
# #                     "dns_servers": ipv4.get("DnsServers", []),
# #                 })
            
# #             # Get current IP for quick access
# #             current_ip = ip
# #             for adapter in network_info["adapters"]:
# #                 if adapter.get("ip_address"):
# #                     current_ip = adapter.get("ip_address")
# #                     break
            
# #             network_info["current_ip"] = current_ip
            
# #             return network_info
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] get_network_config failed: {e}")
# #             return {"error": str(e), "current_ip": ip}

# #     # ========== POWER SETTINGS ==========
    
# #     def get_power_settings(self, ip, port=443, display_id=None) -> dict:
# #         """Get power settings"""
# #         try:
# #             result = self._make_request(ip, "GET", "/Device/App/Config/")
# #             config = self._unwrap(result, "Device", "App", "Config") or {}
# #             general = config.get("General", {})
            
# #             raw_power_mode = general.get("PowerControlOptions", "AlwaysOn")
            
# #             power_schedule = general.get("PowerSchedule", {})
# #             formatted_schedule = {}
            
# #             days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            
# #             for day in days:
# #                 if day in power_schedule:
# #                     schedule = power_schedule[day]
# #                     formatted_schedule[day] = {
# #                         "IsEnabled": schedule.get("IsEnabled", False),
# #                         "OnTime": schedule.get("OnTime", ""),
# #                         "OffTime": schedule.get("OffTime", "")
# #                     }
# #                 else:
# #                     formatted_schedule[day] = {
# #                         "IsEnabled": False,
# #                         "OnTime": "",
# #                         "OffTime": ""
# #                     }
            
# #             return {
# #                 "power_control_options": raw_power_mode,
# #                 "is_flex_mode_enabled": general.get("IsFlexModeEnabled", False),
# #                 "occupancy_power_on": general.get("OccupancyPowerSettings", {}).get("PowerOnEnable", False),
# #                 "occupancy_power_off": general.get("OccupancyPowerSettings", {}).get("PowerOffEnable", False),
# #                 "video_sync_power_on": general.get("VideoSyncPowerSettings", {}).get("PowerOnEnable", False),
# #                 "video_sync_power_off": general.get("VideoSyncPowerSettings", {}).get("PowerOffEnable", False),
# #                 "video_sync_timeout": general.get("VideoSyncPowerSettings", {}).get("PowerOffTimeoutMinutes", 1),
# #                 "power_schedule": formatted_schedule,
# #                 "flex_mode_enabled": general.get("IsFlexModeEnabled", False),
# #             }
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] get_power_settings failed: {e}")
# #             return {"error": str(e)}

# #     # ========== WIRELESS CONFERENCING ==========
    
# #     def get_wireless_conferencing(self, ip, port=443, display_id=None) -> dict:
# #         """Get wireless conferencing status"""
# #         try:
# #             result = self._make_request(ip, "GET", "/Device/AirMedia/")
# #             am = self._unwrap(result, "Device", "AirMedia") or {}
# #             wc = am.get("WirelessConferencing", {})
# #             config = wc.get("Configuration", {})
# #             status = wc.get("Status", {})
            
# #             return {
# #                 "enabled": config.get("IsEnabled", False),
# #                 "quality": config.get("QualityMode", "Normal"),
# #                 "hide_status": config.get("IsPeripheralStatusHidden", False),
# #                 "volume": config.get("PeripheralVolume", 89),
# #                 "muted": config.get("PeripheralMute", False),
# #                 "privacy_enabled": config.get("IsPrivacyEnabled", False),
# #                 "conference_status": status.get("ConferencingStatus", "Unavailable"),
# #                 "mic_detected": status.get("IsMicDetected", False),
# #                 "mic_model": status.get("MicModel", ""),
# #                 "mic_in_use": status.get("IsMicInUse", False),
# #                 "camera_detected": status.get("IsCameraDetected", False),
# #                 "camera_model": status.get("CameraModel", ""),
# #                 "camera_resolution": status.get("CameraResolution", ""),
# #                 "speaker_detected": status.get("IsSpeakerDetected", False),
# #                 "speaker_model": status.get("SpeakerModel", ""),
# #             }
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] get_wireless_conferencing failed: {e}")
# #             return {"error": str(e)}

# #     # ========== APPLICATION MODE ==========
    
# #     def get_application_mode(self, ip, port=443, display_id=None) -> dict:
# #         """Get application mode settings"""
# #         try:
# #             result = self._make_request(ip, "GET", "/Device/App/Config/")
# #             config = self._unwrap(result, "Device", "App", "Config") or {}
# #             general = config.get("General", {})
            
# #             application_mode = general.get("ApplicationMode", "AirMediaExperience")
# #             signage_provider = general.get("SignageProvider", "None")
# #             signage_url = general.get("SignageUrl", "")
# #             content_caching = general.get("ContentCaching", "SignageAsBackground")
            
# #             return {
# #                 "application_mode": application_mode,
# #                 "signage_provider": signage_provider,
# #                 "signage_url": signage_url,
# #                 "content_caching": content_caching,
# #                 "system_mode": general.get("SystemMode", "OptimizedForMultiplePresentations"),
# #                 "canvas_enabled": general.get("IsCanvasEnabled", False),
# #                 "canvas_options": general.get("CanvasOptions", "AllSources"),
# #                 "web_download_enabled": general.get("IsWebApplicationDownloadEnabled", False),
# #                 "flex_mode_enabled": general.get("IsFlexModeEnabled", False),
# #             }
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] get_application_mode failed: {e}")
# #             return {"error": str(e)}

# #     # ========== CONNECTION DISPLAY ==========
    
# #     def get_connection_display(self, ip, port=443, display_id=None) -> dict:
# #         """Get connection display options"""
# #         try:
# #             result = self._make_request(ip, "GET", "/Device/AirMedia/")
# #             am = self._unwrap(result, "Device", "AirMedia") or {}
# #             display = am.get("ConnectionDisplayOptions", {})
            
# #             return {
# #                 "show_airmedia_overlay": display.get("ShowAirMediaOverlay", False) or display.get("ShowAirMediaConnectionInfoOverlay", False),
# #                 "show_connection_info": display.get("ShowConnectionInfo", False),
# #                 "connection_info_mode": display.get("ConnectionInfoMode", "IPAddress"),
# #                 "custom_url": display.get("CustomString", ""),
# #                 "show_guest_connection_info": display.get("ShowGuestConnectionInfo", False),
# #                 "guest_info_mode": display.get("GuestInfoMode", "Internal"),
# #                 "guest_custom_url": display.get("GuestCustomString", ""),
# #                 "show_airplay": display.get("ShowAirplayInfo", False),
# #                 "show_miracast": display.get("ShowMiracastInfo", False),
# #                 "show_connect_adaptor": display.get("ShowConnectAdaptorInfo", False) or display.get("ShowConnectAdapterInfo", False),
# #                 "show_wired_connection": display.get("ShowWiredConnectionInfo", False),
# #                 "show_wired_details": display.get("ShowWiredConnectionDetails", False),
# #             }
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] get_connection_display failed: {e}")
# #             return {"error": str(e)}

# #     # ========== PAIRED DEVICES ==========
    
# #     def get_paired_devices(self, ip, port=443, display_id=None) -> dict:
# #         """Get paired TX3 devices"""
# #         try:
# #             devices_list = []
# #             tx3_root = {}
            
# #             result = self._make_request(ip, "GET", "/Device/AirMediaTx3/")
            
# #             if result and isinstance(result, dict) and "error" not in result:
# #                 tx3_root = self._unwrap(result, "Device", "AirMediaTx3") or result.get("AirMediaTx3", {})
# #                 devices_map = tx3_root.get("Tx3DevicesMap") or tx3_root.get("Devices", {})
                
# #                 if isinstance(devices_map, dict):
# #                     for device_id, device in devices_map.items():
# #                         if isinstance(device, dict):
# #                             parsed_device = self._parse_tx3_device(device_id, device)
# #                             devices_list.append(parsed_device)
# #                 elif isinstance(devices_map, list):
# #                     for device in devices_map:
# #                         if isinstance(device, dict):
# #                             device_id = device.get("Id") or device.get("DeviceId") or device.get("MAC", "")
# #                             parsed_device = self._parse_tx3_device(device_id, device)
# #                             devices_list.append(parsed_device)
            
# #             # Get pairing status
# #             pairing_status = "Not Started"
# #             try:
# #                 status_result = self._make_request(ip, "GET", "/Device/AirMediaTx3/PairingStatus")
# #                 pairing_status = self._extract_pairing_status(status_result)
# #             except:
# #                 pass

# #             connect_adapter_behavior = (
# #                 tx3_root.get("ConnectAdapterBehavior")
# #                 or tx3_root.get("ConnectAdaptorBehavior")
# #                 or "AutoPresentAndAutoConference"
# #             )
            
# #             local_pairing_enabled = self._extract_local_pairing_enabled(tx3_root)
            
# #             return {
# #                 "paired_devices": devices_list,
# #                 "count": len(devices_list),
# #                 "pairing_status": pairing_status,
# #                 "local_pairing_enabled": local_pairing_enabled,
# #                 "connect_adapter_behavior": connect_adapter_behavior,
# #             }
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] get_paired_devices failed: {e}")
# #             return {
# #                 "paired_devices": [],
# #                 "count": 0,
# #                 "pairing_status": "Not Started",
# #                 "local_pairing_enabled": False,
# #                 "connect_adapter_behavior": "AutoPresentAndAutoConference",
# #                 "error": str(e),
# #             }

# #     def _parse_tx3_device(self, device_id: str, device: dict) -> dict:
# #         """Parse a TX3 device into standardized format"""
# #         nickname = (
# #             device.get("Nickname") or 
# #             device.get("FriendlyName") or 
# #             device.get("Name") or 
# #             device.get("DeviceName") or
# #             device.get("displayName")
# #         )
        
# #         if not nickname:
# #             mac = device.get("MacAddress") or device.get("MAC") or device.get("Mac")
# #             if mac and len(str(mac)) > 8:
# #                 nickname = f"AirMedia TX3-{str(mac)[-8:].replace(':', '')}"
# #             else:
# #                 nickname = "AirMedia TX3"
        
# #         serial = device.get("SerialNumber") or device.get("Serial") or "N/A"
# #         if isinstance(serial, str):
# #             serial = serial.replace('\n', '').strip()
# #             if not serial:
# #                 serial = "N/A"
        
# #         status = device.get("Status") or device.get("ConnectionStatus") or device.get("State") or "Unknown"
# #         status_lower = str(status).lower()
# #         if status_lower in ["online", "connected", "active"]:
# #             display_status = "Online"
# #         elif status_lower in ["offline", "disconnected", "inactive"]:
# #             display_status = "Offline"
# #         elif status_lower in ["pairing", "pair"]:
# #             display_status = "Pairing"
# #         else:
# #             display_status = str(status) if status else "Unknown"
        
# #         signal = device.get("SignalStrengthPercentage") or device.get("SignalStrength") or device.get("Signal") or 0
# #         if isinstance(signal, (int, float)):
# #             signal = int(signal)
# #         else:
# #             try:
# #                 signal = int(signal)
# #             except:
# #                 signal = 0
        
# #         firmware = device.get("FirmwareVersion") or device.get("Firmware") or device.get("Version") or "Unknown"
# #         mac = device.get("MacAddress") or device.get("MAC") or device.get("Mac") or "N/A"
# #         model = device.get("ModelNumber") or device.get("Model") or device.get("Product") or "AM-TX3-100-I"
        
# #         return {
# #             "id": device_id,
# #             "nickname": nickname,
# #             "model_number": model,
# #             "status": display_status,
# #             "serial_number": serial,
# #             "mac_address": str(mac) if mac else "N/A",
# #             "firmware_version": firmware,
# #             "signal": signal,
# #             "connection_method": device.get("ConnectionMethod", "WiFi Direct"),
# #             "is_online": display_status == "Online",
# #         }

# #     def _extract_pairing_status(self, status_result) -> str:
# #         """Normalize pairing status from API response"""
# #         if not status_result:
# #             return "Not Started"
# #         if isinstance(status_result, str):
# #             return status_result
# #         if not isinstance(status_result, dict):
# #             return "Not Started"
# #         nested_status = (
# #             status_result.get("Status")
# #             or status_result.get("status")
# #             or self._unwrap(status_result, "Device", "AirMediaTx3", "PairingStatus", "Status")
# #             or self._unwrap(status_result, "Device", "AirMediaTx3", "PairingStatus")
# #             or self._unwrap(status_result, "Device", "AirMediaTx3", "Status")
# #         )
# #         return nested_status or "Not Started"

# #     def _extract_local_pairing_enabled(self, tx3_root: dict) -> bool:
# #         """Read local pairing state from TX3 settings"""
# #         if not isinstance(tx3_root, dict):
# #             tx3_root = {}
# #         for key in ("LocalPairingEnabled", "IsLocalPairingEnabled", "IsPairingEnabled", "PairingEnabled"):
# #             value = tx3_root.get(key)
# #             if isinstance(value, bool):
# #                 return value
# #         return False

# #     # ========== CONNECTED CLIENTS ==========
    
# #     def get_connected_clients(self, ip, port=443, display_id=None) -> dict:
# #         """Get connected AirMedia clients"""
# #         try:
# #             result = self._make_request(ip, "GET", "/Device/AirMedia/ClientData/")
# #             data = self._unwrap(result, "Device", "AirMedia", "ClientData") or {}
            
# #             return {
# #                 "total_users": data.get("TotalUsers", 0),
# #                 "status": data.get("Status", "Idle"),
# #                 "connected_clients": data.get("ConnectedClients", {}),
# #             }
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] get_connected_clients failed: {e}")
# #             return {"error": str(e)}

# #     # ========== FULL STATUS ==========
    
# #     def query_status(self, ip, port=443, display_id=None) -> dict:
# #         """Query device status for polling - returns full device data"""
# #         try:
# #             logger.info(f"[CrestronAirMedia] query_status called for {ip}")
            
# #             device_info = self.get_device_info(ip, port, display_id)
# #             airmedia = self.get_airmedia_status(ip, port, display_id)
# #             network = self.get_network_config(ip, port, display_id)
# #             power = self.get_power_settings(ip, port, display_id)
# #             wc = self.get_wireless_conferencing(ip, port, display_id)
# #             app_mode = self.get_application_mode(ip, port, display_id)
# #             conn_display = self.get_connection_display(ip, port, display_id)
# #             paired = self.get_paired_devices(ip, port, display_id)
# #             clients = self.get_connected_clients(ip, port, display_id)
            
# #             reachable = device_info.get("current_status") == "Online"
            
# #             return {
# #                 "reachable": reachable,
# #                 "power": "ON" if reachable else "OFF",
# #                 "device_name": device_info.get("device_name"),
# #                 "model": device_info.get("model"),
# #                 "serial_number": device_info.get("serial_number"),
# #                 "firmware": device_info.get("firmware"),
# #                 "hostname": network.get("hostname", "") if isinstance(network, dict) else "",
# #                 "current_ip": network.get("current_ip", ip) if isinstance(network, dict) else ip,
# #                 "mac_address": device_info.get("mac_address"),
# #                 "ssh_enabled": network.get("ssh_enabled", False) if isinstance(network, dict) else False,
# #                 "airmedia_enabled": airmedia.get("is_enabled", False) if isinstance(airmedia, dict) else False,
# #                 "flex_mode_enabled": power.get("is_flex_mode_enabled", False) if isinstance(power, dict) else False,
# #                 "wireless_conferencing_enabled": wc.get("enabled", False) if isinstance(wc, dict) else False,
                
# #                 # Full structured data for frontend
# #                 "device_info": device_info,
# #                 "airmedia_status": airmedia,
# #                 "network_config": network,
# #                 "power_settings": power,
# #                 "wireless_conferencing": wc,
# #                 "application_mode": app_mode,
# #                 "connection_display": conn_display,
# #                 "paired_devices": paired,
# #                 "connected_clients": clients,
# #                 "timestamp": time.time(),
# #             }
# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] query_status failed: {e}")
# #             return {
# #                 "reachable": False,
# #                 "power": "OFF",
# #                 "error": str(e),
# #                 "device_info": {"current_status": "Offline", "error": str(e)},
# #                 "network_config": {"current_ip": ip},
# #             }

# #     # ========== COMMAND HANDLER ==========
    
# #     def send_command(self, ip, port, display_id, command, params=None):
# #         """Execute a command on the device"""
# #         if not self.username or not self.password:
# #             return False, "Missing credentials: username and password are required."

# #         logger.info(f"[CrestronAirMedia] Command: {command} to {ip}, params: {params}")
# #         params = params or {}

# #         try:
# #             # ========== Status Commands ==========
# #             if command == "get_status" or command == "refresh_status":
# #                 result = self.query_status(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_device_info":
# #                 result = self.get_device_info(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_airmedia_status":
# #                 result = self.get_airmedia_status(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_network_config":
# #                 result = self.get_network_config(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_power_settings":
# #                 result = self.get_power_settings(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_wireless_conferencing":
# #                 result = self.get_wireless_conferencing(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_application_mode":
# #                 result = self.get_application_mode(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_connection_display":
# #                 result = self.get_connection_display(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_paired_devices":
# #                 result = self.get_paired_devices(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_connected_clients":
# #                 result = self.get_connected_clients(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             elif command == "get_full_status":
# #                 result = self.query_status(ip, port, display_id)
# #                 return True, json.dumps(result)

# #             # ========== Device Operations ==========
# #             elif command == "reboot":
# #                 wait = params.get("wait_for_reboot", False)
# #                 result = self._reboot_device(ip)
# #                 if wait:
# #                     time.sleep(60)
# #                 return result.get("success", False), result.get("message", "")

# #             # ========== Hostname & Domain ==========
# #             elif command == "set_hostname":
# #                 hostname = params.get("hostname", "")
# #                 if not hostname:
# #                     return False, "Hostname is required"
# #                 result = self._set_hostname(ip, hostname)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_domain":
# #                 domain = params.get("domain", "")
# #                 if not domain:
# #                     return False, "Domain is required"
# #                 result = self._set_domain(ip, domain)
# #                 return result.get("success", False), result.get("message", "")

# #             # ========== Network Configuration ==========
# #             elif command == "set_static_ip":
# #                 ip_address = params.get("ip_address", "")
# #                 subnet_mask = params.get("subnet_mask", "")
# #                 gateway = params.get("gateway", "")
# #                 dns1 = params.get("dns1", "8.8.8.8")
# #                 dns2 = params.get("dns2", "8.8.4.4")
# #                 adapter = params.get("adapter", "FEC1")
                
# #                 if not ip_address or not subnet_mask or not gateway:
# #                     return False, "IP address, subnet mask, and gateway are required"
                
# #                 result = self._set_static_ip(ip, ip_address, subnet_mask, gateway, dns1, dns2, adapter)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "enable_dhcp":
# #                 adapter = params.get("adapter", "FEC1")
# #                 result = self._enable_dhcp(ip, adapter)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_ssh":
# #                 enabled = params.get("enabled", False)
# #                 result = self._set_ssh(ip, enabled)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_ping":
# #                 enabled = params.get("enabled", False)
# #                 result = self._set_ping(ip, enabled)
# #                 return result.get("success", False), result.get("message", "")

# #             # ========== Flex Mode ==========
# #             elif command == "enable_flex_mode":
# #                 result = self._set_flex_mode(ip, True)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "disable_flex_mode":
# #                 result = self._set_flex_mode(ip, False)
# #                 return result.get("success", False), result.get("message", "")

# #             # ========== Power Settings ==========
# #             elif command == "set_power_mode":
# #                 mode = params.get("mode", "")
# #                 if not mode:
# #                     return False, "Mode is required"
# #                 result = self._set_power_mode(ip, mode)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_occupancy_power":
# #                 power_on = params.get("power_on")
# #                 power_off = params.get("power_off")
# #                 result = self._set_occupancy_power(ip, power_on, power_off)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_video_sync_power":
# #                 power_on = params.get("power_on")
# #                 power_off = params.get("power_off")
# #                 timeout = params.get("timeout")
# #                 result = self._set_video_sync_power(ip, power_on, power_off, timeout)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_power_schedule":
# #                 day = params.get("day", "")
# #                 enabled = params.get("enabled", False)
# #                 on_time = params.get("on_time", "")
# #                 off_time = params.get("off_time", "")
                
# #                 if not day:
# #                     return False, "Day is required"
                
# #                 result = self._set_power_schedule(ip, day, enabled, on_time, off_time)
# #                 return result.get("success", False), result.get("message", "")

# #             # ========== Wireless Conferencing ==========
# #             elif command == "enable_wireless_conferencing":
# #                 result = self._set_wireless_conferencing_enabled(ip, True)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "disable_wireless_conferencing":
# #                 result = self._set_wireless_conferencing_enabled(ip, False)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_wireless_conferencing_quality":
# #                 quality = params.get("quality", "")
# #                 if not quality:
# #                     return False, "Quality is required"
# #                 result = self._set_wireless_conferencing_quality(ip, quality)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_peripheral_volume":
# #                 volume = params.get("volume", 50)
# #                 result = self._set_peripheral_volume(ip, volume)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "mute_peripheral":
# #                 result = self._mute_peripheral(ip)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "unmute_peripheral":
# #                 result = self._unmute_peripheral(ip)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "hide_peripheral_status":
# #                 result = self._hide_peripheral_status(ip)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "show_peripheral_status":
# #                 result = self._show_peripheral_status(ip)
# #                 return result.get("success", False), result.get("message", "")

# #             # ========== Application Mode ==========
# #             elif command == "set_application_mode":
# #                 mode = params.get("mode", "")
# #                 signage_provider = params.get("signage_provider", "None")
# #                 signage_url = params.get("signage_url", "")
# #                 if not mode:
# #                     return False, "Mode is required"
# #                 result = self._set_application_mode(ip, mode, signage_provider, signage_url)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_content_caching":
# #                 mode = params.get("mode", "")
# #                 if not mode:
# #                     return False, "Mode is required"
# #                 result = self._set_content_caching(ip, mode)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_system_mode":
# #                 mode = params.get("mode", "")
# #                 if not mode:
# #                     return False, "Mode is required"
# #                 result = self._set_system_mode(ip, mode)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "enable_canvas":
# #                 result = self._set_canvas_enabled(ip, True)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "disable_canvas":
# #                 result = self._set_canvas_enabled(ip, False)
# #                 return result.get("success", False), result.get("message", "")

# #             # ========== Connection Display ==========
# #             elif command == "set_airmedia_connection_overlay":
# #                 enabled = params.get("enabled", False)
# #                 result = self._set_airmedia_connection_overlay(ip, enabled)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_connection_display_info":
# #                 show = params.get("show", False)
# #                 mode = params.get("mode")
# #                 custom = params.get("custom")
# #                 result = self._set_connection_display_info(ip, show, mode, custom)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_guest_connection_info":
# #                 show = params.get("show", False)
# #                 mode = params.get("mode")
# #                 custom = params.get("custom")
# #                 result = self._set_guest_connection_info(ip, show, mode, custom)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_connection_info_mode":
# #                 mode = params.get("mode", "")
# #                 custom = params.get("custom")
# #                 if not mode:
# #                     return False, "Mode is required"
# #                 result = self._set_connection_info_mode(ip, mode, custom)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_connection_display_airplay":
# #                 enabled = params.get("enabled", False)
# #                 result = self._set_connection_display_airplay(ip, enabled)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_connection_display_miracast":
# #                 enabled = params.get("enabled", False)
# #                 result = self._set_connection_display_miracast(ip, enabled)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_connection_display_adaptor":
# #                 enabled = params.get("enabled", False)
# #                 result = self._set_connection_display_adaptor(ip, enabled)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_wired_connection_info":
# #                 enabled = params.get("enabled", False)
# #                 result = self._set_wired_connection_info(ip, enabled)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_wired_connection_details":
# #                 enabled = params.get("enabled", False)
# #                 result = self._set_wired_connection_details(ip, enabled)
# #                 return result.get("success", False), result.get("message", "")

# #             # ========== TX3 Pairing ==========
# #             elif command == "start_pairing":
# #                 result = self._start_pairing(ip)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "stop_pairing":
# #                 result = self._stop_pairing(ip)
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_local_pairing_enabled":
# #                 enabled = params.get("enabled")
# #                 if enabled is None:
# #                     return False, "Enabled state is required"
# #                 result = self._set_local_pairing_enabled(ip, bool(enabled))
# #                 return result.get("success", False), result.get("message", "")

# #             elif command == "set_connect_adapter_behavior":
# #                 behavior = params.get("behavior", "")
# #                 if not behavior:
# #                     return False, "Behavior is required"
# #                 result = self._set_connect_adapter_behavior(ip, behavior)
# #                 return result.get("success", False), result.get("message", "")

# #             else:
# #                 return False, f"Unknown command: {command}"

# #         except Exception as e:
# #             logger.error(f"[CrestronAirMedia] Command failed: {e}")
# #             return False, str(e)

# #     # ========== COMMAND IMPLEMENTATIONS ==========
    
# #     def _reboot_device(self, ip):
# #         """Reboot the device"""
# #         try:
# #             payload = {"Device": {"DeviceOperations": {"Reboot": True}}}
# #             result = self._make_request(ip, "POST", "/Device/DeviceOperations/", data=payload)
# #             if "error" in result:
# #                 return {"success": False, "message": result["error"]}
# #             return {"success": True, "message": "Reboot command sent successfully"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_hostname(self, ip, hostname: str) -> dict:
# #         """Set device hostname"""
# #         if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', hostname):
# #             return {"success": False, "message": "Invalid hostname format"}
# #         if len(hostname) > 63:
# #             return {"success": False, "message": "Hostname too long. Max 63 characters"}
        
# #         payload_eth = {"Device": {"Ethernet": {"HostName": hostname}}}
# #         payload_net = {"Device": {"NetworkAdapters": {"HostName": hostname}}}
        
# #         try:
# #             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload_eth)
# #             self._make_request(ip, "POST", "/Device/NetworkAdapters/", data=payload_net)
# #             return {"success": True, "message": f"Hostname set to '{hostname}'"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_domain(self, ip, domain: str) -> dict:
# #         """Set device domain"""
# #         if domain and len(domain) > 127:
# #             return {"success": False, "message": "Domain too long. Max 127 characters"}
        
# #         payload = {"Device": {"Ethernet": {"DomainName": domain}}}
        
# #         try:
# #             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
# #             return {"success": True, "message": f"Domain set to '{domain}'"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_static_ip(self, ip, ip_address: str, subnet_mask: str, gateway: str, 
# #                        dns1: str = "8.8.8.8", dns2: str = "8.8.4.4", adapter: str = "FEC1") -> dict:
# #         """Set static IP configuration"""
# #         payload = {
# #             "Device": {
# #                 "Ethernet": {
# #                     "Adapters": [{
# #                         "Name": adapter,
# #                         "IPv4": {
# #                             "IsDhcpEnabled": False,
# #                             "StaticAddresses": [{"Address": ip_address, "SubnetMask": subnet_mask}],
# #                             "StaticDefaultGateway": gateway,
# #                             "StaticDns": [dns1, dns2]
# #                         }
# #                     }]
# #                 }
# #             }
# #         }
# #         try:
# #             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
# #             return {"success": True, "message": f"Static IP {ip_address} configured"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _enable_dhcp(self, ip, adapter: str = "FEC1") -> dict:
# #         """Enable DHCP"""
# #         payload = {"Device": {"Ethernet": {"Adapters": [{"Name": adapter, "IPv4": {"IsDhcpEnabled": True}}]}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
# #             return {"success": True, "message": "DHCP enabled"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_ssh(self, ip, enabled: bool) -> dict:
# #         """Enable/disable SSH"""
# #         payload_eth = {"Device": {"Ethernet": {"IsSshEnabled": enabled}}}
# #         payload_comm = {"Device": {"CommunicationConfigurations": {"IsSshEnabled": enabled}}}
        
# #         try:
# #             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload_eth)
# #             self._make_request(ip, "POST", "/Device/CommunicationConfigurations/", data=payload_comm)
# #             state = "enabled" if enabled else "disabled"
# #             return {"success": True, "message": f"SSH {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_ping(self, ip, enabled: bool) -> dict:
# #         """Enable/disable ICMP ping"""
# #         payload = {"Device": {"Ethernet": {"IsIcmpPingEnabled": enabled}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
# #             state = "enabled" if enabled else "disabled"
# #             return {"success": True, "message": f"ICMP ping {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_flex_mode(self, ip, enabled: bool) -> dict:
# #         """Set Flex Mode"""
# #         payload = {"Device": {"App": {"Config": {"General": {"IsFlexModeEnabled": enabled}}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
# #             state = "enabled" if enabled else "disabled"
# #             return {"success": True, "message": f"Flex Mode {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_power_mode(self, ip, mode: str) -> dict:
# #         """Set power control mode"""
# #         valid_modes = ["AlwaysOn", "OccupancyBased", "OccupancyBasedWithSignage", "VideoSyncBased", "SignageOnly"]
        
# #         if mode not in valid_modes:
# #             return {"success": False, "message": f"Invalid mode: {mode}. Valid modes: {', '.join(valid_modes)}"}
        
# #         payload = {
# #             "Device": {
# #                 "App": {
# #                     "Config": {
# #                         "General": {
# #                             "PowerControlOptions": mode
# #                         }
# #                     }
# #                 }
# #             }
# #         }
        
# #         try:
# #             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
# #             time.sleep(1)
# #             return {"success": True, "message": f"Power mode set successfully"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_occupancy_power(self, ip, power_on: bool = None, power_off: bool = None) -> dict:
# #         """Set occupancy power settings"""
# #         payload = {"Device": {"App": {"Config": {"General": {"OccupancyPowerSettings": {}}}}}}
# #         if power_on is not None:
# #             payload["Device"]["App"]["Config"]["General"]["OccupancyPowerSettings"]["PowerOnEnable"] = power_on
# #         if power_off is not None:
# #             payload["Device"]["App"]["Config"]["General"]["OccupancyPowerSettings"]["PowerOffEnable"] = power_off
        
# #         try:
# #             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
# #             return {"success": True, "message": "Occupancy power settings updated"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_video_sync_power(self, ip, power_on: bool = None, power_off: bool = None, timeout: int = None) -> dict:
# #         """Set video sync power settings"""
# #         payload = {"Device": {"App": {"Config": {"General": {"VideoSyncPowerSettings": {}}}}}}
# #         if power_on is not None:
# #             payload["Device"]["App"]["Config"]["General"]["VideoSyncPowerSettings"]["PowerOnEnable"] = power_on
# #         if power_off is not None:
# #             payload["Device"]["App"]["Config"]["General"]["VideoSyncPowerSettings"]["PowerOffEnable"] = power_off
# #         if timeout is not None:
# #             if timeout < 1 or timeout > 120:
# #                 return {"success": False, "message": "Timeout must be between 1 and 120 minutes"}
# #             payload["Device"]["App"]["Config"]["General"]["VideoSyncPowerSettings"]["PowerOffTimeoutMinutes"] = timeout
        
# #         try:
# #             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
# #             return {"success": True, "message": "Video sync power settings updated"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_power_schedule(self, ip, day: str, enabled: bool, on_time: str = "", off_time: str = "") -> dict:
# #         """Set power schedule for a specific day"""
# #         days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
# #         day_cap = day.capitalize() if day else day
        
# #         if day_cap not in days:
# #             return {"success": False, "message": f"Invalid day. Must be one of: {', '.join(days)}"}
        
# #         if not on_time or not off_time:
# #             try:
# #                 result = self._make_request(ip, "GET", "/Device/App/Config/")
# #                 config = self._unwrap(result, "Device", "App", "Config") or {}
# #                 general = config.get("General", {})
# #                 power_schedule = general.get("PowerSchedule", {})
# #                 existing = power_schedule.get(day_cap, {})
# #                 on_time = on_time or existing.get("OnTime", "09:00")
# #                 off_time = off_time or existing.get("OffTime", "17:00")
# #             except:
# #                 on_time = on_time or "09:00"
# #                 off_time = off_time or "17:00"
        
# #         payload = {
# #             "Device": {
# #                 "App": {
# #                     "Config": {
# #                         "General": {
# #                             "PowerSchedule": {
# #                                 day_cap: {
# #                                     "IsEnabled": enabled,
# #                                     "OnTime": on_time,
# #                                     "OffTime": off_time
# #                                 }
# #                             }
# #                         }
# #                     }
# #                 }
# #             }
# #         }
# #         try:
# #             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
# #             return {"success": True, "message": f"Schedule for {day_cap} updated"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_wireless_conferencing_enabled(self, ip, enabled: bool) -> dict:
# #         """Set wireless conferencing enabled state"""
# #         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"IsEnabled": enabled}}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             state = "enabled" if enabled else "disabled"
# #             return {"success": True, "message": f"Wireless conferencing {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_wireless_conferencing_quality(self, ip, quality: str) -> dict:
# #         """Set wireless conferencing quality"""
# #         if quality not in ['Normal', 'Low']:
# #             return {"success": False, "message": "Quality must be 'Normal' or 'Low'"}
        
# #         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"QualityMode": quality}}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": f"Quality set to '{quality}'"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_peripheral_volume(self, ip, volume: int) -> dict:
# #         """Set peripheral volume"""
# #         if volume < 0 or volume > 100:
# #             return {"success": False, "message": "Volume must be between 0 and 100"}
        
# #         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"PeripheralVolume": volume}}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": f"Volume set to {volume}%"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _mute_peripheral(self, ip) -> dict:
# #         """Mute peripheral audio"""
# #         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"PeripheralMute": True}}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": "Audio muted"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _unmute_peripheral(self, ip) -> dict:
# #         """Unmute peripheral audio"""
# #         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"PeripheralMute": False}}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": "Audio unmuted"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _hide_peripheral_status(self, ip) -> dict:
# #         """Hide peripheral status"""
# #         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"IsPeripheralStatusHidden": True}}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": "Peripheral status hidden"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _show_peripheral_status(self, ip) -> dict:
# #         """Show peripheral status"""
# #         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"IsPeripheralStatusHidden": False}}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": "Peripheral status shown"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_system_mode(self, ip, mode: str) -> dict:
# #         """Set system mode"""
# #         valid = ["OptimizedForVideoQuality", "OptimizedForMultiplePresentations"]
# #         if mode not in valid:
# #             return {"success": False, "message": f"Invalid mode. Must be one of: {', '.join(valid)}"}
        
# #         payload = {"Device": {"AirMedia": {"SystemMode": mode}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": f"System mode set to '{mode}'"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_canvas_enabled(self, ip, enabled: bool) -> dict:
# #         """Set Canvas enabled state"""
# #         payload = {"Device": {"AirMedia": {"IsCanvasEnabled": enabled}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             state = "enabled" if enabled else "disabled"
# #             return {"success": True, "message": f"Canvas {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_application_mode(self, ip, mode: str, signage_provider: str = "None", signage_url: str = "") -> dict:
# #         """Set application mode and signage provider"""
# #         try:
# #             payload = {
# #                 "Device": {
# #                     "App": {
# #                         "Config": {
# #                             "General": {
# #                                 "ApplicationMode": mode,
# #                                 "SignageProvider": signage_provider
# #                             }
# #                         }
# #                     }
# #                 }
# #             }
            
# #             if signage_url:
# #                 payload["Device"]["App"]["Config"]["General"]["SignageUrl"] = signage_url
            
# #             result = self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
            
# #             if "error" in result:
# #                 alt_payload = {
# #                     "Device": {
# #                         "AirMedia": {
# #                             "ApplicationMode": mode,
# #                             "SignageProvider": signage_provider
# #                         }
# #                     }
# #                 }
# #                 result = self._make_request(ip, "POST", "/Device/AirMedia/", data=alt_payload)
            
# #             if "error" in result:
# #                 return {"success": False, "message": result.get("error", "Failed to set application mode")}
            
# #             return {"success": True, "message": f"Application mode set to '{mode}' with {signage_provider}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_content_caching(self, ip, mode: str) -> dict:
# #         """Set content caching mode for signage"""
# #         valid_modes = ["SignageAsBackground", "SignageInStandby", "BothBackgroundAndStandby"]
# #         if mode not in valid_modes:
# #             return {"success": False, "message": f"Invalid mode. Must be one of: {', '.join(valid_modes)}"}
        
# #         payload = {
# #             "Device": {
# #                 "App": {
# #                     "Config": {
# #                         "General": {
# #                             "ContentCaching": mode
# #                         }
# #                     }
# #                 }
# #             }
# #         }
# #         try:
# #             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
# #             return {"success": True, "message": f"Content caching set to '{mode}'"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_airmedia_connection_overlay(self, ip, enabled: bool) -> dict:
# #         """Show/hide AirMedia connection info overlay"""
# #         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowAirMediaOverlay": enabled}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             state = "shown" if enabled else "hidden"
# #             return {"success": True, "message": f"AirMedia overlay {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_connection_display_info(self, ip, show: bool, mode: str = None, custom: str = None) -> dict:
# #         """Set primary connection display info"""
# #         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {}}}}
# #         payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ShowConnectionInfo"] = show
        
# #         if mode:
# #             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ConnectionInfoMode"] = mode
        
# #         if custom and mode == "Custom":
# #             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["CustomString"] = custom
        
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": "Primary connection display updated"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_guest_connection_info(self, ip, show: bool, mode: str = None, custom: str = None) -> dict:
# #         """Set guest connection info"""
# #         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {}}}}
# #         payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ShowGuestConnectionInfo"] = show
        
# #         if mode:
# #             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["GuestInfoMode"] = mode
        
# #         if custom and mode == "Custom":
# #             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["GuestCustomString"] = custom
        
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": "Guest connection info updated"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_connection_info_mode(self, ip, mode: str, custom: str = None) -> dict:
# #         """Set connection info display mode"""
# #         valid = ["IPAddress", "Host", "HostAndDomain", "Custom"]
# #         if mode not in valid:
# #             return {"success": False, "message": f"Invalid mode. Must be one of: {', '.join(valid)}"}
        
# #         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {}}}}
# #         payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ConnectionInfoMode"] = mode
        
# #         if custom and mode == "Custom":
# #             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ConnectionCustomString"] = custom
        
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             return {"success": True, "message": f"Connection info mode set to '{mode}'"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_connection_display_airplay(self, ip, enabled: bool) -> dict:
# #         """Show/hide Apple Screen Mirroring info"""
# #         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowAirplayInfo": enabled}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             state = "shown" if enabled else "hidden"
# #             return {"success": True, "message": f"Apple Screen Mirroring info {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_connection_display_miracast(self, ip, enabled: bool) -> dict:
# #         """Show/hide Miracast info"""
# #         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowMiracastInfo": enabled}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             state = "shown" if enabled else "hidden"
# #             return {"success": True, "message": f"Miracast info {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_connection_display_adaptor(self, ip, enabled: bool) -> dict:
# #         """Show/hide Connect Adaptor info"""
# #         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowConnectAdaptorInfo": enabled}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             state = "shown" if enabled else "hidden"
# #             return {"success": True, "message": f"Connect Adaptor info {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_wired_connection_info(self, ip, enabled: bool) -> dict:
# #         """Show/hide wired connection info"""
# #         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowWiredConnectionInfo": enabled}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             state = "shown" if enabled else "hidden"
# #             return {"success": True, "message": f"Wired connection info {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_wired_connection_details(self, ip, enabled: bool) -> dict:
# #         """Show/hide wired connection details"""
# #         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowWiredConnectionDetails": enabled}}}}
# #         try:
# #             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
# #             state = "shown" if enabled else "hidden"
# #             return {"success": True, "message": f"Wired connection details {state}"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _start_pairing(self, ip) -> dict:
# #         """Start TX3 device pairing"""
# #         try:
# #             payload = {"Device": {"AirMediaTx3": {"PairCmd": True}}}
# #             result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
# #             if "error" not in result:
# #                 return {"success": True, "message": "Pairing mode started for 60 seconds", "pairing_status": "In Progress"}
# #             return {"success": False, "message": "Could not start pairing mode"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _stop_pairing(self, ip) -> dict:
# #         """Stop TX3 device pairing mode"""
# #         try:
# #             payload = {"Device": {"AirMediaTx3": {"PairCmd": False}}}
# #             result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
# #             if "error" not in result:
# #                 return {"success": True, "message": "Pairing mode stopped", "pairing_status": "Not Started"}
# #             return {"success": False, "message": "Could not stop pairing mode"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_local_pairing_enabled(self, ip, enabled: bool) -> dict:
# #         """Enable or disable local pairing for TX3 devices"""
# #         payload = {"Device": {"AirMediaTx3": {"IsLocalPairingEnabled": enabled}}}
# #         try:
# #             result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
# #             if "error" not in result:
# #                 return {"success": True, "message": f"Local pairing {'enabled' if enabled else 'disabled'}"}
# #             return {"success": False, "message": "Could not update local pairing"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}

# #     def _set_connect_adapter_behavior(self, ip, behavior: str) -> dict:
# #         """Set connect adapter behavior for TX3 devices"""
# #         valid_behaviors = ["AutoPresentAndAutoConference", "AutoPresent", "AutoConference"]
        
# #         if behavior not in valid_behaviors:
# #             return {"success": False, "message": f"Invalid behavior. Must be one of: {', '.join(valid_behaviors)}"}
        
# #         try:
# #             payload = {"Device": {"AirMediaTx3": {"ConnectAdapterBehavior": behavior}}}
# #             result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
            
# #             if "error" not in result:
# #                 return {"success": True, "message": f"Connect adapter behavior set to '{behavior}'"}
            
# #             # Try alternative spelling
# #             alt_payload = {"Device": {"AirMedia": {"ConnectAdapterBehavior": behavior}}}
# #             alt_result = self._make_request(ip, "POST", "/Device/AirMedia/", data=alt_payload)
            
# #             if "error" not in alt_result:
# #                 return {"success": True, "message": f"Connect adapter behavior set to '{behavior}'"}
            
# #             return {"success": False, "message": "Failed to set connect adapter behavior"}
# #         except Exception as e:
# #             return {"success": False, "message": str(e)}


# # def get_plugin(config=None):
# #     """Factory function to create plugin instance."""
# #     return CrestronAirMediaPlugin(config)
# """
# crestron_airmedia_plugin.py - Crestron AirMedia Series 3 Plugin for Edge Collector
# """

# import json
# import time
# import re
# import requests
# import logging
# from typing import Optional, Dict, Any, List

# from .base import ManualPlatformPlugin

# logger = logging.getLogger(__name__)

# urllib3 = None
# try:
#     import urllib3
#     urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# except ImportError:
#     pass


# class CrestronAirMediaPlugin(ManualPlatformPlugin):
#     """Crestron AirMedia Series 3 Plugin for Edge Collector."""

#     name = "crestron_airmedia"
#     display_name = "Crestron AirMedia Series 3"
#     description = "Crestron AirMedia Series 3 with full control capabilities"
#     supports_display_id = False
#     supports_port = False
#     default_port = 443
    
#     SUPPORTED_MODELS = [
#         "AM-3000-WF-I",
#         "AM-3200",
#         "AM-3200-WF",
#         "AM-3200-WF-I",
#         "AirMedia Series 3",
#         "AM-TX3-100-I",
#     ]

#     def __init__(self, config=None):
#         super().__init__(config)
#         self.username = self.config.get("username") if self.config else None
#         self.password = self.config.get("password") if self.config else None
#         self._xsrf_token = None
#         self._session = None
#         self._authenticated = False
#         logger.info(f"[CrestronAirMedia] Initialized")

#     def _login(self, ip):
#         """Authenticate with the Crestron AirMedia device"""
#         if not self.username or not self.password:
#             raise Exception("Missing credentials")
        
#         base_url = f"https://{ip}"
#         login_url = f"{base_url}/userlogin.html"
        
#         if self._session:
#             self._session.close()
        
#         session = requests.Session()
#         session.verify = False
#         session.headers.update({"User-Agent": "Mozilla/5.0"})
#         self._xsrf_token = None
#         self._authenticated = False

#         # Step 1: GET login page to receive TRACKID cookie
#         r = session.get(login_url, timeout=8)
#         r.raise_for_status()
#         trackid = session.cookies.get("TRACKID")
#         if not trackid:
#             raise Exception("TRACKID cookie not received from device")

#         # Step 2: POST credentials
#         login_headers = {
#             "User-Agent": "Mozilla/5.0",
#             "Cookie": f"TRACKID={trackid}",
#             "Origin": base_url,
#             "Referer": login_url,
#             "Content-Type": "application/x-www-form-urlencoded",
#         }

#         payload = f"login={self.username}&&passwd={self.password}"
#         login_response = session.post(
#             login_url,
#             headers=login_headers,
#             data=payload,
#             timeout=10,
#         )

#         if login_response.status_code == 403:
#             raise Exception("Invalid credentials")
#         if login_response.status_code != 200:
#             raise Exception(f"Login failed (HTTP {login_response.status_code})")

#         self._xsrf_token = login_response.headers.get("CREST-XSRF-TOKEN")
#         if self._xsrf_token:
#             session.headers.update({
#                 "CREST-XSRF-TOKEN": self._xsrf_token,
#                 "X-CREST-XSRF-TOKEN": self._xsrf_token,
#             })

#         self._session = session
#         self._authenticated = True
#         logger.info(f"[CrestronAirMedia] Login successful for {ip}")
#         return session

#     def _make_request(self, ip, method: str, endpoint: str, data: dict = None, timeout: int = None) -> dict:
#         """Make an authenticated API request"""
#         try:
#             if not self._authenticated or not self._session:
#                 self._login(ip)

#             url = f"https://{ip}{endpoint}"
#             headers = {
#                 "User-Agent": "Mozilla/5.0",
#                 "Accept": "application/json",
#                 "Content-Type": "application/json",
#             }
            
#             if self._xsrf_token:
#                 headers["CREST-XSRF-TOKEN"] = self._xsrf_token
#                 headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token

#             def _do_request():
#                 if method == "GET":
#                     return self._session.get(url, headers=headers, timeout=timeout or 10, verify=False)
#                 elif method == "POST":
#                     return self._session.post(url, headers=headers, json=data, timeout=timeout or 30, verify=False)
#                 else:
#                     raise Exception(f"Unsupported HTTP method: {method}")

#             response = _do_request()

#             if response.status_code in (401, 403):
#                 self._login(ip)
#                 response = _do_request()

#             if response.status_code not in (200, 204):
#                 return {
#                     "error": f"HTTP {response.status_code}",
#                     "message": response.text[:300],
#                 }

#             if not response.content or not response.content.strip():
#                 return {}
#             try:
#                 return response.json()
#             except ValueError:
#                 return {"_raw": response.text.strip()}

#         except requests.exceptions.ConnectTimeout:
#             return {"error": "Connection timeout — check device IP and network"}
#         except requests.exceptions.ConnectionError:
#             return {"error": "Connection refused — check device IP and network"}
#         except requests.exceptions.Timeout:
#             return {"error": "Request timed out"}
#         except Exception as e:
#             return {"error": str(e)}

#     def _unwrap(self, data, *keys):
#         """Unwrap nested dictionary data"""
#         result = data
#         for key in keys:
#             if isinstance(result, dict):
#                 result = result.get(key)
#                 if result is None:
#                     return None
#             else:
#                 return None
#         return result

#     # ========== DEVICE INFO ==========
    
#     def get_device_info(self, ip, port=443, display_id=None) -> dict:
#         """Get device information"""
#         if not self.username or not self.password:
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "Crestron",
#                 "device_type": "AirMedia Series 3",
#                 "current_status": "Offline",
#                 "error": "Missing credentials: username and password are required."
#             }

#         try:
#             result = self._make_request(ip, "GET", "/Device/DeviceInfo/")
#             device_info = self._unwrap(result, "Device", "DeviceInfo") or {}
            
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": device_info.get("Manufacturer", "Crestron"),
#                 "device_name": device_info.get("Name", "AirMedia"),
#                 "model": device_info.get("Model", "AM-3200"),
#                 "serial_number": device_info.get("SerialNumber", "Unknown"),
#                 "mac_address": device_info.get("MacAddress", "Unknown"),
#                 "firmware": device_info.get("DeviceVersion", "Unknown"),
#                 "build_date": device_info.get("BuildDate", ""),
#                 "device_id": device_info.get("DeviceId", ""),
#                 "device_type": "Crestron AirMedia Series 3",
#                 "category": device_info.get("Category", "Wireless Presentation"),
#                 "reboot_reason": device_info.get("RebootReason", "Unknown"),
#                 "current_status": "Online",
#             }
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] get_device_info failed: {e}")
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "Crestron",
#                 "device_type": "AirMedia Series 3",
#                 "current_status": "Offline",
#                 "error": str(e),
#             }

#     # ========== AIRMEDIA STATUS ==========
    
#     def get_airmedia_status(self, ip, port=443, display_id=None) -> dict:
#         """Get AirMedia status"""
#         try:
#             result = self._make_request(ip, "GET", "/Device/AirMedia/")
#             am = self._unwrap(result, "Device", "AirMedia") or {}
            
#             return {
#                 "is_enabled": am.get("IsEnabled", False),
#                 "login_code_mode": am.get("LoginCodeMode", "Unknown"),
#                 "active_login_code": am.get("ActiveLoginCode", "None"),
#                 "show_login_code": am.get("ShowLoginCode", False),
#                 "system_mode": am.get("SystemMode", "OptimizedForMultiplePresentations"),
#                 "is_canvas_enabled": am.get("IsCanvasEnabled", False),
#                 "canvas_options": am.get("CanvasOptions", "AllSources"),
#                 "is_web_download_enabled": am.get("IsWebApplicationDownloadEnabled", False),
#             }
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] get_airmedia_status failed: {e}")
#             return {"error": str(e)}

#     # ========== NETWORK CONFIGURATION ==========
    
#     def get_network_config(self, ip, port=443, display_id=None) -> dict:
#         """Get network configuration"""
#         try:
#             result = self._make_request(ip, "GET", "/Device/Ethernet/")
#             eth = self._unwrap(result, "Device", "Ethernet") or {}
#             comm = self._make_request(ip, "GET", "/Device/CommunicationConfigurations/")
#             comm_data = self._unwrap(comm, "Device", "CommunicationConfigurations") or {}
            
#             network_info = {
#                 "hostname": eth.get("HostName", ""),
#                 "domain_name": eth.get("DomainName", ""),
#                 "ssh_enabled": comm_data.get("IsSshEnabled", False),
#                 "icmp_ping_enabled": eth.get("IsIcmpPingEnabled", False),
#                 "auto_negotiation": eth.get("AutoNegotiationEnabled", True),
#                 "igmp_version": eth.get("IgmpVersion", "v2"),
#                 "adapters": []
#             }
            
#             for adapter in eth.get("Adapters", []):
#                 ipv4 = adapter.get("IPv4", {})
#                 addresses = ipv4.get("Addresses", [])
                
#                 network_info["adapters"].append({
#                     "name": adapter.get("Name", "Unknown"),
#                     "internal_name": adapter.get("InternalName", ""),
#                     "mac_address": adapter.get("MacAddress", ""),
#                     "link_status": adapter.get("LinkStatus", False),
#                     "enabled": adapter.get("IsAdapterEnabled", True),
#                     "dhcp_enabled": ipv4.get("IsDhcpEnabled", True),
#                     "ip_address": addresses[0].get("Address", "") if addresses else "",
#                     "subnet_mask": addresses[0].get("SubnetMask", "") if addresses else "",
#                     "default_gateway": ipv4.get("DefaultGateway", ""),
#                     "dns_servers": ipv4.get("DnsServers", []),
#                 })
            
#             # Get current IP for quick access
#             current_ip = ip
#             for adapter in network_info["adapters"]:
#                 if adapter.get("ip_address"):
#                     current_ip = adapter.get("ip_address")
#                     break
            
#             network_info["current_ip"] = current_ip
            
#             return network_info
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] get_network_config failed: {e}")
#             return {"error": str(e), "current_ip": ip}

#     # ========== POWER SETTINGS ==========
    
#     def get_power_settings(self, ip, port=443, display_id=None) -> dict:
#         """Get power settings"""
#         try:
#             result = self._make_request(ip, "GET", "/Device/App/Config/")
#             config = self._unwrap(result, "Device", "App", "Config") or {}
#             general = config.get("General", {})
            
#             raw_power_mode = general.get("PowerControlOptions", "AlwaysOn")
            
#             power_schedule = general.get("PowerSchedule", {})
#             formatted_schedule = {}
            
#             days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            
#             for day in days:
#                 if day in power_schedule:
#                     schedule = power_schedule[day]
#                     formatted_schedule[day] = {
#                         "IsEnabled": schedule.get("IsEnabled", False),
#                         "OnTime": schedule.get("OnTime", ""),
#                         "OffTime": schedule.get("OffTime", "")
#                     }
#                 else:
#                     formatted_schedule[day] = {
#                         "IsEnabled": False,
#                         "OnTime": "",
#                         "OffTime": ""
#                     }
            
#             return {
#                 "power_control_options": raw_power_mode,
#                 "is_flex_mode_enabled": general.get("IsFlexModeEnabled", False),
#                 "occupancy_power_on": general.get("OccupancyPowerSettings", {}).get("PowerOnEnable", False),
#                 "occupancy_power_off": general.get("OccupancyPowerSettings", {}).get("PowerOffEnable", False),
#                 "video_sync_power_on": general.get("VideoSyncPowerSettings", {}).get("PowerOnEnable", False),
#                 "video_sync_power_off": general.get("VideoSyncPowerSettings", {}).get("PowerOffEnable", False),
#                 "video_sync_timeout": general.get("VideoSyncPowerSettings", {}).get("PowerOffTimeoutMinutes", 1),
#                 "power_schedule": formatted_schedule,
#                 "flex_mode_enabled": general.get("IsFlexModeEnabled", False),
#             }
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] get_power_settings failed: {e}")
#             return {"error": str(e)}

#     # ========== WIRELESS CONFERENCING ==========
    
#     def get_wireless_conferencing(self, ip, port=443, display_id=None) -> dict:
#         """Get wireless conferencing status"""
#         try:
#             result = self._make_request(ip, "GET", "/Device/AirMedia/")
#             am = self._unwrap(result, "Device", "AirMedia") or {}
#             wc = am.get("WirelessConferencing", {})
#             config = wc.get("Configuration", {})
#             status = wc.get("Status", {})
            
#             return {
#                 "enabled": config.get("IsEnabled", False),
#                 "quality": config.get("QualityMode", "Normal"),
#                 "hide_status": config.get("IsPeripheralStatusHidden", False),
#                 "volume": config.get("PeripheralVolume", 89),
#                 "muted": config.get("PeripheralMute", False),
#                 "privacy_enabled": config.get("IsPrivacyEnabled", False),
#                 "conference_status": status.get("ConferencingStatus", "Unavailable"),
#                 "mic_detected": status.get("IsMicDetected", False),
#                 "mic_model": status.get("MicModel", ""),
#                 "mic_in_use": status.get("IsMicInUse", False),
#                 "camera_detected": status.get("IsCameraDetected", False),
#                 "camera_model": status.get("CameraModel", ""),
#                 "camera_resolution": status.get("CameraResolution", ""),
#                 "speaker_detected": status.get("IsSpeakerDetected", False),
#                 "speaker_model": status.get("SpeakerModel", ""),
#             }
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] get_wireless_conferencing failed: {e}")
#             return {"error": str(e)}

#     # ========== APPLICATION MODE ==========
    
#     def get_application_mode(self, ip, port=443, display_id=None) -> dict:
#         """Get application mode settings"""
#         try:
#             result = self._make_request(ip, "GET", "/Device/App/Config/")
#             config = self._unwrap(result, "Device", "App", "Config") or {}
#             general = config.get("General", {})
            
#             application_mode = general.get("ApplicationMode", "AirMediaExperience")
#             signage_provider = general.get("SignageProvider", "None")
#             signage_url = general.get("SignageUrl", "")
#             content_caching = general.get("ContentCaching", "SignageAsBackground")
            
#             return {
#                 "application_mode": application_mode,
#                 "signage_provider": signage_provider,
#                 "signage_url": signage_url,
#                 "content_caching": content_caching,
#                 "system_mode": general.get("SystemMode", "OptimizedForMultiplePresentations"),
#                 "canvas_enabled": general.get("IsCanvasEnabled", False),
#                 "canvas_options": general.get("CanvasOptions", "AllSources"),
#                 "web_download_enabled": general.get("IsWebApplicationDownloadEnabled", False),
#                 "flex_mode_enabled": general.get("IsFlexModeEnabled", False),
#             }
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] get_application_mode failed: {e}")
#             return {"error": str(e)}

#     # ========== CONNECTION DISPLAY ==========
    
#     def get_connection_display(self, ip, port=443, display_id=None) -> dict:
#         """Get connection display options"""
#         try:
#             result = self._make_request(ip, "GET", "/Device/AirMedia/")
#             am = self._unwrap(result, "Device", "AirMedia") or {}
#             display = am.get("ConnectionDisplayOptions", {})
            
#             return {
#                 "show_airmedia_overlay": display.get("ShowAirMediaOverlay", False) or display.get("ShowAirMediaConnectionInfoOverlay", False),
#                 "show_connection_info": display.get("ShowConnectionInfo", False),
#                 "connection_info_mode": display.get("ConnectionInfoMode", "IPAddress"),
#                 "custom_url": display.get("CustomString", ""),
#                 "show_guest_connection_info": display.get("ShowGuestConnectionInfo", False),
#                 "guest_info_mode": display.get("GuestInfoMode", "Internal"),
#                 "guest_custom_url": display.get("GuestCustomString", ""),
#                 "show_airplay": display.get("ShowAirplayInfo", False),
#                 "show_miracast": display.get("ShowMiracastInfo", False),
#                 "show_connect_adaptor": display.get("ShowConnectAdaptorInfo", False) or display.get("ShowConnectAdapterInfo", False),
#                 "show_wired_connection": display.get("ShowWiredConnectionInfo", False),
#                 "show_wired_details": display.get("ShowWiredConnectionDetails", False),
#             }
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] get_connection_display failed: {e}")
#             return {"error": str(e)}

#     # ========== PAIRED DEVICES ==========
    
#     def get_paired_devices(self, ip, port=443, display_id=None) -> dict:
#         """Get paired TX3 devices"""
#         try:
#             devices_list = []
#             tx3_root = {}
            
#             result = self._make_request(ip, "GET", "/Device/AirMediaTx3/")
            
#             if result and isinstance(result, dict) and "error" not in result:
#                 tx3_root = self._unwrap(result, "Device", "AirMediaTx3") or result.get("AirMediaTx3", {})
#                 devices_map = tx3_root.get("Tx3DevicesMap") or tx3_root.get("Devices", {})
                
#                 if isinstance(devices_map, dict):
#                     for device_id, device in devices_map.items():
#                         if isinstance(device, dict):
#                             parsed_device = self._parse_tx3_device(device_id, device)
#                             devices_list.append(parsed_device)
#                 elif isinstance(devices_map, list):
#                     for device in devices_map:
#                         if isinstance(device, dict):
#                             device_id = device.get("Id") or device.get("DeviceId") or device.get("MAC", "")
#                             parsed_device = self._parse_tx3_device(device_id, device)
#                             devices_list.append(parsed_device)
            
#             # Get pairing status
#             pairing_status = "Not Started"
#             try:
#                 status_result = self._make_request(ip, "GET", "/Device/AirMediaTx3/PairingStatus")
#                 pairing_status = self._extract_pairing_status(status_result)
#             except:
#                 pass

#             connect_adapter_behavior = (
#                 tx3_root.get("ConnectAdapterBehavior")
#                 or tx3_root.get("ConnectAdaptorBehavior")
#                 or "AutoPresentAndAutoConference"
#             )
            
#             local_pairing_enabled = self._extract_local_pairing_enabled(tx3_root)
            
#             return {
#                 "paired_devices": devices_list,
#                 "count": len(devices_list),
#                 "pairing_status": pairing_status,
#                 "local_pairing_enabled": local_pairing_enabled,
#                 "connect_adapter_behavior": connect_adapter_behavior,
#             }
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] get_paired_devices failed: {e}")
#             return {
#                 "paired_devices": [],
#                 "count": 0,
#                 "pairing_status": "Not Started",
#                 "local_pairing_enabled": False,
#                 "connect_adapter_behavior": "AutoPresentAndAutoConference",
#                 "error": str(e),
#             }

#     def _parse_tx3_device(self, device_id: str, device: dict) -> dict:
#         """Parse a TX3 device into standardized format"""
#         nickname = (
#             device.get("Nickname") or 
#             device.get("FriendlyName") or 
#             device.get("Name") or 
#             device.get("DeviceName") or
#             device.get("displayName")
#         )
        
#         if not nickname:
#             mac = device.get("MacAddress") or device.get("MAC") or device.get("Mac")
#             if mac and len(str(mac)) > 8:
#                 nickname = f"AirMedia TX3-{str(mac)[-8:].replace(':', '')}"
#             else:
#                 nickname = "AirMedia TX3"
        
#         serial = device.get("SerialNumber") or device.get("Serial") or "N/A"
#         if isinstance(serial, str):
#             serial = serial.replace('\n', '').strip()
#             if not serial:
#                 serial = "N/A"
        
#         status = device.get("Status") or device.get("ConnectionStatus") or device.get("State") or "Unknown"
#         status_lower = str(status).lower()
#         if status_lower in ["online", "connected", "active"]:
#             display_status = "Online"
#         elif status_lower in ["offline", "disconnected", "inactive"]:
#             display_status = "Offline"
#         elif status_lower in ["pairing", "pair"]:
#             display_status = "Pairing"
#         else:
#             display_status = str(status) if status else "Unknown"
        
#         signal = device.get("SignalStrengthPercentage") or device.get("SignalStrength") or device.get("Signal") or 0
#         if isinstance(signal, (int, float)):
#             signal = int(signal)
#         else:
#             try:
#                 signal = int(signal)
#             except:
#                 signal = 0
        
#         firmware = device.get("FirmwareVersion") or device.get("Firmware") or device.get("Version") or "Unknown"
#         mac = device.get("MacAddress") or device.get("MAC") or device.get("Mac") or "N/A"
#         model = device.get("ModelNumber") or device.get("Model") or device.get("Product") or "AM-TX3-100-I"
        
#         return {
#             "id": device_id,
#             "nickname": nickname,
#             "model_number": model,
#             "status": display_status,
#             "serial_number": serial,
#             "mac_address": str(mac) if mac else "N/A",
#             "firmware_version": firmware,
#             "signal": signal,
#             "connection_method": device.get("ConnectionMethod", "WiFi Direct"),
#             "is_online": display_status == "Online",
#         }

#     def _extract_pairing_status(self, status_result) -> str:
#         """Normalize pairing status from API response"""
#         if not status_result:
#             return "Not Started"
#         if isinstance(status_result, str):
#             return status_result
#         if not isinstance(status_result, dict):
#             return "Not Started"
#         nested_status = (
#             status_result.get("Status")
#             or status_result.get("status")
#             or self._unwrap(status_result, "Device", "AirMediaTx3", "PairingStatus", "Status")
#             or self._unwrap(status_result, "Device", "AirMediaTx3", "PairingStatus")
#             or self._unwrap(status_result, "Device", "AirMediaTx3", "Status")
#         )
#         return nested_status or "Not Started"

#     def _extract_local_pairing_enabled(self, tx3_root: dict) -> bool:
#         """Read local pairing state from TX3 settings"""
#         if not isinstance(tx3_root, dict):
#             tx3_root = {}
#         for key in ("LocalPairingEnabled", "IsLocalPairingEnabled", "IsPairingEnabled", "PairingEnabled"):
#             value = tx3_root.get(key)
#             if isinstance(value, bool):
#                 return value
#         return False

#     # ========== CONNECTED CLIENTS ==========
    
#     def get_connected_clients(self, ip, port=443, display_id=None) -> dict:
#         """Get connected AirMedia clients"""
#         try:
#             result = self._make_request(ip, "GET", "/Device/AirMedia/ClientData/")
#             data = self._unwrap(result, "Device", "AirMedia", "ClientData") or {}
            
#             return {
#                 "total_users": data.get("TotalUsers", 0),
#                 "status": data.get("Status", "Idle"),
#                 "connected_clients": data.get("ConnectedClients", {}),
#             }
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] get_connected_clients failed: {e}")
#             return {"error": str(e)}

#     # ========== FULL STATUS ==========
    
#     def query_status(self, ip, port=443, display_id=None) -> dict:
#         """Query device status for polling - returns full device data"""
#         try:
#             logger.info(f"[CrestronAirMedia] query_status called for {ip}")
            
#             device_info = self.get_device_info(ip, port, display_id)
#             airmedia = self.get_airmedia_status(ip, port, display_id)
#             network = self.get_network_config(ip, port, display_id)
#             power = self.get_power_settings(ip, port, display_id)
#             wc = self.get_wireless_conferencing(ip, port, display_id)
#             app_mode = self.get_application_mode(ip, port, display_id)
#             conn_display = self.get_connection_display(ip, port, display_id)
#             paired = self.get_paired_devices(ip, port, display_id)
#             clients = self.get_connected_clients(ip, port, display_id)
            
#             reachable = device_info.get("current_status") == "Online"
            
#             return {
#                 "reachable": reachable,
#                 "power": "ON" if reachable else "OFF",
#                 "device_name": device_info.get("device_name"),
#                 "model": device_info.get("model"),
#                 "serial_number": device_info.get("serial_number"),
#                 "firmware": device_info.get("firmware"),
#                 "hostname": network.get("hostname", "") if isinstance(network, dict) else "",
#                 "current_ip": network.get("current_ip", ip) if isinstance(network, dict) else ip,
#                 "mac_address": device_info.get("mac_address"),
#                 "ssh_enabled": network.get("ssh_enabled", False) if isinstance(network, dict) else False,
#                 "airmedia_enabled": airmedia.get("is_enabled", False) if isinstance(airmedia, dict) else False,
#                 "flex_mode_enabled": power.get("is_flex_mode_enabled", False) if isinstance(power, dict) else False,
#                 "wireless_conferencing_enabled": wc.get("enabled", False) if isinstance(wc, dict) else False,
                
#                 # Full structured data for frontend
#                 "device_info": device_info,
#                 "airmedia_status": airmedia,
#                 "network_config": network,
#                 "power_settings": power,
#                 "wireless_conferencing": wc,
#                 "application_mode": app_mode,
#                 "connection_display": conn_display,
#                 "paired_devices": paired,
#                 "connected_clients": clients,
#                 "timestamp": time.time(),
#             }
#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] query_status failed: {e}")
#             return {
#                 "reachable": False,
#                 "power": "OFF",
#                 "error": str(e),
#                 "device_info": {"current_status": "Offline", "error": str(e)},
#                 "network_config": {"current_ip": ip},
#             }

#     # ========== COMMAND HANDLER ==========
    
#     def send_command(self, ip, port, display_id, command, params=None):
#         """Execute a command on the device"""
#         if not self.username or not self.password:
#             return False, "Missing credentials: username and password are required."

#         logger.info(f"[CrestronAirMedia] Command: {command} to {ip}, params: {params}")
#         params = params or {}

#         try:
#             # ========== Status Commands ==========
#             if command == "get_status" or command == "refresh_status":
#                 result = self.query_status(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_device_info":
#                 result = self.get_device_info(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_airmedia_status":
#                 result = self.get_airmedia_status(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_network_config":
#                 result = self.get_network_config(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_power_settings":
#                 result = self.get_power_settings(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_wireless_conferencing":
#                 result = self.get_wireless_conferencing(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_application_mode":
#                 result = self.get_application_mode(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_connection_display":
#                 result = self.get_connection_display(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_paired_devices":
#                 result = self.get_paired_devices(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_connected_clients":
#                 result = self.get_connected_clients(ip, port, display_id)
#                 return True, json.dumps(result)

#             elif command == "get_full_status":
#                 result = self.query_status(ip, port, display_id)
#                 return True, json.dumps(result)

#             # ========== Device Operations ==========
#             elif command == "reboot":
#                 wait = params.get("wait_for_reboot", False)
#                 result = self._reboot_device(ip)
#                 if wait:
#                     time.sleep(60)
#                 return result.get("success", False), result.get("message", "")

#             # ========== Hostname & Domain ==========
#             elif command == "set_hostname":
#                 hostname = params.get("hostname", "")
#                 if not hostname:
#                     return False, "Hostname is required"
#                 result = self._set_hostname(ip, hostname)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_domain":
#                 domain = params.get("domain", "")
#                 if not domain:
#                     return False, "Domain is required"
#                 result = self._set_domain(ip, domain)
#                 return result.get("success", False), result.get("message", "")

#             # ========== Network Configuration ==========
#             elif command == "set_static_ip":
#                 ip_address = params.get("ip_address", "")
#                 subnet_mask = params.get("subnet_mask", "")
#                 gateway = params.get("gateway", "")
#                 dns1 = params.get("dns1", "8.8.8.8")
#                 dns2 = params.get("dns2", "8.8.4.4")
#                 adapter = params.get("adapter", "FEC1")
                
#                 if not ip_address or not subnet_mask or not gateway:
#                     return False, "IP address, subnet mask, and gateway are required"
                
#                 result = self._set_static_ip(ip, ip_address, subnet_mask, gateway, dns1, dns2, adapter)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "enable_dhcp":
#                 adapter = params.get("adapter", "FEC1")
#                 result = self._enable_dhcp(ip, adapter)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_ssh":
#                 enabled = params.get("enabled", False)
#                 result = self._set_ssh(ip, enabled)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_ping":
#                 enabled = params.get("enabled", False)
#                 result = self._set_ping(ip, enabled)
#                 return result.get("success", False), result.get("message", "")

#             # ========== Flex Mode ==========
#             elif command == "enable_flex_mode":
#                 result = self._set_flex_mode(ip, True)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "disable_flex_mode":
#                 result = self._set_flex_mode(ip, False)
#                 return result.get("success", False), result.get("message", "")

#             # ========== Power Settings ==========
#             elif command == "set_power_mode":
#                 mode = params.get("mode", "")
#                 if not mode:
#                     return False, "Mode is required"
#                 result = self._set_power_mode(ip, mode)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_occupancy_power":
#                 power_on = params.get("power_on")
#                 power_off = params.get("power_off")
#                 result = self._set_occupancy_power(ip, power_on, power_off)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_video_sync_power":
#                 power_on = params.get("power_on")
#                 power_off = params.get("power_off")
#                 timeout = params.get("timeout")
#                 result = self._set_video_sync_power(ip, power_on, power_off, timeout)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_power_schedule":
#                 day = params.get("day", "")
#                 enabled = params.get("enabled", False)
#                 on_time = params.get("on_time", "")
#                 off_time = params.get("off_time", "")
                
#                 if not day:
#                     return False, "Day is required"
                
#                 result = self._set_power_schedule(ip, day, enabled, on_time, off_time)
#                 return result.get("success", False), result.get("message", "")

#             # ========== Wireless Conferencing ==========
#             elif command == "enable_wireless_conferencing":
#                 result = self._set_wireless_conferencing_enabled(ip, True)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "disable_wireless_conferencing":
#                 result = self._set_wireless_conferencing_enabled(ip, False)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_wireless_conferencing_quality":
#                 quality = params.get("quality", "")
#                 if not quality:
#                     return False, "Quality is required"
#                 result = self._set_wireless_conferencing_quality(ip, quality)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_peripheral_volume":
#                 volume = params.get("volume", 50)
#                 result = self._set_peripheral_volume(ip, volume)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "mute_peripheral":
#                 result = self._mute_peripheral(ip)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "unmute_peripheral":
#                 result = self._unmute_peripheral(ip)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "hide_peripheral_status":
#                 result = self._hide_peripheral_status(ip)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "show_peripheral_status":
#                 result = self._show_peripheral_status(ip)
#                 return result.get("success", False), result.get("message", "")

#             # ========== Application Mode ==========
#             elif command == "set_application_mode":
#                 mode = params.get("mode", "")
#                 signage_provider = params.get("signage_provider", "None")
#                 signage_url = params.get("signage_url", "")
#                 if not mode:
#                     return False, "Mode is required"
#                 result = self._set_application_mode(ip, mode, signage_provider, signage_url)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_content_caching":
#                 mode = params.get("mode", "")
#                 if not mode:
#                     return False, "Mode is required"
#                 result = self._set_content_caching(ip, mode)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_system_mode":
#                 mode = params.get("mode", "")
#                 if not mode:
#                     return False, "Mode is required"
#                 result = self._set_system_mode(ip, mode)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "enable_canvas":
#                 result = self._set_canvas_enabled(ip, True)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "disable_canvas":
#                 result = self._set_canvas_enabled(ip, False)
#                 return result.get("success", False), result.get("message", "")

#             # ========== Connection Display ==========
#             elif command == "set_airmedia_connection_overlay":
#                 enabled = params.get("enabled", False)
#                 result = self._set_airmedia_connection_overlay(ip, enabled)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_connection_display_info":
#                 show = params.get("show", False)
#                 mode = params.get("mode")
#                 custom = params.get("custom")
#                 result = self._set_connection_display_info(ip, show, mode, custom)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_guest_connection_info":
#                 show = params.get("show", False)
#                 mode = params.get("mode")
#                 custom = params.get("custom")
#                 result = self._set_guest_connection_info(ip, show, mode, custom)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_connection_info_mode":
#                 mode = params.get("mode", "")
#                 custom = params.get("custom")
#                 if not mode:
#                     return False, "Mode is required"
#                 result = self._set_connection_info_mode(ip, mode, custom)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_connection_display_airplay":
#                 enabled = params.get("enabled", False)
#                 result = self._set_connection_display_airplay(ip, enabled)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_connection_display_miracast":
#                 enabled = params.get("enabled", False)
#                 result = self._set_connection_display_miracast(ip, enabled)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_connection_display_adaptor":
#                 enabled = params.get("enabled", False)
#                 result = self._set_connection_display_adaptor(ip, enabled)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_wired_connection_info":
#                 enabled = params.get("enabled", False)
#                 result = self._set_wired_connection_info(ip, enabled)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_wired_connection_details":
#                 enabled = params.get("enabled", False)
#                 result = self._set_wired_connection_details(ip, enabled)
#                 return result.get("success", False), result.get("message", "")

#             # ========== TX3 Pairing ==========
#             elif command == "start_pairing":
#                 result = self._start_pairing(ip)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "stop_pairing":
#                 result = self._stop_pairing(ip)
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_local_pairing_enabled":
#                 enabled = params.get("enabled")
#                 if enabled is None:
#                     return False, "Enabled state is required"
#                 result = self._set_local_pairing_enabled(ip, bool(enabled))
#                 return result.get("success", False), result.get("message", "")

#             elif command == "set_connect_adapter_behavior":
#                 behavior = params.get("behavior", "")
#                 if not behavior:
#                     return False, "Behavior is required"
#                 result = self._set_connect_adapter_behavior(ip, behavior)
#                 return result.get("success", False), result.get("message", "")

#             else:
#                 return False, f"Unknown command: {command}"

#         except Exception as e:
#             logger.error(f"[CrestronAirMedia] Command failed: {e}")
#             return False, str(e)

#     # ========== COMMAND IMPLEMENTATIONS ==========
    
#     def _reboot_device(self, ip):
#         """Reboot the device"""
#         try:
#             payload = {"Device": {"DeviceOperations": {"Reboot": True}}}
#             result = self._make_request(ip, "POST", "/Device/DeviceOperations/", data=payload)
#             if "error" in result:
#                 return {"success": False, "message": result["error"]}
#             return {"success": True, "message": "Reboot command sent successfully"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_hostname(self, ip, hostname: str) -> dict:
#         """Set device hostname"""
#         if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', hostname):
#             return {"success": False, "message": "Invalid hostname format"}
#         if len(hostname) > 63:
#             return {"success": False, "message": "Hostname too long. Max 63 characters"}
        
#         payload_eth = {"Device": {"Ethernet": {"HostName": hostname}}}
#         payload_net = {"Device": {"NetworkAdapters": {"HostName": hostname}}}
        
#         try:
#             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload_eth)
#             self._make_request(ip, "POST", "/Device/NetworkAdapters/", data=payload_net)
#             return {"success": True, "message": f"Hostname set to '{hostname}'"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_domain(self, ip, domain: str) -> dict:
#         """Set device domain"""
#         if domain and len(domain) > 127:
#             return {"success": False, "message": "Domain too long. Max 127 characters"}
        
#         payload = {"Device": {"Ethernet": {"DomainName": domain}}}
        
#         try:
#             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
#             return {"success": True, "message": f"Domain set to '{domain}'"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_static_ip(self, ip, ip_address: str, subnet_mask: str, gateway: str, 
#                        dns1: str = "8.8.8.8", dns2: str = "8.8.4.4", adapter: str = "FEC1") -> dict:
#         """Set static IP configuration"""
#         payload = {
#             "Device": {
#                 "Ethernet": {
#                     "Adapters": [{
#                         "Name": adapter,
#                         "IPv4": {
#                             "IsDhcpEnabled": False,
#                             "StaticAddresses": [{"Address": ip_address, "SubnetMask": subnet_mask}],
#                             "StaticDefaultGateway": gateway,
#                             "StaticDns": [dns1, dns2]
#                         }
#                     }]
#                 }
#             }
#         }
#         try:
#             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
#             return {"success": True, "message": f"Static IP {ip_address} configured"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _enable_dhcp(self, ip, adapter: str = "FEC1") -> dict:
#         """Enable DHCP"""
#         payload = {"Device": {"Ethernet": {"Adapters": [{"Name": adapter, "IPv4": {"IsDhcpEnabled": True}}]}}}
#         try:
#             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
#             return {"success": True, "message": "DHCP enabled"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_ssh(self, ip, enabled: bool) -> dict:
#         """Enable/disable SSH"""
#         payload_eth = {"Device": {"Ethernet": {"IsSshEnabled": enabled}}}
#         payload_comm = {"Device": {"CommunicationConfigurations": {"IsSshEnabled": enabled}}}
        
#         try:
#             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload_eth)
#             self._make_request(ip, "POST", "/Device/CommunicationConfigurations/", data=payload_comm)
#             state = "enabled" if enabled else "disabled"
#             return {"success": True, "message": f"SSH {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_ping(self, ip, enabled: bool) -> dict:
#         """Enable/disable ICMP ping"""
#         payload = {"Device": {"Ethernet": {"IsIcmpPingEnabled": enabled}}}
#         try:
#             self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
#             state = "enabled" if enabled else "disabled"
#             return {"success": True, "message": f"ICMP ping {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_flex_mode(self, ip, enabled: bool) -> dict:
#         """Set Flex Mode"""
#         payload = {"Device": {"App": {"Config": {"General": {"IsFlexModeEnabled": enabled}}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
#             state = "enabled" if enabled else "disabled"
#             return {"success": True, "message": f"Flex Mode {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_power_mode(self, ip, mode: str) -> dict:
#         """Set power control mode"""
#         valid_modes = ["AlwaysOn", "OccupancyBased", "OccupancyBasedWithSignage", "VideoSyncBased", "SignageOnly"]
        
#         if mode not in valid_modes:
#             return {"success": False, "message": f"Invalid mode: {mode}. Valid modes: {', '.join(valid_modes)}"}
        
#         payload = {
#             "Device": {
#                 "App": {
#                     "Config": {
#                         "General": {
#                             "PowerControlOptions": mode
#                         }
#                     }
#                 }
#             }
#         }
        
#         try:
#             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
#             time.sleep(1)
#             return {"success": True, "message": f"Power mode set successfully"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_occupancy_power(self, ip, power_on: bool = None, power_off: bool = None) -> dict:
#         """Set occupancy power settings"""
#         payload = {"Device": {"App": {"Config": {"General": {"OccupancyPowerSettings": {}}}}}}
#         if power_on is not None:
#             payload["Device"]["App"]["Config"]["General"]["OccupancyPowerSettings"]["PowerOnEnable"] = power_on
#         if power_off is not None:
#             payload["Device"]["App"]["Config"]["General"]["OccupancyPowerSettings"]["PowerOffEnable"] = power_off
        
#         try:
#             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
#             return {"success": True, "message": "Occupancy power settings updated"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_video_sync_power(self, ip, power_on: bool = None, power_off: bool = None, timeout: int = None) -> dict:
#         """Set video sync power settings"""
#         payload = {"Device": {"App": {"Config": {"General": {"VideoSyncPowerSettings": {}}}}}}
#         if power_on is not None:
#             payload["Device"]["App"]["Config"]["General"]["VideoSyncPowerSettings"]["PowerOnEnable"] = power_on
#         if power_off is not None:
#             payload["Device"]["App"]["Config"]["General"]["VideoSyncPowerSettings"]["PowerOffEnable"] = power_off
#         if timeout is not None:
#             if timeout < 1 or timeout > 120:
#                 return {"success": False, "message": "Timeout must be between 1 and 120 minutes"}
#             payload["Device"]["App"]["Config"]["General"]["VideoSyncPowerSettings"]["PowerOffTimeoutMinutes"] = timeout
        
#         try:
#             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
#             return {"success": True, "message": "Video sync power settings updated"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_power_schedule(self, ip, day: str, enabled: bool, on_time: str = "", off_time: str = "") -> dict:
#         """Set power schedule for a specific day"""
#         days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
#         day_cap = day.capitalize() if day else day
        
#         if day_cap not in days:
#             return {"success": False, "message": f"Invalid day. Must be one of: {', '.join(days)}"}
        
#         if not on_time or not off_time:
#             try:
#                 result = self._make_request(ip, "GET", "/Device/App/Config/")
#                 config = self._unwrap(result, "Device", "App", "Config") or {}
#                 general = config.get("General", {})
#                 power_schedule = general.get("PowerSchedule", {})
#                 existing = power_schedule.get(day_cap, {})
#                 on_time = on_time or existing.get("OnTime", "09:00")
#                 off_time = off_time or existing.get("OffTime", "17:00")
#             except:
#                 on_time = on_time or "09:00"
#                 off_time = off_time or "17:00"
        
#         payload = {
#             "Device": {
#                 "App": {
#                     "Config": {
#                         "General": {
#                             "PowerSchedule": {
#                                 day_cap: {
#                                     "IsEnabled": enabled,
#                                     "OnTime": on_time,
#                                     "OffTime": off_time
#                                 }
#                             }
#                         }
#                     }
#                 }
#             }
#         }
#         try:
#             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
#             return {"success": True, "message": f"Schedule for {day_cap} updated"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_wireless_conferencing_enabled(self, ip, enabled: bool) -> dict:
#         """Set wireless conferencing enabled state"""
#         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"IsEnabled": enabled}}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             state = "enabled" if enabled else "disabled"
#             return {"success": True, "message": f"Wireless conferencing {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_wireless_conferencing_quality(self, ip, quality: str) -> dict:
#         """Set wireless conferencing quality"""
#         if quality not in ['Normal', 'Low']:
#             return {"success": False, "message": "Quality must be 'Normal' or 'Low'"}
        
#         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"QualityMode": quality}}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": f"Quality set to '{quality}'"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_peripheral_volume(self, ip, volume: int) -> dict:
#         """Set peripheral volume"""
#         if volume < 0 or volume > 100:
#             return {"success": False, "message": "Volume must be between 0 and 100"}
        
#         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"PeripheralVolume": volume}}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": f"Volume set to {volume}%"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _mute_peripheral(self, ip) -> dict:
#         """Mute peripheral audio"""
#         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"PeripheralMute": True}}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": "Audio muted"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _unmute_peripheral(self, ip) -> dict:
#         """Unmute peripheral audio"""
#         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"PeripheralMute": False}}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": "Audio unmuted"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _hide_peripheral_status(self, ip) -> dict:
#         """Hide peripheral status"""
#         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"IsPeripheralStatusHidden": True}}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": "Peripheral status hidden"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _show_peripheral_status(self, ip) -> dict:
#         """Show peripheral status"""
#         payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"IsPeripheralStatusHidden": False}}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": "Peripheral status shown"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_system_mode(self, ip, mode: str) -> dict:
#         """Set system mode"""
#         valid = ["OptimizedForVideoQuality", "OptimizedForMultiplePresentations"]
#         if mode not in valid:
#             return {"success": False, "message": f"Invalid mode. Must be one of: {', '.join(valid)}"}
        
#         payload = {"Device": {"AirMedia": {"SystemMode": mode}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": f"System mode set to '{mode}'"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_canvas_enabled(self, ip, enabled: bool) -> dict:
#         """Set Canvas enabled state"""
#         payload = {"Device": {"AirMedia": {"IsCanvasEnabled": enabled}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             state = "enabled" if enabled else "disabled"
#             return {"success": True, "message": f"Canvas {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_application_mode(self, ip, mode: str, signage_provider: str = "None", signage_url: str = "") -> dict:
#         """Set application mode and signage provider"""
#         try:
#             payload = {
#                 "Device": {
#                     "App": {
#                         "Config": {
#                             "General": {
#                                 "ApplicationMode": mode,
#                                 "SignageProvider": signage_provider
#                             }
#                         }
#                     }
#                 }
#             }
            
#             if signage_url:
#                 payload["Device"]["App"]["Config"]["General"]["SignageUrl"] = signage_url
            
#             result = self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
            
#             if "error" in result:
#                 alt_payload = {
#                     "Device": {
#                         "AirMedia": {
#                             "ApplicationMode": mode,
#                             "SignageProvider": signage_provider
#                         }
#                     }
#                 }
#                 result = self._make_request(ip, "POST", "/Device/AirMedia/", data=alt_payload)
            
#             if "error" in result:
#                 return {"success": False, "message": result.get("error", "Failed to set application mode")}
            
#             return {"success": True, "message": f"Application mode set to '{mode}' with {signage_provider}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_content_caching(self, ip, mode: str) -> dict:
#         """Set content caching mode for signage"""
#         valid_modes = ["SignageAsBackground", "SignageInStandby", "BothBackgroundAndStandby"]
#         if mode not in valid_modes:
#             return {"success": False, "message": f"Invalid mode. Must be one of: {', '.join(valid_modes)}"}
        
#         payload = {
#             "Device": {
#                 "App": {
#                     "Config": {
#                         "General": {
#                             "ContentCaching": mode
#                         }
#                     }
#                 }
#             }
#         }
#         try:
#             self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
#             return {"success": True, "message": f"Content caching set to '{mode}'"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_airmedia_connection_overlay(self, ip, enabled: bool) -> dict:
#         """Show/hide AirMedia connection info overlay"""
#         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowAirMediaOverlay": enabled}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             state = "shown" if enabled else "hidden"
#             return {"success": True, "message": f"AirMedia overlay {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_connection_display_info(self, ip, show: bool, mode: str = None, custom: str = None) -> dict:
#         """Set primary connection display info"""
#         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {}}}}
#         payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ShowConnectionInfo"] = show
        
#         if mode:
#             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ConnectionInfoMode"] = mode
        
#         if custom and mode == "Custom":
#             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["CustomString"] = custom
        
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": "Primary connection display updated"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_guest_connection_info(self, ip, show: bool, mode: str = None, custom: str = None) -> dict:
#         """Set guest connection info"""
#         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {}}}}
#         payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ShowGuestConnectionInfo"] = show
        
#         if mode:
#             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["GuestInfoMode"] = mode
        
#         if custom and mode == "Custom":
#             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["GuestCustomString"] = custom
        
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": "Guest connection info updated"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_connection_info_mode(self, ip, mode: str, custom: str = None) -> dict:
#         """Set connection info display mode"""
#         valid = ["IPAddress", "Host", "HostAndDomain", "Custom"]
#         if mode not in valid:
#             return {"success": False, "message": f"Invalid mode. Must be one of: {', '.join(valid)}"}
        
#         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {}}}}
#         payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ConnectionInfoMode"] = mode
        
#         if custom and mode == "Custom":
#             payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ConnectionCustomString"] = custom
        
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             return {"success": True, "message": f"Connection info mode set to '{mode}'"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_connection_display_airplay(self, ip, enabled: bool) -> dict:
#         """Show/hide Apple Screen Mirroring info"""
#         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowAirplayInfo": enabled}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             state = "shown" if enabled else "hidden"
#             return {"success": True, "message": f"Apple Screen Mirroring info {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_connection_display_miracast(self, ip, enabled: bool) -> dict:
#         """Show/hide Miracast info"""
#         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowMiracastInfo": enabled}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             state = "shown" if enabled else "hidden"
#             return {"success": True, "message": f"Miracast info {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_connection_display_adaptor(self, ip, enabled: bool) -> dict:
#         """Show/hide Connect Adaptor info"""
#         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowConnectAdaptorInfo": enabled}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             state = "shown" if enabled else "hidden"
#             return {"success": True, "message": f"Connect Adaptor info {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_wired_connection_info(self, ip, enabled: bool) -> dict:
#         """Show/hide wired connection info"""
#         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowWiredConnectionInfo": enabled}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             state = "shown" if enabled else "hidden"
#             return {"success": True, "message": f"Wired connection info {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_wired_connection_details(self, ip, enabled: bool) -> dict:
#         """Show/hide wired connection details"""
#         payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowWiredConnectionDetails": enabled}}}}
#         try:
#             self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
#             state = "shown" if enabled else "hidden"
#             return {"success": True, "message": f"Wired connection details {state}"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _start_pairing(self, ip) -> dict:
#         """Start TX3 device pairing"""
#         try:
#             payload = {"Device": {"AirMediaTx3": {"PairCmd": True}}}
#             result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
#             if "error" not in result:
#                 return {"success": True, "message": "Pairing mode started for 60 seconds", "pairing_status": "In Progress"}
#             return {"success": False, "message": "Could not start pairing mode"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _stop_pairing(self, ip) -> dict:
#         """Stop TX3 device pairing mode"""
#         try:
#             payload = {"Device": {"AirMediaTx3": {"PairCmd": False}}}
#             result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
#             if "error" not in result:
#                 return {"success": True, "message": "Pairing mode stopped", "pairing_status": "Not Started"}
#             return {"success": False, "message": "Could not stop pairing mode"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_local_pairing_enabled(self, ip, enabled: bool) -> dict:
#         """Enable or disable local pairing for TX3 devices"""
#         payload = {"Device": {"AirMediaTx3": {"IsLocalPairingEnabled": enabled}}}
#         try:
#             result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
#             if "error" not in result:
#                 return {"success": True, "message": f"Local pairing {'enabled' if enabled else 'disabled'}"}
#             return {"success": False, "message": "Could not update local pairing"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     def _set_connect_adapter_behavior(self, ip, behavior: str) -> dict:
#         """Set connect adapter behavior for TX3 devices"""
#         valid_behaviors = ["AutoPresentAndAutoConference", "AutoPresent", "AutoConference"]
        
#         if behavior not in valid_behaviors:
#             return {"success": False, "message": f"Invalid behavior. Must be one of: {', '.join(valid_behaviors)}"}
        
#         try:
#             payload = {"Device": {"AirMediaTx3": {"ConnectAdapterBehavior": behavior}}}
#             result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
            
#             if "error" not in result:
#                 return {"success": True, "message": f"Connect adapter behavior set to '{behavior}'"}
            
#             # Try alternative spelling
#             alt_payload = {"Device": {"AirMedia": {"ConnectAdapterBehavior": behavior}}}
#             alt_result = self._make_request(ip, "POST", "/Device/AirMedia/", data=alt_payload)
            
#             if "error" not in alt_result:
#                 return {"success": True, "message": f"Connect adapter behavior set to '{behavior}'"}
            
#             return {"success": False, "message": "Failed to set connect adapter behavior"}
#         except Exception as e:
#             return {"success": False, "message": str(e)}


# def get_plugin(config=None):
#     """Factory function to create plugin instance."""
#     return CrestronAirMediaPlugin(config)

"""
crestron_airmedia_plugin.py - Crestron AirMedia Series 3 Plugin for Edge Collector
"""

import json
import time
import re
import requests
import logging
from typing import Optional, Dict, Any, List

from .base import ManualPlatformPlugin
from .crestron_firmware_mixin import CrestronFirmwareMixin

logger = logging.getLogger(__name__)

urllib3 = None
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass


class CrestronAirMediaPlugin(ManualPlatformPlugin, CrestronFirmwareMixin):
    """Crestron AirMedia Series 3 Plugin for Edge Collector."""

    name = "crestron_airmedia"
    display_name = "Crestron AirMedia Series 3"
    description = "Crestron AirMedia Series 3 with full control capabilities"
    supports_display_id = False
    supports_port = False
    default_port = 443
    
    SUPPORTED_MODELS = [
        "AM-3000-WF-I",
        "AM-3200",
        "AM-3200-WF",
        "AM-3200-WF-I",
        "AirMedia Series 3",
        "AM-TX3-100-I",
    ]

    SUPPORTED_FIRMWARE_MODELS = {
        "AM-3000-WF-I": {"extensions": [".puf"]},
        "AM-3200": {"extensions": [".puf"]},
        "AM-3200-WF": {"extensions": [".puf"]},
        "AM-3200-WF-I": {"extensions": [".puf"]},
        "AirMedia Series 3": {"extensions": [".puf"]},
        "AM-TX3-100-I": {"extensions": [".puf"]},
    }

    def __init__(self, config=None):
        super().__init__(config)
        self.username = self.config.get("username") if self.config else None
        self.password = self.config.get("password") if self.config else None
        self._xsrf_token = None
        self._session = None
        self._authenticated = False
        logger.info(f"[CrestronAirMedia] Initialized")

    def _login(self, ip):
        """Authenticate with the Crestron AirMedia device"""
        if not self.username or not self.password:
            raise Exception("MISSING_CREDENTIALS: Username and password are required")
        
        base_url = f"https://{ip}"
        login_url = f"{base_url}/userlogin.html"
        
        if self._session:
            self._session.close()
        
        session = requests.Session()
        session.verify = False
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        self._xsrf_token = None
        self._authenticated = False

        try:
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

            payload = f"login={self.username}&&passwd={self.password}"
            login_response = session.post(
                login_url,
                headers=login_headers,
                data=payload,
                timeout=10,
            )

            if login_response.status_code == 403:
                raise Exception("Login failed - incorrect username or password")
            if login_response.status_code != 200:
                raise Exception(f"LOGIN_FAILED: Login failed with HTTP {login_response.status_code}")

            self._xsrf_token = login_response.headers.get("CREST-XSRF-TOKEN")
            if self._xsrf_token:
                session.headers.update({
                    "CREST-XSRF-TOKEN": self._xsrf_token,
                    "X-CREST-XSRF-TOKEN": self._xsrf_token,
                })

            self._session = session
            self._authenticated = True
            logger.info(f"[CrestronAirMedia] Login successful for {ip}")
            return session
            
        except requests.exceptions.ConnectTimeout:
            raise Exception("DEVICE_OFFLINE: Connection timeout - device is not responding")
        except requests.exceptions.ConnectionError:
            raise Exception("DEVICE_OFFLINE: Connection refused - device is offline or unreachable")
        except requests.exceptions.Timeout:
            raise Exception("DEVICE_OFFLINE: Request timed out - device is not responding")
        except Exception as e:
            # Re-raise with the specific error message
            if "INVALID_CREDENTIALS" in str(e) or "LOGIN_FAILED" in str(e):
                raise
            raise Exception(f"CONNECTION_ERROR: {str(e)}")

    def _make_request(self, ip, method: str, endpoint: str, data: dict = None, timeout: int = None) -> dict:
        """Make an authenticated API request"""
        try:
            if not self._authenticated or not self._session:
                self._login(ip)

            url = f"https://{ip}{endpoint}"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
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
                # Re-login and try once more
                self._login(ip)
                response = _do_request()

            if response.status_code not in (200, 204):
                return {
                    "error": f"HTTP {response.status_code}",
                    "message": response.text[:300],
                    "status_code": response.status_code
                }

            if not response.content or not response.content.strip():
                return {}

            try:
                return response.json()
            except ValueError:
                return {"_raw": response.text.strip()}

        except requests.exceptions.ConnectTimeout:
            return {"error": "DEVICE_OFFLINE", "message": "Connection timeout - device is not responding"}
        except requests.exceptions.ConnectionError:
            return {"error": "DEVICE_OFFLINE", "message": "Connection refused - device is offline or unreachable"}
        except requests.exceptions.Timeout:
            return {"error": "DEVICE_OFFLINE", "message": "Request timed out - device is not responding"}
        except Exception as e:
            error_msg = str(e)
            # Extract the error type from the exception message
            if "DEVICE_OFFLINE" in error_msg:
                return {"error": "DEVICE_OFFLINE", "message": error_msg}
            elif "INVALID_CREDENTIALS" in error_msg:
                return {"error": "INVALID_CREDENTIALS", "message": error_msg}
            elif "LOGIN_FAILED" in error_msg:
                return {"error": "LOGIN_FAILED", "message": error_msg}
            elif "MISSING_CREDENTIALS" in error_msg:
                return {"error": "MISSING_CREDENTIALS", "message": error_msg}
            else:
                return {"error": "CONNECTION_ERROR", "message": error_msg}

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

    # ========== DEVICE INFO ==========
    
    def get_device_info(self, ip, port=443, display_id=None) -> dict:
        """Get device information"""
        if not self.username or not self.password:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "AirMedia Series 3",
                "current_status": "Offline",
                "error": "MISSING_CREDENTIALS: Username and password are required."
            }

        try:
            result = self._make_request(ip, "GET", "/Device/DeviceInfo/")
            
            # Check for error in result
            if "error" in result:
                error_type = result.get("error", "UNKNOWN_ERROR")
                error_msg = result.get("message", "Unknown error")
                
                return {
                    "ip_address": ip,
                    "port": port,
                    "display_id": display_id,
                    "make": "Crestron",
                    "device_type": "AirMedia Series 3",
                    "current_status": "Offline",
                    "error": f"{error_type}: {error_msg}",
                    "error_type": error_type
                }
            
            device_info = self._unwrap(result, "Device", "DeviceInfo") or {}
            
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": device_info.get("Manufacturer", "Crestron"),
                "device_name": device_info.get("Name", "AirMedia"),
                "model": device_info.get("Model", "AM-3200"),
                "serial_number": device_info.get("SerialNumber", "Unknown"),
                "mac_address": device_info.get("MacAddress", "Unknown"),
                "firmware": device_info.get("DeviceVersion", "Unknown"),
                "build_date": device_info.get("BuildDate", ""),
                "device_id": device_info.get("DeviceId", ""),
                "device_type": "Crestron AirMedia Series 3",
                "category": device_info.get("Category", "Wireless Presentation"),
                "reboot_reason": device_info.get("RebootReason", "Unknown"),
                "current_status": "Online",
            }
        except Exception as e:
            logger.error(f"[CrestronAirMedia] get_device_info failed: {e}")
            error_msg = str(e)
            
            if "INVALID_CREDENTIALS" in error_msg:
                error_type = "INVALID_CREDENTIALS"
            elif "DEVICE_OFFLINE" in error_msg:
                error_type = "DEVICE_OFFLINE"
            else:
                error_type = "UNKNOWN_ERROR"
                
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "AirMedia Series 3",
                "current_status": "Offline",
                "error": f"{error_type}: {error_msg}",
                "error_type": error_type
            }

    # ========== AIRMEDIA STATUS ==========
    
    def get_airmedia_status(self, ip, port=443, display_id=None) -> dict:
        """Get AirMedia status"""
        try:
            result = self._make_request(ip, "GET", "/Device/AirMedia/")
            am = self._unwrap(result, "Device", "AirMedia") or {}
            
            return {
                "is_enabled": am.get("IsEnabled", False),
                "login_code_mode": am.get("LoginCodeMode", "Unknown"),
                "active_login_code": am.get("ActiveLoginCode", "None"),
                "show_login_code": am.get("ShowLoginCode", False),
                "system_mode": am.get("SystemMode", "OptimizedForMultiplePresentations"),
                "is_canvas_enabled": am.get("IsCanvasEnabled", False),
                "canvas_options": am.get("CanvasOptions", "AllSources"),
                "is_web_download_enabled": am.get("IsWebApplicationDownloadEnabled", False),
            }
        except Exception as e:
            logger.error(f"[CrestronAirMedia] get_airmedia_status failed: {e}")
            return {"error": str(e)}

    # ========== NETWORK CONFIGURATION ==========
    
    def get_network_config(self, ip, port=443, display_id=None) -> dict:
        """Get network configuration"""
        try:
            result = self._make_request(ip, "GET", "/Device/Ethernet/")
            eth = self._unwrap(result, "Device", "Ethernet") or {}
            comm = self._make_request(ip, "GET", "/Device/CommunicationConfigurations/")
            comm_data = self._unwrap(comm, "Device", "CommunicationConfigurations") or {}
            
            network_info = {
                "hostname": eth.get("HostName", ""),
                "domain_name": eth.get("DomainName", ""),
                "ssh_enabled": comm_data.get("IsSshEnabled", False),
                "icmp_ping_enabled": eth.get("IsIcmpPingEnabled", False),
                "auto_negotiation": eth.get("AutoNegotiationEnabled", True),
                "igmp_version": eth.get("IgmpVersion", "v2"),
                "adapters": []
            }
            
            for adapter in eth.get("Adapters", []):
                ipv4 = adapter.get("IPv4", {})
                addresses = ipv4.get("Addresses", [])
                
                network_info["adapters"].append({
                    "name": adapter.get("Name", "Unknown"),
                    "internal_name": adapter.get("InternalName", ""),
                    "mac_address": adapter.get("MacAddress", ""),
                    "link_status": adapter.get("LinkStatus", False),
                    "enabled": adapter.get("IsAdapterEnabled", True),
                    "dhcp_enabled": ipv4.get("IsDhcpEnabled", True),
                    "ip_address": addresses[0].get("Address", "") if addresses else "",
                    "subnet_mask": addresses[0].get("SubnetMask", "") if addresses else "",
                    "default_gateway": ipv4.get("DefaultGateway", ""),
                    "dns_servers": ipv4.get("DnsServers", []),
                })
            
            # Get current IP for quick access
            current_ip = ip
            for adapter in network_info["adapters"]:
                if adapter.get("ip_address"):
                    current_ip = adapter.get("ip_address")
                    break
            
            network_info["current_ip"] = current_ip
            
            return network_info
        except Exception as e:
            logger.error(f"[CrestronAirMedia] get_network_config failed: {e}")
            return {"error": str(e), "current_ip": ip}

    # ========== POWER SETTINGS ==========
    
    def get_power_settings(self, ip, port=443, display_id=None) -> dict:
        """Get power settings"""
        try:
            result = self._make_request(ip, "GET", "/Device/App/Config/")
            config = self._unwrap(result, "Device", "App", "Config") or {}
            general = config.get("General", {})
            
            raw_power_mode = general.get("PowerControlOptions", "AlwaysOn")
            
            power_schedule = general.get("PowerSchedule", {})
            formatted_schedule = {}
            
            days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            
            for day in days:
                if day in power_schedule:
                    schedule = power_schedule[day]
                    formatted_schedule[day] = {
                        "IsEnabled": schedule.get("IsEnabled", False),
                        "OnTime": schedule.get("OnTime", ""),
                        "OffTime": schedule.get("OffTime", "")
                    }
                else:
                    formatted_schedule[day] = {
                        "IsEnabled": False,
                        "OnTime": "",
                        "OffTime": ""
                    }
            
            return {
                "power_control_options": raw_power_mode,
                "is_flex_mode_enabled": general.get("IsFlexModeEnabled", False),
                "occupancy_power_on": general.get("OccupancyPowerSettings", {}).get("PowerOnEnable", False),
                "occupancy_power_off": general.get("OccupancyPowerSettings", {}).get("PowerOffEnable", False),
                "video_sync_power_on": general.get("VideoSyncPowerSettings", {}).get("PowerOnEnable", False),
                "video_sync_power_off": general.get("VideoSyncPowerSettings", {}).get("PowerOffEnable", False),
                "video_sync_timeout": general.get("VideoSyncPowerSettings", {}).get("PowerOffTimeoutMinutes", 1),
                "power_schedule": formatted_schedule,
                "flex_mode_enabled": general.get("IsFlexModeEnabled", False),
            }
        except Exception as e:
            logger.error(f"[CrestronAirMedia] get_power_settings failed: {e}")
            return {"error": str(e)}

    # ========== WIRELESS CONFERENCING ==========
    
    def get_wireless_conferencing(self, ip, port=443, display_id=None) -> dict:
        """Get wireless conferencing status"""
        try:
            result = self._make_request(ip, "GET", "/Device/AirMedia/")
            am = self._unwrap(result, "Device", "AirMedia") or {}
            wc = am.get("WirelessConferencing", {})
            config = wc.get("Configuration", {})
            status = wc.get("Status", {})
            
            return {
                "enabled": config.get("IsEnabled", False),
                "quality": config.get("QualityMode", "Normal"),
                "hide_status": config.get("IsPeripheralStatusHidden", False),
                "volume": config.get("PeripheralVolume", 89),
                "muted": config.get("PeripheralMute", False),
                "privacy_enabled": config.get("IsPrivacyEnabled", False),
                "conference_status": status.get("ConferencingStatus", "Unavailable"),
                "mic_detected": status.get("IsMicDetected", False),
                "mic_model": status.get("MicModel", ""),
                "mic_in_use": status.get("IsMicInUse", False),
                "camera_detected": status.get("IsCameraDetected", False),
                "camera_model": status.get("CameraModel", ""),
                "camera_resolution": status.get("CameraResolution", ""),
                "speaker_detected": status.get("IsSpeakerDetected", False),
                "speaker_model": status.get("SpeakerModel", ""),
            }
        except Exception as e:
            logger.error(f"[CrestronAirMedia] get_wireless_conferencing failed: {e}")
            return {"error": str(e)}

    # ========== APPLICATION MODE ==========
    
    def get_application_mode(self, ip, port=443, display_id=None) -> dict:
        """Get application mode settings"""
        try:
            result = self._make_request(ip, "GET", "/Device/App/Config/")
            config = self._unwrap(result, "Device", "App", "Config") or {}
            general = config.get("General", {})
            
            application_mode = general.get("ApplicationMode", "AirMediaExperience")
            signage_provider = general.get("SignageProvider", "None")
            signage_url = general.get("SignageUrl", "")
            content_caching = general.get("ContentCaching", "SignageAsBackground")
            
            return {
                "application_mode": application_mode,
                "signage_provider": signage_provider,
                "signage_url": signage_url,
                "content_caching": content_caching,
                "system_mode": general.get("SystemMode", "OptimizedForMultiplePresentations"),
                "canvas_enabled": general.get("IsCanvasEnabled", False),
                "canvas_options": general.get("CanvasOptions", "AllSources"),
                "web_download_enabled": general.get("IsWebApplicationDownloadEnabled", False),
                "flex_mode_enabled": general.get("IsFlexModeEnabled", False),
            }
        except Exception as e:
            logger.error(f"[CrestronAirMedia] get_application_mode failed: {e}")
            return {"error": str(e)}

    # ========== CONNECTION DISPLAY ==========
    
    def get_connection_display(self, ip, port=443, display_id=None) -> dict:
        """Get connection display options"""
        try:
            result = self._make_request(ip, "GET", "/Device/AirMedia/")
            am = self._unwrap(result, "Device", "AirMedia") or {}
            display = am.get("ConnectionDisplayOptions", {})
            
            return {
                "show_airmedia_overlay": display.get("ShowAirMediaOverlay", False) or display.get("ShowAirMediaConnectionInfoOverlay", False),
                "show_connection_info": display.get("ShowConnectionInfo", False),
                "connection_info_mode": display.get("ConnectionInfoMode", "IPAddress"),
                "custom_url": display.get("CustomString", ""),
                "show_guest_connection_info": display.get("ShowGuestConnectionInfo", False),
                "guest_info_mode": display.get("GuestInfoMode", "Internal"),
                "guest_custom_url": display.get("GuestCustomString", ""),
                "show_airplay": display.get("ShowAirplayInfo", False),
                "show_miracast": display.get("ShowMiracastInfo", False),
                "show_connect_adaptor": display.get("ShowConnectAdaptorInfo", False) or display.get("ShowConnectAdapterInfo", False),
                "show_wired_connection": display.get("ShowWiredConnectionInfo", False),
                "show_wired_details": display.get("ShowWiredConnectionDetails", False),
            }
        except Exception as e:
            logger.error(f"[CrestronAirMedia] get_connection_display failed: {e}")
            return {"error": str(e)}

    # ========== PAIRED DEVICES ==========
    
    def get_paired_devices(self, ip, port=443, display_id=None) -> dict:
        """Get paired TX3 devices"""
        try:
            devices_list = []
            tx3_root = {}
            
            result = self._make_request(ip, "GET", "/Device/AirMediaTx3/")
            
            if result and isinstance(result, dict) and "error" not in result:
                tx3_root = self._unwrap(result, "Device", "AirMediaTx3") or result.get("AirMediaTx3", {})
                devices_map = tx3_root.get("Tx3DevicesMap") or tx3_root.get("Devices", {})
                
                if isinstance(devices_map, dict):
                    for device_id, device in devices_map.items():
                        if isinstance(device, dict):
                            parsed_device = self._parse_tx3_device(device_id, device)
                            devices_list.append(parsed_device)
                elif isinstance(devices_map, list):
                    for device in devices_map:
                        if isinstance(device, dict):
                            device_id = device.get("Id") or device.get("DeviceId") or device.get("MAC", "")
                            parsed_device = self._parse_tx3_device(device_id, device)
                            devices_list.append(parsed_device)
            
            # Get pairing status
            pairing_status = "Not Started"
            try:
                status_result = self._make_request(ip, "GET", "/Device/AirMediaTx3/PairingStatus")
                pairing_status = self._extract_pairing_status(status_result)
            except:
                pass

            connect_adapter_behavior = (
                tx3_root.get("ConnectAdapterBehavior")
                or tx3_root.get("ConnectAdaptorBehavior")
                or "AutoPresentAndAutoConference"
            )
            
            local_pairing_enabled = self._extract_local_pairing_enabled(tx3_root)
            
            return {
                "paired_devices": devices_list,
                "count": len(devices_list),
                "pairing_status": pairing_status,
                "local_pairing_enabled": local_pairing_enabled,
                "connect_adapter_behavior": connect_adapter_behavior,
            }
        except Exception as e:
            logger.error(f"[CrestronAirMedia] get_paired_devices failed: {e}")
            return {
                "paired_devices": [],
                "count": 0,
                "pairing_status": "Not Started",
                "local_pairing_enabled": False,
                "connect_adapter_behavior": "AutoPresentAndAutoConference",
                "error": str(e),
            }

    def _parse_tx3_device(self, device_id: str, device: dict) -> dict:
        """Parse a TX3 device into standardized format"""
        nickname = (
            device.get("Nickname") or 
            device.get("FriendlyName") or 
            device.get("Name") or 
            device.get("DeviceName") or
            device.get("displayName")
        )
        
        if not nickname:
            mac = device.get("MacAddress") or device.get("MAC") or device.get("Mac")
            if mac and len(str(mac)) > 8:
                nickname = f"AirMedia TX3-{str(mac)[-8:].replace(':', '')}"
            else:
                nickname = "AirMedia TX3"
        
        serial = device.get("SerialNumber") or device.get("Serial") or "N/A"
        if isinstance(serial, str):
            serial = serial.replace('\n', '').strip()
            if not serial:
                serial = "N/A"
        
        status = device.get("Status") or device.get("ConnectionStatus") or device.get("State") or "Unknown"
        status_lower = str(status).lower()
        if status_lower in ["online", "connected", "active"]:
            display_status = "Online"
        elif status_lower in ["offline", "disconnected", "inactive"]:
            display_status = "Offline"
        elif status_lower in ["pairing", "pair"]:
            display_status = "Pairing"
        else:
            display_status = str(status) if status else "Unknown"
        
        signal = device.get("SignalStrengthPercentage") or device.get("SignalStrength") or device.get("Signal") or 0
        if isinstance(signal, (int, float)):
            signal = int(signal)
        else:
            try:
                signal = int(signal)
            except:
                signal = 0
        
        firmware = device.get("FirmwareVersion") or device.get("Firmware") or device.get("Version") or "Unknown"
        mac = device.get("MacAddress") or device.get("MAC") or device.get("Mac") or "N/A"
        model = device.get("ModelNumber") or device.get("Model") or device.get("Product") or "AM-TX3-100-I"
        
        return {
            "id": device_id,
            "nickname": nickname,
            "model_number": model,
            "status": display_status,
            "serial_number": serial,
            "mac_address": str(mac) if mac else "N/A",
            "firmware_version": firmware,
            "signal": signal,
            "connection_method": device.get("ConnectionMethod", "WiFi Direct"),
            "is_online": display_status == "Online",
        }

    def _extract_pairing_status(self, status_result) -> str:
        """Normalize pairing status from API response"""
        if not status_result:
            return "Not Started"
        if isinstance(status_result, str):
            return status_result
        if not isinstance(status_result, dict):
            return "Not Started"
        nested_status = (
            status_result.get("Status")
            or status_result.get("status")
            or self._unwrap(status_result, "Device", "AirMediaTx3", "PairingStatus", "Status")
            or self._unwrap(status_result, "Device", "AirMediaTx3", "PairingStatus")
            or self._unwrap(status_result, "Device", "AirMediaTx3", "Status")
        )
        return nested_status or "Not Started"

    def _extract_local_pairing_enabled(self, tx3_root: dict) -> bool:
        """Read local pairing state from TX3 settings"""
        if not isinstance(tx3_root, dict):
            tx3_root = {}
        for key in ("LocalPairingEnabled", "IsLocalPairingEnabled", "IsPairingEnabled", "PairingEnabled"):
            value = tx3_root.get(key)
            if isinstance(value, bool):
                return value
        return False

    # ========== CONNECTED CLIENTS ==========
    
    def get_connected_clients(self, ip, port=443, display_id=None) -> dict:
        """Get connected AirMedia clients"""
        try:
            result = self._make_request(ip, "GET", "/Device/AirMedia/ClientData/")
            data = self._unwrap(result, "Device", "AirMedia", "ClientData") or {}
            
            return {
                "total_users": data.get("TotalUsers", 0),
                "status": data.get("Status", "Idle"),
                "connected_clients": data.get("ConnectedClients", {}),
            }
        except Exception as e:
            logger.error(f"[CrestronAirMedia] get_connected_clients failed: {e}")
            return {"error": str(e)}

    # ========== FULL STATUS ==========
    
    def query_status(self, ip, port=443, display_id=None) -> dict:
        """Query device status for polling - returns full device data"""
        try:
            logger.info(f"[CrestronAirMedia] query_status called for {ip}")
            
            device_info = self.get_device_info(ip, port, display_id)
            
            # Check for errors in device_info
            if device_info.get("error"):
                error_msg = device_info["error"]
                
                # Determine the specific error type
                if "INVALID_CREDENTIALS" in error_msg or "LOGIN_FAILED" in error_msg:
                    return {
                        "reachable": False,
                        "power": "OFF",
                        "error": "INVALID_CREDENTIALS",
                        "error_message": "Invalid username or password. Please check your credentials.",
                        "device_info": device_info,
                        "network_config": {"current_ip": ip},
                        "timestamp": time.time()
                    }
                elif "MISSING_CREDENTIALS" in error_msg:
                    return {
                        "reachable": False,
                        "power": "OFF",
                        "error": "MISSING_CREDENTIALS",
                        "error_message": "Username and password are required to connect to this device.",
                        "device_info": device_info,
                        "network_config": {"current_ip": ip},
                        "timestamp": time.time()
                    }
                elif "DEVICE_OFFLINE" in error_msg or "CONNECTION_ERROR" in error_msg:
                    return {
                        "reachable": False,
                        "power": "OFF",
                        "error": "DEVICE_OFFLINE",
                        "error_message": "Device is offline or unreachable. Please check the network connection.",
                        "device_info": device_info,
                        "network_config": {"current_ip": ip},
                        "timestamp": time.time()
                    }
                else:
                    return {
                        "reachable": False,
                        "power": "OFF",
                        "error": "UNKNOWN_ERROR",
                        "error_message": error_msg,
                        "device_info": device_info,
                        "network_config": {"current_ip": ip},
                        "timestamp": time.time()
                    }
            
            # If device_info has no error, continue with other status checks
            airmedia = self.get_airmedia_status(ip, port, display_id)
            network = self.get_network_config(ip, port, display_id)
            power = self.get_power_settings(ip, port, display_id)
            wc = self.get_wireless_conferencing(ip, port, display_id)
            app_mode = self.get_application_mode(ip, port, display_id)
            conn_display = self.get_connection_display(ip, port, display_id)
            paired = self.get_paired_devices(ip, port, display_id)
            clients = self.get_connected_clients(ip, port, display_id)
            
            reachable = device_info.get("current_status") == "Online"
            
            return {
                "reachable": reachable,
                "power": "ON" if reachable else "OFF",
                "device_name": device_info.get("device_name"),
                "model": device_info.get("model"),
                "serial_number": device_info.get("serial_number"),
                "firmware": device_info.get("firmware"),
                "hostname": network.get("hostname", "") if isinstance(network, dict) else "",
                "current_ip": network.get("current_ip", ip) if isinstance(network, dict) else ip,
                "mac_address": device_info.get("mac_address"),
                "ssh_enabled": network.get("ssh_enabled", False) if isinstance(network, dict) else False,
                "airmedia_enabled": airmedia.get("is_enabled", False) if isinstance(airmedia, dict) else False,
                "flex_mode_enabled": power.get("is_flex_mode_enabled", False) if isinstance(power, dict) else False,
                "wireless_conferencing_enabled": wc.get("enabled", False) if isinstance(wc, dict) else False,
                
                # Full structured data for frontend
                "device_info": device_info,
                "airmedia_status": airmedia,
                "network_config": network,
                "power_settings": power,
                "wireless_conferencing": wc,
                "application_mode": app_mode,
                "connection_display": conn_display,
                "paired_devices": paired,
                "connected_clients": clients,
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"[CrestronAirMedia] query_status failed: {e}")
            error_msg = str(e)
            
            if "INVALID_CREDENTIALS" in error_msg:
                return {
                    "reachable": False,
                    "power": "OFF",
                    "error": "INVALID_CREDENTIALS",
                    "error_message": "Invalid username or password. Please check your credentials.",
                    "device_info": {"current_status": "Offline", "error": error_msg},
                    "network_config": {"current_ip": ip},
                }
            elif "DEVICE_OFFLINE" in error_msg:
                return {
                    "reachable": False,
                    "power": "OFF",
                    "error": "DEVICE_OFFLINE",
                    "error_message": "Device is offline or unreachable. Please check the network connection.",
                    "device_info": {"current_status": "Offline", "error": error_msg},
                    "network_config": {"current_ip": ip},
                }
            else:
                return {
                    "reachable": False,
                    "power": "OFF",
                    "error": "UNKNOWN_ERROR",
                    "error_message": error_msg,
                    "device_info": {"current_status": "Offline", "error": error_msg},
                    "network_config": {"current_ip": ip},
                }

    # ========== COMMAND HANDLER ==========
    
    def send_command(self, ip, port, display_id, command, params=None):
        """Execute a command on the device"""
        if not self.username or not self.password:
            return False, "Missing credentials: username and password are required."

        logger.info(f"[CrestronAirMedia] Command: {command} to {ip}, params: {params}")
        params = params or {}

        try:
            # ========== Status Commands ==========
            if command == "get_status" or command == "refresh_status":
                result = self.query_status(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_device_info":
                result = self.get_device_info(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_airmedia_status":
                result = self.get_airmedia_status(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_network_config":
                result = self.get_network_config(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_power_settings":
                result = self.get_power_settings(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_wireless_conferencing":
                result = self.get_wireless_conferencing(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_application_mode":
                result = self.get_application_mode(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_connection_display":
                result = self.get_connection_display(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_paired_devices":
                result = self.get_paired_devices(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_connected_clients":
                result = self.get_connected_clients(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_full_status":
                result = self.query_status(ip, port, display_id)
                return True, json.dumps(result)

            # ========== Device Operations ==========
            elif command == "reboot":
                wait = params.get("wait_for_reboot", False)
                result = self._reboot_device(ip)
                if wait:
                    time.sleep(60)
                return result.get("success", False), result.get("message", "")

            # ========== Hostname & Domain ==========
            elif command == "set_hostname":
                hostname = params.get("hostname", "")
                if not hostname:
                    return False, "Hostname is required"
                result = self._set_hostname(ip, hostname)
                return result.get("success", False), result.get("message", "")

            elif command == "set_domain":
                domain = params.get("domain", "")
                if not domain:
                    return False, "Domain is required"
                result = self._set_domain(ip, domain)
                return result.get("success", False), result.get("message", "")

            # ========== Network Configuration ==========
            elif command == "set_static_ip":
                ip_address = params.get("ip_address", "")
                subnet_mask = params.get("subnet_mask", "")
                gateway = params.get("gateway", "")
                dns1 = params.get("dns1", "8.8.8.8")
                dns2 = params.get("dns2", "8.8.4.4")
                adapter = params.get("adapter", "FEC1")
                
                if not ip_address or not subnet_mask or not gateway:
                    return False, "IP address, subnet mask, and gateway are required"
                
                result = self._set_static_ip(ip, ip_address, subnet_mask, gateway, dns1, dns2, adapter)
                return result.get("success", False), result.get("message", "")

            elif command == "enable_dhcp":
                adapter = params.get("adapter", "FEC1")
                result = self._enable_dhcp(ip, adapter)
                return result.get("success", False), result.get("message", "")

            elif command == "set_ssh":
                enabled = params.get("enabled", False)
                result = self._set_ssh(ip, enabled)
                return result.get("success", False), result.get("message", "")

            elif command == "set_ping":
                enabled = params.get("enabled", False)
                result = self._set_ping(ip, enabled)
                return result.get("success", False), result.get("message", "")

            # ========== Flex Mode ==========
            elif command == "enable_flex_mode":
                result = self._set_flex_mode(ip, True)
                return result.get("success", False), result.get("message", "")

            elif command == "disable_flex_mode":
                result = self._set_flex_mode(ip, False)
                return result.get("success", False), result.get("message", "")

            # ========== Power Settings ==========
            elif command == "set_power_mode":
                mode = params.get("mode", "")
                if not mode:
                    return False, "Mode is required"
                result = self._set_power_mode(ip, mode)
                return result.get("success", False), result.get("message", "")

            elif command == "set_occupancy_power":
                power_on = params.get("power_on")
                power_off = params.get("power_off")
                result = self._set_occupancy_power(ip, power_on, power_off)
                return result.get("success", False), result.get("message", "")

            elif command == "set_video_sync_power":
                power_on = params.get("power_on")
                power_off = params.get("power_off")
                timeout = params.get("timeout")
                result = self._set_video_sync_power(ip, power_on, power_off, timeout)
                return result.get("success", False), result.get("message", "")

            elif command == "set_power_schedule":
                day = params.get("day", "")
                enabled = params.get("enabled", False)
                on_time = params.get("on_time", "")
                off_time = params.get("off_time", "")
                
                if not day:
                    return False, "Day is required"
                
                result = self._set_power_schedule(ip, day, enabled, on_time, off_time)
                return result.get("success", False), result.get("message", "")

            # ========== Wireless Conferencing ==========
            elif command == "enable_wireless_conferencing":
                result = self._set_wireless_conferencing_enabled(ip, True)
                return result.get("success", False), result.get("message", "")

            elif command == "disable_wireless_conferencing":
                result = self._set_wireless_conferencing_enabled(ip, False)
                return result.get("success", False), result.get("message", "")

            elif command == "set_wireless_conferencing_quality":
                quality = params.get("quality", "")
                if not quality:
                    return False, "Quality is required"
                result = self._set_wireless_conferencing_quality(ip, quality)
                return result.get("success", False), result.get("message", "")

            elif command == "set_peripheral_volume":
                volume = params.get("volume", 50)
                result = self._set_peripheral_volume(ip, volume)
                return result.get("success", False), result.get("message", "")

            elif command == "mute_peripheral":
                result = self._mute_peripheral(ip)
                return result.get("success", False), result.get("message", "")

            elif command == "unmute_peripheral":
                result = self._unmute_peripheral(ip)
                return result.get("success", False), result.get("message", "")

            elif command == "hide_peripheral_status":
                result = self._hide_peripheral_status(ip)
                return result.get("success", False), result.get("message", "")

            elif command == "show_peripheral_status":
                result = self._show_peripheral_status(ip)
                return result.get("success", False), result.get("message", "")

            # ========== Application Mode ==========
            elif command == "set_application_mode":
                mode = params.get("mode", "")
                signage_provider = params.get("signage_provider", "None")
                signage_url = params.get("signage_url", "")
                if not mode:
                    return False, "Mode is required"
                result = self._set_application_mode(ip, mode, signage_provider, signage_url)
                return result.get("success", False), result.get("message", "")

            elif command == "set_content_caching":
                mode = params.get("mode", "")
                if not mode:
                    return False, "Mode is required"
                result = self._set_content_caching(ip, mode)
                return result.get("success", False), result.get("message", "")

            elif command == "set_system_mode":
                mode = params.get("mode", "")
                if not mode:
                    return False, "Mode is required"
                result = self._set_system_mode(ip, mode)
                return result.get("success", False), result.get("message", "")

            elif command == "enable_canvas":
                result = self._set_canvas_enabled(ip, True)
                return result.get("success", False), result.get("message", "")

            elif command == "disable_canvas":
                result = self._set_canvas_enabled(ip, False)
                return result.get("success", False), result.get("message", "")

            # ========== Connection Display ==========
            elif command == "set_airmedia_connection_overlay":
                enabled = params.get("enabled", False)
                result = self._set_airmedia_connection_overlay(ip, enabled)
                return result.get("success", False), result.get("message", "")

            elif command == "set_connection_display_info":
                show = params.get("show", False)
                mode = params.get("mode")
                custom = params.get("custom")
                result = self._set_connection_display_info(ip, show, mode, custom)
                return result.get("success", False), result.get("message", "")

            elif command == "set_guest_connection_info":
                show = params.get("show", False)
                mode = params.get("mode")
                custom = params.get("custom")
                result = self._set_guest_connection_info(ip, show, mode, custom)
                return result.get("success", False), result.get("message", "")

            elif command == "set_connection_info_mode":
                mode = params.get("mode", "")
                custom = params.get("custom")
                if not mode:
                    return False, "Mode is required"
                result = self._set_connection_info_mode(ip, mode, custom)
                return result.get("success", False), result.get("message", "")

            elif command == "set_connection_display_airplay":
                enabled = params.get("enabled", False)
                result = self._set_connection_display_airplay(ip, enabled)
                return result.get("success", False), result.get("message", "")

            elif command == "set_connection_display_miracast":
                enabled = params.get("enabled", False)
                result = self._set_connection_display_miracast(ip, enabled)
                return result.get("success", False), result.get("message", "")

            elif command == "set_connection_display_adaptor":
                enabled = params.get("enabled", False)
                result = self._set_connection_display_adaptor(ip, enabled)
                return result.get("success", False), result.get("message", "")

            elif command == "set_wired_connection_info":
                enabled = params.get("enabled", False)
                result = self._set_wired_connection_info(ip, enabled)
                return result.get("success", False), result.get("message", "")

            elif command == "set_wired_connection_details":
                enabled = params.get("enabled", False)
                result = self._set_wired_connection_details(ip, enabled)
                return result.get("success", False), result.get("message", "")

            # ========== TX3 Pairing ==========
            elif command == "start_pairing":
                result = self._start_pairing(ip)
                return result.get("success", False), result.get("message", "")

            elif command == "stop_pairing":
                result = self._stop_pairing(ip)
                return result.get("success", False), result.get("message", "")

            elif command == "set_local_pairing_enabled":
                enabled = params.get("enabled")
                if enabled is None:
                    return False, "Enabled state is required"
                result = self._set_local_pairing_enabled(ip, bool(enabled))
                return result.get("success", False), result.get("message", "")

            elif command == "set_connect_adapter_behavior":
                behavior = params.get("behavior", "")
                if not behavior:
                    return False, "Behavior is required"
                result = self._set_connect_adapter_behavior(ip, behavior)
                return result.get("success", False), result.get("message", "")

            else:
                return False, f"Unknown command: {command}"

        except Exception as e:
            logger.error(f"[CrestronAirMedia] Command failed: {e}")
            return False, str(e)

    # ========== COMMAND IMPLEMENTATIONS ==========
    
    def _reboot_device(self, ip):
        """Reboot the device"""
        try:
            payload = {"Device": {"DeviceOperations": {"Reboot": True}}}
            result = self._make_request(ip, "POST", "/Device/DeviceOperations/", data=payload)
            if "error" in result:
                return {"success": False, "message": result["error"]}
            return {"success": True, "message": "Reboot command sent successfully"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_hostname(self, ip, hostname: str) -> dict:
        """Set device hostname"""
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', hostname):
            return {"success": False, "message": "Invalid hostname format"}
        if len(hostname) > 63:
            return {"success": False, "message": "Hostname too long. Max 63 characters"}
        
        payload_eth = {"Device": {"Ethernet": {"HostName": hostname}}}
        payload_net = {"Device": {"NetworkAdapters": {"HostName": hostname}}}
        
        try:
            self._make_request(ip, "POST", "/Device/Ethernet/", data=payload_eth)
            self._make_request(ip, "POST", "/Device/NetworkAdapters/", data=payload_net)
            return {"success": True, "message": f"Hostname set to '{hostname}'"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_domain(self, ip, domain: str) -> dict:
        """Set device domain"""
        if domain and len(domain) > 127:
            return {"success": False, "message": "Domain too long. Max 127 characters"}
        
        payload = {"Device": {"Ethernet": {"DomainName": domain}}}
        
        try:
            self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
            return {"success": True, "message": f"Domain set to '{domain}'"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_static_ip(self, ip, ip_address: str, subnet_mask: str, gateway: str, 
                       dns1: str = "8.8.8.8", dns2: str = "8.8.4.4", adapter: str = "FEC1") -> dict:
        """Set static IP configuration"""
        payload = {
            "Device": {
                "Ethernet": {
                    "Adapters": [{
                        "Name": adapter,
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

    def _enable_dhcp(self, ip, adapter: str = "FEC1") -> dict:
        """Enable DHCP"""
        payload = {"Device": {"Ethernet": {"Adapters": [{"Name": adapter, "IPv4": {"IsDhcpEnabled": True}}]}}}
        try:
            self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
            return {"success": True, "message": "DHCP enabled"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_ssh(self, ip, enabled: bool) -> dict:
        """Enable/disable SSH"""
        payload_eth = {"Device": {"Ethernet": {"IsSshEnabled": enabled}}}
        payload_comm = {"Device": {"CommunicationConfigurations": {"IsSshEnabled": enabled}}}
        
        try:
            self._make_request(ip, "POST", "/Device/Ethernet/", data=payload_eth)
            self._make_request(ip, "POST", "/Device/CommunicationConfigurations/", data=payload_comm)
            state = "enabled" if enabled else "disabled"
            return {"success": True, "message": f"SSH {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_ping(self, ip, enabled: bool) -> dict:
        """Enable/disable ICMP ping"""
        payload = {"Device": {"Ethernet": {"IsIcmpPingEnabled": enabled}}}
        try:
            self._make_request(ip, "POST", "/Device/Ethernet/", data=payload)
            state = "enabled" if enabled else "disabled"
            return {"success": True, "message": f"ICMP ping {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_flex_mode(self, ip, enabled: bool) -> dict:
        """Set Flex Mode"""
        payload = {"Device": {"App": {"Config": {"General": {"IsFlexModeEnabled": enabled}}}}}
        try:
            self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
            state = "enabled" if enabled else "disabled"
            return {"success": True, "message": f"Flex Mode {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_power_mode(self, ip, mode: str) -> dict:
        """Set power control mode"""
        valid_modes = ["AlwaysOn", "OccupancyBased", "OccupancyBasedWithSignage", "VideoSyncBased", "SignageOnly"]
        
        if mode not in valid_modes:
            return {"success": False, "message": f"Invalid mode: {mode}. Valid modes: {', '.join(valid_modes)}"}
        
        payload = {
            "Device": {
                "App": {
                    "Config": {
                        "General": {
                            "PowerControlOptions": mode
                        }
                    }
                }
            }
        }
        
        try:
            self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
            time.sleep(1)
            return {"success": True, "message": f"Power mode set successfully"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_occupancy_power(self, ip, power_on: bool = None, power_off: bool = None) -> dict:
        """Set occupancy power settings"""
        payload = {"Device": {"App": {"Config": {"General": {"OccupancyPowerSettings": {}}}}}}
        if power_on is not None:
            payload["Device"]["App"]["Config"]["General"]["OccupancyPowerSettings"]["PowerOnEnable"] = power_on
        if power_off is not None:
            payload["Device"]["App"]["Config"]["General"]["OccupancyPowerSettings"]["PowerOffEnable"] = power_off
        
        try:
            self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
            return {"success": True, "message": "Occupancy power settings updated"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_video_sync_power(self, ip, power_on: bool = None, power_off: bool = None, timeout: int = None) -> dict:
        """Set video sync power settings"""
        payload = {"Device": {"App": {"Config": {"General": {"VideoSyncPowerSettings": {}}}}}}
        if power_on is not None:
            payload["Device"]["App"]["Config"]["General"]["VideoSyncPowerSettings"]["PowerOnEnable"] = power_on
        if power_off is not None:
            payload["Device"]["App"]["Config"]["General"]["VideoSyncPowerSettings"]["PowerOffEnable"] = power_off
        if timeout is not None:
            if timeout < 1 or timeout > 120:
                return {"success": False, "message": "Timeout must be between 1 and 120 minutes"}
            payload["Device"]["App"]["Config"]["General"]["VideoSyncPowerSettings"]["PowerOffTimeoutMinutes"] = timeout
        
        try:
            self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
            return {"success": True, "message": "Video sync power settings updated"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_power_schedule(self, ip, day: str, enabled: bool, on_time: str = "", off_time: str = "") -> dict:
        """Set power schedule for a specific day"""
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        day_cap = day.capitalize() if day else day
        
        if day_cap not in days:
            return {"success": False, "message": f"Invalid day. Must be one of: {', '.join(days)}"}
        
        if not on_time or not off_time:
            try:
                result = self._make_request(ip, "GET", "/Device/App/Config/")
                config = self._unwrap(result, "Device", "App", "Config") or {}
                general = config.get("General", {})
                power_schedule = general.get("PowerSchedule", {})
                existing = power_schedule.get(day_cap, {})
                on_time = on_time or existing.get("OnTime", "09:00")
                off_time = off_time or existing.get("OffTime", "17:00")
            except:
                on_time = on_time or "09:00"
                off_time = off_time or "17:00"
        
        payload = {
            "Device": {
                "App": {
                    "Config": {
                        "General": {
                            "PowerSchedule": {
                                day_cap: {
                                    "IsEnabled": enabled,
                                    "OnTime": on_time,
                                    "OffTime": off_time
                                }
                            }
                        }
                    }
                }
            }
        }
        try:
            self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
            return {"success": True, "message": f"Schedule for {day_cap} updated"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_wireless_conferencing_enabled(self, ip, enabled: bool) -> dict:
        """Set wireless conferencing enabled state"""
        payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"IsEnabled": enabled}}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            state = "enabled" if enabled else "disabled"
            return {"success": True, "message": f"Wireless conferencing {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_wireless_conferencing_quality(self, ip, quality: str) -> dict:
        """Set wireless conferencing quality"""
        if quality not in ['Normal', 'Low']:
            return {"success": False, "message": "Quality must be 'Normal' or 'Low'"}
        
        payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"QualityMode": quality}}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": f"Quality set to '{quality}'"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_peripheral_volume(self, ip, volume: int) -> dict:
        """Set peripheral volume"""
        if volume < 0 or volume > 100:
            return {"success": False, "message": "Volume must be between 0 and 100"}
        
        payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"PeripheralVolume": volume}}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": f"Volume set to {volume}%"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _mute_peripheral(self, ip) -> dict:
        """Mute peripheral audio"""
        payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"PeripheralMute": True}}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": "Audio muted"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _unmute_peripheral(self, ip) -> dict:
        """Unmute peripheral audio"""
        payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"PeripheralMute": False}}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": "Audio unmuted"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _hide_peripheral_status(self, ip) -> dict:
        """Hide peripheral status"""
        payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"IsPeripheralStatusHidden": True}}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": "Peripheral status hidden"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _show_peripheral_status(self, ip) -> dict:
        """Show peripheral status"""
        payload = {"Device": {"AirMedia": {"WirelessConferencing": {"Configuration": {"IsPeripheralStatusHidden": False}}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": "Peripheral status shown"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_system_mode(self, ip, mode: str) -> dict:
        """Set system mode"""
        valid = ["OptimizedForVideoQuality", "OptimizedForMultiplePresentations"]
        if mode not in valid:
            return {"success": False, "message": f"Invalid mode. Must be one of: {', '.join(valid)}"}
        
        payload = {"Device": {"AirMedia": {"SystemMode": mode}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": f"System mode set to '{mode}'"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_canvas_enabled(self, ip, enabled: bool) -> dict:
        """Set Canvas enabled state"""
        payload = {"Device": {"AirMedia": {"IsCanvasEnabled": enabled}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            state = "enabled" if enabled else "disabled"
            return {"success": True, "message": f"Canvas {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_application_mode(self, ip, mode: str, signage_provider: str = "None", signage_url: str = "") -> dict:
        """Set application mode and signage provider"""
        try:
            payload = {
                "Device": {
                    "App": {
                        "Config": {
                            "General": {
                                "ApplicationMode": mode,
                                "SignageProvider": signage_provider
                            }
                        }
                    }
                }
            }
            
            if signage_url:
                payload["Device"]["App"]["Config"]["General"]["SignageUrl"] = signage_url
            
            result = self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
            
            if "error" in result:
                alt_payload = {
                    "Device": {
                        "AirMedia": {
                            "ApplicationMode": mode,
                            "SignageProvider": signage_provider
                        }
                    }
                }
                result = self._make_request(ip, "POST", "/Device/AirMedia/", data=alt_payload)
            
            if "error" in result:
                return {"success": False, "message": result.get("error", "Failed to set application mode")}
            
            return {"success": True, "message": f"Application mode set to '{mode}' with {signage_provider}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_content_caching(self, ip, mode: str) -> dict:
        """Set content caching mode for signage"""
        valid_modes = ["SignageAsBackground", "SignageInStandby", "BothBackgroundAndStandby"]
        if mode not in valid_modes:
            return {"success": False, "message": f"Invalid mode. Must be one of: {', '.join(valid_modes)}"}
        
        payload = {
            "Device": {
                "App": {
                    "Config": {
                        "General": {
                            "ContentCaching": mode
                        }
                    }
                }
            }
        }
        try:
            self._make_request(ip, "POST", "/Device/App/Config/", data=payload)
            return {"success": True, "message": f"Content caching set to '{mode}'"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_airmedia_connection_overlay(self, ip, enabled: bool) -> dict:
        """Show/hide AirMedia connection info overlay"""
        payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowAirMediaOverlay": enabled}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            state = "shown" if enabled else "hidden"
            return {"success": True, "message": f"AirMedia overlay {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_connection_display_info(self, ip, show: bool, mode: str = None, custom: str = None) -> dict:
        """Set primary connection display info"""
        payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {}}}}
        payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ShowConnectionInfo"] = show
        
        if mode:
            payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ConnectionInfoMode"] = mode
        
        if custom and mode == "Custom":
            payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["CustomString"] = custom
        
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": "Primary connection display updated"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_guest_connection_info(self, ip, show: bool, mode: str = None, custom: str = None) -> dict:
        """Set guest connection info"""
        payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {}}}}
        payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ShowGuestConnectionInfo"] = show
        
        if mode:
            payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["GuestInfoMode"] = mode
        
        if custom and mode == "Custom":
            payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["GuestCustomString"] = custom
        
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": "Guest connection info updated"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_connection_info_mode(self, ip, mode: str, custom: str = None) -> dict:
        """Set connection info display mode"""
        valid = ["IPAddress", "Host", "HostAndDomain", "Custom"]
        if mode not in valid:
            return {"success": False, "message": f"Invalid mode. Must be one of: {', '.join(valid)}"}
        
        payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {}}}}
        payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ConnectionInfoMode"] = mode
        
        if custom and mode == "Custom":
            payload["Device"]["AirMedia"]["ConnectionDisplayOptions"]["ConnectionCustomString"] = custom
        
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            return {"success": True, "message": f"Connection info mode set to '{mode}'"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_connection_display_airplay(self, ip, enabled: bool) -> dict:
        """Show/hide Apple Screen Mirroring info"""
        payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowAirplayInfo": enabled}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            state = "shown" if enabled else "hidden"
            return {"success": True, "message": f"Apple Screen Mirroring info {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_connection_display_miracast(self, ip, enabled: bool) -> dict:
        """Show/hide Miracast info"""
        payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowMiracastInfo": enabled}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            state = "shown" if enabled else "hidden"
            return {"success": True, "message": f"Miracast info {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_connection_display_adaptor(self, ip, enabled: bool) -> dict:
        """Show/hide Connect Adaptor info"""
        payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowConnectAdaptorInfo": enabled}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            state = "shown" if enabled else "hidden"
            return {"success": True, "message": f"Connect Adaptor info {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_wired_connection_info(self, ip, enabled: bool) -> dict:
        """Show/hide wired connection info"""
        payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowWiredConnectionInfo": enabled}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            state = "shown" if enabled else "hidden"
            return {"success": True, "message": f"Wired connection info {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_wired_connection_details(self, ip, enabled: bool) -> dict:
        """Show/hide wired connection details"""
        payload = {"Device": {"AirMedia": {"ConnectionDisplayOptions": {"ShowWiredConnectionDetails": enabled}}}}
        try:
            self._make_request(ip, "POST", "/Device/AirMedia/", data=payload)
            state = "shown" if enabled else "hidden"
            return {"success": True, "message": f"Wired connection details {state}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _start_pairing(self, ip) -> dict:
        """Start TX3 device pairing"""
        try:
            payload = {"Device": {"AirMediaTx3": {"PairCmd": True}}}
            result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
            if "error" not in result:
                return {"success": True, "message": "Pairing mode started for 60 seconds", "pairing_status": "In Progress"}
            return {"success": False, "message": "Could not start pairing mode"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _stop_pairing(self, ip) -> dict:
        """Stop TX3 device pairing mode"""
        try:
            payload = {"Device": {"AirMediaTx3": {"PairCmd": False}}}
            result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
            if "error" not in result:
                return {"success": True, "message": "Pairing mode stopped", "pairing_status": "Not Started"}
            return {"success": False, "message": "Could not stop pairing mode"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_local_pairing_enabled(self, ip, enabled: bool) -> dict:
        """Enable or disable local pairing for TX3 devices"""
        payload = {"Device": {"AirMediaTx3": {"IsLocalPairingEnabled": enabled}}}
        try:
            result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
            if "error" not in result:
                return {"success": True, "message": f"Local pairing {'enabled' if enabled else 'disabled'}"}
            return {"success": False, "message": "Could not update local pairing"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _set_connect_adapter_behavior(self, ip, behavior: str) -> dict:
        """Set connect adapter behavior for TX3 devices"""
        valid_behaviors = ["AutoPresentAndAutoConference", "AutoPresent", "AutoConference"]
        
        if behavior not in valid_behaviors:
            return {"success": False, "message": f"Invalid behavior. Must be one of: {', '.join(valid_behaviors)}"}
        
        try:
            payload = {"Device": {"AirMediaTx3": {"ConnectAdapterBehavior": behavior}}}
            result = self._make_request(ip, "POST", "/Device/AirMediaTx3/", data=payload)
            
            if "error" not in result:
                return {"success": True, "message": f"Connect adapter behavior set to '{behavior}'"}
            
            # Try alternative spelling
            alt_payload = {"Device": {"AirMedia": {"ConnectAdapterBehavior": behavior}}}
            alt_result = self._make_request(ip, "POST", "/Device/AirMedia/", data=alt_payload)
            
            if "error" not in alt_result:
                return {"success": True, "message": f"Connect adapter behavior set to '{behavior}'"}
            
            return {"success": False, "message": "Failed to set connect adapter behavior"}
        except Exception as e:
            return {"success": False, "message": str(e)}


def get_plugin(config=None):
    """Factory function to create plugin instance."""
    return CrestronAirMediaPlugin(config)