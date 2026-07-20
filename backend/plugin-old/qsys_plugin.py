# """
# Manual Platform Plugin: QSYSCorePlugin
# """

# import socket
# import json
# import threading
# import time
# import re
# import asyncio
# import subprocess
# import platform
# import requests
# import xml.etree.ElementTree as ET

# from .base import ManualPlatformPlugin



# class QSYSCorePlugin(ManualPlatformPlugin):
#     """Q-SYS Core Audio/Video Platform Plugin and control too"""
    
#     name = "qsys"
#     display_name = "Q-SYS"
#     description = "QSC Q-SYS Core Monitoring"
#     supports_display_id = False
#     supports_port = False
#     default_port = 443
    
#     COMMANDS = {}
    
#     QUERY_COMMANDS = {}
    
#     def parse_xml_field(self, root, path):
#         """Helper to safely get XML field text"""
#         elem = root.find(path)
#         return elem.text.strip() if elem is not None and elem.text else None

#     def _first_non_empty(self, values):
#         for value in values:
#             if value:
#                 return value.strip() if isinstance(value, str) else value
#         return None

#     def _extract_serial_from_html(self, ip):
#         """Best-effort serial extraction from status page HTML."""
#         try:
#             resp = requests.get(f"https://{ip}/#status", timeout=5, verify=False)
#             if resp.status_code != 200:
#                 return None

#             html = resp.text
#             import re
#             patterns = [
#                 r'"serial_no"\s*:\s*"([^"]+)"',
#                 r'"serialNumber"\s*:\s*"([^"]+)"',
#                 r"device\.serial_no[^>]*>\s*([^<\s][^<]*)<"
#             ]
#             for pattern in patterns:
#                 match = re.search(pattern, html, flags=re.IGNORECASE)
#                 if match:
#                     value = match.group(1).strip()
#                     if value:
#                         return value
#         except Exception:
#             pass
#         return None

#     def _extract_serial_with_selenium(self, ip):
#         """Optional Selenium fallback for pages rendered fully via JS."""
#         try:
#             from selenium import webdriver
#             from selenium.webdriver.chrome.options import Options
#             from selenium.webdriver.common.by import By
#         except Exception:
#             return None

#         driver = None
#         try:
#             options = Options()
#             options.add_argument("--headless")
#             options.add_argument("--ignore-certificate-errors")
#             options.add_argument("--log-level=3")
#             driver = webdriver.Chrome(options=options)
#             driver.set_page_load_timeout(10)
#             driver.get(f"https://{ip}/#status")
#             time.sleep(2)

#             selectors = [
#                 (By.XPATH, '//div[@x-text="device.serial_no"]'),
#                 (By.XPATH, '//*[@x-text="device.serial_no"]')
#             ]
#             for by, selector in selectors:
#                 try:
#                     elem = driver.find_element(by, selector)
#                     serial = (elem.text or "").strip()
#                     if serial:
#                         return serial
#                 except Exception:
#                     continue
#         except Exception:
#             return None
#         finally:
#             if driver:
#                 try:
#                     driver.quit()
#                 except Exception:
#                     pass
#         return None
    
#     def get_device_info(self, ip, port=443, display_id=None):
#         """Get device info via Q-SYS XML Status API"""
#         import platform
#         import subprocess
#         import re
        
#         def ping_host():
#             param = "-n" if platform.system().lower() == "windows" else "-c"
#             try:
#                 result = subprocess.run(["ping", param, "1", ip], capture_output=True, timeout=3)
#                 return result.returncode == 0
#             except:
#                 return False
        
#         is_online = ping_host()
        
#         device_info = {
#             "ip_address": ip,
#             "port": port,
#             "display_id": display_id,
#             "make": "QSC",
#             "firmware_version" : None,
#             "device_name": None,
#             "model": None,
#             "serial_number": None,
#             "mac_address": None,
#             "current_status": "Online" if is_online else "Offline",
#         }
        
#         # Always try to fetch XML status if possible, even if ping failed
#         try:
#             url = f"https://{ip}/cgi-bin/status_xml"
#             resp = requests.get(url, timeout=5, verify=False)
            
#             if resp.status_code == 200:
#                 is_online = True # If we can reach the API, the device is definitely online
#                 device_info["current_status"] = "Online"
                
#                 root = ET.fromstring(resp.text)
#                 serial_from_xml = self._first_non_empty([
#                     self.parse_xml_field(root, "serial_number"),
#                     self.parse_xml_field(root, "serial_no"),
#                     self.parse_xml_field(root, "device_serial_number"),
#                     self.parse_xml_field(root, "device/serial_number"),
#                     self.parse_xml_field(root, "device/serial_no"),
#                 ])

