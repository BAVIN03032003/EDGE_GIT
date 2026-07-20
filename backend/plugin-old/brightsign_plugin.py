
# """
# Manual Platform Plugin: brightsign_plugin.py
# """
 
# import json
# import base64
 
# import requests
# from requests.auth import HTTPDigestAuth
 
# from .base import ManualPlatformPlugin
 
 
# class BrightSignPlugin(ManualPlatformPlugin):
#     """BrightSign player monitoring plugin via REST API."""
 
#     name = "brightsign"
#     display_name = "BrightSign"
#     description = "BrightSign media players via REST API"
#     supports_display_id = False
#     supports_port = False
#     default_port = 80
#     SUPPORTED_MODELS = [
#         "XT",
#         "XD",
#         "HD",
#         "LS",
#         "AU",
#     ]
 
#     COMMANDS = {
#     "snapshot": {"description": "Take snapshot from device", "params": []},
#     "get_network": {"description": "Get network configuration", "params": []},
#     "set_network": {"description": "Set network configuration", "params": []},
#     "get_info":   {"description": "Get device info", "params": []},          # ADD
#     "get_health": {"description": "Get device health", "params": []},        # ADD
#     "get_time":   {"description": "Get device time", "params": []},          # ADD
#     "list_files": {"description": "List files on storage", "params": []},    # ADD
#     "get_registry": {"description": "Get registry", "params": []},           # ADD
#     "set_time": {
#         "description": "Set device time and timezone",
#         "params": [
#             {"name": "time", "type": "str"},
#             {"name": "timezone", "type": "str"},
#         ],
#     },
#     "upload_file": {
#         "description": "Upload a file to player storage",
#         "params": [
#             {"name": "path", "type": "str"},
#             {"name": "file_name", "type": "str"},
#             {"name": "file_contents", "type": "str"},
#             {"name": "file_type", "type": "str"},
#         ],
#     },
#     "create_directory": {
#         "description": "Create a directory on player storage",
#         "params": [{"name": "path", "type": "str"}],
#     },
#     "delete_file_or_directory": {
#         "description": "Delete a file or directory from player storage",
#         "params": [{"name": "path", "type": "str"}],
#     },
#     "rename_file": {
#         "description": "Rename a file on player storage",
#         "params": [
#             {"name": "path", "type": "str"},
#             {"name": "name", "type": "str"},
#         ],
#     },
#     "reboot": {"description": "Reboot device", "params": []},
#     "reboot_crash": {"description": "Reboot and collect crash report", "params": []},
#     "factory_reset": {"description": "Factory reset device", "params": []},
#     "disable_autorun": {"description": "Disable autorun on reboot", "params": []},
# }

#     QUERY_COMMANDS = {
#         "device_info": "get_info",
#         "health": "get_health",
#         "time": "get_time",
#         "video_mode": "get_video_mode",
#         "files": "list_files",
#         "registry": "get_registry",
#         "network_config": "get_network",
#         "snapshot": "snapshot",
#     }
 
#     def _request(self, ip, username, password, method, endpoint, data=None, params=None, files=None, headers=None):
#         url = f"http://{ip}/api/v1{endpoint}"
#         request_headers = {"Accept": "application/json"}
#         if files is None:
#             request_headers["Content-Type"] = "application/json"
#         if headers:
#             request_headers.update(headers)
 
#         response = requests.request(
#             method=method,
#             url=url,
#             auth=HTTPDigestAuth(username, password),
#             headers=request_headers,
#             json=data if files is None else None,
#             params=params,
#             files=files,
#             timeout=10,
#         )
#         response.raise_for_status()
#         return response.json() if response.content else {}
 
#     def _extract_result(self, payload):
#         if not isinstance(payload, dict):
#             return {}
 
#         data = payload.get("data")
#         if isinstance(data, dict):
#             result = data.get("result")
#             if isinstance(result, dict):
#                 return result
 
#         result = payload.get("result")
#         if isinstance(result, dict):
#             return result
 
#         return payload
 
#     def _coalesce(self, *values):
#         for value in values:
#             if value not in (None, "", [], {}):
#                 return value
#         return None
 
#     def _normalize_files_path(self, path):
#         normalized = str(path or "sd").strip().strip("/")
#         if not normalized:
#             normalized = "sd"
#         return f"/files/{normalized}/"
 
#     def _decode_file_contents(self, contents):
#         if contents is None:
#             return b""
#         value = str(contents)
#         if value.startswith("data:") and "," in value:
#             _, encoded = value.split(",", 1)
#             return base64.b64decode(encoded)
#         return value.encode("utf-8")
 
#     def _get_credentials(self):
#         username = self.config.get("username")
#         password = self.config.get("password")
#         if not username or not password:
#             raise ValueError("Missing credentials: username and password are required.")
#         return username, password
 
#     def _decode_command(self, command):
#         if isinstance(command, dict):
#             return command.get("action"), command.get("params") or {}
 
