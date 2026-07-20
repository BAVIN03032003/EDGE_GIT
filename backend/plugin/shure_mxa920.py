# """
# Manual Platform Plugin: ShureMXA920Plugin
# """

# import json
# import socket
# import time

# from .base import ManualPlatformPlugin


# class ShureMXA920Plugin(ManualPlatformPlugin):
#     """Shure MXA920 TCP control plugin based on Shure command strings."""

#     name = "shure_mxa920"
#     display_name = "Shure MXA920"
#     description = "Shure MXA920 microphone array via TCP control port"
#     supports_display_id = False
#     supports_port = False
#     default_port = 2202
#     SUPPORTED_MODELS = ["MXA920", "MXA910", "MXA902", "MXA710"]

#     COMMANDS = {
#         "device_mute": {"description": "Set device mute state", "params": [{"name": "state", "type": "str"}]},
#         "identify": {"description": "Set identify flash", "params": [{"name": "state", "type": "str"}]},
#         "auto_coverage": {"description": "Set auto coverage", "params": [{"name": "state", "type": "str"}]},
#         "reboot": {"description": "Reboot the device", "params": []},
#         "factory_reset": {"description": "Restore factory defaults", "params": []},
#         "set_led_brightness": {"description": "Set LED brightness 0-5", "params": [{"name": "level", "type": "int"}]},
#         "set_led_color_unmuted": {"description": "Set unmuted LED color", "params": [{"name": "color", "type": "str"}]},
#         "set_led_color_muted": {"description": "Set muted LED color", "params": [{"name": "color", "type": "str"}]},
#         "set_led_state_unmuted": {"description": "Set unmuted LED state", "params": [{"name": "state", "type": "str"}]},
#         "set_led_state_muted": {"description": "Set muted LED state", "params": [{"name": "state", "type": "str"}]},
#         "set_led_in_state": {"description": "Set LED-in state", "params": [{"name": "state", "type": "str"}]},
#         "recall_preset": {"description": "Recall preset 1-10", "params": [{"name": "preset", "type": "int"}]},
#         "set_channel_mute": {"description": "Set channel mute", "params": [{"name": "channel", "type": "int"}, {"name": "state", "type": "str"}]},
#         "set_channel_gain_db": {"description": "Set channel gain in dB", "params": [{"name": "channel", "type": "int"}, {"name": "db", "type": "float"}]},
#         "adjust_channel_gain_db": {"description": "Adjust channel gain by dB", "params": [{"name": "channel", "type": "int"}, {"name": "delta_db", "type": "float"}]},
#         "reset_channel_gain": {"description": "Reset channel gain to 0 dB", "params": [{"name": "channel", "type": "int"}]},
#         "set_postgate_mute": {"description": "Set postgate mute", "params": [{"name": "channel", "type": "int"}, {"name": "state", "type": "str"}]},
#         "set_postgate_gain_db": {"description": "Set postgate gain in dB", "params": [{"name": "channel", "type": "int"}, {"name": "db", "type": "float"}]},
#         "set_intellimix_bypass": {"description": "Set IntelliMix bypass", "params": [{"name": "state", "type": "str"}]},
#         "set_eq_bypass": {"description": "Set EQ bypass", "params": [{"name": "state", "type": "str"}]},
#         "set_eq_contour": {"description": "Set EQ contour", "params": [{"name": "state", "type": "str"}]},
#         "set_channel_solo": {"description": "Set channel solo enable/disable", "params": [{"name": "channel", "type": "int"}, {"name": "state", "type": "str"}]},
#         "set_channel_peq": {"description": "Set channel PEQ 0", "params": [{"name": "channel", "type": "int"}, {"name": "state", "type": "str"}]},
#         "set_coverage_mute": {"description": "Set coverage area mute", "params": [{"name": "area", "type": "int"}, {"name": "state", "type": "str"}]},
#         "set_coverage_gain_db": {"description": "Set coverage area gain in dB", "params": [{"name": "area", "type": "int"}, {"name": "db", "type": "float"}]},
#         "adjust_coverage_gain_db": {"description": "Adjust coverage area gain by dB", "params": [{"name": "area", "type": "int"}, {"name": "delta_db", "type": "float"}]},
#         "reset_coverage_gain": {"description": "Reset coverage area gain to 0 dB", "params": [{"name": "area", "type": "int"}]},
#         "set_array_height": {"description": "Set array height in cm", "params": [{"name": "height_cm", "type": "int"}]},
#         "set_lobe_width": {"description": "Set lobe width", "params": [{"name": "lobe", "type": "int"}, {"name": "width", "type": "str"}]},
#         "set_lobe_x": {"description": "Set lobe X", "params": [{"name": "lobe", "type": "int"}, {"name": "value", "type": "int"}]},
#         "set_lobe_y": {"description": "Set lobe Y", "params": [{"name": "lobe", "type": "int"}, {"name": "value", "type": "int"}]},
#         "set_lobe_z": {"description": "Set lobe Z", "params": [{"name": "lobe", "type": "int"}, {"name": "value", "type": "int"}]},
#         "raw_command": {"description": "Send raw TCP command", "params": [{"name": "command", "type": "str"}]},
#     }

#     QUERY_COMMANDS = {
#         "device_info": "retrieve_device_info",
#         "lights": "get_lights_status",
#         "presets": "get_presets_status",
#         "channels": "get_channels_status",
#         "intellimix": "get_intellimix_status",
#         "coverage": "get_coverage_status",
#         "lobes": "get_lobe_status",
#     }

#     ALL_COLORS = [
#         "RED", "ORANGE", "GOLD", "YELLOW", "YELLOWGREEN", "GREEN",
#         "TURQUOISE", "POWDERBLUE", "CYAN", "SKYBLUE", "BLUE",
#         "PURPLE", "LIGHTPURPLE", "VIOLET", "ORCHID", "PINK", "WHITE",
#     ]
#     LED_STATES = {"ON", "OFF", "FLASHING"}
#     TOGGLE_STATES = {"ON", "OFF", "TOGGLE"}
#     SOLO_STATES = {"ENABLE", "DISABLE"}
#     PEQ_STATES = {"ON", "OFF", "TOGGLE"}
#     LOBE_WIDTHS = {"NARROW", "MEDIUM", "WIDE"}

#     def _resolve_port(self, port=None):
#         # MXA920 TCP control is fixed on 2202. Ignore stale saved ports like 443.
#         return int(self.default_port)

#     def _send_tcp(self, ip, command, port=None, timeout=None):
#         target_port = self._resolve_port(port)
#         target_timeout = timeout or self.timeout or 3
#         try:
#             with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
#                 sock.settimeout(target_timeout)
#                 sock.connect((ip, target_port))
#                 sock.sendall(f"{command}\r\n".encode("ascii"))
#                 time.sleep(0.2)
#                 data = b""
#                 sock.settimeout(0.5)
#                 try:
#                     while True:
#                         chunk = sock.recv(4096)
#                         if not chunk:
#                             break
#                         data += chunk
#                 except socket.timeout:
#                     pass
#                 return data.decode("ascii", errors="ignore").strip()
#         except Exception:
#             return None

#     def _parse(self, response, keyword):
#         if not response or keyword not in response:
#             return None
#         tokens = response.split()
#         for idx, token in enumerate(tokens):
#             if keyword in token and idx + 1 < len(tokens):
#                 return self._clean(tokens[idx + 1])
#         return None

#     def _clean(self, value):
#         if value is None:
#             return None
#         return str(value).strip(">").strip("<").strip("{").strip("}").strip('"').strip("'").strip()

#     def _gain_to_db(self, raw):
#         try:
#             return round(int(raw) / 10.0 - 110.0, 1)
#         except Exception:
#             return None

#     def _db_to_gain(self, db):
#         return int((float(db) + 110.0) * 10)

#     def _channel_id(self, number):
#         return str(int(number)).zfill(2)

#     def _toggle_state(self, state, allow_toggle=True):
#         value = str(state or "").strip().upper()
#         allowed = self.TOGGLE_STATES if allow_toggle else {"ON", "OFF"}
#         if value not in allowed:
#             raise ValueError(f"Invalid state '{state}'. Expected one of {sorted(allowed)}")
#         return value

#     def _send_ok(self, ip, command, port=None):
#         response = self._send_tcp(ip, command, port=port)
#         if not response:
#             raise ValueError("No response from device.")
#         return response

#     def _current_channel_gain_db(self, ip, channel, port):
#         ch = self._channel_id(channel)
#         raw = self._query_value(ip, f"< GET {ch} AUDIO_GAIN_HI_RES >", "AUDIO_GAIN_HI_RES", port)
#         return self._gain_to_db(raw) or 0

#     def _current_coverage_gain_db(self, ip, area, port):
#         ca = self._channel_id(area)
#         raw = self._query_value(ip, f"< GET {ca} CA_GAIN >", "CA_GAIN", port)
#         return self._gain_to_db(raw) or 0

#     def _adjust_channel_gain(self, ip, channel, delta_db, port):
#         current = self._current_channel_gain_db(ip, channel, port)
#         ch = self._channel_id(channel)
#         return self._send_ok(ip, f"< SET {ch} AUDIO_GAIN_HI_RES {self._db_to_gain(current + float(delta_db))} >", port)

#     def _adjust_coverage_gain(self, ip, area, delta_db, port):
#         current = self._current_coverage_gain_db(ip, area, port)
#         ca = self._channel_id(area)
#         return self._send_ok(ip, f"< SET {ca} CA_GAIN {self._db_to_gain(current + float(delta_db))} >", port)

#     def _decode_command(self, command):
#         if isinstance(command, dict):
#             return command.get("action"), command.get("params") or {}
#         if isinstance(command, str):
#             stripped = command.strip()
#             if stripped.startswith("{") and stripped.endswith("}"):
#                 try:
#                     parsed = json.loads(stripped)
#                     if isinstance(parsed, dict):
#                         return parsed.get("action"), parsed.get("params") or {}
#                 except Exception:
#                     pass
#             return stripped, {}
#         return None, {}

#     def _query_value(self, ip, command, keyword, port=None):
#         return self._parse(self._send_tcp(ip, command, port=port), keyword)

