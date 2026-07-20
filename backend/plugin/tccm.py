# #!/usr/bin/env python3
# """
# Sennheiser TC Bar M Device Control Plugin - Complete API Integration
# Based on SSC v2 API (Schema 1.0, Protocol 2.3)
# """

# import urllib.request
# import urllib.error
# import ssl
# import json
# import base64
# import time
# import threading
# import getpass
# import sys
# from typing import Optional, Dict, Any, List, Callable, Union
# from datetime import datetime
# from dataclasses import dataclass, field
# from enum import Enum

# # ========== Enums ==========

# class NoiseSuppressionWeighting(Enum):
#     """Noise suppression weighting options"""
#     OFF = "Off"
#     LOW = "Low"
#     MEDIUM = "Medium"
#     HIGH = "High"

# class FadeBehavior(Enum):
#     """Fade behavior for mic mixer"""
#     OFF = "Off"
#     FAST = "Fast"
#     MEDIUM = "Medium"
#     SLOW = "Slow"

# class SoundProfilePreset(Enum):
#     """Sound profile presets"""
#     WALLMOUNT = "Wallmount"
#     CEILING_MOUNT = "CeilingMount"
#     CUSTOM = "Custom"

# class IPMode(Enum):
#     """IP configuration modes"""
#     AUTO = "Auto"
#     MANUAL = "Manual"

# class StandbyMode(Enum):
#     """Standby/energy saving modes"""
#     OFF = "Off"
#     ECO_MODE = "EcoMode"
#     DEEP_SLEEP = "DeepSleep"

# class DeviceProfile(Enum):
#     """Device profiles"""
#     CUSTOM = "Custom"
#     MICROSOFT_TEAMS = "MicrosoftTeams"

# class AntiFlickerFrequency(Enum):
#     """Anti-flicker frequency options"""
#     AUTO = "Auto"
#     _50HZ = "50Hz"
#     _60HZ = "60Hz"

# class ZoomSpeed(Enum):
#     """Zoom speed options"""
#     SLOW = "Slow"
#     MEDIUM = "Medium"
#     FAST = "Fast"

# class PanTiltSpeed(Enum):
#     """Pan/Tilt speed options"""
#     SLOW = "Slow"
#     MEDIUM = "Medium"
#     FAST = "Fast"

# class ZoneGain(Enum):
#     """Zone gain options"""
#     OFF = "Off"
#     LOW = "Low"
#     MEDIUM = "Medium"
#     HIGH = "High"

# # ========== Data Classes ==========

# @dataclass
# class DeviceState:
#     """Device state information"""
#     state: str  # Normal, Warning, Error
#     warnings: List[str] = field(default_factory=list)
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DeviceIdentity:
#     """Device identity information"""
#     product: str
#     hardware_revision: str
#     serial: str
#     vendor: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DeviceSiteInfo:
#     """Device site information"""
#     device_name: str
#     dante_name: str
#     location: str
#     position: str
#     language: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class FirmwareUpdateState:
#     """Firmware update state"""
#     device_version: str
#     state: str  # Idle, Downloading, Updating, Rebooting, Error
#     progress: int
#     last_status: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class LEDRingSettings:
#     """LED ring settings"""
#     brightness: int  # 0-5
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class SoundPromptsSettings:
#     """Sound prompts settings"""
#     sound_prompts: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class InternalMicSettings:
#     """Internal microphone settings"""
#     gain: int  # -30 to 30 dB
#     enabled: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class MuteSettings:
#     """Mute settings"""
#     enabled: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class NoiseGateSettings:
#     """Noise gate settings for internal mic"""
#     enabled: bool
#     threshold: int  # -80 to -20 dB
#     hold_time: int  # 100-2000 ms
#     range: int  # -80 to 0 dB
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class SpeakerOutputSettings:
#     """Speaker output settings"""
#     volume: int  # 0-100
#     level_limiter: int  # 0-100
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class SoundProfileSettings:
#     """Sound profile settings"""
#     preset: str  # Wallmount, CeilingMount, Custom
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class PriorityZoneSettings:
#     """Priority zone settings"""
#     id: int
#     active: bool
#     enabled: bool
#     gain: str  # Off, Low, Medium, High
#     left: int  # 0-100
#     right: int  # 0-100
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class ExclusionZoneSettings:
#     """Exclusion zone settings"""
#     id: int
#     active: bool
#     enabled: bool
#     left: int  # 0-100
#     right: int  # 0-100
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class BeamPosition:
#     """Beam position"""
#     position: int  # 0-180 degrees
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DeviceMetrics:
#     """Real-time device metrics"""
#     timestamp: datetime
#     microphone_level: int  # peak level
#     mute_status: Optional[bool]
#     beam_position: int
#     active_channel: str
#     speaker_volume: int
#     usb_input_level: int
#     bluetooth_input_level: int

# @dataclass
# class CameraVideoParameters:
#     """Camera video parameters"""
#     compensation: str  # Backlight, WDR, etc.
#     anti_flicker_frequency: str  # Auto, 50Hz, 60Hz
#     brightness: int  # -20 to 20
#     contrast: int  # 0-10
#     saturation: int  # 0-10
#     sharpness: int  # 0-4
#     auto_whitebalance_enabled: bool
#     whitebalance: int  # 2000-10000
#     default_camera_mode: str  # ResumeLastView, FullFieldOfView
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class CameraMovementSettings:
#     """Camera movement settings"""
#     pan_position: int  # 0-360
#     tilt_position: int  # -25-25
#     zoom_position: int  # 0-100
#     zoom_speed: str  # Slow, Medium, Fast
#     pan_tilt_speed: str  # Slow, Medium, Fast
#     auto_framing_speed: str  # Slow, Medium, Fast
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class CameraAIAccess:
#     """Camera AI access settings"""
#     auto_framing_access_enabled: bool
#     auto_framing_enabled: bool
#     person_tiling_access_enabled: bool
#     person_tiling_enabled: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class NetworkInterface:
#     """Network interface settings"""
#     name: str
#     type: str
#     mac: str
#     functionalities: List[str]
#     auto_discovery: bool
#     ip_mode: str
#     ipv4: Dict[str, Any]
#     ipv6: Dict[str, Any]
#     vlan_tag: Optional[int]
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DanteSettings:
#     """Dante settings"""
#     enabled: bool
#     continuous_dante_stream: bool = False
#     dante_speaker_output: bool = False
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class BluetoothSettings:
#     """Bluetooth settings"""
#     enabled: bool
#     pairing: bool
#     mac: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class WifiStatus:
#     """WiFi status"""
#     enabled: bool
#     state: str
#     connection: Dict[str, Any]
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class ConferenceOutputSettings:
#     """Conference output settings"""
#     far_end_gain: int  # -18 to 18 dB
#     near_end_gain: int  # -18 to 18 dB
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class PortConfiguration:
#     """Port configuration for RJ45 ports"""
#     configuration: str  # SingleDomain, DualDomain, Split
#     timestamp: datetime = field(default_factory=datetime.now)


# # ========== Main Plugin Class ==========

# class SennheiserTCBarMPlugin:
#     """Complete plugin for Sennheiser TeamConnect Bar M with all API endpoints"""
    
#     def __init__(self, device_ip: str, username: str, password: str, verify_ssl: bool = False):
#         self.device_ip = device_ip
#         self.base_url = f"https://{device_ip}/api"
#         self.username = username
#         self.password = password
        
#         # Setup authentication
#         auth_string = f"{username}:{password}"
#         auth_bytes = auth_string.encode('utf-8')
#         self.auth_header = base64.b64encode(auth_bytes).decode('ascii')
        
#         # SSL context
#         self.ssl_context = ssl.create_default_context()
#         self.ssl_context.check_hostname = False
#         self.ssl_context.verify_mode = ssl.CERT_NONE
        
#         # Monitoring state
#         self.monitoring = False
#         self.monitor_thread = None
#         self.metrics_history = []
#         self.callbacks = []
        
#         # Firmware update monitoring
#         self.firmware_monitoring = False
#         self.firmware_monitor_thread = None
    
#     def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
#         """Make HTTP request to the device"""
#         url = f"{self.base_url}{endpoint}"
        
#         headers = {
#             "Accept": "application/json",
#             "Authorization": f"Basic {self.auth_header}"
#         }
        
#         if data and method in ["PUT", "POST"]:
#             headers["Content-Type"] = "application/json"
#             request_data = json.dumps(data).encode('utf-8')
#         else:
#             request_data = None
        
#         req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
        
#         try:
#             response = urllib.request.urlopen(req, context=self.ssl_context, timeout=10)
#             response_data = response.read().decode('utf-8')
#             return json.loads(response_data) if response_data else {}
#         except urllib.error.HTTPError as e:
#             if e.code == 401:
#                 raise Exception("Authentication failed - Invalid username or password")
#             elif e.code == 403:
#                 raise Exception("Forbidden - Check 3rd party access settings")
#             error_msg = e.read().decode('utf-8') if e.fp else str(e)
#             return {"error": f"HTTP {e.code}", "message": error_msg}
#         except Exception as e:
#             return {"error": str(e)}
    
#     # ========== Validation Method ==========
    
#     def validate_connection(self) -> bool:
#         """Validate that the connection and credentials work"""
#         try:
#             result = self.get_device_identity()
#             if result and 'product' in result:
#                 return True
#             return False
#         except Exception as e:
#             print(f"Validation failed: {e}")
#             return False
    
#     # ========== Device Information Methods ==========
    
#     def get_device_state(self) -> Dict[str, Any]:
#         """GET /api/device/state - Get device state"""
#         return self._make_request("GET", "/device/state")
    
#     def get_device_state_object(self) -> DeviceState:
#         """Get device state as typed object"""
#         response = self.get_device_state()
#         return DeviceState(
#             state=response.get('state', 'Unknown'),
#             warnings=response.get('warnings', [])
#         )
    
#     def get_device_identity(self) -> Dict[str, Any]:
#         """GET /api/device/identity - Get device identity"""
#         return self._make_request("GET", "/device/identity")
    
#     def get_device_identity_object(self) -> DeviceIdentity:
#         """Get device identity as typed object"""
#         response = self.get_device_identity()
#         return DeviceIdentity(
#             product=response.get('product', 'Unknown'),
#             hardware_revision=response.get('hardwareRevision', 'Unknown'),
#             serial=response.get('serial', 'Unknown'),
#             vendor=response.get('vendor', 'Sennheiser')
#         )
    
#     def get_identification_state(self) -> Dict[str, Any]:
#         """GET /api/device/identification - Get identification state"""
#         return self._make_request("GET", "/device/identification")
    
#     def set_identification(self, visual: bool) -> Dict[str, Any]:
#         """PUT /api/device/identification - Set device identification (blink LEDs)"""
#         return self._make_request("PUT", "/device/identification", data={"visual": visual})
    
#     def identify_device(self, enable: bool = True) -> Dict[str, Any]:
#         """Convenience method to identify device by blinking LEDs"""
#         return self.set_identification(enable)
    
#     def restart_device(self) -> Dict[str, Any]:
#         """PUT /api/device/restart - Restart the device"""
#         return self._make_request("PUT", "/device/restart")
    
#     def get_allowed_standby_mode(self) -> Dict[str, Any]:
#         """GET /api/device/allowedStandbyMode - Get lowest allowed standby mode"""
#         return self._make_request("GET", "/device/allowedStandbyMode")
    
#     def set_allowed_standby_mode(self, mode: str) -> Dict[str, Any]:
#         """PUT /api/device/allowedStandbyMode - Set lowest allowed standby mode"""
#         valid_modes = ["Off", "EcoMode", "DeepSleep"]
#         if mode not in valid_modes:
#             raise Exception(f"Invalid mode. Must be one of: {valid_modes}")
#         return self._make_request("PUT", "/device/allowedStandbyMode", data={"mode": mode})
    
#     def get_user_interaction(self) -> Dict[str, Any]:
#         """GET /api/device/hasUserInteraction - Check if device has user interaction"""
#         return self._make_request("GET", "/device/hasUserInteraction")
    
#     def get_sound_prompts(self) -> Dict[str, Any]:
#         """GET /api/device/feedback - Get sound prompts settings"""
#         return self._make_request("GET", "/device/feedback")
    
#     def set_sound_prompts(self, enabled: bool) -> Dict[str, Any]:
#         """PUT /api/device/feedback - Set sound prompts settings"""
#         return self._make_request("PUT", "/device/feedback", data={"soundPrompts": enabled})
    
#     def get_device_site(self) -> Dict[str, Any]:
#         """GET /api/device/site - Get device site information"""
#         return self._make_request("GET", "/device/site")
    
#     def get_device_site_object(self) -> DeviceSiteInfo:
#         """Get device site information as typed object"""
#         response = self.get_device_site()
#         return DeviceSiteInfo(
#             device_name=response.get('deviceName', 'Unknown'),
#             dante_name=response.get('danteName', 'Unknown'),
#             location=response.get('location', 'Unknown'),
#             position=response.get('position', ''),
#             language=response.get('language', 'En_GB')
#         )
    
#     def set_device_site(self, device_name: str = None, location: str = None, 
#                         position: str = None, language: str = None) -> Dict[str, Any]:
#         """PUT /api/device/site - Set device site information"""
#         current = self.get_device_site()
#         data = {
#             "deviceName": device_name if device_name else current.get('deviceName'),
#             "danteName": current.get('danteName', current.get('deviceName')),
#             "location": location if location else current.get('location', ''),
#             "position": position if position else current.get('position', ''),
#             "language": language if language else current.get('language', 'En_GB')
#         }
#         return self._make_request("PUT", "/device/site", data=data)
    
#     def get_device_profile(self) -> Dict[str, Any]:
#         """GET /api/device/profile - Get device profile"""
#         return self._make_request("GET", "/device/profile")
    
#     def set_device_profile(self, configuration: str) -> Dict[str, Any]:
#         """PUT /api/device/profile - Set device profile (Custom, MicrosoftTeams)"""
#         valid_profiles = ["Custom", "MicrosoftTeams"]
#         if configuration not in valid_profiles:
#             raise Exception(f"Invalid profile. Must be one of: {valid_profiles}")
#         return self._make_request("PUT", "/device/profile", data={"configuration": configuration})
    
#     # ========== LED Control Methods ==========
    
#     def get_led_ring(self) -> Dict[str, Any]:
#         """GET /api/device/leds/ring - Get LED ring settings"""
#         return self._make_request("GET", "/device/leds/ring")
    
#     def get_led_ring_object(self) -> LEDRingSettings:
#         """Get LED ring settings as typed object"""
#         response = self.get_led_ring()
#         return LEDRingSettings(
#             brightness=response.get('brightness', 3)
#         )
    
#     def set_led_brightness(self, brightness: int) -> Dict[str, Any]:
#         """PUT /api/device/leds/ring - Set LED ring brightness (0-5)"""
#         if not 0 <= brightness <= 5:
#             raise Exception("Brightness must be between 0 and 5")
#         return self._make_request("PUT", "/device/leds/ring", data={"brightness": brightness})
    
#     # ========== Audio Methods ==========
    
#     def get_relative_speaker_volume(self, volume_up: int = 0, volume_down: int = 0) -> Dict[str, Any]:
#         """PUT /api/audio/outputs/speaker/relative - Adjust speaker volume relatively"""
#         if volume_up > 0 and volume_down > 0:
#             raise Exception("Cannot specify both volume_up and volume_down")
#         return self._make_request("PUT", "/audio/outputs/speaker/relative", 
#                                    data={"volumeUp": volume_up, "volumeDown": volume_down})
    
#     def volume_up(self, steps: int = 1) -> Dict[str, Any]:
#         """Increase speaker volume by steps"""
#         return self.get_relative_speaker_volume(volume_up=steps)
    
#     def volume_down(self, steps: int = 1) -> Dict[str, Any]:
#         """Decrease speaker volume by steps"""
#         return self.get_relative_speaker_volume(volume_down=steps)
    
#     def get_internal_mic(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic - Get internal mic parameters"""
#         return self._make_request("GET", "/audio/inputs/internalMic")
    
#     def get_internal_mic_object(self) -> InternalMicSettings:
#         """Get internal mic settings as typed object"""
#         response = self.get_internal_mic()
#         return InternalMicSettings(
#             gain=response.get('gain', 0),
#             enabled=response.get('enabled', True)
#         )
    
#     def set_internal_mic(self, gain: int = None, enabled: bool = None) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic - Set internal mic parameters"""
#         current = self.get_internal_mic()
#         data = {
#             "gain": gain if gain is not None else current.get('gain', 0),
#             "enabled": enabled if enabled is not None else current.get('enabled', True)
#         }
#         if data["gain"] < -30 or data["gain"] > 30:
#             raise Exception("Gain must be between -30 and 30 dB")
#         return self._make_request("PUT", "/audio/inputs/internalMic", data=data)
    
#     def get_mic_mute(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/mute - Get mute state (after mixer)"""
#         return self._make_request("GET", "/audio/inputs/mute")
    
#     def set_mic_mute(self, enabled: bool) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/mute - Set mute state (after mixer)"""
#         return self._make_request("PUT", "/audio/inputs/mute", data={"enabled": enabled})
    
#     def mute(self) -> Dict[str, Any]:
#         """Convenience method to mute microphone"""
#         return self.set_mic_mute(True)
    
#     def unmute(self) -> Dict[str, Any]:
#         """Convenience method to unmute microphone"""
#         return self.set_mic_mute(False)
    
#     def get_noise_gate(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/noiseGate - Get noise gate settings"""
#         return self._make_request("GET", "/audio/inputs/internalMic/noiseGate")
    
#     def get_noise_gate_object(self) -> NoiseGateSettings:
#         """Get noise gate settings as typed object"""
#         response = self.get_noise_gate()
#         return NoiseGateSettings(
#             enabled=response.get('enabled', False),
#             threshold=response.get('threshold', -40),
#             hold_time=response.get('holdTime', 300),
#             range=response.get('range', -40)
#         )
    
#     def set_noise_gate(self, enabled: bool = None, threshold: int = None, 
#                        hold_time: int = None, range_val: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic/noiseGate - Set noise gate settings"""
#         current = self.get_noise_gate()
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "threshold": threshold if threshold is not None else current.get('threshold', -40),
#             "holdTime": hold_time if hold_time is not None else current.get('holdTime', 300),
#             "range": range_val if range_val is not None else current.get('range', -40)
#         }
#         return self._make_request("PUT", "/audio/inputs/internalMic/noiseGate", data=data)
    
#     def get_noise_suppression(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/noiseSuppression - Get noise suppression config"""
#         return self._make_request("GET", "/audio/inputs/noiseSuppression")
    
#     def set_noise_suppression(self, weighting: str) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/noiseSuppression - Set noise suppression weighting"""
#         valid_weightings = ["Off", "Low", "Medium", "High"]
#         if weighting not in valid_weightings:
#             raise Exception(f"Invalid weighting. Must be one of: {valid_weightings}")
#         return self._make_request("PUT", "/audio/inputs/noiseSuppression", 
#                                    data={"weighting": weighting})
    
#     def get_speaker_output(self) -> Dict[str, Any]:
#         """GET /api/audio/outputs/speaker - Get speaker output parameters"""
#         return self._make_request("GET", "/audio/outputs/speaker")
    
#     def get_speaker_output_object(self) -> SpeakerOutputSettings:
#         """Get speaker output settings as typed object"""
#         response = self.get_speaker_output()
#         return SpeakerOutputSettings(
#             volume=response.get('volume', 50),
#             level_limiter=response.get('levelLimiter', 100)
#         )
    
#     def set_speaker_output(self, volume: int = None, level_limiter: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/outputs/speaker - Set speaker output parameters"""
#         current = self.get_speaker_output()
#         data = {
#             "volume": volume if volume is not None else current.get('volume', 50),
#             "levelLimiter": level_limiter if level_limiter is not None else current.get('levelLimiter', 100)
#         }
#         if data["volume"] < 0 or data["volume"] > 100:
#             raise Exception("Volume must be between 0 and 100")
#         return self._make_request("PUT", "/audio/outputs/speaker", data=data)
    
#     def set_volume(self, volume: int) -> Dict[str, Any]:
#         """Convenience method to set speaker volume"""
#         return self.set_speaker_output(volume=volume)
    
#     def get_sound_profile(self) -> Dict[str, Any]:
#         """GET /api/audio/soundProfile - Get sound profile"""
#         return self._make_request("GET", "/audio/soundProfile")
    
#     def get_sound_profile_object(self) -> SoundProfileSettings:
#         """Get sound profile as typed object"""
#         response = self.get_sound_profile()
#         return SoundProfileSettings(
#             preset=response.get('preset', 'Wallmount')
#         )
    
#     def set_sound_profile(self, preset: str) -> Dict[str, Any]:
#         """PUT /api/audio/soundProfile - Set sound profile"""
#         valid_presets = ["Wallmount", "CeilingMount", "Custom"]
#         if preset not in valid_presets:
#             raise Exception(f"Invalid preset. Must be one of: {valid_presets}")
#         return self._make_request("PUT", "/audio/soundProfile", data={"preset": preset})
    
#     # ========== Zone Methods ==========
    
#     def get_priority_zones(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/priorityZones - Get all priority zones"""
#         return self._make_request("GET", "/audio/inputs/internalMic/priorityZones")
    
#     def get_priority_zone(self, zone_id: int) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/priorityZones/{id} - Get specific priority zone"""
#         return self._make_request("GET", f"/audio/inputs/internalMic/priorityZones/{zone_id}")
    
#     def set_priority_zone(self, zone_id: int, enabled: bool = None, 
#                           gain: str = None, left: int = None, right: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic/priorityZones/{id} - Set priority zone"""
#         current = self.get_priority_zone(zone_id)
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "gain": gain if gain is not None else current.get('gain', 'Medium'),
#             "left": left if left is not None else current.get('left', 0),
#             "right": right if right is not None else current.get('right', 100)
#         }
#         return self._make_request("PUT", f"/audio/inputs/internalMic/priorityZones/{zone_id}", data=data)
    
#     def get_exclusion_zones(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/exclusionZones - Get all exclusion zones"""
#         return self._make_request("GET", "/audio/inputs/internalMic/exclusionZones")
    
#     def get_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/exclusionZones/{id} - Get specific exclusion zone"""
#         return self._make_request("GET", f"/audio/inputs/internalMic/exclusionZones/{zone_id}")
    
#     def set_exclusion_zone(self, zone_id: int, enabled: bool = None, 
#                            left: int = None, right: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic/exclusionZones/{id} - Set exclusion zone"""
#         current = self.get_exclusion_zone(zone_id)
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "left": left if left is not None else current.get('left', 0),
#             "right": right if right is not None else current.get('right', 100)
#         }
#         return self._make_request("PUT", f"/audio/inputs/internalMic/exclusionZones/{zone_id}", data=data)
    
#     # ========== Beam Methods ==========
    
#     def get_beam_position(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/beam - Get beam position"""
#         return self._make_request("GET", "/audio/inputs/internalMic/beam")
    
#     def get_beam_position_object(self) -> BeamPosition:
#         """Get beam position as typed object"""
#         response = self.get_beam_position()
#         return BeamPosition(
#             position=response.get('position', 0)
#         )
    
#     # ========== EQ Methods ==========
    
#     def get_internal_mic_custom_eq(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/customEq - Get internal mic custom EQ"""
#         return self._make_request("GET", "/audio/inputs/internalMic/customEq")
    
#     def set_internal_mic_custom_eq(self, eq_values: List[int]) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic/customEq - Set internal mic custom EQ"""
#         if len(eq_values) != 7:
#             raise Exception("EQ must have exactly 7 values (-12 to 12 dB)")
#         for val in eq_values:
#             if val < -12 or val > 12:
#                 raise Exception("EQ values must be between -12 and 12")
#         return self._make_request("PUT", "/audio/inputs/internalMic/customEq", data=eq_values)
    
#     def get_speaker_custom_eq(self) -> Dict[str, Any]:
#         """GET /api/audio/outputs/speaker/customEq - Get speaker custom EQ"""
#         return self._make_request("GET", "/audio/outputs/speaker/customEq")
    
#     def set_speaker_custom_eq(self, eq_values: List[int]) -> Dict[str, Any]:
#         """PUT /api/audio/outputs/speaker/customEq - Set speaker custom EQ"""
#         if len(eq_values) != 7:
#             raise Exception("EQ must have exactly 7 values (-12 to 12 dB)")
#         for val in eq_values:
#             if val < -12 or val > 12:
#                 raise Exception("EQ values must be between -12 and 12")
#         return self._make_request("PUT", "/audio/outputs/speaker/customEq", data=eq_values)
    
#     # ========== Mixer Methods ==========
    
#     def get_mixer_fade_behavior(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/mixer - Get mixer fade behavior"""
#         return self._make_request("GET", "/audio/inputs/mixer")
    
#     def set_mixer_fade_behavior(self, fade_behavior: str) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/mixer - Set mixer fade behavior"""
#         valid_behaviors = ["Off", "Fast", "Medium", "Slow"]
#         if fade_behavior not in valid_behaviors:
#             raise Exception(f"Invalid fade behavior. Must be one of: {valid_behaviors}")
#         return self._make_request("PUT", "/audio/inputs/mixer", data={"fadeBehavior": fade_behavior})
    
#     def get_active_mic_channel(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/mixer/activity - Get active mic channel"""
#         return self._make_request("GET", "/audio/inputs/mixer/activity")
    
#     # ========== Conference Output Methods ==========
    
#     def get_conference_output(self) -> Dict[str, Any]:
#         """GET /api/audio/outputs/conferenceOutput - Get conference output settings"""
#         return self._make_request("GET", "/audio/outputs/conferenceOutput")
    
#     def get_conference_output_object(self) -> ConferenceOutputSettings:
#         """Get conference output settings as typed object"""
#         response = self.get_conference_output()
#         return ConferenceOutputSettings(
#             far_end_gain=response.get('farEndGain', 0),
#             near_end_gain=response.get('nearEndGain', 0)
#         )
    
#     def set_conference_output(self, far_end_gain: int = None, near_end_gain: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/outputs/conferenceOutput - Set conference output settings"""
#         current = self.get_conference_output()
#         data = {
#             "farEndGain": far_end_gain if far_end_gain is not None else current.get('farEndGain', 0),
#             "nearEndGain": near_end_gain if near_end_gain is not None else current.get('nearEndGain', 0)
#         }
#         if data["farEndGain"] < -18 or data["farEndGain"] > 18:
#             raise Exception("Far end gain must be between -18 and 18 dB")
#         if data["nearEndGain"] < -18 or data["nearEndGain"] > 18:
#             raise Exception("Near end gain must be between -18 and 18 dB")
#         return self._make_request("PUT", "/audio/outputs/conferenceOutput", data=data)
    
#     # ========== Level Monitoring Methods ==========
    
#     def get_internal_mic_level(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/level - Get internal mic level"""
#         return self._make_request("GET", "/audio/inputs/internalMic/level")
    
#     def get_bluetooth_input_level(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/bluetooth - Get bluetooth input level"""
#         return self._make_request("GET", "/audio/inputs/bluetooth")
    
#     def get_usb_input_level(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/usb - Get USB input level"""
#         return self._make_request("GET", "/audio/inputs/usb")
    
#     # ========== Camera Methods ==========
    
#     def reset_camera_to_ffov(self) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/ffov - Reset camera to full field of view"""
#         return self._make_request("PUT", "/video/input/internalCamera/ffov")
    
#     def store_camera_preset(self) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/preset/store - Store current camera config"""
#         return self._make_request("PUT", "/video/input/internalCamera/preset/store")
    
#     def load_camera_preset(self) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/preset/load - Load camera preset"""
#         return self._make_request("PUT", "/video/input/internalCamera/preset/load")
    
#     def get_camera_ai_access(self) -> Dict[str, Any]:
#         """GET /api/video/input/internalCamera/aiAccess - Get auto framing and person tiling status"""
#         return self._make_request("GET", "/video/input/internalCamera/aiAccess")
    
#     def get_camera_ai_access_object(self) -> CameraAIAccess:
#         """Get camera AI access as typed object"""
#         response = self.get_camera_ai_access()
#         return CameraAIAccess(
#             auto_framing_access_enabled=response.get('autoFramingAccessEnabled', False),
#             auto_framing_enabled=response.get('autoFramingEnabled', False),
#             person_tiling_access_enabled=response.get('personTilingAccessEnabled', False),
#             person_tiling_enabled=response.get('personTilingEnabled', False)
#         )
    
#     def set_camera_ai_access(self, auto_framing_access: bool = None, 
#                               auto_framing: bool = None,
#                               person_tiling_access: bool = None,
#                               person_tiling: bool = None) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/aiAccess - Set auto framing and person tiling"""
#         current = self.get_camera_ai_access()
#         data = {
#             "autoFramingAccessEnabled": auto_framing_access if auto_framing_access is not None 
#                                         else current.get('autoFramingAccessEnabled', False),
#             "autoFramingEnabled": auto_framing if auto_framing is not None 
#                                  else current.get('autoFramingEnabled', False),
#             "personTilingAccessEnabled": person_tiling_access if person_tiling_access is not None 
#                                         else current.get('personTilingAccessEnabled', False),
#             "personTilingEnabled": person_tiling if person_tiling is not None 
#                                   else current.get('personTilingEnabled', False)
#         }
#         return self._make_request("PUT", "/video/input/internalCamera/aiAccess", data=data)
    
#     def move_camera_relative(self, up: int = 0, down: int = 0, left: int = 0, 
#                               right: int = 0, zoom_in: int = 0, zoom_out: int = 0) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/movement/relative - Move camera relatively"""
#         if (zoom_in > 0 and zoom_out > 0):
#             raise Exception("Cannot specify both zoom_in and zoom_out")
#         data = {
#             "up": up, "down": down, "left": left, "right": right,
#             "zoomIn": zoom_in, "zoomOut": zoom_out
#         }
#         return self._make_request("PUT", "/video/input/internalCamera/movement/relative", data=data)
    
#     def get_camera_video_parameters(self) -> Dict[str, Any]:
#         """GET /api/video/input/internalCamera/videoParameters - Get video parameters"""
#         return self._make_request("GET", "/video/input/internalCamera/videoParameters")
    
#     def get_camera_video_parameters_object(self) -> CameraVideoParameters:
#         """Get camera video parameters as typed object"""
#         response = self.get_camera_video_parameters()
#         return CameraVideoParameters(
#             compensation=response.get('compensation', 'Backlight'),
#             anti_flicker_frequency=response.get('antiFlickerFrequency', 'Auto'),
#             brightness=response.get('brightness', 0),
#             contrast=response.get('contrast', 5),
#             saturation=response.get('saturation', 5),
#             sharpness=response.get('sharpness', 2),
#             auto_whitebalance_enabled=response.get('autoWhitebalanceEnabled', True),
#             whitebalance=response.get('whitebalance', 4600),
#             default_camera_mode=response.get('defaultCameraMode', 'ResumeLastView')
#         )
    
#     def get_camera_movement(self) -> Dict[str, Any]:
#         """GET /api/video/input/internalCamera/movement - Get camera movement settings"""
#         return self._make_request("GET", "/video/input/internalCamera/movement")
    
#     def get_camera_movement_object(self) -> CameraMovementSettings:
#         """Get camera movement settings as typed object"""
#         response = self.get_camera_movement()
#         return CameraMovementSettings(
#             pan_position=response.get('panPosition', 0),
#             tilt_position=response.get('tiltPosition', 0),
#             zoom_position=response.get('zoomPosition', 100),
#             zoom_speed=response.get('zoomSpeed', 'Medium'),
#             pan_tilt_speed=response.get('panTiltSpeed', 'Medium'),
#             auto_framing_speed=response.get('autoFramingSpeed', 'Medium')
#         )
    
#     def set_camera_movement(self, pan_position: int = None, tilt_position: int = None,
#                              zoom_position: int = None, zoom_speed: str = None,
#                              pan_tilt_speed: str = None, auto_framing_speed: str = None) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/movement - Set camera movement"""
#         current = self.get_camera_movement()
#         data = {
#             "panPosition": pan_position if pan_position is not None else current.get('panPosition', 0),
#             "tiltPosition": tilt_position if tilt_position is not None else current.get('tiltPosition', 0),
#             "zoomPosition": zoom_position if zoom_position is not None else current.get('zoomPosition', 100),
#             "zoomSpeed": zoom_speed if zoom_speed is not None else current.get('zoomSpeed', 'Medium'),
#             "panTiltSpeed": pan_tilt_speed if pan_tilt_speed is not None else current.get('panTiltSpeed', 'Medium'),
#             "autoFramingSpeed": auto_framing_speed if auto_framing_speed is not None 
#                                else current.get('autoFramingSpeed', 'Medium')
#         }
#         return self._make_request("PUT", "/video/input/internalCamera/movement", data=data)
    
