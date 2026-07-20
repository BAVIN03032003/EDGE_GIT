"""
Manual Platform Plugin: PolyVideoOSPlugin
Poly Studio X / VideoOS devices via REST API
"""

import json
import re
import requests
import urllib3

from .base import ManualPlatformPlugin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PolyVideoOSClient:
    def __init__(self, ip, username, password, verify_ssl=False):
        self.ip = ip
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{ip}"
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.logged_in = False

    # -----------------------------
    # INTERNAL HELPERS
    # -----------------------------
    def _safe_json(self, response):
        try:
            return response.json()
        except Exception:
            return {"raw": response.text}

    def _get(self, path):
        url = f"{self.base_url}{path}"
        return self.session.get(
            url,
            timeout=10,
            headers={"Accept": "application/json"}
        )

    def _post_json(self, path, payload=None):
        url = f"{self.base_url}{path}"
        return self.session.post(
            url,
            json=payload,
            timeout=10,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )

    def _post_raw(self, path, raw_data, content_type="application/json"):
        url = f"{self.base_url}{path}"
        return self.session.post(
            url,
            data=raw_data,
            timeout=10,
            headers={
                "Content-Type": content_type,
                "Accept": "application/json"
            }
        )

    # -----------------------------
    # AUTH
    # -----------------------------
    def login(self):
        payload = {
            "user": self.username,
            "password": self.password
        }

        response = self._post_json("/rest/session", payload)

        if response.status_code == 200:
            self.logged_in = True
            return True
        return False

    def ensure_login(self):
        if not self.logged_in:
            if not self.login():
                raise Exception("Poly login failed")

    # -----------------------------
    # SYSTEM / STATUS
    # -----------------------------
    def get_system_info(self):
        self.ensure_login()
        response = self._get("/rest/system")
        return response.status_code, self._safe_json(response)

    def get_system_status(self):
        self.ensure_login()
        response = self._get("/rest/system/status")
        return response.status_code, self._safe_json(response)

    def reboot(self):
        self.ensure_login()
        response = self._post_json("/rest/system/reboot", {})
        return response.status_code, self._safe_json(response)

    # -----------------------------
    # AUDIO
    # -----------------------------
    def get_audio_status(self):
        self.ensure_login()
        response = self._get("/rest/audio")
        return response.status_code, self._safe_json(response)

    def get_mute(self):
        self.ensure_login()
        response = self._get("/rest/audio/muted")
        return response.status_code, self._safe_json(response)

    def set_mute(self, mute=True,param=None):
        self.ensure_login()
        raw_bool = "true" if mute else "false"
        response = self._post_raw("/rest/audio/muted", raw_bool)
        return response.status_code, self._safe_json(response)

    def get_audio_meters(self):
        self.ensure_login()
        response = self._get("/rest/audio/audiometers")
        return response.status_code, self._safe_json(response)

    def get_microphones(self):
        self.ensure_login()
        response = self._get("/rest/audio/microphones")
        return response.status_code, self._safe_json(response)

    def get_best_audio_summary(self):
        mute_code, mute_data = self.get_mute()
        audio_code, audio_data = self.get_audio_status()
        meters_code, meters_data = self.get_audio_meters()

        summary = {
            "mute_supported": mute_code == 200,
            "mute_state": mute_data if mute_code == 200 else None,

            "audio_summary_supported": audio_code == 200,
            "audio_summary": audio_data if audio_code == 200 else None,

            "volume_supported": False,
            "volume_level": None,

            "active_inputs": [],
            "active_outputs": [],
            "best_input_signal": None
        }

        if audio_code == 200 and isinstance(audio_data, dict):
            if "volume" in audio_data:
                summary["volume_supported"] = True
                summary["volume_level"] = audio_data.get("volume")

        if meters_code == 200 and isinstance(meters_data, list):
            active_inputs = []
            active_outputs = []

            for item in meters_data:
                if not item.get("isValid"):
                    continue

                entry = {
                    "portName": item.get("portName"),
                    "portDirection": item.get("portDirection"),
                    "levelLeft": item.get("levelLeft"),
                    "levelRight": item.get("levelRight"),
                    "levelCenter": item.get("levelCenter"),
                    "levelBack": item.get("levelBack")
                }

                if item.get("portDirection") == "IN":
                    active_inputs.append(entry)
                elif item.get("portDirection") == "OUT":
                    active_outputs.append(entry)

            summary["active_inputs"] = active_inputs
            summary["active_outputs"] = active_outputs

            if active_inputs:
                def best_signal(x):
                    vals = [
                        x.get("levelLeft", -100),
                        x.get("levelRight", -100),
                        x.get("levelCenter", -100),
                        x.get("levelBack", -100)
                    ]
                    return max(vals)

                summary["best_input_signal"] = max(active_inputs, key=best_signal)

        return 200, summary
    

    def get_provider_mode(self):
        self.ensure_login()

        # Try newer endpoint first
        response = self._get("/rest/system/mode")

        if response.status_code != 200:
            # fallback for older firmware
            response = self._get("/rest/current/system/mode")

        return response.status_code, self._safe_json(response)

    # -----------------------------
    # CAMERAS / CONFERENCES
    # -----------------------------
    def get_all_cameras(self):
        self.ensure_login()
        response = self._get("/rest/cameras/near/all")
        return response.status_code, self._safe_json(response)

    def get_selected_camera(self):
        self.ensure_login()
        response = self._get("/rest/cameras/near/selectedpeople")
        return response.status_code, self._safe_json(response)

    def get_conferences(self):
        self.ensure_login()
        response = self._get("/rest/conferences")
        return response.status_code, self._safe_json(response)