#     def retrieve_device_info(self, ip, port=2202):
#         port = self._resolve_port(port)
#         info = {
#             "ip_address": ip,
#             "model": self._query_value(ip, "< GET MODEL >", "MODEL", port) or "N/A",
#             "serial_number": self._query_value(ip, "< GET SERIAL_NUM >", "SERIAL_NUM", port) or "N/A",
#             "firmware": self._query_value(ip, "< GET FW_VER >", "FW_VER", port) or "N/A",
#             "device_id": self._query_value(ip, "< GET DEVICE_ID >", "DEVICE_ID", port) or "N/A",
#             "dante_name": self._query_value(ip, "< GET NA_DEVICE_NAME >", "NA_DEVICE_NAME", port) or "N/A",
#             "mac_address": self._query_value(ip, "< GET CONTROL_MAC_ADDR >", "CONTROL_MAC_ADDR", port) or "N/A",
#             "ip_audio": self._query_value(ip, "< GET IP_ADDR_NET_AUDIO_PRIMARY >", "IP_ADDR_NET_AUDIO_PRIMARY", port) or "N/A",
#             "subnet_mask": self._query_value(ip, "< GET IP_SUBNET_NET_AUDIO_PRIMARY >", "IP_SUBNET_NET_AUDIO_PRIMARY", port) or "N/A",
#             "gateway": self._query_value(ip, "< GET IP_GATEWAY_NET_AUDIO_PRIMARY >", "IP_GATEWAY_NET_AUDIO_PRIMARY", port) or "N/A",
#             "encryption": self._query_value(ip, "< GET ENCRYPTION >", "ENCRYPTION", port) or "N/A",
#             "muted": self._query_value(ip, "< GET DEVICE_AUDIO_MUTE >", "DEVICE_AUDIO_MUTE", port) or "N/A",
#             "auto_coverage": self._query_value(ip, "< GET AUTO_COVERAGE >", "AUTO_COVERAGE", port) or "N/A",
#             "last_error": self._send_tcp(ip, "< GET LAST_ERROR_EVENT >", port=port) or "N/A",
#         }
#         return info

#     def get_lights_status(self, ip, port=2202):
#         port = self._resolve_port(port)
#         return {
#             "brightness": self._query_value(ip, "< GET LED_BRIGHTNESS >", "LED_BRIGHTNESS", port),
#             "color_unmuted": self._query_value(ip, "< GET LED_COLOR_UNMUTED >", "LED_COLOR_UNMUTED", port),
#             "state_unmuted": self._query_value(ip, "< GET LED_STATE_UNMUTED >", "LED_STATE_UNMUTED", port),
#             "color_muted": self._query_value(ip, "< GET LED_COLOR_MUTED >", "LED_COLOR_MUTED", port),
#             "state_muted": self._query_value(ip, "< GET LED_STATE_MUTED >", "LED_STATE_MUTED", port),
#             "led_in_state": self._query_value(ip, "< GET DEV_LED_IN_STATE >", "DEV_LED_IN_STATE", port),
#         }

#     def get_presets_status(self, ip, port=2202):
#         port = self._resolve_port(port)
#         active = self._query_value(ip, "< GET PRESET >", "PRESET", port)
#         presets = []
#         for preset in range(1, 11):
#             num = str(preset).zfill(2)
#             response = self._send_tcp(ip, f"< GET PRESET_NAME {num} >", port=port)
#             parts = response.split() if response else []
#             name = parts[4] if len(parts) >= 5 else None
#             if name in ("{empty}", ">", "<", None):
#                 name = None
#             presets.append({
#                 "preset": preset,
#                 "name": name,
#                 "active": str(active) == str(preset),
#             })
#         return {"active_preset": active, "presets": presets}

#     def get_channels_status(self, ip, port=2202):
#         port = self._resolve_port(port)
#         channels = []
#         for number in range(1, 10):
#             ch = self._channel_id(number)
#             label = "Automix" if number == 9 else f"Ch {number}"
#             gain_raw = self._query_value(ip, f"< GET {ch} AUDIO_GAIN_HI_RES >", "AUDIO_GAIN_HI_RES", port)
#             channels.append({
#                 "channel": number,
#                 "name": self._query_value(ip, f"< GET {ch} CHAN_NAME >", "CHAN_NAME", port) or label,
#                 "gain_raw": gain_raw,
#                 "gain_db": self._gain_to_db(gain_raw),
#                 "muted": self._query_value(ip, f"< GET {ch} AUDIO_MUTE >", "AUDIO_MUTE", port),
#                 "rms": self._query_value(ip, f"< GET {ch} AUDIO_IN_RMS_LVL >", "AUDIO_IN_RMS_LVL", port),
#                 "clip": self._query_value(ip, f"< GET {ch} AUDIO_OUT_CLIP_INDICATOR >", "AUDIO_OUT_CLIP_INDICATOR", port),
#             })
#         return {"auto_coverage": self._query_value(ip, "< GET AUTO_COVERAGE >", "AUTO_COVERAGE", port), "channels": channels}

#     def get_intellimix_status(self, ip, port=2202):
#         port = self._resolve_port(port)
#         channels = []
#         for number in range(1, 9):
#             ch = self._channel_id(number)
#             channels.append({
#                 "channel": number,
#                 "solo": self._query_value(ip, f"< GET {ch} CHAN_AUTOMIX_SOLO_EN >", "CHAN_AUTOMIX_SOLO_EN", port),
#                 "gate": self._query_value(ip, f"< GET {ch} AUTOMIX_GATE_OUT_EXT_SIG >", "AUTOMIX_GATE_OUT_EXT_SIG", port),
#                 "peq": self._query_value(ip, f"< GET {ch} PEQ 0 >", "PEQ", port),
#             })
#         return {
#             "bypass_imx": self._query_value(ip, "< GET BYPASS_IMX >", "BYPASS_IMX", port),
#             "bypass_all_eq": self._query_value(ip, "< GET BYPASS_ALL_EQ >", "BYPASS_ALL_EQ", port),
#             "eq_contour": self._query_value(ip, "< GET EQ_CONTOUR >", "EQ_CONTOUR", port),
#             "num_active_mics": self._query_value(ip, "< GET NUM_ACTIVE_MICS >", "NUM_ACTIVE_MICS", port),
#             "channels": channels,
#         }

#     def get_coverage_status(self, ip, port=2202):
#         port = self._resolve_port(port)
#         areas = []
#         for number in range(1, 9):
#             ca = self._channel_id(number)
#             gain_raw = self._query_value(ip, f"< GET {ca} CA_GAIN >", "CA_GAIN", port)
#             areas.append({
#                 "area": number,
#                 "mute": self._query_value(ip, f"< GET {ca} CA_MUTE >", "CA_MUTE", port),
#                 "gain_raw": gain_raw,
#                 "gain_db": self._gain_to_db(gain_raw),
#                 "gate": self._query_value(ip, f"< GET {ca} AUTOMIX_GATE_OUT_CA >", "AUTOMIX_GATE_OUT_CA", port),
#             })
#         return {"auto_coverage": self._query_value(ip, "< GET AUTO_COVERAGE >", "AUTO_COVERAGE", port), "areas": areas}

#     def get_lobe_status(self, ip, port=2202):
#         port = self._resolve_port(port)
#         lobes = []
#         for number in range(1, 9):
#             ch = self._channel_id(number)
#             lobes.append({
#                 "lobe": number,
#                 "width": self._query_value(ip, f"< GET {ch} BEAM_W >", "BEAM_W", port),
#                 "x": self._query_value(ip, f"< GET {ch} BEAM_X >", "BEAM_X", port),
#                 "y": self._query_value(ip, f"< GET {ch} BEAM_Y >", "BEAM_Y", port),
#                 "z": self._query_value(ip, f"< GET {ch} BEAM_Z >", "BEAM_Z", port),
#             })
#         return {"array_height": self._query_value(ip, "< GET ARRAY_HEIGHT >", "ARRAY_HEIGHT", port), "lobes": lobes}

#     def get_device_info(self, ip, port=2202, display_id=None):
#         try:
#             port = self._resolve_port(port)
#             model_probe = self._send_tcp(ip, "< GET MODEL >", port=port)
#             if not model_probe:
#                 return {
#                     "ip_address": ip,
#                     "port": port,
#                     "display_id": display_id,
#                     "make": "Shure",
#                     "device_type": "Shure MXA",
#                     "current_status": "Offline",
#                     "error": f"Cannot connect to {ip}:{port}",
#                 }

#             device = self.retrieve_device_info(ip, port=port)
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "Shure",
#                 "device_type": "Shure MXA",
#                 "device_name": device.get("dante_name") or device.get("model") or "Shure MXA Device",
#                 "model": device.get("model"),
#                 "serial_number": device.get("serial_number"),
#                 "firmware": device.get("firmware"),
#                 "mac_address": device.get("mac_address"),
#                 "device_id": device.get("device_id"),
#                 "dante_name": device.get("dante_name"),
#                 "subnet_mask": device.get("subnet_mask"),
#                 "gateway": device.get("gateway"),
#                 "encryption": device.get("encryption"),
#                 "muted": device.get("muted"),
#                 "auto_coverage": device.get("auto_coverage"),
#                 "last_error": device.get("last_error"),
#                 "current_status": "Online",
#                 "raw_device_info": device,
#                 "raw_queries": {
#                     "device_info": device,
#                     "lights": self.get_lights_status(ip, port=port),
#                     "presets": self.get_presets_status(ip, port=port),
#                     "channels": self.get_channels_status(ip, port=port),
#                     "intellimix": self.get_intellimix_status(ip, port=port),
#                     "coverage": self.get_coverage_status(ip, port=port),
#                     "lobes": self.get_lobe_status(ip, port=port),
#                 },
#             }
#         except Exception as e:
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "Shure",
#                 "device_type": "Shure MXA",
#                 "current_status": "Offline",
#                 "error": str(e),
#             }

#     def send_command(self, ip, port, display_id, command):
#         try:
#             action, params = self._decode_command(command)
#             params = params or {}
#             if not action:
#                 return False, "Missing command action."

#             target_port = self._resolve_port(port)

#             if action == "raw_command":
#                 tcp_command = params.get("command") or (command if isinstance(command, str) and command.strip().startswith("<") else None)
#                 if not tcp_command:
#                     return False, "raw_command requires params.command"
#                 return True, self._send_ok(ip, tcp_command, port=target_port)

