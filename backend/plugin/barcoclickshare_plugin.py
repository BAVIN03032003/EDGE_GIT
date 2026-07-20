"""
Barco ClickShare Plugin - Complete Device Management
Fixed to properly retrieve LAN network information per ClickShare REST API v2 spec
Reference: R5915531 /13 ClickShare REST API
"""

import base64
import io
import traceback
import requests
import sys
import os
from typing import Dict, Any, Optional, Tuple
from urllib3.exceptions import InsecureRequestWarning

from .base import ManualPlatformPlugin

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class BarcoClickSharePlugin(ManualPlatformPlugin):
    """Plugin for managing Barco ClickShare devices via REST API v2"""

    name = "barco_clickshare"
    display_name = "Barco ClickShare"
    description = "Barco ClickShare Base Units via REST API v2"
    supports_display_id = False
    supports_port = True
    default_port = 4003
    OEM_NAME = "Barco"

    def __init__(self, config=None, ip_address=None, username=None, password=None):
        legacy_args = (
            config is not None
            and not isinstance(config, dict)
            and ip_address is not None
            and username is not None
            and password is None
        )
        if legacy_args:
            config, ip_address, username, password = {}, config, ip_address, username

        super().__init__(config)
        self.ip_address = ip_address or self.config.get("ip_address")
        self.username = username or self.config.get("username") or "admin"
        self.password = password or self.config.get("password")
        self.base_url = f"https://{self.ip_address}:{self.default_port}" if self.ip_address else None
        self.api_version = self.config.get("api_version", "v2")
        self.connected = False
        self.device_info = {}

    def _resolve_port(self, port=None):
        try:
            port = int(port) if port not in (None, "", "null") else None
        except (TypeError, ValueError):
            port = None
        return port if port and 0 < port <= 65535 else self.default_port

    def _prepare_target(self, ip_address, port=None):
        resolved_port = self._resolve_port(port)
        self.ip_address = ip_address
        self.base_url = f"https://{ip_address}:{resolved_port}"
        return resolved_port

    def _resolve_credentials(self):
        username = self.username or self.config.get("username") or "admin"
        password = self.password or self.config.get("password")
        return username, password

    def _ensure_connected(self):
        connection = self.connect()
        if connection.get("success"):
            return True, None
        return False, connection.get("error", "Unable to connect to device.")

    def get_device_info(self, ip, port=4003, display_id=None):
        port = self._prepare_target(ip, port)
        username, password = self._resolve_credentials()
        if not password:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Barco",
                "device_type": "Barco ClickShare",
                "current_status": "Offline",
                "error": "Missing credentials: password is required."
            }

        self.username = username
        self.password = password

        try:
            connection = self.connect()
            if not connection.get("success"):
                return {
                    "ip_address": ip,
                    "port": port,
                    "display_id": display_id,
                    "make": "Barco",
                    "device_type": "Barco ClickShare",
                    "current_status": "Offline",
                    "error": connection.get("error", "Unable to connect to device.")
                }

            details = self.get_full_device_info()
            data = details.get("data", {}) if isinstance(details, dict) else {}
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Barco",
                "device_name": data.get("hostname") or data.get("product_name") or data.get("model_name") or "Barco ClickShare",
                "model": data.get("model_name") or data.get("product_name"),
                "serial_number": data.get("serial_number"),
                "firmware": data.get("firmware_version"),
                "hardware_version": data.get("hardware_version"),
                "hostname": data.get("hostname"),
                "mac_address": data.get("mac_address"),
                "ip": data.get("ip_address"),
                "current_status": "Online",
                "raw_data": data,
            }
        except Exception as e:
            traceback.print_exc()
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Barco",
                "device_type": "Barco ClickShare",
                "current_status": "Offline",
                "error": str(e)
            }

    def send_command(self, ip, port, display_id, command, params=None):
        port = self._prepare_target(ip, port)
        username, password = self._resolve_credentials()
        if not password:
            return False, "Missing credentials: password is required."

        self.username = username
        self.password = password
        command = (command or "").strip()
        params = params or {}

        try:
            connected, error = self._ensure_connected()
            if not connected:
                return False, error

            if command == "reboot":
                result = self.reboot_device()
            elif command == "standby":
                result = self.set_standby()
            elif command == "wakeup":
                result = self.wakeup_device()
            elif command == "supported_operations":
                result = self.get_supported_operations()
            elif command == "get_network":
                result = self.get_network_overview()
            elif command == "get_lan":
                result = self.get_lan_settings()
            elif command == "get_wifi":
                result = self.get_wifi_settings()
            elif command == "get_power":
                result = self.get_power_management()
            elif command == "get_peripherals":
                result = self.get_peripherals()
            elif command == "set_hostname":
                hostname = (params.get("hostname") or "").strip()
                if not hostname:
                    return False, "hostname is required."
                result = self.set_hostname(hostname)
            elif command.startswith("set_hostname:"):
                result = self.set_hostname(command.split(":", 1)[1].strip())
            elif command == "set_lan_settings":
                addressing = (params.get("addressing") or "").strip()
                if not addressing:
                    return False, "addressing is required."
                result = self.set_lan_settings(
                    addressing=addressing,
                    ip_address=params.get("ip_address"),
                    subnet_mask=params.get("subnet_mask"),
                    default_gateway=params.get("default_gateway"),
                    dns_servers=params.get("dns_servers"),
                    domain=params.get("domain"),
                    interface_index=params.get("interface_index"),
                )
            elif command == "set_wifi_settings":
                result = self.set_wifi_settings(
                    ssid=params.get("ssid"),
                    password=params.get("password"),
                    frequency_band=params.get("frequency_band"),
                    channel=params.get("channel"),
                    broadcast_ssid=params.get("broadcast_ssid"),
                    operation_mode=params.get("operation_mode"),
                    interface_index=params.get("interface_index"),
                )
            elif command == "set_power_management":
                result = self.set_power_management(
                    power_mode=params.get("power_mode"),
                    standby_timeout=params.get("standby_timeout"),
                )
            else:
                return False, f"Unsupported command: {command or 'empty'}"

            if result.get("success"):
                message = result.get("message")
                if not message:
                    payload = result.get("data")
                    if isinstance(payload, dict):
                        message = str(payload)
                    elif payload is not None:
                        message = str(payload)
                    else:
                        message = "Command completed successfully."
                return True, message

            return False, result.get("error") or "Command failed."
        except Exception as e:
            traceback.print_exc()
            return False, str(e)

    def query_status(self, ip, port=4003, display_id=None):
        info = self.get_device_info(ip, port, display_id)
        online = info.get("current_status") == "Online"
        raw = info.get("raw_data") if isinstance(info.get("raw_data"), dict) else {}
        return {
            "reachable": online,
            "current_status": info.get("current_status", "Unknown"),
            "power": "ON" if online else "OFF",
            "is_powered_on": online,
            "device_name": raw.get("product_name") or info.get("device_name"),
            "product_name": raw.get("product_name"),
            "make": info.get("make"),
            "model": info.get("model"),
            "serial_number": info.get("serial_number"),
            "article_number": raw.get("article_number"),
            "hardware_version": info.get("hardware_version"),
            "firmware": info.get("firmware"),
            "last_update_date": raw.get("last_update_date"),
            "overall_status": raw.get("overall_status"),
            "error_message": raw.get("error_message"),
            "current_uptime": raw.get("current_uptime"),
            "in_use": raw.get("in_use", False),
            "sharing_active": raw.get("sharing_active", False),
            "hostname": raw.get("hostname") or info.get("hostname"),
            "lan_ip_address": raw.get("lan_ip_address"),
            "mac_address": raw.get("mac_address"),
            "subnet_mask": raw.get("subnet_mask"),
            "default_gateway": raw.get("default_gateway"),
            "dns_servers": raw.get("dns_servers") or [],
            "addressing": raw.get("addressing"),
            "addressing_method": raw.get("addressing_method"),
            "link_status": raw.get("link_status"),
            "lan_interface_index": raw.get("lan_interface_index"),
            "lan_domain": raw.get("lan_domain"),
            "wifi_interface_index": raw.get("wifi_interface_index"),
            "wifi_operation_mode": raw.get("wifi_operation_mode"),
            "wifi_supported_operation_modes": raw.get("wifi_supported_operation_modes") or [],
            "wifi_mac_address": raw.get("wifi_mac_address"),
            "wifi_addressing": raw.get("wifi_addressing"),
            "wifi_ip_address": raw.get("wifi_ip_address"),
            "wifi_ssid": raw.get("wifi_ssid"),
            "wifi_broadcast_ssid": raw.get("wifi_broadcast_ssid"),
            "wifi_frequency_band": raw.get("wifi_frequency_band"),
            "wifi_supported_frequency_bands": raw.get("wifi_supported_frequency_bands") or [],
            "wifi_channel": raw.get("wifi_channel"),
            "wifi_signal_strength": raw.get("wifi_signal_strength"),
            "power_mode": raw.get("power_mode"),
            "standby_timeout": raw.get("standby_timeout"),
            "power_status": raw.get("power_status"),
            "supported_power_modes": raw.get("supported_power_modes") or [],
            "supported_standby_timeouts": raw.get("supported_standby_timeouts") or [],
            "supported_power_statuses": raw.get("supported_power_statuses") or [],
            "supported_operations": raw.get("supported_operations") or [],
            "peripherals": raw.get("peripherals") or [],
            "error": info.get("error"),
        }

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Tuple[bool, Any, int]:
        """
        Make HTTP request to the ClickShare API

        Returns:
            Tuple of (success, response_data, status_code)
        """
        url = f"{self.base_url}/{self.api_version}/{endpoint.lstrip('/')}"

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=(self.username, self.password),
                headers=self._get_headers(),
                json=data,
                verify=False,
                timeout=30
            )

            if response.status_code in [200, 201, 202, 204]:
                if response.text and response.headers.get('Content-Type', '').startswith('application/json'):
                    return True, response.json(), response.status_code
                return True, response.text, response.status_code
            else:
                error_msg = response.text if response.text else f"HTTP {response.status_code}"
                return False, error_msg, response.status_code

        except requests.exceptions.ConnectionError:
            return False, "Connection failed. Please check IP address and network connectivity.", 0
        except requests.exceptions.Timeout:
            return False, "Request timeout. Device may be slow or unreachable.", 0
        except Exception as e:
            return False, f"Request error: {str(e)}", 0

    # ==================== CONNECTION & DEVICE INFO ====================

    def connect(self) -> Dict[str, Any]:
        """
        Test connection and get device information
        Endpoint: GET /configuration/system/device-identity
        """
        success, result, status = self._make_request("GET", "configuration/system/device-identity")

        if success and isinstance(result, dict):
            self.connected = True
            self.device_info = result
            return {
                "success": True,
                "data": {
                    "product_name": result.get("productName", "N/A"),
                    "model_name": result.get("modelName", "N/A"),
                    "serial_number": result.get("serialNumber", "N/A"),
                    "article_number": result.get("articleNumber", "N/A"),
                    "hardware_version": result.get("hardwareVersion", "N/A")
                }
            }
        return {"success": False, "error": str(result)}

    def get_full_device_info(self) -> Dict[str, Any]:
        """
        Get complete device information including status and firmware
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        identity_success, identity_result, _ = self._make_request("GET", "configuration/system/device-identity")
        status_success, status_result, _ = self._make_request("GET", "configuration/system/status")
        fw_success, fw_result, _ = self._make_request("GET", "configuration/system/updates/current")
        network_success, network_result, _ = self._make_request("GET", "configuration/system/network")

        result = {"success": True, "data": {}}

        if identity_success and isinstance(identity_result, dict):
            result["data"]["make"] = "Barco"
            result["data"]["product_name"] = identity_result.get("productName", "N/A")
            result["data"]["model_name"] = identity_result.get("modelName", "N/A")
            result["data"]["serial_number"] = identity_result.get("serialNumber", "N/A")
            result["data"]["article_number"] = identity_result.get("articleNumber", "N/A")
            result["data"]["hardware_version"] = identity_result.get("hardwareVersion", "N/A")

        if status_success and isinstance(status_result, dict):
            error_code = status_result.get("errorCode", "")
            if error_code == "Ok" or error_code == "OK" or not error_code:
                overall_status = "Healthy"
            else:
                overall_status = f"Warning: {error_code}"

            uptime_seconds = status_result.get("currentUptime", 0)
            uptime_days = uptime_seconds // 86400
            uptime_hours = (uptime_seconds % 86400) // 3600
            uptime_minutes = (uptime_seconds % 3600) // 60

            result["data"]["overall_status"] = overall_status
            result["data"]["error_message"] = status_result.get("errorMessage", "")
            result["data"]["uptime_formatted"] = f"{uptime_days}d {uptime_hours}h {uptime_minutes}m"
            result["data"]["current_uptime"] = uptime_seconds
            result["data"]["in_use"] = status_result.get("inUse", False)
            result["data"]["sharing_active"] = status_result.get("sharing", False)

        if fw_success and isinstance(fw_result, dict):
            result["data"]["firmware_version"] = fw_result.get("version", "N/A")
            result["data"]["last_update_date"] = fw_result.get("date", "N/A")

        if network_success and isinstance(network_result, dict):
            result["data"]["hostname"] = network_result.get("hostname", "N/A")

        result["data"]["ip_address"] = "N/A"
        result["data"]["mac_address"] = "N/A"
        result["data"]["addressing"] = "N/A"

        try:
            lan_result = self.get_lan_settings()
            if lan_result.get("success"):
                lan = lan_result.get("data", {})
                result["data"]["ip_address"] = lan.get("ip_address", "N/A")
                result["data"]["lan_ip_address"] = lan.get("ip_address", "N/A")
                result["data"]["mac_address"] = lan.get("mac_address", "N/A")
                result["data"]["addressing"] = lan.get("method", lan.get("addressing", "N/A"))
                result["data"]["addressing_method"] = lan.get("method", "N/A")
                result["data"]["lan_interface_index"] = lan.get("interface_index")
                result["data"]["link_status"] = lan.get("status", "N/A")
                result["data"]["subnet_mask"] = lan.get("subnet_mask", "N/A")
                result["data"]["default_gateway"] = lan.get("default_gateway", "N/A")
                result["data"]["dns_servers"] = lan.get("dns_servers", [])
                result["data"]["lan_domain"] = lan.get("domain", "")
        except Exception:
            pass

        try:
            wifi_result = self.get_wifi_settings()
            if wifi_result.get("success"):
                wifi = wifi_result.get("data", {})
                result["data"]["wifi_interface_index"] = wifi.get("interface_index")
                result["data"]["wifi_operation_mode"] = wifi.get("operation_mode", "N/A")
                result["data"]["wifi_supported_operation_modes"] = wifi.get("supported_operation_modes", [])
                result["data"]["wifi_mac_address"] = wifi.get("mac_address", "N/A")
                result["data"]["wifi_addressing"] = wifi.get("addressing", "N/A")
                result["data"]["wifi_ip_address"] = wifi.get("ip_address", "N/A")
                result["data"]["wifi_ssid"] = wifi.get("ssid", "N/A")
                result["data"]["wifi_broadcast_ssid"] = wifi.get("broadcast_ssid", True)
                result["data"]["wifi_frequency_band"] = wifi.get("frequency_band", "N/A")
                result["data"]["wifi_supported_frequency_bands"] = wifi.get("supported_frequency_bands", [])
                result["data"]["wifi_channel"] = wifi.get("channel", "N/A")
                result["data"]["wifi_signal_strength"] = wifi.get("signal_strength", "N/A")
        except Exception:
            pass

        try:
            power_result = self.get_power_management()
            if power_result.get("success"):
                power = power_result.get("data", {})
                result["data"]["power_mode"] = power.get("power_mode", "N/A")
                result["data"]["standby_timeout"] = power.get("standby_timeout", "N/A")
                result["data"]["power_status"] = power.get("current_status", "N/A")
                result["data"]["supported_power_modes"] = power.get("supported_power_modes", [])
                result["data"]["supported_standby_timeouts"] = power.get("supported_standby_timeouts", [])
                result["data"]["supported_power_statuses"] = power.get("supported_statuses", [])
        except Exception:
            pass

        try:
            supported_ops_result = self.get_supported_operations()
            if supported_ops_result.get("success"):
                result["data"]["supported_operations"] = supported_ops_result.get("data") or []
        except Exception:
            pass

        try:
            peripherals_result = self.get_peripherals()
            if peripherals_result.get("success"):
                result["data"]["peripherals"] = peripherals_result.get("data", {}).get("peripherals", [])
        except Exception:
            pass

        return result

    # ==================== LAN CONFIGURATION ====================

    def get_network_overview(self) -> Dict[str, Any]:
        """
        Get top-level network info from /configuration/system/network.
        Per API spec (page 42-44), this returns:
          - hostname
          - services (dhcpServer, proxy)
          - wired (array â€” references to wired interfaces)
          - wireless (array â€” references to wireless interfaces)
        Note: wired/wireless arrays here do NOT contain IP/MAC/Gateway details.
        Those must be fetched from /wired/{index} and /wireless/{index}.
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        success, result, status = self._make_request("GET", "configuration/system/network")

        if success and isinstance(result, dict):
            services = result.get("services", {}) or {}
            dhcp_server = services.get("dhcpServer", {}) or {}
            proxy = services.get("proxy", {}) or {}

            return {
                "success": True,
                "data": {
                    "hostname": result.get("hostname", "N/A"),
                    "dhcp_server": {
                        "domain_name": dhcp_server.get("domainName", "N/A"),
                        "lease_time": dhcp_server.get("leaseTime", "N/A"),
                        "min_address": dhcp_server.get("minAddress", "N/A"),
                        "max_address": dhcp_server.get("maxAddress", "N/A"),
                        "subnet_mask": dhcp_server.get("subnetMask", "N/A"),
                        "leases": dhcp_server.get("leases", []),
                    },
                    "proxy": {
                        "enabled": proxy.get("enabled", False),
                        "server_address": proxy.get("serverAddress", "N/A"),
                        "server_port": proxy.get("serverPort", "N/A"),
                        "username": proxy.get("username", ""),
                    },
                    "wired_refs": result.get("wired", []),
                    "wireless_refs": result.get("wireless", []),
                }
            }
        return {"success": False, "error": str(result)}

    def list_wired_interfaces(self) -> Dict[str, Any]:
        """
        Discover available wired interface indices.
        The 'wired' array under /configuration/system/network contains interface
        references (could be IDs as integers, dicts with 'id', or URI strings).
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        overview = self.get_network_overview()
        if not overview.get("success"):
            return overview

        wired = overview["data"].get("wired_refs", [])
        indices = []
        for item in wired:
            if isinstance(item, dict) and "id" in item:
                indices.append(item["id"])
            elif isinstance(item, int):
                indices.append(item)
            elif isinstance(item, str):
                # Could be a URI like ".../wired/0" â€” extract trailing integer
                try:
                    indices.append(int(item.rstrip("/").split("/")[-1]))
                except ValueError:
                    pass
        # Default to [0] if nothing parseable found (most ClickShare units have a single LAN)
        if not indices:
            indices = [0]
        return {
            "success": True,
            "data": {
                "interface_indices": indices,
                "hostname": overview["data"].get("hostname", "N/A"),
            }
        }

    def get_lan_settings(self, interface_index: int = None) -> Dict[str, Any]:
        """
        Get wired LAN settings including IP, MAC, gateway, DNS, etc.
        Endpoint: GET /configuration/system/network/wired/{index}

        Per API spec (page 45-48), the response contains:
        - macAddress, status, addressing ('DHCP' or 'Static'),
          ipAddress, subnetMask, defaultGateway, dnsServers, domain
        Note: The API does NOT return a 'linkSpeed' field.

        If interface_index is None, this method auto-discovers the correct
        index by trying values returned from list_wired_interfaces(), then
        falling back to indices 0..3.
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        # Get hostname from /network endpoint
        network_success, network_result, _ = self._make_request("GET", "configuration/system/network")
        hostname = "N/A"
        if network_success and isinstance(network_result, dict):
            hostname = network_result.get("hostname", "N/A")

        # Build a list of candidate indices to try
        candidates = []
        if interface_index is not None:
            candidates = [interface_index]
        else:
            # Try whatever the /network endpoint advertises first
            list_result = self.list_wired_interfaces()
            if list_result.get("success"):
                candidates = list(list_result["data"].get("interface_indices", []))
            # Fallback: try common indices
            for idx in [0, 1, 2, 3]:
                if idx not in candidates:
                    candidates.append(idx)

        last_error = None
        last_status = None
        for idx in candidates:
            success, result, status = self._make_request(
                "GET", f"configuration/system/network/wired/{idx}"
            )
            if success and isinstance(result, dict):
                # Per API: addressing is 'DHCP' or 'Static'
                addressing = result.get("addressing", "N/A")
                if isinstance(addressing, str) and addressing.lower() == "dhcp":
                    method_display = "DHCP (Automatic)"
                elif isinstance(addressing, str) and addressing.lower() == "static":
                    method_display = "Static (Manual)"
                else:
                    method_display = str(addressing)

                # dnsServers is an array per API spec
                dns_servers = result.get("dnsServers", [])
                if not isinstance(dns_servers, list):
                    dns_servers = [dns_servers] if dns_servers else []
                # Filter out empty entries
                dns_servers = [d for d in dns_servers if d]

                lan_data = {
                    "interface_index": result.get("id", idx),
                    "hostname": hostname,
                    "mac_address": result.get("macAddress", "N/A"),
                    "status": result.get("status", "N/A"),
                    "addressing": addressing,
                    "method": method_display,
                    "ip_address": result.get("ipAddress", "N/A"),
                    "subnet_mask": result.get("subnetMask", "N/A"),
                    "default_gateway": result.get("defaultGateway", "N/A"),
                    "dns_servers": dns_servers,
                    "domain": result.get("domain", ""),
                    "_raw_response": result,  # For debugging
                }
                return {"success": True, "data": lan_data}
            else:
                last_error = result
                last_status = status

        return {
            "success": False,
            "error": f"Could not fetch LAN settings from any interface index ({candidates}). Last error: {last_error}",
            "status_code": last_status
        }

    def set_lan_settings(self, addressing: str, ip_address: str = None, subnet_mask: str = None,
                         default_gateway: str = None, dns_servers: list = None,
                         domain: str = None, interface_index: int = None) -> Dict[str, Any]:
        """
        Configure wired LAN settings
        Endpoint: PATCH /configuration/system/network/wired/{index}

        Per API spec (page 49-52):
        - 'addressing': 'DHCP' or 'Static' (case-sensitive)
        - For Static: ipAddress, subnetMask, defaultGateway, dnsServers, domain

        If interface_index is None, auto-discovers from a successful GET.
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        # Auto-discover the working index by fetching settings first
        if interface_index is None:
            current = self.get_lan_settings()
            if current.get("success"):
                interface_index = current["data"].get("interface_index", 0)
            else:
                interface_index = 0

        # Normalize addressing â€” API is case-sensitive: 'DHCP' or 'Static'
        norm = addressing.strip().lower()
        if norm == "dhcp":
            addressing_normalized = "DHCP"
        elif norm == "static":
            addressing_normalized = "Static"
        else:
            return {"success": False, "error": f"Invalid addressing mode '{addressing}'. Use 'DHCP' or 'Static'."}

        payload = {"addressing": addressing_normalized}

        if addressing_normalized == "Static":
            if not all([ip_address, subnet_mask, default_gateway]):
                return {
                    "success": False,
                    "error": "Static IP requires ip_address, subnet_mask, and default_gateway"
                }
            payload["ipAddress"] = ip_address
            payload["subnetMask"] = subnet_mask
            payload["defaultGateway"] = default_gateway

            if dns_servers:
                if isinstance(dns_servers, str):
                    dns_servers = [dns_servers]
                payload["dnsServers"] = dns_servers
            if domain:
                payload["domain"] = domain

        success, result, status = self._make_request(
            "PATCH", f"configuration/system/network/wired/{interface_index}", payload
        )

        if success:
            return {
                "success": True,
                "message": f"LAN settings updated on interface {interface_index}. Device may need to reboot for changes to take effect.",
                "payload_sent": payload
            }
        return {
            "success": False,
            "error": str(result),
            "status_code": status,
            "payload_sent": payload,
            "endpoint": f"configuration/system/network/wired/{interface_index}"
        }

    def set_hostname(self, hostname: str) -> Dict[str, Any]:
        """
        Change device hostname.
        Endpoint: PATCH /configuration/system/network
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        payload = {"hostname": hostname}
        success, result, status = self._make_request("PATCH", "configuration/system/network", payload)

        if success:
            return {"success": True, "message": "Hostname updated successfully."}
        return {"success": False, "error": str(result)}

    # ==================== WIFI CONFIGURATION ====================

    def get_wifi_settings(self, interface_index: int = None) -> Dict[str, Any]:
        """
        Get wireless LAN settings.
        Endpoint: GET /configuration/system/network/wireless/{index}

        Per API spec (page 53-58): response contains operationMode
        ('AccessPoint', 'WirelessClient', 'Off'), accessPoint settings,
        macAddress, addressing, etc. If interface_index is None we try
        candidates from /network and fall back to 0..3.
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        # Auto-discover candidate indices if not supplied
        candidates = []
        if interface_index is not None:
            candidates = [interface_index]
        else:
            ov = self.get_network_overview()
            if ov.get("success"):
                wireless_refs = ov["data"].get("wireless_refs", [])
                for item in wireless_refs:
                    if isinstance(item, dict) and "id" in item:
                        candidates.append(item["id"])
                    elif isinstance(item, int):
                        candidates.append(item)
                    elif isinstance(item, str):
                        try:
                            candidates.append(int(item.rstrip("/").split("/")[-1]))
                        except ValueError:
                            pass
            for idx in [0, 1, 2, 3]:
                if idx not in candidates:
                    candidates.append(idx)

        last_error = None
        last_status = None
        for idx in candidates:
            success, result, status = self._make_request(
                "GET", f"configuration/system/network/wireless/{idx}"
            )
            if success and isinstance(result, dict):
                ap = result.get("accessPoint", {}) or {}
                supported_op_modes = result.get("supportedOperationModes", [])
                supported_freq = ap.get("supportedFrequencyBands", [])

                return {
                    "success": True,
                    "data": {
                        "interface_index": result.get("id", idx),
                        "operation_mode": result.get("operationMode", "N/A"),
                        "supported_operation_modes": supported_op_modes,
                        "mac_address": result.get("macAddress", "N/A"),
                        "addressing": result.get("addressing", "N/A"),
                        "ip_address": result.get("ipAddress", "N/A"),
                        "ssid": ap.get("ssid", "N/A"),
                        "broadcast_ssid": ap.get("broadcastSsid", True),
                        "frequency_band": ap.get("frequencyBand", "N/A"),
                        "supported_frequency_bands": supported_freq,
                        "channel": ap.get("channel", "N/A"),
                        "signal_strength": ap.get("signalStrengthPercentage", "N/A"),
                    }
                }
            else:
                last_error = result
                last_status = status

        return {
            "success": False,
            "error": f"Could not fetch WiFi settings from any interface index ({candidates}). Last error: {last_error}",
            "status_code": last_status
        }

    def set_wifi_settings(self, ssid: str = None, password: str = None,
                          frequency_band: str = None, broadcast_ssid: bool = None,
                          channel: int = None, operation_mode: str = None,
                          interface_index: int = None) -> Dict[str, Any]:
        """
        Configure wireless LAN settings.
        Endpoint: PATCH /configuration/system/network/wireless/{index}

        Per API spec (page 58-63):
        - operationMode: 'AccessPoint', 'WirelessClient', or 'Off'
        - accessPoint object with ssid, password, frequencyBand,
          broadcastSsid, channel
        - Top-level: addressing, ipAddress, etc. for client mode

        IMPORTANT: The WiFi PATCH requires the device to be in (or being
        moved to) 'AccessPoint' mode for AP-related fields to apply.
        If the device is currently in 'Off' mode, you must include
        operation_mode='AccessPoint' to enable it.

        All AP fields are optional in the payload â€” only what's provided
        will be sent, so the device keeps existing values for the rest.
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        # Auto-discover the working wireless index by GET
        if interface_index is None:
            current = self.get_wifi_settings()
            if current.get("success"):
                interface_index = current["data"].get("interface_index", 0)
                current_mode = current["data"].get("operation_mode")
            else:
                interface_index = 0
                current_mode = None
        else:
            current_mode = None

        # Build the access point sub-object only with provided values
        ap_payload = {}
        if ssid is not None and ssid != "":
            ap_payload["ssid"] = ssid
        if password is not None and password != "":
            ap_payload["password"] = password
        if frequency_band is not None and frequency_band != "":
            ap_payload["frequencyBand"] = frequency_band
        if broadcast_ssid is not None:
            ap_payload["broadcastSsid"] = bool(broadcast_ssid)
        if channel is not None:
            try:
                ap_payload["channel"] = int(channel)
            except (TypeError, ValueError):
                return {"success": False, "error": f"channel must be an integer, got {channel!r}"}

        payload = {}
        if ap_payload:
            payload["accessPoint"] = ap_payload

        # Operation mode: explicitly requested, or auto-add if AP fields are
        # being set while device is currently 'Off' (PATCH would silently
        # fail otherwise).
        if operation_mode:
            payload["operationMode"] = operation_mode
        elif ap_payload and current_mode and current_mode.lower() == "off":
            payload["operationMode"] = "AccessPoint"

        if not payload:
            return {"success": False, "error": "No WiFi fields provided to update."}

        success, result, status = self._make_request(
            "PATCH", f"configuration/system/network/wireless/{interface_index}", payload
        )

        if success:
            return {
                "success": True,
                "message": f"WiFi settings updated on interface {interface_index}. Buttons may need re-pairing.",
                "payload_sent": payload
            }
        return {
            "success": False,
            "error": str(result),
            "status_code": status,
            "payload_sent": payload,
            "endpoint": f"configuration/system/network/wireless/{interface_index}"
        }

    # ==================== DEVICE OPERATIONS ====================

    def reboot_device(self) -> Dict[str, Any]:
        """Reboot the Base Unit. Endpoint: POST /operations/reboot"""
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        success, result, status = self._make_request("POST", "operations/reboot")

        if success:
            return {"success": True, "message": "Device reboot initiated. Connection will be lost temporarily."}
        return {"success": False, "error": str(result)}

    def set_standby(self) -> Dict[str, Any]:
        """Put device in standby. Endpoint: POST /operations/standby"""
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        success, result, status = self._make_request("POST", "operations/standby")

        if success:
            return {"success": True, "message": "Device entering standby mode."}
        return {"success": False, "error": str(result)}

    def wakeup_device(self) -> Dict[str, Any]:
        """Wake device from standby. Endpoint: POST /operations/wakeup"""
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        success, result, status = self._make_request("POST", "operations/wakeup")

        if success:
            return {"success": True, "message": "Wakeup signal sent to device."}
        return {"success": False, "error": str(result)}

    def get_supported_operations(self) -> Dict[str, Any]:
        """
        Get the list of supported operations.
        Endpoint: GET /operations/supported
        """
        if not self.connected:
            return {"success": False, "error": "Not connected."}

        success, result, status = self._make_request("GET", "operations/supported")

        if success:
            return {"success": True, "data": result}
        return {"success": False, "error": str(result)}

    # ==================== POWER MANAGEMENT ====================

    def get_power_management(self) -> Dict[str, Any]:
        """
        Get current power management settings.
        Endpoint: GET /configuration/system/power-management

        Per API spec (page 63-64):
          - powerMode (e.g. 'EcoStandby', 'NetworkedStandby', 'DeepStandby')
          - standbyTimeout (minutes, or 'Infinite')
          - status (read-only â€” current system state: 'On' or 'Standby')
          - supportedPowerModes, supportedStandbyTimeouts, supportedStatuses
        """
        if not self.connected:
            return {"success": False, "error": "Not connected."}

        success, result, status = self._make_request(
            "GET", "configuration/system/power-management"
        )

        if success and isinstance(result, dict):
            return {
                "success": True,
                "data": {
                    "power_mode": result.get("powerMode", "N/A"),
                    "standby_timeout": result.get("standbyTimeout", "N/A"),
                    "current_status": result.get("status", "N/A"),
                    "supported_power_modes": result.get("supportedPowerModes", []),
                    "supported_standby_timeouts": result.get("supportedStandbyTimeouts", []),
                    "supported_statuses": result.get("supportedStatuses", []),
                }
            }
        return {"success": False, "error": str(result)}

    def set_power_management(self, power_mode: str = None,
                              standby_timeout: str = None) -> Dict[str, Any]:
        """
        Change power management settings.
        Endpoint: PATCH /configuration/system/power-management

        Args:
            power_mode: One of 'EcoStandby', 'NetworkedStandby', 'DeepStandby'
            standby_timeout: Minutes ('1', '5', '10', '15', '30', '45', '60')
                             or 'Infinite' to disable
        """
        if not self.connected:
            return {"success": False, "error": "Not connected."}

        if not power_mode and not standby_timeout:
            return {"success": False, "error": "Provide power_mode and/or standby_timeout."}

        payload = {}
        if power_mode:
            payload["powerMode"] = power_mode
        if standby_timeout:
            payload["standbyTimeout"] = str(standby_timeout)

        success, result, status = self._make_request(
            "PATCH", "configuration/system/power-management", payload
        )

        if success:
            return {"success": True, "message": "Power management settings updated.", "payload_sent": payload}
        return {"success": False, "error": str(result), "status_code": status, "payload_sent": payload}

    # ==================== USER MANAGEMENT ====================

    def change_user_password(self, username: str, new_password: str) -> Dict[str, Any]:
        """
        Change the password for a specified user.
        Endpoint: PATCH /configuration/users/{username}

        IMPORTANT: After changing the admin password, subsequent API calls
        will fail until the plugin is reconnected with the new credentials.
        """
        if not self.connected:
            return {"success": False, "error": "Not connected."}

        if not username or not new_password:
            return {"success": False, "error": "username and new_password are required."}

        payload = {"password": new_password}
        success, result, status = self._make_request(
            "PATCH", f"configuration/users/{username}", payload
        )

        if success:
            # If we changed our own password, future calls will fail â€”
            # update internal credentials so reconnection works seamlessly
            if username == self.username:
                self.password = new_password
                msg = (f"Password changed for user '{username}'. "
                       f"Internal credentials updated to use the new password.")
            else:
                msg = f"Password changed for user '{username}'."
            return {"success": True, "message": msg}
        return {"success": False, "error": str(result), "status_code": status}

    # ==================== PERIPHERALS ====================

    def _summarize_sub_devices(self, sub_list: list, kind: str) -> list:
        """
        Helper: each peripheral can expose lists of cameras / microphones /
        speakers / touchscreens. The API doesn't strictly define each item's
        shape, so pull the most useful fields defensively.
        """
        result = []
        if not isinstance(sub_list, list):
            return result
        for item in sub_list:
            if isinstance(item, dict):
                result.append({
                    "kind": kind,
                    "name": item.get("name", "N/A"),
                    "vendor": item.get("vendor", "N/A"),
                    "serial_number": item.get("serialNumber", "N/A"),
                    "version": item.get("version", "N/A"),
                    "product_id": item.get("productId", "N/A"),
                    "vendor_id": item.get("vendorId", "N/A"),
                })
            elif isinstance(item, str):
                result.append({"kind": kind, "name": item})
        return result

    def get_peripherals(self) -> Dict[str, Any]:
        """
        Get the list of (USB) peripherals connected to the Base Unit.
        Endpoint: GET /configuration/peripherals

        Per API spec (page 35-36), each peripheral exposes:
          id, name, vendor, vendorId, pluggedIn, version, usbSignature,
          combinedRevision, serialNumber, and arrays for cameras,
          microphones, speakers, touchscreens.
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        success, result, status = self._make_request("GET", "configuration/peripherals")

        if not success:
            return {"success": False, "error": str(result), "status_code": status}

        # API may return list directly, or an object with 'peripherals'
        peripherals_raw = result if isinstance(result, list) else result.get("peripherals", [])
        if not isinstance(peripherals_raw, list):
            peripherals_raw = []

        peripherals = []
        for p in peripherals_raw:
            if not isinstance(p, dict):
                continue
            peripherals.append({
                "id": p.get("id", "N/A"),
                "name": p.get("name", "N/A"),
                "vendor": p.get("vendor", "N/A"),
                "vendor_id": p.get("vendorId", "N/A"),
                "plugged_in": p.get("pluggedIn", False),
                "firmware_version": p.get("version", "N/A"),
                "usb_signature": p.get("usbSignature", "N/A"),
                "combined_revision": p.get("combinedRevision", "N/A"),
                "serial_number": p.get("serialNumber", "N/A"),
                "cameras": self._summarize_sub_devices(p.get("cameras", []), "Camera"),
                "microphones": self._summarize_sub_devices(p.get("microphones", []), "Microphone"),
                "speakers": self._summarize_sub_devices(p.get("speakers", []), "Speaker"),
                "touchscreens": self._summarize_sub_devices(p.get("touchscreens", []), "Touchscreen"),
            })

        return {
            "success": True,
            "data": {
                "count": len(peripherals),
                "peripherals": peripherals,
            }
        }

    def get_peripheral_by_id(self, peripheral_id: int) -> Dict[str, Any]:
        """
        Get a specific peripheral.
        Endpoint: GET /configuration/peripherals/{index}
        """
        if not self.connected:
            return {"success": False, "error": "Not connected. Please connect first."}

        success, result, status = self._make_request(
            "GET", f"configuration/peripherals/{peripheral_id}"
        )

        if not success:
            return {"success": False, "error": str(result), "status_code": status}

        if isinstance(result, dict):
            return {
                "success": True,
                "data": {
                    "id": result.get("id", "N/A"),
                    "name": result.get("name", "N/A"),
                    "vendor": result.get("vendor", "N/A"),
                    "vendor_id": result.get("vendorId", "N/A"),
                    "plugged_in": result.get("pluggedIn", False),
                    "firmware_version": result.get("version", "N/A"),
                    "usb_signature": result.get("usbSignature", "N/A"),
                    "combined_revision": result.get("combinedRevision", "N/A"),
                    "serial_number": result.get("serialNumber", "N/A"),
                    "cameras": self._summarize_sub_devices(result.get("cameras", []), "Camera"),
                    "microphones": self._summarize_sub_devices(result.get("microphones", []), "Microphone"),
                    "speakers": self._summarize_sub_devices(result.get("speakers", []), "Speaker"),
                    "touchscreens": self._summarize_sub_devices(result.get("touchscreens", []), "Touchscreen"),
                }
            }
        return {"success": False, "error": "Unexpected response format"}


# ==================== INTERACTIVE MENU SYSTEM ====================

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_success(message: str):
    print(f"\n[OK] {message}")


def print_error(message: str):
    print(f"\n[ERROR] {message}")


def print_info(message: str):
    print(f"\n[INFO] {message}")


def print_warning(message: str):
    print(f"\n[WARNING] {message}")


def print_section(title: str):
    print(f"\n--- {title} ---")


def get_input(prompt: str, default: str = None) -> str:
    if default is not None:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()


def get_yes_no(prompt: str) -> bool:
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'")


def display_device_info(plugin: BarcoClickSharePlugin):
    """Display device information"""
    print_header("DEVICE INFORMATION")

    result = plugin.get_full_device_info()

    if result.get("success"):
        data = result.get("data", {})
        print(f"\n  Make:              {data.get('make', 'N/A')}")
        print(f"  Product Name:      {data.get('product_name', 'N/A')}")
        print(f"  Model Name:        {data.get('model_name', 'N/A')}")
        print(f"  Serial Number:     {data.get('serial_number', 'N/A')}")
        print(f"  Article Number:    {data.get('article_number', 'N/A')}")
        print(f"  Hardware Version:  {data.get('hardware_version', 'N/A')}")
        print(f"  Firmware Version:  {data.get('firmware_version', 'N/A')}")
        print(f"  Last Update:       {data.get('last_update_date', 'N/A')}")
        print(f"  Hostname:          {data.get('hostname', 'N/A')}")
        print(f"  IP Address:        {data.get('ip_address', 'N/A')}")
        print(f"  MAC Address:       {data.get('mac_address', 'N/A')}")
        print(f"  IP Method:         {data.get('addressing', 'N/A')}")
        print(f"  Overall Status:    {data.get('overall_status', 'N/A')}")
        print(f"  Uptime:            {data.get('uptime_formatted', 'N/A')}")
        print(f"  In Use:            {'Yes' if data.get('in_use') else 'No'}")
        print(f"  Sharing Active:    {'Yes' if data.get('sharing_active') else 'No'}")
    else:
        print_error(f"Failed to get device info: {result.get('error')}")

    input("\nPress Enter to continue...")


def show_network_settings(plugin: BarcoClickSharePlugin):
    """Show all network settings"""
    print_header("NETWORK SETTINGS")

    # Top-level network info (hostname, DHCP server, proxy)
    overview = plugin.get_network_overview()
    if overview.get("success"):
        ov = overview["data"]
        print_section("Base Unit Network Info")
        print(f"\n  Hostname:          {ov.get('hostname', 'N/A')}")

        dhcp = ov.get("dhcp_server", {})
        print(f"\n  DHCP Server (internal AP):")
        print(f"    Domain Name:     {dhcp.get('domain_name', 'N/A')}")
        print(f"    Subnet Mask:     {dhcp.get('subnet_mask', 'N/A')}")
        print(f"    IP Range:        {dhcp.get('min_address', 'N/A')} - {dhcp.get('max_address', 'N/A')}")
        print(f"    Lease Time:      {dhcp.get('lease_time', 'N/A')} seconds")
        leases = dhcp.get("leases", [])
        print(f"    Active Leases:   {len(leases) if isinstance(leases, list) else 'N/A'}")

        proxy = ov.get("proxy", {})
        print(f"\n  Proxy:")
        print(f"    Enabled:         {'Yes' if proxy.get('enabled') else 'No'}")
        if proxy.get("enabled"):
            print(f"    Server:          {proxy.get('server_address', 'N/A')}:{proxy.get('server_port', 'N/A')}")
            print(f"    Username:        {proxy.get('username', '') or 'N/A'}")
    else:
        print_error(f"Failed to get network overview: {overview.get('error')}")

    print_section("LAN / Wired Network Settings")
    lan = plugin.get_lan_settings()

    if lan.get("success"):
        data = lan.get("data", {})
        print(f"\n  {'='*50}")
        print(f"  INTERFACE INFORMATION")
        print(f"  {'='*50}")
        print(f"  Interface Index:   {data.get('interface_index', 'N/A')}")
        print(f"  MAC Address:       {data.get('mac_address', 'N/A')}")
        print(f"  Link Status:       {data.get('status', 'N/A')}")

        print(f"\n  {'='*50}")
        print(f"  IP CONFIGURATION")
        print(f"  {'='*50}")
        print(f"  Hostname:          {data.get('hostname', 'N/A')}")
        print(f"  Method:            {data.get('method', 'N/A')}")
        print(f"  IP Address:        {data.get('ip_address', 'N/A')}")
        print(f"  Subnet Mask:       {data.get('subnet_mask', 'N/A')}")
        print(f"  Default Gateway:   {data.get('default_gateway', 'N/A')}")

        print(f"\n  {'='*50}")
        print(f"  DNS CONFIGURATION")
        print(f"  {'='*50}")
        dns_list = data.get('dns_servers', [])
        print(f"  DNS Servers:       {', '.join(dns_list) if dns_list else 'N/A'}")
        print(f"  Domain:            {data.get('domain') or 'N/A'}")
    else:
        print_error(f"Failed to get LAN settings: {lan.get('error')}")

    print_section("WiFi Settings")
    wifi = plugin.get_wifi_settings()
    if wifi.get("success"):
        data = wifi.get("data", {})
        print(f"\n  Operation Mode:    {data.get('operation_mode', 'N/A')}")
        print(f"  WiFi MAC:          {data.get('mac_address', 'N/A')}")
        print(f"  SSID:              {data.get('ssid', 'N/A')}")
        print(f"  Broadcast SSID:    {'Yes' if data.get('broadcast_ssid') else 'No'}")
        print(f"  Frequency Band:    {data.get('frequency_band', 'N/A')}")
        print(f"  Channel:           {data.get('channel', 'N/A')}")
        print(f"  Signal Strength:   {data.get('signal_strength', 'N/A')}%")
    else:
        print_error(f"Failed to get WiFi settings: {wifi.get('error')}")

    input("\nPress Enter to continue...")


def show_peripherals(plugin: BarcoClickSharePlugin):
    """
    Show connected peripherals grouped by device type:
    Cameras, Microphones, Speakers (and Touchscreens if any).
    For each, display the parent USB peripheral's info.

    Note: The ClickShare API often reports the same composite USB device
    (e.g., Poly Studio P15) as multiple peripheral entries with overlapping
    sub-device arrays. We deduplicate by (parent_serial, device_type) so
    one physical mic+speaker+camera unit shows up once per type.
    """
    print_header("PERIPHERALS")
    print_info("Fetching connected peripherals...")

    result = plugin.get_peripherals()

    if not result.get("success"):
        print_error(f"Failed to get peripherals: {result.get('error')}")
        input("\nPress Enter to continue...")
        return

    data = result.get("data", {})
    count = data.get("count", 0)
    peripherals = data.get("peripherals", [])

    if count == 0:
        print_info("No USB peripherals connected to this Base Unit.")
        input("\nPress Enter to continue...")
        return

    # Group with deduplication. Key: (parent_serial_or_name, device_type)
    # Only add a sub-device if the sub-array is non-empty AND the entry
    # contributes new info â€” for composite devices, the API may populate
    # all four arrays on every peripheral record, so the parent serial is
    # the most reliable dedup anchor.
    grouped = {
        "Camera": [],
        "Microphone": [],
        "Speaker": [],
        "Touchscreen": [],
    }
    seen_keys = set()

    type_keys = [
        ("Camera", "cameras"),
        ("Microphone", "microphones"),
        ("Speaker", "speakers"),
        ("Touchscreen", "touchscreens"),
    ]

    for p in peripherals:
        parent_serial = p.get("serial_number", "") or ""
        parent_name = p.get("name", "") or ""
        # Use parent serial as the dedup key when present, fall back to name
        dedup_anchor = parent_serial.strip() or parent_name.strip()

        for label, key in type_keys:
            sub_list = p.get(key, []) or []
            if not sub_list:
                continue

            for sub in sub_list:
                # Extract identifying fields from the sub-device, defending
                # against missing keys.
                if isinstance(sub, dict):
                    sub_serial = (sub.get("serial_number") or "").strip()
                    sub_name = (sub.get("name") or "").strip()
                    sub_vendor = (sub.get("vendor") or "").strip()
                    if sub_serial in ("", "N/A"):
                        sub_serial = ""
                    if sub_name in ("", "N/A"):
                        sub_name = ""
                    if sub_vendor in ("", "N/A"):
                        sub_vendor = ""
                else:
                    sub_serial = sub_name = sub_vendor = ""

                # Phantom-entry filter: some firmware versions populate
                # every sub-array on every peripheral record with an empty
                # placeholder ({}, or {serial: '', name: '', vendor: ''}).
                # If the sub-device has no serial of its own AND no name
                # AND no vendor, treat it as "this peripheral does NOT
                # actually expose this device type" and skip it.
                # (The real device shows up on the OTHER peripheral entry
                # with a populated serial.)
                has_own_data = bool(sub_serial or sub_name or sub_vendor)
                if not has_own_data:
                    # Heuristic: if NO peripheral entry in the whole list
                    # has populated data for this sub-type, then it's truly
                    # absent from the system. We can detect that lazily by
                    # only adding placeholder entries on the FIRST pass and
                    # then suppressing them at the end if no real one shows
                    # up for this type. Simpler: just skip the placeholder.
                    continue

                # Build the dedup key. Prefer sub-device serial if present,
                # otherwise fall back to parent serial.
                key_serial = sub_serial or dedup_anchor
                dedup_key = (key_serial, label)

                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                grouped[label].append({
                    "name": p.get("name", "N/A"),
                    "vendor": p.get("vendor", "N/A"),
                    "vendor_id": p.get("vendor_id", "N/A"),
                    "plugged_in": p.get("plugged_in", False),
                    "firmware_version": p.get("firmware_version", "N/A"),
                    "serial_number": sub_serial or parent_serial or "N/A",
                })

    total_devices = sum(len(v) for v in grouped.values())
    print(f"\n  Total devices found: {total_devices}")
    print(f"  (across {count} USB peripheral entries reported by the Base Unit)\n")

    if total_devices == 0:
        print_info("USB peripherals are connected but no Camera/Mic/Speaker info was reported.")
        input("\nPress Enter to continue...")
        return

    type_order = ["Camera", "Microphone", "Speaker", "Touchscreen"]
    for device_type in type_order:
        devices = grouped[device_type]
        if not devices:
            continue

        plural = device_type + "s"
        print(f"  {'='*50}")
        print(f"  {plural.upper()} ({len(devices)})")
        print(f"  {'='*50}")

        for idx, dev in enumerate(devices, start=1):
            if len(devices) > 1:
                print(f"\n  {device_type} #{idx}")
                print(f"  {'-'*30}")
            else:
                print()
            print(f"  Name:              {dev.get('name', 'N/A')}")
            print(f"  Vendor:            {dev.get('vendor', 'N/A')}")
            print(f"  Vendor ID:         {dev.get('vendor_id', 'N/A')}")
            print(f"  Plugged In:        {'Yes' if dev.get('plugged_in') else 'No'}")
            fw = dev.get('firmware_version', 'N/A')
            print(f"  Firmware Version:  {fw if fw else 'N/A'}")
            print(f"  Serial Number:     {dev.get('serial_number', 'N/A')}")
        print()

    input("\nPress Enter to continue...")


def configure_lan(plugin: BarcoClickSharePlugin):
    """Configure LAN settings"""
    print_header("LAN CONFIGURATION")

    print_info("Fetching current LAN settings...")
    current = plugin.get_lan_settings()

    if current.get("success"):
        data = current.get("data", {})
        print(f"\n  {'='*50}")
        print(f"  CURRENT CONFIGURATION")
        print(f"  {'='*50}")
        print(f"  MAC Address:       {data.get('mac_address', 'N/A')}")
        print(f"  Link Status:       {data.get('status', 'N/A')}")
        print(f"  Method:            {data.get('method', 'N/A')}")
        print(f"  IP Address:        {data.get('ip_address', 'N/A')}")
        print(f"  Subnet Mask:       {data.get('subnet_mask', 'N/A')}")
        print(f"  Default Gateway:   {data.get('default_gateway', 'N/A')}")
        dns_list = data.get('dns_servers', [])
        print(f"  DNS Servers:       {', '.join(dns_list) if dns_list else 'N/A'}")
    else:
        print_error(f"Failed to get LAN settings: {current.get('error')}")
        input("Press Enter to continue...")
        return

    print_section("Configure New Settings")
    print("\n  Select IP Assignment Method:")
    print("    1. DHCP (Automatic - Get IP from router)")
    print("    2. Static (Manual - Set fixed IP)")
    choice = get_input("  Select option (1-2)", "1")

    if choice == "1":
        if not get_yes_no("\n  Switch to DHCP mode"):
            print_info("Configuration cancelled")
            input("\nPress Enter to continue...")
            return
        print_info("Setting to DHCP mode...")
        result = plugin.set_lan_settings("DHCP")
        if result.get("success"):
            print_success("LAN set to DHCP mode. Device may need to reboot to apply changes.")
        else:
            print_error(f"Failed to configure LAN: {result.get('error')}")

    elif choice == "2":
        print("\n  Enter Static IP Configuration:")
        ip_address = get_input("    IP Address",
                                data.get('ip_address') if data.get('ip_address') != 'N/A' else "192.168.1.100")
        subnet_mask = get_input("    Subnet Mask",
                                 data.get('subnet_mask') if data.get('subnet_mask') != 'N/A' else "255.255.255.0")
        default_gateway = get_input("    Default Gateway",
                                     data.get('default_gateway') if data.get('default_gateway') != 'N/A' else "192.168.1.1")
        dns1 = get_input("    Primary DNS Server", "8.8.8.8")
        dns2 = get_input("    Secondary DNS Server (optional, press Enter to skip)", "")
        domain = get_input("    Domain (optional, press Enter to skip)", "")

        dns_servers = [dns1] if dns1 else []
        if dns2:
            dns_servers.append(dns2)

        print("\n  Summary of settings:")
        print(f"    Method:          Static")
        print(f"    IP Address:      {ip_address}")
        print(f"    Subnet Mask:     {subnet_mask}")
        print(f"    Default Gateway: {default_gateway}")
        print(f"    DNS Servers:     {', '.join(dns_servers) if dns_servers else 'N/A'}")
        if domain:
            print(f"    Domain:          {domain}")

        if get_yes_no("\n  Apply these settings"):
            print_info("Applying static IP configuration...")
            result = plugin.set_lan_settings(
                "Static", ip_address, subnet_mask, default_gateway,
                dns_servers if dns_servers else None,
                domain if domain else None
            )

            if result.get("success"):
                print_success("Static IP configuration applied. Device may need reboot.")
                print_info("Note: If you changed the IP address, reconnect using the new IP.")
            else:
                print_error(f"Failed to configure LAN: {result.get('error')}")
        else:
            print_info("Configuration cancelled")
    else:
        print_error("Invalid option")

    input("\nPress Enter to continue...")


def configure_wifi(plugin: BarcoClickSharePlugin):
    """Configure WiFi settings"""
    print_header("WIFI CONFIGURATION")

    print_info("Fetching current WiFi settings...")
    current = plugin.get_wifi_settings()

    if not current.get("success"):
        print_error(f"Failed to get WiFi settings: {current.get('error')}")
        input("Press Enter to continue...")
        return

    data = current.get("data", {})
    op_mode = data.get("operation_mode", "N/A")
    supported_modes = data.get("supported_operation_modes", [])
    supported_freq = data.get("supported_frequency_bands", [])

    print(f"\n  Current Configuration:")
    print(f"    Interface Index: {data.get('interface_index', 'N/A')}")
    print(f"    Operation Mode:  {op_mode}")
    if supported_modes:
        print(f"    Supported Modes: {', '.join(supported_modes)}")
    print(f"    MAC:             {data.get('mac_address', 'N/A')}")
    print(f"    SSID:            {data.get('ssid', 'N/A')}")
    print(f"    Broadcast:       {'Yes' if data.get('broadcast_ssid') else 'No'}")
    print(f"    Frequency Band:  {data.get('frequency_band', 'N/A')}")
    print(f"    Channel:         {data.get('channel', 'N/A')}")

    # Warn if device is in a mode where AP changes won't apply directly
    op_mode_lower = op_mode.lower() if isinstance(op_mode, str) else ""
    if op_mode_lower == "off":
        print_warning("WiFi is currently OFF. Applying settings will also enable AccessPoint mode.")
    elif op_mode_lower == "wirelessclient":
        print_warning("WiFi is in WirelessClient mode (connecting to an external AP). "
                      "AP-related settings (SSID/password) won't take effect unless "
                      "you switch to AccessPoint mode.")

    print_section("Configure New Settings")
    print_info("Press Enter to keep the current value for any field.")

    ssid = get_input("  SSID (Network Name)", data.get('ssid', 'ClickShare'))
    password = get_input("  Password (leave blank to keep current)", "")

    # Build frequency band prompt from what the device supports
    if supported_freq:
        print("\n  Frequency Band:")
        for i, band in enumerate(supported_freq, 1):
            print(f"    {i}. {band}")
        sel = get_input(
            f"  Select band number",
            "2" if len(supported_freq) >= 2 else "1"
        )
        try:
            idx = int(sel) - 1
            frequency_band = supported_freq[idx] if 0 <= idx < len(supported_freq) else supported_freq[-1]
        except ValueError:
            frequency_band = sel
    else:
        print("\n  Frequency Band:")
        print("    1. 2.4 GHz")
        print("    2. 5 GHz (recommended)")
        band_choice = get_input("  Select option (1-2)", "2")
        frequency_band = "2.4 GHz" if band_choice == "1" else "5 GHz"

    broadcast = get_yes_no("  Broadcast SSID (visible to devices)")

    # Optional channel override
    channel_input = get_input("  Channel (leave blank for auto/keep current)", "")
    channel = None
    if channel_input:
        try:
            channel = int(channel_input)
        except ValueError:
            print_warning(f"Invalid channel '{channel_input}', will not be sent.")
            channel = None

    # If the device isn't already in AP mode, ask whether to switch
    operation_mode = None
    if op_mode_lower in ("off", "wirelessclient"):
        if get_yes_no(f"  Switch operationMode to 'AccessPoint' (current: {op_mode})"):
            operation_mode = "AccessPoint"

    print(f"\n  Will send:")
    print(f"    SSID:           {ssid}")
    print(f"    Password:       {'(unchanged)' if not password else '(set)'}")
    print(f"    Frequency Band: {frequency_band}")
    print(f"    Broadcast:      {'Yes' if broadcast else 'No'}")
    if channel is not None:
        print(f"    Channel:        {channel}")
    if operation_mode:
        print(f"    Operation Mode: {operation_mode}")

    if not get_yes_no("\n  Apply these settings"):
        print_info("Configuration cancelled")
        input("\nPress Enter to continue...")
        return

    print_info("Applying WiFi settings...")
    result = plugin.set_wifi_settings(
        ssid=ssid if ssid else None,
        password=password if password else None,
        frequency_band=frequency_band,
        broadcast_ssid=broadcast,
        channel=channel,
        operation_mode=operation_mode,
    )

    if result.get("success"):
        print_success(result.get("message", "WiFi settings applied."))
        print_info("Buttons paired to this Base Unit may need re-pairing.")
    else:
        print_error(f"Failed to configure WiFi: {result.get('error')}")
        if result.get("payload_sent"):
            print_info(f"Payload sent: {result.get('payload_sent')}")
        if result.get("status_code"):
            print_info(f"HTTP status: {result.get('status_code')}")

    input("\nPress Enter to continue...")


def reboot_device(plugin: BarcoClickSharePlugin):
    """Reboot device with confirmation"""
    print_header("REBOOT DEVICE")

    print_info("This will reboot the ClickShare Base Unit.")
    print_info("The device will be unavailable for a few minutes.")
    print_warning("All current meetings/sharing will be interrupted!")

    if get_yes_no("\nAre you sure you want to reboot"):
        result = plugin.reboot_device()
        if result.get("success"):
            print_success("Reboot command sent. Device is restarting...")
            plugin.connected = False
        else:
            print_error(f"Failed to reboot: {result.get('error')}")
    else:
        print_info("Reboot cancelled")

    input("\nPress Enter to continue...")


def manage_power(plugin: BarcoClickSharePlugin):
    """View and configure power management settings."""
    print_header("POWER MANAGEMENT")

    print_info("Fetching current power settings...")
    current = plugin.get_power_management()

    if not current.get("success"):
        print_error(f"Failed to get power settings: {current.get('error')}")
        input("\nPress Enter to continue...")
        return

    data = current["data"]
    print(f"\n  Current Status:        {data.get('current_status', 'N/A')}")
    print(f"  Power Mode:            {data.get('power_mode', 'N/A')}")
    print(f"  Standby Timeout (min): {data.get('standby_timeout', 'N/A')}")

    supported_modes = data.get("supported_power_modes", [])
    supported_timeouts = data.get("supported_standby_timeouts", [])

    print_section("Configure")
    print("\n  1. Change Power Mode")
    print("  2. Change Standby Timeout")
    print("  3. Change Both")
    print("  4. Cancel")
    choice = get_input("  Select option (1-4)", "4")

    new_mode = None
    new_timeout = None

    if choice in ("1", "3"):
        if supported_modes:
            print("\n  Supported power modes:")
            for i, m in enumerate(supported_modes, 1):
                print(f"    {i}. {m}")
            sel = get_input("  Select mode number (or type a name)", "1")
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(supported_modes):
                    new_mode = supported_modes[idx]
                else:
                    new_mode = sel
            except ValueError:
                new_mode = sel
        else:
            new_mode = get_input("  Power mode (e.g. EcoStandby, NetworkedStandby, DeepStandby)")

    if choice in ("2", "3"):
        if supported_timeouts:
            print("\n  Supported standby timeouts (minutes):")
            for i, t in enumerate(supported_timeouts, 1):
                print(f"    {i}. {t}")
            sel = get_input("  Select timeout number (or type a value)", "1")
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(supported_timeouts):
                    new_timeout = supported_timeouts[idx]
                else:
                    new_timeout = sel
            except ValueError:
                new_timeout = sel
        else:
            new_timeout = get_input("  Standby timeout in minutes (or 'Infinite')", "Infinite")

    if choice == "4":
        print_info("Cancelled.")
        input("\nPress Enter to continue...")
        return

    print(f"\n  Will set:")
    if new_mode:
        print(f"    Power Mode:      {new_mode}")
    if new_timeout:
        print(f"    Standby Timeout: {new_timeout}")

    if get_yes_no("\n  Apply these settings"):
        result = plugin.set_power_management(power_mode=new_mode, standby_timeout=new_timeout)
        if result.get("success"):
            print_success(result.get("message", "Updated."))
        else:
            print_error(f"Failed: {result.get('error')}")
    else:
        print_info("Cancelled.")

    input("\nPress Enter to continue...")


def standby_wakeup_menu(plugin: BarcoClickSharePlugin):
    """Standby / Wakeup operations."""
    print_header("STANDBY / WAKEUP")
    print("\n  1. Put device into Standby")
    print("  2. Wake device from Standby")
    print("  3. Show current status")
    print("  4. Cancel")
    choice = get_input("  Select option (1-4)", "4")

    if choice == "1":
        if get_yes_no("  Confirm: put device in standby"):
            result = plugin.set_standby()
            if result.get("success"):
                print_success(result.get("message"))
            else:
                print_error(f"Failed: {result.get('error')}")
    elif choice == "2":
        result = plugin.wakeup_device()
        if result.get("success"):
            print_success(result.get("message"))
        else:
            print_error(f"Failed: {result.get('error')}")
    elif choice == "3":
        result = plugin.get_power_management()
        if result.get("success"):
            print(f"\n  Current Status: {result['data'].get('current_status', 'N/A')}")
        else:
            print_error(f"Failed: {result.get('error')}")
    else:
        print_info("Cancelled.")

    input("\nPress Enter to continue...")


def change_password(plugin: BarcoClickSharePlugin):
    """Change a user password via PATCH /configuration/users/{username}."""
    print_header("CHANGE USER PASSWORD")

    print_warning("After changing the admin password, you must reconnect "
                  "if you log out. The plugin will keep working in this session.")

    username = get_input("  Username to update", plugin.username)
    if not username:
        print_error("Username is required.")
        input("\nPress Enter to continue...")
        return

    new_password = get_input("  New password")
    if not new_password:
        print_error("New password cannot be empty.")
        input("\nPress Enter to continue...")
        return

    confirm = get_input("  Confirm new password")
    if new_password != confirm:
        print_error("Passwords do not match.")
        input("\nPress Enter to continue...")
        return

    if not get_yes_no(f"  Change password for user '{username}'"):
        print_info("Cancelled.")
        input("\nPress Enter to continue...")
        return

    result = plugin.change_user_password(username, new_password)
    if result.get("success"):
        print_success(result.get("message"))
    else:
        print_error(f"Failed: {result.get('error')}")

    input("\nPress Enter to continue...")


def main_menu():
    """Main interactive menu"""
    clear_screen()
    print_header("BARCO CLICKSHARE MANAGEMENT PLATFORM")

    print("\n  This plugin allows you to manage Barco ClickShare devices")
    print("  through the REST API v2 interface.")

    print("\n  Features:")
    print("    - View device information (make, model, serial, firmware)")
    print("    - View / configure LAN settings (DHCP/Static, IP, DNS)")
    print("    - Configure WiFi settings")
    print("    - View connected peripherals (cameras, mics, speakers)")
    print("    - Power management (Standby timeout, Eco/Networked/Deep)")
    print("    - Standby / Wakeup")
    print("    - Change user password")
    print("    - Reboot device")

    print_header("DEVICE CONNECTION")
    print("\n  Please enter the device connection details:")
    print_info("Default credentials are usually admin/admin")

    ip_address = get_input("  IP Address", "192.168.1.100")
    username = get_input("  Username", "admin")
    password = get_input("  Password", "admin")

    plugin = BarcoClickSharePlugin(ip_address, username, password)

    print_info("\nConnecting to device...")
    result = plugin.connect()

    if not result.get("success"):
        print_error(f"Connection failed: {result.get('error')}")
        print("\n  Troubleshooting tips:")
        print("    1. Verify the device IP address is correct")
        print("    2. Ensure the device is powered on and reachable")
        print("    3. Try: ping " + ip_address)
        print("    4. Check if HTTPS is enabled on port 4003")
        print("    5. Try: curl -k -u admin:admin https://" + ip_address +
              ":4003/v2/configuration/system/device-identity")
        print("    6. Verify username/password")
        input("\nPress Enter to exit...")
        return

    data = result.get("data", {})
    print_success(f"Connected to {data.get('product_name', 'ClickShare')}")
    print(f"  Serial Number: {data.get('serial_number', 'N/A')}")
    print(f"  Model: {data.get('model_name', 'N/A')}")

    while True:
        clear_screen()
        print_header("BARCO CLICKSHARE MANAGER")
        print(f"\n  Connected to: {ip_address}")
        print(f"  Device: {data.get('product_name', 'ClickShare')}")
        print(f"  Serial: {data.get('serial_number', 'N/A')}")

        print("\n" + "-" * 40)
        print("\n  MAIN MENU")
        print("-" * 40)
        print("\n   1. Device Information")
        print("   2. Show Network Settings (LAN + WiFi)")
        print("   3. Configure LAN Settings (IP, Gateway, DNS)")
        print("   4. Configure WiFi Settings")
        print("   5. Show Peripherals (Cameras, Mics, Speakers)")
        print("   6. Power Management")
        print("   7. Standby / Wakeup")
        print("   8. Change User Password")
        print("   9. Reboot Device")
        print("  10. Reconnect to Different Device")
        print("  11. Exit")

        choice = get_input("\n  Select option (1-11)", "11")

        if choice == "1":
            display_device_info(plugin)
        elif choice == "2":
            show_network_settings(plugin)
        elif choice == "3":
            configure_lan(plugin)
        elif choice == "4":
            configure_wifi(plugin)
        elif choice == "5":
            show_peripherals(plugin)
        elif choice == "6":
            manage_power(plugin)
        elif choice == "7":
            standby_wakeup_menu(plugin)
        elif choice == "8":
            change_password(plugin)
        elif choice == "9":
            reboot_device(plugin)
        elif choice == "10":
            print_info("Returning to connection screen...")
            input("Press Enter to continue...")
            main_menu()
            return
        elif choice == "11":
            print_header("EXIT")
            print("\n  Thank you for using Barco ClickShare Manager!")
            print("  Goodbye!\n")
            sys.exit(0)
        else:
            print_error("Invalid option. Please try again.")
            input("\nPress Enter to continue...")


# ==================== PLUGIN ENTRY POINT ====================

def create_plugin(ip_address: str, username: str, password: str) -> BarcoClickSharePlugin:
    """
    Factory function for UI integration.
    Returns a BarcoClickSharePlugin instance.
    """
    return BarcoClickSharePlugin(ip_address, username, password)


def get_device_info_ui(ip_address: str, username: str, password: str) -> Dict[str, Any]:
    """
    UI integration function - Get device info without interactive menu.
    """
    plugin = BarcoClickSharePlugin(ip_address, username, password)
    result = plugin.connect()

    if result.get("success"):
        full_info = plugin.get_full_device_info()
        return full_info
    return result


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n  Goodbye!\n")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        input("\nPress Enter to exit...")


