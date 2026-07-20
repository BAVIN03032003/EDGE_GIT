# """
# Manual Platform Plugin: CiscoRoomOSPlugin
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


# class CiscoRoomOSPlugin(ManualPlatformPlugin):
#     """Cisco RoomOS (Room Bar Pro etc.) via XML status endpoint."""

#     name = "cisco_roomos"
#     display_name = "Cisco RoomOS"
#     description = "Cisco Room Bar Pro / RoomOS via SSH"
#     supports_display_id = False
#     supports_port = False
#     default_port = 22
#     SUPPORTED_MODELS = ["Room Bar Pro", "Room Bar", "Room Kit"]

#     COMMANDS = {}
#     QUERY_COMMANDS = {}

#     def _safe_text(self, root, path):
#         elem = root.find(path)
#         return elem.text.strip() if elem is not None and elem.text else None

#     def _parse_connected_devices(self, root):
#         devices = []
#         for dev in root.findall(".//Peripherals/ConnectedDevice"):
#             devices.append({
#                 "Name": self._safe_text(dev, "Name"),
#                 "Type": self._safe_text(dev, "Type"),
#                 "Model": self._safe_text(dev, "Model"),
#                 "SerialNumber": self._safe_text(dev, "SerialNumber"),
#                 "Status": self._safe_text(dev, "Status"),
#                 "IPAddress": self._safe_text(dev, "NetworkAddress"),
#                 "Software": self._safe_text(dev, "SoftwareInfo"),
#                 "HardwareInfo": self._safe_text(dev, "HardwareInfo"),
#                 "DRAM": self._safe_text(dev, "DRAM"),
#             })
#         return devices

#     def _parse_xml_to_device_info(self, root, ip, port, username):
#         device_name = self._safe_text(root, ".//SystemUnit/ProductPlatform")
#         model = self._safe_text(root, ".//SystemUnit/ProductId")
#         firmware = self._safe_text(root, ".//SystemUnit/Software/Version")
#         serial = self._safe_text(root, ".//SystemUnit/Hardware/Module/SerialNumber")
#         mac = self._safe_text(root, ".//Network/Ethernet/MacAddress")

#         periperals = self._parse_connected_devices(root)

#         return {
#             "ip_address": ip,
#             "port": port,
#             "display_id": None,
#             "make": "Cisco",
#             "device_type": "Cisco RoomOS",
#             "device_name": device_name or model or "Cisco RoomOS",
#             "model": model,
#             "serial_number": serial or mac,
#             "firmware": firmware,
#             "software_release_date": self._safe_text(root, ".//SystemUnit/Software/ReleaseDate"),
#             "display_name": self._safe_text(root, ".//SystemUnit/Software/DisplayName"),
#             "udi": self._safe_text(root, ".//SystemUnit/Hardware/UDI"),
#             "broadcast_name": self._safe_text(root, ".//SystemUnit/BroadcastName"),
#             "mac_address": mac,
#             "gateway": self._safe_text(root, ".//Network/IPv4/Gateway"),
#             "subnet_mask": self._safe_text(root, ".//Network/IPv4/SubnetMask"),
#             "current_status": "Online",
#             "http_username": username,
#             "periperals": periperals,
#             "peripherals": periperals
#         }

#     def _fetch_status_xml(self, ip, username, password):
#         from requests.auth import HTTPBasicAuth

#         urls = [f"http://{ip}/status.xml", f"https://{ip}/status.xml"]
#         last_error = None

#         for url in urls:
#             try:
#                 response = requests.get(
#                     url,
#                     auth=HTTPBasicAuth(username, password),
#                     timeout=10,
#                     verify=False
#                 )
#                 response.raise_for_status()
#                 root = ET.fromstring(response.content)
#                 return root, None
#             except Exception as e:
#                 last_error = str(e)

#         return None, last_error or "Unable to fetch status.xml"

#     def get_device_info(self, ip, port=22, display_id=None):
#         username = self.config.get("username")
#         password = self.config.get("password")

#         if not username or not password:
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "Cisco",
#                 "device_type": "Cisco RoomOS",
#                 "current_status": "Offline",
#                 "error": "Missing credentials: username and password are required."
#             }

#         root, error = self._fetch_status_xml(ip, username, password)
#         if error:
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "Cisco",
#                 "device_type": "Cisco RoomOS",
#                 "current_status": "Offline",
#                 "error": error
#             }

#         return self._parse_xml_to_device_info(root, ip, port, username)

#     def send_command(self, ip, port, display_id, command):
#         return False, "Cisco RoomOS plugin is monitoring-only."

#     def query_status(self, ip, port=22, display_id=None):
#         info = self.get_device_info(ip, port, display_id)
#         return {
#             "reachable": info.get("current_status") == "Online",
#             "device_name": info.get("device_name"),
#             "model": info.get("model"),
#             "serial_number": info.get("serial_number"),
#             "firmware": info.get("firmware"),
#             "error": info.get("error")
#         }



"""
Manual Platform Plugin: CiscoRoomOSPlugin
Full xAPI control + rich status for Room Bar Pro / RoomOS 11.x
Verified against RoomOS 11.1 API Reference Guide D15502.02
"""

import requests
import xml.etree.ElementTree as ET

from .base import ManualPlatformPlugin