#             actions = {
#                 "device_mute": lambda: self._send_ok(ip, f"< SET DEVICE_AUDIO_MUTE {self._toggle_state(params.get('state'))} >", target_port),
#                 "identify": lambda: self._send_ok(ip, f"< SET FLASH {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
#                 "auto_coverage": lambda: self._send_ok(ip, f"< SET AUTO_COVERAGE {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
#                 "reboot": lambda: self._send_ok(ip, "< SET REBOOT >", target_port),
#                 "factory_reset": lambda: self._send_ok(ip, "< SET DEFAULT_SETTINGS >", target_port),
#                 "set_led_brightness": lambda: self._send_ok(ip, f"< SET LED_BRIGHTNESS {int(params.get('level'))} >", target_port),
#                 "set_led_color_unmuted": lambda: self._send_ok(ip, f"< SET LED_COLOR_UNMUTED {str(params.get('color')).strip().upper()} >", target_port),
#                 "set_led_color_muted": lambda: self._send_ok(ip, f"< SET LED_COLOR_MUTED {str(params.get('color')).strip().upper()} >", target_port),
#                 "set_led_state_unmuted": lambda: self._send_ok(ip, f"< SET LED_STATE_UNMUTED {str(params.get('state')).strip().upper()} >", target_port),
#                 "set_led_state_muted": lambda: self._send_ok(ip, f"< SET LED_STATE_MUTED {str(params.get('state')).strip().upper()} >", target_port),
#                 "set_led_in_state": lambda: self._send_ok(ip, f"< SET DEV_LED_IN_STATE {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
#                 "recall_preset": lambda: self._send_ok(ip, f"< SET PRESET {self._channel_id(params.get('preset'))} >", target_port),
#                 "set_channel_mute": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_MUTE {self._toggle_state(params.get('state'))} >", target_port),
#                 "set_channel_gain_db": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_GAIN_HI_RES {self._db_to_gain(params.get('db'))} >", target_port),
#                 "adjust_channel_gain_db": lambda: self._adjust_channel_gain(ip, params.get("channel"), params.get("delta_db"), target_port),
#                 "reset_channel_gain": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_GAIN_HI_RES {self._db_to_gain(0)} >", target_port),
#                 "set_postgate_mute": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_MUTE_POSTGATE {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
#                 "set_postgate_gain_db": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_GAIN_POSTGATE {self._db_to_gain(params.get('db'))} >", target_port),
#                 "set_intellimix_bypass": lambda: self._send_ok(ip, f"< SET BYPASS_IMX {self._toggle_state(params.get('state'))} >", target_port),
#                 "set_eq_bypass": lambda: self._send_ok(ip, f"< SET BYPASS_ALL_EQ {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
#                 "set_eq_contour": lambda: self._send_ok(ip, f"< SET EQ_CONTOUR {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
#                 "set_channel_solo": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} CHAN_AUTOMIX_SOLO_EN {str(params.get('state')).strip().upper()} >", target_port),
#                 "set_channel_peq": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} PEQ 0 {str(params.get('state')).strip().upper()} >", target_port),
#                 "set_coverage_mute": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('area'))} CA_MUTE {self._toggle_state(params.get('state'))} >", target_port),
#                 "set_coverage_gain_db": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('area'))} CA_GAIN {self._db_to_gain(params.get('db'))} >", target_port),
#                 "adjust_coverage_gain_db": lambda: self._adjust_coverage_gain(ip, params.get("area"), params.get("delta_db"), target_port),
#                 "reset_coverage_gain": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('area'))} CA_GAIN {self._db_to_gain(0)} >", target_port),
#                 "set_array_height": lambda: self._send_ok(ip, f"< SET ARRAY_HEIGHT {int(params.get('height_cm'))} >", target_port),
#                 "set_lobe_width": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('lobe'))} BEAM_W {str(params.get('width')).strip().upper()} >", target_port),
#                 "set_lobe_x": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('lobe'))} BEAM_X {int(params.get('value'))} >", target_port),
#                 "set_lobe_y": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('lobe'))} BEAM_Y {int(params.get('value'))} >", target_port),
#                 "set_lobe_z": lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('lobe'))} BEAM_Z {int(params.get('value'))} >", target_port),
#             }

#             if action not in actions:
#                 return False, f"Unknown command: {action}"

#             if action in {"set_led_color_unmuted", "set_led_color_muted"}:
#                 color = str(params.get("color", "")).strip().upper()
#                 if color not in self.ALL_COLORS:
#                     return False, f"Invalid color '{color}'"
#             if action in {"set_led_state_unmuted", "set_led_state_muted"}:
#                 state = str(params.get("state", "")).strip().upper()
#                 if state not in self.LED_STATES:
#                     return False, f"Invalid LED state '{state}'"
#             if action == "set_channel_solo":
#                 state = str(params.get("state", "")).strip().upper()
#                 if state not in self.SOLO_STATES:
#                     return False, f"Invalid solo state '{state}'"
#             if action == "set_channel_peq":
#                 state = str(params.get("state", "")).strip().upper()
#                 if state not in self.PEQ_STATES:
#                     return False, f"Invalid PEQ state '{state}'"
#             if action == "set_lobe_width":
#                 width = str(params.get("width", "")).strip().upper()
#                 if width not in self.LOBE_WIDTHS:
#                     return False, f"Invalid lobe width '{width}'"

#             return True, actions[action]()
#         except Exception as e:
#             return False, str(e)

#     def query_status(self, ip, port=2202, display_id=None):
#         info = self.get_device_info(ip, self._resolve_port(port), display_id)
#         return {
#             "reachable": info.get("current_status") == "Online",
#             "device_name": info.get("device_name"),
#             "model": info.get("model"),
#             "serial_number": info.get("serial_number"),
#             "firmware": info.get("firmware"),
#             "muted": info.get("muted"),
#             "auto_coverage": info.get("auto_coverage"),
#             "error": info.get("error"),
#         }




"""
Manual Platform Plugin: ShureMXA920Plugin

Transport priority:
  1. TCP port 2202  – Shure command-string protocol (new plugin)
  2. HTTPS REST     – /api/v1/devices  (old plugin fallback)

get_device_info tries TCP first; if the device doesn't respond on 2202
it falls back to the REST API so existing cloud-managed / firmware-older
devices still work.
"""

import json
import re
import socket
import time

import requests
import urllib3