#     def get_camera_status(self) -> Dict[str, Any]:
#         """GET /api/video/input/internalCamera - Get camera status"""
#         return self._make_request("GET", "/video/input/internalCamera")
    
#     def get_hdmi_enabled(self) -> Dict[str, Any]:
#         """GET /api/video/output/hdmi - Get HDMI enabled status"""
#         return self._make_request("GET", "/video/output/hdmi")
    
#     def set_hdmi_enabled(self, enabled: bool) -> Dict[str, Any]:
#         """PUT /api/video/output/hdmi - Set HDMI enabled status"""
#         return self._make_request("PUT", "/video/output/hdmi", data={"enabled": enabled})
    
#     # ========== Network Methods ==========
    
#     def get_network_interfaces(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network - Get all network interfaces"""
#         return self._make_request("GET", "/interfaces/network")
    
#     def get_dante_status(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network/dante - Get Dante interface status"""
#         return self._make_request("GET", "/interfaces/network/dante")
    
#     def get_dante_settings(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network/dante/settings - Get Dante settings"""
#         return self._make_request("GET", "/interfaces/network/dante/settings")
    
#     def set_dante_settings(self, continuous_stream: bool = None, 
#                             speaker_output: bool = None) -> Dict[str, Any]:
#         """PUT /api/interfaces/network/dante/settings - Set Dante settings"""
#         current = self.get_dante_settings()
#         data = {
#             "continuousDanteStream": continuous_stream if continuous_stream is not None 
#                                     else current.get('continuousDanteStream', False),
#             "danteSpeakerOutput": speaker_output if speaker_output is not None 
#                                  else current.get('danteSpeakerOutput', False)
#         }
#         return self._make_request("PUT", "/interfaces/network/dante/settings", data=data)
    
#     def get_dante_input_levels(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/dante/levels - Get Dante audio levels"""
#         return self._make_request("GET", "/audio/inputs/dante/levels")
    
#     def get_dante_input_level(self, channel_id: int) -> Dict[str, Any]:
#         """GET /api/audio/inputs/dante/{id}/level - Get specific Dante channel level"""
#         return self._make_request("GET", f"/audio/inputs/dante/{channel_id}/level")
    
#     def get_dante_inputs(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/dante - Get Dante input parameters"""
#         return self._make_request("GET", "/audio/inputs/dante")
    
#     def get_dante_input(self, channel_id: int) -> Dict[str, Any]:
#         """GET /api/audio/inputs/dante/{id} - Get specific Dante input"""
#         return self._make_request("GET", f"/audio/inputs/dante/{channel_id}")
    
#     def set_dante_input_gain(self, channel_id: int, gain: int) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/dante/{id} - Set Dante input gain"""
#         if gain < -30 or gain > 30:
#             raise Exception("Gain must be between -30 and 30 dB")
#         return self._make_request("PUT", f"/audio/inputs/dante/{channel_id}", data={"gain": gain})
    
#     def get_port_configuration(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network/portConfiguration - Get port configuration"""
#         return self._make_request("GET", "/interfaces/network/portConfiguration")
    
#     def get_port_configuration_object(self) -> PortConfiguration:
#         """Get port configuration as typed object"""
#         response = self.get_port_configuration()
#         return PortConfiguration(
#             configuration=response.get('configuration', 'Split')
#         )
    
#     # ========== Bluetooth Methods ==========
    
#     def get_bluetooth_settings(self) -> Dict[str, Any]:
#         """GET /api/interfaces/bluetooth - Get Bluetooth settings"""
#         return self._make_request("GET", "/interfaces/bluetooth")
    
#     def get_bluetooth_settings_object(self) -> BluetoothSettings:
#         """Get Bluetooth settings as typed object"""
#         response = self.get_bluetooth_settings()
#         return BluetoothSettings(
#             enabled=response.get('enabled', False),
#             pairing=response.get('pairing', False),
#             mac=response.get('mac', '00:00:00:00:00:00')
#         )
    
#     def set_bluetooth_settings(self, enabled: bool = None, pairing: bool = None) -> Dict[str, Any]:
#         """PUT /api/interfaces/bluetooth - Set Bluetooth settings"""
#         current = self.get_bluetooth_settings()
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "pairing": pairing if pairing is not None else current.get('pairing', False)
#         }
#         return self._make_request("PUT", "/interfaces/bluetooth", data=data)
    
#     def get_bluetooth_devices_list(self) -> Dict[str, Any]:
#         """GET /api/interfaces/bluetooth/devicesList - Get list of known Bluetooth devices"""
#         return self._make_request("GET", "/interfaces/bluetooth/devicesList")
    
#     # ========== WiFi Methods ==========
    
#     def get_wifi_status(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network/wifi - Get WiFi status"""
#         return self._make_request("GET", "/interfaces/network/wifi")
    
#     def get_wifi_status_object(self) -> WifiStatus:
#         """Get WiFi status as typed object"""
#         response = self.get_wifi_status()
#         return WifiStatus(
#             enabled=response.get('enabled', False),
#             state=response.get('state', 'Disconnected'),
#             connection=response.get('connection', {})
#         )
    
#     # ========== Firmware Update Methods ==========
    
#     def get_firmware_update_state(self) -> Dict[str, Any]:
#         """GET /api/firmware/update/state - Get firmware update state"""
#         return self._make_request("GET", "/firmware/update/state")
    
#     def get_firmware_state_object(self) -> FirmwareUpdateState:
#         """Get firmware update state as typed object"""
#         response = self.get_firmware_update_state()
#         return FirmwareUpdateState(
#             device_version=response.get('deviceVersion', 'Unknown'),
#             state=response.get('state', 'Idle'),
#             progress=response.get('progress', 0),
#             last_status=response.get('lastStatus', 'None')
#         )
    
#     def is_firmware_updating(self) -> bool:
#         """Check if firmware update is in progress"""
#         state = self.get_firmware_update_state()
#         update_state = state.get('state', 'Idle')
#         return update_state in ['Downloading', 'Updating', 'Rebooting']
    
#     def get_firmware_progress(self) -> int:
#         """Get firmware update progress percentage"""
#         state = self.get_firmware_update_state()
#         return state.get('progress', 0)
    
#     # ========== SSC Methods ==========
    
#     def get_ssc_version(self) -> Dict[str, Any]:
#         """GET /api/ssc/version - Get schema version"""
#         return self._make_request("GET", "/ssc/version")
    
#     def get_ssc_schema(self) -> Dict[str, Any]:
#         """GET /api/ssc/schema - Get address tree"""
#         return self._make_request("GET", "/ssc/schema")
    
#     # ========== Real-time Monitoring ==========
    
#     def get_all_metrics(self) -> DeviceMetrics:
#         """Get all current device metrics"""
#         mic_level = self.get_internal_mic_level()
#         mute = self.get_mic_mute()
#         beam = self.get_beam_position()
#         active = self.get_active_mic_channel()
#         speaker = self.get_speaker_output()
#         usb_level = self.get_usb_input_level()
#         bt_level = self.get_bluetooth_input_level()
        
#         return DeviceMetrics(
#             timestamp=datetime.now(),
#             microphone_level=mic_level.get('peak', 0) if isinstance(mic_level, dict) else 0,
#             mute_status=mute.get('enabled') if isinstance(mute, dict) else None,
#             beam_position=beam.get('position', 0) if isinstance(beam, dict) else 0,
#             active_channel=active.get('activeChannel', 'Unknown') if isinstance(active, dict) else 'Unknown',
#             speaker_volume=speaker.get('volume', 50) if isinstance(speaker, dict) else 50,
#             usb_input_level=usb_level.get('level', 0) if isinstance(usb_level, dict) else 0,
#             bluetooth_input_level=bt_level.get('level', 0) if isinstance(bt_level, dict) else 0
#         )
    
#     def start_monitoring(self, interval: float = 1.0, callback: Optional[Callable] = None):
#         """Start continuous monitoring"""
#         if callback:
#             self.callbacks.append(callback)
        
#         if not self.monitoring:
#             self.monitoring = True
#             self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
#             self.monitor_thread.daemon = True
#             self.monitor_thread.start()
#             print(f"✅ Monitoring started (interval: {interval}s)")
    
#     def stop_monitoring(self):
#         """Stop continuous monitoring"""
#         self.monitoring = False
#         if self.monitor_thread:
#             self.monitor_thread.join(timeout=2)
#         print("✅ Monitoring stopped")
    
#     def _monitor_loop(self, interval: float):
#         """Background monitoring loop"""
#         while self.monitoring:
#             try:
#                 metrics = self.get_all_metrics()
#                 self.metrics_history.append(metrics)
                
#                 if len(self.metrics_history) > 1000:
#                     self.metrics_history = self.metrics_history[-1000:]
                
#                 for callback in self.callbacks:
#                     try:
#                         callback(metrics)
#                     except Exception as e:
#                         print(f"Callback error: {e}")
                
#                 time.sleep(interval)
#             except Exception as e:
#                 print(f"Monitoring error: {e}")
#                 time.sleep(interval)
    
#     def get_metrics_history(self, last_n: int = 100) -> List[DeviceMetrics]:
#         """Get historical metrics"""
#         return self.metrics_history[-last_n:] if self.metrics_history else []
    
#     def get_complete_device_info(self) -> Dict[str, Any]:
#         """Get all device information"""
#         identity = self.get_device_identity()
#         firmware = self.get_firmware_update_state()
#         state = self.get_device_state()
#         led = self.get_led_ring()
#         site = self.get_device_site()
#         beam = self.get_beam_position()
#         mic = self.get_internal_mic()
#         speaker = self.get_speaker_output()
#         noise_gate = self.get_noise_gate()
#         noise_suppression = self.get_noise_suppression()
#         sound_profile = self.get_sound_profile()
#         camera_ai = self.get_camera_ai_access()
#         camera_video = self.get_camera_video_parameters()
#         network = self.get_network_interfaces()
#         bluetooth = self.get_bluetooth_settings()
#         wifi = self.get_wifi_status()
        
#         return {
#             "identity": identity,
#             "firmware": firmware,
#             "state": state,
#             "led_settings": led,
#             "site_info": site,
#             "beam_position": beam,
#             "microphone": mic,
#             "speaker": speaker,
#             "noise_gate": noise_gate,
#             "noise_suppression": noise_suppression,
#             "sound_profile": sound_profile,
#             "camera": {
#                 "ai_access": camera_ai,
#                 "video_parameters": camera_video
#             },
#             "network": network,
#             "bluetooth": bluetooth,
#             "wifi": wifi,
#             "timestamp": datetime.now().isoformat(),
#             "ip": self.device_ip
#         }


# # ========== Interactive Controller ==========

# class SennheiserTCBarMController:
#     """Interactive controller for TeamConnect Bar M"""
    
#     def __init__(self, device_ip: str, username: str, password: str):
#         self.device = SennheiserTCBarMPlugin(device_ip, username, password)
#         self.monitoring_active = False
#         self.device_ip = device_ip
    
#     def display_metrics(self, metrics: DeviceMetrics):
#         """Display real-time metrics"""
#         mute_display = "🔴 MUTED" if metrics.mute_status else "🟢 LIVE"
#         print(f"\r📊 [{metrics.timestamp.strftime('%H:%M:%S')}] "
#               f"Mic: {metrics.microphone_level}dB | "
#               f"Beam: {metrics.beam_position}° | "
#               f"Volume: {metrics.speaker_volume}% | "
#               f"Active: {metrics.active_channel} | "
#               f"Mute: {mute_display}", end="")
    
#     def run_interactive_menu(self):
#         """Run interactive control menu"""
#         while True:
#             print("\n" + "=" * 70)
#             print(f" SENNHEISER TEAMCONNECT BAR M - COMPLETE CONTROL SYSTEM ({self.device_ip})")
#             print("=" * 70)
#             print("\n📊 CURRENT STATUS:")
            
#             try:
#                 metrics = self.device.get_all_metrics()
#                 identity = self.device.get_device_identity()
#                 state = self.device.get_device_state()
#                 site = self.device.get_device_site()
#                 mic = self.device.get_internal_mic()
#                 speaker = self.device.get_speaker_output()
#                 noise_gate = self.device.get_noise_gate()
#                 noise_suppression = self.device.get_noise_suppression()
#                 beam = self.device.get_beam_position()
#                 camera_ai = self.device.get_camera_ai_access()
#                 firmware = self.device.get_firmware_state_object()
                
#                 print(f"\n📱 DEVICE: {identity.get('product', 'TC Bar M')}")
#                 print(f"   Serial: {identity.get('serial', 'Unknown')}")
#                 print(f"   State: {state.get('state', 'Unknown')}")
#                 print(f"   Firmware: {firmware.device_version}")
                
#                 print(f"\n📍 SITE:")
#                 print(f"   Name: {site.get('deviceName', 'Unknown')}")
#                 print(f"   Location: {site.get('location', 'Unknown')}")
                
#                 print(f"\n🎤 AUDIO:")
#                 print(f"   Mic Level: {metrics.microphone_level} dB")
#                 print(f"   Mic Enabled: {'✅' if mic.get('enabled') else '❌'}")
#                 print(f"   Mic Gain: {mic.get('gain', 0)} dB")
#                 mute_display = "🔴 MUTED" if metrics.mute_status else "🟢 LIVE"
#                 print(f"   Mute Status: {mute_display}")
#                 print(f"   Speaker Volume: {speaker.get('volume', 50)}%")
#                 print(f"   Active Channel: {metrics.active_channel}")
                
#                 print(f"\n🎯 BEAMFORMING:")
#                 print(f"   Beam Position: {beam.get('position', 0)}°")
                
#                 print(f"\n🔧 PROCESSING:")
#                 print(f"   Noise Gate: {'✅' if noise_gate.get('enabled') else '❌'}")
#                 print(f"   Noise Suppression: {noise_suppression.get('weighting', 'Medium')}")
                
#                 print(f"\n📷 CAMERA:")
#                 print(f"   Auto Framing: {'✅' if camera_ai.get('autoFramingEnabled') else '❌'}")
#                 print(f"   Person Tiling: {'✅' if camera_ai.get('personTilingEnabled') else '❌'}")
                
#             except Exception as e:
#                 print(f"   ⚠️ Error getting status: {e}")
            
#             print("\n" + "=" * 70)
#             print("🎮 CONTROL COMMANDS:")
            
#             print("\n📢 AUDIO CONTROLS:")
#             print("  mute on/off           - Mute/Unmute microphone")
#             print("  volume <0-100>        - Set speaker volume")
#             # print("  volume up/down        - Increase/Decrease volume")
#             print("  mic gain <-30-30>     - Set microphone gain")
#             print("  mic enable/disable    - Enable/Disable microphone")
            
#             print("\n🎛️ PROCESSING:")
#             print("  noisegate on/off      - Enable/Disable noise gate")
#             print("  noisegate <thresh> <hold> <range> - Set noise gate params")
#             print("  suppress <off/low/medium/high> - Set noise suppression")
            
#             print("\n🎯 BEAMFORMING:")
#             print("  beam status           - Show beam position")
            
#             print("\n📷 CAMERA CONTROLS:")
#             print("  camera ai on/off      - Enable/Disable auto framing")
#             print("  camera tiling on/off  - Enable/Disable person tiling")
#             print("  camera ffov           - Reset to full field of view")
#             print("  camera preset store   - Store current camera preset")
#             print("  camera preset load    - Load camera preset")
#             print("  camera move <up/down/left/right> <steps> - Move camera")
            
#             print("  hdmi status           - Show HDMI output status")
#             print("  hdmi on/off           - Enable/Disable HDMI output")
            
#             print("\n💡 LED CONTROLS:")
#             print("  led bright <0-5>      - Set LED brightness")
#             print("  led status            - Show LED settings")
            
#             print("\n🌐 NETWORK:")
#             print("  network status        - Show network interfaces")
#             print("  dante status          - Show Dante status")
#             print("  bluetooth on/off      - Enable/Disable Bluetooth")
#             print("  wifi status           - Show WiFi status")
            
#             print("\n🔧 DEVICE:")
#             # print("  site name <name>      - Set device name")
#             # print("  site location <loc>   - Set location")
#             print("  sound prompts on/off  - Enable/Disable sound prompts")
#             print("  identify on/off       - Identify device (blink LEDs)")
#             print("  restart               - Restart device")
#             # print("  profile <custom/teams> - Set device profile")
#             print("  check profile         - Check current device profile")
#             print("  test permissions      - Test API read/write permissions")
#             print("  profile <custom/teams> - Set device profile")
            
#             print("\n📊 MONITORING:")
#             print("  status                - Show detailed status")
#             print("  firmware              - Show firmware status")
#             print("  monitor               - Start real-time monitoring")
#             print("  stop                  - Stop monitoring")
#             print("  info                  - Complete device info")
#             print("  exit                  - Exit")
#             print("=" * 70)
            
#             cmd = input("\n👉 Enter command: ").strip().lower()
            
#             try:
#                 if cmd == "exit":
#                     if self.monitoring_active:
#                         self.device.stop_monitoring()
#                     print("👋 Goodbye!")
#                     break

#                 elif cmd == "check profile":
#                     """Check current device profile"""
#                     try:
#                         profile = self.device.get_device_profile()
#                         print(f"📱 Current Device Profile: {profile.get('configuration', 'Unknown')}")
#                         if profile.get('configuration') == 'MicrosoftTeams':
#                             print("   ⚠️ WARNING: Microsoft Teams profile active!")
#                             print("   This restricts: HDMI control, camera parameters, and some audio settings")
#                             print("   Try: profile custom")
#                         else:
#                             print("   ✅ Custom profile active - Full control available")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")

#                 elif cmd == "test permissions":
#                     """Test various API permissions"""
#                     print("\n🔐 TESTING API PERMISSIONS:")
                    
#                     # Test read (should work)
#                     try:
#                         identity = self.device.get_device_identity()
#                         print("   ✅ GET /device/identity - READ permission: OK")
#                     except Exception as e:
#                         print(f"   ❌ READ test failed: {e}")
                    
#                     # Test write with LED (usually allowed)
#                     try:
#                         current_led = self.device.get_led_ring()
#                         current_brightness = current_led.get('brightness', 3)
#                         self.device.set_led_brightness(current_brightness)
#                         print("   ✅ PUT /device/leds/ring - WRITE permission: OK")
#                     except Exception as e:
#                         print(f"   ❌ LED write test failed: {e}")
                    
#                     # Check profile
#                     try:
#                         profile = self.device.get_device_profile()
#                         print(f"   📱 Device Profile: {profile.get('configuration')}")
#                     except Exception as e:
#                         print(f"   ❌ Profile check failed: {e}")
                
#                 # Audio commands
#                 elif cmd == "mute on":
#                     self.device.mute()
#                     print("✅ Microphone MUTED")
                
#                 elif cmd == "mute off":
#                     self.device.unmute()
#                     print("✅ Microphone UNMUTED")
                
#                 elif cmd.startswith("volume "):
#                     parts = cmd.split()
#                     if len(parts) == 2:
#                         volume = int(parts[1])
#                         self.device.set_volume(volume)
#                         print(f"✅ Volume set to {volume}%")
#                     else:
#                         print("❌ Usage: volume <0-100>")
                
#                 elif cmd == "volume up":
#                     self.device.volume_up()
#                     print("✅ Volume increased")
                
#                 elif cmd == "volume down":
#                     self.device.volume_down()
#                     print("✅ Volume decreased")
                
#                 elif cmd.startswith("mic gain"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         gain = int(parts[2])
#                         self.device.set_internal_mic(gain=gain)
#                         print(f"✅ Mic gain set to {gain} dB")
#                     else:
#                         print("❌ Usage: mic gain <-30 to 30>")
                
#                 elif cmd == "mic enable":
#                     self.device.set_internal_mic(enabled=True)
#                     print("✅ Microphone ENABLED")
                
#                 elif cmd == "mic disable":
#                     self.device.set_internal_mic(enabled=False)
#                     print("✅ Microphone DISABLED")
                    

#                 elif cmd == "hdmi status":
#                     """Get HDMI output status"""
#                     try:
#                         hdmi = self.device.get_hdmi_enabled()
#                         status = "✅ ENABLED" if hdmi.get('enabled') else "❌ DISABLED"
#                         print(f"📺 HDMI Output: {status}")
#                         if not hdmi.get('enabled'):
#                             print("   Note: HDMI output is disabled. Use 'hdmi on' to enable")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
#                 elif cmd == "hdmi on":
#                     """Enable HDMI output"""
#                     try:
#                         self.device.set_hdmi_enabled(True)
#                         print("✅ HDMI Output ENABLED")
#                         # Verify the change
#                         time.sleep(0.5)
#                         hdmi = self.device.get_hdmi_enabled()
#                         if hdmi.get('enabled'):
#                             print("   Verified: HDMI is now active")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 elif cmd == "hdmi off":
#                     """Disable HDMI output"""
#                     try:
#                         self.device.set_hdmi_enabled(False)
#                         print("✅ HDMI Output DISABLED")
#                         # Verify the change
#                         time.sleep(0.5)
#                         hdmi = self.device.get_hdmi_enabled()
#                         if not hdmi.get('enabled'):
#                             print("   Verified: HDMI is now inactive")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 # Processing commands
#                 elif cmd == "noisegate on":
#                     self.device.set_noise_gate(enabled=True)
#                     print("✅ Noise gate ENABLED")
                
#                 elif cmd == "noisegate off":
#                     self.device.set_noise_gate(enabled=False)
#                     print("✅ Noise gate DISABLED")
                
#                 elif cmd.startswith("noisegate "):
#                     parts = cmd.split()
#                     if len(parts) == 4:
#                         threshold = int(parts[1])
#                         hold = int(parts[2])
#                         range_val = int(parts[3])
#                         self.device.set_noise_gate(enabled=True, threshold=threshold, 
#                                                     hold_time=hold, range_val=range_val)
#                         print(f"✅ Noise gate set: threshold={threshold}dB, hold={hold}ms, range={range_val}dB")
#                     else:
#                         print("❌ Usage: noisegate <threshold -80 to -20> <hold 100-2000> <range -80 to 0>")
                
#                 elif cmd.startswith("suppress"):
#                     parts = cmd.split()
#                     if len(parts) == 2:
#                         weighting = parts[1].capitalize()
#                         self.device.set_noise_suppression(weighting)
#                         print(f"✅ Noise suppression set to {weighting}")
#                     else:
#                         print("❌ Usage: suppress <off/low/medium/high>")
                
#                 # Beam commands
#                 elif cmd == "beam status":
#                     beam = self.device.get_beam_position()
#                     print(f"🎯 Beam Position: {beam.get('position', 0)}°")
                
#                 # Camera commands
#                 elif cmd == "camera ai on":
#                     self.device.set_camera_ai_access(auto_framing=True)
#                     print("✅ Auto framing ENABLED")
                
#                 elif cmd == "camera ai off":
#                     self.device.set_camera_ai_access(auto_framing=False)
#                     print("✅ Auto framing DISABLED")
                
#                 elif cmd == "camera tiling on":
#                     self.device.set_camera_ai_access(person_tiling=True)
#                     print("✅ Person tiling ENABLED")
                
#                 elif cmd == "camera tiling off":
#                     self.device.set_camera_ai_access(person_tiling=False)
#                     print("✅ Person tiling DISABLED")
                
#                 elif cmd == "camera ffov":
#                     self.device.reset_camera_to_ffov()
#                     print("✅ Camera reset to full field of view")
                
#                 elif cmd == "camera preset store":
#                     self.device.store_camera_preset()
#                     print("✅ Camera preset STORED")
                
#                 elif cmd == "camera preset load":
#                     self.device.load_camera_preset()
#                     print("✅ Camera preset LOADED")
                
#                 elif cmd == "camera zoom in":
#                     self.device.move_camera_relative(zoom_in=1)
#                     print("✅ Zoom IN")
                
#                 elif cmd == "camera zoom out":
#                     self.device.move_camera_relative(zoom_out=1)
#                     print("✅ Zoom OUT")
                
#                 elif cmd.startswith("camera move"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         direction = parts[2]
#                         steps = int(parts[3]) if len(parts) > 3 else 1
#                         if direction == "up":
#                             self.device.move_camera_relative(up=steps)
#                         elif direction == "down":
#                             self.device.move_camera_relative(down=steps)
#                         elif direction == "left":
#                             self.device.move_camera_relative(left=steps)
#                         elif direction == "right":
#                             self.device.move_camera_relative(right=steps)
#                         print(f"✅ Camera moved {direction} by {steps}")
#                     else:
#                         print("❌ Usage: camera move <up/down/left/right> [steps]")
                
#                 # LED commands
#                 elif cmd.startswith("led bright"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         brightness = int(parts[2])
#                         if 0 <= brightness <= 5:
#                             self.device.set_led_brightness(brightness)
#                             print(f"✅ LED brightness set to {brightness}")
#                         else:
#                             print("❌ Brightness must be 0-5")
                
#                 elif cmd == "led status":
#                     led = self.device.get_led_ring()
#                     print(f"💡 LED Brightness: {led.get('brightness', 3)}")

#                 elif cmd == "restart":
#                     confirm = input("⚠️ Are you sure you want to restart the device? (yes/no): ")
#                     if confirm.lower() == "yes":
#                         self.device.restart_device()
#                         print("🔄 Device restarting...")
#                     else:
#                         print("Restart cancelled")
                
#                 # Network commands
#                 elif cmd == "network status":
#                     network = self.device.get_network_interfaces()
#                     print("\n🌐 NETWORK INTERFACES:")
#                     print(json.dumps(network, indent=2))
                
#                 elif cmd == "dante status":
#                     dante = self.device.get_dante_status()
#                     print(f"🎵 Dante Enabled: {dante.get('enabled', False)}")
                
#                 elif cmd == "bluetooth on":
#                     self.device.set_bluetooth_settings(enabled=True)
#                     print("✅ Bluetooth ENABLED")
                
#                 elif cmd == "bluetooth off":
#                     self.device.set_bluetooth_settings(enabled=False)
#                     print("✅ Bluetooth DISABLED")
                
#                 elif cmd == "wifi status":
#                     wifi = self.device.get_wifi_status()
#                     print(f"📡 WiFi Enabled: {wifi.get('enabled', False)}")
#                     print(f"   State: {wifi.get('state', 'Unknown')}")
                
#                 # Device commands
#                 elif cmd.startswith("site name"):
#                     parts = cmd.split(maxsplit=2)
#                     if len(parts) >= 3:
#                         name = parts[2]
#                         self.device.set_device_site(device_name=name)
#                         print(f"✅ Device name set to {name}")
#                     else:
#                         print("❌ Usage: site name <name>")
                
#                 elif cmd.startswith("site location"):
#                     parts = cmd.split(maxsplit=2)
#                     if len(parts) >= 3:
#                         location = parts[2]
#                         self.device.set_device_site(location=location)
#                         print(f"✅ Location set to {location}")
#                     else:
#                         print("❌ Usage: site location <location>")
                
#                 elif cmd == "sound prompts on":
#                     self.device.set_sound_prompts(True)
#                     print("✅ Sound prompts ENABLED")
                
#                 elif cmd == "sound prompts off":
#                     self.device.set_sound_prompts(False)
#                     print("✅ Sound prompts DISABLED")
                
#                 elif cmd == "identify on":
#                     self.device.identify_device(True)
#                     print("✅ Device identification started - LEDs will blink")
                
#                 elif cmd == "identify off":
#                     self.device.identify_device(False)
#                     print("✅ Device identification stopped")
                
#                 elif cmd == "restart":
#                     confirm = input("⚠️ Are you sure you want to restart the device? (yes/no): ")
#                     if confirm.lower() == "yes":
#                         self.device.restart_device()
#                         print("🔄 Device restarting...")
#                     else:
#                         print("Restart cancelled")
                
#                 elif cmd.startswith("profile"):
#                     parts = cmd.split()
#                     if len(parts) == 2:
#                         profile = parts[1].capitalize()
#                         if profile in ["Custom", "MicrosoftTeams"]:
#                             self.device.set_device_profile(profile)
#                             print(f"✅ Device profile set to {profile}")
#                         else:
#                             print("❌ Profile must be 'custom' or 'teams'")
#                     else:
#                         print("❌ Usage: profile <custom/teams>")
                
#                 # Monitoring commands
#                 elif cmd == "status":
#                     info = self.device.get_complete_device_info()
#                     print("\n📱 DETAILED DEVICE STATUS:")
#                     print(json.dumps(info, indent=2, default=str))
                
#                 elif cmd == "firmware":
#                     fw = self.device.get_firmware_state_object()
#                     print(f"\n📦 FIRMWARE:")
#                     print(f"   Device Version: {fw.device_version}")
#                     print(f"   State: {fw.state}")
#                     if fw.state != 'Idle':
#                         print(f"   Progress: {fw.progress}%")
#                         print(f"   Last Status: {fw.last_status}")
                
#                 elif cmd == "monitor":
#                     if not self.monitoring_active:
#                         self.monitoring_active = True
#                         self.device.start_monitoring(1.0, self.display_metrics)
#                         print("\n✅ Real-time monitoring started (press Ctrl+C to stop)")
#                     else:
#                         print("⚠️ Monitoring already active")
                
#                 elif cmd == "stop":
#                     if self.monitoring_active:
#                         self.device.stop_monitoring()
#                         self.monitoring_active = False
#                         print("✅ Monitoring stopped")
                
#                 elif cmd == "info":
#                     info = self.device.get_complete_device_info()
#                     print("\n📱 COMPLETE DEVICE INFO:")
#                     print(json.dumps(info, indent=2, default=str))
                
#                 else:
#                     print("❌ Unknown command")
                    
#             except Exception as e:
#                 print(f"❌ Error: {e}")


# # ========== Main Entry Point ==========

# def get_user_credentials():
#     """Get device connection details from user"""
#     print("\n" + "=" * 60)
#     print(" SENNHEISER TEAMCONNECT BAR M DEVICE CONNECTION SETUP")
#     print("=" * 60)
    
#     device_ip = input("\n🔌 Enter Device IP Address: ").strip()
#     username = input("👤 Enter Username (default: api): ").strip() or "api"
#     password = getpass.getpass("🔑 Enter Password: ").strip()
    
#     return device_ip, username, password


# def validate_connection(device_ip, username, password):
#     """Validate the connection with provided credentials"""
#     print("\n🔍 Validating connection...")
    
#     test_device = SennheiserTCBarMPlugin(device_ip, username, password)
    
#     try:
#         identity = test_device.get_device_identity()
#         if identity and 'product' in identity:
#             print(f"   ✅ Connection successful!")
#             print(f"   📱 Device: {identity.get('product')}")
#             print(f"   🔢 Serial: {identity.get('serial')}")
#             return True, test_device
#         return False, None
#     except Exception as e:
#         print(f"   ❌ Connection failed: {e}")
#         return False, None


# def main():
#     """Main entry point"""
#     print("\n" + "=" * 60)
#     print(" SENNHEISER TEAMCONNECT BAR M DEVICE CONTROL PLUGIN")
#     print("=" * 60)
    
#     device_ip, username, password = get_user_credentials()
#     success, device = validate_connection(device_ip, username, password)
    
#     if not success:
#         print("\n❌ Failed to connect. Please check:")
#         print("   1. Device IP address is correct")
#         print("   2. 3rd Party Access is enabled in device settings")
#         print("   3. Username and password are correct")
#         print("\n   Note: Default credentials are username='api' with password set in device settings")
#         return
    
#     print("\n✅ CONNECTION ESTABLISHED - LAUNCHING CONTROL INTERFACE")
#     controller = SennheiserTCBarMController(device_ip, username, password)
    
#     try:
#         controller.run_interactive_menu()
#     except KeyboardInterrupt:
#         print("\n\n👋 Goodbye!")
#     except Exception as e:
#         print(f"\n❌ Error: {e}")


# if __name__ == "__main__":
#     main()







# #!/usr/bin/env python3
# """
# Sennheiser TC Bar M Device Control Plugin - Complete API Integration
# Based on SSC v2 API (Schema 1.0, Protocol 2.3)
# """

# import urllib.request
# import urllib.error
# import ssl
# import json
# import base64
# import time
# import threading
# import getpass
# import sys
# from typing import Optional, Dict, Any, List, Callable, Union
# from datetime import datetime
# from dataclasses import dataclass, field
# from enum import Enum

# # ========== Enums ==========

# class NoiseSuppressionWeighting(Enum):
#     """Noise suppression weighting options"""
#     OFF = "Off"
#     LOW = "Low"
#     MEDIUM = "Medium"
#     HIGH = "High"

# class FadeBehavior(Enum):
#     """Fade behavior for mic mixer"""
#     OFF = "Off"
#     FAST = "Fast"
#     MEDIUM = "Medium"
#     SLOW = "Slow"

# class SoundProfilePreset(Enum):
#     """Sound profile presets"""
#     WALLMOUNT = "Wallmount"
#     CEILING_MOUNT = "CeilingMount"
#     CUSTOM = "Custom"