class PolyVideoOSPlugin(ManualPlatformPlugin):
    """Poly Studio X / VideoOS plugin"""

    name = "poly_videoos"
    display_name = "Poly Video Collaboration Devices"
    description = "Poly Studio X / VideoOS devices via REST API"
    supports_display_id = False
    supports_port = False
    default_port = 443

    SUPPORTED_MODELS = [
        "Studio X30",
        "Studio X50",
        "Studio X52",
        "Studio X70",
        "Poly G7500",
        "Poly Studio",
        "Poly VideoOS"
    ]

    COMMANDS = {
        "reboot": "Reboot Device",
        "mute": "Mute Microphone",
        "unmute": "Unmute Microphone"
    }

    QUERY_COMMANDS = {
        "system_info": "Get System Info",
        "system_status": "Get System Status",
        "audio_summary": "Get Audio Summary",
        "conferences": "Get Conference State",
        "cameras": "Get Cameras",
        "microphones": "Get Microphones",
        "provider_mode": "Get Provider / Device Mode"
    }

    def _normalize_mac(self, raw_mac):
        if not raw_mac:
            return None
        cleaned = re.sub(r"[^0-9A-Fa-f]", "", str(raw_mac))
        if len(cleaned) < 12:
            return None
        cleaned = cleaned[:12]
        return ":".join(cleaned[i:i+2] for i in range(0, 12, 2)).lower()

    def _build_client(self, ip):
        username = self.config.get("username")
        password = self.config.get("password")

        if not username or not password:
            raise Exception("Missing credentials: username and password are required.")

        return PolyVideoOSClient(ip, username, password, verify_ssl=False)

    def get_device_info(self, ip, port=443, display_id=None):
        try:
            client = self._build_client(ip)
            status_code, data = client.get_system_info()

            if status_code != 200 or not isinstance(data, dict):
                return {
                    "ip_address": ip,
                    "port": port,
                    "display_id": display_id,
                    "make": "Poly",
                    "device_type": "Poly Video Device",
                    "current_status": "Offline",
                    "error": f"Failed to get system info (HTTP {status_code})",
                    "raw_data": data
                }

            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Poly",
                "device_name": data.get("systemName") or "Poly Device",
                "model": data.get("model"),
                "serial_number": data.get("serialNumber"),
                "mac_address": None,
                "firmware": data.get("softwareVersion"),
                "firmware_current_version": data.get("softwareVersion"),
                "hardware_version": data.get("hardwareVersion"),
                "build": data.get("build"),
                "build_type": data.get("buildType"),
                "state": data.get("state"),
                "uptime": data.get("uptime"),
                "time_server_state": data.get("timeServerState"),
                "lan_status": data.get("lanStatus"),
                "device_type": "Poly Video Device",
                "current_status": "Online",
                "raw_data": data
            }

        except Exception as e:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Poly",
                "device_type": "Poly Video Device",
                "current_status": "Offline",
                "error": str(e)
            }

    def send_command(self, ip, port, display_id, command, params=None):
        try:
            client = self._build_client(ip)

            if command == "reboot":
                status_code, data = client.reboot()
            elif command == "mute":
                status_code, data = client.set_mute(True)
            elif command == "unmute":
                status_code, data = client.set_mute(False)
            else:
                return False, f"Unsupported command: {command}"

            if status_code in [200, 202, 204]:
                return True, {
                    "command": command,
                    "status_code": status_code,
                    "data": data
                }

            if status_code == 403:
                return False, {
                    "command": command,
                    "status_code": status_code,
                    "error": "Command blocked by device mode / policy (likely Teams mode)",
                    "data": data
                }

            return False, {
                "command": command,
                "status_code": status_code,
                "data": data
            }

        except Exception as e:
            return False, str(e)

    def query_status(self, ip, port=443, display_id=None):
        try:
            client = self._build_client(ip)

            _, sysinfo = client.get_system_info()
            _, audio = client.get_best_audio_summary()
           
            # ── Conferences ──────────────────────────────────────
            conferences_list = []
            conf_code, conf_raw = client.get_conferences()
            if conf_code == 200 and isinstance(conf_raw, list):
                conferences_list = conf_raw

            # ── Camera data ──────────────────────────────────────
            cameras_list = []
            selected_camera = None

            cameras_code, cameras_data = client.get_all_cameras()
            if cameras_code == 200 and isinstance(cameras_data, list):
                cameras_list = cameras_data

            selected_code, selected_data = client.get_selected_camera()
            if selected_code == 200 and isinstance(selected_data, dict):
                selected_camera = selected_data


            provider_mode = None
            provider_raw = None

            provider_code, provider_data = client.get_provider_mode()

            if provider_code == 200:
                provider_raw = provider_data

                if isinstance(provider_data, dict):
                    provider_mode = (
                        provider_data.get("provider")
                        or provider_data.get("mode")
                        or provider_data.get("currentProvider")
                    )    


            return {
                "reachable": True,
                "device_name": sysinfo.get("systemName"),
                "model": sysinfo.get("model"),
                "serial_number": sysinfo.get("serialNumber"),
                "firmware": sysinfo.get("softwareVersion"),
                "state": sysinfo.get("state"),
                "uptime": sysinfo.get("uptime"),
                "mute_state": audio.get("mute_state"),
                "volume_level": audio.get("volume_level"),
                "num_of_mics_connected": (
                    (audio.get("audio_summary") or {}).get("numOfMicsConnected")
                ),
                "best_input_signal": audio.get("best_input_signal"),
                "conference_count": len(conferences_list),
                "conferences": conferences_list,
                "cameras": cameras_list,
                "cameras_count": len(cameras_list),
                "selected_camera": selected_camera,
                "audio_control_supported": False,  # current real-world behavior
                "brightness_supported": False,
                "provider_mode": provider_mode,
                "provider_raw": provider_raw,
                "is_teams_mode": str(provider_mode).lower() == "teams",
                "is_device_mode": str(provider_mode).lower() in [
                    "device",
                    "camuvc",
                    "usb"
                ],
            }

        except Exception as e:
            return {
                "reachable": False,
                "error": str(e)
            }