#         action = command
#         params = {}
#         if isinstance(command, str):
#             stripped = command.strip()
#             if stripped.startswith("{") and stripped.endswith("}"):
#                 try:
#                     parsed = json.loads(stripped)
#                     if isinstance(parsed, dict):
#                         return parsed.get("action"), parsed.get("params") or {}
#                 except Exception:
#                     pass
#         return action, params
 
#     def get_info(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "GET", "/info")
 
#     def get_health(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "GET", "/health")
 
#     def get_time(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "GET", "/time")
 
#     def get_video_mode(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "GET", "/video-mode")
 
#     def list_files(self, ip, path="sd", raw=False, contents=False, stream=False):
#         username, password = self._get_credentials()
#         params = {}
#         if raw:
#             params["raw"] = ""
#         if contents:
#             params["contents"] = ""
#         if stream:
#             params["stream"] = ""
#         return self._request(
#             ip,
#             username,
#             password,
#             "GET",
#             self._normalize_files_path(path),
#             params=params or None,
#         )
 
#     def upload_file(self, ip, path, file_name, file_contents, file_type="application/octet-stream"):
#         username, password = self._get_credentials()
#         file_bytes = self._decode_file_contents(file_contents)
#         files = {
#             "file": (file_name, file_bytes, file_type or "application/octet-stream"),
#         }
#         return self._request(
#             ip,
#             username,
#             password,
#             "PUT",
#             self._normalize_files_path(path),
#             files=files,
#         )
 
#     def create_directory(self, ip, path):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "PUT", self._normalize_files_path(path))
 
#     def delete_file_or_directory(self, ip, path):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "DELETE", self._normalize_files_path(path))
 
#     def rename_file(self, ip, path, new_name):
#         username, password = self._get_credentials()
#         return self._request(
#             ip,
#             username,
#             password,
#             "POST",
#             self._normalize_files_path(path),
#             data={"name": new_name},
#         )
 
#     def get_registry(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "GET", "/registry/")
 
#     def take_snapshot(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "POST", "/snapshot/")
 
#     def get_network_config(self, ip, interface="eth0"):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "GET", f"/diagnostics/network-configuration/{interface}/")
 
#     def set_network_config(self, ip, interface="eth0", payload=None):
#         username, password = self._get_credentials()
#         request_payload = payload or {
#             "caCertificates": "",
#             "clientCertificate": False,
#             "clientIdentifier": "BrightSign:D7E8CV332141",
#             "dnsServerList": ["192.168.86.1"],
#             "domain": "lan",
#             "eapTlsOptions": "",
#             "enabledProtocolList": ["IPv4", "IPv6"],
#             "identity": "",
#             "ipAddressList": [],
#             "inboundShaperRate": 0,
#             "metric": 1002,
#             "privateKey": False,
#             "securityMode": "",
#             "vlanIdList": [],
#         }
#         return self._request(ip, username, password, "PUT", f"/diagnostics/network-configuration/{interface}", request_payload)
 
#     def set_time(self, ip, time_str=None, timezone="Asia/Kolkata"):
#         username, password = self._get_credentials()
#         date_part = None
#         time_part = None

#         if time_str and "T" in time_str:
#             parts = time_str.split("T")
#             date_part = parts[0]          # "2026-04-15"
#             time_part = parts[1][:8]      # "14:07:41"
#         elif time_str and len(time_str) >= 8:
#             time_part = time_str[:8]

#         payload = {"data": {}}

#         if time_part:
#             payload["data"]["time"] = time_part

#         if date_part:
#             payload["data"]["date"] = date_part

#         # ✅ IMPORTANT (as per docs)
#         if timezone:
#             payload["data"]["timezone"] = timezone
#             payload["data"]["applyTimezone"] = True

#         if not payload["data"]:
#             raise ValueError("set_time requires time and/or timezone")

#         return self._request(
#             ip,
#             username,
#             password,
#             "PUT",
#             "/time/",
#             payload   # ✅ correct payload
#         )
 
#     def reboot(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "PUT", "/control/reboot/", {})
 
#     def reboot_with_crash(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "PUT", "/control/reboot/", {"crash_report": True})
 
#     def factory_reset(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "PUT", "/control/reboot/", {"factory_reset": True})
 
#     def disable_autorun(self, ip):
#         username, password = self._get_credentials()
#         return self._request(ip, username, password, "PUT", "/control/reboot/", {"autorun": "disable"})
 
#     def get_device_info(self, ip, port=80, display_id=None):
#         try:
#             self._get_credentials()
#         except ValueError as e:
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "BrightSign",
#                 "device_type": "BrightSign Player",
#                 "current_status": "Offline",
#                 "error": str(e),
#             }
 
#         try:
#             info_response = self.get_info(ip)
#             health_response = self.get_health(ip)
#             time_response = self.get_time(ip)
#             video_mode_response = self.get_video_mode(ip)
#             network_response = self.get_network_config(ip)
 