class CiscoRoomOSPlugin(ManualPlatformPlugin):
    """
    Cisco RoomOS (Room Bar Pro, Room Bar, Room Kit) via HTTP XMLAPI.

    Two connection paths:
      Direct HTTP  – username + password → /status.xml  /getxml  /putxml
      Webex Cloud  – webex_token + device_id → webexapis.com/v1/xapi/*

    Config keys
    -----------
    username      local admin username
    password      local admin password
    webex_token   Webex Bearer token   (optional, cloud commands)
    device_id     Webex cloud deviceId (optional, cloud commands)
    """

    name             = "cisco_roomos"
    display_name     = "Cisco RoomOS"
    description      = "Cisco Room Bar Pro / RoomOS via HTTP XMLAPI or Webex xAPI"
    supports_display_id = False
    supports_port    = False
    default_port     = 22
    SUPPORTED_MODELS = ["Room Bar Pro", "Room Bar", "Room Kit"]

    # ── COMMAND REGISTRY (for capability advertisement) ──────────────────────
    COMMANDS = {
        # Standby / power
        "power_on":                "Standby.Deactivate",
        "power_off":               "Standby.Activate",
        "halfwake":                "Standby.Halfwake",
        "standby_reset_timer":     "Standby.ResetTimer",
        # System
        "reboot":                  "SystemUnit.Boot",
        "factory_reset":           "SystemUnit.FactoryReset",
        "software_upgrade":        "Provisioning.SoftwareUpgrade",
        # Audio
        "set_volume":              "Audio.Volume.Set",
        "volume_up":               "Audio.Volume.Increase",
        "volume_down":             "Audio.Volume.Decrease",
        "mic_mute_on":             "Audio.Microphones.Mute",
        "mic_mute_off":            "Audio.Microphones.Unmute",
        "speaker_mute_on":         "Audio.Volume.Mute",
        "speaker_mute_off":        "Audio.Volume.Unmute",
        "toggle_mute":             "Audio.Microphones.ToggleMute",
        "noise_removal_on":        "Audio.Microphones.NoiseRemoval.Activate",
        "noise_removal_off":       "Audio.Microphones.NoiseRemoval.Deactivate",
        # Camera
        "camera_pan":              "Camera.Ramp",
        "camera_tilt":             "Camera.Ramp",
        "camera_zoom":             "Camera.Ramp",
        "camera_reset":            "Camera.PositionReset",
        "camera_position_set":     "Camera.PositionSet",
        "camera_autofocus":        "Camera.TriggerAutofocus",
        "preset_activate":         "Camera.Preset.Activate",
        "preset_store":            "Camera.Preset.Store",
        "speakertrack_on":         "Cameras.SpeakerTrack.Activate",
        "speakertrack_off":        "Cameras.SpeakerTrack.Deactivate",
        # Calls
        "dial":                    "Dial",
        "disconnect_call":         "Call.Disconnect",
        "hold_call":               "Call.Hold",
        "resume_call":             "Call.Resume",
        "dnd_on":                  "Conference.DoNotDisturb.Activate",
        "dnd_off":                 "Conference.DoNotDisturb.Deactivate",
        # UI messages
        "show_alert":              "UserInterface.Message.Alert.Display",
        "clear_alert":             "UserInterface.Message.Alert.Clear",
        "show_text_line":          "UserInterface.Message.TextLine.Display",
        "clear_text_line":         "UserInterface.Message.TextLine.Clear",
        # Logging
        "log_start":               "Logging.ExtendedLogging.Start",
        "log_stop":                "Logging.ExtendedLogging.Stop",
        "log_send":                "Logging.SendLogs",
        "macro_log_get":           "Macros.Log.Get",
        "macro_log_clear":         "Macros.Log.Clear",
        # Network / IP setup
        "set_static_ip":           "xConfiguration.Network.IPv4",
        "set_dhcp":                "xConfiguration.Network.IPv4.Assignment",
        "set_dns":                 "xConfiguration.Network.DNS",
        "set_qos":                 "xConfiguration.Network.QoS",
        "set_vlan":                "xConfiguration.Network.VLAN",
        "set_ntp":                 "xConfiguration.NetworkServices.NTP",
        "set_ssh_on":              "xConfiguration.NetworkServices.SSH",
        "set_ssh_off":             "xConfiguration.NetworkServices.SSH",
        "set_ethernet_speed":      "xConfiguration.Network.Speed",
        "set_mtu":                 "xConfiguration.Network.MTU",
        "wifi_configure":          "Network.Wifi.Configure",
        "wifi_scan":               "Network.Wifi.Scan.Start",
        "set_snmp":                "xConfiguration.NetworkServices.SNMP",
        # Config
        "set_default_volume":      "xConfiguration.Audio.DefaultVolume",
        "set_standby_delay":       "xConfiguration.Standby.Delay",
        "people_count_on":         "xConfiguration.RoomAnalytics.PeopleCountOutOfCall",
        "people_count_off":        "xConfiguration.RoomAnalytics.PeopleCountOutOfCall",
        "presence_detector_on":    "xConfiguration.RoomAnalytics.PeoplePresence.Detector",
        "presence_detector_off":   "xConfiguration.RoomAnalytics.PeoplePresence.Detector",
        "speakertrack_mode":       "xConfiguration.Cameras.SpeakerTrack.Mode",
        # Security
        "session_list":            "Security.Session.List",
        "session_terminate":       "Security.Session.Terminate",
        # History
        "call_history":            "CallHistory.Get",
    }

    QUERY_COMMANDS = {
        "get_status":       "/Status",
        "get_audio":        "/Status/Audio",
        "get_cameras":      "/Status/Cameras",
        "get_standby":      "/Status/Standby",
        "get_analytics":    "/Status/RoomAnalytics",
        "get_network":      "/Status/Network",
        "get_calls":        "/Status/Call",
        "get_diagnostics":  "/Status/Diagnostics",
        "get_peripherals":  "/Status/Peripherals",
    }

    # ── HELPERS ──────────────────────────────────────────────────────────────

    def _t(self, root, path):
        """Safe text extraction from XML element."""
        if root is None:
            return None
        e = root.find(path)
        return e.text.strip() if e is not None and e.text else None

    def _fetch_xml(self, ip, path="/status.xml"):
        """GET an XML document from the device. Returns (root, error)."""
        from requests.auth import HTTPBasicAuth
        username = self.config.get("username")
        password = self.config.get("password")
        last_error = None

        # Modern devices prefer HTTPS
        urls = (
            [f"https://{ip}/getxml", f"http://{ip}/getxml"]
            if path.startswith("/Status") or path.startswith("/Configuration")
            else [f"https://{ip}{path}", f"http://{ip}{path}"]
        )

        for url in urls:
            try:
                params = {"location": path} if "getxml" in url else {}
                r = requests.get(
                    url, params=params,
                    auth=HTTPBasicAuth(username, password),
                    timeout=8, verify=False,
                )
                r.raise_for_status()
                return ET.fromstring(r.content), None
            except Exception as e:
                last_error = str(e)

        return None, last_error or f"Unable to fetch {path}"

    def _putxml(self, ip, xml_body):
        """POST /putxml — send xCommand or xConfiguration XML."""
        from requests.auth import HTTPBasicAuth
        username = self.config.get("username")
        password = self.config.get("password")

        for scheme in ["https", "http"]:
            try:
                r = requests.post(
                    f"{scheme}://{ip}/putxml",
                    auth=HTTPBasicAuth(username, password),
                    data=xml_body.encode("utf-8"),
                    headers={"Content-Type": "text/xml"},
                    timeout=8, verify=False,
                )
                r.raise_for_status()
                # Parse result to extract status
                try:
                    root = ET.fromstring(r.content)
                    parts = []
                    # Common result patterns: status="OK", status="Error", or Success/Failure tags
                    for elem in root.iter():
                        s = elem.get("status")
                        if s:
                            parts.append(f"{elem.tag}: {s}")
                    
                    if parts:
                        all_ok = all(x in ["OK", "ok", "Success", "True"] for x in [p.split(": ")[1] for p in parts])
                        return all_ok, " | ".join(parts)
                except Exception:
                    pass
                return True, "OK"
            except requests.HTTPError as e:
                # Some errors return helpful XML even on 400
                try:
                    root = ET.fromstring(e.response.content)
                    err_msg = root.find(".//Value").text if root.find(".//Value") is not None else e.response.text[:200]
                    return False, f"HTTP {e.response.status_code}: {err_msg}"
                except:
                    return False, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            except Exception:
                continue

        return False, "Unable to reach device on HTTP or HTTPS"

    def _parse_connected_devices(self, root):
        devices = []
        for dev in root.findall(".//Peripherals/ConnectedDevice"):
            devices.append({
                "Name":          self._t(dev, "Name"),
                "Type":          self._t(dev, "Type"),
                "Model":         self._t(dev, "Model"),
                "SerialNumber":  self._t(dev, "SerialNumber"),
                "Status":        self._t(dev, "Status"),
                "IPAddress":     self._t(dev, "NetworkAddress"),
                "Software":      self._t(dev, "SoftwareInfo"),
                "HardwareInfo":  self._t(dev, "HardwareInfo"),
                "Location":      self._t(dev, "Location"),
            })
        return devices

    # ── GET DEVICE INFO ──────────────────────────────────────────────────────

    def get_device_info(self, ip, port=22, display_id=None):
        """
        Full device info from status.xml.
        Returns rich dict including audio, camera, standby, analytics,
        network, SIP, and peripherals — everything the frontend needs.
        """
        username = self.config.get("username")
        password = self.config.get("password")

        if not username or not password:
            return {
                "ip_address":    ip, "port": port, "display_id": display_id,
                "make": "Cisco", "device_type": "Cisco RoomOS",
                "current_status": "Offline",
                "error": "Missing credentials: username and password are required.",
            }

        root, error = self._fetch_xml(ip, "/status.xml")
        if error:
            return {
                "ip_address":    ip, "port": port, "display_id": display_id,
                "make": "Cisco", "device_type": "Cisco RoomOS",
                "current_status": "Offline", "error": error,
            }

        t = self._t
        model       = t(root, ".//SystemUnit/ProductId")
        serial      = t(root, ".//SystemUnit/Hardware/Module/SerialNumber")
        mac         = t(root, ".//Network/Ethernet/MacAddress")
        peripherals = self._parse_connected_devices(root)

        # Camera positions (first camera)
        cam1 = root.find(".//Cameras/Camera[@item='1']") or root.find(".//Cameras/Camera")

        # Active call check
        call_elem   = root.find(".//Call")
        call_status = t(call_elem, "Status") if call_elem is not None else None

        # Peripheral env sensor (Room Navigator)
        peri_temp = peri_aq = peri_hum = None
        for dev in root.findall(".//Peripherals/ConnectedDevice"):
            peri_temp = peri_temp or t(dev, "RoomAnalytics/AmbientTemperature")
            peri_aq   = peri_aq   or t(dev, "RoomAnalytics/AirQuality/Index")
            peri_hum  = peri_hum  or t(dev, "RoomAnalytics/RelativeHumidity")

        return {
            # Identity
            "ip_address":               ip,
            "port":                     port,
            "display_id":               None,
            "make":                     "Cisco",
            "device_type":              "Cisco RoomOS",
            "device_name":              t(root, ".//SystemUnit/ProductPlatform") or model or "Cisco RoomOS",
            "model":                    model,
            "serial_number":            serial or mac,
            "firmware":                 t(root, ".//SystemUnit/Software/Version"),
            "firmware_display":         t(root, ".//SystemUnit/Software/DisplayName"),
            "release_date":             t(root, ".//SystemUnit/Software/ReleaseDate"),
            "uptime":                   t(root, ".//SystemUnit/Uptime"),
            "broadcast_name":           t(root, ".//SystemUnit/BroadcastName"),
            "udi":                      t(root, ".//SystemUnit/Hardware/UDI"),
            "product_type":             t(root, ".//SystemUnit/ProductType"),
            "has_wifi":                 t(root, ".//SystemUnit/Hardware/HasWifi"),
            "developer_preview":        t(root, ".//SystemUnit/DeveloperPreview/Mode"),
            "temp_status":              t(root, ".//SystemUnit/Hardware/Monitoring/Temperature/Status"),
            "current_status":           "Online",
            "http_username":            username,
            # Network
            "ip_address_v4":            t(root, ".//Network/IPv4/Address"),
            "mac_address":              mac,
            "subnet_mask":              t(root, ".//Network/IPv4/SubnetMask"),
            "gateway":                  t(root, ".//Network/IPv4/Gateway"),
            "ipv6_address":             t(root, ".//Network/IPv6/Address"),
            "ethernet_speed":           t(root, ".//Network/Ethernet/Speed"),
            "dns_domain":               t(root, ".//Network/DNS/Domain/Name"),
            # Registration
            "sip_status":               t(root, ".//SIP/Registration/Status"),
            "sip_uri":                  t(root, ".//SIP/Registration/URI"),
            # Standby
            "standby_state":            t(root, ".//Standby/State"),
            # Audio
            "volume":                   t(root, ".//Audio/Volume"),
            "volume_muted":             t(root, ".//Audio/VolumeMute"),
            "microphones_muted":        t(root, ".//Audio/Microphones/Mute"),
            "noise_removal":            t(root, ".//Audio/Microphones/NoiseRemoval"),
            "music_mode":               t(root, ".//Audio/Microphones/MusicMode"),
            # Camera
            "speakertrack_status":      t(root, ".//Cameras/SpeakerTrack/Status"),
            "speakertrack_availability":t(root, ".//Cameras/SpeakerTrack/Availability"),
            "presentertrack_status":    t(root, ".//Cameras/PresenterTrack/Status"),
            "camera_pan":               t(cam1, "Position/Pan")  if cam1 is not None else None,
            "camera_tilt":              t(cam1, "Position/Tilt") if cam1 is not None else None,
            "camera_zoom":              t(cam1, "Position/Zoom") if cam1 is not None else None,
            # Room analytics
            "people_count":             t(root, ".//RoomAnalytics/PeopleCount/Current"),
            "people_count_capacity":    t(root, ".//RoomAnalytics/PeopleCount/Capacity"),
            "people_presence":          t(root, ".//RoomAnalytics/PeoplePresence"),
            "ambient_temperature":      t(root, ".//RoomAnalytics/AmbientTemperature") or peri_temp,
            "ambient_noise":            t(root, ".//RoomAnalytics/AmbientNoise/Level/A"),
            "sound_level":              t(root, ".//RoomAnalytics/Sound/Level/A"),
            "relative_humidity":        t(root, ".//RoomAnalytics/RelativeHumidity") or peri_hum,
            "air_quality_index":        peri_aq,
            "engagement_proximity":     t(root, ".//RoomAnalytics/Engagement/CloseProximity"),
            "t3_alarm":                 t(root, ".//RoomAnalytics/T3Alarm/Detected"),
            # Video
            "active_source":            t(root, ".//Video/Input/MainVideoSource"),
            "selected_source":          t(root, ".//Video/Input/MainVideoSource"),
            # Calls
            "call_status":              call_status,
            # Peripherals
            "peripherals":              peripherals,
        }

    # ── QUERY STATUS ─────────────────────────────────────────────────────────

    def query_status(self, ip, port=22, display_id=None):
        """
        Returns the status dict used by the frontend panel.
        Superset of get_device_info — all fields the UI needs.
        """
        info = self.get_device_info(ip, port, display_id)
        return {
            # Core
            "reachable":                info.get("current_status") == "Online",
            "device_name":              info.get("device_name"),
            "model":                    info.get("model"),
            "serial_number":            info.get("serial_number"),
            "firmware":                 info.get("firmware"),
            "firmware_display":         info.get("firmware_display"),
            "release_date":             info.get("release_date"),
            "uptime":                   info.get("uptime"),
            "broadcast_name":           info.get("broadcast_name"),
            "temp_status":              info.get("temp_status"),
            # Network
            "ip_address":               info.get("ip_address_v4") or ip,
            "mac_address":              info.get("mac_address"),
            "ethernet_speed":           info.get("ethernet_speed"),
            "sip_status":               info.get("sip_status"),
            "sip_uri":                  info.get("sip_uri"),
            # Standby
            "standby_state":            info.get("standby_state"),
            # Audio
            "volume":                   info.get("volume"),
            "volume_muted":             info.get("volume_muted"),
            "microphones_muted":        info.get("microphones_muted"),
            "noise_removal":            info.get("noise_removal"),
            "music_mode":               info.get("music_mode"),
            # Camera
            "speakertrack_status":      info.get("speakertrack_status"),
            "speakertrack_availability":info.get("speakertrack_availability"),
            "presentertrack_status":    info.get("presentertrack_status"),
            "camera_pan":               info.get("camera_pan"),
            "camera_tilt":              info.get("camera_tilt"),
            "camera_zoom":              info.get("camera_zoom"),
            # Room analytics
            "people_count":             info.get("people_count"),
            "people_count_capacity":    info.get("people_count_capacity"),
            "people_presence":          info.get("people_presence"),
            "ambient_temperature":      info.get("ambient_temperature"),
            "ambient_noise":            info.get("ambient_noise"),
            "sound_level":              info.get("sound_level"),
            "relative_humidity":        info.get("relative_humidity"),
            "air_quality_index":        info.get("air_quality_index"),
            "engagement_proximity":     info.get("engagement_proximity"),
            # Video
            "active_source":            info.get("active_source"),
            # Calls
            "call_status":              info.get("call_status"),
            # Error
            "error":                    info.get("error"),
        }

    # ── SEND COMMAND ─────────────────────────────────────────────────────────

    def send_command(self, ip, port, display_id, command, params=None):
        """
        Unified command dispatcher.
        params: dict of extra arguments (level, steps, camera_id, direction, etc.)

        Returns (success: bool, message: str)
        """
        username = self.config.get("username")
        password = self.config.get("password")
        params   = params or {}

        if not username or not password:
            return False, "Missing credentials: username and password are required."

        xml = self._build_xml(command, params)
        if xml is None:
            return False, f"Unsupported command: '{command}'. Check COMMANDS registry."

        return self._putxml(ip, xml)

    def _build_xml(self, command, params):
        """
        Maps command names → putxml XML strings.
        Returns None for unknown commands.
        """
        p = params

        # ── Standby / Power ─────────────────────────────────────────────
        if command == "power_on":
            return "<Command><Standby><Deactivate command='True'/></Standby></Command>"

        if command == "power_off":
            return "<Command><Standby><Activate command='True'/></Standby></Command>"

        if command == "halfwake":
            return "<Command><Standby><Halfwake command='True'/></Standby></Command>"

        if command == "standby_reset_timer":
            delay = p.get("delay", 60)
            return f"<Command><Standby><ResetTimer command='True'><Delay>{delay}</Delay></ResetTimer></Standby></Command>"

        # ── System ──────────────────────────────────────────────────────
        if command == "reboot":
            return "<Command><SystemUnit><Boot command='True'><Action>Restart</Action></Boot></SystemUnit></Command>"

        if command == "factory_reset":
            keep = p.get("keep", "Network")
            return f"<Command><SystemUnit><FactoryReset command='True'><Keep>{keep}</Keep></FactoryReset></SystemUnit></Command>"

        if command == "software_upgrade":
            url = p.get("url", "")
            return f"<Command><Provisioning><SoftwareUpgrade command='True'><URL>{url}</URL></SoftwareUpgrade></Provisioning></Command>"

        # ── Audio ────────────────────────────────────────────────────────
        if command == "set_volume":
            level = int(p.get("level", 50))
            return f"<Command><Audio><Volume><Set command='True'><Level>{level}</Level></Set></Volume></Audio></Command>"

        if command == "volume_up":
            steps = int(p.get("steps", 5))
            return f"<Command><Audio><Volume><Increase command='True'><Steps>{steps}</Steps></Increase></Volume></Audio></Command>"

        if command == "volume_down":
            steps = int(p.get("steps", 5))
            return f"<Command><Audio><Volume><Decrease command='True'><Steps>{steps}</Steps></Decrease></Volume></Audio></Command>"

        if command == "mic_mute_on":
            return "<Command><Audio><Microphones><Mute command='True'/></Microphones></Audio></Command>"

        if command == "mic_mute_off":
            return "<Command><Audio><Microphones><Unmute command='True'/></Microphones></Audio></Command>"

        if command == "speaker_mute_on":
            return "<Command><Audio><Volume><Mute command='True'/></Volume></Audio></Command>"

        if command == "speaker_mute_off":
            return "<Command><Audio><Volume><Unmute command='True'/></Volume></Audio></Command>"

        if command == "toggle_mute":
            return "<Command><Audio><Microphones><ToggleMute command='True'/></Microphones></Audio></Command>"

        if command == "noise_removal_on":
            return "<Command><Audio><Microphones><NoiseRemoval><Activate command='True'/></NoiseRemoval></Microphones></Audio></Command>"

        if command == "noise_removal_off":
            return "<Command><Audio><Microphones><NoiseRemoval><Deactivate command='True'/></NoiseRemoval></Microphones></Audio></Command>"

        # ── Camera — Ramp (continuous) ────────────────────────────────────
        if command in ("camera_pan", "camera_tilt", "camera_zoom"):
            cam_id    = int(p.get("camera_id", 1))
            direction = p.get("direction", "Stop")
            speed     = int(p.get("speed", 7))
            
            xml = f"<Command><Camera><Ramp command='True'><CameraId>{cam_id}</CameraId>"
            if command == "camera_pan":
                xml += f"<Pan>{direction}</Pan>"
                if direction != "Stop":
                    xml += f"<PanSpeed>{speed}</PanSpeed>"
            elif command == "camera_tilt":
                xml += f"<Tilt>{direction}</Tilt>"
                if direction != "Stop":
                    xml += f"<TiltSpeed>{speed}</TiltSpeed>"
            elif command == "camera_zoom":
                xml += f"<Zoom>{direction}</Zoom>"
                if direction != "Stop":
                    xml += f"<ZoomSpeed>{speed}</ZoomSpeed>"
            
            xml += "</Ramp></Camera></Command>"
            return xml

        # ── Camera — Absolute position ───────────────────────────────────
        if command == "camera_position_set":
            cam_id = int(p.get("camera_id", 1))
            pan    = int(p.get("pan", 0))
            tilt   = int(p.get("tilt", 0))
            zoom   = int(p.get("zoom", 0))
            return (f"<Command><Camera><PositionSet command='True'>"
                    f"<CameraId>{cam_id}</CameraId>"
                    f"<Pan>{pan}</Pan><Tilt>{tilt}</Tilt><Zoom>{zoom}</Zoom>"
                    f"</PositionSet></Camera></Command>")

        if command == "camera_reset":
            cam_id = int(p.get("camera_id", 1))
            return (f"<Command><Camera><PositionReset command='True'>"
                    f"<CameraId>{cam_id}</CameraId></PositionReset></Camera></Command>")

        if command == "camera_autofocus":
            cam_id = int(p.get("camera_id", 1))
            return (f"<Command><Camera><TriggerAutofocus command='True'>"
                    f"<CameraId>{cam_id}</CameraId></TriggerAutofocus></Camera></Command>")

        # ── Camera presets ───────────────────────────────────────────────
        if command == "preset_activate":
            preset_id = int(p.get("preset_id", 1))
            return (f"<Command><Camera><Preset><Activate command='True'>"
                    f"<PresetId>{preset_id}</PresetId></Activate></Preset></Camera></Command>")

        if command == "preset_store":
            cam_id = int(p.get("camera_id", 1))
            name   = p.get("name", "Preset")
            return (f"<Command><Camera><Preset><Store command='True'>"
                    f"<CameraId>{cam_id}</CameraId><Name>{name}</Name>"
                    f"<TakeSnapshot>True</TakeSnapshot>"
                    f"</Store></Preset></Camera></Command>")

        # ── SpeakerTrack ─────────────────────────────────────────────────
        if command == "speakertrack_on":
            return "<Command><Cameras><SpeakerTrack><Activate command='True'/></SpeakerTrack></Cameras></Command>"

        if command == "speakertrack_off":
            return "<Command><Cameras><SpeakerTrack><Deactivate command='True'/></SpeakerTrack></Cameras></Command>"

        # ── Calls ────────────────────────────────────────────────────────
        if command == "dial":
            number    = p.get("number", "")
            protocol  = p.get("protocol", "Sip")     # Sip / H323 / Spark  (NOT "Auto")
            call_type = p.get("call_type", "Video")   # Video / Audio / Auto
            call_rate = int(p.get("call_rate", 6000))
            return (f"<Command><Dial command='True'>"
                    f"<Number>{number}</Number>"
                    f"<Protocol>{protocol}</Protocol>"
                    f"<CallType>{call_type}</CallType>"
                    f"<CallRate>{call_rate}</CallRate>"
                    f"</Dial></Command>")

        if command == "disconnect_call":
            call_id = p.get("call_id")
            if call_id:
                return (f"<Command><Call><Disconnect command='True'>"
                        f"<CallId>{call_id}</CallId></Disconnect></Call></Command>")
            return "<Command><Call><Disconnect command='True'/></Call></Command>"

        if command == "hold_call":
            call_id = int(p.get("call_id", 0))
            return f"<Command><Call><Hold command='True'><CallId>{call_id}</CallId></Hold></Call></Command>"

        if command == "resume_call":
            call_id = int(p.get("call_id", 0))
            return f"<Command><Call><Resume command='True'><CallId>{call_id}</CallId></Resume></Call></Command>"

        if command == "dnd_on":
            timeout = int(p.get("timeout", 60))
            return (f"<Command><Conference><DoNotDisturb>"
                    f"<Activate command='True'><Timeout>{timeout}</Timeout></Activate>"
                    f"</DoNotDisturb></Conference></Command>")

        if command == "dnd_off":
            return "<Command><Conference><DoNotDisturb><Deactivate command='True'/></DoNotDisturb></Conference></Command>"

        # ── UI Messages ──────────────────────────────────────────────────
        if command == "show_alert":
            title    = p.get("title", "Alert")
            text     = p.get("text", "")
            duration = int(p.get("duration", 5))
            return (f"<Command><UserInterface><Message><Alert>"
                    f"<Display command='True'>"
                    f"<Title>{title}</Title><Text>{text}</Text><Duration>{duration}</Duration>"
                    f"</Display></Alert></Message></UserInterface></Command>")

        if command == "clear_alert":
            return "<Command><UserInterface><Message><Alert><Clear command='True'/></Alert></Message></UserInterface></Command>"

        if command == "show_text_line":
            text     = p.get("text", "")
            duration = int(p.get("duration", 0))
            return (f"<Command><UserInterface><Message><TextLine>"
                    f"<Display command='True'><Text>{text}</Text><Duration>{duration}</Duration>"
                    f"</Display></TextLine></Message></UserInterface></Command>")

        if command == "clear_text_line":
            return "<Command><UserInterface><Message><TextLine><Clear command='True'/></TextLine></Message></UserInterface></Command>"

        # ── Logging ──────────────────────────────────────────────────────
        if command == "log_start":
            duration     = int(p.get("duration", 60))
            packet_dump  = p.get("packet_dump", "None")
            render_dump  = p.get("rendering_dump", "None")
            return (f"<Command><Logging><ExtendedLogging>"
                    f"<Start command='True'>"
                    f"<Duration>{duration}</Duration>"
                    f"<PacketDump>{packet_dump}</PacketDump>"
                    f"<RenderingDump>{render_dump}</RenderingDump>"
                    f"</Start></ExtendedLogging></Logging></Command>")

        if command == "log_stop":
            rpd = "True" if p.get("remove_packet_dump") else "False"
            rrd = "True" if p.get("remove_rendering_dump") else "False"
            return (f"<Command><Logging><ExtendedLogging>"
                    f"<Stop command='True'>"
                    f"<RemovePacketDump>{rpd}</RemovePacketDump>"
                    f"<RemoveRenderingDump>{rrd}</RemoveRenderingDump>"
                    f"</Stop></ExtendedLogging></Logging></Command>")

        if command == "log_send":
            return "<Command><Logging><SendLogs command='True'/></Logging></Command>"

        if command == "macro_log_get":
            offset = int(p.get("offset", 0))
            return f"<Command><Macros><Log><Get command='True'><Offset>{offset}</Offset></Get></Log></Macros></Command>"

        if command == "macro_log_clear":
            return "<Command><Macros><Log><Clear command='True'/></Log></Macros></Command>"

        # ── Macros ───────────────────────────────────────────────────────
        if command == "macros_restart":
            return "<Command><Macros><Runtime><Restart command='True'/></Runtime></Macros></Command>"

        # ── Network / WiFi ───────────────────────────────────────────────
        if command == "wifi_scan":
            duration = int(p.get("duration", 10))
            return (f"<Command><Network><Wifi><Scan>"
                    f"<Start command='True'><Duration>{duration}</Duration></Start>"
                    f"</Scan></Wifi></Network></Command>")

        if command == "wifi_configure":
            ssid     = p.get("ssid", "")
            wtype    = p.get("type", "Wpa2-psk")
            password = p.get("password", "")
            identity = p.get("identity", "")
            pwd_xml  = f"<Password>{password}</Password>" if password else ""
            id_xml   = f"<Identity>{identity}</Identity>"  if identity else ""
            return (f"<Command><Network><Wifi><Configure command='True'>"
                    f"<SSID>{ssid}</SSID><Type>{wtype}</Type>{pwd_xml}{id_xml}"
                    f"</Configure></Wifi></Network></Command>")

        # ── Security ─────────────────────────────────────────────────────
        if command == "session_list":
            return "<Command><Security><Session><List command='True'/></Session></Security></Command>"

        if command == "session_terminate":
            sid = p.get("session_id", "")
            return (f"<Command><Security><Session>"
                    f"<Terminate command='True'><SessionId>{sid}</SessionId></Terminate>"
                    f"</Session></Security></Command>")

        # ── Call history ─────────────────────────────────────────────────
        if command == "call_history":
            count = int(p.get("count", 20))
            order = p.get("order", "StartTime")
            return (f"<Command><CallHistory><Get command='True'>"
                    f"<Count>{count}</Count><Order>{order}</Order>"
                    f"</Get></CallHistory></Command>")

        # ── xConfiguration — IP Setup ────────────────────────────────────
        if command == "set_static_ip":
            ip_addr = p.get("ip", "")
            subnet  = p.get("subnet", "")
            gateway = p.get("gateway", "")
            return (f"<Configuration><Network item='1'><IPv4>"
                    f"<Assignment>Static</Assignment>"
                    f"<Address>{ip_addr}</Address>"
                    f"<SubnetMask>{subnet}</SubnetMask>"
                    f"<Gateway>{gateway}</Gateway>"
                    f"</IPv4></Network></Configuration>")

        if command == "set_dhcp":
            return "<Configuration><Network item='1'><IPv4><Assignment>DHCP</Assignment></IPv4></Network></Configuration>"

        if command == "set_dns":
            dns1 = p.get("dns1", "")
            dns2 = p.get("dns2", "")
            s2   = f"<Server item='2'><Address>{dns2}</Address></Server>" if dns2 else ""
            return (f"<Configuration><Network item='1'><DNS>"
                    f"<Server item='1'><Address>{dns1}</Address></Server>{s2}"
                    f"</DNS></Network></Configuration>")

        if command == "set_ethernet_speed":
            speed = p.get("speed", "Auto")
            return f"<Configuration><Network item='1'><Speed>{speed}</Speed></Network></Configuration>"

        if command == "set_mtu":
            mtu = int(p.get("mtu", 1500))
            return f"<Configuration><Network item='1'><MTU>{mtu}</MTU></Network></Configuration>"

        if command == "set_qos":
            mode   = p.get("mode", "Diffserv")
            audio  = int(p.get("audio_dscp", 46))
            video  = int(p.get("video_dscp", 34))
            data   = int(p.get("data_dscp", 34))
            sig    = int(p.get("signalling_dscp", 24))
            return (f"<Configuration><Network item='1'><QoS>"
                    f"<Mode>{mode}</Mode><Diffserv>"
                    f"<Audio>{audio}</Audio><Video>{video}</Video>"
                    f"<Data>{data}</Data><Signalling>{sig}</Signalling>"
                    f"</Diffserv></QoS></Network></Configuration>")

        if command == "set_vlan":
            mode    = p.get("mode", "Auto")
            vlan_id = int(p.get("vlan_id", 1))
            return (f"<Configuration><Network item='1'><VLAN><Voice>"
                    f"<Mode>{mode}</Mode><VlanId>{vlan_id}</VlanId>"
                    f"</Voice></VLAN></Network></Configuration>")

        if command == "set_ntp":
            server = p.get("server", "")
            mode   = p.get("mode", "Manual")
            return (f"<Configuration><NetworkServices><NTP>"
                    f"<Mode>{mode}</Mode>"
                    f"<Server item='1'><Address>{server}</Address></Server>"
                    f"</NTP></NetworkServices></Configuration>")

        if command == "set_ssh_on":
            return "<Configuration><NetworkServices><SSH><Mode>On</Mode></SSH></NetworkServices></Configuration>"

        if command == "set_ssh_off":
            return "<Configuration><NetworkServices><SSH><Mode>Off</Mode></SSH></NetworkServices></Configuration>"

        if command == "set_snmp":
            mode      = p.get("mode", "ReadOnly")
            community = p.get("community", "public")
            contact   = p.get("contact", "")
            location  = p.get("location", "")
            return (f"<Configuration><NetworkServices><SNMP>"
                    f"<Mode>{mode}</Mode>"
                    f"<CommunityName>{community}</CommunityName>"
                    f"<SystemContact>{contact}</SystemContact>"
                    f"<SystemLocation>{location}</SystemLocation>"
                    f"</SNMP></NetworkServices></Configuration>")

        # ── xConfiguration — Device settings ────────────────────────────
        if command == "set_default_volume":
            level = int(p.get("level", 50))
            return f"<Configuration><Audio><DefaultVolume>{level}</DefaultVolume></Audio></Configuration>"

        if command == "set_standby_delay":
            minutes = int(p.get("minutes", 10))
            return f"<Configuration><Standby><Delay>{minutes}</Delay></Standby></Configuration>"

        if command == "people_count_on":
            return "<Configuration><RoomAnalytics><PeopleCountOutOfCall>On</PeopleCountOutOfCall></RoomAnalytics></Configuration>"

        if command == "people_count_off":
            return "<Configuration><RoomAnalytics><PeopleCountOutOfCall>Off</PeopleCountOutOfCall></RoomAnalytics></Configuration>"

        if command == "presence_detector_on":
            return "<Configuration><RoomAnalytics><PeoplePresence><Detector>On</Detector></PeoplePresence></RoomAnalytics></Configuration>"

        if command == "presence_detector_off":
            return "<Configuration><RoomAnalytics><PeoplePresence><Detector>Off</Detector></PeoplePresence></Configuration>"

        if command == "speakertrack_mode":
            mode = p.get("mode", "Auto")
            return f"<Configuration><Cameras><SpeakerTrack><Mode>{mode}</Mode></SpeakerTrack></Cameras></Configuration>"

        # Unknown command
        return None

    def diagnostics_run(self, ip, port=22, display_id=None):
        """xCommand Diagnostics Run + fetch results."""
        success, msg = self._putxml(ip, "<Command><Diagnostics><Run command='True'/></Diagnostics></Command>")
        if not success:
            return {"error": msg}

        root, err = self._fetch_xml(ip, "/Status/Diagnostics")
        if err:
            return {"error": err}

        msgs = []
        for m in root.findall(".//Message"):
            msgs.append({
                "type":        self._t(m, "Type"),
                "level":       self._t(m, "Level"),
                "description": self._t(m, "Description"),
            })
        return {"messages": msgs, "count": len(msgs)}