# class IPMode(Enum):
#     """IP configuration modes"""
#     AUTO = "Auto"
#     MANUAL = "Manual"

# class StandbyMode(Enum):
#     """Standby/energy saving modes"""
#     OFF = "Off"
#     ECO_MODE = "EcoMode"
#     DEEP_SLEEP = "DeepSleep"

# class DeviceProfile(Enum):
#     """Device profiles"""
#     CUSTOM = "Custom"
#     MICROSOFT_TEAMS = "MicrosoftTeams"

# class AntiFlickerFrequency(Enum):
#     """Anti-flicker frequency options"""
#     AUTO = "Auto"
#     _50HZ = "50Hz"
#     _60HZ = "60Hz"

# class ZoomSpeed(Enum):
#     """Zoom speed options"""
#     SLOW = "Slow"
#     MEDIUM = "Medium"
#     FAST = "Fast"

# class PanTiltSpeed(Enum):
#     """Pan/Tilt speed options"""
#     SLOW = "Slow"
#     MEDIUM = "Medium"
#     FAST = "Fast"

# class ZoneGain(Enum):
#     """Zone gain options"""
#     OFF = "Off"
#     LOW = "Low"
#     MEDIUM = "Medium"
#     HIGH = "High"

# # ========== Data Classes ==========

# @dataclass
# class DeviceState:
#     """Device state information"""
#     state: str  # Normal, Warning, Error
#     warnings: List[str] = field(default_factory=list)
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DeviceIdentity:
#     """Device identity information"""
#     product: str
#     hardware_revision: str
#     serial: str
#     vendor: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DeviceSiteInfo:
#     """Device site information"""
#     device_name: str
#     dante_name: str
#     location: str
#     position: str
#     language: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class FirmwareUpdateState:
#     """Firmware update state"""
#     device_version: str
#     state: str  # Idle, Downloading, Updating, Rebooting, Error
#     progress: int
#     last_status: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class LEDRingSettings:
#     """LED ring settings"""
#     brightness: int  # 0-5
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class SoundPromptsSettings:
#     """Sound prompts settings"""
#     sound_prompts: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class InternalMicSettings:
#     """Internal microphone settings"""
#     gain: int  # -30 to 30 dB
#     enabled: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class MuteSettings:
#     """Mute settings"""
#     enabled: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class NoiseGateSettings:
#     """Noise gate settings for internal mic"""
#     enabled: bool
#     threshold: int  # -80 to -20 dB
#     hold_time: int  # 100-2000 ms
#     range: int  # -80 to 0 dB
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class SpeakerOutputSettings:
#     """Speaker output settings"""
#     volume: int  # 0-100
#     level_limiter: int  # 0-100
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class SoundProfileSettings:
#     """Sound profile settings"""
#     preset: str  # Wallmount, CeilingMount, Custom
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class PriorityZoneSettings:
#     """Priority zone settings"""
#     id: int
#     active: bool
#     enabled: bool
#     gain: str  # Off, Low, Medium, High
#     left: int  # 0-100
#     right: int  # 0-100
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class ExclusionZoneSettings:
#     """Exclusion zone settings"""
#     id: int
#     active: bool
#     enabled: bool
#     left: int  # 0-100
#     right: int  # 0-100
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class BeamPosition:
#     """Beam position"""
#     position: int  # 0-180 degrees
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DeviceMetrics:
#     """Real-time device metrics"""
#     timestamp: datetime
#     microphone_level: int  # peak level
#     mute_status: Optional[bool]
#     beam_position: int
#     active_channel: str
#     speaker_volume: int
#     usb_input_level: int
#     bluetooth_input_level: int

# @dataclass
# class CameraVideoParameters:
#     """Camera video parameters"""
#     compensation: str  # Backlight, WDR, etc.
#     anti_flicker_frequency: str  # Auto, 50Hz, 60Hz
#     brightness: int  # -20 to 20
#     contrast: int  # 0-10
#     saturation: int  # 0-10
#     sharpness: int  # 0-4
#     auto_whitebalance_enabled: bool
#     whitebalance: int  # 2000-10000
#     default_camera_mode: str  # ResumeLastView, FullFieldOfView
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class CameraMovementSettings:
#     """Camera movement settings"""
#     pan_position: int  # 0-360
#     tilt_position: int  # -25-25
#     zoom_position: int  # 0-100
#     zoom_speed: str  # Slow, Medium, Fast
#     pan_tilt_speed: str  # Slow, Medium, Fast
#     auto_framing_speed: str  # Slow, Medium, Fast
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class CameraAIAccess:
#     """Camera AI access settings"""
#     auto_framing_access_enabled: bool
#     auto_framing_enabled: bool
#     person_tiling_access_enabled: bool
#     person_tiling_enabled: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class NetworkInterface:
#     """Network interface settings"""
#     name: str
#     type: str
#     mac: str
#     functionalities: List[str]
#     auto_discovery: bool
#     ip_mode: str
#     ipv4: Dict[str, Any]
#     ipv6: Dict[str, Any]
#     vlan_tag: Optional[int]
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DanteSettings:
#     """Dante settings"""
#     enabled: bool
#     continuous_dante_stream: bool = False
#     dante_speaker_output: bool = False
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class BluetoothSettings:
#     """Bluetooth settings"""
#     enabled: bool
#     pairing: bool
#     mac: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class WifiStatus:
#     """WiFi status"""
#     enabled: bool
#     state: str
#     connection: Dict[str, Any]
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class ConferenceOutputSettings:
#     """Conference output settings"""
#     far_end_gain: int  # -18 to 18 dB
#     near_end_gain: int  # -18 to 18 dB
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class PortConfiguration:
#     """Port configuration for RJ45 ports"""
#     configuration: str  # SingleDomain, DualDomain, Split
#     timestamp: datetime = field(default_factory=datetime.now)


# # ========== Main Plugin Class ==========

# class SennheiserTCBarMPlugin:
#     """Complete plugin for Sennheiser TeamConnect Bar M with all API endpoints"""
    
#     def __init__(self, device_ip: str, username: str, password: str, verify_ssl: bool = False):
#         self.device_ip = device_ip
#         self.base_url = f"https://{device_ip}/api"
#         self.username = username
#         self.password = password
        
#         # Setup authentication
#         auth_string = f"{username}:{password}"
#         auth_bytes = auth_string.encode('utf-8')
#         self.auth_header = base64.b64encode(auth_bytes).decode('ascii')
        
#         # SSL context
#         self.ssl_context = ssl.create_default_context()
#         self.ssl_context.check_hostname = False
#         self.ssl_context.verify_mode = ssl.CERT_NONE
        
#         # Monitoring state
#         self.monitoring = False
#         self.monitor_thread = None
#         self.metrics_history = []
#         self.callbacks = []
        
#         # Firmware update monitoring
#         self.firmware_monitoring = False
#         self.firmware_monitor_thread = None
    
#     def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
#         """Make HTTP request to the device"""
#         url = f"{self.base_url}{endpoint}"
        
#         headers = {
#             "Accept": "application/json",
#             "Authorization": f"Basic {self.auth_header}"
#         }
        
#         if data and method in ["PUT", "POST"]:
#             headers["Content-Type"] = "application/json"
#             request_data = json.dumps(data).encode('utf-8')
#         else:
#             request_data = None
        
#         req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
        
#         try:
#             response = urllib.request.urlopen(req, context=self.ssl_context, timeout=10)
#             response_data = response.read().decode('utf-8')
#             return json.loads(response_data) if response_data else {}
#         except urllib.error.HTTPError as e:
#             if e.code == 401:
#                 raise Exception("Authentication failed - Invalid username or password")
#             elif e.code == 403:
#                 raise Exception("Forbidden - Check 3rd party access settings")
#             error_msg = e.read().decode('utf-8') if e.fp else str(e)
#             return {"error": f"HTTP {e.code}", "message": error_msg}
#         except Exception as e:
#             return {"error": str(e)}
    
#     # ========== Validation Method ==========
    
#     def validate_connection(self) -> bool:
#         """Validate that the connection and credentials work"""
#         try:
#             result = self.get_device_identity()
#             if result and 'product' in result:
#                 return True
#             return False
#         except Exception as e:
#             print(f"Validation failed: {e}")
#             return False
    
#     # ========== Device Information Methods ==========
    
#     def get_device_state(self) -> Dict[str, Any]:
#         """GET /api/device/state - Get device state"""
#         return self._make_request("GET", "/device/state")
    
#     def get_device_state_object(self) -> DeviceState:
#         """Get device state as typed object"""
#         response = self.get_device_state()
#         return DeviceState(
#             state=response.get('state', 'Unknown'),
#             warnings=response.get('warnings', [])
#         )
    
#     def get_device_identity(self) -> Dict[str, Any]:
#         """GET /api/device/identity - Get device identity"""
#         return self._make_request("GET", "/device/identity")
    
#     def get_device_identity_object(self) -> DeviceIdentity:
#         """Get device identity as typed object"""
#         response = self.get_device_identity()
#         return DeviceIdentity(
#             product=response.get('product', 'Unknown'),
#             hardware_revision=response.get('hardwareRevision', 'Unknown'),
#             serial=response.get('serial', 'Unknown'),
#             vendor=response.get('vendor', 'Sennheiser')
#         )
    
#     def get_identification_state(self) -> Dict[str, Any]:
#         """GET /api/device/identification - Get identification state"""
#         return self._make_request("GET", "/device/identification")
    
#     def set_identification(self, visual: bool) -> Dict[str, Any]:
#         """PUT /api/device/identification - Set device identification (blink LEDs)"""
#         return self._make_request("PUT", "/device/identification", data={"visual": visual})
    
#     def identify_device(self, enable: bool = True) -> Dict[str, Any]:
#         """Convenience method to identify device by blinking LEDs"""
#         return self.set_identification(enable)
    
#     def restart_device(self) -> Dict[str, Any]:
#         """PUT /api/device/restart - Restart the device"""
#         return self._make_request("PUT", "/device/restart")
    
#     def get_allowed_standby_mode(self) -> Dict[str, Any]:
#         """GET /api/device/allowedStandbyMode - Get lowest allowed standby mode"""
#         return self._make_request("GET", "/device/allowedStandbyMode")
    
#     def set_allowed_standby_mode(self, mode: str) -> Dict[str, Any]:
#         """PUT /api/device/allowedStandbyMode - Set lowest allowed standby mode"""
#         valid_modes = ["Off", "EcoMode", "DeepSleep"]
#         if mode not in valid_modes:
#             raise Exception(f"Invalid mode. Must be one of: {valid_modes}")
#         return self._make_request("PUT", "/device/allowedStandbyMode", data={"mode": mode})
    
#     def get_user_interaction(self) -> Dict[str, Any]:
#         """GET /api/device/hasUserInteraction - Check if device has user interaction"""
#         return self._make_request("GET", "/device/hasUserInteraction")
    
#     def get_sound_prompts(self) -> Dict[str, Any]:
#         """GET /api/device/feedback - Get sound prompts settings"""
#         return self._make_request("GET", "/device/feedback")
    
#     def set_sound_prompts(self, enabled: bool) -> Dict[str, Any]:
#         """PUT /api/device/feedback - Set sound prompts settings"""
#         return self._make_request("PUT", "/device/feedback", data={"soundPrompts": enabled})
    
#     def get_device_site(self) -> Dict[str, Any]:
#         """GET /api/device/site - Get device site information"""
#         return self._make_request("GET", "/device/site")
    
#     def get_device_site_object(self) -> DeviceSiteInfo:
#         """Get device site information as typed object"""
#         response = self.get_device_site()
#         return DeviceSiteInfo(
#             device_name=response.get('deviceName', 'Unknown'),
#             dante_name=response.get('danteName', 'Unknown'),
#             location=response.get('location', 'Unknown'),
#             position=response.get('position', ''),
#             language=response.get('language', 'En_GB')
#         )
    
#     def set_device_site(self, device_name: str = None, location: str = None, 
#                         position: str = None, language: str = None) -> Dict[str, Any]:
#         """PUT /api/device/site - Set device site information"""
#         current = self.get_device_site()
#         data = {
#             "deviceName": device_name if device_name else current.get('deviceName'),
#             "danteName": current.get('danteName', current.get('deviceName')),
#             "location": location if location else current.get('location', ''),
#             "position": position if position else current.get('position', ''),
#             "language": language if language else current.get('language', 'En_GB')
#         }
#         return self._make_request("PUT", "/device/site", data=data)
    
#     def get_device_profile(self) -> Dict[str, Any]:
#         """GET /api/device/profile - Get device profile"""
#         return self._make_request("GET", "/device/profile")
    
#     def set_device_profile(self, configuration: str) -> Dict[str, Any]:
#         """PUT /api/device/profile - Set device profile (Custom, MicrosoftTeams)"""
#         valid_profiles = ["Custom", "MicrosoftTeams"]
#         if configuration not in valid_profiles:
#             raise Exception(f"Invalid profile. Must be one of: {valid_profiles}")
#         return self._make_request("PUT", "/device/profile", data={"configuration": configuration})
    
#     # ========== LED Control Methods ==========
    
#     def get_led_ring(self) -> Dict[str, Any]:
#         """GET /api/device/leds/ring - Get LED ring settings"""
#         return self._make_request("GET", "/device/leds/ring")
    
#     def get_led_ring_object(self) -> LEDRingSettings:
#         """Get LED ring settings as typed object"""
#         response = self.get_led_ring()
#         return LEDRingSettings(
#             brightness=response.get('brightness', 3)
#         )
    
#     def set_led_brightness(self, brightness: int) -> Dict[str, Any]:
#         """PUT /api/device/leds/ring - Set LED ring brightness (0-5)"""
#         if not 0 <= brightness <= 5:
#             raise Exception("Brightness must be between 0 and 5")
#         return self._make_request("PUT", "/device/leds/ring", data={"brightness": brightness})
    
#     # ========== Audio Methods ==========
    
#     def get_relative_speaker_volume(self, volume_up: int = 0, volume_down: int = 0) -> Dict[str, Any]:
#         """PUT /api/audio/outputs/speaker/relative - Adjust speaker volume relatively"""
#         if volume_up > 0 and volume_down > 0:
#             raise Exception("Cannot specify both volume_up and volume_down")
#         return self._make_request("PUT", "/audio/outputs/speaker/relative", 
#                                    data={"volumeUp": volume_up, "volumeDown": volume_down})
    
#     def volume_up(self, steps: int = 1) -> Dict[str, Any]:
#         """Increase speaker volume by steps"""
#         return self.get_relative_speaker_volume(volume_up=steps)
    
#     def volume_down(self, steps: int = 1) -> Dict[str, Any]:
#         """Decrease speaker volume by steps"""
#         return self.get_relative_speaker_volume(volume_down=steps)
    
#     def get_internal_mic(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic - Get internal mic parameters"""
#         return self._make_request("GET", "/audio/inputs/internalMic")
    
#     def get_internal_mic_object(self) -> InternalMicSettings:
#         """Get internal mic settings as typed object"""
#         response = self.get_internal_mic()
#         return InternalMicSettings(
#             gain=response.get('gain', 0),
#             enabled=response.get('enabled', True)
#         )
    
#     def set_internal_mic(self, gain: int = None, enabled: bool = None) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic - Set internal mic parameters"""
#         current = self.get_internal_mic()
#         data = {
#             "gain": gain if gain is not None else current.get('gain', 0),
#             "enabled": enabled if enabled is not None else current.get('enabled', True)
#         }
#         if data["gain"] < -30 or data["gain"] > 30:
#             raise Exception("Gain must be between -30 and 30 dB")
#         return self._make_request("PUT", "/audio/inputs/internalMic", data=data)
    
#     def get_mic_mute(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/mute - Get mute state (after mixer)"""
#         return self._make_request("GET", "/audio/inputs/mute")
    
#     def set_mic_mute(self, enabled: bool) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/mute - Set mute state (after mixer)"""
#         return self._make_request("PUT", "/audio/inputs/mute", data={"enabled": enabled})
    
#     def mute(self) -> Dict[str, Any]:
#         """Convenience method to mute microphone"""
#         return self.set_mic_mute(True)
    
#     def unmute(self) -> Dict[str, Any]:
#         """Convenience method to unmute microphone"""
#         return self.set_mic_mute(False)
    
#     def get_noise_gate(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/noiseGate - Get noise gate settings"""
#         return self._make_request("GET", "/audio/inputs/internalMic/noiseGate")
    
#     def get_noise_gate_object(self) -> NoiseGateSettings:
#         """Get noise gate settings as typed object"""
#         response = self.get_noise_gate()
#         return NoiseGateSettings(
#             enabled=response.get('enabled', False),
#             threshold=response.get('threshold', -40),
#             hold_time=response.get('holdTime', 300),
#             range=response.get('range', -40)
#         )
    
#     def set_noise_gate(self, enabled: bool = None, threshold: int = None, 
#                        hold_time: int = None, range_val: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic/noiseGate - Set noise gate settings"""
#         current = self.get_noise_gate()
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "threshold": threshold if threshold is not None else current.get('threshold', -40),
#             "holdTime": hold_time if hold_time is not None else current.get('holdTime', 300),
#             "range": range_val if range_val is not None else current.get('range', -40)
#         }
#         return self._make_request("PUT", "/audio/inputs/internalMic/noiseGate", data=data)
    
#     def get_noise_suppression(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/noiseSuppression - Get noise suppression config"""
#         return self._make_request("GET", "/audio/inputs/noiseSuppression")
    
#     def set_noise_suppression(self, weighting: str) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/noiseSuppression - Set noise suppression weighting"""
#         valid_weightings = ["Off", "Low", "Medium", "High"]
#         if weighting not in valid_weightings:
#             raise Exception(f"Invalid weighting. Must be one of: {valid_weightings}")
#         return self._make_request("PUT", "/audio/inputs/noiseSuppression", 
#                                    data={"weighting": weighting})
    
#     def get_speaker_output(self) -> Dict[str, Any]:
#         """GET /api/audio/outputs/speaker - Get speaker output parameters"""
#         return self._make_request("GET", "/audio/outputs/speaker")
    
#     def get_speaker_output_object(self) -> SpeakerOutputSettings:
#         """Get speaker output settings as typed object"""
#         response = self.get_speaker_output()
#         return SpeakerOutputSettings(
#             volume=response.get('volume', 50),
#             level_limiter=response.get('levelLimiter', 100)
#         )
    
#     def set_speaker_output(self, volume: int = None, level_limiter: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/outputs/speaker - Set speaker output parameters"""
#         current = self.get_speaker_output()
#         data = {
#             "volume": volume if volume is not None else current.get('volume', 50),
#             "levelLimiter": level_limiter if level_limiter is not None else current.get('levelLimiter', 100)
#         }
#         if data["volume"] < 0 or data["volume"] > 100:
#             raise Exception("Volume must be between 0 and 100")
#         return self._make_request("PUT", "/audio/outputs/speaker", data=data)
    
#     def set_volume(self, volume: int) -> Dict[str, Any]:
#         """Convenience method to set speaker volume"""
#         return self.set_speaker_output(volume=volume)
    
#     def get_sound_profile(self) -> Dict[str, Any]:
#         """GET /api/audio/soundProfile - Get sound profile"""
#         return self._make_request("GET", "/audio/soundProfile")
    
#     def get_sound_profile_object(self) -> SoundProfileSettings:
#         """Get sound profile as typed object"""
#         response = self.get_sound_profile()
#         return SoundProfileSettings(
#             preset=response.get('preset', 'Wallmount')
#         )
    
#     def set_sound_profile(self, preset: str) -> Dict[str, Any]:
#         """PUT /api/audio/soundProfile - Set sound profile"""
#         valid_presets = ["Wallmount", "CeilingMount", "Custom"]
#         if preset not in valid_presets:
#             raise Exception(f"Invalid preset. Must be one of: {valid_presets}")
#         return self._make_request("PUT", "/audio/soundProfile", data={"preset": preset})
    
#     # ========== Priority Zone Methods ==========
    
#     def get_priority_zones(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/priorityZones - Get all priority zones"""
#         return self._make_request("GET", "/audio/inputs/internalMic/priorityZones")
    
#     def get_priority_zone(self, zone_id: int) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/priorityZones/{id} - Get specific priority zone"""
#         return self._make_request("GET", f"/audio/inputs/internalMic/priorityZones/{zone_id}")
    
#     def set_priority_zone(self, zone_id: int, enabled: bool = None, 
#                       gain: str = None, left: int = None, right: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic/priorityZones/{id} - Set priority zone"""
#         current = self.get_priority_zone(zone_id)
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "gain": gain if gain is not None else current.get('gain', 'Medium'),
#             "left": left if left is not None else current.get('left', 0),
#             "right": right if right is not None else current.get('right', 100)
#         }
#         print(f"📤 Sending priority zone update: {json.dumps(data, indent=2)}")  # Debug line
#         result = self._make_request("PUT", f"/audio/inputs/internalMic/priorityZones/{zone_id}", data=data)
#         print(f"📥 Response: {result}")  # Debug line
#         return result
    
#     def enable_priority_zone(self, zone_id: int) -> Dict[str, Any]:
#         """Enable a priority zone"""
#         return self.set_priority_zone(zone_id, enabled=True)
    
#     def disable_priority_zone(self, zone_id: int) -> Dict[str, Any]:
#         """Disable a priority zone"""
#         return self.set_priority_zone(zone_id, enabled=False)
    
#     # def set_priority_zone_gain(self, zone_id: int, gain) -> Dict[str, Any]:
#     #     """Set priority zone gain - accepts string (Min/Mid/Max) or integer (0-100)"""
#     #     # Handle numeric gain
#     #     if isinstance(gain, int) or (isinstance(gain, str) and gain.isdigit()):
#     #         gain_num = int(gain)
#     #         if 0 <= gain_num <= 100:
#     #             return self.set_priority_zone(zone_id, gain=gain_num)
#     #         else:
#     #             raise Exception("Numeric gain must be between 0 and 100")
        
#     #     # Handle string gain values (TC Bar M uses Min, Mid, Max)
#     #     valid_gains = ["Min", "Mid", "Max", "Off", "Low", "Medium", "High"]
#     #     if gain not in valid_gains:
#     #         raise Exception(f"Invalid gain. Must be: Min, Mid, Max, or numeric 0-100")
#     #     return self.set_priority_zone(zone_id, gain=gain)
#     def set_priority_zone_gain(self, zone_id: int, gain) -> Dict[str, Any]:
#         """Set priority zone gain
        
#         TC Bar M accepts: "Min", "Mid", "Max" or numeric 0-100
#         """
#         # Handle numeric gain
#         if isinstance(gain, int) or (isinstance(gain, str) and gain.isdigit()):
#             gain_num = int(gain)
#             if 0 <= gain_num <= 100:
#                 return self.set_priority_zone(zone_id, gain=gain_num)
#             else:
#                 raise Exception("Numeric gain must be between 0 and 100")
        
#         # For string values, pass directly to API - let it validate
#         # The API expects "Min", "Mid", "Max" (case-sensitive)
#         return self.set_priority_zone(zone_id, gain=gain)
    

#     def set_priority_zone_range(self, zone_id: int, left: int, right: int) -> Dict[str, Any]:
#         """Set priority zone angular range (0-100 representing 0-180°)"""
#         if not 0 <= left <= 100 or not 0 <= right <= 100:
#             raise Exception("Left and right must be between 0 and 100")
#         if left > right:
#             left, right = right, left
#         return self.set_priority_zone(zone_id, left=left, right=right)
    
#     # ========== Exclusion Zone Methods ==========
    
#     def get_exclusion_zones(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/exclusionZones - Get all exclusion zones"""
#         return self._make_request("GET", "/audio/inputs/internalMic/exclusionZones")
    
#     def get_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/exclusionZones/{id} - Get specific exclusion zone"""
#         return self._make_request("GET", f"/audio/inputs/internalMic/exclusionZones/{zone_id}")
    
#     def set_exclusion_zone(self, zone_id: int, enabled: bool = None, 
#                            left: int = None, right: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic/exclusionZones/{id} - Set exclusion zone"""
#         current = self.get_exclusion_zone(zone_id)
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "left": left if left is not None else current.get('left', 0),
#             "right": right if right is not None else current.get('right', 100)
#         }
#         return self._make_request("PUT", f"/audio/inputs/internalMic/exclusionZones/{zone_id}", data=data)
    
#     def enable_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
#         """Enable an exclusion zone"""
#         return self.set_exclusion_zone(zone_id, enabled=True)
    
#     def disable_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
#         """Disable an exclusion zone"""
#         return self.set_exclusion_zone(zone_id, enabled=False)
    
#     def set_exclusion_zone_range(self, zone_id: int, left: int, right: int) -> Dict[str, Any]:
#         """Set exclusion zone angular range (0-100 representing 0-180°)"""
#         if not 0 <= left <= 100 or not 0 <= right <= 100:
#             raise Exception("Left and right must be between 0 and 100")
#         if left > right:
#             left, right = right, left
#         return self.set_exclusion_zone(zone_id, left=left, right=right)
    
#     # ========== Beam Methods ==========
    
#     def get_beam_position(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/beam - Get beam position"""
#         return self._make_request("GET", "/audio/inputs/internalMic/beam")
    
#     def get_beam_position_object(self) -> BeamPosition:
#         """Get beam position as typed object"""
#         response = self.get_beam_position()
#         return BeamPosition(
#             position=response.get('position', 0)
#         )
    
#     # ========== EQ Methods ==========
    
#     def get_internal_mic_custom_eq(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/customEq - Get internal mic custom EQ"""
#         return self._make_request("GET", "/audio/inputs/internalMic/customEq")
    
#     def set_internal_mic_custom_eq(self, eq_values: List[int]) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/internalMic/customEq - Set internal mic custom EQ"""
#         if len(eq_values) != 7:
#             raise Exception("EQ must have exactly 7 values (-12 to 12 dB)")
#         for val in eq_values:
#             if val < -12 or val > 12:
#                 raise Exception("EQ values must be between -12 and 12")
#         return self._make_request("PUT", "/audio/inputs/internalMic/customEq", data=eq_values)
    
#     def get_speaker_custom_eq(self) -> Dict[str, Any]:
#         """GET /api/audio/outputs/speaker/customEq - Get speaker custom EQ"""
#         return self._make_request("GET", "/audio/outputs/speaker/customEq")
    
#     def set_speaker_custom_eq(self, eq_values: List[int]) -> Dict[str, Any]:
#         """PUT /api/audio/outputs/speaker/customEq - Set speaker custom EQ"""
#         if len(eq_values) != 7:
#             raise Exception("EQ must have exactly 7 values (-12 to 12 dB)")
#         for val in eq_values:
#             if val < -12 or val > 12:
#                 raise Exception("EQ values must be between -12 and 12")
#         return self._make_request("PUT", "/audio/outputs/speaker/customEq", data=eq_values)
    
#     # ========== Mixer Methods ==========
    
#     def get_mixer_fade_behavior(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/mixer - Get mixer fade behavior"""
#         return self._make_request("GET", "/audio/inputs/mixer")
    
#     def set_mixer_fade_behavior(self, fade_behavior: str) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/mixer - Set mixer fade behavior"""
#         valid_behaviors = ["Off", "Fast", "Medium", "Slow"]
#         if fade_behavior not in valid_behaviors:
#             raise Exception(f"Invalid fade behavior. Must be one of: {valid_behaviors}")
#         return self._make_request("PUT", "/audio/inputs/mixer", data={"fadeBehavior": fade_behavior})
    
#     def get_active_mic_channel(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/mixer/activity - Get active mic channel"""
#         return self._make_request("GET", "/audio/inputs/mixer/activity")
    
#     # ========== Conference Output Methods ==========
    
#     def get_conference_output(self) -> Dict[str, Any]:
#         """GET /api/audio/outputs/conferenceOutput - Get conference output settings"""
#         return self._make_request("GET", "/audio/outputs/conferenceOutput")
    
#     def get_conference_output_object(self) -> ConferenceOutputSettings:
#         """Get conference output settings as typed object"""
#         response = self.get_conference_output()
#         return ConferenceOutputSettings(
#             far_end_gain=response.get('farEndGain', 0),
#             near_end_gain=response.get('nearEndGain', 0)
#         )
    
#     def set_conference_output(self, far_end_gain: int = None, near_end_gain: int = None) -> Dict[str, Any]:
#         """PUT /api/audio/outputs/conferenceOutput - Set conference output settings"""
#         current = self.get_conference_output()
#         data = {
#             "farEndGain": far_end_gain if far_end_gain is not None else current.get('farEndGain', 0),
#             "nearEndGain": near_end_gain if near_end_gain is not None else current.get('nearEndGain', 0)
#         }
#         if data["farEndGain"] < -18 or data["farEndGain"] > 18:
#             raise Exception("Far end gain must be between -18 and 18 dB")
#         if data["nearEndGain"] < -18 or data["nearEndGain"] > 18:
#             raise Exception("Near end gain must be between -18 and 18 dB")
#         return self._make_request("PUT", "/audio/outputs/conferenceOutput", data=data)
    
#     # ========== Level Monitoring Methods ==========
    
#     def get_internal_mic_level(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/internalMic/level - Get internal mic level"""
#         return self._make_request("GET", "/audio/inputs/internalMic/level")
    
#     def get_bluetooth_input_level(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/bluetooth - Get bluetooth input level"""
#         return self._make_request("GET", "/audio/inputs/bluetooth")
    
#     def get_usb_input_level(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/usb - Get USB input level"""
#         return self._make_request("GET", "/audio/inputs/usb")
    
#     # ========== Camera Methods ==========
    
#     def reset_camera_to_ffov(self) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/ffov - Reset camera to full field of view"""
#         return self._make_request("PUT", "/video/input/internalCamera/ffov")
    
#     def store_camera_preset(self) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/preset/store - Store current camera config"""
#         return self._make_request("PUT", "/video/input/internalCamera/preset/store")
    
#     def load_camera_preset(self) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/preset/load - Load camera preset"""
#         return self._make_request("PUT", "/video/input/internalCamera/preset/load")
    
#     def get_camera_ai_access(self) -> Dict[str, Any]:
#         """GET /api/video/input/internalCamera/aiAccess - Get auto framing and person tiling status"""
#         return self._make_request("GET", "/video/input/internalCamera/aiAccess")
    
#     def get_camera_ai_access_object(self) -> CameraAIAccess:
#         """Get camera AI access as typed object"""
#         response = self.get_camera_ai_access()
#         return CameraAIAccess(
#             auto_framing_access_enabled=response.get('autoFramingAccessEnabled', False),
#             auto_framing_enabled=response.get('autoFramingEnabled', False),
#             person_tiling_access_enabled=response.get('personTilingAccessEnabled', False),
#             person_tiling_enabled=response.get('personTilingEnabled', False)
#         )
    
#     def set_camera_ai_access(self, auto_framing_access: bool = None, 
#                               auto_framing: bool = None,
#                               person_tiling_access: bool = None,
#                               person_tiling: bool = None) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/aiAccess - Set auto framing and person tiling"""
#         current = self.get_camera_ai_access()
#         data = {
#             "autoFramingAccessEnabled": auto_framing_access if auto_framing_access is not None 
#                                         else current.get('autoFramingAccessEnabled', False),
#             "autoFramingEnabled": auto_framing if auto_framing is not None 
#                                  else current.get('autoFramingEnabled', False),
#             "personTilingAccessEnabled": person_tiling_access if person_tiling_access is not None 
#                                         else current.get('personTilingAccessEnabled', False),
#             "personTilingEnabled": person_tiling if person_tiling is not None 
#                                   else current.get('personTilingEnabled', False)
#         }
#         return self._make_request("PUT", "/video/input/internalCamera/aiAccess", data=data)
    
#     def move_camera_relative(self, up: int = 0, down: int = 0, left: int = 0, 
#                               right: int = 0, zoom_in: int = 0, zoom_out: int = 0) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/movement/relative - Move camera relatively"""
#         if (zoom_in > 0 and zoom_out > 0):
#             raise Exception("Cannot specify both zoom_in and zoom_out")
#         data = {
#             "up": up, "down": down, "left": left, "right": right,
#             "zoomIn": zoom_in, "zoomOut": zoom_out
#         }
#         return self._make_request("PUT", "/video/input/internalCamera/movement/relative", data=data)
    
#     def get_camera_video_parameters(self) -> Dict[str, Any]:
#         """GET /api/video/input/internalCamera/videoParameters - Get video parameters"""
#         return self._make_request("GET", "/video/input/internalCamera/videoParameters")
    