#             info = self._extract_result(info_response)
#             health = self._extract_result(health_response)
#             time_info = self._extract_result(time_response)
#             video_mode = self._extract_result(video_mode_response)
#             network = self._extract_result(network_response)
 
#             networking = info.get("networking", {})
#             networking_result = networking.get("result", {}) if isinstance(networking, dict) else {}
#             ethernet = info.get("ethernet") or []
#             primary_ethernet = ethernet[0] if ethernet else {}
#             primary_ipv4 = (primary_ethernet.get("IPv4") or [{}])[0] if isinstance(primary_ethernet, dict) else {}
#             power = info.get("power", {})
#             power_result = power.get("result", {}) if isinstance(power, dict) else {}
 
#             model = self._coalesce(
#                 info.get("model"),
#                 info.get("modelName"),
#                 info.get("product"),
#                 info.get("family"),
#             )
#             serial_number = self._coalesce(
#                 info.get("serial"),
#                 info.get("serialNumber"),
#                 info.get("unitName"),
#             )
#             firmware = self._coalesce(
#                 info.get("FWVersion"),
#                 info.get("firmware"),
#                 info.get("firmwareVersion"),
#                 info.get("osVersion"),
#                 info.get("version"),
#             )
#             device_name = self._coalesce(
#                 info.get("name"),
#                 info.get("unitName"),
#                 info.get("hostname"),
#                 networking_result.get("name"),
#                 model,
#                 "BrightSign Player",
#             )
#             storage = self._coalesce(
#                 health.get("storage"),
#                 health.get("storageHealth"),
#                 health.get("storageState"),
#             )
 
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "BrightSign",
#                 "device_type": "BrightSign Player",
#                 "device_name": device_name,
#                 "model": model,
#                 "serial_number": serial_number,
#                 "firmware": firmware,
#                 "boot_version": info.get("bootVersion"),
#                 "family": info.get("family"),
#                 "uptime": self._coalesce(info.get("upTime"), health.get("uptime"), info.get("uptime")),
#                 "uptime_seconds": info.get("upTimeSeconds"),
#                 "cpu_temperature": self._coalesce(health.get("cpuTemperature"), health.get("temperature")),
#                 "storage_health": storage,
#                 "current_time": self._coalesce(time_info.get("time"), time_info.get("currentTime")),
#                 "timezone": self._coalesce(time_info.get("timezone_name"), time_info.get("timezone")),
#                 "timezone_abbr": time_info.get("timezone_abbr"),
#                 "video_mode": self._coalesce(
#                     video_mode.get("mode"),
#                     video_mode.get("name"),
#                     video_mode.get("videoMode"),
#                 ),
#                 "video_mode_name": video_mode.get("name"),
#                 "ip_address": self._coalesce(primary_ipv4.get("address"), ip),
#                 "mac_address": primary_ipv4.get("mac"),
#                 "subnet_mask": primary_ipv4.get("netmask"),
#                 "connection_type": info.get("connectionType"),
#                 "network_description": networking_result.get("description"),
#                 "power_source": power_result.get("source"),
#                 "health_status": health.get("status"),
#                 "health_status_time": health.get("statusTime"),
#                 "network_config": network,
#                 "current_status": "Online",
#                 "raw_info": info_response,
#                 "raw_health": health_response,
#                 "raw_time": time_response,
#                 "raw_video_mode": video_mode_response,
#                 "raw_network_config": network_response,
#                 "raw_get_responses": {
#                     "info": info_response,
#                     "health": health_response,
#                     "time": time_response,
#                     "video_mode": video_mode_response,
#                     "network_config": network_response,
#                 },
#             }
#         except Exception as e:
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "BrightSign",
#                 "device_type": "BrightSign Player",
#                 "current_status": "Offline",
#                 "error": str(e),
#             }
 
#     def send_command(self, ip, port, display_id, command):
#         try:
#             action, params = self._decode_command(command)
#             params = params or {}
 