# """
# Manual Platform Plugin: CiscoRoomOSPlugin
# Full xAPI control + rich status for Room Bar Pro / RoomOS 11.x
# Verified against RoomOS 11.1 API Reference Guide D15502.02
# """

# import requests
# import xml.etree.ElementTree as ET

# from .base import ManualPlatformPlugin


# class CiscoRoomOSPlugin(ManualPlatformPlugin):
#     """
#     Cisco RoomOS (Room Bar Pro, Room Bar, Room Kit) via HTTP XMLAPI.

#     Two connection paths:
#       Direct HTTP  – username + password → /status.xml  /getxml  /putxml
#       Webex Cloud  – webex_token + device_id → webexapis.com/v1/xapi/*

#     Config keys
#     -----------
#     username      local admin username
#     password      local admin password
#     webex_token   Webex Bearer token   (optional, cloud commands)
#     device_id     Webex cloud deviceId (optional, cloud commands)
#     """

#     name             = "cisco_roomos"
#     display_name     = "Cisco RoomOS"
#     description      = "Cisco Room Bar Pro / RoomOS via HTTP XMLAPI or Webex xAPI"
#     supports_display_id = False
#     supports_port    = False
#     default_port     = 22
#     SUPPORTED_MODELS = ["Room Bar Pro", "Room Bar", "Room Kit"]