#     def get_camera_video_parameters_object(self) -> CameraVideoParameters:
#         """Get camera video parameters as typed object"""
#         response = self.get_camera_video_parameters()
#         return CameraVideoParameters(
#             compensation=response.get('compensation', 'Backlight'),
#             anti_flicker_frequency=response.get('antiFlickerFrequency', 'Auto'),
#             brightness=response.get('brightness', 0),
#             contrast=response.get('contrast', 5),
#             saturation=response.get('saturation', 5),
#             sharpness=response.get('sharpness', 2),
#             auto_whitebalance_enabled=response.get('autoWhitebalanceEnabled', True),
#             whitebalance=response.get('whitebalance', 4600),
#             default_camera_mode=response.get('defaultCameraMode', 'ResumeLastView')
#         )
    
#     def get_camera_movement(self) -> Dict[str, Any]:
#         """GET /api/video/input/internalCamera/movement - Get camera movement settings"""
#         return self._make_request("GET", "/video/input/internalCamera/movement")
    
#     def get_camera_movement_object(self) -> CameraMovementSettings:
#         """Get camera movement settings as typed object"""
#         response = self.get_camera_movement()
#         return CameraMovementSettings(
#             pan_position=response.get('panPosition', 0),
#             tilt_position=response.get('tiltPosition', 0),
#             zoom_position=response.get('zoomPosition', 100),
#             zoom_speed=response.get('zoomSpeed', 'Medium'),
#             pan_tilt_speed=response.get('panTiltSpeed', 'Medium'),
#             auto_framing_speed=response.get('autoFramingSpeed', 'Medium')
#         )
    
#     def set_camera_movement(self, pan_position: int = None, tilt_position: int = None,
#                              zoom_position: int = None, zoom_speed: str = None,
#                              pan_tilt_speed: str = None, auto_framing_speed: str = None) -> Dict[str, Any]:
#         """PUT /api/video/input/internalCamera/movement - Set camera movement"""
#         current = self.get_camera_movement()
#         data = {
#             "panPosition": pan_position if pan_position is not None else current.get('panPosition', 0),
#             "tiltPosition": tilt_position if tilt_position is not None else current.get('tiltPosition', 0),
#             "zoomPosition": zoom_position if zoom_position is not None else current.get('zoomPosition', 100),
#             "zoomSpeed": zoom_speed if zoom_speed is not None else current.get('zoomSpeed', 'Medium'),
#             "panTiltSpeed": pan_tilt_speed if pan_tilt_speed is not None else current.get('panTiltSpeed', 'Medium'),
#             "autoFramingSpeed": auto_framing_speed if auto_framing_speed is not None 
#                                else current.get('autoFramingSpeed', 'Medium')
#         }
#         return self._make_request("PUT", "/video/input/internalCamera/movement", data=data)
    
#     def get_camera_status(self) -> Dict[str, Any]:
#         """GET /api/video/input/internalCamera - Get camera status"""
#         return self._make_request("GET", "/video/input/internalCamera")
    
#     def get_hdmi_enabled(self) -> Dict[str, Any]:
#         """GET /api/video/output/hdmi - Get HDMI enabled status"""
#         return self._make_request("GET", "/video/output/hdmi")
    
#     def set_hdmi_enabled(self, enabled: bool) -> Dict[str, Any]:
#         """PUT /api/video/output/hdmi - Set HDMI enabled status"""
#         return self._make_request("PUT", "/video/output/hdmi", data={"enabled": enabled})
    
#     # ========== Network Methods ==========
    
#     def get_network_interfaces(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network - Get all network interfaces"""
#         return self._make_request("GET", "/interfaces/network")
    
#     def get_dante_status(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network/dante - Get Dante interface status"""
#         return self._make_request("GET", "/interfaces/network/dante")
    
#     def get_dante_settings(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network/dante/settings - Get Dante settings"""
#         return self._make_request("GET", "/interfaces/network/dante/settings")
    
#     def set_dante_settings(self, continuous_stream: bool = None, 
#                             speaker_output: bool = None) -> Dict[str, Any]:
#         """PUT /api/interfaces/network/dante/settings - Set Dante settings"""
#         current = self.get_dante_settings()
#         data = {
#             "continuousDanteStream": continuous_stream if continuous_stream is not None 
#                                     else current.get('continuousDanteStream', False),
#             "danteSpeakerOutput": speaker_output if speaker_output is not None 
#                                  else current.get('danteSpeakerOutput', False)
#         }
#         return self._make_request("PUT", "/interfaces/network/dante/settings", data=data)
    
#     def get_dante_input_levels(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/dante/levels - Get Dante audio levels"""
#         return self._make_request("GET", "/audio/inputs/dante/levels")
    
#     def get_dante_input_level(self, channel_id: int) -> Dict[str, Any]:
#         """GET /api/audio/inputs/dante/{id}/level - Get specific Dante channel level"""
#         return self._make_request("GET", f"/audio/inputs/dante/{channel_id}/level")
    
#     def get_dante_inputs(self) -> Dict[str, Any]:
#         """GET /api/audio/inputs/dante - Get Dante input parameters"""
#         return self._make_request("GET", "/audio/inputs/dante")
    
#     def get_dante_input(self, channel_id: int) -> Dict[str, Any]:
#         """GET /api/audio/inputs/dante/{id} - Get specific Dante input"""
#         return self._make_request("GET", f"/audio/inputs/dante/{channel_id}")
    
#     def set_dante_input_gain(self, channel_id: int, gain: int) -> Dict[str, Any]:
#         """PUT /api/audio/inputs/dante/{id} - Set Dante input gain"""
#         if gain < -30 or gain > 30:
#             raise Exception("Gain must be between -30 and 30 dB")
#         return self._make_request("PUT", f"/audio/inputs/dante/{channel_id}", data={"gain": gain})
    
#     def get_port_configuration(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network/portConfiguration - Get port configuration"""
#         return self._make_request("GET", "/interfaces/network/portConfiguration")
    
#     def get_port_configuration_object(self) -> PortConfiguration:
#         """Get port configuration as typed object"""
#         response = self.get_port_configuration()
#         return PortConfiguration(
#             configuration=response.get('configuration', 'Split')
#         )
    
#     # ========== Bluetooth Methods ==========
    
#     def get_bluetooth_settings(self) -> Dict[str, Any]:
#         """GET /api/interfaces/bluetooth - Get Bluetooth settings"""
#         return self._make_request("GET", "/interfaces/bluetooth")
    
#     def get_bluetooth_settings_object(self) -> BluetoothSettings:
#         """Get Bluetooth settings as typed object"""
#         response = self.get_bluetooth_settings()
#         return BluetoothSettings(
#             enabled=response.get('enabled', False),
#             pairing=response.get('pairing', False),
#             mac=response.get('mac', '00:00:00:00:00:00')
#         )
    
#     def set_bluetooth_settings(self, enabled: bool = None, pairing: bool = None) -> Dict[str, Any]:
#         """PUT /api/interfaces/bluetooth - Set Bluetooth settings"""
#         current = self.get_bluetooth_settings()
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "pairing": pairing if pairing is not None else current.get('pairing', False)
#         }
#         return self._make_request("PUT", "/interfaces/bluetooth", data=data)
    
#     def get_bluetooth_devices_list(self) -> Dict[str, Any]:
#         """GET /api/interfaces/bluetooth/devicesList - Get list of known Bluetooth devices"""
#         return self._make_request("GET", "/interfaces/bluetooth/devicesList")
    
#     # ========== WiFi Methods ==========
    
#     def get_wifi_status(self) -> Dict[str, Any]:
#         """GET /api/interfaces/network/wifi - Get WiFi status"""
#         return self._make_request("GET", "/interfaces/network/wifi")
    
#     def get_wifi_status_object(self) -> WifiStatus:
#         """Get WiFi status as typed object"""
#         response = self.get_wifi_status()
#         return WifiStatus(
#             enabled=response.get('enabled', False),
#             state=response.get('state', 'Disconnected'),
#             connection=response.get('connection', {})
#         )
    
#     # ========== Firmware Update Methods ==========
    
#     def get_firmware_update_state(self) -> Dict[str, Any]:
#         """GET /api/firmware/update/state - Get firmware update state"""
#         return self._make_request("GET", "/firmware/update/state")
    
#     def get_firmware_state_object(self) -> FirmwareUpdateState:
#         """Get firmware update state as typed object"""
#         response = self.get_firmware_update_state()
#         return FirmwareUpdateState(
#             device_version=response.get('deviceVersion', 'Unknown'),
#             state=response.get('state', 'Idle'),
#             progress=response.get('progress', 0),
#             last_status=response.get('lastStatus', 'None')
#         )
    
#     def is_firmware_updating(self) -> bool:
#         """Check if firmware update is in progress"""
#         state = self.get_firmware_update_state()
#         update_state = state.get('state', 'Idle')
#         return update_state in ['Downloading', 'Updating', 'Rebooting']
    
#     def get_firmware_progress(self) -> int:
#         """Get firmware update progress percentage"""
#         state = self.get_firmware_update_state()
#         return state.get('progress', 0)
    
#     # ========== SSC Methods ==========
    
#     def get_ssc_version(self) -> Dict[str, Any]:
#         """GET /api/ssc/version - Get schema version"""
#         return self._make_request("GET", "/ssc/version")
    
#     def get_ssc_schema(self) -> Dict[str, Any]:
#         """GET /api/ssc/schema - Get address tree"""
#         return self._make_request("GET", "/ssc/schema")
    
#     # ========== Real-time Monitoring ==========
    
#     def get_all_metrics(self) -> DeviceMetrics:
#         """Get all current device metrics"""
#         mic_level = self.get_internal_mic_level()
#         mute = self.get_mic_mute()
#         beam = self.get_beam_position()
#         active = self.get_active_mic_channel()
#         speaker = self.get_speaker_output()
#         usb_level = self.get_usb_input_level()
#         bt_level = self.get_bluetooth_input_level()
        
#         return DeviceMetrics(
#             timestamp=datetime.now(),
#             microphone_level=mic_level.get('peak', 0) if isinstance(mic_level, dict) else 0,
#             mute_status=mute.get('enabled') if isinstance(mute, dict) else None,
#             beam_position=beam.get('position', 0) if isinstance(beam, dict) else 0,
#             active_channel=active.get('activeChannel', 'Unknown') if isinstance(active, dict) else 'Unknown',
#             speaker_volume=speaker.get('volume', 50) if isinstance(speaker, dict) else 50,
#             usb_input_level=usb_level.get('level', 0) if isinstance(usb_level, dict) else 0,
#             bluetooth_input_level=bt_level.get('level', 0) if isinstance(bt_level, dict) else 0
#         )
    
#     def start_monitoring(self, interval: float = 1.0, callback: Optional[Callable] = None):
#         """Start continuous monitoring"""
#         if callback:
#             self.callbacks.append(callback)
        
#         if not self.monitoring:
#             self.monitoring = True
#             self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
#             self.monitor_thread.daemon = True
#             self.monitor_thread.start()
#             print(f"✅ Monitoring started (interval: {interval}s)")
    
#     def stop_monitoring(self):
#         """Stop continuous monitoring"""
#         self.monitoring = False
#         if self.monitor_thread:
#             self.monitor_thread.join(timeout=2)
#         print("✅ Monitoring stopped")
    
#     def _monitor_loop(self, interval: float):
#         """Background monitoring loop"""
#         while self.monitoring:
#             try:
#                 metrics = self.get_all_metrics()
#                 self.metrics_history.append(metrics)
                
#                 if len(self.metrics_history) > 1000:
#                     self.metrics_history = self.metrics_history[-1000:]
                
#                 for callback in self.callbacks:
#                     try:
#                         callback(metrics)
#                     except Exception as e:
#                         print(f"Callback error: {e}")
                
#                 time.sleep(interval)
#             except Exception as e:
#                 print(f"Monitoring error: {e}")
#                 time.sleep(interval)
    
#     def get_metrics_history(self, last_n: int = 100) -> List[DeviceMetrics]:
#         """Get historical metrics"""
#         return self.metrics_history[-last_n:] if self.metrics_history else []
    
#     def get_complete_device_info(self) -> Dict[str, Any]:
#         """Get all device information"""
#         identity = self.get_device_identity()
#         firmware = self.get_firmware_update_state()
#         state = self.get_device_state()
#         led = self.get_led_ring()
#         site = self.get_device_site()
#         beam = self.get_beam_position()
#         mic = self.get_internal_mic()
#         speaker = self.get_speaker_output()
#         noise_gate = self.get_noise_gate()
#         noise_suppression = self.get_noise_suppression()
#         sound_profile = self.get_sound_profile()
#         camera_ai = self.get_camera_ai_access()
#         camera_video = self.get_camera_video_parameters()
#         network = self.get_network_interfaces()
#         bluetooth = self.get_bluetooth_settings()
#         wifi = self.get_wifi_status()
#         priority_zones = self.get_priority_zones()
#         exclusion_zones = self.get_exclusion_zones()
        
#         return {
#             "identity": identity,
#             "firmware": firmware,
#             "state": state,
#             "led_settings": led,
#             "site_info": site,
#             "beam_position": beam,
#             "microphone": mic,
#             "speaker": speaker,
#             "noise_gate": noise_gate,
#             "noise_suppression": noise_suppression,
#             "sound_profile": sound_profile,
#             "camera": {
#                 "ai_access": camera_ai,
#                 "video_parameters": camera_video
#             },
#             "network": network,
#             "bluetooth": bluetooth,
#             "wifi": wifi,
#             "priority_zones": priority_zones,
#             "exclusion_zones": exclusion_zones,
#             "timestamp": datetime.now().isoformat(),
#             "ip": self.device_ip
#         }


# # ========== Interactive Controller ==========

# class SennheiserTCBarMController:
#     """Interactive controller for TeamConnect Bar M"""
    
#     def __init__(self, device_ip: str, username: str, password: str):
#         self.device = SennheiserTCBarMPlugin(device_ip, username, password)
#         self.monitoring_active = False
#         self.device_ip = device_ip
    
#     def display_metrics(self, metrics: DeviceMetrics):
#         """Display real-time metrics"""
#         mute_display = "🔴 MUTED" if metrics.mute_status else "🟢 LIVE"
#         print(f"\r📊 [{metrics.timestamp.strftime('%H:%M:%S')}] "
#               f"Mic: {metrics.microphone_level}dB | "
#               f"Beam: {metrics.beam_position}° | "
#               f"Volume: {metrics.speaker_volume}% | "
#               f"Active: {metrics.active_channel} | "
#               f"Mute: {mute_display}", end="")
    
#     def run_interactive_menu(self):
#         """Run interactive control menu"""
#         while True:
#             print("\n" + "=" * 70)
#             print(f" SENNHEISER TEAMCONNECT BAR M - COMPLETE CONTROL SYSTEM ({self.device_ip})")
#             print("=" * 70)
#             print("\n📊 CURRENT STATUS:")
            
#             try:
#                 metrics = self.device.get_all_metrics()
#                 identity = self.device.get_device_identity()
#                 state = self.device.get_device_state()
#                 site = self.device.get_device_site()
#                 mic = self.device.get_internal_mic()
#                 speaker = self.device.get_speaker_output()
#                 noise_gate = self.device.get_noise_gate()
#                 noise_suppression = self.device.get_noise_suppression()
#                 beam = self.device.get_beam_position()
#                 camera_ai = self.device.get_camera_ai_access()
#                 firmware = self.device.get_firmware_state_object()
                
#                 print(f"\n📱 DEVICE: {identity.get('product', 'TC Bar M')}")
#                 print(f"   Serial: {identity.get('serial', 'Unknown')}")
#                 print(f"   State: {state.get('state', 'Unknown')}")
#                 print(f"   Firmware: {firmware.device_version}")
                
#                 print(f"\n📍 SITE:")
#                 print(f"   Name: {site.get('deviceName', 'Unknown')}")
#                 print(f"   Location: {site.get('location', 'Unknown')}")
                
#                 print(f"\n🎤 AUDIO:")
#                 print(f"   Mic Level: {metrics.microphone_level} dB")
#                 print(f"   Mic Enabled: {'✅' if mic.get('enabled') else '❌'}")
#                 print(f"   Mic Gain: {mic.get('gain', 0)} dB")
#                 mute_display = "🔴 MUTED" if metrics.mute_status else "🟢 LIVE"
#                 print(f"   Mute Status: {mute_display}")
#                 print(f"   Speaker Volume: {speaker.get('volume', 50)}%")
#                 print(f"   Active Channel: {metrics.active_channel}")
                
#                 print(f"\n🎯 BEAMFORMING:")
#                 print(f"   Beam Position: {beam.get('position', 0)}°")
                
#                 print(f"\n🔧 PROCESSING:")
#                 print(f"   Noise Gate: {'✅' if noise_gate.get('enabled') else '❌'}")
#                 print(f"   Noise Suppression: {noise_suppression.get('weighting', 'Medium')}")
                
#                 print(f"\n📷 CAMERA:")
#                 print(f"   Auto Framing: {'✅' if camera_ai.get('autoFramingEnabled') else '❌'}")
#                 print(f"   Person Tiling: {'✅' if camera_ai.get('personTilingEnabled') else '❌'}")
                
#             except Exception as e:
#                 print(f"   ⚠️ Error getting status: {e}")
            
#             print("\n" + "=" * 70)
#             print("🎮 CONTROL COMMANDS:")
            
#             print("\n📢 AUDIO CONTROLS:")
#             print("  mute on/off           - Mute/Unmute microphone")
#             print("  volume <0-100>        - Set speaker volume")
#             print("  volume up/down        - Increase/Decrease volume")
#             print("  mic gain <-30-30>     - Set microphone gain")
#             print("  mic enable/disable    - Enable/Disable microphone")
            
#             print("\n🎛️ PROCESSING:")
#             print("  noisegate on/off      - Enable/Disable noise gate")
#             print("  noisegate <thresh> <hold> <range> - Set noise gate params")
#             print("  suppress <off/low/medium/high> - Set noise suppression")
            
#             print("\n🎯 BEAMFORMING:")
#             print("  beam status           - Show beam position")
            
#             print("\n📷 CAMERA CONTROLS:")
#             print("  camera ai on/off      - Enable/Disable auto framing")
#             print("  camera tiling on/off  - Enable/Disable person tiling")
#             print("  camera ffov           - Reset to full field of view")
#             print("  camera preset store   - Store current camera preset")
#             print("  camera preset load    - Load camera preset")
#             print("  camera move <up/down/left/right> <steps> - Move camera")
#             print("  camera zoom in/out    - Zoom camera")
#             print("  hdmi status           - Show HDMI output status")
#             print("  hdmi on/off           - Enable/Disable HDMI output")
            
#             print("\n🎯 ZONE CONTROLS (Priority Zones):")
#             print("  priority list         - List all priority zones")
#             print("  priority get <id>     - Get priority zone (shows valid gain values)")
#             print("  priority on <id>      - Enable priority zone")
#             print("  priority off <id>     - Disable priority zone")
#             print("  priority gain <id> <value> - Set gain (Min/Mid/Max or 0-100)")
#             print("  priority range <id> <left> <right> - Set angular range (0-100)")

#             print("\n🚫 ZONE CONTROLS (Exclusion Zones):")
#             print("  exclude list          - List all exclusion zones")
#             print("  exclude get <id>      - Get exclusion zone (use IDs from list)")
#             print("  exclude on <id>       - Enable exclusion zone")
#             print("  exclude off <id>      - Disable exclusion zone")
#             print("  exclude range <id> <left> <right> - Set angular range (0-100)")
            
#             print("\n💡 LED CONTROLS:")
#             print("  led bright <0-5>      - Set LED brightness")
#             print("  led status            - Show LED settings")
            
#             print("\n🌐 NETWORK:")
#             print("  network status        - Show network interfaces")
#             print("  dante status          - Show Dante status")
#             print("  bluetooth on/off      - Enable/Disable Bluetooth")
#             print("  wifi status           - Show WiFi status")
            
#             print("\n🔧 DEVICE:")
#             print("  site name <name>      - Set device name")
#             print("  site location <loc>   - Set location")
#             print("  sound prompts on/off  - Enable/Disable sound prompts")
#             print("  identify on/off       - Identify device (blink LEDs)")
#             print("  restart               - Restart device")
#             print("  check profile         - Check current device profile")
#             print("  test permissions      - Test API read/write permissions")
#             print("  profile <custom/teams> - Set device profile")
            
#             print("\n📊 MONITORING:")
#             print("  status                - Show detailed status")
#             print("  firmware              - Show firmware status")
#             print("  monitor               - Start real-time monitoring")
#             print("  stop                  - Stop monitoring")
#             print("  info                  - Complete device info")
#             print("  exit                  - Exit")
#             print("=" * 70)
            
#             cmd = input("\n👉 Enter command: ").strip().lower()
            
#             try:
#                 if cmd == "exit":
#                     if self.monitoring_active:
#                         self.device.stop_monitoring()
#                     print("👋 Goodbye!")
#                     break

#                 # ========== Profile Commands ==========
#                 elif cmd == "check profile":
#                     try:
#                         profile = self.device.get_device_profile()
#                         print(f"📱 Current Device Profile: {profile.get('configuration', 'Unknown')}")
#                         if profile.get('configuration') == 'MicrosoftTeams':
#                             print("   ⚠️ WARNING: Microsoft Teams profile active!")
#                             print("   This restricts: HDMI control, camera parameters, and some audio settings")
#                             print("   Try: profile custom")
#                         else:
#                             print("   ✅ Custom profile active - Full control available")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")

#                 elif cmd == "test permissions":
#                     print("\n🔐 TESTING API PERMISSIONS:")
#                     try:
#                         identity = self.device.get_device_identity()
#                         print("   ✅ GET /device/identity - READ permission: OK")
#                     except Exception as e:
#                         print(f"   ❌ READ test failed: {e}")
                    
#                     try:
#                         current_led = self.device.get_led_ring()
#                         current_brightness = current_led.get('brightness', 3)
#                         self.device.set_led_brightness(current_brightness)
#                         print("   ✅ PUT /device/leds/ring - WRITE permission: OK")
#                     except Exception as e:
#                         print(f"   ❌ LED write test failed: {e}")
                    
#                     try:
#                         profile = self.device.get_device_profile()
#                         print(f"   📱 Device Profile: {profile.get('configuration')}")
#                     except Exception as e:
#                         print(f"   ❌ Profile check failed: {e}")
                
#                 # ========== Audio Commands ==========
#                 elif cmd == "mute on":
#                     self.device.mute()
#                     print("✅ Microphone MUTED")
                
#                 elif cmd == "mute off":
#                     self.device.unmute()
#                     print("✅ Microphone UNMUTED")
                
#                 elif cmd.startswith("volume "):
#                     parts = cmd.split()
#                     if len(parts) == 2:
#                         try:
#                             volume = int(parts[1])
#                             if 0 <= volume <= 100:
#                                 self.device.set_volume(volume)
#                                 print(f"✅ Volume set to {volume}%")
#                             else:
#                                 print("❌ Volume must be between 0 and 100")
#                         except ValueError:
#                             print("❌ Invalid volume value")
#                     else:
#                         print("❌ Usage: volume <0-100>")
                
#                 elif cmd == "volume up":
#                     current = self.device.get_speaker_output()
#                     current_volume = current.get('volume', 50)
#                     new_volume = min(100, current_volume + 5)
#                     self.device.set_volume(new_volume)
#                     print(f"✅ Volume increased to {new_volume}%")
                
#                 elif cmd == "volume down":
#                     current = self.device.get_speaker_output()
#                     current_volume = current.get('volume', 50)
#                     new_volume = max(0, current_volume - 5)
#                     self.device.set_volume(new_volume)
#                     print(f"✅ Volume decreased to {new_volume}%")
                
#                 elif cmd.startswith("mic gain"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             gain = int(parts[2])
#                             if -30 <= gain <= 30:
#                                 self.device.set_internal_mic(gain=gain)
#                                 print(f"✅ Mic gain set to {gain} dB")
#                             else:
#                                 print("❌ Gain must be between -30 and 30")
#                         except ValueError:
#                             print("❌ Invalid gain value")
#                     else:
#                         print("❌ Usage: mic gain <-30 to 30>")
                
#                 elif cmd == "mic enable":
#                     self.device.set_internal_mic(enabled=True)
#                     print("✅ Microphone ENABLED")
                
#                 elif cmd == "mic disable":
#                     self.device.set_internal_mic(enabled=False)
#                     print("✅ Microphone DISABLED")
                
#                 # ========== HDMI Commands ==========
#                 elif cmd == "hdmi status":
#                     try:
#                         hdmi = self.device.get_hdmi_enabled()
#                         status = "✅ ENABLED" if hdmi.get('enabled') else "❌ DISABLED"
#                         print(f"📺 HDMI Output: {status}")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 elif cmd == "hdmi on":
#                     try:
#                         self.device.set_hdmi_enabled(True)
#                         print("✅ HDMI Output ENABLED")
#                         time.sleep(0.5)
#                         hdmi = self.device.get_hdmi_enabled()
#                         if hdmi.get('enabled'):
#                             print("   Verified: HDMI is now active")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 elif cmd == "hdmi off":
#                     try:
#                         self.device.set_hdmi_enabled(False)
#                         print("✅ HDMI Output DISABLED")
#                         time.sleep(0.5)
#                         hdmi = self.device.get_hdmi_enabled()
#                         if not hdmi.get('enabled'):
#                             print("   Verified: HDMI is now inactive")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 # ========== Processing Commands ==========
#                 elif cmd == "noisegate on":
#                     self.device.set_noise_gate(enabled=True)
#                     print("✅ Noise gate ENABLED")
                
#                 elif cmd == "noisegate off":
#                     self.device.set_noise_gate(enabled=False)
#                     print("✅ Noise gate DISABLED")
                
#                 elif cmd.startswith("noisegate "):
#                     parts = cmd.split()
#                     if len(parts) == 4:
#                         try:
#                             threshold = int(parts[1])
#                             hold = int(parts[2])
#                             range_val = int(parts[3])
#                             self.device.set_noise_gate(enabled=True, threshold=threshold, 
#                                                         hold_time=hold, range_val=range_val)
#                             print(f"✅ Noise gate set: threshold={threshold}dB, hold={hold}ms, range={range_val}dB")
#                         except ValueError:
#                             print("❌ Invalid values")
#                     else:
#                         print("❌ Usage: noisegate <threshold -80 to -20> <hold 100-2000> <range -80 to 0>")
                
#                 elif cmd.startswith("suppress"):
#                     parts = cmd.split()
#                     if len(parts) == 2:
#                         weighting = parts[1].capitalize()
#                         self.device.set_noise_suppression(weighting)
#                         print(f"✅ Noise suppression set to {weighting}")
#                     else:
#                         print("❌ Usage: suppress <off/low/medium/high>")
                
#                 # ========== Beam Commands ==========
#                 elif cmd == "beam status":
#                     beam = self.device.get_beam_position()
#                     print(f"🎯 Beam Position: {beam.get('position', 0)}°")
                