#             actions = {
#                 "get_info": lambda: self.get_info(ip),
#                 "get_health": lambda: self.get_health(ip),
#                 "get_time": lambda: self.get_time(ip),
#                 "get_video_mode": lambda: self.get_video_mode(ip),
#                 "list_files": lambda: self.list_files(
#                     ip,
#                     params.get("path", "sd"),
#                     raw=params.get("raw", False),
#                     contents=params.get("contents", False),
#                     stream=params.get("stream", False),
#                 ),
#                 "get_files": lambda: self.list_files(
#                     ip,
#                     params.get("path", "sd"),
#                     raw=params.get("raw", False),
#                     contents=params.get("contents", False),
#                     stream=params.get("stream", False),
#                 ),
#                 "upload_file": lambda: self.upload_file(
#                     ip,
#                     params.get("path", "sd"),
#                     params.get("file_name"),
#                     params.get("file_contents"),
#                     params.get("file_type", "application/octet-stream"),
#                 ),
#                 "create_directory": lambda: self.create_directory(ip, params.get("path", "sd")),
#                 "delete_file_or_directory": lambda: self.delete_file_or_directory(ip, params.get("path", "sd")),
#                 "delete_file": lambda: self.delete_file_or_directory(ip, params.get("path", "sd")),
#                 "rename_file": lambda: self.rename_file(ip, params.get("path", "sd"), params.get("name")),
#                 "get_registry": lambda: self.get_registry(ip),
#                 "snapshot": lambda: self.take_snapshot(ip),
#                 "get_network": lambda: self.get_network_config(ip, params.get("interface", "eth0")),
#                 "set_network": lambda: self.set_network_config(ip, params.get("interface", "eth0"), params.get("payload")),
#                 "set_time": lambda: self.set_time(ip, params.get("time"), params.get("timezone", "Asia/Kolkata")),
#                 "reboot": lambda: self.reboot(ip),
#                 "reboot_crash": lambda: self.reboot_with_crash(ip),
#                 "factory_reset": lambda: self.factory_reset(ip),
#                 "disable_autorun": lambda: self.disable_autorun(ip),
#             }
 
#             if action not in actions:
#                 return False, f"Invalid action: {action}"
 
#             if action == "set_time" and not params.get("time") and not params.get("timezone"):
#                 return False, "set_time requires params.time and/or params.timezone"
#             if action == "upload_file":
#                 if not params.get("file_name"):
#                     return False, "upload_file requires params.file_name"
#                 if params.get("file_contents") is None:
#                     return False, "upload_file requires params.file_contents"
#             if action == "rename_file" and not params.get("name"):
#                 return False, "rename_file requires params.name"
#             if action in {"create_directory", "delete_file_or_directory", "delete_file", "rename_file"} and not params.get("path"):
#                 return False, f"{action} requires params.path"
 
#             result = actions[action]()
#             return True, json.dumps(result, default=str)
#         except Exception as e:
#             return False, str(e)
 
#     def query_status(self, ip, port=80, display_id=None):
#         info = self.get_device_info(ip, port, display_id)

#         # video_mode comes back as a dict from get_video_mode — pass it through as-is
#         # so the frontend can read individual fields (width, height, frequency, etc.)
#         raw_video_mode = None
#         try:
#             vm_response = self.get_video_mode(ip)
#             raw_video_mode = self._extract_result(vm_response)
#             if not raw_video_mode:
#                 raw_video_mode = vm_response  # fallback to raw if extract returns {}
#         except Exception:
#             pass

#         # time info
#         current_time = None
#         timezone     = None
#         timezone_abbr = None
#         try:
#             time_response = self.get_time(ip)
#             time_info = self._extract_result(time_response)
#             current_time  = self._coalesce(time_info.get("time"), time_info.get("currentTime"))
#             timezone      = self._coalesce(time_info.get("timezone_name"), time_info.get("timezone"))
#             timezone_abbr = time_info.get("timezone_abbr")
#         except Exception:
#             pass

#         # network info
#         mac_address       = None
#         subnet_mask       = None
#         connection_type   = None
#         network_description = None
#         try:
#             net_response = self.get_network_config(ip)
#             net = self._extract_result(net_response)
#             mac_address       = net.get("mac") or info.get("mac_address")
#             subnet_mask       = net.get("netmask") or info.get("subnet_mask")
#             connection_type   = net.get("connectionType") or info.get("connection_type")
#             network_description = net.get("description") or info.get("network_description")
#         except Exception:
#             mac_address       = info.get("mac_address")
#             subnet_mask       = info.get("subnet_mask")
#             connection_type   = info.get("connection_type")
#             network_description = info.get("network_description")

#         return {
#             # core
#             "reachable":      info.get("current_status") == "Online",
#             "power":          "ON" if info.get("current_status") == "Online" else "OFF",
#             # device info
#             "device_name":    info.get("device_name"),
#             "model":          info.get("model"),
#             "serial_number":  info.get("serial_number"),
#             "firmware":       info.get("firmware"),
#             "boot_version":   info.get("boot_version"),
#             "family":         info.get("family"),
#             # health
#             "uptime":         info.get("uptime"),
#             "uptime_seconds": info.get("uptime_seconds"),
#             "cpu_temperature": info.get("cpu_temperature"),
#             "storage_health": info.get("storage_health"),
#             "health_status":  info.get("health_status"),
#             "health_status_time": info.get("health_status_time"),
#             "power_source":   info.get("power_source"),
#             # video — full object so frontend can read width/height/frequency etc.
#             "video_mode":     raw_video_mode,
#             "video_mode_name": info.get("video_mode_name"),
#             # network
#             "ip_address":     info.get("ip_address"),
#             "mac_address":    mac_address,
#             "subnet_mask":    subnet_mask,
#             "connection_type": connection_type,
#             "network_description": network_description,
#             # time
#             "current_time":   current_time,
#             "timezone":       timezone,
#             "timezone_abbr":  timezone_abbr,
#             # errors
#             "error":          info.get("error"),
#         }
 
 
# def run_plugin(params):
#     plugin = BrightSignPlugin({
#         "username": params.get("username"),
#         "password": params.get("password"),
#     })
#     action = params.get("action")
#     command = {
#         "action": action,
#         "params": {
#             "interface": params.get("interface"),
#             "payload": params.get("payload"),
#             "time": params.get("time"),
#             "timezone": params.get("timezone"),
#         },
#     }
#     success, result = plugin.send_command(params.get("ip"), 80, None, command)
#     if success:
#         try:
#             return json.loads(result)
#         except Exception:
#             return {"success": True, "data": result}
#     return {"success": False, "error": result}
 
 