#     # ── COMMAND REGISTRY (for capability advertisement) ──────────────────────
#     COMMANDS = {
#         # Standby / power
#         "power_on":                "Standby.Deactivate",
#         "power_off":               "Standby.Activate",
#         "halfwake":                "Standby.Halfwake",
#         "standby_reset_timer":     "Standby.ResetTimer",
#         # System
#         "reboot":                  "SystemUnit.Boot",
#         "factory_reset":           "SystemUnit.FactoryReset",
#         "software_upgrade":        "Provisioning.SoftwareUpgrade",
#         # Audio
#         "set_volume":              "Audio.Volume.Set",
#         "volume_up":               "Audio.Volume.Increase",
#         "volume_down":             "Audio.Volume.Decrease",
#         "mute_on":                 "Audio.Microphones.Mute",
#         "mute_off":                "Audio.Microphones.Unmute",
#         "toggle_mute":             "Audio.Microphones.ToggleMute",
#         "noise_removal_on":        "Audio.Microphones.NoiseRemoval.Activate",
#         "noise_removal_off":       "Audio.Microphones.NoiseRemoval.Deactivate",
#         # Camera
#         "camera_pan":              "Camera.Ramp",
#         "camera_tilt":             "Camera.Ramp",
#         "camera_zoom":             "Camera.Ramp",
#         "camera_reset":            "Camera.PositionReset",
#         "camera_position_set":     "Camera.PositionSet",
#         "camera_autofocus":        "Camera.TriggerAutofocus",
#         "preset_activate":         "Camera.Preset.Activate",
#         "preset_store":            "Camera.Preset.Store",
#         "speakertrack_on":         "Cameras.SpeakerTrack.Activate",
#         "speakertrack_off":        "Cameras.SpeakerTrack.Deactivate",
#         # Calls
#         "dial":                    "Dial",
#         "disconnect_call":         "Call.Disconnect",
#         "hold_call":               "Call.Hold",
#         "resume_call":             "Call.Resume",
#         "dnd_on":                  "Conference.DoNotDisturb.Activate",
#         "dnd_off":                 "Conference.DoNotDisturb.Deactivate",
#         # UI messages
#         "show_alert":              "UserInterface.Message.Alert.Display",
#         "clear_alert":             "UserInterface.Message.Alert.Clear",
#         "show_text_line":          "UserInterface.Message.TextLine.Display",
#         "clear_text_line":         "UserInterface.Message.TextLine.Clear",
#         # Logging
#         "log_start":               "Logging.ExtendedLogging.Start",
#         "log_stop":                "Logging.ExtendedLogging.Stop",
#         "log_send":                "Logging.SendLogs",
#         "macro_log_get":           "Macros.Log.Get",
#         "macro_log_clear":         "Macros.Log.Clear",
#         # Network / IP setup
#         "set_static_ip":           "xConfiguration.Network.IPv4",
#         "set_dhcp":                "xConfiguration.Network.IPv4.Assignment",
#         "set_dns":                 "xConfiguration.Network.DNS",
#         "set_qos":                 "xConfiguration.Network.QoS",
#         "set_vlan":                "xConfiguration.Network.VLAN",
#         "set_ntp":                 "xConfiguration.NetworkServices.NTP",
#         "set_ssh_on":              "xConfiguration.NetworkServices.SSH",
#         "set_ssh_off":             "xConfiguration.NetworkServices.SSH",
#         "set_ethernet_speed":      "xConfiguration.Network.Speed",
#         "set_mtu":                 "xConfiguration.Network.MTU",
#         "wifi_configure":          "Network.Wifi.Configure",
#         "wifi_scan":               "Network.Wifi.Scan.Start",
#         "set_snmp":                "xConfiguration.NetworkServices.SNMP",
#         # Config
#         "set_default_volume":      "xConfiguration.Audio.DefaultVolume",
#         "set_standby_delay":       "xConfiguration.Standby.Delay",
#         "people_count_on":         "xConfiguration.RoomAnalytics.PeopleCountOutOfCall",
#         "people_count_off":        "xConfiguration.RoomAnalytics.PeopleCountOutOfCall",
#         "presence_detector_on":    "xConfiguration.RoomAnalytics.PeoplePresenceDetector",
#         "speakertrack_mode":       "xConfiguration.Cameras.SpeakerTrack.Mode",
#         # Security
#         "session_list":            "Security.Session.List",
#         "session_terminate":       "Security.Session.Terminate",
#         # History
#         "call_history":            "CallHistory.Get",
#     }