#                 device_info.update({
#                     "device_name": self.parse_xml_field(root, "device_name"),
#                     "device_type": self.parse_xml_field(root, "device_type"),
#                     "model": self.parse_xml_field(root, "device_model_pretty"),
#                     "firmware": self.parse_xml_field(root, "firmware_version"),
#                     "design_name": self.parse_xml_field(root, "design/pretty_name"),
#                     "design_status": self.parse_xml_field(root, "design/state_pretty"),
#                     "mac_address": self.parse_xml_field(root, "network_interfaces/network_interface/mac_address"),
#                     "uptime": self.parse_xml_field(root, "design/uptime"),
#                     "serial_number": serial_from_xml,
#                 })

#                 # Your device publishes serial in the JS status page on some firmware builds.
#                 if not device_info.get("serial_number"):
#                     device_info["serial_number"] = self._extract_serial_from_html(ip)

#                 if not device_info.get("serial_number") and self.config.get("use_selenium_serial", True):
#                     device_info["serial_number"] = self._extract_serial_with_selenium(ip)

#         except Exception as e:
#             if is_online: # Only log error if we thought it was online via ping but API failed
#                 device_info["error"] = str(e)
        
#         if not device_info.get("serial_number"):
#             device_info["serial_number"] = device_info.get("mac_address")

#         if not device_info.get("device_name"):
#             device_info["device_name"] = device_info.get("model") or f"Q-SYS {ip}"
        
#         return device_info
    
#     def send_command(self, ip, port, display_id, command):
#         """Q-SYS is monitoring-only, no control commands"""
#         return False, "Q-SYS is monitoring-only. Control commands not supported."
    
#     def query_status(self, ip, port=443, display_id=None):
#         """Query Q-SYS device status"""
#         status = {}
        
#         try:
#             url = f"https://{ip}/cgi-bin/status_xml"
#             resp = requests.get(url, timeout=5, verify=False)
            
#             if resp.status_code == 200:
#                 root = ET.fromstring(resp.text)
                
#                 status.update({
#                     "device_name": self.parse_xml_field(root, "device_name"),
#                     "device_type": self.parse_xml_field(root, "device_type"),
#                     "model": self.parse_xml_field(root, "device_model_pretty"),
#                     "firmware": self.parse_xml_field(root, "firmware_version"),
#                     "design_name": self.parse_xml_field(root, "design/pretty_name"),
#                     "design_status": self.parse_xml_field(root, "design/state_pretty"),
#                     "ip_address": self.parse_xml_field(root, "network_interfaces/network_interface/address"),
#                     "mac_address": self.parse_xml_field(root, "network_interfaces/network_interface/mac_address"),
#                     "uptime": self.parse_xml_field(root, "design/uptime"),
#                     "serial_number": self._first_non_empty([
#                         self.parse_xml_field(root, "serial_number"),
#                         self.parse_xml_field(root, "serial_no"),
#                         self.parse_xml_field(root, "device_serial_number"),
#                         self.parse_xml_field(root, "device/serial_number"),
#                         self.parse_xml_field(root, "device/serial_no"),
#                     ]),
#                 })

#                 if not status.get("serial_number"):
#                     status["serial_number"] = self._extract_serial_from_html(ip)
#                 if not status.get("serial_number") and self.config.get("use_selenium_serial", True):
#                     status["serial_number"] = self._extract_serial_with_selenium(ip)
#                 if not status.get("serial_number"):
#                     status["serial_number"] = status.get("mac_address")
                
#                 status["reachable"] = True
#         except Exception as e:
#             status["reachable"] = False
#             status["error"] = str(e)
        
#         return status




"""
Manual Platform Plugin: QSYSCorePlugin
Updated version with proper API authentication for Core and Peripheral devices
Includes Bearer Token authentication for Core devices
"""

import re
import time
import subprocess
import platform
import requests
import xml.etree.ElementTree as ET
from requests.auth import HTTPDigestAuth, HTTPBasicAuth

from .base import ManualPlatformPlugin

