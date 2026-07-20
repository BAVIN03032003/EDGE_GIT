
"""
Manual Platform Plugin: SennheiserTCBarMPlugin
"""

import urllib.request
import urllib.error
import ssl
import json
import base64
import threading
from typing import Optional, Dict, Any, List

from .base import ManualPlatformPlugin


class SennheiserTCBarMPlugin(ManualPlatformPlugin):
    """Sennheiser TeamConnect Bar M device control over HTTPS API."""

    name = "sennheiser_tcbarm"
    display_name = "Sennheiser TC Bar M"
    description = "Sennheiser TeamConnect Bar M audio/video bar control"
    supports_display_id = False
    supports_port = False
    default_port = 443
    SUPPORTED_MODELS = ["TCBarM", "TC Bar M"]

    COMMANDS = {
        # ── Basic mic ──────────────────────────────────────────────────────
        "mute": {
            "description": "Mute the microphone",
            "params": [],
        },
        "unmute": {
            "description": "Unmute the microphone",
            "params": [],
        },
        "identify": {
            "description": "Blink LEDs to identify device",
            "params": [],
        },
        "restart": {
            "description": "Restart the device",
            "params": [],
        },
        "reboot": {
            "description": "Reboot the device",
            "params": [],
        },
        # ── LED ────────────────────────────────────────────────────────────
        "set_led_brightness": {
            "description": "Set LED ring brightness (0–5)",
            "params": [{"name": "brightness", "type": "int", "min": 0, "max": 5}],
        },
        # ── Mic ────────────────────────────────────────────────────────────
        "set_mic_gain": {
            "description": "Set internal microphone gain (-30 to 30 dB)",
            "params": [{"name": "gain", "type": "int", "min": -30, "max": 30}],
        },
        "mic_enable": {
            "description": "Enable internal microphone",
            "params": [],
        },
        "mic_disable": {
            "description": "Disable internal microphone",
            "params": [],
        },
        # ── Speaker ────────────────────────────────────────────────────────
        "set_volume": {
            "description": "Set speaker volume (0–100)",
            "params": [{"name": "volume", "type": "int", "min": 0, "max": 100}],
        },
        "volume_up": {
            "description": "Increase speaker volume by steps",
            "params": [{"name": "steps", "type": "int", "min": 1, "max": 20}],
        },
        "volume_down": {
            "description": "Decrease speaker volume by steps",
            "params": [{"name": "steps", "type": "int", "min": 1, "max": 20}],
        },
        "set_level_limiter": {
            "description": "Set speaker level limiter (0–100)",
            "params": [{"name": "level_limiter", "type": "int", "min": 0, "max": 100}],
        },
        # ── Noise gate ─────────────────────────────────────────────────────
        "noisegate_on": {
            "description": "Enable noise gate",
            "params": [],
        },
        "noisegate_off": {
            "description": "Disable noise gate",
            "params": [],
        },
        "set_noisegate": {
            "description": "Set noise gate parameters",
            "params": [
                {"name": "threshold", "type": "int", "min": -80, "max": -20},
                {"name": "hold_time", "type": "int", "min": 100, "max": 2000},
                {"name": "range_val", "type": "int", "min": -80, "max": 0},
            ],
        },
        # ── Noise suppression ──────────────────────────────────────────────
        "set_noise_suppression": {
            "description": "Set noise suppression weighting",
            "params": [{"name": "weighting", "type": "str",
                        "options": ["Off", "Low", "Medium", "High"]}],
        },
        # ── Sound profile ─────────────────────────────────────────────────
        "set_sound_profile": {
            "description": "Set sound profile preset",
            "params": [{"name": "preset", "type": "str",
                        "options": ["Wallmount", "TableTop", "UnderDisplay", 
                                   "AboveDisplay", "FreeStanding", "Custom"]}],
        },
        # ── Conference output ──────────────────────────────────────────────
        "set_far_end_gain": {
            "description": "Set far end gain (-18 to 18 dB)",
            "params": [{"name": "gain", "type": "int", "min": -18, "max": 18}],
        },
        "set_near_end_gain": {
            "description": "Set near end gain (-18 to 18 dB)",
            "params": [{"name": "gain", "type": "int", "min": -18, "max": 18}],
        },
        # ── Device profile ─────────────────────────────────────────────────
        "set_device_profile": {
                "description": "Set device profile",
                "params": [{"name": "configuration", "type": "str",
                            "options": ["Custom", "MicrosoftTeams", "Zoom"]}],
            },
        # ── Sound prompts ──────────────────────────────────────────────────
        "sound_prompts_on": {
            "description": "Enable sound prompts",
            "params": [],
        },
        "sound_prompts_off": {
            "description": "Disable sound prompts",
            "params": [],
        },
        # ── Standby mode ───────────────────────────────────────────────────
        "set_standby_mode": {
            "description": "Set allowed standby mode",
            "params": [{"name": "mode", "type": "str",
                        "options": ["Off", "EcoMode", "DeepSleep"]}],
        },
        # ── Priority zones (values are in degrees directly) ────────────────
        "enable_priority_zone": {
            "description": "Enable or disable a priority zone",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "enable", "type": "bool"},
            ],
        },
        "set_priority_zone_gain": {
            "description": "Set priority zone gain (Off/Low/Medium/High)",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "gain", "type": "str",
                 "options": ["Off", "Low", "Medium", "High"]},
            ],
        },
        "set_priority_zone_range": {
            "description": "Set priority zone angular range in degrees (0–180)",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "left_deg", "type": "int", "min": 0, "max": 180},
                {"name": "right_deg", "type": "int", "min": 0, "max": 180},
            ],
        },
        "set_priority_zone": {
            "description": "Set all fields of a priority zone",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "enabled", "type": "bool"},
                {"name": "gain", "type": "str",
                 "options": ["Off", "Low", "Medium", "High"]},
                {"name": "left_deg", "type": "int", "min": 0, "max": 180},
                {"name": "right_deg", "type": "int", "min": 0, "max": 180},
            ],
        },
        # ── Exclusion zones (values are in degrees directly) ───────────────
        "enable_exclusion_zone": {
            "description": "Enable or disable an exclusion zone",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "enable", "type": "bool"},
            ],
        },
        "set_exclusion_zone_range": {
            "description": "Set exclusion zone angular range in degrees (0–180)",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "left_deg", "type": "int", "min": 0, "max": 180},
                {"name": "right_deg", "type": "int", "min": 0, "max": 180},
            ],
        },
        "set_exclusion_zone": {
            "description": "Set all fields of an exclusion zone",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "enabled", "type": "bool"},
                {"name": "left_deg", "type": "int", "min": 0, "max": 180},
                {"name": "right_deg", "type": "int", "min": 0, "max": 180},
            ],
        },
        # ── Camera AI ─────────────────────────────────────────────────────
        "camera_autoframing_on": {
            "description": "Enable camera auto framing",
            "params": [],
        },
        "camera_autoframing_off": {
            "description": "Disable camera auto framing",
            "params": [],
        },
        "camera_tiling_on": {
            "description": "Enable camera person tiling",
            "params": [],
        },
        "camera_tiling_off": {
            "description": "Disable camera person tiling",
            "params": [],
        },
        "camera_ffov": {
            "description": "Reset camera to full field of view",
            "params": [],
        },
        "camera_preset_store": {
            "description": "Store current camera preset",
            "params": [],
        },
        "camera_preset_load": {
            "description": "Load camera preset",
            "params": [],
        },
        # ── Camera movement ───────────────────────────────────────────────
        "camera_move": {
            "description": "Move camera relatively (up/down/left/right steps)",
            "params": [
                {"name": "direction", "type": "str",
                 "options": ["up", "down", "left", "right", "zoom_in", "zoom_out"]},
                {"name": "steps", "type": "int", "min": 1, "max": 50},
            ],
        },
        "set_camera_pan": {
            "description": "Set camera pan position (0–360°)",
            "params": [{"name": "pan", "type": "int", "min": 0, "max": 360}],
        },
        "set_camera_tilt": {
            "description": "Set camera tilt position (-25 to 25°)",
            "params": [{"name": "tilt", "type": "int", "min": -25, "max": 25}],
        },
        "set_camera_zoom": {
            "description": "Set camera zoom position (0–100%)",
            "params": [{"name": "zoom", "type": "int", "min": 0, "max": 100}],
        },
        "set_camera_zoom_speed": {
            "description": "Set camera zoom speed",
            "params": [{"name": "speed", "type": "str",
                        "options": ["Slow", "Medium", "Fast"]}],
        },
        "set_camera_pantilt_speed": {
            "description": "Set camera pan/tilt speed",
            "params": [{"name": "speed", "type": "str",
                        "options": ["Slow", "Medium", "Fast"]}],
        },
        "set_camera_autoframing_speed": {
            "description": "Set camera auto framing speed",
            "params": [{"name": "speed", "type": "str",
                        "options": ["Slow", "Medium", "Fast"]}],
        },
        # ── Camera video parameters ───────────────────────────────────────
        "set_camera_brightness": {
            "description": "Set camera brightness (-20 to 20)",
            "params": [{"name": "brightness", "type": "int", "min": -20, "max": 20}],
        },
        "set_camera_contrast": {
            "description": "Set camera contrast (0–10)",
            "params": [{"name": "contrast", "type": "int", "min": 0, "max": 10}],
        },
        "set_camera_saturation": {
            "description": "Set camera saturation (0–10)",
            "params": [{"name": "saturation", "type": "int", "min": 0, "max": 10}],
        },
        "set_camera_sharpness": {
            "description": "Set camera sharpness (0–6)",
            "params": [{"name": "sharpness", "type": "int", "min": 0, "max": 6}],
        },
        "camera_whitebalance_auto": {
            "description": "Set camera white balance to auto",
            "params": [],
        },
        "set_camera_whitebalance": {
            "description": "Set camera white balance manually (2000–10000 K)",
            "params": [{"name": "whitebalance", "type": "int", "min": 2000, "max": 10000}],
        },
        "set_camera_antiflicker": {
            "description": "Set camera anti-flicker frequency",
            "params": [{"name": "frequency", "type": "str",
                        "options": ["Auto", "50Hz", "60Hz", "Off"]}],
        },
        "camera_backlight_on": {
            "description": "Enable backlight compensation",
            "params": [],
        },
        "camera_backlight_off": {
            "description": "Disable backlight compensation",
            "params": [],
        },
        "camera_lowlight_on": {
            "description": "Enable lowlight compensation",
            "params": [],
        },
        "camera_lowlight_off": {
            "description": "Disable lowlight compensation",
            "params": [],
        },
        # ── HDMI ──────────────────────────────────────────────────────────
        "hdmi_on": {
            "description": "Enable HDMI output",
            "params": [],
        },
        "hdmi_off": {
            "description": "Disable HDMI output",
            "params": [],
        },
        # ── Network ───────────────────────────────────────────────────────
        "bluetooth_on": {
            "description": "Enable Bluetooth",
            "params": [],
        },
        "bluetooth_off": {
            "description": "Disable Bluetooth",
            "params": [],
        },
        # ── EQ ────────────────────────────────────────────────────────────
        "set_mic_eq": {
            "description": "Set internal mic custom EQ (7 values, -12 to 12 dB each)",
            "params": [
                {"name": "eq1", "type": "int", "min": -12, "max": 12},
                {"name": "eq2", "type": "int", "min": -12, "max": 12},
                {"name": "eq3", "type": "int", "min": -12, "max": 12},
                {"name": "eq4", "type": "int", "min": -12, "max": 12},
                {"name": "eq5", "type": "int", "min": -12, "max": 12},
                {"name": "eq6", "type": "int", "min": -12, "max": 12},
                {"name": "eq7", "type": "int", "min": -12, "max": 12},
            ],
        },
        "set_speaker_eq": {
            "description": "Set speaker custom EQ (7 values, -12 to 12 dB each)",
            "params": [
                {"name": "eq1", "type": "int", "min": -12, "max": 12},
                {"name": "eq2", "type": "int", "min": -12, "max": 12},
                {"name": "eq3", "type": "int", "min": -12, "max": 12},
                {"name": "eq4", "type": "int", "min": -12, "max": 12},
                {"name": "eq5", "type": "int", "min": -12, "max": 12},
                {"name": "eq6", "type": "int", "min": -12, "max": 12},
                {"name": "eq7", "type": "int", "min": -12, "max": 12},
            ],
        },
        # ── Mixer ─────────────────────────────────────────────────────────
        "set_mixer_fade": {
            "description": "Set mixer fade behavior",
            "params": [{"name": "fade_behavior", "type": "str",
                        "options": ["Off", "Fast", "Medium", "Slow"]}],
        },
        # ── Dante input ───────────────────────────────────────────────────
        "set_dante_input_gain": {
            "description": "Set Dante input gain for a channel (-30 to 30 dB)",
            "params": [
                {"name": "channel_id", "type": "int"},
                {"name": "gain", "type": "int", "min": -30, "max": 30},
            ],
        },
        # ── Dante network settings ────────────────────────────────────────
        "dante_continuous_stream_on": {
            "description": "Enable continuous Dante stream",
            "params": [],
        },
        "dante_continuous_stream_off": {
            "description": "Disable continuous Dante stream",
            "params": [],
        },
        "dante_speaker_output_on": {
            "description": "Enable Dante speaker output",
            "params": [],
        },
        "dante_speaker_output_off": {
            "description": "Disable Dante speaker output",
            "params": [],
        },
    }

    QUERY_COMMANDS = {
        "device_info":        "get_device_identity",
        "status":             "get_device_state",
        "mute":               "get_mute_state",
        "mic_level":          "get_mic_level",
        "beam_position":      "get_beam_position",
        "speaker":            "get_speaker_output",
        "noise_gate":         "get_noise_gate",
        "noise_suppression":  "get_noise_suppression",
        "sound_profile":      "get_sound_profile",
        "conference_output":  "get_conference_output",
        "led_ring":           "get_led_ring",
        "site_info":          "get_device_site",
        "firmware":           "get_firmware_update_state",
        "camera_ai":          "get_camera_ai_access",
        "camera_video":       "get_camera_video_parameters",
        "camera_movement":    "get_camera_movement",
        "camera_status":      "get_camera_status",
        "hdmi":               "get_hdmi_enabled",
        "network":            "get_network_interfaces",
        "dante_status":       "get_dante_status",
        "dante_settings":     "get_dante_settings",
        "bluetooth":          "get_bluetooth_settings",
        "wifi":               "get_wifi_status",
        "priority_zones":     "get_priority_zones",
        "exclusion_zones":    "get_exclusion_zones",
        "device_profile":     "get_device_profile",
        "sound_prompts":      "get_sound_prompts",
        "standby_mode":       "get_allowed_standby_mode",
        "active_channel":     "get_active_mic_channel",
        "mixer":              "get_mixer_fade_behavior",
    }

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.username    = self.config.get("username", "")
        self.password    = self.config.get("password", "")
        self.auth_header = None
        self.ssl_context = None
        self._setup_connection()

    def _setup_connection(self):
        if self.username and self.password:
            auth_string      = f"{self.username}:{self.password}"
            self.auth_header = base64.b64encode(auth_string.encode()).decode("ascii")
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode    = ssl.CERT_NONE

    # ── helpers ───────────────────────────────────────────────────────────

    def _normalize_angle(self, angle: int) -> int:
        """Normalize angle to 0-180 range"""
        if angle < 0:
            return 0
        if angle > 180:
            return 180
        return angle

    def _make_request(self, method: str, url: str, data=None):
        headers = {"Accept": "application/json"}
        if self.auth_header:
            headers["Authorization"] = f"Basic {self.auth_header}"

        request_data = None
        if data is not None and method in ("PUT", "POST"):
            headers["Content-Type"] = "application/json"
            request_data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
        try:
            response      = urllib.request.urlopen(req, context=self.ssl_context, timeout=10)
            response_data = response.read().decode("utf-8")
            return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise Exception("Authentication failed - Invalid username or password")
            if e.code == 403:
                raise Exception("Forbidden - Check 3rd party access settings")
            error_msg = e.read().decode("utf-8") if e.fp else str(e)
            return {"error": f"HTTP {e.code}", "message": error_msg}
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    def _get_base_url(self, ip: str) -> str:
        return f"https://{ip}:443/api"

    # ── device info ───────────────────────────────────────────────────────

    def get_device_info(self, ip: str, port: int = 443, display_id: str = None) -> dict:
        if not self.username or not self.password:
            return {
                "ip_address": ip, "port": port, "display_id": display_id,
                "make": "Sennheiser", "device_type": "TC Bar M",
                "current_status": "Offline",
                "error": "Missing credentials: username and password are required.",
            }

        base_url = self._get_base_url(ip)
        try:
            identity          = self._make_request("GET", f"{base_url}/device/identity")
            state             = self._make_request("GET", f"{base_url}/device/state")
            firmware          = self._make_request("GET", f"{base_url}/firmware/update/state")
            site              = self._make_request("GET", f"{base_url}/device/site")
            led               = self._make_request("GET", f"{base_url}/device/leds/ring")
            profile           = self._make_request("GET", f"{base_url}/device/profile")
            mute              = self._make_request("GET", f"{base_url}/audio/inputs/mute")
            mic               = self._make_request("GET", f"{base_url}/audio/inputs/internalMic")
            mic_level         = self._make_request("GET", f"{base_url}/audio/inputs/internalMic/level")
            speaker           = self._make_request("GET", f"{base_url}/audio/outputs/speaker")
            noise_gate        = self._make_request("GET", f"{base_url}/audio/inputs/internalMic/noiseGate")
            noise_supp        = self._make_request("GET", f"{base_url}/audio/inputs/noiseSuppression")
            sound_profile     = self._make_request("GET", f"{base_url}/audio/soundProfile")
            conf_output       = self._make_request("GET", f"{base_url}/audio/outputs/conferenceOutput")
            beam              = self._make_request("GET", f"{base_url}/audio/inputs/internalMic/beam")
            mixer             = self._make_request("GET", f"{base_url}/audio/inputs/mixer")
            active_ch         = self._make_request("GET", f"{base_url}/audio/inputs/mixer/activity")
            camera_ai         = self._make_request("GET", f"{base_url}/video/input/internalCamera/aiAccess")
            camera_video      = self._make_request("GET", f"{base_url}/video/input/internalCamera/videoParameters")
            camera_movement   = self._make_request("GET", f"{base_url}/video/input/internalCamera/movement")
            camera_status     = self._make_request("GET", f"{base_url}/video/input/internalCamera")
            hdmi              = self._make_request("GET", f"{base_url}/video/output/hdmi")
            bluetooth         = self._make_request("GET", f"{base_url}/interfaces/bluetooth")
            wifi              = self._make_request("GET", f"{base_url}/interfaces/network/wifi")
            dante_settings    = self._make_request("GET", f"{base_url}/interfaces/network/dante/settings")
            feedback          = self._make_request("GET", f"{base_url}/device/feedback")
            standby           = self._make_request("GET", f"{base_url}/device/allowedStandbyMode")

            # ── priority zones (values are already in degrees) ──
            pz_raw = self._make_request("GET", f"{base_url}/audio/inputs/internalMic/priorityZones")
            priority_zones = pz_raw if isinstance(pz_raw, list) else []

            # ── exclusion zones (values are already in degrees) ──
            ez_raw = self._make_request("GET", f"{base_url}/audio/inputs/internalMic/exclusionZones")
            exclusion_zones = ez_raw if isinstance(ez_raw, list) else []

            return {
                "ip_address":           ip,
                "port":                 port,
                "display_id":           display_id,
                "make":                 "Sennheiser",
                "device_type":          "TC Bar M",
                "device_name":          identity.get("product", "Sennheiser TC Bar M"),
                "model":                identity.get("product", "TC Bar M"),
                "serial_number":        identity.get("serial"),
                "hardware_revision":    identity.get("hardwareRevision"),
                "firmware":             firmware.get("deviceVersion"),
                "firmware_state":       firmware.get("state", "Idle"),
                "firmware_progress":    firmware.get("progress", 0),
                "current_status":       state.get("state", "Unknown"),
                "warnings":             state.get("warnings", []),
                "site_name":            site.get("deviceName", "Unknown"),
                "site_location":        site.get("location", "Unknown"),
                "site_position":        site.get("position", "Unknown"),
                "site_language":        site.get("language", "En_GB"),
                "device_profile":       profile.get("configuration", "Custom"),
                "led_brightness":       led.get("brightness", 3),
                "mute_enabled":         mute.get("enabled", False),
                "mic_gain":             mic.get("gain", 0),
                "mic_enabled":          mic.get("enabled", True),
                "microphone_level":     mic_level.get("peak", 0),
                "speaker_volume":       speaker.get("volume", 50),
                "speaker_level_limiter":speaker.get("levelLimiter", 100),
                "noisegate_enabled":    noise_gate.get("enabled", False),
                "noisegate_threshold":  noise_gate.get("threshold", -40),
                "noisegate_holdtime":   noise_gate.get("holdTime", 300),
                "noisegate_range":      noise_gate.get("range", -40),
                "noise_suppression":    noise_supp.get("weighting", "Medium"),
                "sound_profile":        sound_profile.get("preset", "Wallmount"),
                "far_end_gain":         conf_output.get("farEndGain", 0),
                "near_end_gain":        conf_output.get("nearEndGain", 0),
                "beam_position":        beam.get("position", 0),
                "mixer_fade":           mixer.get("fadeBehavior", "Off"),
                "active_channel":       active_ch.get("activeChannel", "Unknown"),
                "camera_active":        camera_status.get("active", False),
                "autoframing_enabled":  camera_ai.get("autoFramingAccessEnabled", False),
                "autoframing_access":   camera_ai.get("autoFramingAccessEnabled", False),
                "autoframing_raw_enabled": camera_ai.get("autoFramingEnabled", False),
                "tiling_enabled":       camera_ai.get("personTilingAccessEnabled", False),
                "tiling_access":        camera_ai.get("personTilingAccessEnabled", False),
                "tiling_raw_enabled":   camera_ai.get("personTilingEnabled", False),
                "camera_brightness":    camera_video.get("brightness", 0),
                "camera_contrast":      camera_video.get("contrast", 5),
                "camera_saturation":    camera_video.get("saturation", 5),
                "camera_sharpness":     camera_video.get("sharpness", 2),
                "camera_auto_wb":       camera_video.get("autoWhitebalanceEnabled", True),
                "camera_whitebalance":  camera_video.get("whitebalance", 4600),
                "camera_antiflicker":   camera_video.get("antiFlickerFrequency", "Auto"),
                "camera_backlight":     camera_video.get("backlightCompensationEnabled", True),
                "camera_lowlight":      camera_video.get("lowlightCompensationEnabled", False),
                "camera_pan":           camera_movement.get("panPosition", 0),
                "camera_tilt":          camera_movement.get("tiltPosition", 0),
                "camera_zoom":          camera_movement.get("zoomPosition", 100),
                "camera_zoom_speed":    camera_movement.get("zoomSpeed", "Medium"),
                "camera_pantilt_speed": camera_movement.get("panTiltSpeed", "Medium"),
                "camera_autoframing_speed": camera_movement.get("autoFramingSpeed", "Medium"),
                "hdmi_enabled":         hdmi.get("enabled", False),
                "bluetooth_enabled":    bluetooth.get("enabled", False),
                "bluetooth_pairing":    bluetooth.get("pairing", False),
                "bluetooth_mac":        bluetooth.get("mac", ""),
                "wifi_enabled":         wifi.get("enabled", False),
                "wifi_state":           wifi.get("state", "Disconnected"),
                "dante_continuous_stream": dante_settings.get("continuousDanteStream", False),
                "dante_speaker_output": dante_settings.get("danteSpeakerOutput", False),
                "sound_prompts":        feedback.get("soundPrompts", True),
                "standby_mode":         standby.get("mode", "Off"),
                "priority_zones":       priority_zones,
                "exclusion_zones":      exclusion_zones,
            }

        except Exception as e:
            return {
                "ip_address": ip, "port": port, "display_id": display_id,
                "make": "Sennheiser", "device_type": "TC Bar M",
                "current_status": "Offline", "error": str(e),
            }

    # ── query_status ──────────────────────────────────────────────────────

    def query_status(self, ip: str, port: int = 443, display_id: str = None) -> dict:
        info      = self.get_device_info(ip, port, display_id)
        reachable = info.get("current_status") in ("Normal", "Online", "Ready", True)

        return {
            "reachable":             reachable,
            "power":                 "ON" if reachable else "OFF",
            "device_name":           info.get("device_name"),
            "model":                 info.get("model"),
            "serial_number":         info.get("serial_number"),
            "firmware":              info.get("firmware"),
            "firmware_state":        info.get("firmware_state"),
            "firmware_progress":     info.get("firmware_progress"),
            "device_profile":        info.get("device_profile"),
            "mute_status":           info.get("mute_enabled"),
            "mute":                  "ON" if info.get("mute_enabled") else "OFF",
            "mic_gain":              info.get("mic_gain"),
            "mic_enabled":           info.get("mic_enabled"),
            "microphone_level":      info.get("microphone_level"),
            "speaker_volume":        info.get("speaker_volume"),
            "speaker_level_limiter": info.get("speaker_level_limiter"),
            "noisegate_enabled":     info.get("noisegate_enabled"),
            "noisegate_threshold":   info.get("noisegate_threshold"),
            "noisegate_holdtime":    info.get("noisegate_holdtime"),
            "noisegate_range":       info.get("noisegate_range"),
            "noise_suppression":     info.get("noise_suppression"),
            "sound_profile":         info.get("sound_profile"),
            "far_end_gain":          info.get("far_end_gain"),
            "near_end_gain":         info.get("near_end_gain"),
            "beam_position":         info.get("beam_position"),
            "mixer_fade":            info.get("mixer_fade"),
            "active_channel":        info.get("active_channel"),
            "led_brightness":        info.get("led_brightness"),
            "site_name":             info.get("site_name"),
            "site_location":         info.get("site_location"),
            "camera_active":         info.get("camera_active"),
            "autoframing_enabled":   info.get("autoframing_access", info.get("autoframing_enabled")),
            "autoframing_access":    info.get("autoframing_access"),
            "autoframing_raw_enabled": info.get("autoframing_raw_enabled"),
            "tiling_enabled":        info.get("tiling_access", info.get("tiling_enabled")),
            "tiling_access":         info.get("tiling_access"),
            "tiling_raw_enabled":    info.get("tiling_raw_enabled"),
            "camera_brightness":     info.get("camera_brightness"),
            "camera_contrast":       info.get("camera_contrast"),
            "camera_saturation":     info.get("camera_saturation"),
            "camera_sharpness":      info.get("camera_sharpness"),
            "camera_auto_wb":        info.get("camera_auto_wb"),
            "camera_whitebalance":   info.get("camera_whitebalance"),
            "camera_antiflicker":    info.get("camera_antiflicker"),
            "camera_backlight":      info.get("camera_backlight"),
            "camera_lowlight":       info.get("camera_lowlight"),
            "camera_pan":            info.get("camera_pan"),
            "camera_tilt":           info.get("camera_tilt"),
            "camera_zoom":           info.get("camera_zoom"),
            "camera_zoom_speed":     info.get("camera_zoom_speed"),
            "camera_pantilt_speed":  info.get("camera_pantilt_speed"),
            "camera_autoframing_speed": info.get("camera_autoframing_speed"),
            "hdmi_enabled":          info.get("hdmi_enabled"),
            "bluetooth_enabled":     info.get("bluetooth_enabled"),
            "wifi_enabled":          info.get("wifi_enabled"),
            "wifi_state":            info.get("wifi_state"),
            "dante_continuous_stream": info.get("dante_continuous_stream"),
            "dante_speaker_output":  info.get("dante_speaker_output"),
            "sound_prompts":         info.get("sound_prompts"),
            "standby_mode":          info.get("standby_mode"),
            "priority_zones":        info.get("priority_zones", []),
            "exclusion_zones":       info.get("exclusion_zones", []),
            "error":                 info.get("error"),
        }

    # ── low-level helpers ─────────────────────────────────────────────────

    def _get_priority_zone(self, ip: str, zone_id: int) -> dict:
        base_url = self._get_base_url(ip)
        return self._make_request("GET", f"{base_url}/audio/inputs/internalMic/priorityZones/{zone_id}")

    def _set_priority_zone(self, ip: str, zone_id: int, enabled: bool = None,
                           gain: str = None, left_deg: int = None, right_deg: int = None) -> dict:
        """Set priority zone - values are in degrees directly (no conversion needed)"""
        base_url = self._get_base_url(ip)
        current  = self._get_priority_zone(ip, zone_id)
        if "error" in current:
            raise Exception(f"Failed to read priority zone {zone_id}: {current}")

        data = {}
        
        if enabled is not None:
            data["enabled"] = enabled
        elif "enabled" in current:
            data["enabled"] = current.get("enabled", False)
        
        if gain is not None:
            data["gain"] = gain
        elif "gain" in current:
            data["gain"] = current.get("gain", "Medium")
        
        if left_deg is not None:
            data["left"] = self._normalize_angle(left_deg)
        elif "left" in current:
            data["left"] = current.get("left", 0)
        
        if right_deg is not None:
            data["right"] = self._normalize_angle(right_deg)
        elif "right" in current:
            data["right"] = current.get("right", 100)
        
        return self._make_request("PUT",
                                  f"{base_url}/audio/inputs/internalMic/priorityZones/{zone_id}",
                                  data=data)

    def _get_exclusion_zone(self, ip: str, zone_id: int) -> dict:
        base_url = self._get_base_url(ip)
        return self._make_request("GET", f"{base_url}/audio/inputs/internalMic/exclusionZones/{zone_id}")

    def _set_exclusion_zone(self, ip: str, zone_id: int, enabled: bool = None,
                            left_deg: int = None, right_deg: int = None) -> dict:
        """Set exclusion zone - values are in degrees directly (no conversion needed)"""
        base_url = self._get_base_url(ip)
        current  = self._get_exclusion_zone(ip, zone_id)
        if "error" in current:
            raise Exception(f"Failed to read exclusion zone {zone_id}: {current}")

        data = {}
        
        if enabled is not None:
            data["enabled"] = enabled
        elif "enabled" in current:
            data["enabled"] = current.get("enabled", False)
        
        if left_deg is not None:
            data["left"] = self._normalize_angle(left_deg)
        elif "left" in current:
            data["left"] = current.get("left", 0)
        
        if right_deg is not None:
            data["right"] = self._normalize_angle(right_deg)
        elif "right" in current:
            data["right"] = current.get("right", 100)
        
        return self._make_request("PUT",
                                  f"{base_url}/audio/inputs/internalMic/exclusionZones/{zone_id}",
                                  data=data)

    def _get_camera_video(self, base_url: str) -> dict:
        return self._make_request("GET", f"{base_url}/video/input/internalCamera/videoParameters")

    def _set_camera_video(self, ip: str, **kwargs) -> dict:
        base_url = self._get_base_url(ip)
        current  = self._get_camera_video(base_url)
        data = {
            "brightness":                  kwargs.get("brightness",          current.get("brightness", 0)),
            "contrast":                    kwargs.get("contrast",            current.get("contrast", 5)),
            "saturation":                  kwargs.get("saturation",          current.get("saturation", 5)),
            "sharpness":                   kwargs.get("sharpness",           current.get("sharpness", 2)),
            "autoWhitebalanceEnabled":     kwargs.get("auto_whitebalance",   current.get("autoWhitebalanceEnabled", True)),
            "whitebalance":                kwargs.get("whitebalance",        current.get("whitebalance", 4600)),
            "antiFlickerFrequency":        kwargs.get("anti_flicker",        current.get("antiFlickerFrequency", "Auto")),
            "backlightCompensationEnabled":kwargs.get("backlight",           current.get("backlightCompensationEnabled", True)),
            "lowlightCompensationEnabled": kwargs.get("lowlight",            current.get("lowlightCompensationEnabled", False)),
        }
        return self._make_request("PUT",
                                  f"{base_url}/video/input/internalCamera/videoParameters",
                                  data=data)

    def _get_camera_movement(self, base_url: str) -> dict:
        return self._make_request("GET", f"{base_url}/video/input/internalCamera/movement")

    def _set_camera_movement(self, ip: str, **kwargs) -> dict:
        base_url = self._get_base_url(ip)
        current  = self._get_camera_movement(base_url)
        data = {
            "panPosition":      kwargs.get("pan",                current.get("panPosition", 0)),
            "tiltPosition":     kwargs.get("tilt",               current.get("tiltPosition", 0)),
            "zoomPosition":     kwargs.get("zoom",               current.get("zoomPosition", 100)),
            "zoomSpeed":        kwargs.get("zoom_speed",         current.get("zoomSpeed", "Medium")),
            "panTiltSpeed":     kwargs.get("pan_tilt_speed",     current.get("panTiltSpeed", "Medium")),
            "autoFramingSpeed": kwargs.get("autoframing_speed",  current.get("autoFramingSpeed", "Medium")),
        }
        return self._make_request("PUT",
                                  f"{base_url}/video/input/internalCamera/movement",
                                  data=data)

    def _get_camera_ai(self, base_url: str) -> dict:
        return self._make_request("GET", f"{base_url}/video/input/internalCamera/aiAccess")

    # def _set_camera_ai(self, ip: str, auto_framing: bool = None,
    #                    person_tiling: bool = None) -> dict:
    #     """Set camera AI UI toggles (AccessEnabled controls the UI switch)"""
    #     base_url = self._get_base_url(ip)
    #     current = self._get_camera_ai(base_url)
        
    #     # Build the payload - AccessEnabled controls UI toggles, Enabled always false
    #     data = {
    #         "autoFramingAccessEnabled": current.get("autoFramingAccessEnabled", False),
    #         "autoFramingEnabled": False,  # Always false per Cockpit behavior
    #         "personTilingAccessEnabled": current.get("personTilingAccessEnabled", False),
    #         "personTilingEnabled": False,  # Always false per Cockpit behavior
    #     }
        
    #     # Update auto framing AccessEnabled if provided
    #     if auto_framing is not None:
    #         data["autoFramingAccessEnabled"] = auto_framing
        
    #     # Update person tiling AccessEnabled if provided
    #     if person_tiling is not None:
    #         data["personTilingAccessEnabled"] = person_tiling
        
    #     return self._make_request("PUT",
    #                               f"{base_url}/video/input/internalCamera/aiAccess",
    #                               data=data)


    def _set_camera_ai(self, ip: str, auto_framing: bool = None,
                   person_tiling: bool = None) -> dict:
        """Set camera AI UI toggles via the AccessEnabled flags."""
        base_url = self._get_base_url(ip)
        current = self._get_camera_ai(base_url)
        
        data = {
            "autoFramingAccessEnabled": current.get("autoFramingAccessEnabled", False),
            "autoFramingEnabled": False,
            "personTilingAccessEnabled": current.get("personTilingAccessEnabled", False),
            "personTilingEnabled": False,
        }
        
        if auto_framing is not None:
            data["autoFramingAccessEnabled"] = auto_framing
        
        if person_tiling is not None:
            data["personTilingAccessEnabled"] = person_tiling
        
        return self._make_request("PUT",
                                f"{base_url}/video/input/internalCamera/aiAccess",
                                data=data)

    def _get_noise_gate(self, base_url: str) -> dict:
        return self._make_request("GET", f"{base_url}/audio/inputs/internalMic/noiseGate")

    def _set_noise_gate(self, ip: str, enabled: bool = None, threshold: int = None,
                        hold_time: int = None, range_val: int = None) -> dict:
        base_url = self._get_base_url(ip)
        current  = self._get_noise_gate(base_url)
        data = {
            "enabled":   enabled    if enabled    is not None else current.get("enabled", False),
            "threshold": threshold  if threshold  is not None else current.get("threshold", -40),
            "holdTime":  hold_time  if hold_time  is not None else current.get("holdTime", 300),
            "range":     range_val  if range_val  is not None else current.get("range", -40),
        }
        return self._make_request("PUT",
                                  f"{base_url}/audio/inputs/internalMic/noiseGate",
                                  data=data)

    def _get_internal_mic(self, base_url: str) -> dict:
        return self._make_request("GET", f"{base_url}/audio/inputs/internalMic")

    def _get_speaker_output(self, base_url: str) -> dict:
        return self._make_request("GET", f"{base_url}/audio/outputs/speaker")

    def _get_conference_output(self, base_url: str) -> dict:
        return self._make_request("GET", f"{base_url}/audio/outputs/conferenceOutput")

    def _get_dante_settings(self, base_url: str) -> dict:
        return self._make_request("GET", f"{base_url}/interfaces/network/dante/settings")

    def _get_bluetooth(self, base_url: str) -> dict:
        return self._make_request("GET", f"{base_url}/interfaces/bluetooth")

    def _stop_identification(self, base_url: str):
        try:
            self._make_request("PUT", f"{base_url}/device/identification",
                                data={"visual": False})
        except Exception:
            pass

    # ── send_command ──────────────────────────────────────────────────────

    def send_command(self, ip: str, port: int, display_id: str,
                     command: str, params: dict = None) -> tuple:
        if not self.username or not self.password:
            return False, "Missing credentials: username and password are required."

        base_url = self._get_base_url(ip)
        params   = params or {}

        try:
            # ── basic mic ──────────────────────────────────────────────────
            if command == "mute":
                self._make_request("PUT", f"{base_url}/audio/inputs/mute",
                                   data={"enabled": True})
                return True, "Microphone muted successfully"

            elif command == "unmute":
                self._make_request("PUT", f"{base_url}/audio/inputs/mute",
                                   data={"enabled": False})
                return True, "Microphone unmuted successfully"

            elif command == "identify":
                self._make_request("PUT", f"{base_url}/device/identification",
                                   data={"visual": True})
                threading.Timer(10.0,
                                lambda: self._stop_identification(base_url)).start()
                return True, "Device identification started - LEDs will blink for 10 seconds"

            # ── LED ────────────────────────────────────────────────────────
            elif command in ("restart", "reboot"):
                self._make_request("PUT", f"{base_url}/device/restart")
                return True, "Device restart command sent"

            elif command == "set_led_brightness":
                brightness = params.get("brightness", 3)
                if not 0 <= brightness <= 5:
                    return False, "Brightness must be between 0 and 5"
                self._make_request("PUT", f"{base_url}/device/leds/ring",
                                   data={"brightness": brightness})
                return True, f"LED brightness set to {brightness}"

            # ── mic ───────────────────────────────────────────────────────
            elif command == "set_mic_gain":
                gain = params.get("gain", 0)
                if not -30 <= gain <= 30:
                    return False, "Gain must be between -30 and 30 dB"
                current = self._get_internal_mic(base_url)
                self._make_request("PUT", f"{base_url}/audio/inputs/internalMic",
                                   data={"gain": gain,
                                         "enabled": current.get("enabled", True)})
                return True, f"Mic gain set to {gain} dB"

            elif command == "mic_enable":
                current = self._get_internal_mic(base_url)
                self._make_request("PUT", f"{base_url}/audio/inputs/internalMic",
                                   data={"gain": current.get("gain", 0),
                                         "enabled": True})
                return True, "Microphone ENABLED"

            elif command == "mic_disable":
                current = self._get_internal_mic(base_url)
                self._make_request("PUT", f"{base_url}/audio/inputs/internalMic",
                                   data={"gain": current.get("gain", 0),
                                         "enabled": False})
                return True, "Microphone DISABLED"

            # ── speaker ───────────────────────────────────────────────────
            elif command == "set_volume":
                volume = params.get("volume", 50)
                if not 0 <= volume <= 100:
                    return False, "Volume must be between 0 and 100"
                self._make_request("PUT", f"{base_url}/audio/outputs/speaker",
                                   data={"volume": volume})
                return True, f"Volume set to {volume}%"

            elif command == "volume_up":
                steps = params.get("steps", 5)
                self._make_request("PUT", f"{base_url}/audio/outputs/speaker/relative",
                                   data={"volumeUp": steps})
                return True, f"Volume increased by {steps}"

            elif command == "volume_down":
                steps = params.get("steps", 5)
                self._make_request("PUT", f"{base_url}/audio/outputs/speaker/relative",
                                   data={"volumeDown": steps})
                return True, f"Volume decreased by {steps}"

            elif command == "set_level_limiter":
                level_limiter = params.get("level_limiter", 100)
                if not 0 <= level_limiter <= 100:
                    return False, "Level limiter must be between 0 and 100"
                current = self._get_speaker_output(base_url)
                self._make_request("PUT", f"{base_url}/audio/outputs/speaker",
                                   data={"volume": current.get("volume", 50),
                                         "levelLimiter": level_limiter})
                return True, f"Level limiter set to {level_limiter}"

            # ── noise gate ────────────────────────────────────────────────
            elif command == "noisegate_on":
                self._set_noise_gate(ip, enabled=True)
                return True, "Noise gate ENABLED"

            elif command == "noisegate_off":
                self._set_noise_gate(ip, enabled=False)
                return True, "Noise gate DISABLED"

            elif command == "set_noisegate":
                threshold = params.get("threshold", -40)
                hold_time = params.get("hold_time", 300)
                range_val = params.get("range_val", -40)
                if not -80 <= threshold <= -20:
                    return False, "Threshold must be between -80 and -20 dB"
                if not 100 <= hold_time <= 2000:
                    return False, "Hold time must be between 100 and 2000 ms"
                if not -80 <= range_val <= 0:
                    return False, "Range must be between -80 and 0 dB"
                self._set_noise_gate(ip, enabled=True,
                                     threshold=threshold,
                                     hold_time=hold_time,
                                     range_val=range_val)
                return True, f"Noise gate set: threshold={threshold}dB, hold={hold_time}ms, range={range_val}dB"

            # ── noise suppression ─────────────────────────────────────────
            elif command == "set_noise_suppression":
                weighting = params.get("weighting", "Medium")
                if weighting not in ["Off", "Low", "Medium", "High"]:
                    return False, f"Invalid weighting: {weighting}"
                self._make_request("PUT", f"{base_url}/audio/inputs/noiseSuppression",
                                   data={"weighting": weighting})
                return True, f"Noise suppression set to {weighting}"

            # ── sound profile ─────────────────────────────────────────────
            elif command == "set_sound_profile":
                preset = params.get("preset", "Wallmount")
                valid_presets = ["Wallmount", "TableTop", "UnderDisplay", 
                                "AboveDisplay", "FreeStanding", "Custom"]
                if preset not in valid_presets:
                    return False, f"Invalid preset: {preset}. Must be one of: {valid_presets}"
                self._make_request("PUT", f"{base_url}/audio/soundProfile",
                                   data={"preset": preset})
                return True, f"Sound profile set to {preset}"

            # ── conference output ─────────────────────────────────────────
            elif command == "set_far_end_gain":
                gain = params.get("gain", 0)
                if not -18 <= gain <= 18:
                    return False, "Gain must be between -18 and 18 dB"
                current = self._get_conference_output(base_url)
                self._make_request("PUT", f"{base_url}/audio/outputs/conferenceOutput",
                                   data={"farEndGain": gain,
                                         "nearEndGain": current.get("nearEndGain", 0)})
                return True, f"Far end gain set to {gain} dB"

            elif command == "set_near_end_gain":
                gain = params.get("gain", 0)
                if not -18 <= gain <= 18:
                    return False, "Gain must be between -18 and 18 dB"
                current = self._get_conference_output(base_url)
                self._make_request("PUT", f"{base_url}/audio/outputs/conferenceOutput",
                                   data={"farEndGain": current.get("farEndGain", 0),
                                         "nearEndGain": gain})
                return True, f"Near end gain set to {gain} dB"

            # ── device profile ────────────────────────────────────────────
            elif command == "set_device_profile":
                configuration = params.get("configuration", "Custom")
                if configuration not in ["Custom", "MicrosoftTeams", "Zoom"]:
                    return False, f"Invalid profile: {configuration}"
                self._make_request("PUT", f"{base_url}/device/profile",
                                data={"configuration": configuration})
                return True, f"Device profile set to {configuration}"

            # ── sound prompts ─────────────────────────────────────────────
            elif command == "sound_prompts_on":
                self._make_request("PUT", f"{base_url}/device/feedback",
                                   data={"soundPrompts": True})
                return True, "Sound prompts ENABLED"

            elif command == "sound_prompts_off":
                self._make_request("PUT", f"{base_url}/device/feedback",
                                   data={"soundPrompts": False})
                return True, "Sound prompts DISABLED"

            # ── standby mode ──────────────────────────────────────────────
            elif command == "set_standby_mode":
                mode = params.get("mode", "Off")
                if mode not in ["Off", "EcoMode", "DeepSleep"]:
                    return False, f"Invalid mode: {mode}"
                self._make_request("PUT", f"{base_url}/device/allowedStandbyMode",
                                   data={"mode": mode})
                return True, f"Standby mode set to {mode}"

            # ── priority zones ────────────────────────────────────────────
            elif command == "enable_priority_zone":
                zone_id = params.get("zone_id")
                enable  = params.get("enable")
                if zone_id is None or enable is None:
                    return False, "zone_id and enable are required"
                self._set_priority_zone(ip, int(zone_id), enabled=bool(enable))
                return True, f"Priority zone {zone_id} {'enabled' if enable else 'disabled'}"

            elif command == "set_priority_zone_gain":
                zone_id = params.get("zone_id")
                gain    = params.get("gain")
                if zone_id is None or gain is None:
                    return False, "zone_id and gain are required"
                if gain not in ["Off", "Low", "Medium", "High"]:
                    return False, f"Invalid gain: {gain}"
                self._set_priority_zone(ip, int(zone_id), gain=gain)
                return True, f"Priority zone {zone_id} gain set to {gain}"

            elif command == "set_priority_zone_range":
                zone_id   = params.get("zone_id")
                left_deg  = params.get("left_deg")
                right_deg = params.get("right_deg")
                if zone_id is None or left_deg is None or right_deg is None:
                    return False, "zone_id, left_deg and right_deg are required"
                if not 0 <= left_deg <= 180 or not 0 <= right_deg <= 180:
                    return False, "Degrees must be between 0 and 180"
                # Don't auto-swap for priority zones - preserve wrap-around
                self._set_priority_zone(ip, int(zone_id),
                                        left_deg=int(left_deg),
                                        right_deg=int(right_deg))
                return True, f"Priority zone {zone_id} range set to {left_deg}° - {right_deg}°"

            elif command == "set_priority_zone":
                zone_id   = params.get("zone_id")
                if zone_id is None:
                    return False, "zone_id is required"
                self._set_priority_zone(
                    ip, int(zone_id),
                    enabled   = params.get("enabled"),
                    gain      = params.get("gain"),
                    left_deg  = params.get("left_deg"),
                    right_deg = params.get("right_deg"),
                )
                return True, f"Priority zone {zone_id} updated"

            # ── exclusion zones ───────────────────────────────────────────
            elif command == "enable_exclusion_zone":
                zone_id = params.get("zone_id")
                enable  = params.get("enable")
                if zone_id is None or enable is None:
                    return False, "zone_id and enable are required"
                self._set_exclusion_zone(ip, int(zone_id), enabled=bool(enable))
                return True, f"Exclusion zone {zone_id} {'enabled' if enable else 'disabled'}"

            elif command == "set_exclusion_zone_range":
                zone_id   = params.get("zone_id")
                left_deg  = params.get("left_deg")
                right_deg = params.get("right_deg")
                if zone_id is None or left_deg is None or right_deg is None:
                    return False, "zone_id, left_deg and right_deg are required"
                if not 0 <= left_deg <= 180 or not 0 <= right_deg <= 180:
                    return False, "Degrees must be between 0 and 180"
                # Don't auto-swap for exclusion zones - preserve wrap-around
                self._set_exclusion_zone(ip, int(zone_id),
                                         left_deg=int(left_deg),
                                         right_deg=int(right_deg))
                return True, f"Exclusion zone {zone_id} range set to {left_deg}° - {right_deg}°"

            elif command == "set_exclusion_zone":
                zone_id = params.get("zone_id")
                if zone_id is None:
                    return False, "zone_id is required"
                self._set_exclusion_zone(
                    ip, int(zone_id),
                    enabled   = params.get("enabled"),
                    left_deg  = params.get("left_deg"),
                    right_deg = params.get("right_deg"),
                )
                return True, f"Exclusion zone {zone_id} updated"

            # ── camera AI ─────────────────────────────────────────────────
            elif command == "camera_autoframing_on":
                self._set_camera_ai(ip, auto_framing=True)
                return True, "Auto framing ACTIVATED in Cockpit"

            elif command == "camera_autoframing_off":
                self._set_camera_ai(ip, auto_framing=False)
                return True, "Auto framing DEACTIVATED in Cockpit"

            elif command == "camera_tiling_on":
                self._set_camera_ai(ip, person_tiling=True)
                return True, "Person tiling ACTIVATED in Cockpit"

            elif command == "camera_tiling_off":
                self._set_camera_ai(ip, person_tiling=False)
                return True, "Person tiling DEACTIVATED in Cockpit"

            elif command == "camera_ffov":
                self._make_request("PUT",
                                   f"{base_url}/video/input/internalCamera/ffov")
                return True, "Camera reset to full field of view"

            elif command == "camera_preset_store":
                self._make_request("PUT",
                                   f"{base_url}/video/input/internalCamera/preset/store")
                return True, "Camera preset STORED"

            elif command == "camera_preset_load":
                self._make_request("PUT",
                                   f"{base_url}/video/input/internalCamera/preset/load")
                return True, "Camera preset LOADED"

            # ── camera movement ───────────────────────────────────────────
            elif command == "camera_move":
                direction = params.get("direction", "up")
                steps     = params.get("steps", 1)
                move_map  = {
                    "up":       {"up": steps},
                    "down":     {"down": steps},
                    "left":     {"left": steps},
                    "right":    {"right": steps},
                    "zoom_in":  {"zoomIn": steps},
                    "zoom_out": {"zoomOut": steps},
                }
                if direction not in move_map:
                    return False, f"Invalid direction: {direction}"
                data = {"up": 0, "down": 0, "left": 0, "right": 0,
                        "zoomIn": 0, "zoomOut": 0}
                data.update(move_map[direction])
                self._make_request("PUT",
                                   f"{base_url}/video/input/internalCamera/movement/relative",
                                   data=data)
                return True, f"Camera moved {direction} by {steps}"

            elif command == "set_camera_pan":
                pan = params.get("pan", 0)
                if not 0 <= pan <= 360:
                    return False, "Pan must be between 0 and 360 degrees"
                self._set_camera_movement(ip, pan=pan)
                return True, f"Camera pan set to {pan}°"

            elif command == "set_camera_tilt":
                tilt = params.get("tilt", 0)
                if not -25 <= tilt <= 25:
                    return False, "Tilt must be between -25 and 25 degrees"
                self._set_camera_movement(ip, tilt=tilt)
                return True, f"Camera tilt set to {tilt}°"

            elif command == "set_camera_zoom":
                zoom = params.get("zoom", 100)
                if not 0 <= zoom <= 100:
                    return False, "Zoom must be between 0 and 100%"
                self._set_camera_movement(ip, zoom=zoom)
                return True, f"Camera zoom set to {zoom}%"

            elif command == "set_camera_zoom_speed":
                speed = params.get("speed", "Medium")
                if speed not in ["Slow", "Medium", "Fast"]:
                    return False, f"Invalid speed: {speed}"
                self._set_camera_movement(ip, zoom_speed=speed)
                return True, f"Camera zoom speed set to {speed}"

            elif command == "set_camera_pantilt_speed":
                speed = params.get("speed", "Medium")
                if speed not in ["Slow", "Medium", "Fast"]:
                    return False, f"Invalid speed: {speed}"
                self._set_camera_movement(ip, pan_tilt_speed=speed)
                return True, f"Camera pan/tilt speed set to {speed}"

            elif command == "set_camera_autoframing_speed":
                speed = params.get("speed", "Medium")
                if speed not in ["Slow", "Medium", "Fast"]:
                    return False, f"Invalid speed: {speed}"
                self._set_camera_movement(ip, autoframing_speed=speed)
                return True, f"Camera auto framing speed set to {speed}"

            # ── camera video parameters ───────────────────────────────────
            elif command == "set_camera_brightness":
                val = params.get("brightness", 0)
                if not -20 <= val <= 20:
                    return False, "Brightness must be between -20 and 20"
                self._set_camera_video(ip, brightness=val)
                return True, f"Camera brightness set to {val}"

            elif command == "set_camera_contrast":
                val = params.get("contrast", 5)
                if not 0 <= val <= 10:
                    return False, "Contrast must be between 0 and 10"
                self._set_camera_video(ip, contrast=val)
                return True, f"Camera contrast set to {val}"

            elif command == "set_camera_saturation":
                val = params.get("saturation", 5)
                if not 0 <= val <= 10:
                    return False, "Saturation must be between 0 and 10"
                self._set_camera_video(ip, saturation=val)
                return True, f"Camera saturation set to {val}"

            elif command == "set_camera_sharpness":
                val = params.get("sharpness", 2)
                if not 0 <= val <= 6:
                    return False, "Sharpness must be between 0 and 6"
                self._set_camera_video(ip, sharpness=val)
                return True, f"Camera sharpness set to {val}"

            elif command == "camera_whitebalance_auto":
                self._set_camera_video(ip, auto_whitebalance=True)
                return True, "Camera white balance set to AUTO"

            elif command == "set_camera_whitebalance":
                val = params.get("whitebalance", 4600)
                if not 2000 <= val <= 10000:
                    return False, "White balance must be between 2000 and 10000 K"
                self._set_camera_video(ip, auto_whitebalance=False, whitebalance=val)
                return True, f"Camera white balance set to {val}K (Manual)"

            elif command == "set_camera_antiflicker":
                freq = params.get("frequency", "Auto")
                if freq not in ["Auto", "50Hz", "60Hz", "Off"]:
                    return False, f"Invalid frequency: {freq}"
                self._set_camera_video(ip, anti_flicker=freq)
                return True, f"Camera anti-flicker set to {freq}"

            elif command == "camera_backlight_on":
                self._set_camera_video(ip, backlight=True)
                return True, "Backlight compensation ENABLED"

            elif command == "camera_backlight_off":
                self._set_camera_video(ip, backlight=False)
                return True, "Backlight compensation DISABLED"

            elif command == "camera_lowlight_on":
                self._set_camera_video(ip, lowlight=True)
                return True, "Lowlight compensation ENABLED"

            elif command == "camera_lowlight_off":
                self._set_camera_video(ip, lowlight=False)
                return True, "Lowlight compensation DISABLED"

            # ── HDMI ──────────────────────────────────────────────────────
            elif command == "hdmi_on":
                self._make_request("PUT", f"{base_url}/video/output/hdmi",
                                   data={"enabled": True})
                return True, "HDMI output ENABLED"

            elif command == "hdmi_off":
                self._make_request("PUT", f"{base_url}/video/output/hdmi",
                                   data={"enabled": False})
                return True, "HDMI output DISABLED"

            # ── Bluetooth ─────────────────────────────────────────────────
            elif command == "bluetooth_on":
                current = self._get_bluetooth(base_url)
                self._make_request("PUT", f"{base_url}/interfaces/bluetooth",
                                   data={"enabled": True,
                                         "pairing": current.get("pairing", False)})
                return True, "Bluetooth ENABLED"

            elif command == "bluetooth_off":
                current = self._get_bluetooth(base_url)
                self._make_request("PUT", f"{base_url}/interfaces/bluetooth",
                                   data={"enabled": False,
                                         "pairing": current.get("pairing", False)})
                return True, "Bluetooth DISABLED"

            # ── EQ ────────────────────────────────────────────────────────
            elif command == "set_mic_eq":
                eq_values = [params.get(f"eq{i}", 0) for i in range(1, 8)]
                for v in eq_values:
                    if not -12 <= v <= 12:
                        return False, "EQ values must be between -12 and 12 dB"
                self._make_request("PUT",
                                   f"{base_url}/audio/inputs/internalMic/customEq",
                                   data=eq_values)
                return True, f"Mic EQ set to {eq_values}"

            elif command == "set_speaker_eq":
                eq_values = [params.get(f"eq{i}", 0) for i in range(1, 8)]
                for v in eq_values:
                    if not -12 <= v <= 12:
                        return False, "EQ values must be between -12 and 12 dB"
                self._make_request("PUT",
                                   f"{base_url}/audio/outputs/speaker/customEq",
                                   data=eq_values)
                return True, f"Speaker EQ set to {eq_values}"

            # ── Mixer ─────────────────────────────────────────────────────
            elif command == "set_mixer_fade":
                fade_behavior = params.get("fade_behavior", "Off")
                if fade_behavior not in ["Off", "Fast", "Medium", "Slow"]:
                    return False, f"Invalid fade behavior: {fade_behavior}"
                self._make_request("PUT", f"{base_url}/audio/inputs/mixer",
                                   data={"fadeBehavior": fade_behavior})
                return True, f"Mixer fade behavior set to {fade_behavior}"

            # ── Dante input ───────────────────────────────────────────────
            elif command == "set_dante_input_gain":
                channel_id = params.get("channel_id")
                gain       = params.get("gain", 0)
                if channel_id is None:
                    return False, "channel_id is required"
                if not -30 <= gain <= 30:
                    return False, "Gain must be between -30 and 30 dB"
                self._make_request("PUT",
                                   f"{base_url}/audio/inputs/dante/{channel_id}",
                                   data={"gain": gain})
                return True, f"Dante input channel {channel_id} gain set to {gain} dB"

            # ── Dante network settings ────────────────────────────────────
            elif command == "dante_continuous_stream_on":
                current = self._get_dante_settings(base_url)
                self._make_request("PUT",
                                   f"{base_url}/interfaces/network/dante/settings",
                                   data={"continuousDanteStream": True,
                                         "danteSpeakerOutput": current.get("danteSpeakerOutput", False)})
                return True, "Continuous Dante stream ENABLED"

            elif command == "dante_continuous_stream_off":
                current = self._get_dante_settings(base_url)
                self._make_request("PUT",
                                   f"{base_url}/interfaces/network/dante/settings",
                                   data={"continuousDanteStream": False,
                                         "danteSpeakerOutput": current.get("danteSpeakerOutput", False)})
                return True, "Continuous Dante stream DISABLED"

            elif command == "dante_speaker_output_on":
                current = self._get_dante_settings(base_url)
                self._make_request("PUT",
                                   f"{base_url}/interfaces/network/dante/settings",
                                   data={"continuousDanteStream": current.get("continuousDanteStream", False),
                                         "danteSpeakerOutput": True})
                return True, "Dante speaker output ENABLED"

            elif command == "dante_speaker_output_off":
                current = self._get_dante_settings(base_url)
                self._make_request("PUT",
                                   f"{base_url}/interfaces/network/dante/settings",
                                   data={"continuousDanteStream": current.get("continuousDanteStream", False),
                                         "danteSpeakerOutput": False})
                return True, "Dante speaker output DISABLED"

            else:
                return False, f"Unknown command: {command}"

        except Exception as e:
            return False, str(e)

    def get_firmware_info(self, ip: str, port: int = 443) -> dict:
        base_url = self._get_base_url(ip)
        try:
            firmware = self._make_request("GET", f"{base_url}/firmware/update/state")
            return {
                "device_version":     firmware.get("deviceVersion"),
                "update_state":       firmware.get("state", "Idle"),
                "update_progress":    firmware.get("progress", 0),
                "last_update_status": firmware.get("lastStatus", "None"),
            }
        except Exception as e:
            return {"error": str(e)}