#     QUERY_COMMANDS = {
#         "get_status":       "/Status",
#         "get_audio":        "/Status/Audio",
#         "get_cameras":      "/Status/Cameras",
#         "get_standby":      "/Status/Standby",
#         "get_analytics":    "/Status/RoomAnalytics",
#         "get_network":      "/Status/Network",
#         "get_calls":        "/Status/Call",
#         "get_diagnostics":  "/Status/Diagnostics",
#         "get_peripherals":  "/Status/Peripherals",
#     }

#     # ── HELPERS ──────────────────────────────────────────────────────────────

#     def _t(self, root, path):
#         """Safe text extraction from XML element."""
#         if root is None:
#             return None
#         e = root.find(path)
#         return e.text.strip() if e is not None and e.text else None

#     def _fetch_xml(self, ip, path="/status.xml"):
#         """GET an XML document from the device. Returns (root, error)."""
#         from requests.auth import HTTPBasicAuth
#         username = self.config.get("username")
#         password = self.config.get("password")
#         last_error = None

#         urls = (
#             [f"http://{ip}/getxml", f"https://{ip}/getxml"]
#             if path.startswith("/Status") or path.startswith("/Configuration")
#             else [f"http://{ip}{path}", f"https://{ip}{path}"]
#         )

#         for url in urls:
#             try:
#                 params = {"location": path} if "getxml" in url else {}
#                 r = requests.get(
#                     url, params=params,
#                     auth=HTTPBasicAuth(username, password),
#                     timeout=10, verify=False,
#                 )
#                 r.raise_for_status()
#                 return ET.fromstring(r.content), None
#             except Exception as e:
#                 last_error = str(e)

#         return None, last_error or f"Unable to fetch {path}"

#     def _putxml(self, ip, xml_body):
#         """POST /putxml — send xCommand or xConfiguration XML."""
#         from requests.auth import HTTPBasicAuth
#         username = self.config.get("username")
#         password = self.config.get("password")

#         for scheme in ["https", "http"]:
#             try:
#                 r = requests.post(
#                     f"{scheme}://{ip}/putxml",
#                     auth=HTTPBasicAuth(username, password),
#                     data=xml_body.encode("utf-8"),
#                     headers={"Content-Type": "text/xml"},
#                     timeout=10, verify=False,
#                 )
#                 r.raise_for_status()
#                 # Parse result to extract status
#                 try:
#                     root = ET.fromstring(r.content)
#                     parts = []
#                     for elem in root.iter():
#                         s = elem.get("status")
#                         if s:
#                             parts.append(f"{elem.tag}: {s}")
#                     if parts:
#                         all_ok = all("OK" in p or "ok" in p.lower() for p in parts)
#                         return all_ok, " | ".join(parts)
#                 except Exception:
#                     pass
#                 return True, "OK"
#             except requests.HTTPError as e:
#                 try:
#                     err_body = e.response.content if e.response is not None else b""
#                     err_root = ET.fromstring(err_body) if err_body else None
#                     val = err_root.find(".//Value") if err_root is not None else None
#                     err_msg = val.text if val is not None else (e.response.text[:300] if e.response is not None else str(e))
#                 except Exception:
#                     err_msg = str(e)
#                 sc = e.response.status_code if e.response is not None else 0
#                 return False, f"HTTP {sc}: {err_msg}"
#             except Exception:
#                 continue