# Disable SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class QSYSCorePlugin(ManualPlatformPlugin):
    """Q-SYS Core Audio/Video Platform Plugin"""
    
    name = "qsys"
    display_name = "Q-SYS"
    description = "QSC Q-SYS Core Monitoring with Serial Number Support"
    supports_display_id = False
    supports_port = True
    default_port = 443
    
    COMMANDS = {}
    QUERY_COMMANDS = {}
    
    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or {}
        self.session = requests.Session()
        self.session.verify = False
        self.token = None
        self.token_expiry = 0
    
    def _ping_host(self, ip):
        """Helper method to ping host"""
        param = "-n" if platform.system().lower() == "windows" else "-c"
        try:
            result = subprocess.run(["ping", param, "1", ip], capture_output=True, timeout=3)
            return result.returncode == 0
        except:
            return False
    
    def _parse_xml_field(self, root, path):
        """Helper to safely get XML field text"""
        try:
            elem = root.find(path)
            return elem.text.strip() if elem is not None and elem.text else None
        except:
            return None
    
    def _is_mac_address(self, text):
        """Check if string looks like a MAC address"""
        if not text or not isinstance(text, str):
            return False
        return bool(re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', text, re.IGNORECASE))
    
    def _get_status_xml(self, ip, port):
        """Get the status XML from the device"""
        try:
            url = f"https://{ip}:{port}/cgi-bin/status_xml"
            response = requests.get(url, timeout=10, verify=False)
            if response.status_code == 200:
                return ET.fromstring(response.text)
            return None
        except:
            return None
    
    def _get_bearer_token(self, ip, port, username, password):
        """Get bearer token from Core device using /api/v0/logon"""
        if self.token and time.time() < self.token_expiry:
            return self.token
        
        try:
            url = f"https://{ip}:{port}/api/v0/logon"
            payload = {"username": username, "password": password}
            response = requests.post(url, json=payload, timeout=10, verify=False)
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.token = data.get("token")
                self.token_expiry = time.time() + 3600
                return self.token
            return None
        except Exception:
            return None
    
    def _get_core_serial(self, ip, port, username, password):
        """Get serial number from Core device using Bearer Token authentication"""
        
        base_url = f"https://{ip}:{port}"
        
        # Method 1: Bearer Token on /api/v0/cores (works for Core devices)
        try:
            token = self._get_bearer_token(ip, port, username, password)
            if token:
                headers = {"Authorization": f"Bearer {token}"}
                url = f"{base_url}/api/v0/cores"
                response = requests.get(url, timeout=10, verify=False, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        core = data[0]
                        serial = core.get("serialNo")
                        if serial and len(serial) > 5 and not self._is_mac_address(serial):
                            return serial
        except Exception:
            pass
        
        # Method 2: Direct Digest Auth on /api/v0/cores/self (fallback)
        try:
            auth = HTTPDigestAuth(username, password)
            url = f"{base_url}/api/v0/cores/self"
            response = requests.get(url, timeout=10, verify=False, auth=auth)
            if response.status_code == 200:
                data = response.json()
                serial = data.get("serialNo")
                if serial and len(serial) > 5 and not self._is_mac_address(serial):
                    return serial
        except Exception:
            pass
        
        return None
    
    def _get_peripheral_serial(self, ip, port, username, password):
        """Get serial number from peripheral device using env_show endpoint"""
        try:
            url = f"https://{ip}:{port}/api/v1/env_show?serialno"
            
            if username and password:
                auth = HTTPDigestAuth(username, password)
                response = requests.get(url, timeout=10, verify=False, auth=auth)
            else:
                response = requests.get(url, timeout=10, verify=False)
            
            if response and response.status_code == 200:
                data = response.json()
                serial = data.get("serialno")
                if serial and len(serial) > 5 and not self._is_mac_address(serial):
                    return serial
            return None
        except Exception:
            return None
    
    def _get_serial_from_xml(self, root):
        """Extract serial from XML if available"""
        if root is None:
            return None
        
        for path in ["serial_number", "serial_no", "device_serial_number"]:
            serial = self._parse_xml_field(root, path)
            if serial and len(serial) > 5 and not self._is_mac_address(serial):
                return serial
        return None

    def get_device_info(self, ip, port=443, display_id=None):
        """
        Get device info via Q-SYS API with authentication support.
        Credentials are read from self.config (passed during plugin initialization).
        """
        
        # IMPORTANT: Read credentials from self.config (passed by Edge)
        username = self.config.get('username') if self.config else None
        password = self.config.get('password') if self.config else None
        
        is_online = self._ping_host(ip)
        
        device_info = {
            "ip_address": ip,
            "port": port,
            "display_id": display_id,
            "make": "QSC",
            "firmware_version": None,
            "device_name": None,
            "model": None,
            "serial_number": None,
            "mac_address": None,
            "device_type": None,
            "design_name": None,
            "design_status": None,
            "uptime": None,
            "current_status": "Online" if is_online else "Offline",
        }
        
        if is_online:
            try:
                # Get basic info from XML status (works without auth)
                root = self._get_status_xml(ip, port)
                
                if root:
                    device_info.update({
                        "device_name": self._parse_xml_field(root, "device_name") or "Unknown",
                        "device_type": self._parse_xml_field(root, "device_type") or "Unknown",
                        "model": self._parse_xml_field(root, "device_model_pretty") or "Unknown",
                        "firmware_version": self._parse_xml_field(root, "firmware_version") or "Unknown",
                        "design_name": self._parse_xml_field(root, "design/pretty_name") or "Unknown",
                        "design_status": self._parse_xml_field(root, "design/state_pretty") or "Unknown",
                        "uptime": self._parse_xml_field(root, "design/uptime") or "Unknown",
                        "mac_address": self._parse_xml_field(root, "network_interfaces/network_interface/mac_address"),
                    })
                    device_info["firmware"] = device_info.get("firmware_version")
                
                # Determine if this is a Core or Peripheral device
                device_type = device_info.get("device_type", "")
                model = device_info.get("model", "")
                is_core = "Core" in device_type or "Processor" in device_type or "Core Mode" in model
                
                serial = None
                
                if is_core and username and password:
                    # Core device - use Bearer Token authentication
                    serial = self._get_core_serial(ip, port, username, password)
                    if serial:
                        device_info["serial_number"] = serial
                        return device_info
                
                elif not is_core:
                    # Peripheral device - try env_show endpoint
                    serial = self._get_peripheral_serial(ip, port, username, password)
                    if serial:
                        device_info["serial_number"] = serial
                        return device_info
                
                # If still no serial, try XML
                if not serial and root:
                    serial = self._get_serial_from_xml(root)
                    if serial:
                        device_info["serial_number"] = serial
                        return device_info
                
                # Fallback to MAC address
                if not serial and device_info.get("mac_address"):
                    device_info["serial_number"] = device_info["mac_address"]
                
            except Exception as e:
                device_info["error"] = str(e)
        
        # Final fallback
        if not device_info.get("serial_number") and device_info.get("mac_address"):
            device_info["serial_number"] = device_info["mac_address"]
        
        if not device_info.get("serial_number"):
            device_info["serial_number"] = "NOT_AVAILABLE"
        
        if not device_info.get("device_name"):
            device_info["device_name"] = device_info.get("model") or f"Q-SYS {ip}"
        
        if not device_info.get("firmware_version") or device_info["firmware_version"] == "Unknown":
            device_info["firmware_version"] = "Unknown"
        device_info["firmware"] = device_info.get("firmware_version")

        return device_info
    
    def send_command(self, ip, port, display_id, command, params=None):
        """Q-SYS is monitoring-only, no control commands"""
        return False, "Q-SYS is monitoring-only. Control commands not supported."
    
    def query_status(self, ip, port=443, display_id=None):
        """Query Q-SYS device status"""
        
        # IMPORTANT: Read credentials from self.config
        username = self.config.get('username') if self.config else None
        password = self.config.get('password') if self.config else None
        
        status = {
            "reachable": False,
            "device_name": None,
            "model": None,
            "firmware": None,
            "serial": None,
            "design_status": None,
            "uptime": None,
            "error": None
        }
        
        try:
            # Get basic info from XML
            root = self._get_status_xml(ip, port)
            
            if root:
                status.update({
                    "reachable": True,
                    "device_name": self._parse_xml_field(root, "device_name"),
                    "model": self._parse_xml_field(root, "device_model_pretty"),
                    "firmware": self._parse_xml_field(root, "firmware_version"),
                    "design_status": self._parse_xml_field(root, "design/state_pretty"),
                    "uptime": self._parse_xml_field(root, "design/uptime"),
                })
                
                # Determine device type
                device_type = self._parse_xml_field(root, "device_type") or ""
                model = status.get("model", "")
                is_core = "Core" in device_type or "Processor" in device_type or "Core Mode" in model
                
                serial = None
                
                if is_core and username and password:
                    serial = self._get_core_serial(ip, port, username, password)
                elif not is_core:
                    serial = self._get_peripheral_serial(ip, port, username, password)
                
                if not serial:
                    serial = self._get_serial_from_xml(root)
                
                if not serial:
                    mac = self._parse_xml_field(root, "network_interfaces/network_interface/mac_address")
                    if mac:
                        serial = mac
                
                status["serial"] = serial
                
            elif self._ping_host(ip):
                status["reachable"] = True
                status["error"] = "API requires authentication or is not accessible"
            else:
                status["error"] = "Device is offline or unreachable"
                
        except Exception as e:
            status["error"] = str(e)
        
        return status


# Factory function for plugin discovery
def get_plugin(config=None):
    """Factory function for plugin discovery"""
    return QSYSCorePlugin(config)