#                 # ========== Priority Zone Commands ==========
#                 elif cmd == "priority list":
#                     try:
#                         zones = self.device.get_priority_zones()
#                         print("\n🎯 PRIORITY ZONES:")
#                         print("-" * 60)
#                         if not zones:
#                             print("   No priority zones configured")
#                         else:
#                             for zone in zones:
#                                 status = "✅ ACTIVE" if zone.get('active') else "⭕ INACTIVE"
#                                 enabled = "🔵 ENABLED" if zone.get('enabled') else "⚪ DISABLED"
#                                 print(f"Zone {zone.get('id')}: {status} | {enabled}")
#                                 print(f"   Gain: {zone.get('gain', 'Medium')}")
#                                 print(f"   Range: {zone.get('left', 0)}° - {zone.get('right', 100)}°")
#                                 print("-" * 40)
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 elif cmd.startswith("priority get"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             # First get all zones to validate ID exists
#                             zones = self.device.get_priority_zones()
#                             zone_ids = [z.get('id') for z in zones]
                            
#                             if zone_id in zone_ids:
#                                 zone = self.device.get_priority_zone(zone_id)
#                                 print(f"\n🎯 PRIORITY ZONE {zone_id}:")
#                                 print(f"   Active: {zone.get('active', False)}")
#                                 print(f"   Enabled: {zone.get('enabled', False)}")
#                                 print(f"   Gain: {zone.get('gain', 'Medium')}")
#                                 print(f"   Left Range: {zone.get('left', 0)}°")
#                                 print(f"   Right Range: {zone.get('right', 100)}°")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: priority get <zone_id>")
                
#                 elif cmd.startswith("priority on"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             # First get all zones to validate ID exists
#                             zones = self.device.get_priority_zones()
#                             zone_ids = [z.get('id') for z in zones]
                            
#                             if zone_id in zone_ids:
#                                 self.device.enable_priority_zone(zone_id)
#                                 print(f"✅ Priority zone {zone_id} ENABLED")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: priority on <zone_id>")
                
#                 elif cmd.startswith("priority off"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_priority_zones()
#                             zone_ids = [z.get('id') for z in zones]
                            
#                             if zone_id in zone_ids:
#                                 self.device.disable_priority_zone(zone_id)
#                                 print(f"✅ Priority zone {zone_id} DISABLED")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: priority off <zone_id>")
                
#                 elif cmd.startswith("priority gain"):
#                     parts = cmd.split()
#                     if len(parts) == 4:
#                         try:
#                             zone_id = int(parts[2])
#                             gain = parts[3].capitalize()  # Capitalize first letter for Min/Mid/Max
                            
#                             # First, get a zone to discover valid gain values
#                             zones = self.device.get_priority_zones()
#                             zone_ids = [z.get('id') for z in zones]
                            
#                             if zone_id in zone_ids:
#                                 # Try to get the current zone to see what gain values look like
#                                 current_zone = self.device.get_priority_zone(zone_id)
#                                 current_gain = current_zone.get('gain', '')
                                
#                                 # Define possible gain values (update these based on your device)
#                                 valid_gains = ["Min", "Mid", "Max", "Off", "Low", "Medium", "High"]
                                
#                                 # Also try numeric values
#                                 try:
#                                     gain_num = int(gain)
#                                     if 0 <= gain_num <= 100:
#                                         self.device.set_priority_zone_gain(zone_id, gain_num)
#                                         print(f"✅ Priority zone {zone_id} gain set to {gain_num}")
#                                     else:
#                                         print(f"❌ Gain must be between 0 and 100")
#                                 except ValueError:
#                                     # Not a number, check string options
#                                     if gain in valid_gains:
#                                         self.device.set_priority_zone_gain(zone_id, gain)
#                                         print(f"✅ Priority zone {zone_id} gain set to {gain}")
#                                     else:
#                                         print(f"❌ Invalid gain. Current zone {zone_id} uses: {current_gain}")
#                                         print(f"   Try: Min, Mid, Max, or numeric 0-100")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: priority gain <zone_id> <Min/Mid/Max or 0-100>")
                
#                 # ========== Exclusion Zone Commands ==========
#                 elif cmd == "exclude list":
#                     try:
#                         zones = self.device.get_exclusion_zones()
#                         print("\n🚫 EXCLUSION ZONES:")
#                         print("-" * 60)
#                         if not zones:
#                             print("   No exclusion zones configured")
#                         else:
#                             for zone in zones:
#                                 status = "✅ ACTIVE" if zone.get('active') else "⭕ INACTIVE"
#                                 enabled = "🔵 ENABLED" if zone.get('enabled') else "⚪ DISABLED"
#                                 print(f"Zone {zone.get('id')}: {status} | {enabled}")
#                                 print(f"   Range: {zone.get('left', 0)}° - {zone.get('right', 100)}°")
#                                 print("-" * 40)
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 elif cmd.startswith("exclude get"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_exclusion_zones()
#                             zone_ids = [z.get('id') for z in zones]
                            
#                             if zone_id in zone_ids:
#                                 zone = self.device.get_exclusion_zone(zone_id)
#                                 print(f"\n🚫 EXCLUSION ZONE {zone_id}:")
#                                 print(f"   Active: {zone.get('active', False)}")
#                                 print(f"   Enabled: {zone.get('enabled', False)}")
#                                 print(f"   Left Range: {zone.get('left', 0)}°")
#                                 print(f"   Right Range: {zone.get('right', 100)}°")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: exclude get <zone_id>")
                
#                 elif cmd.startswith("exclude on"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_exclusion_zones()
#                             zone_ids = [z.get('id') for z in zones]
                            
#                             if zone_id in zone_ids:
#                                 self.device.enable_exclusion_zone(zone_id)
#                                 print(f"✅ Exclusion zone {zone_id} ENABLED")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: exclude on <zone_id>")
                
#                 elif cmd.startswith("exclude off"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_exclusion_zones()
#                             zone_ids = [z.get('id') for z in zones]
                            
#                             if zone_id in zone_ids:
#                                 self.device.disable_exclusion_zone(zone_id)
#                                 print(f"✅ Exclusion zone {zone_id} DISABLED")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: exclude off <zone_id>")
                
#                 elif cmd.startswith("exclude range"):
#                     parts = cmd.split()
#                     if len(parts) == 5:
#                         try:
#                             zone_id = int(parts[2])
#                             left = int(parts[3])
#                             right = int(parts[4])
#                             zones = self.device.get_exclusion_zones()
#                             zone_ids = [z.get('id') for z in zones]
                            
#                             if zone_id in zone_ids and 0 <= left <= 100 and 0 <= right <= 100:
#                                 self.device.set_exclusion_zone_range(zone_id, left, right)
#                                 print(f"✅ Exclusion zone {zone_id} range set to {left}° - {right}°")
#                             else:
#                                 if zone_id not in zone_ids:
#                                     print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                                 if not (0 <= left <= 100 and 0 <= right <= 100):
#                                     print("❌ Range values must be between 0 and 100")
#                         except ValueError:
#                             print("❌ Invalid numbers")
#                     else:
#                         print("❌ Usage: exclude range <zone_id> <left 0-100> <right 0-100>")
                
#                 # ========== Camera Commands ==========
#                 elif cmd == "camera ai on":
#                     self.device.set_camera_ai_access(auto_framing=True)
#                     print("✅ Auto framing ENABLED")
                
#                 elif cmd == "camera ai off":
#                     self.device.set_camera_ai_access(auto_framing=False)
#                     print("✅ Auto framing DISABLED")
                
#                 elif cmd == "camera tiling on":
#                     self.device.set_camera_ai_access(person_tiling=True)
#                     print("✅ Person tiling ENABLED")
                
#                 elif cmd == "camera tiling off":
#                     self.device.set_camera_ai_access(person_tiling=False)
#                     print("✅ Person tiling DISABLED")
                
#                 elif cmd == "camera ffov":
#                     self.device.reset_camera_to_ffov()
#                     print("✅ Camera reset to full field of view")
                
#                 elif cmd == "camera preset store":
#                     self.device.store_camera_preset()
#                     print("✅ Camera preset STORED")
                
#                 elif cmd == "camera preset load":
#                     self.device.load_camera_preset()
#                     print("✅ Camera preset LOADED")
                
#                 elif cmd == "camera zoom in":
#                     self.device.move_camera_relative(zoom_in=1)
#                     print("✅ Zoom IN")
                
#                 elif cmd == "camera zoom out":
#                     self.device.move_camera_relative(zoom_out=1)
#                     print("✅ Zoom OUT")
                
#                 elif cmd.startswith("camera move"):
#                     parts = cmd.split()
#                     if len(parts) >= 3:
#                         direction = parts[2]
#                         steps = 1
#                         if len(parts) > 3:
#                             try:
#                                 steps = int(parts[3])
#                             except ValueError:
#                                 steps = 1
                        
#                         if direction == "up":
#                             self.device.move_camera_relative(up=steps)
#                             print(f"✅ Camera moved UP by {steps}")
#                         elif direction == "down":
#                             self.device.move_camera_relative(down=steps)
#                             print(f"✅ Camera moved DOWN by {steps}")
#                         elif direction == "left":
#                             self.device.move_camera_relative(left=steps)
#                             print(f"✅ Camera moved LEFT by {steps}")
#                         elif direction == "right":
#                             self.device.move_camera_relative(right=steps)
#                             print(f"✅ Camera moved RIGHT by {steps}")
#                         else:
#                             print("❌ Direction must be: up, down, left, right")
#                     else:
#                         print("❌ Usage: camera move <up/down/left/right> [steps]")
                
#                 # ========== LED Commands ==========
#                 elif cmd.startswith("led bright"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             brightness = int(parts[2])
#                             if 0 <= brightness <= 5:
#                                 self.device.set_led_brightness(brightness)
#                                 print(f"✅ LED brightness set to {brightness}")
#                             else:
#                                 print("❌ Brightness must be 0-5")
#                         except ValueError:
#                             print("❌ Invalid brightness value")
                
#                 elif cmd == "led status":
#                     led = self.device.get_led_ring()
#                     print(f"💡 LED Brightness: {led.get('brightness', 3)}")
                
#                 # ========== Network Commands ==========
#                 elif cmd == "network status":
#                     network = self.device.get_network_interfaces()
#                     print("\n🌐 NETWORK INTERFACES:")
#                     print(json.dumps(network, indent=2))
                
#                 elif cmd == "dante status":
#                     dante = self.device.get_dante_status()
#                     print(f"🎵 Dante Enabled: {dante.get('enabled', False)}")
                
#                 elif cmd == "bluetooth on":
#                     self.device.set_bluetooth_settings(enabled=True)
#                     print("✅ Bluetooth ENABLED")
                
#                 elif cmd == "bluetooth off":
#                     self.device.set_bluetooth_settings(enabled=False)
#                     print("✅ Bluetooth DISABLED")
                
#                 elif cmd == "wifi status":
#                     wifi = self.device.get_wifi_status()
#                     print(f"📡 WiFi Enabled: {wifi.get('enabled', False)}")
#                     print(f"   State: {wifi.get('state', 'Unknown')}")
                
#                 # ========== Device Commands ==========
#                 elif cmd.startswith("site name"):
#                     parts = cmd.split(maxsplit=2)
#                     if len(parts) >= 3:
#                         name = parts[2]
#                         self.device.set_device_site(device_name=name)
#                         print(f"✅ Device name set to {name}")
#                     else:
#                         print("❌ Usage: site name <name>")
                
#                 elif cmd.startswith("site location"):
#                     parts = cmd.split(maxsplit=2)
#                     if len(parts) >= 3:
#                         location = parts[2]
#                         self.device.set_device_site(location=location)
#                         print(f"✅ Location set to {location}")
#                     else:
#                         print("❌ Usage: site location <location>")
                
#                 elif cmd == "sound prompts on":
#                     self.device.set_sound_prompts(True)
#                     print("✅ Sound prompts ENABLED")
                
#                 elif cmd == "sound prompts off":
#                     self.device.set_sound_prompts(False)
#                     print("✅ Sound prompts DISABLED")
                
#                 elif cmd == "identify on":
#                     self.device.identify_device(True)
#                     print("✅ Device identification started - LEDs will blink for 5 seconds")
#                     # Auto turn off after 5 seconds
#                     threading.Timer(5.0, lambda: self.device.identify_device(False)).start()
                
#                 elif cmd == "identify off":
#                     self.device.identify_device(False)
#                     print("✅ Device identification stopped")
                
#                 elif cmd == "restart":
#                     confirm = input("⚠️ Are you sure you want to restart the device? (yes/no): ")
#                     if confirm.lower() == "yes":
#                         self.device.restart_device()
#                         print("🔄 Device restarting...")
#                     else:
#                         print("Restart cancelled")
                
#                 elif cmd.startswith("profile"):
#                     parts = cmd.split()
#                     if len(parts) == 2:
#                         profile = parts[1].capitalize()
#                         if profile in ["Custom", "MicrosoftTeams"]:
#                             self.device.set_device_profile(profile)
#                             print(f"✅ Device profile set to {profile}")
#                         else:
#                             print("❌ Profile must be 'custom' or 'teams'")
#                     else:
#                         print("❌ Usage: profile <custom/teams>")
                
#                 # ========== Monitoring Commands ==========
#                 elif cmd == "status":
#                     info = self.device.get_complete_device_info()
#                     print("\n📱 DETAILED DEVICE STATUS:")
#                     print(json.dumps(info, indent=2, default=str))
                
#                 elif cmd == "firmware":
#                     fw = self.device.get_firmware_state_object()
#                     print(f"\n📦 FIRMWARE:")
#                     print(f"   Device Version: {fw.device_version}")
#                     print(f"   State: {fw.state}")
#                     if fw.state != 'Idle':
#                         print(f"   Progress: {fw.progress}%")
#                         print(f"   Last Status: {fw.last_status}")
                
#                 elif cmd == "monitor":
#                     if not self.monitoring_active:
#                         self.monitoring_active = True
#                         self.device.start_monitoring(1.0, self.display_metrics)
#                         print("\n✅ Real-time monitoring started")
#                     else:
#                         print("⚠️ Monitoring already active")
                
#                 elif cmd == "stop":
#                     if self.monitoring_active:
#                         self.device.stop_monitoring()
#                         self.monitoring_active = False
#                         print("✅ Monitoring stopped")
                
#                 elif cmd == "info":
#                     info = self.device.get_complete_device_info()
#                     print("\n📱 COMPLETE DEVICE INFO:")
#                     print(json.dumps(info, indent=2, default=str))
                
#                 else:
#                     print("❌ Unknown command")
                    
#             except Exception as e:
#                 print(f"❌ Error: {e}")


# # ========== Main Entry Point ==========

# def get_user_credentials():
#     """Get device connection details from user"""
#     print("\n" + "=" * 60)
#     print(" SENNHEISER TEAMCONNECT BAR M DEVICE CONNECTION SETUP")
#     print("=" * 60)
    
#     device_ip = input("\n🔌 Enter Device IP Address: ").strip()
#     username = input("👤 Enter Username (default: api): ").strip() or "api"
#     password = getpass.getpass("🔑 Enter Password: ").strip()
    
#     return device_ip, username, password


# def validate_connection(device_ip, username, password):
#     """Validate the connection with provided credentials"""
#     print("\n🔍 Validating connection...")
    
#     test_device = SennheiserTCBarMPlugin(device_ip, username, password)
    
#     try:
#         identity = test_device.get_device_identity()
#         if identity and 'product' in identity:
#             print(f"   ✅ Connection successful!")
#             print(f"   📱 Device: {identity.get('product')}")
#             print(f"   🔢 Serial: {identity.get('serial')}")
#             return True, test_device
#         return False, None
#     except Exception as e:
#         print(f"   ❌ Connection failed: {e}")
#         return False, None


# def main():
#     """Main entry point"""
#     print("\n" + "=" * 60)
#     print(" SENNHEISER TEAMCONNECT BAR M DEVICE CONTROL PLUGIN")
#     print("=" * 60)
    
#     device_ip, username, password = get_user_credentials()
#     success, device = validate_connection(device_ip, username, password)
    
#     if not success:
#         print("\n❌ Failed to connect. Please check:")
#         print("   1. Device IP address is correct")
#         print("   2. 3rd Party Access is enabled in device settings")
#         print("   3. Username and password are correct")
#         print("\n   Note: Default credentials are username='api' with password set in device settings")
#         return
    
#     print("\n✅ CONNECTION ESTABLISHED - LAUNCHING CONTROL INTERFACE")
#     controller = SennheiserTCBarMController(device_ip, username, password)
    
#     try:
#         controller.run_interactive_menu()
#     except KeyboardInterrupt:
#         print("\n\n👋 Goodbye!")
#     except Exception as e:
#         print(f"\n❌ Error: {e}")


# if __name__ == "__main__":
#     main()






# #!/usr/bin/env python3
# """
# Sennheiser TC Bar M Device Control Plugin - Complete API Integration
# Based on SSC v2 API (Schema 1.0, Protocol 2.3)
# """

# import urllib.request
# import urllib.error
# import ssl
# import json
# import base64
# import time
# import threading
# import getpass
# import sys
# from typing import Optional, Dict, Any, List, Callable, Union
# from datetime import datetime
# from dataclasses import dataclass, field
# from enum import Enum

# # ========== Enums ==========

# class NoiseSuppressionWeighting(Enum):
#     """Noise suppression weighting options"""
#     OFF = "Off"
#     LOW = "Low"
#     MEDIUM = "Medium"
#     HIGH = "High"

# class FadeBehavior(Enum):
#     """Fade behavior for mic mixer"""
#     OFF = "Off"
#     FAST = "Fast"
#     MEDIUM = "Medium"
#     SLOW = "Slow"

# class SoundProfilePreset(Enum):
#     """Sound profile presets"""
#     WALLMOUNT = "Wallmount"
#     CEILING_MOUNT = "CeilingMount"
#     CUSTOM = "Custom"

# class IPMode(Enum):
#     """IP configuration modes"""
#     AUTO = "Auto"
#     MANUAL = "Manual"

# class StandbyMode(Enum):
#     """Standby/energy saving modes"""
#     OFF = "Off"
#     ECO_MODE = "EcoMode"
#     DEEP_SLEEP = "DeepSleep"

# class DeviceProfile(Enum):
#     """Device profiles"""
#     CUSTOM = "Custom"
#     MICROSOFT_TEAMS = "MicrosoftTeams"

# class AntiFlickerFrequency(Enum):
#     """Anti-flicker frequency options"""
#     AUTO = "Auto"
#     _50HZ = "50Hz"
#     _60HZ = "60Hz"

# class ZoomSpeed(Enum):
#     """Zoom speed options"""
#     SLOW = "Slow"
#     MEDIUM = "Medium"
#     FAST = "Fast"

# class PanTiltSpeed(Enum):
#     """Pan/Tilt speed options"""
#     SLOW = "Slow"
#     MEDIUM = "Medium"
#     FAST = "Fast"

# class ZoneGain(Enum):
#     """Zone gain options"""
#     OFF = "Off"
#     LOW = "Low"
#     MEDIUM = "Medium"
#     HIGH = "High"


# # ========== Data Classes ==========

# @dataclass
# class DeviceState:
#     """Device state information"""
#     state: str
#     warnings: List[str] = field(default_factory=list)
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DeviceIdentity:
#     """Device identity information"""
#     product: str
#     hardware_revision: str
#     serial: str
#     vendor: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DeviceSiteInfo:
#     """Device site information"""
#     device_name: str
#     dante_name: str
#     location: str
#     position: str
#     language: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class FirmwareUpdateState:
#     """Firmware update state"""
#     device_version: str
#     state: str
#     progress: int
#     last_status: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class LEDRingSettings:
#     """LED ring settings"""
#     brightness: int
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class SoundPromptsSettings:
#     """Sound prompts settings"""
#     sound_prompts: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class InternalMicSettings:
#     """Internal microphone settings"""
#     gain: int
#     enabled: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class MuteSettings:
#     """Mute settings"""
#     enabled: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class NoiseGateSettings:
#     """Noise gate settings for internal mic"""
#     enabled: bool
#     threshold: int
#     hold_time: int
#     range_val: int
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class SpeakerOutputSettings:
#     """Speaker output settings"""
#     volume: int
#     level_limiter: int
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class SoundProfileSettings:
#     """Sound profile settings"""
#     preset: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class PriorityZoneSettings:
#     """Priority zone settings"""
#     id: int
#     active: bool
#     enabled: bool
#     gain: str
#     left: int
#     right: int
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class ExclusionZoneSettings:
#     """Exclusion zone settings"""
#     id: int
#     active: bool
#     enabled: bool
#     left: int
#     right: int
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class BeamPosition:
#     """Beam position"""
#     position: int
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DeviceMetrics:
#     """Real-time device metrics"""
#     timestamp: datetime
#     microphone_level: int
#     mute_status: Optional[bool]
#     beam_position: int
#     active_channel: str
#     speaker_volume: int
#     usb_input_level: int
#     bluetooth_input_level: int

# @dataclass
# class CameraVideoParameters:
#     """Camera video parameters"""
#     compensation: str
#     anti_flicker_frequency: str
#     brightness: int
#     contrast: int
#     saturation: int
#     sharpness: int
#     auto_whitebalance_enabled: bool
#     whitebalance: int
#     default_camera_mode: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class CameraMovementSettings:
#     """Camera movement settings"""
#     pan_position: int
#     tilt_position: int
#     zoom_position: int
#     zoom_speed: str
#     pan_tilt_speed: str
#     auto_framing_speed: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class CameraAIAccess:
#     """Camera AI access settings"""
#     auto_framing_access_enabled: bool
#     auto_framing_enabled: bool
#     person_tiling_access_enabled: bool
#     person_tiling_enabled: bool
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class NetworkInterface:
#     """Network interface settings"""
#     name: str
#     type: str
#     mac: str
#     functionalities: List[str]
#     auto_discovery: bool
#     ip_mode: str
#     ipv4: Dict[str, Any]
#     ipv6: Dict[str, Any]
#     vlan_tag: Optional[int]
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class DanteSettings:
#     """Dante settings"""
#     enabled: bool
#     continuous_dante_stream: bool = False
#     dante_speaker_output: bool = False
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class BluetoothSettings:
#     """Bluetooth settings"""
#     enabled: bool
#     pairing: bool
#     mac: str
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class WifiStatus:
#     """WiFi status"""
#     enabled: bool
#     state: str
#     connection: Dict[str, Any]
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class ConferenceOutputSettings:
#     """Conference output settings"""
#     far_end_gain: int
#     near_end_gain: int
#     timestamp: datetime = field(default_factory=datetime.now)

# @dataclass
# class PortConfiguration:
#     """Port configuration for RJ45 ports"""
#     configuration: str
#     timestamp: datetime = field(default_factory=datetime.now)


# # ========== Main Plugin Class ==========

# class SennheiserTCBarMPlugin:
#     """Complete plugin for Sennheiser TeamConnect Bar M with all API endpoints"""
    
#     def __init__(self, device_ip: str, username: str, password: str, verify_ssl: bool = False):
#         self.device_ip = device_ip
#         self.base_url = f"https://{device_ip}/api"
#         self.username = username
#         self.password = password
        
#         auth_string = f"{username}:{password}"
#         auth_bytes = auth_string.encode('utf-8')
#         self.auth_header = base64.b64encode(auth_bytes).decode('ascii')
        
#         self.ssl_context = ssl.create_default_context()
#         self.ssl_context.check_hostname = False
#         self.ssl_context.verify_mode = ssl.CERT_NONE
        
#         self.monitoring = False
#         self.monitor_thread = None
#         self.metrics_history = []
#         self.callbacks = []
#         self.firmware_monitoring = False
#         self.firmware_monitor_thread = None
    
#     def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
#         """Make HTTP request to the device"""
#         url = f"{self.base_url}{endpoint}"
        
#         headers = {
#             "Accept": "application/json",
#             "Authorization": f"Basic {self.auth_header}"
#         }
        
#         if data and method in ["PUT", "POST"]:
#             headers["Content-Type"] = "application/json"
#             request_data = json.dumps(data).encode('utf-8')
#         else:
#             request_data = None
        
#         req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
        
#         try:
#             response = urllib.request.urlopen(req, context=self.ssl_context, timeout=10)
#             response_data = response.read().decode('utf-8')
#             return json.loads(response_data) if response_data else {}
#         except urllib.error.HTTPError as e:
#             if e.code == 401:
#                 raise Exception("Authentication failed - Invalid username or password")
#             elif e.code == 403:
#                 raise Exception("Forbidden - Check 3rd party access settings")
#             error_msg = e.read().decode('utf-8') if e.fp else str(e)
#             return {"error": f"HTTP {e.code}", "message": error_msg}
#         except Exception as e:
#             return {"error": str(e)}
    
#     def validate_connection(self) -> bool:
#         """Validate that the connection and credentials work"""
#         try:
#             result = self.get_device_identity()
#             return result and 'product' in result
#         except Exception:
#             return False
    
#     # ========== Device Information Methods ==========
    
#     def get_device_state(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/device/state")
    
#     def get_device_identity(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/device/identity")
    
#     def get_identification_state(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/device/identification")
    
#     def set_identification(self, visual: bool) -> Dict[str, Any]:
#         return self._make_request("PUT", "/device/identification", data={"visual": visual})
    
#     def identify_device(self, enable: bool = True) -> Dict[str, Any]:
#         return self.set_identification(enable)
    
#     def restart_device(self) -> Dict[str, Any]:
#         return self._make_request("PUT", "/device/restart")
    
#     def get_allowed_standby_mode(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/device/allowedStandbyMode")
    
#     def set_allowed_standby_mode(self, mode: str) -> Dict[str, Any]:
#         valid_modes = ["Off", "EcoMode", "DeepSleep"]
#         if mode not in valid_modes:
#             raise Exception(f"Invalid mode. Must be one of: {valid_modes}")
#         return self._make_request("PUT", "/device/allowedStandbyMode", data={"mode": mode})
    
#     def get_user_interaction(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/device/hasUserInteraction")
    
#     def get_sound_prompts(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/device/feedback")
    
#     def set_sound_prompts(self, enabled: bool) -> Dict[str, Any]:
#         return self._make_request("PUT", "/device/feedback", data={"soundPrompts": enabled})
    
#     def get_device_site(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/device/site")
    
#     def set_device_site(self, device_name: str = None, location: str = None, 
#                         position: str = None, language: str = None) -> Dict[str, Any]:
#         current = self.get_device_site()
#         data = {
#             "deviceName": device_name if device_name else current.get('deviceName'),
#             "danteName": current.get('danteName', current.get('deviceName')),
#             "location": location if location else current.get('location', ''),
#             "position": position if position else current.get('position', ''),
#             "language": language if language else current.get('language', 'En_GB')
#         }
#         return self._make_request("PUT", "/device/site", data=data)
    
#     def get_device_profile(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/device/profile")
    
#     def set_device_profile(self, configuration: str) -> Dict[str, Any]:
#         valid_profiles = ["Custom", "MicrosoftTeams"]
#         if configuration not in valid_profiles:
#             raise Exception(f"Invalid profile. Must be one of: {valid_profiles}")
#         return self._make_request("PUT", "/device/profile", data={"configuration": configuration})
    
#     # ========== LED Control Methods ==========
    
#     def get_led_ring(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/device/leds/ring")
    
#     def set_led_brightness(self, brightness: int) -> Dict[str, Any]:
#         if not 0 <= brightness <= 5:
#             raise Exception("Brightness must be between 0 and 5")
#         return self._make_request("PUT", "/device/leds/ring", data={"brightness": brightness})
    
#     # ========== Audio Methods ==========
    
#     def get_relative_speaker_volume(self, volume_up: int = 0, volume_down: int = 0) -> Dict[str, Any]:
#         if volume_up > 0 and volume_down > 0:
#             raise Exception("Cannot specify both volume_up and volume_down")
#         return self._make_request("PUT", "/audio/outputs/speaker/relative", 
#                                    data={"volumeUp": volume_up, "volumeDown": volume_down})
    
#     def volume_up(self, steps: int = 1) -> Dict[str, Any]:
#         return self.get_relative_speaker_volume(volume_up=steps)
    
#     def volume_down(self, steps: int = 1) -> Dict[str, Any]:
#         return self.get_relative_speaker_volume(volume_down=steps)
    
#     def get_internal_mic(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/internalMic")
    
#     def set_internal_mic(self, gain: int = None, enabled: bool = None) -> Dict[str, Any]:
#         current = self.get_internal_mic()
#         data = {
#             "gain": gain if gain is not None else current.get('gain', 0),
#             "enabled": enabled if enabled is not None else current.get('enabled', True)
#         }
#         if data["gain"] < -30 or data["gain"] > 30:
#             raise Exception("Gain must be between -30 and 30 dB")
#         return self._make_request("PUT", "/audio/inputs/internalMic", data=data)
    
#     def get_mic_mute(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/mute")
    
#     def set_mic_mute(self, enabled: bool) -> Dict[str, Any]:
#         return self._make_request("PUT", "/audio/inputs/mute", data={"enabled": enabled})
    
#     def mute(self) -> Dict[str, Any]:
#         return self.set_mic_mute(True)
    
#     def unmute(self) -> Dict[str, Any]:
#         return self.set_mic_mute(False)
    
#     def get_noise_gate(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/internalMic/noiseGate")
    
#     def set_noise_gate(self, enabled: bool = None, threshold: int = None, 
#                        hold_time: int = None, range_val: int = None) -> Dict[str, Any]:
#         current = self.get_noise_gate()
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "threshold": threshold if threshold is not None else current.get('threshold', -40),
#             "holdTime": hold_time if hold_time is not None else current.get('holdTime', 300),
#             "range": range_val if range_val is not None else current.get('range', -40)
#         }
#         return self._make_request("PUT", "/audio/inputs/internalMic/noiseGate", data=data)
    
#     def get_noise_suppression(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/noiseSuppression")
    
#     def set_noise_suppression(self, weighting: str) -> Dict[str, Any]:
#         valid_weightings = ["Off", "Low", "Medium", "High"]
#         if weighting not in valid_weightings:
#             raise Exception(f"Invalid weighting. Must be one of: {valid_weightings}")
#         return self._make_request("PUT", "/audio/inputs/noiseSuppression", 
#                                    data={"weighting": weighting})
    
#     def get_speaker_output(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/outputs/speaker")
    
#     def set_speaker_output(self, volume: int = None, level_limiter: int = None) -> Dict[str, Any]:
#         current = self.get_speaker_output()
#         data = {
#             "volume": volume if volume is not None else current.get('volume', 50),
#             "levelLimiter": level_limiter if level_limiter is not None else current.get('levelLimiter', 100)
#         }
#         if data["volume"] < 0 or data["volume"] > 100:
#             raise Exception("Volume must be between 0 and 100")
#         return self._make_request("PUT", "/audio/outputs/speaker", data=data)
    
#     def set_volume(self, volume: int) -> Dict[str, Any]:
#         return self.set_speaker_output(volume=volume)
    
#     def get_sound_profile(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/soundProfile")
    
#     def set_sound_profile(self, preset: str) -> Dict[str, Any]:
#         valid_presets = ["Wallmount", "CeilingMount", "Custom"]
#         if preset not in valid_presets:
#             raise Exception(f"Invalid preset. Must be one of: {valid_presets}")
#         return self._make_request("PUT", "/audio/soundProfile", data={"preset": preset})
    
#     # ========== Priority Zone Methods ==========
    
#     def get_priority_zones(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/internalMic/priorityZones")
    
#     def get_priority_zone(self, zone_id: int) -> Dict[str, Any]:
#         return self._make_request("GET", f"/audio/inputs/internalMic/priorityZones/{zone_id}")
    
#     def set_priority_zone(self, zone_id: int, enabled: bool = None, 
#                           gain: str = None, left: int = None, right: int = None) -> Dict[str, Any]:
#         current = self.get_priority_zone(zone_id)
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "gain": gain if gain is not None else current.get('gain', 'Medium'),
#             "left": left if left is not None else current.get('left', 0),
#             "right": right if right is not None else current.get('right', 100)
#         }
#         return self._make_request("PUT", f"/audio/inputs/internalMic/priorityZones/{zone_id}", data=data)
    
#     def enable_priority_zone(self, zone_id: int) -> Dict[str, Any]:
#         return self.set_priority_zone(zone_id, enabled=True)
    
#     def disable_priority_zone(self, zone_id: int) -> Dict[str, Any]:
#         return self.set_priority_zone(zone_id, enabled=False)
    
#     def set_priority_zone_gain(self, zone_id: int, gain) -> Dict[str, Any]:
#         if isinstance(gain, int) or (isinstance(gain, str) and gain.isdigit()):
#             gain_num = int(gain)
#             if 0 <= gain_num <= 100:
#                 return self.set_priority_zone(zone_id, gain=gain_num)
#             else:
#                 raise Exception("Numeric gain must be between 0 and 100")
#         return self.set_priority_zone(zone_id, gain=gain)
    
#     def set_priority_zone_range(self, zone_id: int, left: int, right: int) -> Dict[str, Any]:
#         if not 0 <= left <= 100 or not 0 <= right <= 100:
#             raise Exception("Left and right must be between 0 and 100")
#         if left > right:
#             left, right = right, left
#         return self.set_priority_zone(zone_id, left=left, right=right)
    
#     # ========== Exclusion Zone Methods ==========
    
#     def get_exclusion_zones(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/internalMic/exclusionZones")
    
#     def get_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
#         return self._make_request("GET", f"/audio/inputs/internalMic/exclusionZones/{zone_id}")
    
#     def set_exclusion_zone(self, zone_id: int, enabled: bool = None, 
#                            left: int = None, right: int = None) -> Dict[str, Any]:
#         current = self.get_exclusion_zone(zone_id)
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "left": left if left is not None else current.get('left', 0),
#             "right": right if right is not None else current.get('right', 100)
#         }
#         return self._make_request("PUT", f"/audio/inputs/internalMic/exclusionZones/{zone_id}", data=data)
    
#     def enable_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
#         return self.set_exclusion_zone(zone_id, enabled=True)
    
#     def disable_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
#         return self.set_exclusion_zone(zone_id, enabled=False)
    
#     def set_exclusion_zone_range(self, zone_id: int, left: int, right: int) -> Dict[str, Any]:
#         if not 0 <= left <= 100 or not 0 <= right <= 100:
#             raise Exception("Left and right must be between 0 and 100")
#         if left > right:
#             left, right = right, left
#         return self.set_exclusion_zone(zone_id, left=left, right=right)
    
#     # ========== Beam Methods ==========
    
#     def get_beam_position(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/internalMic/beam")
    
#     # ========== EQ Methods ==========
    
#     def get_internal_mic_custom_eq(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/internalMic/customEq")
    
#     def set_internal_mic_custom_eq(self, eq_values: List[int]) -> Dict[str, Any]:
#         if len(eq_values) != 7:
#             raise Exception("EQ must have exactly 7 values (-12 to 12 dB)")
#         for val in eq_values:
#             if val < -12 or val > 12:
#                 raise Exception("EQ values must be between -12 and 12")
#         return self._make_request("PUT", "/audio/inputs/internalMic/customEq", data=eq_values)
    
#     def get_speaker_custom_eq(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/outputs/speaker/customEq")
    
#     def set_speaker_custom_eq(self, eq_values: List[int]) -> Dict[str, Any]:
#         if len(eq_values) != 7:
#             raise Exception("EQ must have exactly 7 values (-12 to 12 dB)")
#         for val in eq_values:
#             if val < -12 or val > 12:
#                 raise Exception("EQ values must be between -12 and 12")
#         return self._make_request("PUT", "/audio/outputs/speaker/customEq", data=eq_values)
    
#     # ========== Mixer Methods ==========
    
#     def get_mixer_fade_behavior(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/mixer")
    
#     def set_mixer_fade_behavior(self, fade_behavior: str) -> Dict[str, Any]:
#         valid_behaviors = ["Off", "Fast", "Medium", "Slow"]
#         if fade_behavior not in valid_behaviors:
#             raise Exception(f"Invalid fade behavior. Must be one of: {valid_behaviors}")
#         return self._make_request("PUT", "/audio/inputs/mixer", data={"fadeBehavior": fade_behavior})
    
#     def get_active_mic_channel(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/mixer/activity")
    
#     # ========== Conference Output Methods ==========
    
#     def get_conference_output(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/outputs/conferenceOutput")
    
#     def set_conference_output(self, far_end_gain: int = None, near_end_gain: int = None) -> Dict[str, Any]:
#         current = self.get_conference_output()
#         data = {
#             "farEndGain": far_end_gain if far_end_gain is not None else current.get('farEndGain', 0),
#             "nearEndGain": near_end_gain if near_end_gain is not None else current.get('nearEndGain', 0)
#         }
#         if data["farEndGain"] < -18 or data["farEndGain"] > 18:
#             raise Exception("Far end gain must be between -18 and 18 dB")
#         if data["nearEndGain"] < -18 or data["nearEndGain"] > 18:
#             raise Exception("Near end gain must be between -18 and 18 dB")
#         return self._make_request("PUT", "/audio/outputs/conferenceOutput", data=data)
    
#     # ========== Level Monitoring Methods ==========
    
#     def get_internal_mic_level(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/internalMic/level")
    
#     def get_bluetooth_input_level(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/bluetooth")
    
#     def get_usb_input_level(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/audio/inputs/usb")
    
#     # ========== Camera Methods ==========
    
#     def reset_camera_to_ffov(self) -> Dict[str, Any]:
#         return self._make_request("PUT", "/video/input/internalCamera/ffov")
    
#     def store_camera_preset(self) -> Dict[str, Any]:
#         return self._make_request("PUT", "/video/input/internalCamera/preset/store")
    
#     def load_camera_preset(self) -> Dict[str, Any]:
#         return self._make_request("PUT", "/video/input/internalCamera/preset/load")
    
#     def get_camera_ai_access(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/video/input/internalCamera/aiAccess")
    
#     def set_camera_ai_access(self, auto_framing_access: bool = None, 
#                               auto_framing: bool = None,
#                               person_tiling_access: bool = None,
#                               person_tiling: bool = None) -> Dict[str, Any]:
#         current = self.get_camera_ai_access()
#         data = {
#             "autoFramingAccessEnabled": auto_framing_access if auto_framing_access is not None 
#                                         else current.get('autoFramingAccessEnabled', False),
#             "autoFramingEnabled": auto_framing if auto_framing is not None 
#                                  else current.get('autoFramingEnabled', False),
#             "personTilingAccessEnabled": person_tiling_access if person_tiling_access is not None 
#                                         else current.get('personTilingAccessEnabled', False),
#             "personTilingEnabled": person_tiling if person_tiling is not None 
#                                   else current.get('personTilingEnabled', False)
#         }
#         return self._make_request("PUT", "/video/input/internalCamera/aiAccess", data=data)
    
#     def move_camera_relative(self, up: int = 0, down: int = 0, left: int = 0, 
#                               right: int = 0, zoom_in: int = 0, zoom_out: int = 0) -> Dict[str, Any]:
#         if zoom_in > 0 and zoom_out > 0:
#             raise Exception("Cannot specify both zoom_in and zoom_out")
#         data = {
#             "up": up, "down": down, "left": left, "right": right,
#             "zoomIn": zoom_in, "zoomOut": zoom_out
#         }
#         return self._make_request("PUT", "/video/input/internalCamera/movement/relative", data=data)
    
#     def get_camera_video_parameters(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/video/input/internalCamera/videoParameters")
    
#     def get_camera_movement(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/video/input/internalCamera/movement")
    
#     def set_camera_movement(self, pan_position: int = None, tilt_position: int = None,
#                              zoom_position: int = None, zoom_speed: str = None,
#                              pan_tilt_speed: str = None, auto_framing_speed: str = None) -> Dict[str, Any]:
#         current = self.get_camera_movement()
#         data = {
#             "panPosition": pan_position if pan_position is not None else current.get('panPosition', 0),
#             "tiltPosition": tilt_position if tilt_position is not None else current.get('tiltPosition', 0),
#             "zoomPosition": zoom_position if zoom_position is not None else current.get('zoomPosition', 100),
#             "zoomSpeed": zoom_speed if zoom_speed is not None else current.get('zoomSpeed', 'Medium'),
#             "panTiltSpeed": pan_tilt_speed if pan_tilt_speed is not None else current.get('panTiltSpeed', 'Medium'),
#             "autoFramingSpeed": auto_framing_speed if auto_framing_speed is not None 
#                                else current.get('autoFramingSpeed', 'Medium')
#         }
#         return self._make_request("PUT", "/video/input/internalCamera/movement", data=data)
    
#     def get_camera_status(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/video/input/internalCamera")
    
#     def get_hdmi_enabled(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/video/output/hdmi")
    
#     def set_hdmi_enabled(self, enabled: bool) -> Dict[str, Any]:
#         return self._make_request("PUT", "/video/output/hdmi", data={"enabled": enabled})
    
#     # ========== Network Methods ==========
    
#     def get_network_interfaces(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/interfaces/network")
    
#     def get_dante_status(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/interfaces/network/dante")
    
#     def get_dante_settings(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/interfaces/network/dante/settings")
    
#     def set_dante_settings(self, continuous_stream: bool = None, 
#                             speaker_output: bool = None) -> Dict[str, Any]:
#         current = self.get_dante_settings()
#         data = {
#             "continuousDanteStream": continuous_stream if continuous_stream is not None 
#                                     else current.get('continuousDanteStream', False),
#             "danteSpeakerOutput": speaker_output if speaker_output is not None 
#                                  else current.get('danteSpeakerOutput', False)
#         }
#         return self._make_request("PUT", "/interfaces/network/dante/settings", data=data)
    
#     def get_port_configuration(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/interfaces/network/portConfiguration")
    
#     # ========== Bluetooth Methods ==========
    
#     def get_bluetooth_settings(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/interfaces/bluetooth")
    
#     def set_bluetooth_settings(self, enabled: bool = None, pairing: bool = None) -> Dict[str, Any]:
#         current = self.get_bluetooth_settings()
#         data = {
#             "enabled": enabled if enabled is not None else current.get('enabled', False),
#             "pairing": pairing if pairing is not None else current.get('pairing', False)
#         }
#         return self._make_request("PUT", "/interfaces/bluetooth", data=data)
    
#     # ========== WiFi Methods ==========
    
#     def get_wifi_status(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/interfaces/network/wifi")
    
#     # ========== Firmware Update Methods ==========
    
#     def get_firmware_update_state(self) -> Dict[str, Any]:
#         return self._make_request("GET", "/firmware/update/state")
    
#     def is_firmware_updating(self) -> bool:
#         state = self.get_firmware_update_state()
#         update_state = state.get('state', 'Idle')
#         return update_state in ['Downloading', 'Updating', 'Rebooting']
    
#     # ========== Real-time Monitoring ==========
    
#     def get_all_metrics(self) -> DeviceMetrics:
#         mic_level = self.get_internal_mic_level()
#         mute = self.get_mic_mute()
#         beam = self.get_beam_position()
#         active = self.get_active_mic_channel()
#         speaker = self.get_speaker_output()
#         usb_level = self.get_usb_input_level()
#         bt_level = self.get_bluetooth_input_level()
        
#         return DeviceMetrics(
#             timestamp=datetime.now(),
#             microphone_level=mic_level.get('peak', 0) if isinstance(mic_level, dict) else 0,
#             mute_status=mute.get('enabled') if isinstance(mute, dict) else None,
#             beam_position=beam.get('position', 0) if isinstance(beam, dict) else 0,
#             active_channel=active.get('activeChannel', 'Unknown') if isinstance(active, dict) else 'Unknown',
#             speaker_volume=speaker.get('volume', 50) if isinstance(speaker, dict) else 50,
#             usb_input_level=usb_level.get('level', 0) if isinstance(usb_level, dict) else 0,
#             bluetooth_input_level=bt_level.get('level', 0) if isinstance(bt_level, dict) else 0
#         )
    
#     def start_monitoring(self, interval: float = 1.0, callback: Optional[Callable] = None):
#         if callback:
#             self.callbacks.append(callback)
#         if not self.monitoring:
#             self.monitoring = True
#             self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
#             self.monitor_thread.daemon = True
#             self.monitor_thread.start()
#             print(f"✅ Monitoring started (interval: {interval}s)")
    
#     def stop_monitoring(self):
#         self.monitoring = False
#         if self.monitor_thread:
#             self.monitor_thread.join(timeout=2)
#         print("✅ Monitoring stopped")
    
#     def _monitor_loop(self, interval: float):
#         while self.monitoring:
#             try:
#                 metrics = self.get_all_metrics()
#                 self.metrics_history.append(metrics)
#                 if len(self.metrics_history) > 1000:
#                     self.metrics_history = self.metrics_history[-1000:]
#                 for callback in self.callbacks:
#                     try:
#                         callback(metrics)
#                     except Exception as e:
#                         print(f"Callback error: {e}")
#                 time.sleep(interval)
#             except Exception as e:
#                 print(f"Monitoring error: {e}")
#                 time.sleep(interval)
    
#     def get_complete_device_info(self) -> Dict[str, Any]:
#         return {
#             "identity": self.get_device_identity(),
#             "firmware": self.get_firmware_update_state(),
#             "state": self.get_device_state(),
#             "led_settings": self.get_led_ring(),
#             "site_info": self.get_device_site(),
#             "beam_position": self.get_beam_position(),
#             "microphone": self.get_internal_mic(),
#             "speaker": self.get_speaker_output(),
#             "noise_gate": self.get_noise_gate(),
#             "noise_suppression": self.get_noise_suppression(),
#             "sound_profile": self.get_sound_profile(),
#             "camera": {
#                 "ai_access": self.get_camera_ai_access(),
#                 "video_parameters": self.get_camera_video_parameters()
#             },
#             "network": self.get_network_interfaces(),
#             "bluetooth": self.get_bluetooth_settings(),
#             "wifi": self.get_wifi_status(),
#             "priority_zones": self.get_priority_zones(),
#             "exclusion_zones": self.get_exclusion_zones(),
#             "timestamp": datetime.now().isoformat(),
#             "ip": self.device_ip
#         }


# # ========== Interactive Controller ==========

# class SennheiserTCBarMController:
#     """Interactive controller for TeamConnect Bar M"""
    
#     def __init__(self, device_ip: str, username: str, password: str):
#         self.device = SennheiserTCBarMPlugin(device_ip, username, password)
#         self.monitoring_active = False
#         self.device_ip = device_ip
    
#     def display_metrics(self, metrics: DeviceMetrics):
#         mute_display = "🔴 MUTED" if metrics.mute_status else "🟢 LIVE"
#         print(f"\r📊 [{metrics.timestamp.strftime('%H:%M:%S')}] "
#               f"Mic: {metrics.microphone_level}dB | "
#               f"Beam: {metrics.beam_position}° | "
#               f"Volume: {metrics.speaker_volume}% | "
#               f"Active: {metrics.active_channel} | "
#               f"Mute: {mute_display}", end="")
    
#     def run_interactive_menu(self):
#         """Run interactive control menu"""
#         while True:
#             print("\n" + "=" * 70)
#             print(f" SENNHEISER TEAMCONNECT BAR M - COMPLETE CONTROL SYSTEM ({self.device_ip})")
#             print("=" * 70)
#             print("\n📊 CURRENT STATUS:")
            
#             try:
#                 metrics = self.device.get_all_metrics()
#                 identity = self.device.get_device_identity()
#                 state = self.device.get_device_state()
#                 site = self.device.get_device_site()
#                 mic = self.device.get_internal_mic()
#                 speaker = self.device.get_speaker_output()
#                 noise_gate = self.device.get_noise_gate()
#                 noise_suppression = self.device.get_noise_suppression()
#                 beam = self.device.get_beam_position()
#                 camera_ai = self.device.get_camera_ai_access()
#                 firmware = self.device.get_firmware_update_state()
                
#                 print(f"\n📱 DEVICE: {identity.get('product', 'TC Bar M')}")
#                 print(f"   Serial: {identity.get('serial', 'Unknown')}")
#                 print(f"   State: {state.get('state', 'Unknown')}")
#                 print(f"   Firmware: {firmware.get('deviceVersion', 'Unknown')}")
                
#                 print(f"\n📍 SITE:")
#                 print(f"   Name: {site.get('deviceName', 'Unknown')}")
#                 print(f"   Location: {site.get('location', 'Unknown')}")
                
#                 print(f"\n🎤 AUDIO:")
#                 print(f"   Mic Level: {metrics.microphone_level} dB")
#                 print(f"   Mic Enabled: {'✅' if mic.get('enabled') else '❌'}")
#                 print(f"   Mic Gain: {mic.get('gain', 0)} dB")
#                 mute_display = "🔴 MUTED" if metrics.mute_status else "🟢 LIVE"
#                 print(f"   Mute Status: {mute_display}")
#                 print(f"   Speaker Volume: {speaker.get('volume', 50)}%")
#                 print(f"   Active Channel: {metrics.active_channel}")
                
#                 print(f"\n🎯 BEAMFORMING:")
#                 print(f"   Beam Position: {beam.get('position', 0)}°")
                
#                 print(f"\n🔧 PROCESSING:")
#                 print(f"   Noise Gate: {'✅' if noise_gate.get('enabled') else '❌'}")
#                 print(f"   Noise Suppression: {noise_suppression.get('weighting', 'Medium')}")
                
#                 print(f"\n📷 CAMERA:")
#                 print(f"   Auto Framing: {'✅' if camera_ai.get('autoFramingEnabled') else '❌'}")
#                 print(f"   Person Tiling: {'✅' if camera_ai.get('personTilingEnabled') else '❌'}")
                
#             except Exception as e:
#                 print(f"   ⚠️ Error getting status: {e}")
            
#             print("\n" + "=" * 70)
#             print("🎮 CONTROL COMMANDS:")
            
#             print("\n📢 AUDIO CONTROLS:")
#             print("  mute on/off           - Mute/Unmute microphone")
#             print("  volume <0-100>        - Set speaker volume")
#             print("  volume up/down        - Increase/Decrease volume")
#             print("  mic gain <-30-30>     - Set microphone gain")
#             print("  mic enable/disable    - Enable/Disable microphone")
            
#             print("\n🎛️ PROCESSING:")
#             print("  noisegate on/off      - Enable/Disable noise gate")
#             print("  noisegate <thresh> <hold> <range> - Set noise gate params")
#             print("  suppress <off/low/medium/high> - Set noise suppression")
            
#             print("\n🎯 BEAMFORMING:")
#             print("  beam status           - Show beam position")
            
#             print("\n📷 CAMERA CONTROLS:")
#             print("  camera ai on/off      - Enable/Disable auto framing")
#             print("  camera tiling on/off  - Enable/Disable person tiling")
#             print("  camera ffov           - Reset to full field of view")
#             print("  camera preset store   - Store current camera preset")
#             print("  camera preset load    - Load camera preset")
#             print("  camera move <up/down/left/right> <steps> - Move camera")
#             print("  camera zoom in/out    - Zoom camera")
#             print("  hdmi status           - Show HDMI output status")
            
#             print("\n🎯 ZONE CONTROLS (Priority Zones):")
#             print("  priority list         - List all priority zones")
#             print("  priority get <id>     - Get priority zone")
#             print("  priority on <id>      - Enable priority zone")
#             print("  priority off <id>     - Disable priority zone")
#             print("  priority gain <id> <value> - Set gain (Off/Low/Medium/High or 0-100)")
#             print("  priority range <id> <left> <right> - Set angular range (0-100)")

#             print("\n🚫 ZONE CONTROLS (Exclusion Zones):")
#             print("  exclude list          - List all exclusion zones")
#             print("  exclude get <id>      - Get exclusion zone")
#             print("  exclude on <id>       - Enable exclusion zone")
#             print("  exclude off <id>      - Disable exclusion zone")
#             print("  exclude range <id> <left> <right> - Set angular range (0-100)")
            
#             print("\n💡 LED CONTROLS:")
#             print("  led bright <0-5>      - Set LED brightness")
#             print("  led status            - Show LED settings")
            
#             print("\n🌐 NETWORK:")
#             print("  network status        - Show network interfaces")
#             print("  dante status          - Show Dante status")
#             print("  bluetooth on/off      - Enable/Disable Bluetooth")
#             print("  wifi status           - Show WiFi status")
            
#             print("\n🔧 DEVICE:")
#             print("  site name <name>      - Set device name")
#             print("  site location <loc>   - Set location")
#             print("  sound prompts on/off  - Enable/Disable sound prompts")
#             print("  identify on/off       - Identify device (blink LEDs)")
#             print("  restart               - Restart device")
#             print("  check profile         - Check current device profile")
#             print("  profile <custom/teams> - Set device profile")
            
#             print("\n📊 MONITORING:")
#             print("  status                - Show detailed status")
#             print("  firmware              - Show firmware status")
#             print("  monitor               - Start real-time monitoring")
#             print("  stop                  - Stop monitoring")
#             print("  info                  - Complete device info")
#             print("  exit                  - Exit")
#             print("=" * 70)
            
#             cmd = input("\n👉 Enter command: ").strip().lower()
            
#             try:
#                 if cmd == "exit":
#                     if self.monitoring_active:
#                         self.device.stop_monitoring()
#                     print("👋 Goodbye!")
#                     break

#                 # ========== Profile Commands ==========
#                 elif cmd == "check profile":
#                     try:
#                         profile = self.device.get_device_profile()
#                         print(f"📱 Current Device Profile: {profile.get('configuration', 'Unknown')}")
#                         if profile.get('configuration') == 'MicrosoftTeams':
#                             print("   ⚠️ WARNING: Microsoft Teams profile active!")
#                             print("   Try: profile custom")
#                         else:
#                             print("   ✅ Custom profile active - Full control available")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")

#                 # ========== Audio Commands ==========
#                 elif cmd == "mute on":
#                     self.device.mute()
#                     print("✅ Microphone MUTED")
                
#                 elif cmd == "mute off":
#                     self.device.unmute()
#                     print("✅ Microphone UNMUTED")
                
#                 elif cmd.startswith("volume "):
#                     parts = cmd.split()
#                     if len(parts) == 2:
#                         try:
#                             volume = int(parts[1])
#                             if 0 <= volume <= 100:
#                                 self.device.set_volume(volume)
#                                 print(f"✅ Volume set to {volume}%")
#                             else:
#                                 print("❌ Volume must be between 0 and 100")
#                         except ValueError:
#                             print("❌ Invalid volume value")
#                     else:
#                         print("❌ Usage: volume <0-100>")
                
#                 elif cmd == "volume up":
#                     current = self.device.get_speaker_output()
#                     current_volume = current.get('volume', 50)
#                     new_volume = min(100, current_volume + 5)
#                     self.device.set_volume(new_volume)
#                     print(f"✅ Volume increased to {new_volume}%")
                
#                 elif cmd == "volume down":
#                     current = self.device.get_speaker_output()
#                     current_volume = current.get('volume', 50)
#                     new_volume = max(0, current_volume - 5)
#                     self.device.set_volume(new_volume)
#                     print(f"✅ Volume decreased to {new_volume}%")
                
#                 elif cmd.startswith("mic gain"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             gain = int(parts[2])
#                             if -30 <= gain <= 30:
#                                 self.device.set_internal_mic(gain=gain)
#                                 print(f"✅ Mic gain set to {gain} dB")
#                             else:
#                                 print("❌ Gain must be between -30 and 30")
#                         except ValueError:
#                             print("❌ Invalid gain value")
#                     else:
#                         print("❌ Usage: mic gain <-30 to 30>")
                
#                 elif cmd == "mic enable":
#                     self.device.set_internal_mic(enabled=True)
#                     print("✅ Microphone ENABLED")
                
#                 elif cmd == "mic disable":
#                     self.device.set_internal_mic(enabled=False)
#                     print("✅ Microphone DISABLED")
                
#                 # ========== HDMI Commands ==========
#                 elif cmd == "hdmi status":
#                     try:
#                         hdmi = self.device.get_hdmi_enabled()
#                         status = "✅ ENABLED" if hdmi.get('enabled') else "❌ DISABLED"
#                         print(f"📺 HDMI Output: {status}")
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 # ========== Processing Commands ==========
#                 elif cmd == "noisegate on":
#                     self.device.set_noise_gate(enabled=True)
#                     print("✅ Noise gate ENABLED")
                
#                 elif cmd == "noisegate off":
#                     self.device.set_noise_gate(enabled=False)
#                     print("✅ Noise gate DISABLED")
                
#                 elif cmd.startswith("noisegate "):
#                     parts = cmd.split()
#                     if len(parts) == 4:
#                         try:
#                             threshold = int(parts[1])
#                             hold = int(parts[2])
#                             range_val = int(parts[3])
#                             self.device.set_noise_gate(enabled=True, threshold=threshold, 
#                                                         hold_time=hold, range_val=range_val)
#                             print(f"✅ Noise gate set: threshold={threshold}dB, hold={hold}ms, range={range_val}dB")
#                         except ValueError:
#                             print("❌ Invalid values")
#                     else:
#                         print("❌ Usage: noisegate <threshold -80 to -20> <hold 100-2000> <range -80 to 0>")
                
#                 elif cmd.startswith("suppress"):
#                     parts = cmd.split()
#                     if len(parts) == 2:
#                         weighting = parts[1].capitalize()
#                         self.device.set_noise_suppression(weighting)
#                         print(f"✅ Noise suppression set to {weighting}")
#                     else:
#                         print("❌ Usage: suppress <off/low/medium/high>")
                
#                 # ========== Beam Commands ==========
#                 elif cmd == "beam status":
#                     beam = self.device.get_beam_position()
#                     print(f"🎯 Beam Position: {beam.get('position', 0)}°")
                
#                 # ========== Priority Zone Commands ==========
#                 elif cmd == "priority list":
#                     try:
#                         zones = self.device.get_priority_zones()
#                         print("\n🎯 PRIORITY ZONES:")
#                         print("-" * 60)
#                         if not zones:
#                             print("   No priority zones configured")
#                         else:
#                             for zone in zones:
#                                 status = "✅ ACTIVE" if zone.get('active') else "⭕ INACTIVE"
#                                 enabled = "🔵 ENABLED" if zone.get('enabled') else "⚪ DISABLED"
#                                 print(f"Zone {zone.get('id')}: {status} | {enabled}")
#                                 print(f"   Gain: {zone.get('gain', 'Medium')}")
#                                 print(f"   Range: {zone.get('left', 0)}° - {zone.get('right', 100)}°")
#                                 print("-" * 40)
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 elif cmd.startswith("priority get"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_priority_zones()
#                             zone_ids = [z.get('id') for z in zones]
#                             if zone_id in zone_ids:
#                                 zone = self.device.get_priority_zone(zone_id)
#                                 print(f"\n🎯 PRIORITY ZONE {zone_id}:")
#                                 print(f"   Active: {zone.get('active', False)}")
#                                 print(f"   Enabled: {zone.get('enabled', False)}")
#                                 print(f"   Gain: {zone.get('gain', 'Medium')}")
#                                 print(f"   Left Range: {zone.get('left', 0)}°")
#                                 print(f"   Right Range: {zone.get('right', 100)}°")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: priority get <zone_id>")
                
#                 elif cmd.startswith("priority on"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_priority_zones()
#                             zone_ids = [z.get('id') for z in zones]
#                             if zone_id in zone_ids:
#                                 self.device.enable_priority_zone(zone_id)
#                                 print(f"✅ Priority zone {zone_id} ENABLED")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: priority on <zone_id>")
                
#                 elif cmd.startswith("priority off"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_priority_zones()
#                             zone_ids = [z.get('id') for z in zones]
#                             if zone_id in zone_ids:
#                                 self.device.disable_priority_zone(zone_id)
#                                 print(f"✅ Priority zone {zone_id} DISABLED")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: priority off <zone_id>")
                
#                 elif cmd.startswith("priority gain"):
#                     parts = cmd.split()
#                     if len(parts) == 4:
#                         try:
#                             zone_id = int(parts[2])
#                             gain = parts[3].capitalize()
#                             zones = self.device.get_priority_zones()
#                             zone_ids = [z.get('id') for z in zones]
#                             if zone_id in zone_ids:
#                                 valid_gains = ["Off", "Low", "Medium", "High", "Min", "Mid", "Max"]
#                                 try:
#                                     gain_num = int(gain)
#                                     if 0 <= gain_num <= 100:
#                                         self.device.set_priority_zone_gain(zone_id, gain_num)
#                                         print(f"✅ Priority zone {zone_id} gain set to {gain_num}")
#                                     else:
#                                         print(f"❌ Gain must be between 0 and 100")
#                                 except ValueError:
#                                     if gain in valid_gains:
#                                         self.device.set_priority_zone_gain(zone_id, gain)
#                                         print(f"✅ Priority zone {zone_id} gain set to {gain}")
#                                         time.sleep(0.5)
#                                         updated_zone = self.device.get_priority_zone(zone_id)
#                                         print(f"   Verified: Gain is now {updated_zone.get('gain', 'Unknown')}")
#                                     else:
#                                         print(f"❌ Invalid gain. Valid values: Off, Low, Medium, High")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: priority gain <zone_id> <Off/Low/Medium/High or 0-100>")
                
#                 # ========== Priority Zone Range Command ==========
#                 elif cmd.startswith("priority range"):
#                     parts = cmd.split()
#                     if len(parts) == 5:
#                         try:
#                             zone_id = int(parts[2])
#                             left = int(parts[3])
#                             right = int(parts[4])
#                             zones = self.device.get_priority_zones()
#                             zone_ids = [z.get('id') for z in zones]
#                             if zone_id in zone_ids and 0 <= left <= 100 and 0 <= right <= 100:
#                                 self.device.set_priority_zone_range(zone_id, left, right)
#                                 print(f"✅ Priority zone {zone_id} range set to {left}° - {right}°")
#                                 time.sleep(0.5)
#                                 updated_zone = self.device.get_priority_zone(zone_id)
#                                 print(f"   Verified: Range is now {updated_zone.get('left', 0)}° - {updated_zone.get('right', 100)}°")
#                             else:
#                                 if zone_id not in zone_ids:
#                                     print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                                 if not (0 <= left <= 100 and 0 <= right <= 100):
#                                     print("❌ Range values must be between 0 and 100")
#                         except ValueError:
#                             print("❌ Invalid numbers. Usage: priority range <zone_id> <left 0-100> <right 0-100>")
#                     else:
#                         print("❌ Usage: priority range <zone_id> <left 0-100> <right 0-100>")
                
#                 # ========== Exclusion Zone Commands ==========
#                 elif cmd == "exclude list":
#                     try:
#                         zones = self.device.get_exclusion_zones()
#                         print("\n🚫 EXCLUSION ZONES:")
#                         print("-" * 60)
#                         if not zones:
#                             print("   No exclusion zones configured")
#                         else:
#                             for zone in zones:
#                                 status = "✅ ACTIVE" if zone.get('active') else "⭕ INACTIVE"
#                                 enabled = "🔵 ENABLED" if zone.get('enabled') else "⚪ DISABLED"
#                                 print(f"Zone {zone.get('id')}: {status} | {enabled}")
#                                 print(f"   Range: {zone.get('left', 0)}° - {zone.get('right', 100)}°")
#                                 print("-" * 40)
#                     except Exception as e:
#                         print(f"❌ Error: {e}")
                
#                 elif cmd.startswith("exclude get"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_exclusion_zones()
#                             zone_ids = [z.get('id') for z in zones]
#                             if zone_id in zone_ids:
#                                 zone = self.device.get_exclusion_zone(zone_id)
#                                 print(f"\n🚫 EXCLUSION ZONE {zone_id}:")
#                                 print(f"   Active: {zone.get('active', False)}")
#                                 print(f"   Enabled: {zone.get('enabled', False)}")
#                                 print(f"   Left Range: {zone.get('left', 0)}°")
#                                 print(f"   Right Range: {zone.get('right', 100)}°")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: exclude get <zone_id>")
                
#                 elif cmd.startswith("exclude on"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_exclusion_zones()
#                             zone_ids = [z.get('id') for z in zones]
#                             if zone_id in zone_ids:
#                                 self.device.enable_exclusion_zone(zone_id)
#                                 print(f"✅ Exclusion zone {zone_id} ENABLED")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: exclude on <zone_id>")
                
#                 elif cmd.startswith("exclude off"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             zone_id = int(parts[2])
#                             zones = self.device.get_exclusion_zones()
#                             zone_ids = [z.get('id') for z in zones]
#                             if zone_id in zone_ids:
#                                 self.device.disable_exclusion_zone(zone_id)
#                                 print(f"✅ Exclusion zone {zone_id} DISABLED")
#                             else:
#                                 print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                         except ValueError:
#                             print("❌ Invalid zone ID")
#                     else:
#                         print("❌ Usage: exclude off <zone_id>")
                
#                 elif cmd.startswith("exclude range"):
#                     parts = cmd.split()
#                     if len(parts) == 5:
#                         try:
#                             zone_id = int(parts[2])
#                             left = int(parts[3])
#                             right = int(parts[4])
#                             zones = self.device.get_exclusion_zones()
#                             zone_ids = [z.get('id') for z in zones]
#                             if zone_id in zone_ids and 0 <= left <= 100 and 0 <= right <= 100:
#                                 self.device.set_exclusion_zone_range(zone_id, left, right)
#                                 print(f"✅ Exclusion zone {zone_id} range set to {left}° - {right}°")
#                                 time.sleep(0.5)
#                                 updated_zone = self.device.get_exclusion_zone(zone_id)
#                                 print(f"   Verified: Range is now {updated_zone.get('left', 0)}° - {updated_zone.get('right', 100)}°")
#                             else:
#                                 if zone_id not in zone_ids:
#                                     print(f"❌ Zone ID {zone_id} not found. Available zones: {zone_ids}")
#                                 if not (0 <= left <= 100 and 0 <= right <= 100):
#                                     print("❌ Range values must be between 0 and 100")
#                         except ValueError:
#                             print("❌ Invalid numbers. Usage: exclude range <zone_id> <left 0-100> <right 0-100>")
#                     else:
#                         print("❌ Usage: exclude range <zone_id> <left 0-100> <right 0-100>")
                
#                 # ========== Camera Commands ==========
#                 elif cmd == "camera ai on":
#                     self.device.set_camera_ai_access(auto_framing=True)
#                     print("✅ Auto framing ENABLED")
                
#                 elif cmd == "camera ai off":
#                     self.device.set_camera_ai_access(auto_framing=False)
#                     print("✅ Auto framing DISABLED")
                
#                 elif cmd == "camera tiling on":
#                     self.device.set_camera_ai_access(person_tiling=True)
#                     print("✅ Person tiling ENABLED")
                
#                 elif cmd == "camera tiling off":
#                     self.device.set_camera_ai_access(person_tiling=False)
#                     print("✅ Person tiling DISABLED")
                
#                 elif cmd == "camera ffov":
#                     self.device.reset_camera_to_ffov()
#                     print("✅ Camera reset to full field of view")
                
#                 elif cmd == "camera preset store":
#                     self.device.store_camera_preset()
#                     print("✅ Camera preset STORED")
                
#                 elif cmd == "camera preset load":
#                     self.device.load_camera_preset()
#                     print("✅ Camera preset LOADED")
                
#                 elif cmd == "camera zoom in":
#                     self.device.move_camera_relative(zoom_in=1)
#                     print("✅ Zoom IN")
                
#                 elif cmd == "camera zoom out":
#                     self.device.move_camera_relative(zoom_out=1)
#                     print("✅ Zoom OUT")
                
#                 elif cmd.startswith("camera move"):
#                     parts = cmd.split()
#                     if len(parts) >= 3:
#                         direction = parts[2]
#                         steps = 1
#                         if len(parts) > 3:
#                             try:
#                                 steps = int(parts[3])
#                             except ValueError:
#                                 steps = 1
#                         if direction == "up":
#                             self.device.move_camera_relative(up=steps)
#                             print(f"✅ Camera moved UP by {steps}")
#                         elif direction == "down":
#                             self.device.move_camera_relative(down=steps)
#                             print(f"✅ Camera moved DOWN by {steps}")
#                         elif direction == "left":
#                             self.device.move_camera_relative(left=steps)
#                             print(f"✅ Camera moved LEFT by {steps}")
#                         elif direction == "right":
#                             self.device.move_camera_relative(right=steps)
#                             print(f"✅ Camera moved RIGHT by {steps}")
#                         else:
#                             print("❌ Direction must be: up, down, left, right")
#                     else:
#                         print("❌ Usage: camera move <up/down/left/right> [steps]")
                
#                 # ========== LED Commands ==========
#                 elif cmd.startswith("led bright"):
#                     parts = cmd.split()
#                     if len(parts) == 3:
#                         try:
#                             brightness = int(parts[2])
#                             if 0 <= brightness <= 5:
#                                 self.device.set_led_brightness(brightness)
#                                 print(f"✅ LED brightness set to {brightness}")
#                             else:
#                                 print("❌ Brightness must be 0-5")
#                         except ValueError:
#                             print("❌ Invalid brightness value")
                
#                 elif cmd == "led status":
#                     led = self.device.get_led_ring()
#                     print(f"💡 LED Brightness: {led.get('brightness', 3)}")
                
#                 # ========== Network Commands ==========
#                 elif cmd == "network status":
#                     network = self.device.get_network_interfaces()
#                     print("\n🌐 NETWORK INTERFACES:")
#                     print(json.dumps(network, indent=2))
                
#                 elif cmd == "dante status":
#                     dante = self.device.get_dante_status()
#                     print(f"🎵 Dante Enabled: {dante.get('enabled', False)}")
                
#                 elif cmd == "bluetooth on":
#                     self.device.set_bluetooth_settings(enabled=True)
#                     print("✅ Bluetooth ENABLED")
                
#                 elif cmd == "bluetooth off":
#                     self.device.set_bluetooth_settings(enabled=False)
#                     print("✅ Bluetooth DISABLED")
                
#                 elif cmd == "wifi status":
#                     wifi = self.device.get_wifi_status()
#                     print(f"📡 WiFi Enabled: {wifi.get('enabled', False)}")
#                     print(f"   State: {wifi.get('state', 'Unknown')}")
                
#                 # ========== Device Commands ==========
#                 elif cmd.startswith("site name"):
#                     parts = cmd.split(maxsplit=2)
#                     if len(parts) >= 3:
#                         name = parts[2]
#                         self.device.set_device_site(device_name=name)
#                         print(f"✅ Device name set to {name}")
#                     else:
#                         print("❌ Usage: site name <name>")
                
#                 elif cmd.startswith("site location"):
#                     parts = cmd.split(maxsplit=2)
#                     if len(parts) >= 3:
#                         location = parts[2]
#                         self.device.set_device_site(location=location)
#                         print(f"✅ Location set to {location}")
#                     else:
#                         print("❌ Usage: site location <location>")
                
#                 elif cmd == "sound prompts on":
#                     self.device.set_sound_prompts(True)
#                     print("✅ Sound prompts ENABLED")
                
#                 elif cmd == "sound prompts off":
#                     self.device.set_sound_prompts(False)
#                     print("✅ Sound prompts DISABLED")
                
#                 elif cmd == "identify on":
#                     self.device.identify_device(True)
#                     print("✅ Device identification started - LEDs will blink for 5 seconds")
#                     threading.Timer(5.0, lambda: self.device.identify_device(False)).start()
                
#                 elif cmd == "identify off":
#                     self.device.identify_device(False)
#                     print("✅ Device identification stopped")
                
#                 elif cmd == "restart":
#                     confirm = input("⚠️ Are you sure you want to restart the device? (yes/no): ")
#                     if confirm.lower() == "yes":
#                         self.device.restart_device()
#                         print("🔄 Device restarting...")
#                     else:
#                         print("Restart cancelled")
                
#                 elif cmd.startswith("profile"):
#                     parts = cmd.split()
#                     if len(parts) == 2:
#                         profile = parts[1].capitalize()
#                         if profile in ["Custom", "MicrosoftTeams"]:
#                             self.device.set_device_profile(profile)
#                             print(f"✅ Device profile set to {profile}")
#                         else:
#                             print("❌ Profile must be 'custom' or 'teams'")
#                     else:
#                         print("❌ Usage: profile <custom/teams>")
                
#                 # ========== Monitoring Commands ==========
#                 elif cmd == "status":
#                     info = self.device.get_complete_device_info()
#                     print("\n📱 DETAILED DEVICE STATUS:")
#                     print(json.dumps(info, indent=2, default=str))
                
#                 elif cmd == "firmware":
#                     fw = self.device.get_firmware_update_state()
#                     print(f"\n📦 FIRMWARE:")
#                     print(f"   Device Version: {fw.get('deviceVersion', 'Unknown')}")
#                     print(f"   State: {fw.get('state', 'Idle')}")
#                     if fw.get('state') != 'Idle':
#                         print(f"   Progress: {fw.get('progress', 0)}%")
                
#                 elif cmd == "monitor":
#                     if not self.monitoring_active:
#                         self.monitoring_active = True
#                         self.device.start_monitoring(1.0, self.display_metrics)
#                         print("\n✅ Real-time monitoring started")
#                     else:
#                         print("⚠️ Monitoring already active")
                
#                 elif cmd == "stop":
#                     if self.monitoring_active:
#                         self.device.stop_monitoring()
#                         self.monitoring_active = False
#                         print("✅ Monitoring stopped")
                
#                 elif cmd == "info":
#                     info = self.device.get_complete_device_info()
#                     print("\n📱 COMPLETE DEVICE INFO:")
#                     print(json.dumps(info, indent=2, default=str))
                
#                 else:
#                     print("❌ Unknown command")
                    
#             except Exception as e:
#                 print(f"❌ Error: {e}")


# # ========== Main Entry Point ==========

# def get_user_credentials():
#     """Get device connection details from user"""
#     print("\n" + "=" * 60)
#     print(" SENNHEISER TEAMCONNECT BAR M DEVICE CONNECTION SETUP")
#     print("=" * 60)
    
#     device_ip = input("\n🔌 Enter Device IP Address: ").strip()
#     username = input("👤 Enter Username (default: api): ").strip() or "api"
#     password = getpass.getpass("🔑 Enter Password: ").strip()
    
#     return device_ip, username, password


# def validate_connection(device_ip, username, password):
#     """Validate the connection with provided credentials"""
#     print("\n🔍 Validating connection...")
    
#     test_device = SennheiserTCBarMPlugin(device_ip, username, password)
    
#     try:
#         identity = test_device.get_device_identity()
#         if identity and 'product' in identity:
#             print(f"   ✅ Connection successful!")
#             print(f"   📱 Device: {identity.get('product')}")
#             print(f"   🔢 Serial: {identity.get('serial')}")
#             return True, test_device
#         return False, None
#     except Exception as e:
#         print(f"   ❌ Connection failed: {e}")
#         return False, None


# def main():
#     """Main entry point"""
#     print("\n" + "=" * 60)
#     print(" SENNHEISER TEAMCONNECT BAR M DEVICE CONTROL PLUGIN")
#     print("=" * 60)
    
#     device_ip, username, password = get_user_credentials()
#     success, device = validate_connection(device_ip, username, password)
    
#     if not success:
#         print("\n❌ Failed to connect. Please check:")
#         print("   1. Device IP address is correct")
#         print("   2. 3rd Party Access is enabled in device settings")
#         print("   3. Username and password are correct")
#         return
    
#     print("\n✅ CONNECTION ESTABLISHED - LAUNCHING CONTROL INTERFACE")
#     controller = SennheiserTCBarMController(device_ip, username, password)
    
#     try:
#         controller.run_interactive_menu()
#     except KeyboardInterrupt:
#         print("\n\n👋 Goodbye!")
#     except Exception as e:
#         print(f"\n❌ Error: {e}")


# if __name__ == "__main__":
#     main()



#BEFORE CAMERA CONTROL Working

#!/usr/bin/env python3
"""
Sennheiser TC Bar M Device Control Plugin - Complete API Integration
Based on SSC v2 API (Schema 1.0, Protocol 2.3)
"""

import urllib.request
import urllib.error
import ssl
import json
import base64
import time
import threading
import getpass
import sys
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# ========== Enums ==========

class NoiseSuppressionWeighting(Enum):
    OFF = "Off"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class SoundProfilePreset(Enum):
    WALLMOUNT = "Wallmount"
    CEILING_MOUNT = "CeilingMount"
    CUSTOM = "Custom"

class DeviceProfile(Enum):
    CUSTOM = "Custom"
    MICROSOFT_TEAMS = "MicrosoftTeams"

class ZoneGain(Enum):
    OFF = "Off"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class AntiFlickerFrequency(Enum):
    AUTO = "Auto"
    HZ50 = "50Hz"
    HZ60 = "60Hz"

class Speed(Enum):
    SLOW = "Slow"
    MEDIUM = "Medium"
    FAST = "Fast"


# ========== Data Classes ==========

@dataclass
class DeviceMetrics:
    timestamp: datetime
    microphone_level: int
    mute_status: Optional[bool]
    beam_position: int
    active_channel: str
    speaker_volume: int
    usb_input_level: int
    bluetooth_input_level: int

@dataclass
class PriorityZoneSettings:
    id: int
    active: bool
    enabled: bool
    gain: str
    left_deg: int
    right_deg: int
    timestamp: datetime

@dataclass
class ExclusionZoneSettings:
    id: int
    active: bool
    enabled: bool
    left_deg: int
    right_deg: int
    timestamp: datetime

@dataclass
class CameraVideoParameters:
    brightness: int
    contrast: int
    saturation: int
    sharpness: int
    auto_whitebalance: bool
    whitebalance: int
    anti_flicker: str
    backlight_compensation: bool
    lowlight_compensation: bool

@dataclass
class CameraMovement:
    pan: int
    tilt: int
    zoom: int
    zoom_speed: str
    pan_tilt_speed: str
    auto_framing_speed: str


# ========== Main Plugin Class ==========

class SennheiserTCBarMPlugin:
    """Complete plugin for Sennheiser TeamConnect Bar M with all API endpoints"""
    
    def __init__(self, device_ip: str, username: str, password: str, verify_ssl: bool = False):
        self.device_ip = device_ip
        self.base_url = f"https://{device_ip}/api"
        self.username = username
        self.password = password
        
        auth_string = f"{username}:{password}"
        auth_bytes = auth_string.encode('utf-8')
        self.auth_header = base64.b64encode(auth_bytes).decode('ascii')
        
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self.monitoring = False
        self.monitor_thread = None
        self.metrics_history = []
        self.callbacks = []
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {self.auth_header}"
        }
        
        if data and method in ["PUT", "POST"]:
            headers["Content-Type"] = "application/json"
            request_data = json.dumps(data).encode('utf-8')
        else:
            request_data = None
        
        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
        
        try:
            response = urllib.request.urlopen(req, context=self.ssl_context, timeout=10)
            response_data = response.read().decode('utf-8')
            return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise Exception("Authentication failed - Invalid username or password")
            elif e.code == 403:
                raise Exception("Forbidden - Check 3rd party access settings")
            error_msg = e.read().decode('utf-8') if e.fp else str(e)
            return {"error": f"HTTP {e.code}", "message": error_msg}
        except Exception as e:
            return {"error": str(e)}
    
    # ========== Helper Methods ==========
    
    def _deg_to_scale(self, degrees: float) -> int:
        """Convert degrees (0-180) to scale (0-100)"""
        return int(round(degrees * 100 / 180))
    
    def _scale_to_deg(self, scale: int) -> int:
        """Convert scale (0-100) to degrees (0-180)"""
        return int(round(scale * 180 / 100))
    
    # ========== Device Information Methods ==========
    
    def get_device_identity(self) -> Dict[str, Any]:
        return self._make_request("GET", "/device/identity")
    
    def get_device_state(self) -> Dict[str, Any]:
        return self._make_request("GET", "/device/state")
    
    def get_device_profile(self) -> Dict[str, Any]:
        return self._make_request("GET", "/device/profile")
    
    def set_device_profile(self, configuration: str) -> Dict[str, Any]:
        valid_profiles = ["Custom", "MicrosoftTeams"]
        if configuration not in valid_profiles:
            raise Exception(f"Invalid profile. Must be one of: {valid_profiles}")
        return self._make_request("PUT", "/device/profile", data={"configuration": configuration})
    
    def get_device_site(self) -> Dict[str, Any]:
        return self._make_request("GET", "/device/site")
    
    def set_device_site(self, device_name: str = None, location: str = None) -> Dict[str, Any]:
        current = self.get_device_site()
        data = {
            "deviceName": device_name if device_name else current.get('deviceName'),
            "location": location if location else current.get('location', ''),
            "language": current.get('language', 'En_GB')
        }
        return self._make_request("PUT", "/device/site", data=data)
    
    def identify_device(self, enable: bool = True) -> Dict[str, Any]:
        return self._make_request("PUT", "/device/identification", data={"visual": enable})
    
    def restart_device(self) -> Dict[str, Any]:
        return self._make_request("PUT", "/device/restart")
    
    # ========== LED Control Methods ==========
    
    def get_led_ring(self) -> Dict[str, Any]:
        return self._make_request("GET", "/device/leds/ring")
    
    def set_led_brightness(self, brightness: int) -> Dict[str, Any]:
        if not 0 <= brightness <= 5:
            raise Exception("Brightness must be between 0 and 5")
        return self._make_request("PUT", "/device/leds/ring", data={"brightness": brightness})
    
    # ========== Audio Methods ==========
    
    def get_internal_mic(self) -> Dict[str, Any]:
        return self._make_request("GET", "/audio/inputs/internalMic")
    
    def set_internal_mic(self, gain: int = None, enabled: bool = None) -> Dict[str, Any]:
        current = self.get_internal_mic()
        data = {
            "gain": gain if gain is not None else current.get('gain', 0),
            "enabled": enabled if enabled is not None else current.get('enabled', True)
        }
        if data["gain"] < -30 or data["gain"] > 30:
            raise Exception("Gain must be between -30 and 30 dB")
        return self._make_request("PUT", "/audio/inputs/internalMic", data=data)
    
    def get_mic_mute(self) -> Dict[str, Any]:
        return self._make_request("GET", "/audio/inputs/mute")
    
    def set_mic_mute(self, enabled: bool) -> Dict[str, Any]:
        return self._make_request("PUT", "/audio/inputs/mute", data={"enabled": enabled})
    
    def mute(self) -> Dict[str, Any]:
        return self.set_mic_mute(True)
    
    def unmute(self) -> Dict[str, Any]:
        return self.set_mic_mute(False)
    
    def get_speaker_output(self) -> Dict[str, Any]:
        return self._make_request("GET", "/audio/outputs/speaker")
    
    def set_volume(self, volume: int) -> Dict[str, Any]:
        if volume < 0 or volume > 100:
            raise Exception("Volume must be between 0 and 100")
        return self._make_request("PUT", "/audio/outputs/speaker", data={"volume": volume})
    
    def volume_up(self, steps: int = 5) -> Dict[str, Any]:
        return self._make_request("PUT", "/audio/outputs/speaker/relative", data={"volumeUp": steps})
    
    def volume_down(self, steps: int = 5) -> Dict[str, Any]:
        return self._make_request("PUT", "/audio/outputs/speaker/relative", data={"volumeDown": steps})
    
    def get_noise_gate(self) -> Dict[str, Any]:
        return self._make_request("GET", "/audio/inputs/internalMic/noiseGate")
    
    def set_noise_gate(self, enabled: bool = None, threshold: int = None, 
                       hold_time: int = None, range_val: int = None) -> Dict[str, Any]:
        current = self.get_noise_gate()
        data = {
            "enabled": enabled if enabled is not None else current.get('enabled', False),
            "threshold": threshold if threshold is not None else current.get('threshold', -40),
            "holdTime": hold_time if hold_time is not None else current.get('holdTime', 300),
            "range": range_val if range_val is not None else current.get('range', -40)
        }
        return self._make_request("PUT", "/audio/inputs/internalMic/noiseGate", data=data)
    
    def get_noise_suppression(self) -> Dict[str, Any]:
        return self._make_request("GET", "/audio/inputs/noiseSuppression")
    
    def set_noise_suppression(self, weighting: str) -> Dict[str, Any]:
        valid_weightings = ["Off", "Low", "Medium", "High"]
        if weighting not in valid_weightings:
            raise Exception(f"Invalid weighting. Must be one of: {valid_weightings}")
        return self._make_request("PUT", "/audio/inputs/noiseSuppression", data={"weighting": weighting})
    
    def get_sound_prompts(self) -> Dict[str, Any]:
        return self._make_request("GET", "/device/feedback")
    
    def set_sound_prompts(self, enabled: bool) -> Dict[str, Any]:
        return self._make_request("PUT", "/device/feedback", data={"soundPrompts": enabled})
    
    # ========== Zone Methods ==========
    
    def get_priority_zones(self) -> List[Dict[str, Any]]:
        return self._make_request("GET", "/audio/inputs/internalMic/priorityZones")
    
    def get_priority_zone(self, zone_id: int) -> Dict[str, Any]:
        return self._make_request("GET", f"/audio/inputs/internalMic/priorityZones/{zone_id}")
    
    def set_priority_zone(self, zone_id: int, enabled: bool = None, 
                          gain: str = None, left_deg: int = None, right_deg: int = None) -> Dict[str, Any]:
        current = self.get_priority_zone(zone_id)
        
        left_scale = self._deg_to_scale(left_deg) if left_deg is not None else None
        right_scale = self._deg_to_scale(right_deg) if right_deg is not None else None
        
        data = {
            "enabled": enabled if enabled is not None else current.get('enabled', False),
            "gain": gain if gain is not None else current.get('gain', 'Medium'),
            "left": left_scale if left_scale is not None else current.get('left', 0),
            "right": right_scale if right_scale is not None else current.get('right', 100)
        }
        return self._make_request("PUT", f"/audio/inputs/internalMic/priorityZones/{zone_id}", data=data)
    
    def enable_priority_zone(self, zone_id: int) -> Dict[str, Any]:
        return self.set_priority_zone(zone_id, enabled=True)
    
    def disable_priority_zone(self, zone_id: int) -> Dict[str, Any]:
        return self.set_priority_zone(zone_id, enabled=False)
    
    def set_priority_zone_gain(self, zone_id: int, gain: str) -> Dict[str, Any]:
        valid_gains = ["Off", "Low", "Medium", "High"]
        if gain not in valid_gains:
            raise Exception(f"Invalid gain. Must be one of: {valid_gains}")
        return self.set_priority_zone(zone_id, gain=gain)
    
    def set_priority_zone_range(self, zone_id: int, left_deg: int, right_deg: int) -> Dict[str, Any]:
        if not 0 <= left_deg <= 180 or not 0 <= right_deg <= 180:
            raise Exception("Degrees must be between 0 and 180")
        if left_deg > right_deg:
            left_deg, right_deg = right_deg, left_deg
        return self.set_priority_zone(zone_id, left_deg=left_deg, right_deg=right_deg)
    
    def get_exclusion_zones(self) -> List[Dict[str, Any]]:
        return self._make_request("GET", "/audio/inputs/internalMic/exclusionZones")
    
    def get_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
        return self._make_request("GET", f"/audio/inputs/internalMic/exclusionZones/{zone_id}")
    
    def set_exclusion_zone(self, zone_id: int, enabled: bool = None, 
                           left_deg: int = None, right_deg: int = None) -> Dict[str, Any]:
        current = self.get_exclusion_zone(zone_id)
        
        left_scale = self._deg_to_scale(left_deg) if left_deg is not None else None
        right_scale = self._deg_to_scale(right_deg) if right_deg is not None else None
        
        data = {
            "enabled": enabled if enabled is not None else current.get('enabled', False),
            "left": left_scale if left_scale is not None else current.get('left', 0),
            "right": right_scale if right_scale is not None else current.get('right', 100)
        }
        return self._make_request("PUT", f"/audio/inputs/internalMic/exclusionZones/{zone_id}", data=data)
    
    def enable_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
        return self.set_exclusion_zone(zone_id, enabled=True)
    
    def disable_exclusion_zone(self, zone_id: int) -> Dict[str, Any]:
        return self.set_exclusion_zone(zone_id, enabled=False)
    
    def set_exclusion_zone_range(self, zone_id: int, left_deg: int, right_deg: int) -> Dict[str, Any]:
        if not 0 <= left_deg <= 180 or not 0 <= right_deg <= 180:
            raise Exception("Degrees must be between 0 and 180")
        if left_deg > right_deg:
            left_deg, right_deg = right_deg, left_deg
        return self.set_exclusion_zone(zone_id, left_deg=left_deg, right_deg=right_deg)
    
    # ========== Beam Methods ==========
    
    def get_beam_position(self) -> Dict[str, Any]:
        return self._make_request("GET", "/audio/inputs/internalMic/beam")
    
    # ========== Camera Video Parameters Methods ==========
    
    def get_camera_video_parameters(self) -> Dict[str, Any]:
        """GET /api/video/input/internalCamera/videoParameters - Get video parameters"""
        return self._make_request("GET", "/video/input/internalCamera/videoParameters")
    
    def set_camera_video_parameters(self, brightness: int = None, contrast: int = None,
                                     saturation: int = None, sharpness: int = None,
                                     auto_whitebalance: bool = None, whitebalance: int = None,
                                     anti_flicker: str = None, backlight_compensation: bool = None,
                                     lowlight_compensation: bool = None) -> Dict[str, Any]:
        """PUT /api/video/input/internalCamera/videoParameters - Set video parameters"""
        current = self.get_camera_video_parameters()
        
        data = {
            "brightness": brightness if brightness is not None else current.get('brightness', 0),
            "contrast": contrast if contrast is not None else current.get('contrast', 5),
            "saturation": saturation if saturation is not None else current.get('saturation', 5),
            "sharpness": sharpness if sharpness is not None else current.get('sharpness', 2),
            "autoWhitebalanceEnabled": auto_whitebalance if auto_whitebalance is not None else current.get('autoWhitebalanceEnabled', True),
            "whitebalance": whitebalance if whitebalance is not None else current.get('whitebalance', 4600),
            "antiFlickerFrequency": anti_flicker if anti_flicker is not None else current.get('antiFlickerFrequency', 'Auto'),
            "backlightCompensationEnabled": backlight_compensation if backlight_compensation is not None else current.get('backlightCompensationEnabled', True),
            "lowlightCompensationEnabled": lowlight_compensation if lowlight_compensation is not None else current.get('lowlightCompensationEnabled', False)
        }
        return self._make_request("PUT", "/video/input/internalCamera/videoParameters", data=data)
    
    # ========== Camera Movement Methods ==========
    
    def get_camera_movement(self) -> Dict[str, Any]:
        """GET /api/video/input/internalCamera/movement - Get camera movement settings"""
        return self._make_request("GET", "/video/input/internalCamera/movement")
    
    def set_camera_movement(self, pan: int = None, tilt: int = None, zoom: int = None,
                            zoom_speed: str = None, pan_tilt_speed: str = None,
                            auto_framing_speed: str = None) -> Dict[str, Any]:
        """PUT /api/video/input/internalCamera/movement - Set camera movement"""
        current = self.get_camera_movement()
        
        data = {
            "panPosition": pan if pan is not None else current.get('panPosition', 0),
            "tiltPosition": tilt if tilt is not None else current.get('tiltPosition', 0),
            "zoomPosition": zoom if zoom is not None else current.get('zoomPosition', 100),
            "zoomSpeed": zoom_speed if zoom_speed is not None else current.get('zoomSpeed', 'Medium'),
            "panTiltSpeed": pan_tilt_speed if pan_tilt_speed is not None else current.get('panTiltSpeed', 'Medium'),
            "autoFramingSpeed": auto_framing_speed if auto_framing_speed is not None else current.get('autoFramingSpeed', 'Medium')
        }
        return self._make_request("PUT", "/video/input/internalCamera/movement", data=data)
    
    # ========== Camera Status Methods ==========
    
    def get_camera_status(self) -> Dict[str, Any]:
        """GET /api/video/input/internalCamera - Get camera active status"""
        return self._make_request("GET", "/video/input/internalCamera")
    
    def get_camera_ai_access(self) -> Dict[str, Any]:
        """GET /api/video/input/internalCamera/aiAccess - Get AI features status"""
        return self._make_request("GET", "/video/input/internalCamera/aiAccess")
    
    def set_camera_ai_access(self, auto_framing: bool = None, person_tiling: bool = None) -> Dict[str, Any]:
        """PUT /api/video/input/internalCamera/aiAccess - Set AI features"""
        current = self.get_camera_ai_access()
        data = {
            "autoFramingAccessEnabled": current.get('autoFramingAccessEnabled', True),
            "autoFramingEnabled": auto_framing if auto_framing is not None else current.get('autoFramingEnabled', False),
            "personTilingAccessEnabled": current.get('personTilingAccessEnabled', True),
            "personTilingEnabled": person_tiling if person_tiling is not None else current.get('personTilingEnabled', False)
        }
        return self._make_request("PUT", "/video/input/internalCamera/aiAccess", data=data)
    
    def reset_camera_to_ffov(self) -> Dict[str, Any]:
        """PUT /api/video/input/internalCamera/ffov - Reset to full field of view"""
        return self._make_request("PUT", "/video/input/internalCamera/ffov")
    
    def store_camera_preset(self) -> Dict[str, Any]:
        """PUT /api/video/input/internalCamera/preset/store - Store current camera preset"""
        return self._make_request("PUT", "/video/input/internalCamera/preset/store")
    
    def load_camera_preset(self) -> Dict[str, Any]:
        """PUT /api/video/input/internalCamera/preset/load - Load camera preset"""
        return self._make_request("PUT", "/video/input/internalCamera/preset/load")
    
    def move_camera_relative(self, up: int = 0, down: int = 0, left: int = 0, 
                              right: int = 0, zoom_in: int = 0, zoom_out: int = 0) -> Dict[str, Any]:
        """PUT /api/video/input/internalCamera/movement/relative - Move camera relatively"""
        if zoom_in > 0 and zoom_out > 0:
            raise Exception("Cannot specify both zoom_in and zoom_out")
        data = {"up": up, "down": down, "left": left, "right": right, "zoomIn": zoom_in, "zoomOut": zoom_out}
        return self._make_request("PUT", "/video/input/internalCamera/movement/relative", data=data)
    
    def get_hdmi_enabled(self) -> Dict[str, Any]:
        """GET /api/video/output/hdmi - Get HDMI status"""
        return self._make_request("GET", "/video/output/hdmi")
    
    # ========== Network Methods ==========
    
    def get_network_interfaces(self) -> Dict[str, Any]:
        return self._make_request("GET", "/interfaces/network")
    
    def get_dante_status(self) -> Dict[str, Any]:
        return self._make_request("GET", "/interfaces/network/dante")
    
    def get_bluetooth_settings(self) -> Dict[str, Any]:
        return self._make_request("GET", "/interfaces/bluetooth")
    
    def set_bluetooth_settings(self, enabled: bool = None) -> Dict[str, Any]:
        current = self.get_bluetooth_settings()
        data = {"enabled": enabled if enabled is not None else current.get('enabled', False)}
        return self._make_request("PUT", "/interfaces/bluetooth", data=data)
    
    def get_wifi_status(self) -> Dict[str, Any]:
        return self._make_request("GET", "/interfaces/network/wifi")
    
    # ========== Firmware Methods ==========
    
    def get_firmware_update_state(self) -> Dict[str, Any]:
        return self._make_request("GET", "/firmware/update/state")
    
    # ========== Real-time Monitoring ==========
    
    def get_all_metrics(self) -> DeviceMetrics:
        mic_level = self._make_request("GET", "/audio/inputs/internalMic/level")
        mute = self.get_mic_mute()
        beam = self.get_beam_position()
        active = self._make_request("GET", "/audio/inputs/mixer/activity")
        speaker = self.get_speaker_output()
        usb_level = self._make_request("GET", "/audio/inputs/usb")
        bt_level = self._make_request("GET", "/audio/inputs/bluetooth")
        
        return DeviceMetrics(
            timestamp=datetime.now(),
            microphone_level=mic_level.get('peak', 0) if isinstance(mic_level, dict) else 0,
            mute_status=mute.get('enabled') if isinstance(mute, dict) else None,
            beam_position=beam.get('position', 0) if isinstance(beam, dict) else 0,
            active_channel=active.get('activeChannel', 'Unknown') if isinstance(active, dict) else 'Unknown',
            speaker_volume=speaker.get('volume', 50) if isinstance(speaker, dict) else 50,
            usb_input_level=usb_level.get('level', 0) if isinstance(usb_level, dict) else 0,
            bluetooth_input_level=bt_level.get('level', 0) if isinstance(bt_level, dict) else 0
        )
    
    def start_monitoring(self, interval: float = 1.0, callback: Optional[Callable] = None):
        if callback:
            self.callbacks.append(callback)
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            print(f"✅ Monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("✅ Monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        while self.monitoring:
            try:
                metrics = self.get_all_metrics()
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]
                for callback in self.callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        print(f"Callback error: {e}")
                time.sleep(interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(interval)
    
    def get_complete_device_info(self) -> Dict[str, Any]:
        identity = self.get_device_identity()
        firmware = self.get_firmware_update_state()
        state = self.get_device_state()
        led = self.get_led_ring()
        site = self.get_device_site()
        beam = self.get_beam_position()
        mic = self.get_internal_mic()
        speaker = self.get_speaker_output()
        noise_gate = self.get_noise_gate()
        noise_suppression = self.get_noise_suppression()
        camera_ai = self.get_camera_ai_access()
        camera_video = self.get_camera_video_parameters()
        camera_movement = self.get_camera_movement()
        network = self.get_network_interfaces()
        bluetooth = self.get_bluetooth_settings()
        wifi = self.get_wifi_status()
        priority_zones = self.get_priority_zones()
        exclusion_zones = self.get_exclusion_zones()
        
        return {
            "identity": identity,
            "firmware": firmware,
            "state": state,
            "led_settings": led,
            "site_info": site,
            "beam_position": beam,
            "microphone": mic,
            "speaker": speaker,
            "noise_gate": noise_gate,
            "noise_suppression": noise_suppression,
            "camera": {
                "ai_access": camera_ai,
                "video_parameters": camera_video,
                "movement": camera_movement
            },
            "network": network,
            "bluetooth": bluetooth,
            "wifi": wifi,
            "priority_zones": priority_zones,
            "exclusion_zones": exclusion_zones,
            "timestamp": datetime.now().isoformat(),
            "ip": self.device_ip
        }


# ========== Interactive Controller ==========

class SennheiserTCBarMController:
    """Interactive controller for TeamConnect Bar M"""
    
    def __init__(self, device_ip: str, username: str, password: str):
        self.device = SennheiserTCBarMPlugin(device_ip, username, password)
        self.monitoring_active = False
        self.device_ip = device_ip
    
    def display_metrics(self, metrics: DeviceMetrics):
        mute_display = "🔴 MUTED" if metrics.mute_status else "🟢 LIVE"
        print(f"\r📊 [{metrics.timestamp.strftime('%H:%M:%S')}] "
              f"Mic: {metrics.microphone_level}dB | "
              f"Beam: {metrics.beam_position}° | "
              f"Volume: {metrics.speaker_volume}% | "
              f"Active: {metrics.active_channel} | "
              f"Mute: {mute_display}", end="")
    
    def run_interactive_menu(self):
        while True:
            print("\n" + "=" * 70)
            print(f" SENNHEISER TEAMCONNECT BAR M - COMPLETE CONTROL SYSTEM ({self.device_ip})")
            print("=" * 70)
            print("\n📊 CURRENT STATUS:")
            
            try:
                metrics = self.device.get_all_metrics()
                identity = self.device.get_device_identity()
                state = self.device.get_device_state()
                site = self.device.get_device_site()
                mic = self.device.get_internal_mic()
                speaker = self.device.get_speaker_output()
                noise_gate = self.device.get_noise_gate()
                noise_suppression = self.device.get_noise_suppression()
                beam = self.device.get_beam_position()
                camera_ai = self.device.get_camera_ai_access()
                camera_video = self.device.get_camera_video_parameters()
                camera_movement = self.device.get_camera_movement()
                firmware = self.device.get_firmware_update_state()
                
                print(f"\n📱 DEVICE: {identity.get('product', 'TC Bar M')}")
                print(f"   Serial: {identity.get('serial', 'Unknown')}")
                print(f"   State: {state.get('state', 'Unknown')}")
                print(f"   Firmware: {firmware.get('deviceVersion', 'Unknown')}")
                
                print(f"\n📍 SITE:")
                print(f"   Name: {site.get('deviceName', 'Unknown')}")
                print(f"   Location: {site.get('location', 'Unknown')}")
                
                print(f"\n🎤 AUDIO:")
                print(f"   Mic Level: {metrics.microphone_level} dB")
                print(f"   Mic Enabled: {'✅' if mic.get('enabled') else '❌'}")
                print(f"   Mic Gain: {mic.get('gain', 0)} dB")
                mute_display = "🔴 MUTED" if metrics.mute_status else "🟢 LIVE"
                print(f"   Mute Status: {mute_display}")
                print(f"   Speaker Volume: {speaker.get('volume', 50)}%")
                print(f"   Active Channel: {metrics.active_channel}")
                
                print(f"\n🎯 BEAMFORMING:")
                print(f"   Beam Position: {beam.get('position', 0)}°")
                
                print(f"\n🔧 PROCESSING:")
                print(f"   Noise Gate: {'✅' if noise_gate.get('enabled') else '❌'}")
                print(f"   Noise Suppression: {noise_suppression.get('weighting', 'Medium')}")
                
                print(f"\n📷 CAMERA AI:")
                print(f"   Auto Framing: {'✅' if camera_ai.get('autoFramingEnabled') else '❌'}")
                print(f"   Person Tiling: {'✅' if camera_ai.get('personTilingEnabled') else '❌'}")
                
                print(f"\n🎨 CAMERA VIDEO:")
                print(f"   Brightness: {camera_video.get('brightness', 0)}")
                print(f"   Contrast: {camera_video.get('contrast', 5)}")
                print(f"   Saturation: {camera_video.get('saturation', 5)}")
                print(f"   Sharpness: {camera_video.get('sharpness', 2)}")
                wb_mode = "Auto" if camera_video.get('autoWhitebalanceEnabled') else "Manual"
                wb_val = camera_video.get('whitebalance', 4600)
                print(f"   White Balance: {wb_mode} ({wb_val}K)" if not camera_video.get('autoWhitebalanceEnabled') else f"   White Balance: {wb_mode}")
                print(f"   Anti-flicker: {camera_video.get('antiFlickerFrequency', 'Auto')}")
                
                print(f"\n🎥 CAMERA MOVEMENT:")
                print(f"   Pan: {camera_movement.get('panPosition', 0)}°")
                print(f"   Tilt: {camera_movement.get('tiltPosition', 0)}°")
                print(f"   Zoom: {camera_movement.get('zoomPosition', 100)}%")
                print(f"   Zoom Speed: {camera_movement.get('zoomSpeed', 'Medium')}")
                print(f"   Pan/Tilt Speed: {camera_movement.get('panTiltSpeed', 'Medium')}")
                print(f"   Auto Framing Speed: {camera_movement.get('autoFramingSpeed', 'Medium')}")
                
                # Display zones
                pzones = self.device.get_priority_zones()
                if pzones:
                    print(f"\n🎯 PRIORITY ZONES:")
                    for zone in pzones:
                        left_deg = self.device._scale_to_deg(zone.get('left', 0))
                        right_deg = self.device._scale_to_deg(zone.get('right', 100))
                        print(f"   Zone {zone.get('id')}: {'✅ ACTIVE' if zone.get('active') else '⭕ INACTIVE'} | "
                              f"Gain: {zone.get('gain', 'Medium')} | Range: {left_deg}°-{right_deg}°")
                
                ezones = self.device.get_exclusion_zones()
                if ezones:
                    print(f"\n🚫 EXCLUSION ZONES:")
                    for zone in ezones:
                        left_deg = self.device._scale_to_deg(zone.get('left', 0))
                        right_deg = self.device._scale_to_deg(zone.get('right', 100))
                        print(f"   Zone {zone.get('id')}: {'✅ ACTIVE' if zone.get('active') else '⭕ INACTIVE'} | "
                              f"Range: {left_deg}°-{right_deg}°")
                
            except Exception as e:
                print(f"   ⚠️ Error getting status: {e}")
            
            print("\n" + "=" * 70)
            print("🎮 CONTROL COMMANDS:")
            
            print("\n📢 AUDIO CONTROLS:")
            print("  mute on/off           - Mute/Unmute microphone")
            print("  volume <0-100>        - Set speaker volume")
            print("  volume up/down        - Increase/Decrease volume")
            print("  mic gain <-30-30>     - Set microphone gain")
            print("  mic enable/disable    - Enable/Disable microphone")
            
            print("\n🎛️ PROCESSING:")
            print("  noisegate on/off      - Enable/Disable noise gate")
            print("  noisegate <thresh> <hold> <range> - Set noise gate params")
            print("  suppress <off/low/medium/high> - Set noise suppression")
            
            print("\n🎯 BEAMFORMING:")
            print("  beam status           - Show beam position")
            
            print("\n📷 CAMERA CONTROLS:")
            print("  camera status         - Show all camera parameters")
            print("  camera brightness <-20-20> - Set brightness")
            print("  camera contrast <0-10> - Set contrast")
            print("  camera saturation <0-10> - Set saturation")
            print("  camera sharpness <0-4> - Set sharpness")
            print("  camera whitebalance auto - Auto white balance")
            print("  camera whitebalance <2000-10000> - Manual white balance (Kelvin)")
            print("  camera antiflicker auto - Auto anti-flicker")
            print("  camera antiflicker 50 - 50Hz anti-flicker")
            print("  camera antiflicker 60 - 60Hz anti-flicker")
            print("  camera backlight on/off - Backlight compensation")
            print("  camera lowlight on/off - Lowlight compensation")
            print("  camera speed zoom <Slow/Medium/Fast> - Zoom speed")
            print("  camera speed pantilt <Slow/Medium/Fast> - Pan/Tilt speed")
            print("  camera speed framing <Slow/Medium/Fast> - Auto framing speed")
            print("  camera pan <0-360>     - Set pan position")
            print("  camera tilt <-25-25>   - Set tilt position")
            print("  camera zoom <0-100>    - Set zoom position")
            print("  camera ai on/off       - Enable/Disable auto framing")
            print("  camera tiling on/off   - Enable/Disable person tiling")
            print("  camera ffov            - Reset to full field of view")
            print("  camera preset store    - Store current camera preset")
            print("  camera preset load     - Load camera preset")
            print("  camera move <up/down/left/right> <steps> - Move camera")
            print("  camera zoom in/out     - Zoom camera")
            print("  hdmi status            - Show HDMI output status")
            
            print("\n🎯 ZONE CONTROLS (Priority Zones):")
            print("  priority list         - List all priority zones")
            print("  priority get <id>     - Get priority zone")
            print("  priority on <id>      - Enable priority zone")
            print("  priority off <id>     - Disable priority zone")
            print("  priority gain <id> <gain> - Set gain (Off/Low/Medium/High)")
            print("  priority range <id> <left> <right> - Set range in degrees (0-180)")

            print("\n🚫 ZONE CONTROLS (Exclusion Zones):")
            print("  exclude list          - List all exclusion zones")
            print("  exclude get <id>      - Get exclusion zone")
            print("  exclude on <id>       - Enable exclusion zone")
            print("  exclude off <id>      - Disable exclusion zone")
            print("  exclude range <id> <left> <right> - Set range in degrees (0-180)")
            
            print("\n💡 LED CONTROLS:")
            print("  led bright <0-5>      - Set LED brightness")
            print("  led status            - Show LED settings")
            
            print("\n🌐 NETWORK:")
            print("  network status        - Show network interfaces")
            print("  dante status          - Show Dante status")
            print("  bluetooth on/off      - Enable/Disable Bluetooth")
            print("  wifi status           - Show WiFi status")
            
            print("\n🔧 DEVICE:")
            print("  site name <name>      - Set device name")
            print("  site location <loc>   - Set location")
            print("  sound prompts on/off  - Enable/Disable sound prompts")
            print("  identify on/off       - Identify device (blink LEDs)")
            print("  restart               - Restart device")
            print("  check profile         - Check current device profile")
            print("  profile <custom/teams> - Set device profile")
            
            print("\n📊 MONITORING:")
            print("  status                - Show detailed status")
            print("  firmware              - Show firmware status")
            print("  monitor               - Start real-time monitoring")
            print("  stop                  - Stop monitoring")
            print("  info                  - Complete device info")
            print("  exit                  - Exit")
            print("=" * 70)
            
            cmd = input("\n👉 Enter command: ").strip().lower()
            
            try:
                if cmd == "exit":
                    if self.monitoring_active:
                        self.device.stop_monitoring()
                    print("👋 Goodbye!")
                    break
                
                # ========== Profile Commands ==========
                elif cmd == "check profile":
                    try:
                        profile = self.device.get_device_profile()
                        print(f"📱 Current Device Profile: {profile.get('configuration', 'Unknown')}")
                        if profile.get('configuration') == 'MicrosoftTeams':
                            print("   ⚠️ WARNING: Microsoft Teams profile active!")
                            print("   Try: profile custom")
                        else:
                            print("   ✅ Custom profile active - Full control available")
                    except Exception as e:
                        print(f"❌ Error: {e}")
                
                elif cmd.startswith("profile"):
                    parts = cmd.split()
                    if len(parts) == 2:
                        profile = parts[1].capitalize()
                        if profile in ["Custom", "MicrosoftTeams"]:
                            self.device.set_device_profile(profile)
                            print(f"✅ Device profile set to {profile}")
                        else:
                            print("❌ Profile must be 'custom' or 'teams'")
                    else:
                        print("❌ Usage: profile <custom/teams>")
                
                # ========== Audio Commands ==========
                elif cmd == "mute on":
                    self.device.mute()
                    print("✅ Microphone MUTED")
                
                elif cmd == "mute off":
                    self.device.unmute()
                    print("✅ Microphone UNMUTED")
                
                elif cmd.startswith("volume "):
                    parts = cmd.split()
                    if len(parts) == 2:
                        try:
                            volume = int(parts[1])
                            self.device.set_volume(volume)
                            print(f"✅ Volume set to {volume}%")
                        except ValueError:
                            print("❌ Invalid volume value")
                    else:
                        print("❌ Usage: volume <0-100>")
                
                elif cmd == "volume up":
                    self.device.volume_up()
                    print("✅ Volume increased")
                
                elif cmd == "volume down":
                    self.device.volume_down()
                    print("✅ Volume decreased")
                
                elif cmd.startswith("mic gain"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            gain = int(parts[2])
                            self.device.set_internal_mic(gain=gain)
                            print(f"✅ Mic gain set to {gain} dB")
                        except ValueError:
                            print("❌ Invalid gain value")
                    else:
                        print("❌ Usage: mic gain <-30 to 30>")
                
                elif cmd == "mic enable":
                    self.device.set_internal_mic(enabled=True)
                    print("✅ Microphone ENABLED")
                
                elif cmd == "mic disable":
                    self.device.set_internal_mic(enabled=False)
                    print("✅ Microphone DISABLED")
                
                # ========== Processing Commands ==========
                elif cmd == "noisegate on":
                    self.device.set_noise_gate(enabled=True)
                    print("✅ Noise gate ENABLED")
                
                elif cmd == "noisegate off":
                    self.device.set_noise_gate(enabled=False)
                    print("✅ Noise gate DISABLED")
                
                elif cmd.startswith("noisegate "):
                    parts = cmd.split()
                    if len(parts) == 4:
                        try:
                            threshold = int(parts[1])
                            hold = int(parts[2])
                            range_val = int(parts[3])
                            self.device.set_noise_gate(enabled=True, threshold=threshold, 
                                                        hold_time=hold, range_val=range_val)
                            print(f"✅ Noise gate set: threshold={threshold}dB, hold={hold}ms, range={range_val}dB")
                        except ValueError:
                            print("❌ Invalid values")
                    else:
                        print("❌ Usage: noisegate <threshold -80 to -20> <hold 100-2000> <range -80 to 0>")
                
                elif cmd.startswith("suppress"):
                    parts = cmd.split()
                    if len(parts) == 2:
                        weighting = parts[1].capitalize()
                        self.device.set_noise_suppression(weighting)
                        print(f"✅ Noise suppression set to {weighting}")
                    else:
                        print("❌ Usage: suppress <off/low/medium/high>")
                
                # ========== Beam Commands ==========
                elif cmd == "beam status":
                    beam = self.device.get_beam_position()
                    print(f"🎯 Beam Position: {beam.get('position', 0)}°")
                
                # ========== Camera Status Command ==========
                elif cmd == "camera status":
                    try:
                        ai = self.device.get_camera_ai_access()
                        video = self.device.get_camera_video_parameters()
                        movement = self.device.get_camera_movement()
                        status = self.device.get_camera_status()
                        
                        print("\n📷 CAMERA STATUS:")
                        print("-" * 50)
                        print("🤖 AI FEATURES:")
                        print(f"   Auto Framing: {'✅ ENABLED' if ai.get('autoFramingEnabled') else '❌ DISABLED'}")
                        print(f"   Person Tiling: {'✅ ENABLED' if ai.get('personTilingEnabled') else '❌ DISABLED'}")
                        
                        print("\n🎨 VIDEO PARAMETERS:")
                        print(f"   Brightness: {video.get('brightness', 0)}")
                        print(f"   Contrast: {video.get('contrast', 5)}")
                        print(f"   Saturation: {video.get('saturation', 5)}")
                        print(f"   Sharpness: {video.get('sharpness', 2)}")
                        wb_mode = "Auto" if video.get('autoWhitebalanceEnabled') else "Manual"
                        print(f"   White Balance: {wb_mode}")
                        if not video.get('autoWhitebalanceEnabled'):
                            print(f"   White Balance Value: {video.get('whitebalance', 4600)}K")
                        print(f"   Anti-flicker: {video.get('antiFlickerFrequency', 'Auto')}")
                        print(f"   Backlight Compensation: {'✅' if video.get('backlightCompensationEnabled') else '❌'}")
                        print(f"   Lowlight Compensation: {'✅' if video.get('lowlightCompensationEnabled') else '❌'}")
                        
                        print("\n🎥 MOVEMENT:")
                        print(f"   Pan: {movement.get('panPosition', 0)}°")
                        print(f"   Tilt: {movement.get('tiltPosition', 0)}°")
                        print(f"   Zoom: {movement.get('zoomPosition', 100)}%")
                        print(f"   Zoom Speed: {movement.get('zoomSpeed', 'Medium')}")
                        print(f"   Pan/Tilt Speed: {movement.get('panTiltSpeed', 'Medium')}")
                        print(f"   Auto Framing Speed: {movement.get('autoFramingSpeed', 'Medium')}")
                        
                        print(f"\n📹 Camera Active: {'✅ YES' if status.get('active') else '❌ NO'}")
                        
                    except Exception as e:
                        print(f"❌ Error: {e}")
                
                # ========== Camera Video Parameter Commands ==========
                elif cmd.startswith("camera brightness"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            val = int(parts[2])
                            if -20 <= val <= 20:
                                self.device.set_camera_video_parameters(brightness=val)
                                print(f"✅ Camera brightness set to {val}")
                            else:
                                print("❌ Brightness must be between -20 and 20")
                        except ValueError:
                            print("❌ Invalid value")
                    else:
                        print("❌ Usage: camera brightness <-20 to 20>")
                
                elif cmd.startswith("camera contrast"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            val = int(parts[2])
                            if 0 <= val <= 10:
                                self.device.set_camera_video_parameters(contrast=val)
                                print(f"✅ Camera contrast set to {val}")
                            else:
                                print("❌ Contrast must be between 0 and 10")
                        except ValueError:
                            print("❌ Invalid value")
                    else:
                        print("❌ Usage: camera contrast <0-10>")
                
                elif cmd.startswith("camera saturation"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            val = int(parts[2])
                            if 0 <= val <= 10:
                                self.device.set_camera_video_parameters(saturation=val)
                                print(f"✅ Camera saturation set to {val}")
                            else:
                                print("❌ Saturation must be between 0 and 10")
                        except ValueError:
                            print("❌ Invalid value")
                    else:
                        print("❌ Usage: camera saturation <0-10>")
                
                elif cmd.startswith("camera sharpness"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            val = int(parts[2])
                            if 0 <= val <= 4:
                                self.device.set_camera_video_parameters(sharpness=val)
                                print(f"✅ Camera sharpness set to {val}")
                            else:
                                print("❌ Sharpness must be between 0 and 4")
                        except ValueError:
                            print("❌ Invalid value")
                    else:
                        print("❌ Usage: camera sharpness <0-4>")
                
                elif cmd == "camera whitebalance auto":
                    self.device.set_camera_video_parameters(auto_whitebalance=True)
                    print("✅ White balance set to AUTO")
                
                elif cmd.startswith("camera whitebalance"):
                    parts = cmd.split()
                    if len(parts) == 3 and parts[2] != "auto":
                        try:
                            val = int(parts[2])
                            if 2000 <= val <= 10000:
                                self.device.set_camera_video_parameters(auto_whitebalance=False, whitebalance=val)
                                print(f"✅ White balance set to {val}K (Manual)")
                            else:
                                print("❌ White balance must be between 2000 and 10000 Kelvin")
                        except ValueError:
                            print("❌ Invalid value")
                    elif len(parts) == 3 and parts[2] == "auto":
                        pass
                    else:
                        print("❌ Usage: camera whitebalance <2000-10000> or 'auto'")
                
                elif cmd == "camera antiflicker auto":
                    self.device.set_camera_video_parameters(anti_flicker="Auto")
                    print("✅ Anti-flicker set to AUTO")
                
                elif cmd == "camera antiflicker 50":
                    self.device.set_camera_video_parameters(anti_flicker="50Hz")
                    print("✅ Anti-flicker set to 50Hz")
                
                elif cmd == "camera antiflicker 60":
                    self.device.set_camera_video_parameters(anti_flicker="60Hz")
                    print("✅ Anti-flicker set to 60Hz")
                
                elif cmd == "camera backlight on":
                    self.device.set_camera_video_parameters(backlight_compensation=True)
                    print("✅ Backlight compensation ENABLED")
                
                elif cmd == "camera backlight off":
                    self.device.set_camera_video_parameters(backlight_compensation=False)
                    print("✅ Backlight compensation DISABLED")
                
                elif cmd == "camera lowlight on":
                    self.device.set_camera_video_parameters(lowlight_compensation=True)
                    print("✅ Lowlight compensation ENABLED")
                
                elif cmd == "camera lowlight off":
                    self.device.set_camera_video_parameters(lowlight_compensation=False)
                    print("✅ Lowlight compensation DISABLED")
                
                # ========== Camera Movement Commands ==========
                elif cmd.startswith("camera speed zoom"):
                    parts = cmd.split()
                    if len(parts) == 4:
                        speed = parts[3].capitalize()
                        if speed in ["Slow", "Medium", "Fast"]:
                            self.device.set_camera_movement(zoom_speed=speed)
                            print(f"✅ Zoom speed set to {speed}")
                        else:
                            print("❌ Speed must be Slow, Medium, or Fast")
                    else:
                        print("❌ Usage: camera speed zoom <Slow/Medium/Fast>")
                
                elif cmd.startswith("camera speed pantilt"):
                    parts = cmd.split()
                    if len(parts) == 4:
                        speed = parts[3].capitalize()
                        if speed in ["Slow", "Medium", "Fast"]:
                            self.device.set_camera_movement(pan_tilt_speed=speed)
                            print(f"✅ Pan/Tilt speed set to {speed}")
                        else:
                            print("❌ Speed must be Slow, Medium, or Fast")
                    else:
                        print("❌ Usage: camera speed pantilt <Slow/Medium/Fast>")
                
                elif cmd.startswith("camera speed framing"):
                    parts = cmd.split()
                    if len(parts) == 4:
                        speed = parts[3].capitalize()
                        if speed in ["Slow", "Medium", "Fast"]:
                            self.device.set_camera_movement(auto_framing_speed=speed)
                            print(f"✅ Auto framing speed set to {speed}")
                        else:
                            print("❌ Speed must be Slow, Medium, or Fast")
                    else:
                        print("❌ Usage: camera speed framing <Slow/Medium/Fast>")
                
                elif cmd.startswith("camera pan"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            val = int(parts[2])
                            if 0 <= val <= 360:
                                self.device.set_camera_movement(pan=val)
                                print(f"✅ Camera pan set to {val}°")
                            else:
                                print("❌ Pan must be between 0 and 360 degrees")
                        except ValueError:
                            print("❌ Invalid value")
                    else:
                        print("❌ Usage: camera pan <0-360>")
                
                elif cmd.startswith("camera tilt"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            val = int(parts[2])
                            if -25 <= val <= 25:
                                self.device.set_camera_movement(tilt=val)
                                print(f"✅ Camera tilt set to {val}°")
                            else:
                                print("❌ Tilt must be between -25 and 25 degrees")
                        except ValueError:
                            print("❌ Invalid value")
                    else:
                        print("❌ Usage: camera tilt <-25 to 25>")
                
                elif cmd.startswith("camera zoom"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            val = int(parts[2])
                            if 0 <= val <= 100:
                                self.device.set_camera_movement(zoom=val)
                                print(f"✅ Camera zoom set to {val}%")
                            else:
                                print("❌ Zoom must be between 0 and 100%")
                        except ValueError:
                            print("❌ Invalid value")
                    else:
                        print("❌ Usage: camera zoom <0-100>")
                
                # ========== Camera AI Commands ==========
                elif cmd == "camera ai on":
                    self.device.set_camera_ai_access(auto_framing=True)
                    print("✅ Auto framing ENABLED")
                
                elif cmd == "camera ai off":
                    self.device.set_camera_ai_access(auto_framing=False)
                    print("✅ Auto framing DISABLED")
                
                elif cmd == "camera tiling on":
                    self.device.set_camera_ai_access(person_tiling=True)
                    print("✅ Person tiling ENABLED")
                
                elif cmd == "camera tiling off":
                    self.device.set_camera_ai_access(person_tiling=False)
                    print("✅ Person tiling DISABLED")
                
                elif cmd == "camera ffov":
                    self.device.reset_camera_to_ffov()
                    print("✅ Camera reset to full field of view")
                
                elif cmd == "camera preset store":
                    self.device.store_camera_preset()
                    print("✅ Camera preset STORED")
                
                elif cmd == "camera preset load":
                    self.device.load_camera_preset()
                    print("✅ Camera preset LOADED")
                
                elif cmd == "camera zoom in":
                    self.device.move_camera_relative(zoom_in=1)
                    print("✅ Zoom IN")
                
                elif cmd == "camera zoom out":
                    self.device.move_camera_relative(zoom_out=1)
                    print("✅ Zoom OUT")
                
                elif cmd.startswith("camera move"):
                    parts = cmd.split()
                    if len(parts) >= 3:
                        direction = parts[2]
                        steps = 1
                        if len(parts) > 3:
                            try:
                                steps = int(parts[3])
                            except ValueError:
                                steps = 1
                        if direction == "up":
                            self.device.move_camera_relative(up=steps)
                            print(f"✅ Camera moved UP by {steps}")
                        elif direction == "down":
                            self.device.move_camera_relative(down=steps)
                            print(f"✅ Camera moved DOWN by {steps}")
                        elif direction == "left":
                            self.device.move_camera_relative(left=steps)
                            print(f"✅ Camera moved LEFT by {steps}")
                        elif direction == "right":
                            self.device.move_camera_relative(right=steps)
                            print(f"✅ Camera moved RIGHT by {steps}")
                        else:
                            print("❌ Direction must be: up, down, left, right")
                    else:
                        print("❌ Usage: camera move <up/down/left/right> [steps]")
                
                elif cmd == "hdmi status":
                    try:
                        hdmi = self.device.get_hdmi_enabled()
                        status = "✅ ENABLED" if hdmi.get('enabled') else "❌ DISABLED"
                        print(f"📺 HDMI Output: {status}")
                    except Exception as e:
                        print(f"❌ Error: {e}")
                
                # ========== Priority Zone Commands ==========
                elif cmd == "priority list":
                    try:
                        zones = self.device.get_priority_zones()
                        print("\n🎯 PRIORITY ZONES:")
                        print("-" * 60)
                        if not zones:
                            print("   No priority zones configured")
                        else:
                            for zone in zones:
                                left_deg = self.device._scale_to_deg(zone.get('left', 0))
                                right_deg = self.device._scale_to_deg(zone.get('right', 100))
                                status = "✅ ACTIVE" if zone.get('active') else "⭕ INACTIVE"
                                enabled = "🔵 ENABLED" if zone.get('enabled') else "⚪ DISABLED"
                                print(f"Zone {zone.get('id')}: {status} | {enabled}")
                                print(f"   Gain: {zone.get('gain', 'Medium')}")
                                print(f"   Range: {left_deg}° - {right_deg}°")
                                print("-" * 40)
                    except Exception as e:
                        print(f"❌ Error: {e}")
                
                elif cmd.startswith("priority get"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            zone_id = int(parts[2])
                            zone = self.device.get_priority_zone(zone_id)
                            left_deg = self.device._scale_to_deg(zone.get('left', 0))
                            right_deg = self.device._scale_to_deg(zone.get('right', 100))
                            print(f"\n🎯 PRIORITY ZONE {zone_id}:")
                            print(f"   Active: {zone.get('active', False)}")
                            print(f"   Enabled: {zone.get('enabled', False)}")
                            print(f"   Gain: {zone.get('gain', 'Medium')}")
                            print(f"   Range: {left_deg}° - {right_deg}°")
                        except ValueError:
                            print("❌ Invalid zone ID")
                    else:
                        print("❌ Usage: priority get <zone_id>")
                
                elif cmd.startswith("priority on"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            zone_id = int(parts[2])
                            self.device.enable_priority_zone(zone_id)
                            print(f"✅ Priority zone {zone_id} ENABLED")
                        except ValueError:
                            print("❌ Invalid zone ID")
                    else:
                        print("❌ Usage: priority on <zone_id>")
                
                elif cmd.startswith("priority off"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            zone_id = int(parts[2])
                            self.device.disable_priority_zone(zone_id)
                            print(f"✅ Priority zone {zone_id} DISABLED")
                        except ValueError:
                            print("❌ Invalid zone ID")
                    else:
                        print("❌ Usage: priority off <zone_id>")
                
                elif cmd.startswith("priority gain"):
                    parts = cmd.split()
                    if len(parts) == 4:
                        try:
                            zone_id = int(parts[2])
                            gain = parts[3].capitalize()
                            self.device.set_priority_zone_gain(zone_id, gain)
                            print(f"✅ Priority zone {zone_id} gain set to {gain}")
                        except ValueError:
                            print("❌ Invalid zone ID")
                    else:
                        print("❌ Usage: priority gain <zone_id> <Off/Low/Medium/High>")
                
                elif cmd.startswith("priority range"):
                    parts = cmd.split()
                    if len(parts) == 5:
                        try:
                            zone_id = int(parts[2])
                            left_deg = int(parts[3])
                            right_deg = int(parts[4])
                            self.device.set_priority_zone_range(zone_id, left_deg, right_deg)
                            print(f"✅ Priority zone {zone_id} range set to {left_deg}° - {right_deg}°")
                            time.sleep(0.5)
                            zone = self.device.get_priority_zone(zone_id)
                            left_deg = self.device._scale_to_deg(zone.get('left', 0))
                            right_deg = self.device._scale_to_deg(zone.get('right', 100))
                            print(f"   Verified: Range is now {left_deg}° - {right_deg}°")
                        except ValueError:
                            print("❌ Invalid numbers. Usage: priority range <zone_id> <left_deg 0-180> <right_deg 0-180>")
                    else:
                        print("❌ Usage: priority range <zone_id> <left_deg 0-180> <right_deg 0-180>")
                
                # ========== Exclusion Zone Commands ==========
                elif cmd == "exclude list":
                    try:
                        zones = self.device.get_exclusion_zones()
                        print("\n🚫 EXCLUSION ZONES:")
                        print("-" * 60)
                        if not zones:
                            print("   No exclusion zones configured")
                        else:
                            for zone in zones:
                                left_deg = self.device._scale_to_deg(zone.get('left', 0))
                                right_deg = self.device._scale_to_deg(zone.get('right', 100))
                                status = "✅ ACTIVE" if zone.get('active') else "⭕ INACTIVE"
                                enabled = "🔵 ENABLED" if zone.get('enabled') else "⚪ DISABLED"
                                print(f"Zone {zone.get('id')}: {status} | {enabled}")
                                print(f"   Range: {left_deg}° - {right_deg}°")
                                print("-" * 40)
                    except Exception as e:
                        print(f"❌ Error: {e}")
                
                elif cmd.startswith("exclude get"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            zone_id = int(parts[2])
                            zone = self.device.get_exclusion_zone(zone_id)
                            left_deg = self.device._scale_to_deg(zone.get('left', 0))
                            right_deg = self.device._scale_to_deg(zone.get('right', 100))
                            print(f"\n🚫 EXCLUSION ZONE {zone_id}:")
                            print(f"   Active: {zone.get('active', False)}")
                            print(f"   Enabled: {zone.get('enabled', False)}")
                            print(f"   Range: {left_deg}° - {right_deg}°")
                        except ValueError:
                            print("❌ Invalid zone ID")
                    else:
                        print("❌ Usage: exclude get <zone_id>")
                
                elif cmd.startswith("exclude on"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            zone_id = int(parts[2])
                            self.device.enable_exclusion_zone(zone_id)
                            print(f"✅ Exclusion zone {zone_id} ENABLED")
                        except ValueError:
                            print("❌ Invalid zone ID")
                    else:
                        print("❌ Usage: exclude on <zone_id>")
                
                elif cmd.startswith("exclude off"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            zone_id = int(parts[2])
                            self.device.disable_exclusion_zone(zone_id)
                            print(f"✅ Exclusion zone {zone_id} DISABLED")
                        except ValueError:
                            print("❌ Invalid zone ID")
                    else:
                        print("❌ Usage: exclude off <zone_id>")
                
                elif cmd.startswith("exclude range"):
                    parts = cmd.split()
                    if len(parts) == 5:
                        try:
                            zone_id = int(parts[2])
                            left_deg = int(parts[3])
                            right_deg = int(parts[4])
                            self.device.set_exclusion_zone_range(zone_id, left_deg, right_deg)
                            print(f"✅ Exclusion zone {zone_id} range set to {left_deg}° - {right_deg}°")
                            time.sleep(0.5)
                            zone = self.device.get_exclusion_zone(zone_id)
                            left_deg = self.device._scale_to_deg(zone.get('left', 0))
                            right_deg = self.device._scale_to_deg(zone.get('right', 100))
                            print(f"   Verified: Range is now {left_deg}° - {right_deg}°")
                        except ValueError:
                            print("❌ Invalid numbers. Usage: exclude range <zone_id> <left_deg 0-180> <right_deg 0-180>")
                    else:
                        print("❌ Usage: exclude range <zone_id> <left_deg 0-180> <right_deg 0-180>")
                
                # ========== LED Commands ==========
                elif cmd.startswith("led bright"):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            brightness = int(parts[2])
                            self.device.set_led_brightness(brightness)
                            print(f"✅ LED brightness set to {brightness}")
                        except ValueError:
                            print("❌ Invalid brightness value")
                    else:
                        print("❌ Usage: led bright <0-5>")
                
                elif cmd == "led status":
                    led = self.device.get_led_ring()
                    print(f"💡 LED Brightness: {led.get('brightness', 3)}")
                
                # ========== Network Commands ==========
                elif cmd == "network status":
                    network = self.device.get_network_interfaces()
                    print("\n🌐 NETWORK INTERFACES:")
                    print(json.dumps(network, indent=2))
                
                elif cmd == "dante status":
                    dante = self.device.get_dante_status()
                    print(f"🎵 Dante Enabled: {dante.get('enabled', False)}")
                
                elif cmd == "bluetooth on":
                    self.device.set_bluetooth_settings(enabled=True)
                    print("✅ Bluetooth ENABLED")
                
                elif cmd == "bluetooth off":
                    self.device.set_bluetooth_settings(enabled=False)
                    print("✅ Bluetooth DISABLED")
                
                elif cmd == "wifi status":
                    wifi = self.device.get_wifi_status()
                    print(f"📡 WiFi Enabled: {wifi.get('enabled', False)}")
                    print(f"   State: {wifi.get('state', 'Unknown')}")
                
                # ========== Device Commands ==========
                elif cmd.startswith("site name"):
                    parts = cmd.split(maxsplit=2)
                    if len(parts) >= 3:
                        name = parts[2]
                        self.device.set_device_site(device_name=name)
                        print(f"✅ Device name set to {name}")
                    else:
                        print("❌ Usage: site name <name>")
                
                elif cmd.startswith("site location"):
                    parts = cmd.split(maxsplit=2)
                    if len(parts) >= 3:
                        location = parts[2]
                        self.device.set_device_site(location=location)
                        print(f"✅ Location set to {location}")
                    else:
                        print("❌ Usage: site location <location>")
                
                elif cmd == "sound prompts on":
                    self.device.set_sound_prompts(True)
                    print("✅ Sound prompts ENABLED")
                
                elif cmd == "sound prompts off":
                    self.device.set_sound_prompts(False)
                    print("✅ Sound prompts DISABLED")
                
                elif cmd == "identify on":
                    self.device.identify_device(True)
                    print("✅ Device identification started - LEDs will blink for 5 seconds")
                    threading.Timer(5.0, lambda: self.device.identify_device(False)).start()
                
                elif cmd == "identify off":
                    self.device.identify_device(False)
                    print("✅ Device identification stopped")
                
                elif cmd == "restart":
                    confirm = input("⚠️ Are you sure you want to restart the device? (yes/no): ")
                    if confirm.lower() == "yes":
                        self.device.restart_device()
                        print("🔄 Device restarting...")
                    else:
                        print("Restart cancelled")
                
                # ========== Monitoring Commands ==========
                elif cmd == "status":
                    info = self.device.get_complete_device_info()
                    print("\n📱 DETAILED DEVICE STATUS:")
                    print(json.dumps(info, indent=2, default=str))
                
                elif cmd == "firmware":
                    fw = self.device.get_firmware_update_state()
                    print(f"\n📦 FIRMWARE:")
                    print(f"   Device Version: {fw.get('deviceVersion', 'Unknown')}")
                    print(f"   State: {fw.get('state', 'Idle')}")
                    if fw.get('state') != 'Idle':
                        print(f"   Progress: {fw.get('progress', 0)}%")
                
                elif cmd == "monitor":
                    if not self.monitoring_active:
                        self.monitoring_active = True
                        self.device.start_monitoring(1.0, self.display_metrics)
                        print("\n✅ Real-time monitoring started")
                    else:
                        print("⚠️ Monitoring already active")
                
                elif cmd == "stop":
                    if self.monitoring_active:
                        self.device.stop_monitoring()
                        self.monitoring_active = False
                        print("✅ Monitoring stopped")
                
                elif cmd == "info":
                    info = self.device.get_complete_device_info()
                    print("\n📱 COMPLETE DEVICE INFO:")
                    print(json.dumps(info, indent=2, default=str))
                
                else:
                    print("❌ Unknown command")
                    
            except Exception as e:
                print(f"❌ Error: {e}")


# ========== Main Entry Point ==========

def get_user_credentials():
    print("\n" + "=" * 60)
    print(" SENNHEISER TEAMCONNECT BAR M DEVICE CONNECTION SETUP")
    print("=" * 60)
    
    device_ip = input("\n🔌 Enter Device IP Address: ").strip()
    username = input("👤 Enter Username (default: api): ").strip() or "api"
    password = getpass.getpass("🔑 Enter Password: ").strip()
    
    return device_ip, username, password


def validate_connection(device_ip, username, password):
    print("\n🔍 Validating connection...")
    
    test_device = SennheiserTCBarMPlugin(device_ip, username, password)
    
    try:
        identity = test_device.get_device_identity()
        if identity and 'product' in identity:
            print(f"   ✅ Connection successful!")
            print(f"   📱 Device: {identity.get('product')}")
            print(f"   🔢 Serial: {identity.get('serial')}")
            return True, test_device
        return False, None
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False, None


def main():
    print("\n" + "=" * 60)
    print(" SENNHEISER TEAMCONNECT BAR M DEVICE CONTROL PLUGIN")
    print("=" * 60)
    
    device_ip, username, password = get_user_credentials()
    success, device = validate_connection(device_ip, username, password)
    
    if not success:
        print("\n❌ Failed to connect. Please check:")
        print("   1. Device IP address is correct")
        print("   2. 3rd Party Access is enabled in device settings")
        print("   3. Username and password are correct")
        return
    
    print("\n✅ CONNECTION ESTABLISHED - LAUNCHING CONTROL INTERFACE")
    controller = SennheiserTCBarMController(device_ip, username, password)
    
    try:
        controller.run_interactive_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()