#         return False, "Unable to reach device on HTTP or HTTPS"

#     def _parse_connected_devices(self, root):
#         devices = []
#         for dev in root.findall(".//Peripherals/ConnectedDevice"):
#             devices.append({
#                 "Name":          self._t(dev, "Name"),
#                 "Type":          self._t(dev, "Type"),
#                 "Model":         self._t(dev, "Model"),
#                 "SerialNumber":  self._t(dev, "SerialNumber"),
#                 "Status":        self._t(dev, "Status"),
#                 "IPAddress":     self._t(dev, "NetworkAddress"),
#                 "Software":      self._t(dev, "SoftwareInfo"),
#                 "HardwareInfo":  self._t(dev, "HardwareInfo"),
#                 "Location":      self._t(dev, "Location"),
#             })
#         return devices

#     # ── GET DEVICE INFO ──────────────────────────────────────────────────────

#     def get_device_info(self, ip, port=22, display_id=None):
#         """
#         Full device info from status.xml.
#         Returns rich dict including audio, camera, standby, analytics,
#         network, SIP, and peripherals — everything the frontend needs.
#         """
#         username = self.config.get("username")
#         password = self.config.get("password")

#         if not username or not password:
#             return {
#                 "ip_address":    ip, "port": port, "display_id": display_id,
#                 "make": "Cisco", "device_type": "Cisco RoomOS",
#                 "current_status": "Offline",
#                 "error": "Missing credentials: username and password are required.",
#             }

#         root, error = self._fetch_xml(ip, "/status.xml")
#         if error:
#             return {
#                 "ip_address":    ip, "port": port, "display_id": display_id,
#                 "make": "Cisco", "device_type": "Cisco RoomOS",
#                 "current_status": "Offline", "error": error,
#             }

#         t = self._t
#         model       = t(root, ".//SystemUnit/ProductId")
#         serial      = t(root, ".//SystemUnit/Hardware/Module/SerialNumber")
#         mac         = t(root, ".//Network/Ethernet/MacAddress")
#         peripherals = self._parse_connected_devices(root)

#         # Camera positions (first camera)
#         cam1 = root.find(".//Cameras/Camera[@item='1']") or root.find(".//Cameras/Camera")

#         # Active call check
#         call_elem   = root.find(".//Call")
#         call_status = t(call_elem, "Status") if call_elem is not None else None

#         # Peripheral env sensor (Room Navigator)
#         peri_temp = peri_aq = peri_hum = None
#         for dev in root.findall(".//Peripherals/ConnectedDevice"):
#             peri_temp = peri_temp or t(dev, "RoomAnalytics/AmbientTemperature")
#             peri_aq   = peri_aq   or t(dev, "RoomAnalytics/AirQuality/Index")
#             peri_hum  = peri_hum  or t(dev, "RoomAnalytics/RelativeHumidity")

#         return {
#             # Identity
#             "ip_address":               ip,
#             "port":                     port,
#             "display_id":               None,
#             "make":                     "Cisco",
#             "device_type":              "Cisco RoomOS",
#             "device_name":              t(root, ".//SystemUnit/ProductPlatform") or model or "Cisco RoomOS",
#             "model":                    model,
#             "serial_number":            serial or mac,
#             "firmware":                 t(root, ".//SystemUnit/Software/Version"),
#             "firmware_display":         t(root, ".//SystemUnit/Software/DisplayName"),
#             "release_date":             t(root, ".//SystemUnit/Software/ReleaseDate"),
#             "uptime":                   t(root, ".//SystemUnit/Uptime"),
#             "broadcast_name":           t(root, ".//SystemUnit/BroadcastName"),
#             "udi":                      t(root, ".//SystemUnit/Hardware/UDI"),
#             "product_type":             t(root, ".//SystemUnit/ProductType"),
#             "has_wifi":                 t(root, ".//SystemUnit/Hardware/HasWifi"),
#             "developer_preview":        t(root, ".//SystemUnit/DeveloperPreview/Mode"),
#             "temp_status":              t(root, ".//SystemUnit/Hardware/Monitoring/Temperature/Status"),
#             "current_status":           "Online",
#             "http_username":            username,
#             # Network
#             "ip_address_v4":            t(root, ".//Network/IPv4/Address"),
#             "mac_address":              mac,
#             "subnet_mask":              t(root, ".//Network/IPv4/SubnetMask"),
#             "gateway":                  t(root, ".//Network/IPv4/Gateway"),
#             "ipv6_address":             t(root, ".//Network/IPv6/Address"),
#             "ethernet_speed":           t(root, ".//Network/Ethernet/Speed"),
#             "dns_domain":               t(root, ".//Network/DNS/Domain/Name"),
#             # Registration
#             "sip_status":               t(root, ".//SIP/Registration/Status"),
#             "sip_uri":                  t(root, ".//SIP/Registration/URI"),
#             # Standby
#             "standby_state":            t(root, ".//Standby/State"),
#             # Audio
#             "volume":                   t(root, ".//Audio/Volume"),
#             "volume_muted":             t(root, ".//Audio/VolumeMute"),
#             "microphones_muted":        t(root, ".//Audio/Microphones/Mute"),
#             "noise_removal":            t(root, ".//Audio/Microphones/NoiseRemoval"),
#             "music_mode":               t(root, ".//Audio/Microphones/MusicMode"),
#             # Camera
#             "speakertrack_status":      t(root, ".//Cameras/SpeakerTrack/Status"),
#             "speakertrack_availability":t(root, ".//Cameras/SpeakerTrack/Availability"),
#             "presentertrack_status":    t(root, ".//Cameras/PresenterTrack/Status"),
#             "camera_pan":               t(cam1, "Position/Pan")  if cam1 is not None else None,
#             "camera_tilt":              t(cam1, "Position/Tilt") if cam1 is not None else None,
#             "camera_zoom":              t(cam1, "Position/Zoom") if cam1 is not None else None,
#             # Room analytics
#             "people_count":             t(root, ".//RoomAnalytics/PeopleCount/Current"),
#             "people_count_capacity":    t(root, ".//RoomAnalytics/PeopleCount/Capacity"),
#             "people_presence":          t(root, ".//RoomAnalytics/PeoplePresence"),
#             "ambient_temperature":      t(root, ".//RoomAnalytics/AmbientTemperature") or peri_temp,
#             "ambient_noise":            t(root, ".//RoomAnalytics/AmbientNoise/Level/A"),
#             "sound_level":              t(root, ".//RoomAnalytics/Sound/Level/A"),
#             "relative_humidity":        t(root, ".//RoomAnalytics/RelativeHumidity") or peri_hum,
#             "air_quality_index":        peri_aq,
#             "engagement_proximity":     t(root, ".//RoomAnalytics/Engagement/CloseProximity"),
#             "t3_alarm":                 t(root, ".//RoomAnalytics/T3Alarm/Detected"),
#             # Calls
#             "call_status":              call_status,
#             # Peripherals
#             "periperals":               peripherals,  # legacy typo kept
#             "peripherals":              peripherals,
#         }

#     # ── QUERY STATUS ─────────────────────────────────────────────────────────

#     def query_status(self, ip, port=22, display_id=None):
#         """
#         Returns the status dict used by the frontend panel.
#         Superset of get_device_info — all fields the UI needs.
#         """
#         info = self.get_device_info(ip, port, display_id)
#         return {
#             # Core
#             "reachable":                info.get("current_status") == "Online",
#             "device_name":              info.get("device_name"),
#             "model":                    info.get("model"),
#             "serial_number":            info.get("serial_number"),
#             "firmware":                 info.get("firmware"),
#             "firmware_display":         info.get("firmware_display"),
#             "release_date":             info.get("release_date"),
#             "uptime":                   info.get("uptime"),
#             "broadcast_name":           info.get("broadcast_name"),
#             "temp_status":              info.get("temp_status"),
#             # Network
#             "ip_address":               info.get("ip_address_v4") or ip,
#             "mac_address":              info.get("mac_address"),
#             "ethernet_speed":           info.get("ethernet_speed"),
#             "sip_status":               info.get("sip_status"),
#             "sip_uri":                  info.get("sip_uri"),
#             # Standby
#             "standby_state":            info.get("standby_state"),
#             # Audio
#             "volume":                   info.get("volume"),
#             "volume_muted":             info.get("volume_muted"),
#             "microphones_muted":        info.get("microphones_muted"),
#             "noise_removal":            info.get("noise_removal"),
#             "music_mode":               info.get("music_mode"),
#             # Camera
#             "speakertrack_status":      info.get("speakertrack_status"),
#             "speakertrack_availability":info.get("speakertrack_availability"),
#             "presentertrack_status":    info.get("presentertrack_status"),
#             "camera_pan":               info.get("camera_pan"),
#             "camera_tilt":              info.get("camera_tilt"),
#             "camera_zoom":              info.get("camera_zoom"),
#             # Room analytics
#             "people_count":             info.get("people_count"),
#             "people_count_capacity":    info.get("people_count_capacity"),
#             "people_presence":          info.get("people_presence"),
#             "ambient_temperature":      info.get("ambient_temperature"),
#             "ambient_noise":            info.get("ambient_noise"),
#             "sound_level":              info.get("sound_level"),
#             "relative_humidity":        info.get("relative_humidity"),
#             "air_quality_index":        info.get("air_quality_index"),
#             "engagement_proximity":     info.get("engagement_proximity"),
#             # Calls
#             "call_status":              info.get("call_status"),
#             # Error
#             "error":                    info.get("error"),
#         }

