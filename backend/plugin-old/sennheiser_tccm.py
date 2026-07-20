
"""
Manual Platform Plugin: SennheiserTCCMPlugin
"""

import urllib.request
import urllib.error
import ssl
import json
import base64
import threading
from typing import Optional, Dict, Any, List

from .base import ManualPlatformPlugin


class SennheiserTCCMPlugin(ManualPlatformPlugin):
    """Sennheiser TCC M (TeamConnect Ceiling Medium) microphone array control over HTTPS API."""

    name = "sennheiser_tccm"
    display_name = "Sennheiser TCC M"
    description = "Sennheiser TeamConnect Ceiling Medium microphone array control"
    supports_display_id = False
    supports_port = False
    default_port = 443
    SUPPORTED_MODELS = ["TCCM", "TCC2"]

    COMMANDS = {
        "mute":        {"description": "Mute the microphone",   "params": []},
        "unmute":      {"description": "Unmute the microphone", "params": []},
        "identify":    {"description": "Blink LEDs to identify device", "params": []},
        "set_led_brightness": {
            "description": "Set LED ring brightness (0–5)",
            "params": [{"name": "brightness", "type": "int", "min": 0, "max": 5}],
        },
        "set_mic_on_color": {
            "description": "Set LED color when mic is ON",
            "params": [{"name": "color", "type": "str",
                        "options": ["Green","Red","Blue","LightGreen","Yellow","Cyan","Orange"]}],
        },
        "set_mic_mute_color": {
            "description": "Set LED color when mic is MUTED",
            "params": [{"name": "color", "type": "str",
                        "options": ["Green","Red","Blue","LightGreen","Yellow","Cyan","Orange"]}],
        },
        "set_voice_lift": {
            "description": "Set voice lift emergency mute",
            "params": [
                {"name": "threshold", "type": "int", "min": -30, "max": 0},
                {"name": "timeout",   "type": "int", "min": 1,   "max": 10},
            ],
        },
        "set_beam_type": {
            "description": "Set installation type",
            "params": [{"name": "type", "type": "str",
                        "options": ["FlushMounted","SurfaceMounted","Suspended"]}],
        },
        "set_beam_threshold": {
            "description": "Set source detection threshold",
            "params": [{"name": "threshold", "type": "str",
                        "options": ["QuietRoom","NormalRoom","NoisyRoom"]}],
        },
        "set_beam_offset": {
            "description": "Set beam offset (multiples of 30)",
            "params": [{"name": "offset", "type": "int", "min": 0, "max": 330}],
        },
        "analog_mute_on":  {"description": "Mute analog output",   "params": []},
        "analog_mute_off": {"description": "Unmute analog output",  "params": []},
        "set_analog_gain": {
            "description": "Set analog output gain",
            "params": [{"name": "gain", "type": "int", "min": -18, "max": 18}],
        },
        # Dante far end
        "dante_far_gain": {
            "description": "Set far end Dante output gain",
            "params": [{"name": "gain", "type": "int", "min": -18, "max": 18}],
        },
        "dante_far_noisegate_on":   {"description": "Enable far end noise gate",   "params": []},
        "dante_far_noisegate_off":  {"description": "Disable far end noise gate",  "params": []},
        "dante_far_equalizer_on":   {"description": "Enable far end equalizer",    "params": []},
        "dante_far_equalizer_off":  {"description": "Disable far end equalizer",   "params": []},
        "dante_far_delay": {
            "description": "Set far end delay",
            "params": [{"name": "delay", "type": "int", "min": 0, "max": 100}],
        },
        # Dante local
        "dante_local_gain": {
            "description": "Set local Dante output gain",
            "params": [{"name": "gain", "type": "int", "min": -18, "max": 18}],
        },
        "dante_local_noisegate_on":   {"description": "Enable local noise gate",   "params": []},
        "dante_local_noisegate_off":  {"description": "Disable local noise gate",  "params": []},
        "dante_local_equalizer_on":   {"description": "Enable local equalizer",    "params": []},
        "dante_local_equalizer_off":  {"description": "Disable local equalizer",   "params": []},
        "dante_local_voicelift_on":   {"description": "Enable local voice lift",   "params": []},
        "dante_local_voicelift_off":  {"description": "Disable local voice lift",  "params": []},
        "dante_local_delay": {
            "description": "Set local delay",
            "params": [{"name": "delay", "type": "int", "min": 0, "max": 100}],
        },
        # Sound profile
        "sound_profile_auto":   {"description": "Set sound profile to Automatic Gain", "params": []},
        "sound_profile_custom": {"description": "Set sound profile to Custom",         "params": []},
        "sound_profile_off":    {"description": "Deactivate sound profile",            "params": []},
        "sound_level": {
            "description": "Set sound level",
            "params": [{"name": "level", "type": "int", "min": 0, "max": 100}],
        },
        "sound_gain": {
            "description": "Set sound gain",
            "params": [{"name": "gain", "type": "int", "min": -18, "max": 18}],
        },
        # ── Priority zones ──────────────────────────────────────────
        "enable_priority_zone": {
            "description": "Enable or disable a priority zone",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "enable",  "type": "bool"},
            ],
        },
        "set_priority_zone": {
            "description": "Set all fields of a priority zone",
            "params": [
                {"name": "zone_id",       "type": "int"},
                {"name": "enabled",       "type": "bool"},
                {"name": "weight",        "type": "float"},
                {"name": "elevation_min", "type": "int"},
                {"name": "elevation_max", "type": "int"},
                {"name": "azimuth_min",   "type": "int"},
                {"name": "azimuth_max",   "type": "int"},
            ],
        },
        "set_priority_weight": {
            "description": "Set priority zone weight only",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "weight",  "type": "float"},
            ],
        },
        # ── Exclusion zones ─────────────────────────────────────────
        "enable_exclusion_zone": {
            "description": "Enable or disable an exclusion zone",
            "params": [
                {"name": "zone_id", "type": "int"},
                {"name": "enable",  "type": "bool"},
            ],
        },
        "set_exclusion_zone": {
            "description": "Set all fields of an exclusion zone",
            "params": [
                {"name": "zone_id",       "type": "int"},
                {"name": "enabled",       "type": "bool"},
                {"name": "elevation_min", "type": "int"},
                {"name": "elevation_max", "type": "int"},
                {"name": "azimuth_min",   "type": "int"},
                {"name": "azimuth_max",   "type": "int"},
            ],
        },
    }

    QUERY_COMMANDS = {
        "device_info":    "get_device_identity",
        "status":         "get_device_state",
        "mute":           "get_global_mute",
        "mic_level":      "get_microphone_level",
        "beam_direction": "get_beam_direction",
        "beam_settings":  "get_beam_settings",
        "voice_lift":     "get_voice_lift",
        "led_ring":       "get_led_ring",
        "site_info":      "get_device_site",
        "analog_output":  "get_analog_output",
        "firmware":       "get_firmware_update_state",
        "room_in_use":    "get_room_in_use",
        "dante_far_end":  "get_dante_far_end",
        "dante_local":    "get_dante_local",
        "sound_profile":  "get_sound_profile",
        "priority_zones": "get_priority_zones",
        "exclusion_zones":"get_exclusion_zones",
    }

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.username   = self.config.get("username", "")
        self.password   = self.config.get("password", "")
        self.auth_header = None
        self.ssl_context = None
        self._setup_connection()

    def _setup_connection(self):
        if self.username and self.password:
            auth_string  = f"{self.username}:{self.password}"
            self.auth_header = base64.b64encode(auth_string.encode()).decode("ascii")
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode    = ssl.CERT_NONE

    def _make_request(self, method: str, url: str, data: Optional[Dict] = None) -> Any:
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
                raise Exception("Forbidden - Check 3rd party access settings in Control Cockpit")
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
                "make": "Sennheiser", "device_type": "TCC M",
                "current_status": "Offline",
                "error": "Missing credentials: username and password are required.",
            }

        base_url = self._get_base_url(ip)
        try:
            identity      = self._make_request("GET", f"{base_url}/device/identity")
            state         = self._make_request("GET", f"{base_url}/device/state")
            firmware      = self._make_request("GET", f"{base_url}/firmware/update/state")
            mute          = self._make_request("GET", f"{base_url}/audio/outputs/global/mute")
            mic_level     = self._make_request("GET", f"{base_url}/audio/inputs/microphone/level")
            beam_dir      = self._make_request("GET", f"{base_url}/audio/inputs/microphone/beam/direction")
            beam_settings = self._make_request("GET", f"{base_url}/audio/inputs/microphone/beam")
            led           = self._make_request("GET", f"{base_url}/device/leds/ring")
            site          = self._make_request("GET", f"{base_url}/device/site")
            voice         = self._make_request("GET", f"{base_url}/audio/voiceLift")
            analog        = self._make_request("GET", f"{base_url}/audio/outputs/analog")
            room_in_use   = self._make_request("GET", f"{base_url}/audio/roomInUse")
            dante_far     = self._make_request("GET", f"{base_url}/audio/outputs/dante/farEnd")
            dante_local   = self._make_request("GET", f"{base_url}/audio/outputs/dante/local")
            sound_profile = self._make_request("GET", f"{base_url}/audio/soundProfile")

            # ── priority zones (list) ──
            pz_raw = self._make_request("GET", f"{base_url}/audio/inputs/microphone/priorityZones")
            priority_zones = pz_raw if isinstance(pz_raw, list) else []

            # ── exclusion zones (list) ──
            ez_raw = self._make_request("GET", f"{base_url}/audio/inputs/microphone/exclusionZones")
            exclusion_zones = ez_raw if isinstance(ez_raw, list) else []

            return {
                "ip_address": ip, "port": port, "display_id": display_id,
                "make": "Sennheiser", "device_type": "TCC M",
                "device_name":        identity.get("product", "Sennheiser TCC M"),
                "model":              identity.get("product", "TCC M"),
                "serial_number":      identity.get("serial"),
                "firmware":           firmware.get("deviceVersion"),
                "dante_version":      firmware.get("danteVersion"),
                "hardware_revision":  identity.get("hardwareRevision"),
                "current_status":     state.get("state", "Unknown"),
                "warnings":           state.get("warnings", []),
                "mute_enabled":       mute.get("enabled", False),
                "microphone_level":   mic_level.get("peak", 0),
                "beam_azimuth":       beam_dir.get("azimuth", 0),
                "beam_elevation":     beam_dir.get("elevation", 0),
                "beam_freeze_active": beam_dir.get("beamFreezeActive", False),
                "beam_installation_type":   beam_settings.get("installationType", "Unknown"),
                "beam_source_detection":    beam_settings.get("sourceDetectionThreshold", "Unknown"),
                "beam_offset":              beam_settings.get("offset", 0),
                "led_brightness":     led.get("brightness", 0),
                "mic_on_color":       led.get("micOn",   {}).get("color", "Green"),
                "mic_mute_color":     led.get("micMute", {}).get("color", "Red"),
                "site_name":          site.get("deviceName", "Unknown"),
                "site_location":      site.get("location", "Unknown"),
                "site_position":      site.get("position", "Unknown"),
                "voice_lift_threshold": voice.get("emergencyMuteThreshold", -20),
                "voice_lift_timeout":   voice.get("emergencyMuteTime", 3),
                "analog_gain":        analog.get("gain", 0),
                "analog_mute":        analog.get("mute", False),
                "room_in_use":        room_in_use.get("active", False),
                "dante_far_gain":          dante_far.get("gain", 0),
                "dante_far_noise_gate":    dante_far.get("noiseGateEnabled", False),
                "dante_far_equalizer":     dante_far.get("equalizerEnabled", False),
                "dante_far_delay":         dante_far.get("delay", 0),
                "dante_local_gain":        dante_local.get("gain", 0),
                "dante_local_noise_gate":  dante_local.get("noiseGateEnabled", False),
                "dante_local_equalizer":   dante_local.get("equalizerEnabled", False),
                "dante_local_voice_lift":  dante_local.get("voiceLiftEnabled", False),
                "dante_local_delay":       dante_local.get("delay", 0),
                "sound_profile":      sound_profile.get("profile", "Deactivated"),
                "sound_level":        sound_profile.get("level", 60),
                "sound_gain":         sound_profile.get("gain", 0),
                # ── zones ──────────────────────────────────────────────────
                "priority_zones":  priority_zones,
                "exclusion_zones": exclusion_zones,
            }

        except Exception as e:
            return {
                "ip_address": ip, "port": port, "display_id": display_id,
                "make": "Sennheiser", "device_type": "TCC M",
                "current_status": "Offline", "error": str(e),
            }

    # ── query_status (called by the backend route every poll) ─────────────
    def query_status(self, ip: str, port: int = 443, display_id: str = None) -> dict:
        info = self.get_device_info(ip, port, display_id)
        reachable = info.get("current_status") in ("Normal", "Online", "Ready", True)

        return {
            "reachable":       reachable,
            "power":           "ON" if reachable else "OFF",
            "device_name":     info.get("device_name"),
            "model":           info.get("model"),
            "serial_number":   info.get("serial_number"),
            "firmware":        info.get("firmware"),
            "dante_version":   info.get("dante_version"),
            "mute_status":     info.get("mute_enabled"),
            "mute":            "ON" if info.get("mute_enabled") else "OFF",
            "microphone_level":    info.get("microphone_level"),
            "beam_azimuth":        info.get("beam_azimuth"),
            "beam_elevation":      info.get("beam_elevation"),
            "beam_freeze_active":  info.get("beam_freeze_active"),
            "beam_installation_type": info.get("beam_installation_type"),
            "beam_source_detection":  info.get("beam_source_detection"),
            "beam_offset":         info.get("beam_offset"),
            "led_brightness":      info.get("led_brightness"),
            "mic_on_color":        info.get("mic_on_color"),
            "mic_mute_color":      info.get("mic_mute_color"),
            "voice_lift_threshold":info.get("voice_lift_threshold"),
            "voice_lift_timeout":  info.get("voice_lift_timeout"),
            "analog_gain":         info.get("analog_gain"),
            "analog_mute":         info.get("analog_mute"),
            "room_in_use":         info.get("room_in_use", False),
            "dante_far_gain":      info.get("dante_far_gain"),
            "dante_far_noise_gate":info.get("dante_far_noise_gate"),
            "dante_far_equalizer": info.get("dante_far_equalizer"),
            "dante_far_delay":     info.get("dante_far_delay"),
            "dante_local_gain":    info.get("dante_local_gain"),
            "dante_local_noise_gate": info.get("dante_local_noise_gate"),
            "dante_local_equalizer":  info.get("dante_local_equalizer"),
            "dante_local_voice_lift": info.get("dante_local_voice_lift"),
            "dante_local_delay":   info.get("dante_local_delay"),
            "sound_profile":       info.get("sound_profile"),
            "sound_level":         info.get("sound_level"),
            "sound_gain":          info.get("sound_gain"),
            # ── zones ── these were missing before ─────────────────────────
            "priority_zones":  info.get("priority_zones", []),
            "exclusion_zones": info.get("exclusion_zones", []),
            "error":           info.get("error"),
        }

    # ── low-level zone helpers ─────────────────────────────────────────────
    def get_priority_zones(self, ip: str = None, base_url: str = None) -> List[Dict]:
        if base_url is None and ip:
            base_url = self._get_base_url(ip)
        result = self._make_request("GET", f"{base_url}/audio/inputs/microphone/priorityZones")
        return result if isinstance(result, list) else []

    def get_priority_zone(self, ip: str, zone_id: int) -> Dict:
        base_url = self._get_base_url(ip)
        return self._make_request("GET", f"{base_url}/audio/inputs/microphone/priorityZones/{zone_id}")

    def set_priority_zone(self, ip: str, zone_id: int, enabled: bool = None, weight: float = None,
                          elevation_min: int = None, elevation_max: int = None,
                          azimuth_min: int = None, azimuth_max: int = None) -> Dict:
        base_url = self._get_base_url(ip)
        current  = self.get_priority_zone(ip, zone_id)
        if "error" in current:
            raise Exception(f"Failed to read priority zone {zone_id}: {current}")
        data = {
            "enabled": enabled       if enabled       is not None else current.get("enabled", False),
            "weight":  weight        if weight         is not None else current.get("weight",  1.0),
            "elevation": {
                "min": elevation_min if elevation_min is not None else current.get("elevation", {}).get("min", 0),
                "max": elevation_max if elevation_max is not None else current.get("elevation", {}).get("max", 90),
            },
            "azimuth": {
                "min": azimuth_min   if azimuth_min   is not None else current.get("azimuth", {}).get("min", 0),
                "max": azimuth_max   if azimuth_max   is not None else current.get("azimuth", {}).get("max", 360),
            },
        }
        return self._make_request("PUT", f"{base_url}/audio/inputs/microphone/priorityZones/{zone_id}", data=data)

    def get_exclusion_zones(self, ip: str = None, base_url: str = None) -> List[Dict]:
        if base_url is None and ip:
            base_url = self._get_base_url(ip)
        result = self._make_request("GET", f"{base_url}/audio/inputs/microphone/exclusionZones")
        return result if isinstance(result, list) else []

    def get_exclusion_zone(self, ip: str, zone_id: int) -> Dict:
        base_url = self._get_base_url(ip)
        return self._make_request("GET", f"{base_url}/audio/inputs/microphone/exclusionZones/{zone_id}")

    def set_exclusion_zone(self, ip: str, zone_id: int, enabled: bool = None,
                           elevation_min: int = None, elevation_max: int = None,
                           azimuth_min: int = None, azimuth_max: int = None) -> Dict:
        base_url = self._get_base_url(ip)
        current  = self.get_exclusion_zone(ip, zone_id)
        if "error" in current:
            raise Exception(f"Failed to read exclusion zone {zone_id}: {current}")
        data = {
            "enabled": enabled       if enabled       is not None else current.get("enabled", False),
            "elevation": {
                "min": elevation_min if elevation_min is not None else current.get("elevation", {}).get("min", 0),
                "max": elevation_max if elevation_max is not None else current.get("elevation", {}).get("max", 10),
            },
            "azimuth": {
                "min": azimuth_min   if azimuth_min   is not None else current.get("azimuth", {}).get("min", 0),
                "max": azimuth_max   if azimuth_max   is not None else current.get("azimuth", {}).get("max", 360),
            },
        }
        return self._make_request("PUT", f"{base_url}/audio/inputs/microphone/exclusionZones/{zone_id}", data=data)

    # ── Dante helpers ──────────────────────────────────────────────────────
    def get_dante_far_end(self, ip: str = None, base_url: str = None) -> Dict:
        if base_url is None and ip:
            base_url = self._get_base_url(ip)
        return self._make_request("GET", f"{base_url}/audio/outputs/dante/farEnd")

    def set_dante_far_end(self, ip: str, gain: int = None, noise_gate_enabled: bool = None,
                          equalizer_enabled: bool = None, delay: int = None) -> Dict:
        base_url = self._get_base_url(ip)
        current  = self.get_dante_far_end(base_url=base_url)
        if "error" in current:
            raise Exception(f"Failed to read far end settings: {current}")
        data = {
            "gain":             gain               if gain               is not None else current.get("gain", 0),
            "noiseGateEnabled": noise_gate_enabled if noise_gate_enabled is not None else current.get("noiseGateEnabled", False),
            "equalizerEnabled": equalizer_enabled  if equalizer_enabled  is not None else current.get("equalizerEnabled", False),
            "delay":            delay              if delay              is not None else current.get("delay", 0),
        }
        return self._make_request("PUT", f"{base_url}/audio/outputs/dante/farEnd", data=data)

    def get_dante_local(self, ip: str = None, base_url: str = None) -> Dict:
        if base_url is None and ip:
            base_url = self._get_base_url(ip)
        return self._make_request("GET", f"{base_url}/audio/outputs/dante/local")

    def set_dante_local(self, ip: str, gain: int = None, noise_gate_enabled: bool = None,
                        equalizer_enabled: bool = None, voice_lift_enabled: bool = None,
                        delay: int = None) -> Dict:
        base_url = self._get_base_url(ip)
        current  = self.get_dante_local(base_url=base_url)
        if "error" in current:
            raise Exception(f"Failed to read local dante settings: {current}")
        data = {
            "gain":             gain               if gain               is not None else current.get("gain", 0),
            "noiseGateEnabled": noise_gate_enabled if noise_gate_enabled is not None else current.get("noiseGateEnabled", False),
            "equalizerEnabled": equalizer_enabled  if equalizer_enabled  is not None else current.get("equalizerEnabled", False),
            "voiceLiftEnabled": voice_lift_enabled if voice_lift_enabled is not None else current.get("voiceLiftEnabled", False),
            "delay":            delay              if delay              is not None else current.get("delay", 0),
        }
        return self._make_request("PUT", f"{base_url}/audio/outputs/dante/local", data=data)

    def get_sound_profile(self, ip: str = None, base_url: str = None) -> Dict:
        if base_url is None and ip:
            base_url = self._get_base_url(ip)
        return self._make_request("GET", f"{base_url}/audio/soundProfile")

    def set_sound_profile(self, ip: str, profile: str = None, level: int = None, gain: int = None) -> Dict:
        base_url = self._get_base_url(ip)
        current  = self.get_sound_profile(base_url=base_url)
        if "error" in current:
            raise Exception(f"Failed to read sound profile: {current}")
        data = {
            "profile": profile if profile is not None else current.get("profile", "Deactivated"),
            "level":   level   if level   is not None else current.get("level",   60),
            "gain":    gain    if gain    is not None else current.get("gain",     0),
        }
        return self._make_request("PUT", f"{base_url}/audio/soundProfile", data=data)

    # ── send_command ───────────────────────────────────────────────────────
    def send_command(self, ip: str, port: int, display_id: str, command: str, params: dict = None) -> tuple:
        if not self.username or not self.password:
            return False, "Missing credentials: username and password are required."

        base_url = self._get_base_url(ip)
        params   = params or {}

        try:
            # ── basic mic ──────────────────────────────────────────────────
            if command == "mute":
                self._make_request("PUT", f"{base_url}/audio/outputs/global/mute", data={"enabled": True})
                return True, "Microphone muted successfully"

            elif command == "unmute":
                self._make_request("PUT", f"{base_url}/audio/outputs/global/mute", data={"enabled": False})
                return True, "Microphone unmuted successfully"

            elif command == "identify":
                self._make_request("PUT", f"{base_url}/device/identification", data={"visual": True})
                threading.Timer(10.0, lambda: self._stop_identification(base_url)).start()
                return True, "Device identification started - LEDs will blink for 10 seconds"

            # ── LED ────────────────────────────────────────────────────────
            elif command == "set_led_brightness":
                brightness = params.get("brightness", 5)
                if not 0 <= brightness <= 5:
                    return False, "Brightness must be between 0 and 5"
                url     = f"{base_url}/device/leds/ring"
                current = self._make_request("GET", url)
                data    = {
                    "brightness":        brightness,
                    "showFarendActivity": current.get("showFarendActivity", False),
                    "micOn":    current.get("micOn",    {"color": "Green"}),
                    "micMute":  current.get("micMute",  {"color": "Red"}),
                    "micCustom":current.get("micCustom",{"enabled": False, "color": "Green"}),
                }
                self._make_request("PUT", url, data=data)
                return True, f"LED brightness set to {brightness}"

            elif command == "set_mic_on_color":
                color   = params.get("color", "Green")
                url     = f"{base_url}/device/leds/ring"
                current = self._make_request("GET", url)
                data    = {
                    "brightness":         current.get("brightness", 50),
                    "showFarendActivity": current.get("showFarendActivity", False),
                    "micOn":    {"color": color},
                    "micMute":  current.get("micMute",  {"color": "Red"}),
                    "micCustom":current.get("micCustom",{"enabled": False, "color": "Green"}),
                }
                self._make_request("PUT", url, data=data)
                return True, f"Mic ON color set to {color}"

            elif command == "set_mic_mute_color":
                color   = params.get("color", "Red")
                url     = f"{base_url}/device/leds/ring"
                current = self._make_request("GET", url)
                data    = {
                    "brightness":         current.get("brightness", 50),
                    "showFarendActivity": current.get("showFarendActivity", False),
                    "micOn":    current.get("micOn",   {"color": "Green"}),
                    "micMute":  {"color": color},
                    "micCustom":current.get("micCustom",{"enabled": False, "color": "Green"}),
                }
                self._make_request("PUT", url, data=data)
                return True, f"Mic MUTE color set to {color}"

            # ── voice lift ────────────────────────────────────────────────
            elif command == "set_voice_lift":
                threshold = params.get("threshold", -20)
                timeout   = params.get("timeout", 3)
                if not -30 <= threshold <= 0:
                    return False, "Threshold must be between -30 and 0 dB"
                if not 1 <= timeout <= 10:
                    return False, "Timeout must be between 1 and 10 seconds"
                self._make_request("PUT", f"{base_url}/audio/voiceLift",
                                   data={"emergencyMuteThreshold": threshold, "emergencyMuteTime": timeout})
                return True, f"Voice lift set: threshold={threshold}dB, timeout={timeout}s"

            # ── beam ──────────────────────────────────────────────────────
            elif command == "set_beam_type":
                beam_type = params.get("type", "SurfaceMounted")
                if beam_type not in ["FlushMounted", "SurfaceMounted", "Suspended"]:
                    return False, f"Invalid type: {beam_type}"
                url     = f"{base_url}/audio/inputs/microphone/beam"
                current = self._make_request("GET", url)
                self._make_request("PUT", url, data={
                    "installationType":          beam_type,
                    "sourceDetectionThreshold":  current.get("sourceDetectionThreshold", "NormalRoom"),
                    "offset":                    current.get("offset", 0),
                })
                return True, f"Installation type set to {beam_type}"

            elif command == "set_beam_threshold":
                threshold = params.get("threshold", "NormalRoom")
                if threshold not in ["QuietRoom", "NormalRoom", "NoisyRoom"]:
                    return False, f"Invalid threshold: {threshold}"
                url     = f"{base_url}/audio/inputs/microphone/beam"
                current = self._make_request("GET", url)
                self._make_request("PUT", url, data={
                    "installationType":         current.get("installationType", "SurfaceMounted"),
                    "sourceDetectionThreshold": threshold,
                    "offset":                   current.get("offset", 0),
                })
                return True, f"Source detection set to {threshold}"

            elif command == "set_beam_offset":
                offset = params.get("offset", 0)
                if offset % 30 != 0 or not 0 <= offset <= 330:
                    return False, "Offset must be a multiple of 30 between 0 and 330"
                url     = f"{base_url}/audio/inputs/microphone/beam"
                current = self._make_request("GET", url)
                self._make_request("PUT", url, data={
                    "installationType":         current.get("installationType", "SurfaceMounted"),
                    "sourceDetectionThreshold": current.get("sourceDetectionThreshold", "NormalRoom"),
                    "offset":                   offset,
                })
                return True, f"Beam offset set to {offset}°"

            # ── analog ───────────────────────────────────────────────────
            elif command == "analog_mute_on":
                url     = f"{base_url}/audio/outputs/analog"
                current = self._make_request("GET", url)
                self._make_request("PUT", url, data={"gain": current.get("gain", 0), "mute": True})
                return True, "Analog output muted"

            elif command == "analog_mute_off":
                url     = f"{base_url}/audio/outputs/analog"
                current = self._make_request("GET", url)
                self._make_request("PUT", url, data={"gain": current.get("gain", 0), "mute": False})
                return True, "Analog output unmuted"

            elif command == "set_analog_gain":
                gain = params.get("gain", 0)
                if not -18 <= gain <= 18:
                    return False, "Gain must be between -18 and 18 dB"
                url     = f"{base_url}/audio/outputs/analog"
                current = self._make_request("GET", url)
                self._make_request("PUT", url, data={"gain": gain, "mute": current.get("mute", False)})
                return True, f"Analog gain set to {gain} dB"

            # ── Dante far end ─────────────────────────────────────────────
            elif command == "dante_far_gain":
                gain = params.get("gain", 0)
                if not -18 <= gain <= 18:
                    return False, "Gain must be between -18 and 18 dB"
                self.set_dante_far_end(ip, gain=gain)
                return True, f"Far end gain set to {gain} dB"

            elif command == "dante_far_noisegate_on":
                self.set_dante_far_end(ip, noise_gate_enabled=True)
                return True, "Far end noise gate ENABLED"

            elif command == "dante_far_noisegate_off":
                self.set_dante_far_end(ip, noise_gate_enabled=False)
                return True, "Far end noise gate DISABLED"

            elif command == "dante_far_equalizer_on":
                self.set_dante_far_end(ip, equalizer_enabled=True)
                return True, "Far end equalizer ENABLED"

            elif command == "dante_far_equalizer_off":
                self.set_dante_far_end(ip, equalizer_enabled=False)
                return True, "Far end equalizer DISABLED"

            elif command == "dante_far_delay":
                delay = params.get("delay", 0)
                if not 0 <= delay <= 100:
                    return False, "Delay must be between 0 and 100 ms"
                self.set_dante_far_end(ip, delay=delay)
                return True, f"Far end delay set to {delay} ms"

            # ── Dante local ───────────────────────────────────────────────
            elif command == "dante_local_gain":
                gain = params.get("gain", 0)
                if not -18 <= gain <= 18:
                    return False, "Gain must be between -18 and 18 dB"
                self.set_dante_local(ip, gain=gain)
                return True, f"Local gain set to {gain} dB"

            elif command == "dante_local_noisegate_on":
                self.set_dante_local(ip, noise_gate_enabled=True)
                return True, "Local noise gate ENABLED"

            elif command == "dante_local_noisegate_off":
                self.set_dante_local(ip, noise_gate_enabled=False)
                return True, "Local noise gate DISABLED"

            elif command == "dante_local_equalizer_on":
                self.set_dante_local(ip, equalizer_enabled=True)
                return True, "Local equalizer ENABLED"

            elif command == "dante_local_equalizer_off":
                self.set_dante_local(ip, equalizer_enabled=False)
                return True, "Local equalizer DISABLED"

            elif command == "dante_local_voicelift_on":
                self.set_dante_local(ip, voice_lift_enabled=True)
                return True, "Local voice lift ENABLED"

            elif command == "dante_local_voicelift_off":
                self.set_dante_local(ip, voice_lift_enabled=False)
                return True, "Local voice lift DISABLED"

            elif command == "dante_local_delay":
                delay = params.get("delay", 0)
                if not 0 <= delay <= 100:
                    return False, "Delay must be between 0 and 100 ms"
                self.set_dante_local(ip, delay=delay)
                return True, f"Local delay set to {delay} ms"

            # ── sound profile ─────────────────────────────────────────────
            elif command == "sound_profile_auto":
                self.set_sound_profile(ip, profile="AutomaticGain")
                return True, "Sound profile set to Automatic Gain"

            elif command == "sound_profile_custom":
                self.set_sound_profile(ip, profile="Custom")
                return True, "Sound profile set to Custom"

            elif command == "sound_profile_off":
                self.set_sound_profile(ip, profile="Deactivated")
                return True, "Sound profile DEACTIVATED"

            elif command == "sound_level":
                level = params.get("level", 60)
                if not 0 <= level <= 100:
                    return False, "Level must be between 0 and 100"
                self.set_sound_profile(ip, level=level)
                return True, f"Sound level set to {level}"

            elif command == "sound_gain":
                gain = params.get("gain", 0)
                if not -18 <= gain <= 18:
                    return False, "Gain must be between -18 and 18 dB"
                self.set_sound_profile(ip, gain=gain)
                return True, f"Sound gain set to {gain} dB"

            # ── priority zones ────────────────────────────────────────────
            elif command == "enable_priority_zone":
                zone_id = params.get("zone_id")
                enable  = params.get("enable")
                if zone_id is None or enable is None:
                    return False, "zone_id and enable are required"
                self.set_priority_zone(ip, int(zone_id), enabled=bool(enable))
                return True, f"Priority zone {zone_id} {'enabled' if enable else 'disabled'}"

            elif command == "set_priority_zone":
                zone_id = params.get("zone_id")
                if zone_id is None:
                    return False, "zone_id is required"
                self.set_priority_zone(
                    ip, int(zone_id),
                    enabled       = params.get("enabled"),
                    weight        = params.get("weight"),
                    elevation_min = params.get("elevation_min"),
                    elevation_max = params.get("elevation_max"),
                    azimuth_min   = params.get("azimuth_min"),
                    azimuth_max   = params.get("azimuth_max"),
                )
                return True, f"Priority zone {zone_id} updated"

            elif command == "set_priority_weight":
                zone_id = params.get("zone_id")
                weight  = params.get("weight")
                if zone_id is None or weight is None:
                    return False, "zone_id and weight are required"
                self.set_priority_zone(ip, int(zone_id), weight=float(weight))
                return True, f"Priority zone {zone_id} weight set to {weight}"

            # ── exclusion zones ───────────────────────────────────────────
            elif command == "enable_exclusion_zone":
                zone_id = params.get("zone_id")
                enable  = params.get("enable")
                if zone_id is None or enable is None:
                    return False, "zone_id and enable are required"
                self.set_exclusion_zone(ip, int(zone_id), enabled=bool(enable))
                return True, f"Exclusion zone {zone_id} {'enabled' if enable else 'disabled'}"

            elif command == "set_exclusion_zone":
                zone_id = params.get("zone_id")
                if zone_id is None:
                    return False, "zone_id is required"
                self.set_exclusion_zone(
                    ip, int(zone_id),
                    enabled       = params.get("enabled"),
                    elevation_min = params.get("elevation_min"),
                    elevation_max = params.get("elevation_max"),
                    azimuth_min   = params.get("azimuth_min"),
                    azimuth_max   = params.get("azimuth_max"),
                )
                return True, f"Exclusion zone {zone_id} updated"

            else:
                return False, f"Unknown command: {command}"

        except Exception as e:
            return False, str(e)

    def _stop_identification(self, base_url: str):
        try:
            self._make_request("PUT", f"{base_url}/device/identification", data={"visual": False})
        except Exception:
            pass

    def get_firmware_info(self, ip: str, port: int = 443) -> dict:
        base_url = self._get_base_url(ip)
        try:
            firmware = self._make_request("GET", f"{base_url}/firmware/update/state")
            return {
                "device_version":     firmware.get("deviceVersion"),
                "dante_version":      firmware.get("danteVersion"),
                "update_state":       firmware.get("state", "Idle"),
                "update_progress":    firmware.get("progress", 0),
                "last_update_status": firmware.get("lastStatus", "None"),
            }
        except Exception as e:
            return {"error": str(e)}