"""
Manual Platform Plugin: brightsign_plugin.py
"""

import json
import base64

import requests
from requests.auth import HTTPDigestAuth

from .base import ManualPlatformPlugin


class BrightSignPlugin(ManualPlatformPlugin):
    """BrightSign player monitoring plugin via REST API."""

    name = "brightsign"
    display_name = "BrightSign"
    description = "BrightSign media players via REST API"
    supports_display_id = False
    supports_port = False
    default_port = 80
    SUPPORTED_MODELS = ["XT", "XD", "HD", "LS", "AU"]

    COMMANDS = {
        "snapshot":       {"description": "Take snapshot from device",          "params": []},
        "get_network":    {"description": "Get network configuration",           "params": []},
        "set_network":    {"description": "Set network configuration",           "params": []},
        "get_info":       {"description": "Get device info",                     "params": []},
        "get_health":     {"description": "Get device health",                   "params": []},
        "get_time":       {"description": "Get device time",                     "params": []},
        "list_files":     {"description": "List files on storage",               "params": []},
        "get_registry":   {"description": "Get registry",                        "params": []},
        # ── NEW ──
        "get_logs": {
            "description": "Get device logs",
            "params": [
                {"name": "count", "type": "int"},   # optional — number of log lines to return
                {"name": "raw",   "type": "bool"},  # optional — return raw format
            ],
        },
        "set_time": {
            "description": "Set device time and timezone",
            "params": [
                {"name": "time",     "type": "str"},
                {"name": "timezone", "type": "str"},
            ],
        },
        "upload_file": {
            "description": "Upload a file to player storage",
            "params": [
                {"name": "path",          "type": "str"},
                {"name": "file_name",     "type": "str"},
                {"name": "file_contents", "type": "str"},
                {"name": "file_type",     "type": "str"},
            ],
        },
        "create_directory": {
            "description": "Create a directory on player storage",
            "params": [{"name": "path", "type": "str"}],
        },
        "delete_file_or_directory": {
            "description": "Delete a file or directory from player storage",
            "params": [{"name": "path", "type": "str"}],
        },
        "rename_file": {
            "description": "Rename a file on player storage",
            "params": [
                {"name": "path", "type": "str"},
                {"name": "name", "type": "str"},
            ],
        },
        "reboot":           {"description": "Reboot device",                    "params": []},
        "reboot_crash":     {"description": "Reboot and collect crash report",  "params": []},
        "factory_reset":    {"description": "Factory reset device",             "params": []},
        "disable_autorun":  {"description": "Disable autorun on reboot",        "params": []},
    }

    QUERY_COMMANDS = {
        "device_info":    "get_info",
        "health":         "get_health",
        "time":           "get_time",
        "video_mode":     "get_video_mode",
        "files":          "list_files",
        "registry":       "get_registry",
        "network_config": "get_network",
        "snapshot":       "snapshot",
        "logs":           "get_logs",   # ── NEW ──
    }

    # ───────────────────────── helpers (unchanged) ─────────────────────────

    def _request(self, ip, username, password, method, endpoint, data=None, params=None, files=None, headers=None):
        url = f"http://{ip}/api/v1{endpoint}"
        request_headers = {"Accept": "application/json"}
        if files is None:
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        response = requests.request(
            method=method, url=url,
            auth=HTTPDigestAuth(username, password),
            headers=request_headers,
            json=data if files is None else None,
            params=params, files=files, timeout=10,
        )
        response.raise_for_status()
        return response.json() if response.content else {}

    def _extract_result(self, payload):
        if not isinstance(payload, dict):
            return {}
        data = payload.get("data")
        if isinstance(data, dict):
            result = data.get("result")
            if isinstance(result, dict):
                return result
        result = payload.get("result")
        if isinstance(result, dict):
            return result
        return payload

    def _coalesce(self, *values):
        for value in values:
            if value not in (None, "", [], {}):
                return value
        return None

    def _normalize_files_path(self, path):
        normalized = str(path or "sd").strip().strip("/")
        if not normalized:
            normalized = "sd"
        return f"/files/{normalized}/"

    def _decode_file_contents(self, contents):
        if contents is None:
            return b""
        value = str(contents)
        if value.startswith("data:") and "," in value:
            _, encoded = value.split(",", 1)
            return base64.b64decode(encoded)
        return value.encode("utf-8")

    def _get_credentials(self):
        username = self.config.get("username")
        password = self.config.get("password")
        if not username or not password:
            raise ValueError("Missing credentials: username and password are required.")
        return username, password

    def _decode_command(self, command):
        if isinstance(command, dict):
            return command.get("action"), command.get("params") or {}
        action = command
        params = {}
        if isinstance(command, str):
            stripped = command.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        return parsed.get("action"), parsed.get("params") or {}
                except Exception:
                    pass
        return action, params

    # ───────────────────────── device methods ─────────────────────────

    def get_info(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "GET", "/info")

    def get_health(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "GET", "/health")

    def get_time(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "GET", "/time")

    def get_video_mode(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "GET", "/video-mode")

    # ── NEW ──
    def get_logs(self, ip, count=None, raw=False):
        """Fetch device logs from /v1/logs."""
        username, password = self._get_credentials()
        params = {}
        if count is not None:
            params["count"] = count
        if raw:
            params["raw"] = ""
        return self._request(
            ip, username, password,
            "GET", "/logs",
            params=params or None,
        )

    def list_files(self, ip, path="sd", raw=False, contents=False, stream=False):
        username, password = self._get_credentials()
        params = {}
        if raw:      params["raw"]      = ""
        if contents: params["contents"] = ""
        if stream:   params["stream"]   = ""
        return self._request(ip, username, password, "GET", self._normalize_files_path(path), params=params or None)

    def upload_file(self, ip, path, file_name, file_contents, file_type="application/octet-stream"):
        username, password = self._get_credentials()
        file_bytes = self._decode_file_contents(file_contents)
        files = {"file": (file_name, file_bytes, file_type or "application/octet-stream")}
        return self._request(ip, username, password, "PUT", self._normalize_files_path(path), files=files)

    def create_directory(self, ip, path):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "PUT", self._normalize_files_path(path))

    def delete_file_or_directory(self, ip, path):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "DELETE", self._normalize_files_path(path))

    def rename_file(self, ip, path, new_name):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "POST", self._normalize_files_path(path), data={"name": new_name})

    def get_registry(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "GET", "/registry/")

    def take_snapshot(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "POST", "/snapshot/")

    def get_network_config(self, ip, interface="eth0"):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "GET", f"/diagnostics/network-configuration/{interface}/")

    def set_network_config(self, ip, interface="eth0", payload=None):
        username, password = self._get_credentials()
        request_payload = payload or {
            "caCertificates": "", "clientCertificate": False,
            "clientIdentifier": "BrightSign:D7E8CV332141",
            "dnsServerList": ["192.168.86.1"], "domain": "lan",
            "eapTlsOptions": "", "enabledProtocolList": ["IPv4", "IPv6"],
            "identity": "", "ipAddressList": [], "inboundShaperRate": 0,
            "metric": 1002, "privateKey": False, "securityMode": "",
            "vlanIdList": [],
        }
        return self._request(ip, username, password, "PUT", f"/diagnostics/network-configuration/{interface}", request_payload)

    def set_time(self, ip, time_str=None, timezone="Asia/Kolkata"):
        username, password = self._get_credentials()
        date_part = None
        time_part = None
        if time_str and "T" in time_str:
            parts = time_str.split("T")
            date_part = parts[0]
            time_part = parts[1][:8]
        elif time_str and len(time_str) >= 8:
            time_part = time_str[:8]
        payload = {"data": {}}
        if time_part:  payload["data"]["time"] = time_part
        if date_part:  payload["data"]["date"] = date_part
        if timezone:
            payload["data"]["timezone"]      = timezone
            payload["data"]["applyTimezone"] = True
        if not payload["data"]:
            raise ValueError("set_time requires time and/or timezone")
        return self._request(ip, username, password, "PUT", "/time/", payload)

    def reboot(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "PUT", "/control/reboot/", {})

    def reboot_with_crash(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "PUT", "/control/reboot/", {"crash_report": True})

    def factory_reset(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "PUT", "/control/reboot/", {"factory_reset": True})

    def disable_autorun(self, ip):
        username, password = self._get_credentials()
        return self._request(ip, username, password, "PUT", "/control/reboot/", {"autorun": "disable"})

    # ───────────────────────── get_device_info (unchanged) ─────────────────────────

    def get_device_info(self, ip, port=80, display_id=None):
        try:
            self._get_credentials()
        except ValueError as e:
            return {"ip_address": ip, "port": port, "display_id": display_id, "make": "BrightSign", "device_type": "BrightSign Player", "current_status": "Offline", "error": str(e)}

        try:
            info_response       = self.get_info(ip)
            health_response     = self.get_health(ip)
            time_response       = self.get_time(ip)
            video_mode_response = self.get_video_mode(ip)
            network_response    = self.get_network_config(ip)

            info       = self._extract_result(info_response)
            health     = self._extract_result(health_response)
            time_info  = self._extract_result(time_response)
            video_mode = self._extract_result(video_mode_response)
            network    = self._extract_result(network_response)

            networking        = info.get("networking", {})
            networking_result = networking.get("result", {}) if isinstance(networking, dict) else {}
            ethernet          = info.get("ethernet") or []
            primary_ethernet  = ethernet[0] if ethernet else {}
            primary_ipv4      = (primary_ethernet.get("IPv4") or [{}])[0] if isinstance(primary_ethernet, dict) else {}
            power             = info.get("power", {})
            power_result      = power.get("result", {}) if isinstance(power, dict) else {}

            model         = self._coalesce(info.get("model"), info.get("modelName"), info.get("product"), info.get("family"))
            serial_number = self._coalesce(info.get("serial"), info.get("serialNumber"), info.get("unitName"))
            firmware      = self._coalesce(info.get("FWVersion"), info.get("firmware"), info.get("firmwareVersion"), info.get("osVersion"), info.get("version"))
            device_name   = self._coalesce(info.get("name"), info.get("unitName"), info.get("hostname"), networking_result.get("name"), model, "BrightSign Player")
            storage       = self._coalesce(health.get("storage"), health.get("storageHealth"), health.get("storageState"))

            return {
                "ip_address": ip, "port": port, "display_id": display_id,
                "make": "BrightSign", "device_type": "BrightSign Player",
                "device_name": device_name, "model": model,
                "serial_number": serial_number, "firmware": firmware,
                "boot_version": info.get("bootVersion"), "family": info.get("family"),
                "uptime": self._coalesce(info.get("upTime"), health.get("uptime"), info.get("uptime")),
                "uptime_seconds": info.get("upTimeSeconds"),
                "cpu_temperature": self._coalesce(health.get("cpuTemperature"), health.get("temperature")),
                "storage_health": storage,
                "current_time": self._coalesce(time_info.get("time"), time_info.get("currentTime")),
                "timezone": self._coalesce(time_info.get("timezone_name"), time_info.get("timezone")),
                "timezone_abbr": time_info.get("timezone_abbr"),
                "video_mode": self._coalesce(video_mode.get("mode"), video_mode.get("name"), video_mode.get("videoMode")),
                "video_mode_name": video_mode.get("name"),
                "mac_address": primary_ipv4.get("mac"),
                "subnet_mask": primary_ipv4.get("netmask"),
                "connection_type": info.get("connectionType"),
                "network_description": networking_result.get("description"),
                "power_source": power_result.get("source"),
                "health_status": health.get("status"),
                "health_status_time": health.get("statusTime"),
                "network_config": network,
                "current_status": "Online",
                "raw_info": info_response, "raw_health": health_response,
                "raw_time": time_response, "raw_video_mode": video_mode_response,
                "raw_network_config": network_response,
                "raw_get_responses": {
                    "info": info_response, "health": health_response,
                    "time": time_response, "video_mode": video_mode_response,
                    "network_config": network_response,
                },
            }
        except Exception as e:
            return {"ip_address": ip, "port": port, "display_id": display_id, "make": "BrightSign", "device_type": "BrightSign Player", "current_status": "Offline", "error": str(e)}

    # ───────────────────────── send_command ─────────────────────────

    def send_command(self, ip, port, display_id, command):
        try:
            action, params = self._decode_command(command)
            params = params or {}

            actions = {
                "get_info":       lambda: self.get_info(ip),
                "get_health":     lambda: self.get_health(ip),
                "get_time":       lambda: self.get_time(ip),
                "get_video_mode": lambda: self.get_video_mode(ip),
                # ── NEW ──
                "get_logs": lambda: self.get_logs(
                    ip,
                    count=params.get("count"),
                    raw=params.get("raw", False),
                ),
                "list_files": lambda: self.list_files(ip, params.get("path", "sd"), raw=params.get("raw", False), contents=params.get("contents", False), stream=params.get("stream", False)),
                "get_files":  lambda: self.list_files(ip, params.get("path", "sd"), raw=params.get("raw", False), contents=params.get("contents", False), stream=params.get("stream", False)),
                "upload_file": lambda: self.upload_file(ip, params.get("path", "sd"), params.get("file_name"), params.get("file_contents"), params.get("file_type", "application/octet-stream")),
                "create_directory":        lambda: self.create_directory(ip, params.get("path", "sd")),
                "delete_file_or_directory":lambda: self.delete_file_or_directory(ip, params.get("path", "sd")),
                "delete_file":             lambda: self.delete_file_or_directory(ip, params.get("path", "sd")),
                "rename_file":             lambda: self.rename_file(ip, params.get("path", "sd"), params.get("name")),
                "get_registry":            lambda: self.get_registry(ip),
                "snapshot":                lambda: self.take_snapshot(ip),
                "get_network": lambda: self.get_network_config(ip, params.get("interface", "eth0")),
                "set_network": lambda: self.set_network_config(ip, params.get("interface", "eth0"), params.get("payload")),
                "set_time":    lambda: self.set_time(ip, params.get("time"), params.get("timezone", "Asia/Kolkata")),
                "reboot":          lambda: self.reboot(ip),
                "reboot_crash":    lambda: self.reboot_with_crash(ip),
                "factory_reset":   lambda: self.factory_reset(ip),
                "disable_autorun": lambda: self.disable_autorun(ip),
            }

            if action not in actions:
                return False, f"Invalid action: {action}"

            if action == "set_time" and not params.get("time") and not params.get("timezone"):
                return False, "set_time requires params.time and/or params.timezone"
            if action == "upload_file":
                if not params.get("file_name"):     return False, "upload_file requires params.file_name"
                if params.get("file_contents") is None: return False, "upload_file requires params.file_contents"
            if action == "rename_file" and not params.get("name"):
                return False, "rename_file requires params.name"
            if action in {"create_directory", "delete_file_or_directory", "delete_file", "rename_file"} and not params.get("path"):
                return False, f"{action} requires params.path"

            result = actions[action]()
            return True, json.dumps(result, default=str)
        except Exception as e:
            return False, str(e)

    # ───────────────────────── query_status ─────────────────────────

    def query_status(self, ip, port=80, display_id=None):
        info = self.get_device_info(ip, port, display_id)

        raw_video_mode = None
        try:
            vm_response    = self.get_video_mode(ip)
            raw_video_mode = self._extract_result(vm_response) or vm_response
        except Exception:
            pass

        current_time  = None
        timezone      = None
        timezone_abbr = None
        try:
            time_response = self.get_time(ip)
            time_info     = self._extract_result(time_response)
            current_time  = self._coalesce(time_info.get("time"), time_info.get("currentTime"))
            timezone      = self._coalesce(time_info.get("timezone_name"), time_info.get("timezone"))
            timezone_abbr = time_info.get("timezone_abbr")
        except Exception:
            pass

        mac_address         = None
        subnet_mask         = None
        connection_type     = None
        network_description = None
        try:
            net_response        = self.get_network_config(ip)
            net                 = self._extract_result(net_response)
            mac_address         = net.get("mac")         or info.get("mac_address")
            subnet_mask         = net.get("netmask")     or info.get("subnet_mask")
            connection_type     = net.get("connectionType") or info.get("connection_type")
            network_description = net.get("description") or info.get("network_description")
        except Exception:
            mac_address         = info.get("mac_address")
            subnet_mask         = info.get("subnet_mask")
            connection_type     = info.get("connection_type")
            network_description = info.get("network_description")

        # ── NEW — fetch logs, fail-soft ──
        device_logs = None
        try:
            logs_response = self.get_logs(ip)
            device_logs   = self._extract_result(logs_response) or logs_response
        except Exception:
            pass

        return {
            "reachable":            info.get("current_status") == "Online",
            "power":                "ON" if info.get("current_status") == "Online" else "OFF",
            "device_name":          info.get("device_name"),
            "model":                info.get("model"),
            "serial_number":        info.get("serial_number"),
            "firmware":             info.get("firmware"),
            "boot_version":         info.get("boot_version"),
            "family":               info.get("family"),
            "uptime":               info.get("uptime"),
            "uptime_seconds":       info.get("uptime_seconds"),
            "cpu_temperature":      info.get("cpu_temperature"),
            "storage_health":       info.get("storage_health"),
            "health_status":        info.get("health_status"),
            "health_status_time":   info.get("health_status_time"),
            "power_source":         info.get("power_source"),
            "video_mode":           raw_video_mode,
            "video_mode_name":      info.get("video_mode_name"),
            "ip_address":           info.get("ip_address"),
            "mac_address":          mac_address,
            "subnet_mask":          subnet_mask,
            "connection_type":      connection_type,
            "network_description":  network_description,
            "current_time":         current_time,
            "timezone":             timezone,
            "timezone_abbr":        timezone_abbr,
            # ── NEW ──
            "logs":                 device_logs,
            "error":                info.get("error"),
        }


def run_plugin(params):
    plugin = BrightSignPlugin({
        "username": params.get("username"),
        "password": params.get("password"),
    })
    action  = params.get("action")
    command = {
        "action": action,
        "params": {
            "interface": params.get("interface"),
            "payload":   params.get("payload"),
            "time":      params.get("time"),
            "timezone":  params.get("timezone"),
            "count":     params.get("count"),   # ── NEW ──
            "raw":       params.get("raw"),     # ── NEW ──
        },
    }
    success, result = plugin.send_command(params.get("ip"), 80, None, command)
    if success:
        try:
            return json.loads(result)
        except Exception:
            return {"success": True, "data": result}
    return {"success": False, "error": result}