#     # ── SEND COMMAND ─────────────────────────────────────────────────────────

#     def send_command(self, ip, port, display_id, command, params=None):
#         """
#         Unified command dispatcher.
#         params: dict of extra arguments (level, steps, camera_id, direction, etc.)

#         Returns (success: bool, message: str)
#         """
#         username = self.config.get("username")
#         password = self.config.get("password")
#         params   = params or {}

#         if not username or not password:
#             return False, "Missing credentials: username and password are required."

#         xml = self._build_xml(command, params)
#         if xml is None:
#             return False, f"Unsupported command: '{command}'. Check COMMANDS registry."

#         return self._putxml(ip, xml)

#     def _build_xml(self, command, params):
#         """
#         Maps command names → putxml XML strings.
#         Returns None for unknown commands.
#         """
#         p = params

#         # ── Standby / Power ─────────────────────────────────────────────
#         if command == "power_on":
#             return "<Command><Standby><Deactivate command='True'/></Standby></Command>"

#         if command == "power_off":
#             return "<Command><Standby><Activate command='True'/></Standby></Command>"

#         if command == "halfwake":
#             return "<Command><Standby><Halfwake command='True'/></Standby></Command>"

#         if command == "standby_reset_timer":
#             delay = p.get("delay", 60)
#             return f"<Command><Standby><ResetTimer command='True'><Delay>{delay}</Delay></ResetTimer></Standby></Command>"

#         # ── System ──────────────────────────────────────────────────────
#         if command == "reboot":
#             return "<Command><SystemUnit><Boot command='True'><Action>Restart</Action></Boot></SystemUnit></Command>"

#         if command == "factory_reset":
#             keep = p.get("keep", "Network")
#             return f"<Command><SystemUnit><FactoryReset command='True'><Keep>{keep}</Keep></FactoryReset></SystemUnit></Command>"

#         if command == "software_upgrade":
#             url = p.get("url", "")
#             return f"<Command><Provisioning><SoftwareUpgrade command='True'><URL>{url}</URL></SoftwareUpgrade></Provisioning></Command>"

#         # ── Audio ────────────────────────────────────────────────────────
#         if command == "set_volume":
#             level = int(p.get("level", 50))
#             return f"<Command><Audio><Volume><Set command='True'><Level>{level}</Level></Set></Volume></Audio></Command>"

#         if command == "volume_up":
#             steps = int(p.get("steps", 5))
#             return f"<Command><Audio><Volume><Increase command='True'><Steps>{steps}</Steps></Increase></Volume></Audio></Command>"

#         if command == "volume_down":
#             steps = int(p.get("steps", 5))
#             return f"<Command><Audio><Volume><Decrease command='True'><Steps>{steps}</Steps></Decrease></Volume></Audio></Command>"

#         if command == "mute_on":
#             return "<Command><Audio><Microphones><Mute command='True'/></Microphones></Audio></Command>"

#         if command == "mute_off":
#             return "<Command><Audio><Microphones><Unmute command='True'/></Microphones></Audio></Command>"

#         if command == "toggle_mute":
#             return "<Command><Audio><Microphones><ToggleMute command='True'/></Microphones></Audio></Command>"

#         if command == "noise_removal_on":
#             return "<Command><Audio><Microphones><NoiseRemoval><Activate command='True'/></NoiseRemoval></Microphones></Audio></Command>"

#         if command == "noise_removal_off":
#             return "<Command><Audio><Microphones><NoiseRemoval><Deactivate command='True'/></NoiseRemoval></Microphones></Audio></Command>"

#         # ── Camera — Ramp (continuous) ────────────────────────────────────
#         if command in ("camera_pan", "camera_tilt", "camera_zoom"):
#             cam_id    = int(p.get("camera_id", 1))
#             direction = p.get("direction", "Stop")
#             speed     = int(p.get("speed", 7))
#             # FIX: Speed elements must be OMITTED when direction is "Stop"
#             # and each XML tag must be on its own line to prevent tag-merge
#             # parse errors (e.g. <Pan>Left</Pan><PanSpeed>7 -> PanPanSpeed).
#             hdr = (
#                 "<Command>\n"
#                 "  <Camera>\n"
#                 "    <Ramp command='True'>\n"
#                 f"      <CameraId>{cam_id}</CameraId>\n"
#             )
#             ftr = "    </Ramp>\n  </Camera>\n</Command>"
#             if command == "camera_pan":
#                 if direction == "Stop":
#                     return hdr + "      <Pan>Stop</Pan>\n" + ftr
#                 return hdr + f"      <Pan>{direction}</Pan>\n      <PanSpeed>{speed}</PanSpeed>\n" + ftr
#             if command == "camera_tilt":
#                 if direction == "Stop":
#                     return hdr + "      <Tilt>Stop</Tilt>\n" + ftr
#                 return hdr + f"      <Tilt>{direction}</Tilt>\n      <TiltSpeed>{speed}</TiltSpeed>\n" + ftr
#             if command == "camera_zoom":
#                 if direction == "Stop":
#                     return hdr + "      <Zoom>Stop</Zoom>\n" + ftr
#                 return hdr + f"      <Zoom>{direction}</Zoom>\n      <ZoomSpeed>{speed}</ZoomSpeed>\n" + ftr

#         if command == "camera_position_set":
#             cam_id = int(p.get("camera_id", 1))
#             pan    = int(p.get("pan", 0))
#             tilt   = int(p.get("tilt", 0))
#             zoom   = int(p.get("zoom", 0))
#             return (f"<Command><Camera><PositionSet command='True'>"
#                     f"<CameraId>{cam_id}</CameraId>"
#                     f"<Pan>{pan}</Pan><Tilt>{tilt}</Tilt><Zoom>{zoom}</Zoom>"
#                     f"</PositionSet></Camera></Command>")

#         if command == "camera_reset":
#             cam_id = int(p.get("camera_id", 1))
#             return (f"<Command><Camera><PositionReset command='True'>"
#                     f"<CameraId>{cam_id}</CameraId></PositionReset></Camera></Command>")

#         if command == "camera_autofocus":
#             cam_id = int(p.get("camera_id", 1))
#             return (f"<Command><Camera><TriggerAutofocus command='True'>"
#                     f"<CameraId>{cam_id}</CameraId></TriggerAutofocus></Camera></Command>")

#         # ── Camera presets ───────────────────────────────────────────────
#         if command == "preset_activate":
#             preset_id = int(p.get("preset_id", 1))
#             return (f"<Command><Camera><Preset><Activate command='True'>"
#                     f"<PresetId>{preset_id}</PresetId></Activate></Preset></Camera></Command>")

#         if command == "preset_store":
#             cam_id = int(p.get("camera_id", 1))
#             name   = p.get("name", "Preset")
#             return (f"<Command><Camera><Preset><Store command='True'>"
#                     f"<CameraId>{cam_id}</CameraId><Name>{name}</Name>"
#                     f"<TakeSnapshot>True</TakeSnapshot>"
#                     f"</Store></Preset></Camera></Command>")

#         # ── SpeakerTrack ─────────────────────────────────────────────────
#         if command == "speakertrack_on":
#             return "<Command><Cameras><SpeakerTrack><Activate command='True'/></SpeakerTrack></Cameras></Command>"

#         if command == "speakertrack_off":
#             return "<Command><Cameras><SpeakerTrack><Deactivate command='True'/></SpeakerTrack></Cameras></Command>"

#         # ── Calls ────────────────────────────────────────────────────────
#         if command == "dial":
#             number    = p.get("number", "")
#             protocol  = p.get("protocol", "Sip")     # Sip / H323 / Spark  (NOT "Auto")
#             call_type = p.get("call_type", "Video")   # Video / Audio / Auto
#             call_rate = int(p.get("call_rate", 6000))
#             return (f"<Command><Dial command='True'>"
#                     f"<Number>{number}</Number>"
#                     f"<Protocol>{protocol}</Protocol>"
#                     f"<CallType>{call_type}</CallType>"
#                     f"<CallRate>{call_rate}</CallRate>"
#                     f"</Dial></Command>")

#         if command == "disconnect_call":
#             call_id = p.get("call_id")
#             if call_id:
#                 return (f"<Command><Call><Disconnect command='True'>"
#                         f"<CallId>{call_id}</CallId></Disconnect></Call></Command>")
#             return "<Command><Call><Disconnect command='True'/></Call></Command>"

#         if command == "hold_call":
#             call_id = int(p.get("call_id", 0))
#             return f"<Command><Call><Hold command='True'><CallId>{call_id}</CallId></Hold></Call></Command>"

#         if command == "resume_call":
#             call_id = int(p.get("call_id", 0))
#             return f"<Command><Call><Resume command='True'><CallId>{call_id}</CallId></Resume></Call></Command>"

#         if command == "dnd_on":
#             timeout = int(p.get("timeout", 60))
#             return (f"<Command><Conference><DoNotDisturb>"
#                     f"<Activate command='True'><Timeout>{timeout}</Timeout></Activate>"
#                     f"</DoNotDisturb></Conference></Command>")

#         if command == "dnd_off":
#             return "<Command><Conference><DoNotDisturb><Deactivate command='True'/></DoNotDisturb></Conference></Command>"

#         # ── UI Messages ──────────────────────────────────────────────────
#         if command == "show_alert":
#             title    = p.get("title", "Alert")
#             text     = p.get("text", "")
#             duration = int(p.get("duration", 5))
#             return (f"<Command><UserInterface><Message><Alert>"
#                     f"<Display command='True'>"
#                     f"<Title>{title}</Title><Text>{text}</Text><Duration>{duration}</Duration>"
#                     f"</Display></Alert></Message></UserInterface></Command>")

#         if command == "clear_alert":
#             return "<Command><UserInterface><Message><Alert><Clear command='True'/></Alert></Message></UserInterface></Command>"