from .base import ManualPlatformPlugin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ShureMXA920Plugin(ManualPlatformPlugin):
    """Shure MXA920 / MXA910 / MXA902 / MXA710 – TCP + REST."""

    name = "shure_mxa920"
    display_name = "Shure MXA Series"
    description = "Shure MXA920/MXA910/MXA902/MXA710 devices (TCP + REST)"
    supports_display_id = False
    supports_port = False
    default_port = 2202
    SUPPORTED_MODELS = ["MXA920", "MXA910", "MXA902", "MXA710",]

    COMMANDS = {
        "device_mute":            {"description": "Set device mute state",              "params": [{"name": "state",     "type": "str"}]},
        "identify":               {"description": "Set identify flash",                  "params": [{"name": "state",     "type": "str"}]},
        "auto_coverage":          {"description": "Set auto coverage",                   "params": [{"name": "state",     "type": "str"}]},
        "reboot":                 {"description": "Reboot the device",                   "params": []},
        "factory_reset":          {"description": "Restore factory defaults",            "params": []},
        "set_led_brightness":     {"description": "Set LED brightness 0-5",             "params": [{"name": "level",     "type": "int"}]},
        "set_led_color_unmuted":  {"description": "Set unmuted LED color",               "params": [{"name": "color",     "type": "str"}]},
        "set_led_color_muted":    {"description": "Set muted LED color",                 "params": [{"name": "color",     "type": "str"}]},
        "set_led_state_unmuted":  {"description": "Set unmuted LED state",               "params": [{"name": "state",     "type": "str"}]},
        "set_led_state_muted":    {"description": "Set muted LED state",                 "params": [{"name": "state",     "type": "str"}]},
        "set_led_in_state":       {"description": "Set LED-in state",                    "params": [{"name": "state",     "type": "str"}]},
        "recall_preset":          {"description": "Recall preset 1-10",                  "params": [{"name": "preset",    "type": "int"}]},
        "set_channel_mute":       {"description": "Set channel mute",                    "params": [{"name": "channel",   "type": "int"}, {"name": "state", "type": "str"}]},
        "set_channel_gain_db":    {"description": "Set channel gain in dB",              "params": [{"name": "channel",   "type": "int"}, {"name": "db",    "type": "float"}]},
        "adjust_channel_gain_db": {"description": "Adjust channel gain by dB",           "params": [{"name": "channel",   "type": "int"}, {"name": "delta_db", "type": "float"}]},
        "reset_channel_gain":     {"description": "Reset channel gain to 0 dB",          "params": [{"name": "channel",   "type": "int"}]},
        "set_postgate_mute":      {"description": "Set postgate mute",                   "params": [{"name": "channel",   "type": "int"}, {"name": "state", "type": "str"}]},
        "set_postgate_gain_db":   {"description": "Set postgate gain in dB",             "params": [{"name": "channel",   "type": "int"}, {"name": "db",    "type": "float"}]},
        "set_intellimix_bypass":  {"description": "Set IntelliMix bypass",               "params": [{"name": "state",     "type": "str"}]},
        "set_eq_bypass":          {"description": "Set EQ bypass",                       "params": [{"name": "state",     "type": "str"}]},
        "set_eq_contour":         {"description": "Set EQ contour",                      "params": [{"name": "state",     "type": "str"}]},
        "set_channel_solo":       {"description": "Set channel solo enable/disable",     "params": [{"name": "channel",   "type": "int"}, {"name": "state", "type": "str"}]},
        "set_channel_peq":        {"description": "Set channel PEQ 0",                   "params": [{"name": "channel",   "type": "int"}, {"name": "state", "type": "str"}]},
        "set_coverage_mute":      {"description": "Set coverage area mute",              "params": [{"name": "area",      "type": "int"}, {"name": "state", "type": "str"}]},
        "set_coverage_gain_db":   {"description": "Set coverage area gain in dB",        "params": [{"name": "area",      "type": "int"}, {"name": "db",    "type": "float"}]},
        "adjust_coverage_gain_db":{"description": "Adjust coverage area gain by dB",     "params": [{"name": "area",      "type": "int"}, {"name": "delta_db", "type": "float"}]},
        "reset_coverage_gain":    {"description": "Reset coverage area gain to 0 dB",    "params": [{"name": "area",      "type": "int"}]},
        "set_array_height":       {"description": "Set array height in cm",              "params": [{"name": "height_cm", "type": "int"}]},
        "set_lobe_width":         {"description": "Set lobe width",                      "params": [{"name": "lobe",      "type": "int"}, {"name": "width", "type": "str"}]},
        "set_lobe_x":             {"description": "Set lobe X",                          "params": [{"name": "lobe",      "type": "int"}, {"name": "value", "type": "int"}]},
        "set_lobe_y":             {"description": "Set lobe Y",                          "params": [{"name": "lobe",      "type": "int"}, {"name": "value", "type": "int"}]},
        "set_lobe_z":             {"description": "Set lobe Z",                          "params": [{"name": "lobe",      "type": "int"}, {"name": "value", "type": "int"}]},
        "raw_command":            {"description": "Send raw TCP command",                "params": [{"name": "command",   "type": "str"}]},
    }

    QUERY_COMMANDS = {
        "device_info": "retrieve_device_info",
        "lights":      "get_lights_status",
        "presets":     "get_presets_status",
        "channels":    "get_channels_status",
        "intellimix":  "get_intellimix_status",
        "coverage":    "get_coverage_status",
        "lobes":       "get_lobe_status",
    }

    ALL_COLORS = [
        "RED", "ORANGE", "GOLD", "YELLOW", "YELLOWGREEN", "GREEN",
        "TURQUOISE", "POWDERBLUE", "CYAN", "SKYBLUE", "BLUE",
        "PURPLE", "LIGHTPURPLE", "VIOLET", "ORCHID", "PINK", "WHITE",
    ]
    LED_STATES    = {"ON", "OFF", "FLASHING"}
    TOGGLE_STATES = {"ON", "OFF", "TOGGLE"}
    SOLO_STATES   = {"ENABLE", "DISABLE"}
    PEQ_STATES    = {"ON", "OFF", "TOGGLE"}
    LOBE_WIDTHS   = {"NARROW", "MEDIUM", "WIDE"}

    # ─────────────────────────────────────────────────────────────────────
    #  TCP helpers  (new plugin transport)
    # ─────────────────────────────────────────────────────────────────────

    def _resolve_port(self, port=None):
        """MXA920 TCP control is always on 2202; ignore stale saved ports."""
        return int(self.default_port)

    def _resolve_rest_port(self):
        try:
            rest_port = getattr(self, "config", {}).get("rest_port") or getattr(self, "config", {}).get("https_port")
            return int(rest_port or 443)
        except Exception:
            return 443

    def _network_timeout(self, default=3, cap=5):
        try:
            configured = float(getattr(self, "config", {}).get("timeout") or getattr(self, "timeout", default) or default)
            return max(1, min(configured, cap))
        except Exception:
            return default

    def _send_tcp(self, ip, command, port=None, timeout=None):
        target_port    = self._resolve_port(port)
        target_timeout = timeout or self._network_timeout(default=3, cap=5)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(target_timeout)
                sock.connect((ip, target_port))
                sock.sendall(f"{command}\r\n".encode("ascii"))
                time.sleep(0.2)
                data = b""
                sock.settimeout(0.5)
                try:
                    while True:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                except socket.timeout:
                    pass
                return data.decode("ascii", errors="ignore").strip()
        except Exception:
            return None

    def _send_tcp_batch(self, ip, commands, port=None, timeout=None):
        target_port = self._resolve_port(port)
        target_timeout = timeout or self._network_timeout(default=3, cap=5)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(target_timeout)
                sock.connect((ip, target_port))
                payload = "\r\n".join(commands) + "\r\n"
                sock.sendall(payload.encode("ascii"))
                time.sleep(0.35)
                data = b""
                sock.settimeout(0.8)
                try:
                    while True:
                        chunk = sock.recv(8192)
                        if not chunk:
                            break
                        data += chunk
                except socket.timeout:
                    pass
                text = data.decode("ascii", errors="ignore")
                return [match.group(0).strip() for match in re.finditer(r"<[^>]*>", text)]
        except Exception:
            return []

    def _parse(self, response, keyword):
        if not response or keyword not in response:
            return None
        tokens = response.split()
        for idx, token in enumerate(tokens):
            if keyword in token and idx + 1 < len(tokens):
                return self._clean(tokens[idx + 1])
        return None

    def _clean(self, value):
        if value is None:
            return None
        return (
            str(value)
            .strip(">").strip("<")
            .strip("{").strip("}")
            .strip('"').strip("'")
            .strip()
        )

    def _response_value(self, responses, keyword, channel=None, default=None):
        keyword = str(keyword or "").upper()
        channel = str(channel).zfill(2) if channel is not None else None
        for response in responses or []:
            tokens = [self._clean(token) for token in str(response).split()]
            tokens_upper = [str(token or "").upper() for token in tokens]
            if keyword not in tokens_upper:
                continue
            if channel and channel not in tokens_upper:
                continue
            idx = tokens_upper.index(keyword)
            value_idx = idx + 1
            if value_idx < len(tokens) and channel and tokens_upper[value_idx] == channel:
                value_idx += 1
            if keyword == "PEQ" and value_idx < len(tokens) and tokens_upper[value_idx] == "0":
                value_idx += 1
            if value_idx < len(tokens):
                value = self._clean(tokens[value_idx])
                return None if value in {"", "{empty}"} else value
        return default

    def _preset_name_from_responses(self, responses, preset):
        preset_id = str(int(preset)).zfill(2)
        for response in responses or []:
            tokens = [self._clean(token) for token in str(response).split()]
            tokens_upper = [str(token or "").upper() for token in tokens]
            if "PRESET_NAME" not in tokens_upper or preset_id not in tokens_upper:
                continue
            start_idx = max(tokens_upper.index("PRESET_NAME"), tokens_upper.index(preset_id)) + 1
            name = " ".join(token for token in tokens[start_idx:] if token and token != ">").strip()
            return None if name in {"", "{empty}"} else name
        return None

    def _gain_to_db(self, raw):
        try:
            return round(int(raw) / 10.0 - 110.0, 1)
        except Exception:
            return None

    def _db_to_gain(self, db):
        return int((float(db) + 110.0) * 10)

    def _channel_id(self, number):
        return str(int(number)).zfill(2)

    def _toggle_state(self, state, allow_toggle=True):
        value   = str(state or "").strip().upper()
        allowed = self.TOGGLE_STATES if allow_toggle else {"ON", "OFF"}
        if value not in allowed:
            raise ValueError(f"Invalid state '{state}'. Expected one of {sorted(allowed)}")
        return value

    def _send_ok(self, ip, command, port=None):
        response = self._send_tcp(ip, command, port=port)
        is_set_command = str(command or "").strip().upper().startswith("< SET ")
        if response is None:
            raise ValueError("No response from device.")
        if "REP ERR" in response:
            raise ValueError(f"Device rejected command: {command}")
        if response == "" and is_set_command:
            return f"Command sent: {command}"
        if response == "":
            raise ValueError("No response from device.")
        return response

    def _send_no_ack(self, ip, command, port=None):
        response = self._send_tcp(ip, command, port=port)
        if response is None:
            raise ValueError("No response from device.")
        if "REP ERR" in response:
            raise ValueError(f"Device rejected command: {command}")
        return f"Command sent: {command}"

    def _current_channel_gain_db(self, ip, channel, port):
        ch  = self._channel_id(channel)
        raw = self._query_value(ip, f"< GET {ch} AUDIO_GAIN_HI_RES >", "AUDIO_GAIN_HI_RES", port)
        return self._gain_to_db(raw) or 0

    def _current_coverage_gain_db(self, ip, area, port):
        ca  = self._channel_id(area)
        raw = self._query_value(ip, f"< GET {ca} CA_GAIN >", "CA_GAIN", port)
        return self._gain_to_db(raw) or 0

    def _adjust_channel_gain(self, ip, channel, delta_db, port):
        ch = self._channel_id(channel)
        direction = "inc" if float(delta_db) >= 0 else "dec"
        step = int(round(abs(float(delta_db)) * 10))
        return self._send_ok(ip, f"< SET {ch} AUDIO_GAIN_HI_RES {direction} {step} >", port)

    def _adjust_coverage_gain(self, ip, area, delta_db, port):
        ca = self._channel_id(area)
        direction = "inc" if float(delta_db) >= 0 else "dec"
        step = int(round(abs(float(delta_db)) * 10))
        return self._send_ok(ip, f"< SET {ca} CA_GAIN {direction} {step} >", port)

    def _decode_command(self, command):
        if isinstance(command, dict):
            return command.get("action"), command.get("params") or {}
        if isinstance(command, str):
            stripped = command.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        return parsed.get("action"), parsed.get("params") or {}
                except Exception:
                    pass
            return stripped, {}
        return None, {}

    def _query_value(self, ip, command, keyword, port=None):
        return self._parse(self._send_tcp(ip, command, port=port), keyword)

    # ─────────────────────────────────────────────────────────────────────
    #  REST helpers  (old plugin transport — used as fallback)
    # ─────────────────────────────────────────────────────────────────────

    def _rest_session(self):
        """Build a requests.Session with optional basic-auth from config."""
        session = requests.Session()
        session.verify = False
        session.headers.update({
            "Accept":       "application/json",
            "Content-Type": "application/json",
        })
        username = self.config.get("username") if hasattr(self, "config") else None
        password = self.config.get("password") if hasattr(self, "config") else None
        if username and password:
            session.auth = (username, password)
        return session

    def _rest_base_url(self, ip, port=443):
        return f"https://{ip}:{port}/api/v1"

    def _parse_rest_device_node(self, node):
        """Parse a single device node from the REST /devices edge list."""
        hw  = node.get("hardwareIdentity",      {}) if isinstance(node, dict) else {}
        sw  = node.get("softwareIdentity",       {}) if isinstance(node, dict) else {}
        com = node.get("communicationProtocol",  {}) if isinstance(node, dict) else {}
        return {
            "device_id":     hw.get("deviceId")       or "",
            "serial_number": hw.get("serialNumber")   or "",
            "model":         sw.get("model")           or "",
            "firmware":      sw.get("firmwareVersion") or "",
            "firmware_valid":sw.get("firmwareValid", True),
            "device_state":  node.get("deviceState")  if isinstance(node, dict) else None,
            "compatibility": node.get("compatibility") if isinstance(node, dict) else None,
            "ip_address":    com.get("address")        or "",
            "capabilities":  node.get("capabilities")  or [],
        }

    def _get_device_info_rest(self, ip, rest_port=443, display_id=None):
        """
        Replicated from the old ShureMXA920Plugin.get_device_info().
        Queries https://<ip>:<rest_port>/api/v1/devices and optionally
        fetches the mute state from the audio/mute endpoint.
        Returns the same-shaped dict as get_device_info() so callers
        can use either transport transparently.
        """
        session = self._rest_session()
        try:
            devices_url = f"{self._rest_base_url(ip, rest_port)}/devices"
            resp = session.get(devices_url, timeout=self._network_timeout(default=3, cap=5))

            if resp.status_code in (401, 403):
                return {
                    "ip_address":     ip,
                    "port":           rest_port,
                    "display_id":     display_id,
                    "make":           "Shure",
                    "device_type":    "Shure MXA",
                    "current_status": "Offline",
                    "error":          "Invalid username or password.",
                }

            resp.raise_for_status()
            data  = resp.json() if resp.content else {}
            edges = data.get("edges", [])

            if not edges:
                return {
                    "ip_address":     ip,
                    "port":           rest_port,
                    "display_id":     display_id,
                    "make":           "Shure",
                    "device_type":    "Shure MXA",
                    "current_status": "Offline",
                    "error":          "No devices found on this IP.",
                }

            node      = edges[0].get("node", {}) if isinstance(edges[0], dict) else {}
            device    = self._parse_rest_device_node(node)
            device_id = device.get("device_id")

            # Fetch mute state
            muted = None
            if device_id:
                try:
                    mute_url  = f"{self._rest_base_url(ip, rest_port)}/devices/{device_id}/audio/mute"
                    mute_resp = session.get(mute_url, timeout=self._network_timeout(default=3, cap=5))
                    if mute_resp.ok and mute_resp.content:
                        muted = mute_resp.json().get("mute")
                except Exception:
                    muted = None

            return {
                "ip_address":     ip,
                "port":           rest_port,
                "display_id":     display_id,
                "make":           "Shure",
                "device_type":    "Shure MXA",
                "device_name":    device.get("model") or "Shure MXA Device",
                "model":          device.get("model"),
                "serial_number":  device.get("serial_number"),
                "firmware":       device.get("firmware"),
                "firmware_valid": device.get("firmware_valid"),
                "mac_address":    device.get("device_id"),
                "device_id":      device.get("device_id"),
                "device_state":   device.get("device_state"),
                "compatibility":  device.get("compatibility"),
                "capabilities":   device.get("capabilities"),
                "muted":          muted,
                "current_status": "Online",
                "transport":      "rest",
                "raw_data":       device,
            }

        except Exception as exc:
            return {
                "ip_address":     ip,
                "port":           rest_port,
                "display_id":     display_id,
                "make":           "Shure",
                "device_type":    "Shure MXA",
                "current_status": "Offline",
                "error":          str(exc),
            }
        finally:
            try:
                session.close()
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────
    #  TCP query helpers  (unchanged from new plugin)
    # ─────────────────────────────────────────────────────────────────────

    def retrieve_device_info(self, ip, port=2202):
        port = self._resolve_port(port)
        return {
            "ip_address":    ip,
            "model":         self._query_value(ip, "< GET MODEL >",                          "MODEL",                         port) or "N/A",
            "serial_number": self._query_value(ip, "< GET SERIAL_NUM >",                     "SERIAL_NUM",                    port) or "N/A",
            "firmware":      self._query_value(ip, "< GET FW_VER >",                         "FW_VER",                        port) or "N/A",
            "device_id":     self._query_value(ip, "< GET DEVICE_ID >",                      "DEVICE_ID",                     port) or "N/A",
            "dante_name":    self._query_value(ip, "< GET NA_DEVICE_NAME >",                 "NA_DEVICE_NAME",                port) or "N/A",
            "mac_address":   self._query_value(ip, "< GET CONTROL_MAC_ADDR >",               "CONTROL_MAC_ADDR",              port) or "N/A",
            "ip_audio":      self._query_value(ip, "< GET IP_ADDR_NET_AUDIO_PRIMARY >",      "IP_ADDR_NET_AUDIO_PRIMARY",     port) or "N/A",
            "subnet_mask":   self._query_value(ip, "< GET IP_SUBNET_NET_AUDIO_PRIMARY >",    "IP_SUBNET_NET_AUDIO_PRIMARY",   port) or "N/A",
            "gateway":       self._query_value(ip, "< GET IP_GATEWAY_NET_AUDIO_PRIMARY >",   "IP_GATEWAY_NET_AUDIO_PRIMARY",  port) or "N/A",
            "encryption":    self._query_value(ip, "< GET ENCRYPTION >",                     "ENCRYPTION",                    port) or "N/A",
            "muted":         self._query_value(ip, "< GET DEVICE_AUDIO_MUTE >",              "DEVICE_AUDIO_MUTE",             port) or "N/A",
            "auto_coverage": self._query_value(ip, "< GET AUTO_COVERAGE >",                  "AUTO_COVERAGE",                 port) or "N/A",
            "last_error":    self._send_tcp(ip,    "< GET LAST_ERROR_EVENT >",               port=port)                             or "N/A",
        }

    def get_lights_status(self, ip, port=2202):
        port = self._resolve_port(port)
        return {
            "brightness":     self._query_value(ip, "< GET LED_BRIGHTNESS >",      "LED_BRIGHTNESS",      port),
            "color_unmuted":  self._query_value(ip, "< GET LED_COLOR_UNMUTED >",   "LED_COLOR_UNMUTED",   port),
            "state_unmuted":  self._query_value(ip, "< GET LED_STATE_UNMUTED >",   "LED_STATE_UNMUTED",   port),
            "color_muted":    self._query_value(ip, "< GET LED_COLOR_MUTED >",     "LED_COLOR_MUTED",     port),
            "state_muted":    self._query_value(ip, "< GET LED_STATE_MUTED >",     "LED_STATE_MUTED",     port),
            "led_in_state":   self._query_value(ip, "< GET DEV_LED_IN_STATE >",    "DEV_LED_IN_STATE",    port),
        }

    def get_presets_status(self, ip, port=2202):
        port   = self._resolve_port(port)
        active = self._query_value(ip, "< GET PRESET >", "PRESET", port)
        presets = []
        for preset in range(1, 11):
            num      = str(preset).zfill(2)
            response = self._send_tcp(ip, f"< GET PRESET_NAME {num} >", port=port)
            parts    = response.split() if response else []
            name     = parts[4] if len(parts) >= 5 else None
            if name in ("{empty}", ">", "<", None):
                name = None
            presets.append({
                "preset": preset,
                "name":   name,
                "active": str(active) == str(preset),
            })
        return {"active_preset": active, "presets": presets}

    def get_channels_status(self, ip, port=2202):
        port     = self._resolve_port(port)
        channels = []
        for number in range(1, 10):
            ch    = self._channel_id(number)
            label = "Automix" if number == 9 else f"Ch {number}"
            gain_raw = self._query_value(ip, f"< GET {ch} AUDIO_GAIN_HI_RES >", "AUDIO_GAIN_HI_RES", port)
            channels.append({
                "channel":  number,
                "name":     self._query_value(ip, f"< GET {ch} CHAN_NAME >",               "CHAN_NAME",               port) or label,
                "gain_raw": gain_raw,
                "gain_db":  self._gain_to_db(gain_raw),
                "muted":    self._query_value(ip, f"< GET {ch} AUDIO_MUTE >",             "AUDIO_MUTE",              port),
                "rms":      self._query_value(ip, f"< GET {ch} AUDIO_IN_RMS_LVL >",       "AUDIO_IN_RMS_LVL",        port),
                "clip":     self._query_value(ip, f"< GET {ch} AUDIO_OUT_CLIP_INDICATOR >","AUDIO_OUT_CLIP_INDICATOR", port),
            })
        return {
            "auto_coverage": self._query_value(ip, "< GET AUTO_COVERAGE >", "AUTO_COVERAGE", port),
            "channels":      channels,
        }

    def get_intellimix_status(self, ip, port=2202):
        port     = self._resolve_port(port)
        channels = []
        for number in range(1, 9):
            ch = self._channel_id(number)
            channels.append({
                "channel": number,
                "solo":    self._query_value(ip, f"< GET {ch} CHAN_AUTOMIX_SOLO_EN >",   "CHAN_AUTOMIX_SOLO_EN",  port),
                "gate":    self._query_value(ip, f"< GET {ch} AUTOMIX_GATE_OUT_EXT_SIG >","AUTOMIX_GATE_OUT_EXT_SIG", port),
                "peq":     self._query_value(ip, f"< GET {ch} PEQ 0 >",                  "PEQ",                  port),
            })
        return {
            "bypass_imx":     self._query_value(ip, "< GET BYPASS_IMX >",      "BYPASS_IMX",     port),
            "bypass_all_eq":  self._query_value(ip, "< GET BYPASS_ALL_EQ >",   "BYPASS_ALL_EQ",  port),
            "eq_contour":     self._query_value(ip, "< GET EQ_CONTOUR >",      "EQ_CONTOUR",     port),
            "num_active_mics":self._query_value(ip, "< GET NUM_ACTIVE_MICS >", "NUM_ACTIVE_MICS",port),
            "channels":       channels,
        }

    def get_coverage_status(self, ip, port=2202):
        port  = self._resolve_port(port)
        areas = []
        for number in range(1, 9):
            ca       = self._channel_id(number)
            gain_raw = self._query_value(ip, f"< GET {ca} CA_GAIN >", "CA_GAIN", port)
            areas.append({
                "area":     number,
                "mute":     self._query_value(ip, f"< GET {ca} CA_MUTE >",                "CA_MUTE",             port),
                "gain_raw": gain_raw,
                "gain_db":  self._gain_to_db(gain_raw),
                "gate":     self._query_value(ip, f"< GET {ca} AUTOMIX_GATE_OUT_CA >",    "AUTOMIX_GATE_OUT_CA", port),
            })
        return {
            "auto_coverage": self._query_value(ip, "< GET AUTO_COVERAGE >", "AUTO_COVERAGE", port),
            "areas":         areas,
        }

    def get_lobe_status(self, ip, port=2202):
        port  = self._resolve_port(port)
        lobes = []
        for number in range(1, 9):
            ch = self._channel_id(number)
            lobes.append({
                "lobe":  number,
                "width": self._query_value(ip, f"< GET {ch} BEAM_W >", "BEAM_W", port),
                "x":     self._query_value(ip, f"< GET {ch} BEAM_X >", "BEAM_X", port),
                "y":     self._query_value(ip, f"< GET {ch} BEAM_Y >", "BEAM_Y", port),
                "z":     self._query_value(ip, f"< GET {ch} BEAM_Z >", "BEAM_Z", port),
            })
        return {
            "array_height": self._query_value(ip, "< GET ARRAY_HEIGHT >", "ARRAY_HEIGHT", port),
            "lobes":        lobes,
        }

    def get_tcp_status_snapshot(self, ip, port=2202):
        port = self._resolve_port(port)
        commands = [
            "< GET MODEL >",
            "< GET SERIAL_NUM >",
            "< GET FW_VER >",
            "< GET DEVICE_ID >",
            "< GET NA_DEVICE_NAME >",
            "< GET CONTROL_MAC_ADDR >",
            "< GET IP_ADDR_NET_AUDIO_PRIMARY >",
            "< GET IP_SUBNET_NET_AUDIO_PRIMARY >",
            "< GET IP_GATEWAY_NET_AUDIO_PRIMARY >",
            "< GET ENCRYPTION >",
            "< GET DEVICE_AUDIO_MUTE >",
            "< GET AUTO_COVERAGE >",
            "< GET LED_BRIGHTNESS >",
            "< GET LED_COLOR_UNMUTED >",
            "< GET LED_STATE_UNMUTED >",
            "< GET LED_COLOR_MUTED >",
            "< GET LED_STATE_MUTED >",
            "< GET DEV_LED_IN_STATE >",
            "< GET PRESET >",
            "< GET BYPASS_IMX >",
            "< GET BYPASS_ALL_EQ >",
            "< GET EQ_CONTOUR >",
            "< GET NUM_ACTIVE_MICS >",
            "< GET ARRAY_HEIGHT >",
        ]
        commands += [f"< GET PRESET_NAME {str(preset).zfill(2)} >" for preset in range(1, 11)]
        for number in range(1, 10):
            channel = self._channel_id(number)
            commands += [
                f"< GET {channel} CHAN_NAME >",
                f"< GET {channel} AUDIO_GAIN_HI_RES >",
                f"< GET {channel} AUDIO_MUTE >",
                f"< GET {channel} AUDIO_IN_RMS_LVL >",
                f"< GET {channel} AUDIO_OUT_CLIP_INDICATOR >",
            ]
        for number in range(1, 9):
            channel = self._channel_id(number)
            commands += [
                f"< GET {channel} CHAN_AUTOMIX_SOLO_EN >",
                f"< GET {channel} AUTOMIX_GATE_OUT_EXT_SIG >",
                f"< GET {channel} PEQ 0 >",
                f"< GET {channel} CA_MUTE >",
                f"< GET {channel} CA_GAIN >",
                f"< GET {channel} AUTOMIX_GATE_OUT_CA >",
                f"< GET {channel} BEAM_W >",
                f"< GET {channel} BEAM_X >",
                f"< GET {channel} BEAM_Y >",
                f"< GET {channel} BEAM_Z >",
            ]

        responses = self._send_tcp_batch(ip, commands, port=port, timeout=3)
        if not responses:
            return {}

        device = {
            "ip_address": ip,
            "model": self._response_value(responses, "MODEL"),
            "serial_number": self._response_value(responses, "SERIAL_NUM"),
            "firmware": self._response_value(responses, "FW_VER"),
            "device_id": self._response_value(responses, "DEVICE_ID"),
            "dante_name": self._response_value(responses, "NA_DEVICE_NAME"),
            "mac_address": self._response_value(responses, "CONTROL_MAC_ADDR"),
            "ip_audio": self._response_value(responses, "IP_ADDR_NET_AUDIO_PRIMARY"),
            "subnet_mask": self._response_value(responses, "IP_SUBNET_NET_AUDIO_PRIMARY"),
            "gateway": self._response_value(responses, "IP_GATEWAY_NET_AUDIO_PRIMARY"),
            "encryption": self._response_value(responses, "ENCRYPTION"),
            "muted": self._response_value(responses, "DEVICE_AUDIO_MUTE"),
            "auto_coverage": self._response_value(responses, "AUTO_COVERAGE"),
        }
        lights = {
            "brightness": self._response_value(responses, "LED_BRIGHTNESS"),
            "color_unmuted": self._response_value(responses, "LED_COLOR_UNMUTED"),
            "state_unmuted": self._response_value(responses, "LED_STATE_UNMUTED"),
            "color_muted": self._response_value(responses, "LED_COLOR_MUTED"),
            "state_muted": self._response_value(responses, "LED_STATE_MUTED"),
            "led_in_state": self._response_value(responses, "DEV_LED_IN_STATE"),
        }
        active_preset = self._response_value(responses, "PRESET")
        presets = [
            {
                "preset": preset,
                "name": self._preset_name_from_responses(responses, preset),
                "active": str(active_preset) == str(preset).zfill(2) or str(active_preset) == str(preset),
            }
            for preset in range(1, 11)
        ]
        channels = []
        for number in range(1, 10):
            channel = self._channel_id(number)
            gain_raw = self._response_value(responses, "AUDIO_GAIN_HI_RES", channel=channel)
            channels.append({
                "channel": number,
                "name": self._response_value(responses, "CHAN_NAME", channel=channel) or ("Automix" if number == 9 else f"Ch {number}"),
                "gain_raw": gain_raw,
                "gain_db": self._gain_to_db(gain_raw),
                "muted": self._response_value(responses, "AUDIO_MUTE", channel=channel),
                "rms": self._response_value(responses, "AUDIO_IN_RMS_LVL", channel=channel),
                "clip": self._response_value(responses, "AUDIO_OUT_CLIP_INDICATOR", channel=channel),
            })
        intellimix_channels = []
        areas = []
        lobes = []
        for number in range(1, 9):
            channel = self._channel_id(number)
            intellimix_channels.append({
                "channel": number,
                "solo": self._response_value(responses, "CHAN_AUTOMIX_SOLO_EN", channel=channel),
                "gate": self._response_value(responses, "AUTOMIX_GATE_OUT_EXT_SIG", channel=channel),
                "peq": self._response_value(responses, "PEQ", channel=channel),
            })
            ca_gain_raw = self._response_value(responses, "CA_GAIN", channel=channel)
            areas.append({
                "area": number,
                "mute": self._response_value(responses, "CA_MUTE", channel=channel),
                "gain_raw": ca_gain_raw,
                "gain_db": self._gain_to_db(ca_gain_raw),
                "gate": self._response_value(responses, "AUTOMIX_GATE_OUT_CA", channel=channel),
            })
            lobes.append({
                "lobe": number,
                "width": self._response_value(responses, "BEAM_W", channel=channel),
                "x": self._response_value(responses, "BEAM_X", channel=channel),
                "y": self._response_value(responses, "BEAM_Y", channel=channel),
                "z": self._response_value(responses, "BEAM_Z", channel=channel),
            })

        return {
            "device_info": device,
            "lights": lights,
            "presets": {"active_preset": active_preset, "presets": presets},
            "channels": {"auto_coverage": device.get("auto_coverage"), "channels": channels},
            "intellimix": {
                "bypass_imx": self._response_value(responses, "BYPASS_IMX"),
                "bypass_all_eq": self._response_value(responses, "BYPASS_ALL_EQ"),
                "eq_contour": self._response_value(responses, "EQ_CONTOUR"),
                "num_active_mics": self._response_value(responses, "NUM_ACTIVE_MICS"),
                "channels": intellimix_channels,
            },
            "coverage": {"auto_coverage": device.get("auto_coverage"), "areas": areas},
            "lobes": {"array_height": self._response_value(responses, "ARRAY_HEIGHT"), "lobes": lobes},
            "raw_responses": responses,
        }

    # ─────────────────────────────────────────────────────────────────────
    #  get_device_info  — TCP first, REST fallback  (merged from both plugins)
    # ─────────────────────────────────────────────────────────────────────

    def get_device_info(self, ip, port=2202, display_id=None):
        """
        Try TCP (port 2202) first.
        If the device doesn't respond on TCP, fall back to the old
        REST API (HTTPS port 443) so legacy / cloud-managed devices still work.
        """
        tcp_port = self._resolve_port(port)

        # ── 1. TCP probe ──────────────────────────────────────────────────
        model_probe = self._send_tcp(ip, "< GET MODEL >", port=tcp_port)

        if model_probe:
            # TCP is alive — use full TCP device info
            try:
                device = self.retrieve_device_info(ip, port=tcp_port)
                return {
                    "ip_address":     ip,
                    "port":           tcp_port,
                    "display_id":     display_id,
                    "make":           "Shure",
                    "device_type":    "Shure MXA",
                    "device_name":    device.get("dante_name") or device.get("model") or "Shure MXA Device",
                    "model":          device.get("model"),
                    "serial_number":  device.get("serial_number"),
                    "firmware":       device.get("firmware"),
                    "mac_address":    device.get("mac_address"),
                    "device_id":      device.get("device_id"),
                    "dante_name":     device.get("dante_name"),
                    "subnet_mask":    device.get("subnet_mask"),
                    "gateway":        device.get("gateway"),
                    "encryption":     device.get("encryption"),
                    "muted":          device.get("muted"),
                    "auto_coverage":  device.get("auto_coverage"),
                    "last_error":     device.get("last_error"),
                    "current_status": "Online",
                    "transport":      "tcp",
                    "raw_device_info": device,
                    "raw_queries": {
                        "device_info": device,
                        "lights":      self.get_lights_status(ip,    port=tcp_port),
                        "presets":     self.get_presets_status(ip,   port=tcp_port),
                        "channels":    self.get_channels_status(ip,  port=tcp_port),
                        "intellimix":  self.get_intellimix_status(ip,port=tcp_port),
                        "coverage":    self.get_coverage_status(ip,  port=tcp_port),
                        "lobes":       self.get_lobe_status(ip,      port=tcp_port),
                    },
                }
            except Exception as tcp_exc:
                # TCP connected but something went wrong mid-query — still try REST
                tcp_error = str(tcp_exc)
        else:
            tcp_error = f"No TCP response from {ip}:{tcp_port}"

        # ── 2. REST fallback (old plugin logic) ───────────────────────────
        rest_result = self._get_device_info_rest(ip, rest_port=443, display_id=display_id)

        if rest_result.get("current_status") == "Online":
            # Annotate that we fell back so callers / logs can tell
            rest_result["tcp_error"]  = tcp_error
            rest_result["transport"]  = "rest"
            return rest_result

        # ── 3. Both transports failed ─────────────────────────────────────
        return {
            "ip_address":     ip,
            "port":           tcp_port,
            "display_id":     display_id,
            "make":           "Shure",
            "device_type":    "Shure MXA",
            "current_status": "Offline",
            "error":          f"TCP: {tcp_error} | REST: {rest_result.get('error', 'failed')}",
        }

    def get_device_info_fast(self, ip, port=2202, display_id=None):
        """
        Fast status/info path: use REST only, with one lightweight TCP model
        probe as fallback. Full TCP status scraping is intentionally skipped.
        """
        tcp_port = self._resolve_port(port)
        rest_port = self._resolve_rest_port()
        rest_result = self._get_device_info_rest(ip, rest_port=rest_port, display_id=display_id)
        tcp_snapshot = self.get_tcp_status_snapshot(ip, port=tcp_port)

        if rest_result.get("current_status") == "Online":
            rest_result["tcp_port"] = tcp_port
            if tcp_snapshot:
                tcp_device = tcp_snapshot.get("device_info") or {}
                for key in (
                    "model", "serial_number", "firmware", "device_id", "dante_name",
                    "mac_address", "ip_audio", "subnet_mask", "gateway", "encryption",
                    "muted", "auto_coverage",
                ):
                    if tcp_device.get(key) not in (None, "", "N/A"):
                        rest_result[key] = tcp_device.get(key)
                rest_result["device_name"] = tcp_device.get("dante_name") or rest_result.get("device_name")
                rest_result["raw_queries"] = tcp_snapshot
                rest_result["transport"] = "rest+tcp-status"
            return rest_result

        tcp_device = tcp_snapshot.get("device_info") if tcp_snapshot else {}
        model = tcp_device.get("model") if tcp_device else None
        if model:
            return {
                "ip_address":     ip,
                "port":           tcp_port,
                "display_id":     display_id,
                "make":           "Shure",
                "device_type":    "Shure MXA",
                "device_name":    tcp_device.get("dante_name") or model,
                "model":          model,
                "serial_number":  tcp_device.get("serial_number"),
                "firmware":       tcp_device.get("firmware"),
                "mac_address":    tcp_device.get("mac_address"),
                "device_id":      tcp_device.get("device_id"),
                "dante_name":     tcp_device.get("dante_name"),
                "ip_audio":       tcp_device.get("ip_audio"),
                "subnet_mask":    tcp_device.get("subnet_mask"),
                "gateway":        tcp_device.get("gateway"),
                "encryption":     tcp_device.get("encryption"),
                "muted":          tcp_device.get("muted"),
                "auto_coverage":  tcp_device.get("auto_coverage"),
                "current_status": "Online",
                "transport":      "tcp-lite",
                "rest_error":     rest_result.get("error"),
                "raw_queries":    tcp_snapshot,
            }

        return {
            "ip_address":     ip,
            "port":           tcp_port,
            "display_id":     display_id,
            "make":           "Shure",
            "device_type":    "Shure MXA",
            "current_status": "Offline",
            "error":          f"REST: {rest_result.get('error', 'failed')} | TCP: no response from {ip}:{tcp_port}",
        }

    # ─────────────────────────────────────────────────────────────────────
    #  REST command helpers
    #  These mirror the TCP commands but use the HTTPS /api/v1 endpoints.
    #  Used automatically when the device only responds on REST (port 443).
    # ─────────────────────────────────────────────────────────────────────

    def _tcp_alive(self, ip: str) -> bool:
        """Quick 1-second probe to see if TCP 2202 is reachable."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((ip, self.default_port))
                return True
        except Exception:
            return False

    def _send_rest_command(self, ip: str, action: str, params: dict) -> tuple:
        """
        Execute a command via the REST API (/api/v1/devices/<id>/…).
        Returns (success: bool, message: str).

        REST command map (from Shure Network Audio API):
          device_mute          → PUT /devices/{id}/audio/mute           body: {"mute": true|false}
          identify             → PUT /devices/{id}/identify              body: {"flash": true|false}
          set_led_brightness   → PUT /devices/{id}/leds/brightness       body: {"brightness": N}
          set_led_color_unmuted→ PUT /devices/{id}/leds/unmutedColor     body: {"color": "GREEN"}
          set_led_color_muted  → PUT /devices/{id}/leds/mutedColor       body: {"color": "RED"}
          set_led_state_unmuted→ PUT /devices/{id}/leds/unmutedState     body: {"state": "ON"}
          set_led_state_muted  → PUT /devices/{id}/leds/mutedState       body: {"state": "ON"}
          recall_preset        → PUT /devices/{id}/presets/active        body: {"preset": N}
          reboot               → POST /devices/{id}/reboot
          auto_coverage        → PUT /devices/{id}/coverage/auto         body: {"enabled": true|false}
          set_channel_mute     → PUT /devices/{id}/channels/{ch}/mute    body: {"mute": true|false}
          adjust_channel_gain_db→PUT /devices/{id}/channels/{ch}/gainAdjust body: {"gainAdjust": N}
          set_channel_gain_db  → PUT /devices/{id}/channels/{ch}/gain    body: {"gain": N}  (raw)
        """
        session = self._rest_session()
        try:
            # Step 1 — get device_id
            devices_url = f"{self._rest_base_url(ip, 443)}/devices"
            resp = session.get(devices_url, timeout=self._network_timeout(default=3, cap=5))
            resp.raise_for_status()
            edges = (resp.json() or {}).get("edges", [])
            if not edges:
                return False, "No device found on REST API"
            node      = edges[0].get("node", {}) if isinstance(edges[0], dict) else {}
            hw        = node.get("hardwareIdentity", {})
            device_id = hw.get("deviceId") or ""
            if not device_id:
                return False, "Could not determine device_id from REST API"

            base = f"{self._rest_base_url(ip, 443)}/devices/{device_id}"

            # Step 2 — map action → REST call
            if action == "device_mute":
                state = str(params.get("state", "OFF")).strip().upper()
                r = session.put(f"{base}/audio/mute",
                                json={"mute": state == "ON"},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Mute set to {state}" if r.ok else r.text

            if action == "identify":
                state = str(params.get("state", "ON")).strip().upper()
                r = session.put(f"{base}/identify",
                                json={"flash": state == "ON"},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, "Identify flash sent" if r.ok else r.text

            if action == "reboot":
                r = session.post(f"{base}/reboot", timeout=self._network_timeout(default=3, cap=5))
                return r.ok, "Reboot sent" if r.ok else r.text

            if action == "auto_coverage":
                state = str(params.get("state", "OFF")).strip().upper()
                r = session.put(f"{base}/coverage/auto",
                                json={"enabled": state == "ON"},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Auto coverage set to {state}" if r.ok else r.text

            if action == "set_led_brightness":
                level = int(params.get("level", 3))
                r = session.put(f"{base}/leds/brightness",
                                json={"brightness": level},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Brightness set to {level}" if r.ok else r.text

            if action == "set_led_color_unmuted":
                color = str(params.get("color", "GREEN")).strip().upper()
                r = session.put(f"{base}/leds/unmutedColor",
                                json={"color": color},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Unmuted LED color set to {color}" if r.ok else r.text

            if action == "set_led_color_muted":
                color = str(params.get("color", "RED")).strip().upper()
                r = session.put(f"{base}/leds/mutedColor",
                                json={"color": color},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Muted LED color set to {color}" if r.ok else r.text

            if action == "set_led_state_unmuted":
                state = str(params.get("state", "ON")).strip().upper()
                r = session.put(f"{base}/leds/unmutedState",
                                json={"state": state},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Unmuted LED state set to {state}" if r.ok else r.text

            if action == "set_led_state_muted":
                state = str(params.get("state", "ON")).strip().upper()
                r = session.put(f"{base}/leds/mutedState",
                                json={"state": state},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Muted LED state set to {state}" if r.ok else r.text

            if action == "recall_preset":
                preset = int(params.get("preset", 1))
                r = session.put(f"{base}/presets/active",
                                json={"preset": preset},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Preset {preset} recalled" if r.ok else r.text

            if action == "set_channel_mute":
                ch    = int(params.get("channel", 1))
                state = str(params.get("state", "OFF")).strip().upper()
                r = session.put(f"{base}/channels/{ch}/mute",
                                json={"mute": state == "ON"},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Channel {ch} mute set to {state}" if r.ok else r.text

            if action == "set_channel_gain_db":
                ch  = int(params.get("channel", 1))
                db  = float(params.get("db", 0))
                raw = self._db_to_gain(db)
                r = session.put(f"{base}/channels/{ch}/gain",
                                json={"gain": raw},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Channel {ch} gain set to {db} dB" if r.ok else r.text

            if action == "adjust_channel_gain_db":
                ch    = int(params.get("channel", 1))
                delta = float(params.get("delta_db", 1))
                r = session.put(f"{base}/channels/{ch}/gainAdjust",
                                json={"gainAdjust": delta},
                                timeout=self._network_timeout(default=3, cap=5))
                return r.ok, f"Channel {ch} gain adjusted by {delta} dB" if r.ok else r.text

            # Fallback — action not mapped to REST
            return False, f"Action '{action}' is not supported over REST (TCP only)"

        except Exception as exc:
            return False, f"REST command error: {exc}"
        finally:
            try:
                session.close()
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────
    #  send_command  — TCP first, REST fallback
    # ─────────────────────────────────────────────────────────────────────

    def send_command(self, ip, port, display_id, command, **kwargs):
        """
        Execute a control command.

        Transport selection (mirrors get_device_info):
          1. Try TCP port 2202 first (1-second probe).
          2. If TCP is unreachable, route the command through the REST API.
        """
        try:
            action, params = self._decode_command(command)
            params = params or {}
            if kwargs.get("params"):
                params = {**params, **(kwargs.get("params") or {})}
            if not action:
                return False, "Missing command action."

            target_port = self._resolve_port(port)

            # ── raw TCP passthrough — always uses TCP ─────────────────────
            if action == "raw_command":
                tcp_command = params.get("command") or (
                    command if isinstance(command, str) and command.strip().startswith("<") else None
                )
                if not tcp_command:
                    return False, "raw_command requires params.command"
                return True, self._send_ok(ip, tcp_command, port=target_port)

            # ── input validation (transport-independent) ──────────────────
            if action in {"set_led_color_unmuted", "set_led_color_muted"}:
                color = str(params.get("color", "")).strip().upper()
                if color not in self.ALL_COLORS:
                    return False, f"Invalid color '{color}'"
            if action in {"set_led_state_unmuted", "set_led_state_muted"}:
                state = str(params.get("state", "")).strip().upper()
                if state not in self.LED_STATES:
                    return False, f"Invalid LED state '{state}'"
            if action == "set_channel_solo":
                state = str(params.get("state", "")).strip().upper()
                if state not in self.SOLO_STATES:
                    return False, f"Invalid solo state '{state}'"
            if action == "set_channel_peq":
                state = str(params.get("state", "")).strip().upper()
                if state not in self.PEQ_STATES:
                    return False, f"Invalid PEQ state '{state}'"
            if action == "set_lobe_width":
                width = str(params.get("width", "")).strip().upper()
                if width not in self.LOBE_WIDTHS:
                    return False, f"Invalid lobe width '{width}'"

            # ── TCP command map ───────────────────────────────────────────
            def _tcp_actions():
                return {
                    "device_mute":            lambda: self._send_ok(ip, f"< SET DEVICE_AUDIO_MUTE {self._toggle_state(params.get('state'))} >", target_port),
                    "identify":               lambda: self._send_ok(ip, f"< SET FLASH {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
                    "auto_coverage":          lambda: self._send_ok(ip, f"< SET AUTO_COVERAGE {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
                    "reboot":                 lambda: self._send_no_ack(ip, "< SET REBOOT >", target_port),
                    "factory_reset":          lambda: self._send_ok(ip, "< SET DEFAULT_SETTINGS >", target_port),
                    "set_led_brightness":     lambda: self._send_ok(ip, f"< SET LED_BRIGHTNESS {int(params.get('level'))} >", target_port),
                    "set_led_color_unmuted":  lambda: self._send_ok(ip, f"< SET LED_COLOR_UNMUTED {str(params.get('color')).strip().upper()} >", target_port),
                    "set_led_color_muted":    lambda: self._send_ok(ip, f"< SET LED_COLOR_MUTED {str(params.get('color')).strip().upper()} >", target_port),
                    "set_led_state_unmuted":  lambda: self._send_ok(ip, f"< SET LED_STATE_UNMUTED {str(params.get('state')).strip().upper()} >", target_port),
                    "set_led_state_muted":    lambda: self._send_ok(ip, f"< SET LED_STATE_MUTED {str(params.get('state')).strip().upper()} >", target_port),
                    "set_led_in_state":       lambda: self._send_ok(ip, f"< SET DEV_LED_IN_STATE {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
                    "recall_preset":          lambda: self._send_ok(ip, f"< SET PRESET {self._channel_id(params.get('preset'))} >", target_port),
                    "set_channel_mute":       lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_MUTE {self._toggle_state(params.get('state'))} >", target_port),
                    "set_channel_gain_db":    lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_GAIN_HI_RES {self._db_to_gain(params.get('db'))} >", target_port),
                    "adjust_channel_gain_db": lambda: self._adjust_channel_gain(ip, params.get("channel"), params.get("delta_db"), target_port),
                    "reset_channel_gain":     lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_GAIN_HI_RES {self._db_to_gain(0)} >", target_port),
                    "set_postgate_mute":      lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_MUTE_POSTGATE {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
                    "set_postgate_gain_db":   lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} AUDIO_GAIN_POSTGATE {self._db_to_gain(params.get('db'))} >", target_port),
                    "set_intellimix_bypass":  lambda: self._send_ok(ip, f"< SET BYPASS_IMX {self._toggle_state(params.get('state'))} >", target_port),
                    "set_eq_bypass":          lambda: self._send_ok(ip, f"< SET BYPASS_ALL_EQ {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
                    "set_eq_contour":         lambda: self._send_ok(ip, f"< SET EQ_CONTOUR {self._toggle_state(params.get('state'), allow_toggle=False)} >", target_port),
                    "set_channel_solo":       lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} CHAN_AUTOMIX_SOLO_EN {str(params.get('state')).strip().upper()} >", target_port),
                    "set_channel_peq":        lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('channel'))} PEQ 0 {str(params.get('state')).strip().upper()} >", target_port),
                    "set_coverage_mute":      lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('area'))} CA_MUTE {self._toggle_state(params.get('state'))} >", target_port),
                    "set_coverage_gain_db":   lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('area'))} CA_GAIN {self._db_to_gain(params.get('db'))} >", target_port),
                    "adjust_coverage_gain_db":lambda: self._adjust_coverage_gain(ip, params.get("area"), params.get("delta_db"), target_port),
                    "reset_coverage_gain":    lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('area'))} CA_GAIN {self._db_to_gain(0)} >", target_port),
                    "set_array_height":       lambda: self._send_ok(ip, f"< SET ARRAY_HEIGHT {int(params.get('height_cm'))} >", target_port),
                    "set_lobe_width":         lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('lobe'))} BEAM_W {str(params.get('width')).strip().upper()} >", target_port),
                    "set_lobe_x":             lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('lobe'))} BEAM_X {int(params.get('value'))} >", target_port),
                    "set_lobe_y":             lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('lobe'))} BEAM_Y {int(params.get('value'))} >", target_port),
                    "set_lobe_z":             lambda: self._send_ok(ip, f"< SET {self._channel_id(params.get('lobe'))} BEAM_Z {int(params.get('value'))} >", target_port),
                }

            # ── Transport selection ───────────────────────────────────────
            if self._tcp_alive(ip):
                # TCP is up — use TCP command map
                tcp_map = _tcp_actions()
                if action not in tcp_map:
                    return False, f"Unknown command: {action}"
                return True, tcp_map[action]()
            else:
                # TCP unreachable — route through REST
                return self._send_rest_command(ip, action, params)

        except Exception as exc:
            return False, str(exc)

    # ─────────────────────────────────────────────────────────────────────
    #  query_status  — rich version (TCP) or basic (REST)
    # ─────────────────────────────────────────────────────────────────────

    def query_status(self, ip, port=2202, display_id=None):
        info        = self.get_device_info_fast(ip, self._resolve_port(port), display_id)
        raw_queries = info.get("raw_queries") or {}
        lights       = raw_queries.get("lights")    or {}
        presets      = raw_queries.get("presets")   or {}
        channels_raw = raw_queries.get("channels")  or {}
        intellimix   = raw_queries.get("intellimix") or {}
        coverage     = raw_queries.get("coverage")  or {}
        lobes        = raw_queries.get("lobes")     or {}

        channel_map = {}
        for ch in channels_raw.get("channels") or []:
            number = ch.get("channel")
            if number is None:
                continue
            key = "automix" if int(number) == 9 else f"ch{int(number)}"
            channel_map[key] = {
                "name":      ch.get("name"),
                "gain_db":   ch.get("gain_db"),
                "gain_raw":  ch.get("gain_raw"),
                "muted":     ch.get("muted"),
                "level_rms": ch.get("rms"),
                "clip":      ch.get("clip"),
            }

        intellimix_map = {}
        for ch in intellimix.get("channels") or []:
            number = ch.get("channel")
            if number is None:
                continue
            key = f"ch{int(number)}"
            intellimix_map[key] = {
                "gain_db": channel_map.get(key, {}).get("gain_db"),
                "on":   str(ch.get("solo") or "").strip().upper() not in {"DISABLE", "OFF", "FALSE", "0"},
                "solo": ch.get("solo"),
                "gate": ch.get("gate"),
                "peq":  ch.get("peq"),
            }

        preset_names = {}
        for preset in presets.get("presets") or []:
            idx = preset.get("preset")
            if idx is not None:
                preset_names[int(idx)] = preset.get("name")

        # Normalise muted: TCP returns "ON"/"OFF" string; REST returns bool
        raw_muted = info.get("muted")
        if isinstance(raw_muted, bool):
            muted_norm = raw_muted
        elif isinstance(raw_muted, str):
            muted_norm = raw_muted.strip().upper() == "ON"
        else:
            muted_norm = None

        return {
            "reachable":      info.get("current_status") == "Online",
            "current_status": info.get("current_status"),
            "device_name":    info.get("device_name"),
            "model":          info.get("model"),
            "serial_number":  info.get("serial_number"),
            "firmware":       info.get("firmware"),
            "mac_address":    info.get("mac_address"),
            "device_id":      info.get("device_id"),
            "dante_name":     info.get("dante_name"),
            "ip_audio":       info.get("ip_audio"),
            "subnet_mask":    info.get("subnet_mask"),
            "gateway":        info.get("gateway"),
            "encryption":     info.get("encryption"),
            "muted":          muted_norm,
            "auto_coverage":  (
                info.get("auto_coverage")
                or channels_raw.get("auto_coverage")
                or coverage.get("auto_coverage")
            ),
            "transport":      info.get("transport"),  # "tcp" | "rest"
            "error":          info.get("error"),
            # Lights (TCP only — null when REST)
            "led_brightness":      lights.get("brightness"),
            "led_color_unmuted":   lights.get("color_unmuted"),
            "led_state_unmuted":   lights.get("state_unmuted"),
            "led_color_muted":     lights.get("color_muted"),
            "led_state_muted":     lights.get("state_muted"),
            "led_in_state":        lights.get("led_in_state"),
            # Presets (TCP only)
            "active_preset":  presets.get("active_preset"),
            "preset_names":   preset_names,
            # Channels (TCP only)
            "channels":       channel_map,
            "intellimix": {
                "bypass_imx":     intellimix.get("bypass_imx"),
                "bypass_all_eq":  intellimix.get("bypass_all_eq"),
                "eq_contour":     intellimix.get("eq_contour"),
                "num_active_mics": intellimix.get("num_active_mics"),
                "channels":       intellimix_map,
            },
            "coverage":       coverage,
            "lobes":          lobes.get("lobes"),
            "raw_queries":    raw_queries,
        }