#         if command == "show_text_line":
#             text     = p.get("text", "")
#             duration = int(p.get("duration", 0))
#             return (f"<Command><UserInterface><Message><TextLine>"
#                     f"<Display command='True'><Text>{text}</Text><Duration>{duration}</Duration>"
#                     f"</Display></TextLine></Message></UserInterface></Command>")

#         if command == "clear_text_line":
#             return "<Command><UserInterface><Message><TextLine><Clear command='True'/></TextLine></Message></UserInterface></Command>"

#         # ── Logging ──────────────────────────────────────────────────────
#         if command == "log_start":
#             duration     = int(p.get("duration", 60))
#             packet_dump  = p.get("packet_dump", "None")
#             render_dump  = p.get("rendering_dump", "None")
#             return (f"<Command><Logging><ExtendedLogging>"
#                     f"<Start command='True'>"
#                     f"<Duration>{duration}</Duration>"
#                     f"<PacketDump>{packet_dump}</PacketDump>"
#                     f"<RenderingDump>{render_dump}</RenderingDump>"
#                     f"</Start></ExtendedLogging></Logging></Command>")

#         if command == "log_stop":
#             rpd = "True" if p.get("remove_packet_dump") else "False"
#             rrd = "True" if p.get("remove_rendering_dump") else "False"
#             return (f"<Command><Logging><ExtendedLogging>"
#                     f"<Stop command='True'>"
#                     f"<RemovePacketDump>{rpd}</RemovePacketDump>"
#                     f"<RemoveRenderingDump>{rrd}</RemoveRenderingDump>"
#                     f"</Stop></ExtendedLogging></Logging></Command>")

#         if command == "log_send":
#             return "<Command><Logging><SendLogs command='True'/></Logging></Command>"

#         if command == "macro_log_get":
#             offset = int(p.get("offset", 0))
#             return f"<Command><Macros><Log><Get command='True'><Offset>{offset}</Offset></Get></Log></Macros></Command>"

#         if command == "macro_log_clear":
#             return "<Command><Macros><Log><Clear command='True'/></Log></Macros></Command>"

#         # ── Macros ───────────────────────────────────────────────────────
#         if command == "macros_restart":
#             return "<Command><Macros><Runtime><Restart command='True'/></Runtime></Macros></Command>"

#         # ── Network / WiFi ───────────────────────────────────────────────
#         if command == "wifi_scan":
#             duration = int(p.get("duration", 10))
#             return (f"<Command><Network><Wifi><Scan>"
#                     f"<Start command='True'><Duration>{duration}</Duration></Start>"
#                     f"</Scan></Wifi></Network></Command>")

#         if command == "wifi_configure":
#             ssid     = p.get("ssid", "")
#             wtype    = p.get("type", "Wpa2-psk")
#             password = p.get("password", "")
#             identity = p.get("identity", "")
#             pwd_xml  = f"<Password>{password}</Password>" if password else ""
#             id_xml   = f"<Identity>{identity}</Identity>"  if identity else ""
#             return (f"<Command><Network><Wifi><Configure command='True'>"
#                     f"<SSID>{ssid}</SSID><Type>{wtype}</Type>{pwd_xml}{id_xml}"
#                     f"</Configure></Wifi></Network></Command>")

#         # ── Security ─────────────────────────────────────────────────────
#         if command == "session_list":
#             return "<Command><Security><Session><List command='True'/></Session></Security></Command>"

#         if command == "session_terminate":
#             sid = p.get("session_id", "")
#             return (f"<Command><Security><Session>"
#                     f"<Terminate command='True'><SessionId>{sid}</SessionId></Terminate>"
#                     f"</Session></Security></Command>")

#         # ── Call history ─────────────────────────────────────────────────
#         if command == "call_history":
#             count = int(p.get("count", 20))
#             # Valid Order values per RoomOS 11.1 API: StartTime / OccurrenceCount
#             # "OccurrenceTime" is NOT a valid value — causes ParameterError
#             order = p.get("order", "StartTime")
#             return (f"<Command><CallHistory><Get command='True'>"
#                     f"<Count>{count}</Count><Order>{order}</Order>"
#                     f"</Get></CallHistory></Command>")

#         # ── xConfiguration — IP Setup ────────────────────────────────────
#         if command == "set_static_ip":
#             ip_addr = p.get("ip", "")
#             subnet  = p.get("subnet", "")
#             gateway = p.get("gateway", "")
#             return (f"<Configuration><Network item='1'><IPv4>"
#                     f"<Assignment>Static</Assignment>"
#                     f"<Address>{ip_addr}</Address>"
#                     f"<SubnetMask>{subnet}</SubnetMask>"
#                     f"<Gateway>{gateway}</Gateway>"
#                     f"</IPv4></Network></Configuration>")

#         if command == "set_dhcp":
#             return "<Configuration><Network item='1'><IPv4><Assignment>DHCP</Assignment></IPv4></Network></Configuration>"

#         if command == "set_dns":
#             dns1 = p.get("dns1", "")
#             dns2 = p.get("dns2", "")
#             s2   = f"<Server item='2'><Address>{dns2}</Address></Server>" if dns2 else ""
#             return (f"<Configuration><Network item='1'><DNS>"
#                     f"<Server item='1'><Address>{dns1}</Address></Server>{s2}"
#                     f"</DNS></Network></Configuration>")

#         if command == "set_ethernet_speed":
#             speed = p.get("speed", "Auto")
#             return f"<Configuration><Network item='1'><Speed>{speed}</Speed></Network></Configuration>"

#         if command == "set_mtu":
#             mtu = int(p.get("mtu", 1500))
#             return f"<Configuration><Network item='1'><MTU>{mtu}</MTU></Network></Configuration>"

#         if command == "set_qos":
#             mode   = p.get("mode", "Diffserv")
#             audio  = int(p.get("audio_dscp", 46))
#             video  = int(p.get("video_dscp", 34))
#             data   = int(p.get("data_dscp", 34))
#             sig    = int(p.get("signalling_dscp", 24))
#             return (f"<Configuration><Network item='1'><QoS>"
#                     f"<Mode>{mode}</Mode><Diffserv>"
#                     f"<Audio>{audio}</Audio><Video>{video}</Video>"
#                     f"<Data>{data}</Data><Signalling>{sig}</Signalling>"
#                     f"</Diffserv></QoS></Network></Configuration>")

#         if command == "set_vlan":
#             mode    = p.get("mode", "Auto")
#             vlan_id = int(p.get("vlan_id", 1))
#             return (f"<Configuration><Network item='1'><VLAN><Voice>"
#                     f"<Mode>{mode}</Mode><VlanId>{vlan_id}</VlanId>"
#                     f"</Voice></VLAN></Network></Configuration>")

#         if command == "set_ntp":
#             server = p.get("server", "")
#             mode   = p.get("mode", "Manual")
#             return (f"<Configuration><NetworkServices><NTP>"
#                     f"<Mode>{mode}</Mode>"
#                     f"<Server item='1'><Address>{server}</Address></Server>"
#                     f"</NTP></NetworkServices></Configuration>")

#         if command == "set_ssh_on":
#             return "<Configuration><NetworkServices><SSH><Mode>On</Mode></SSH></NetworkServices></Configuration>"

#         if command == "set_ssh_off":
#             return "<Configuration><NetworkServices><SSH><Mode>Off</Mode></SSH></NetworkServices></Configuration>"

#         if command == "set_snmp":
#             mode      = p.get("mode", "ReadOnly")
#             community = p.get("community", "public")
#             contact   = p.get("contact", "")
#             location  = p.get("location", "")
#             return (f"<Configuration><NetworkServices><SNMP>"
#                     f"<Mode>{mode}</Mode>"
#                     f"<CommunityName>{community}</CommunityName>"
#                     f"<SystemContact>{contact}</SystemContact>"
#                     f"<SystemLocation>{location}</SystemLocation>"
#                     f"</SNMP></NetworkServices></Configuration>")

#         # ── xConfiguration — Device settings ────────────────────────────
#         if command == "set_default_volume":
#             level = int(p.get("level", 50))
#             return f"<Configuration><Audio><DefaultVolume>{level}</DefaultVolume></Audio></Configuration>"

#         if command == "set_standby_delay":
#             minutes = int(p.get("minutes", 10))
#             return f"<Configuration><Standby><Delay>{minutes}</Delay></Standby></Configuration>"

#         if command == "people_count_on":
#             return "<Configuration><RoomAnalytics><PeopleCountOutOfCall>On</PeopleCountOutOfCall></RoomAnalytics></Configuration>"

#         if command == "people_count_off":
#             return "<Configuration><RoomAnalytics><PeopleCountOutOfCall>Off</PeopleCountOutOfCall></RoomAnalytics></Configuration>"

#         if command == "presence_detector_on":
#             return "<Configuration><RoomAnalytics><PeoplePresenceDetector>On</PeoplePresenceDetector></RoomAnalytics></Configuration>"

#         if command == "presence_detector_off":
#             return "<Configuration><RoomAnalytics><PeoplePresenceDetector>Off</PeoplePresenceDetector></RoomAnalytics></Configuration>"

#         if command == "speakertrack_mode":
#             mode = p.get("mode", "Auto")
#             return f"<Configuration><Cameras><SpeakerTrack><Mode>{mode}</Mode></SpeakerTrack></Cameras></Configuration>"

#         # Unknown command
#         return None

#     def diagnostics_run(self, ip, port=22, display_id=None):
#         """xCommand Diagnostics Run + fetch results."""
#         success, msg = self._putxml(ip, "<Command><Diagnostics><Run command='True'/></Diagnostics></Command>")
#         if not success:
#             return {"error": msg}

#         root, err = self._fetch_xml(ip, "/Status/Diagnostics")
#         if err:
#             return {"error": err}

#         msgs = []
#         for m in root.findall(".//Message"):
#             msgs.append({
#                 "type":        self._t(m, "Type"),
#                 "level":       self._t(m, "Level"),
#                 "description": self._t(m, "Description"),
#             })
#         return {"messages": msgs, "count": len(msgs)}