
# """
# Manual Platform Plugin: ShureP300Plugin
# """

# import socket
# import time
# import threading
# import re
# import ipaddress
# from typing import Optional, Callable, Dict, Any, List

# from .base import ManualPlatformPlugin

# # ── channel configuration matrix mapping ──────────────────────────────────────
# CHANNELS: Dict[str, str] = {
#     "01": "Dante In 1",
#     "02": "Dante In 2",
#     "03": "Dante In 3",
#     "04": "Dante In 4",
#     "05": "Dante Out 1",
#     "06": "Dante Out 2",
#     "07": "Analog In",
#     "08": "Analog Out",
#     "09": "USB In",
#     "10": "USB Out",
# }


# class ANIUSBMatrix:
#     """Pure-Python standard TCP socket connection manager for Shure Audio API."""
#     BUF  = 4096
#     PORT = 2202

#     def __init__(self, host: str, password: str = "", timeout: float = 5.0):
#         self.host     = host
#         self.port     = self.PORT
#         self.password = password
#         self.timeout  = timeout
#         self._sock: Optional[socket.socket] = None
#         self._lock  = threading.Lock()

#     def connect(self):
#         if self._sock:
#             return
#         try:
#             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             s.settimeout(self.timeout)
#             s.connect((self.host, self.port))
#             self._sock = s
#             if self.password:
#                 self._xfer(f"< SET DEVICE_PASSWORD {self.password} >")
#         except socket.timeout:
#             self._sock = None
#             raise Exception(f"Connection timeout tracking to {self.host}:{self.port}")
#         except OSError as e:
#             self._sock = None
#             raise Exception(f"Cannot initialize pipeline link on {self.host}:{self.port} - {e}")

#     def disconnect(self):
#         if self._sock:
#             try:    self._sock.close()
#             except: pass
#             self._sock = None

#     def _ensure(self):
#         if not self._sock:
#             self.connect()

#     def _send(self, c: str):
#         try:
#             self._sock.sendall((c.strip() + "\r\n").encode("ascii"))
#         except OSError as e:
#             self._sock = None
#             raise Exception(f"Socket transmission dropped: {e}")

#     def _recv(self) -> str:
#         buf = b""
#         try:
#             while b">" not in buf:
#                 chunk = self._sock.recv(self.BUF)
#                 if not chunk:
#                     raise Exception("Remote Shure matrix hardware severed link.")
#                 buf += chunk
#         except OSError as e:
#             self._sock = None
#             raise Exception(f"Socket incoming parse error: {e}")
#         return buf.decode("ascii", errors="ignore").strip()

#     def _xfer(self, c: str) -> str:
#         self._send(c); return self._recv()

#     def cmd(self, command: str) -> str:
#         with self._lock:
#             for attempt in range(2):
#                 try:
#                     self._ensure()
#                     self._send(command)
#                     resp = self._recv()
#                     if "REP ERR" in resp.upper():
#                         raise Exception(f"Hardware rejected raw string evaluation → {command.strip()!r}")
#                     return resp
#                 except Exception:
#                     self._sock = None
#                     if attempt == 0: time.sleep(0.25)
#                     else: raise

#     @staticmethod
#     def _val(resp: str, keyword: str) -> str:
#         idx = resp.upper().find(keyword.upper())
#         if idx < 0:
#             raise Exception(f"Keyword target '{keyword}' not found inside: {resp!r}")
#         v = resp[idx + len(keyword):].strip().rstrip(">").strip()
#         return v.strip("{").strip("}").strip()

#     @staticmethod
#     def _db2raw(db: float) -> str:
#         """Converts float decibel readings directly into 4-digit tenth-dB formats."""
#         db  = max(-100.0, min(14.0, db))
#         raw = max(0, min(1140, int(round((db + 100.0) * 10))))
#         return f"{raw:04d}"


# class ShureP300Plugin(ManualPlatformPlugin):
#     """Shure P300/ANIUSB platform interface adapter class."""

#     name = "shure_p300"
#     display_name = "Shure P300 / ANIUSB"
#     description = "Shure P300 and ANIUSB-MATRIX matrix mixer integrations"
#     supports_display_id = False
#     supports_port = True
#     default_port = 2202
#     SUPPORTED_MODELS = ["P300", "ANIUSB-MATRIX"]

#     COMMANDS = {
#         "global_mute": {"description": "Mute or unmute the automix output", "params": [{"name": "state", "type": "str"}]},
#         "mute_on": {"description": "Mute the automix output", "params": []},
#         "mute_off": {"description": "Unmute the automix output", "params": []},
#         "set_channel_mute": {"description": "Set a channel mute state", "params": [{"name": "channel", "type": "int"}, {"name": "state", "type": "str"}]},
#         "set_channel_gain_db": {"description": "Set channel gain in dB", "params": [{"name": "channel", "type": "int"}, {"name": "db", "type": "float"}]},
#         "inc_channel_gain": {"description": "Increase channel gain", "params": [{"name": "channel", "type": "int"}, {"name": "delta_db", "type": "float"}]},
#         "dec_channel_gain": {"description": "Decrease channel gain", "params": [{"name": "channel", "type": "int"}, {"name": "delta_db", "type": "float"}]},
#         "adjust_channel_gain_db": {"description": "Adjust channel gain by dB", "params": [{"name": "channel", "type": "int"}, {"name": "delta_db", "type": "float"}]},
#         "set_channel_name": {"description": "Set channel name", "params": [{"name": "channel", "type": "int"}, {"name": "name", "type": "str"}]},
#         "rename_channel": {"description": "Rename channel", "params": [{"name": "channel", "type": "int"}, {"name": "name", "type": "str"}]},
#         "recall_preset": {"description": "Recall a preset", "params": [{"name": "preset", "type": "int"}]},
#         "set_usb_device_type": {"description": "Set USB device type", "params": [{"name": "device_type", "type": "str"}]},
#         "set_led_brightness": {"description": "Set LED ring brightness", "params": [{"name": "level", "type": "int"}]},
#         "set_dhcp": {"description": "Enable or disable DHCP on the control or audio network", "params": [{"name": "network", "type": "str"}, {"name": "enabled", "type": "bool"}]},
#         "set_ip_address": {"description": "Set a static IP address on the control or audio network", "params": [{"name": "network", "type": "str"}, {"name": "ip", "type": "str"}, {"name": "subnet", "type": "str"}, {"name": "gateway", "type": "str"}]},
#         "raw_command": {"description": "Send a raw TCP command string", "params": [{"name": "command", "type": "str"}]},
#         "reboot": {"description": "Reboot the device", "params": []},
#     }
#     QUERY_COMMANDS = {}

#     def _send_ok(self, ip, cmd_str, port=2202):
#         password = self.config.get("password", "")
#         driver = ANIUSBMatrix(host=ip, password=password, timeout=self.timeout)
#         try:
#             driver.connect()
#             return driver.cmd(f"< {cmd_str} >")
#         finally:
#             try: driver.disconnect()
#             except Exception: pass

#     def _send_raw(self, ip, raw_command, port=2202):
#         password = self.config.get("password", "")
#         driver = ANIUSBMatrix(host=ip, password=password, timeout=self.timeout)
#         try:
#             driver.connect()
#             cmd = str(raw_command or "").strip()
#             if not cmd:
#                 raise ValueError("raw_command requires params.command")
#             if not cmd.startswith("<"):
#                 cmd = f"< {cmd} >"
#             return driver.cmd(cmd)
#         finally:
#             try: driver.disconnect()
#             except Exception: pass

#     @staticmethod
#     def _channel_id(value):
#         channel = str(value or "").strip()
#         if not channel:
#             raise ValueError("channel is required")
#         if channel.isdigit():
#             return channel.zfill(2)
#         return channel

#     @staticmethod
#     def _gain_step_tenths(delta_db):
#         try:
#             return max(1, int(round(abs(float(delta_db)) * 10)))
#         except Exception:
#             return 10

#     @staticmethod
#     def _normalize_usb_device_type(device_type):
#         value = str(device_type or "").strip().upper()
#         aliases = {
#             "AUDIO_PROCESSOR": "ECHO_CANCELING_SPEAKERPHONE",
#             "ECHO_CANCELLING_SPEAKERPHONE": "ECHO_CANCELING_SPEAKERPHONE",
#             "ECHO-CANCELING_SPEAKERPHONE": "ECHO_CANCELING_SPEAKERPHONE",
#             "ECHO_CANCELING_SPEAKERPHONE": "ECHO_CANCELING_SPEAKERPHONE",
#         }
#         return aliases.get(value, value)

#     @staticmethod
#     def _normalize_mute_state(state):
#         value = str(state or "").strip().upper()
#         return "ON" if value in {"ON", "MUTE", "TRUE", "1", "YES"} else "OFF"

#     @staticmethod
#     def _is_valid_ip(value):
#         try:
#             ipaddress.ip_address(str(value).strip())
#             return True
#         except Exception:
#             return False

#     def get_device_info(self, ip, port=2202, display_id=None):
#         password = self.config.get("password", "")
#         device_port = port if port else self.default_port
#         driver = ANIUSBMatrix(host=ip, password=password, timeout=self.timeout)
#         try:
#             driver.connect()
#             dev_id   = driver._val(driver.cmd("< GET DEVICE_ID >"), "DEVICE_ID").strip()
#             firmware = driver._val(driver.cmd("< GET FW_VER >"),    "FW_VER").strip()
#             try:    model = driver._val(driver.cmd("< GET MODEL >"), "MODEL").strip()
#             except: model = "P300"
#             try:    serial = driver._val(driver.cmd("< GET SERIAL_NUM >"), "SERIAL_NUM").strip()
#             except: serial = dev_id

#             return {
#                 "ip_address": ip, "port": device_port, "display_id": display_id,
#                 "make": "Shure", "device_name": dev_id, "model": model,
#                 "serial_number": serial, "firmware": firmware,
#                 "device_type": "Audio Processor", "current_status": "Online"
#             }
#         except Exception as e:
#             return {
#                 "ip_address": ip, "port": device_port, "display_id": display_id,
#                 "make": "Shure", "device_type": "Audio Processor",
#                 "current_status": "Offline", "error": str(e)
#             }
#         finally:
#             try: driver.disconnect()
#             except Exception: pass

#     def send_command(self, ip, port, display_id, command):
#         """Processes dynamic commands from both manual wrappers or raw string keys."""
#         action = None
#         params = {}

#         # 1. Parse payload schemas without breaking common frontend behaviors
#         if isinstance(command, dict):
#             action = command.get("action") or command.get("command")
#             params = command.get("params") or {}
#             if isinstance(params, dict) and not action:
#                 action = params.get("command") or params.get("action")
#         elif isinstance(command, str):
#             action = command

#         action = str(action or "").strip().lower()
#         device_port = port if port else self.default_port

#         try:
#             if action == "raw_command":
#                 raw = params.get("command") if isinstance(params, dict) else None
#                 res = self._send_raw(ip, raw, device_port)
#                 return {"success": True, "result": res}

#             # 2. COMPATIBILITY LAYER: Intercept common frontend generic string actions
#             # Handles strings like "mute_on", "mute_off", "mute_on_01", "mute_off_05"
#             if action in {"global_mute", "mute_on", "mute_off", "mute"} or action.startswith("mute_on_") or action.startswith("mute_off_"):
#                 state = "ON" if action in {"mute_on", "global_mute", "mute"} or action.startswith("mute_on_") else "OFF"
                
#                 # Check if a specific channel index suffix exists (e.g., "mute_on_02")
#                 match = re.search(r'_(0[1-9]|10)$', action)
                
#                 if match:
#                     channel = match.group(1)
#                     res = self._send_ok(ip, f"SET {channel} AUDIO_MUTE {state}", device_port)
#                     return {"success": True, "result": res}
#                 elif isinstance(params, dict) and params.get("channel"):
#                     channel = self._channel_id(params.get("channel"))
#                     res = self._send_ok(ip, f"SET {channel} AUDIO_MUTE {state}", device_port)
#                     return {"success": True, "result": res}
#                 else:
#                     # Default fallback: Route to Master Matrix Automix Logic Line
#                     res = self._send_ok(ip, f"SET AUTOMIX_OUT_MUTE {state}", device_port)
#                     return {"success": True, "result": res}

#             # 3. Native Explicit Command Parsers
#             if action == "set_channel_mute":
#                 channel = self._channel_id(params.get("channel"))
#                 state = self._normalize_mute_state(params.get("state"))
#                 res = self._send_ok(ip, f"SET {channel} AUDIO_MUTE {state}", device_port)
#                 return {"success": True, "result": res}

#             elif action == "set_channel_gain_db":
#                 channel = self._channel_id(params.get("channel"))
#                 db_val = float(params.get("db", 0.0))
#                 raw_str = ANIUSBMatrix._db2raw(db_val)
#                 res = self._send_ok(ip, f"SET {channel} AUDIO_GAIN_HI_RES {raw_str}", device_port)
#                 return {"success": True, "result": res}

#             elif action == "global_mute":
#                 shure_state = self._normalize_mute_state(params.get("state"))
#                 res = self._send_ok(ip, f"SET AUTOMIX_OUT_MUTE {shure_state}", device_port)
#                 return {"success": True, "result": res}

#             elif action in {"inc_channel_gain", "dec_channel_gain", "adjust_channel_gain_db"}:
#                 channel = self._channel_id(params.get("channel"))
#                 delta_db = float(params.get("delta_db", 1.0))
#                 direction = "INC" if action != "dec_channel_gain" and delta_db >= 0 else "DEC"
#                 tenths = self._gain_step_tenths(delta_db)
#                 res = self._send_ok(ip, f"SET {channel} AUDIO_GAIN_HI_RES {direction} {tenths}", device_port)
#                 return {"success": True, "result": res}

#             elif action in {"set_channel_name", "rename_channel"}:
#                 channel = self._channel_id(params.get("channel"))
#                 name = str(params.get("name", "")).strip()[:31]
#                 if not name:
#                     raise ValueError("name is required")
#                 res = self._send_ok(ip, f"SET {channel} CHAN_NAME {{{name}}}", device_port)
#                 return {"success": True, "result": res}

#             elif action == "recall_preset":
#                 preset = int(params.get("preset", 1))
#                 res = self._send_ok(ip, f"SET PRESET {preset:02d}", device_port)
#                 return {"success": True, "result": res}

#             elif action == "set_usb_device_type":
#                 dtype = self._normalize_usb_device_type(params.get("device_type"))
#                 res = self._send_ok(ip, f"SET USB_DEVICE_TYPE {dtype}", device_port)
#                 return {"success": True, "result": res}

#             elif action == "set_led_brightness":
#                 level = max(0, min(8, int(params.get("level", 3))))
#                 res = self._send_ok(ip, f"SET LED_BRIGHTNESS {level}", device_port)
#                 return {"success": True, "result": res}

#             elif action == "set_dhcp":
#                 network = str(params.get("network", "control")).strip().lower()
#                 enabled = bool(params.get("enabled", True))
#                 state = "ON" if enabled else "OFF"
#                 if network == "audio":
#                     res = self._send_ok(ip, f"SET DHCP_NET_AUDIO_PRIMARY {state}", device_port)
#                 else:
#                     res = self._send_ok(ip, f"SET DHCP_NET_DEVICE {state}", device_port)
#                 return {"success": True, "result": res}

#             elif action == "set_ip_address":
#                 network = str(params.get("network", "control")).strip().lower()
#                 ip_addr = str(params.get("ip") or params.get("ip_address") or "").strip()
#                 subnet = str(params.get("subnet") or params.get("subnet_mask") or "").strip()
#                 gateway = str(params.get("gateway") or params.get("default_gateway") or "").strip()
#                 if not self._is_valid_ip(ip_addr):
#                     raise ValueError(f"Invalid IP address: {ip_addr!r}")
#                 if network == "audio":
#                     self._send_ok(ip, "SET DHCP_NET_AUDIO_PRIMARY OFF", device_port)
#                     res = self._send_ok(ip, f"SET IP_ADDR_NET_AUDIO_PRIMARY {ip_addr}", device_port)
#                     if subnet and self._is_valid_ip(subnet):
#                         self._send_ok(ip, f"SET IP_SUBNET_NET_AUDIO_PRIMARY {subnet}", device_port)
#                     if gateway and self._is_valid_ip(gateway):
#                         self._send_ok(ip, f"SET IP_GATEWAY_NET_AUDIO_PRIMARY {gateway}", device_port)
#                 else:
#                     self._send_ok(ip, "SET DHCP_NET_DEVICE OFF", device_port)
#                     res = self._send_ok(ip, f"SET IP_ADDR_NET_DEVICE {ip_addr}", device_port)
#                     if subnet and self._is_valid_ip(subnet):
#                         self._send_ok(ip, f"SET IP_SUBNET_NET_DEVICE {subnet}", device_port)
#                     if gateway and self._is_valid_ip(gateway):
#                         self._send_ok(ip, f"SET IP_GATEWAY_NET_DEVICE {gateway}", device_port)
#                 return {"success": True, "result": res}

#             elif action == "reboot":
#                 res = self._send_ok(ip, "SET REBOOT", device_port)
#                 return {"success": True, "result": res}

#             return {"success": False, "error": f"Unknown plugin control hook: {action}"}

#         except Exception as e:
#             return {"success": False, "error": str(e)}

#     def query_status(self, ip, port=2202, display_id=None):
#         info = self.get_device_info(ip, port, display_id)
#         return {
#             "reachable": info.get("current_status") == "Online",
#             "device_name": info.get("device_name"),
#             "model": info.get("model"),
#             "serial_number": info.get("serial_number"),
#             "firmware": info.get("firmware"),
#             "current_status": info.get("current_status"),
#             "error": info.get("error", None)
#         }


"""
Manual Platform Plugin: Shure P300 IntelliMix DSP
TCP port 2202 — Shure command-string protocol
"""

import json
import re
import socket
import time
import urllib3
from .base import ManualPlatformPlugin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PORT = 2202
BUFFER = 8192

P300_CHANNELS = {
    1: "Dante Input 1", 2: "Dante Input 2", 3: "Dante Input 3", 4: "Dante Input 4",
    5: "Dante Input 5", 6: "Dante Input 6", 7: "Dante Input 7", 8: "Dante Input 8",
    9: "Dante Input 9", 10: "Dante Input 10", 11: "Analog - From Codec", 12: "Analog Input 2",
    13: "USB Input", 14: "Mobile Input",
    15: "Dante Output 1", 16: "Dante Output 2", 17: "Analog - To Codec", 18: "Analog - To Speaker",
    19: "USB Output", 20: "Mobile Output",
    21: "Automixer", 22: "AEC Reference",
    23: "Dante Output 3", 24: "Dante Output 4", 25: "Dante Output 5", 26: "Dante Output 6",
    27: "Dante Output 7", 28: "Dante Output 8",
}

INPUT_CHS = list(range(1, 15))
OUTPUT_CHS = [15, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28]
DANTE_IN_CHS = list(range(1, 9))
DANTE_OUT_CHS = [15, 16, 23, 24, 25, 26, 27, 28]
ANALOG_OUT_CHS = [17, 18]
MIC_CHS = list(range(1, 9))  # channels with AEC/NR/AGC processing


class ShureP300Plugin(ManualPlatformPlugin):
    name = "shure_p300"
    display_name = "Shure P300"
    description = "Shure P300 IntelliMix DSP (TCP port 2202)"
    supports_display_id = False
    supports_port = False
    default_port = PORT
    SUPPORTED_MODELS = ["P300"]

    COMMANDS = {
        "device_mute_on":      {"description": "Mute device audio", "params": []},
        "device_mute_off":     {"description": "Unmute device audio", "params": []},
        "device_mute_toggle":  {"description": "Toggle device audio mute", "params": []},
        "channel_mute_on":     {"description": "Mute channel", "params": [{"name": "channel", "type": "int"}]},
        "channel_mute_off":    {"description": "Unmute channel", "params": [{"name": "channel", "type": "int"}]},
        "channel_mute_toggle": {"description": "Toggle channel mute", "params": [{"name": "channel", "type": "int"}]},
        "channel_gain_set":    {"description": "Set channel gain (0-1400)", "params": [{"name": "channel", "type": "int"}, {"name": "gain", "type": "int"}]},
        "channel_gain_inc":    {"description": "Increase gain (decrement value)", "params": [{"name": "channel", "type": "int"}, {"name": "amount", "type": "int"}]},
        "channel_gain_dec":    {"description": "Decrease gain (increment value)", "params": [{"name": "channel", "type": "int"}, {"name": "amount", "type": "int"}]},
        "aec_on":              {"description": "Enable AEC", "params": [{"name": "channel", "type": "int"}]},
        "aec_off":             {"description": "Disable AEC", "params": [{"name": "channel", "type": "int"}]},
        "aec_toggle":          {"description": "Toggle AEC", "params": [{"name": "channel", "type": "int"}]},
        "noise_red_on":        {"description": "Enable noise reduction", "params": [{"name": "channel", "type": "int"}]},
        "noise_red_off":       {"description": "Disable noise reduction", "params": [{"name": "channel", "type": "int"}]},
        "agc_on":              {"description": "Enable AGC", "params": [{"name": "channel", "type": "int"}]},
        "agc_off":             {"description": "Disable AGC", "params": [{"name": "channel", "type": "int"}]},
        "agc_toggle":          {"description": "Toggle AGC", "params": [{"name": "channel", "type": "int"}]},
        "peq_on":              {"description": "Enable PEQ filter", "params": [{"name": "block", "type": "int"}, {"name": "filter", "type": "int"}]},
        "peq_off":             {"description": "Disable PEQ filter", "params": [{"name": "block", "type": "int"}, {"name": "filter", "type": "int"}]},
        "preset_load":         {"description": "Load preset", "params": [{"name": "preset", "type": "int"}]},
        "matrix_route_on":     {"description": "Enable matrix route", "params": [{"name": "input", "type": "int"}, {"name": "output", "type": "int"}]},
        "matrix_route_off":    {"description": "Disable matrix route", "params": [{"name": "input", "type": "int"}, {"name": "output", "type": "int"}]},
        "matrix_gain_set":     {"description": "Set matrix crosspoint gain", "params": [{"name": "input", "type": "int"}, {"name": "output", "type": "int"}, {"name": "gain", "type": "int"}]},
        "automixer_mode_set":  {"description": "Set automixer mode MANUAL|GATING|GAINSHARE", "params": [{"name": "mode", "type": "str"}]},
        "compressor_on":       {"description": "Enable compressor", "params": []},
        "compressor_off":      {"description": "Disable compressor", "params": []},
        "delay_set":           {"description": "Set delay ms", "params": [{"name": "channel", "type": "int"}, {"name": "ms", "type": "int"}]},
        "flash_on":            {"description": "Flash identify", "params": []},
        "flash_off":           {"description": "Flash off", "params": []},
        "reboot":              {"description": "Reboot device", "params": []},
        "restore_defaults":    {"description": "Factory restore", "params": []},
        "raw":                 {"description": "Raw TCP command", "params": [{"name": "command", "type": "str"}]},
        "mute_sync_on":        {"description": "Enable mute sync", "params": []},
        "mute_sync_off":       {"description": "Disable mute sync", "params": []},
        "usb_device_type_set": {"description": "Set USB type SPEAKERPHONE|ECHO_CANCELLER", "params": [{"name": "type", "type": "str"}]},
        "meter_mode_input_set":  {"description": "Set input meter mode PRE_FADER|POST_FADER", "params": [{"name": "mode", "type": "str"}]},
        "meter_mode_output_set": {"description": "Set output meter mode PRE_FADER|POST_FADER", "params": [{"name": "mode", "type": "str"}]},
        "output_type_set":     {"description": "Set analog output type LINE|AUX|MIC", "params": [{"name": "channel", "type": "int"}, {"name": "type", "type": "str"}]},
        "automixer_priority_on":  {"description": "Enable automixer priority", "params": [{"name": "channel", "type": "int"}]},
        "automixer_priority_off": {"description": "Disable automixer priority", "params": [{"name": "channel", "type": "int"}]},
        "automixer_always_on_on":  {"description": "Enable automixer always-on", "params": [{"name": "channel", "type": "int"}]},
        "automixer_always_on_off": {"description": "Disable automixer always-on", "params": [{"name": "channel", "type": "int"}]},
        "automixer_off_att_set":  {"description": "Set automixer off attenuation (0-107)", "params": [{"name": "value", "type": "int"}]},
        "automixer_sensitivity_set": {"description": "Set automixer sensitivity", "params": [{"name": "value", "type": "int"}]},
        "automixer_last_mic_hold_set": {"description": "Set last mic hold time (ms)", "params": [{"name": "ms", "type": "int"}]},
        "automixer_max_mics_set": {"description": "Set max open microphones", "params": [{"name": "count", "type": "int"}]},
        "compressor_threshold_set": {"description": "Set compressor threshold (000-600)", "params": [{"name": "value", "type": "int"}]},
        "compressor_ratio_set":    {"description": "Set compressor ratio (0010-1000)", "params": [{"name": "value", "type": "int"}]},
        "gate_inhibit_on":    {"description": "Enable gate inhibit (ch 22)", "params": []},
        "gate_inhibit_off":   {"description": "Disable gate inhibit (ch 22)", "params": []},
        "directout_point_set": {"description": "Set direct out tap point (0-3)", "params": [{"name": "channel", "type": "int"}, {"name": "point", "type": "int"}]},
        "aec_reference_set":  {"description": "Set AEC reference source", "params": [{"name": "channel", "type": "int"}, {"name": "ref", "type": "str"}]},
        "aec_nlp_set":        {"description": "Set AEC NLP level LOW|MEDIUM|HIGH", "params": [{"name": "channel", "type": "int"}, {"name": "level", "type": "str"}]},
        "noise_red_level_set": {"description": "Set noise reduction level LOW|MEDIUM|HIGH", "params": [{"name": "channel", "type": "int"}, {"name": "level", "type": "str"}]},
        "log_export":          {"description": "Trigger log export", "params": []},
    }

    # ── TCP helpers ──────────────────────────────────────────

    # def _tcp_send(self, ip, command, timeout=5):
    #     sock = None
    #     try:
    #         sock = socket.create_connection((ip, PORT), timeout=3)
    #         self._flush(sock)
    #         # FIX 1: Always terminate with \r\n so the P300 processes the command
    #         if not command.endswith("\r\n"):
    #             command += "\r\n"
    #         sock.sendall(command.encode("ascii"))
    #         data = b""
    #         sock.settimeout(timeout)
    #         first = True
    #         while True:
    #             try:
    #                 chunk = sock.recv(BUFFER)
    #                 if not chunk:
    #                     break
    #                 data += chunk
    #                 if first:
    #                     sock.settimeout(0.2)
    #                     first = False
    #             except socket.timeout:
    #                 break
    #         return data.decode("ascii", errors="ignore")
    #     except Exception:
    #         return ""
    #     finally:
    #         if sock:
    #             try:
    #                 sock.close()
    #             except Exception:
    #                 pass





    # REMOVE the existing _tcp_send method entirely.
# ADD this instead:

    def _tcp_session(self, ip: str, commands: list, timeout: float = 10) -> str:
        """One TCP connection, all commands sent in one burst, all responses read."""
        sock = None
        try:
            sock = socket.create_connection((ip, PORT), timeout=4)
            # flush banner
            sock.settimeout(0.3)
            try:
                while True: sock.recv(BUFFER)
            except socket.timeout:
                pass
            # send all at once
            payload = ""
            for cmd in commands:
                cmd = cmd.strip()
                if not cmd.endswith("\r\n"): cmd += "\r\n"
                payload += cmd
            sock.sendall(payload.encode("ascii"))
            # read until quiet
            data = b""
            sock.settimeout(timeout)
            first = True
            while True:
                try:
                    chunk = sock.recv(BUFFER)
                    if not chunk: break
                    data += chunk
                    if first:
                        sock.settimeout(0.5)
                        first = False
                except socket.timeout:
                    break
            return data.decode("ascii", errors="ignore")
        except Exception:
            return ""
        finally:
            if sock:
                try: sock.close()
                except: pass

    def _tcp_send(self, ip, command, timeout=5):
            """Single-command convenience wrapper around _tcp_session."""
            return self._tcp_session(ip, [command], timeout=timeout)

    def _flush(self, sock):
            sock.settimeout(0.1)
            try:
                while True:
                    sock.recv(BUFFER)
            except Exception:
                pass

    def _get_value(self, raw, keyword):
            m = re.search(rf"REP\s+(?:\d+\s+)?{re.escape(keyword)}\s+{{?(.*?)}}?\s*(?:>|$)", raw, re.DOTALL)
            if m:
                return m.group(1).strip()
            m = re.search(rf"REP\s+(?:\d+\s+)?{re.escape(keyword)}\s+(\S+)", raw)
            if m:
                return m.group(1).strip()
            return ""

    def _send_ok(self, ip, command):
        raw = self._tcp_send(ip, command)
        return "REP ERR" not in raw and bool(raw)

    def _probe(self, ip):
      raw = self._tcp_session(ip, ["< GET MODEL >"], timeout=10)
      return "P300" in raw or bool(self._get_value(raw, "MODEL"))
    # ── get_device_info ──────────────────────────────────────

    def get_device_info(self, ip, port=PORT, display_id=None):
        if not self._probe(ip):
            return {"ip_address": ip, "port": PORT, "display_id": display_id,
                    "make": "Shure", "device_type": "P300",
                    "current_status": "Offline", "error": "No P300 response on TCP 2202"}
        try:
            raw_all = self._tcp_send(ip, "< GET 00 ALL >", timeout=8)
            model   = self._get_value(raw_all, "MODEL") or self._tcp_send(ip, "< GET MODEL >", 3)
            serial  = self._get_value(raw_all, "SERIAL_NUM")
            fw      = self._get_value(raw_all, "FW_VER")
            dev_id  = self._get_value(raw_all, "DEVICE_ID")
            name    = self._get_value(raw_all, "NA_DEVICE_NAME")
            mac     = self._get_value(raw_all, "CONTROL_MAC_ADDR")
            ip_addr = self._get_value(raw_all, "IP_ADDR_NET_AUDIO_PRIMARY")
            subnet  = self._get_value(raw_all, "IP_SUBNET_NET_AUDIO_PRIMARY")
            gateway = self._get_value(raw_all, "IP_GATEWAY_NET_AUDIO_PRIMARY")
            mute    = self._get_value(raw_all, "DEVICE_AUDIO_MUTE")
            preset  = self._get_value(raw_all, "PRESET")
            encrypt = self._get_value(raw_all, "ENCRYPTION")
            mutesync = self._get_value(raw_all, "MUTESYNC")
            usb_conn = self._get_value(raw_all, "USB_CONNECT")
            onhook  = self._get_value(raw_all, "ONHOOK_STATE")
            led_br  = self._get_value(raw_all, "LED_BRIGHTNESS")
            in_meter_mode = self._get_value(raw_all, "INPUT_METER_MODE")
            out_meter_mode = self._get_value(raw_all, "OUTPUT_METER_MODE")
            automxr_mode = self._get_value(raw_all, "AUTOMXR_MODE")
            gate_inhibit = self._get_value(raw_all, "GATE_INHIBIT")

            return {
                "ip_address": ip, "port": PORT, "display_id": display_id,
                "make": "Shure", "device_type": "P300",
                "model": model or "P300",
                "serial_number": serial,
                "firmware_version": fw,
                "device_id": dev_id,
                "device_name": name,
                "mac_address": mac,
                "ip": ip_addr,
                "subnet_mask": subnet,
                "gateway": gateway,
                "muted": mute == "ON",
                "active_preset": preset,
                "encryption": encrypt == "ON",
                "mute_sync": mutesync == "ON",
                "usb_connected": usb_conn == "ON",
                "onhook_state": onhook,
                "led_brightness": led_br,
                "input_meter_mode": in_meter_mode,
                "output_meter_mode": out_meter_mode,
                "automixer_mode": automxr_mode,
                "gate_inhibit": gate_inhibit,
                "current_status": "Online",
            }
        except Exception as e:
            return {"ip_address": ip, "port": PORT, "display_id": display_id,
                    "make": "Shure", "device_type": "P300",
                    "current_status": "Offline", "error": str(e)}

    # ── query_status ─────────────────────────────────────────

    def _query_channel_param(self, ip, param):
        raw = self._tcp_send(ip, f"< GET 00 {param} >", timeout=4)
        results = {}
        if raw:
            for ch, val in re.findall(rf"REP\s+(\d+)\s+{re.escape(param)}\s+(\S+)", raw):
                results[str(int(ch))] = val
        return results

    # def _fetch_channels(self, ip):
    #     channels = {}
    #     mute_map  = self._query_channel_param(ip, "AUDIO_MUTE")
    #     gain_map  = self._query_channel_param(ip, "AUDIO_GAIN_HI_RES")
    #     aec_map   = self._query_channel_param(ip, "AEC")
    #     nr_map    = self._query_channel_param(ip, "NOISE_RED")
    #     agc_map   = self._query_channel_param(ip, "AGC")
    #     for ch in set(list(mute_map) + list(gain_map) + list(aec_map) + list(nr_map) + list(agc_map)):
    #         entry = {}
    #         if ch in mute_map:  entry["mute"] = mute_map[ch] == "ON"
    #         if ch in gain_map:  entry["gain"] = int(gain_map[ch])
    #         if ch in aec_map:   entry["aec"] = aec_map[ch] == "ON"
    #         if ch in nr_map:    entry["noise_red"] = nr_map[ch] == "ON"
    #         if ch in agc_map:   entry["agc"] = agc_map[ch] == "ON"
    #         channels[ch] = entry
    #     return channels
     

    def _fetch_channels(self, ip):
        raw = self._tcp_session(ip, [
            "< GET 00 AUDIO_MUTE >",
            "< GET 00 AUDIO_GAIN_HI_RES >",
            "< GET 00 AEC >",
            "< GET 00 NOISE_RED >",
            "< GET 00 AGC >",
        ], timeout=6)
        return self._parse_channels_batch(raw)
    
    def _parse_network(self, raw):
        return {
            "ip_address": self._get_value(raw, "IP_ADDR_NET_AUDIO_PRIMARY"),
            "subnet_mask": self._get_value(raw, "IP_SUBNET_NET_AUDIO_PRIMARY"),
            "gateway": self._get_value(raw, "IP_GATEWAY_NET_AUDIO_PRIMARY"),
            "mac_address": self._get_value(raw, "CONTROL_MAC_ADDR"),
        }

    def _parse_automixer(self, raw):
        result = {}
        mode = self._get_value(raw, "AUTOMXR_MODE")
        if mode:
            result["mode"] = mode
        for key, desc in [("AUTOMXR_LMLO", "last_mic_lockout"),
                          ("AUTOMXR_HOLDTIME", "hold_time"),
                          ("AUTOMXR_OFF_ATT", "off_attenuation"),
                          ("AUTOMXR_MAX_NOM", "max_mics"),
                          ("AUTOMXR_MUTE", "mute"),
                          ("AUTOMXR_GATE_OPT", "gate_option"),
                          ("AUTOMXR_GATE_SEN", "gate_sensitivity")]:
            v = self._get_value(raw, key)
            if v:
                result[desc] = v
        m = re.findall(r"REP\s+21\s+MATRIX_MXR_GAIN\s+(\d+)\s+(\d+)", raw)
        if m:
            result["matrix_gain"] = {out: int(g) for out, g in m}
        return result

    def _parse_matrix_routes(self, raw):
        routes = {}
        for inp, out, state in re.findall(r"REP\s+(\d+)\s+MATRIX_MXR_ROUTE\s+(\d+)\s+(ON|OFF)", raw):
            routes.setdefault(str(int(inp)), {})[str(int(out))] = state == "ON"
        return routes

    def _parse_matrix_gains(self, raw):
        gains = {}
        for inp, out, g in re.findall(r"REP\s+(\d+)\s+MATRIX_MXR_GAIN\s+(\d+)\s+(\d+)", raw):
            gains.setdefault(str(int(inp)), {})[str(int(out))] = int(g)
        return gains

    def _parse_peq(self, raw):
        peq = {}
        for ch, filt, state in re.findall(r"REP\s+(\d+)\s+PEQ\s+(\d+)\s+(ON|OFF)", raw):
            peq.setdefault(str(int(ch)), {})[str(int(filt))] = state == "ON"
        return peq

    def _parse_output_types(self, raw):
        types = {}
        for ch, val in re.findall(r"REP\s+(\d+)\s+AUDIO_OUT_LVL_SWITCH\s+(\S+)", raw):
            types[str(int(ch))] = val
        for ch, val in re.findall(r"REP\s+(\d+)\s+AUDIO_IN_LVL_SWITCH\s+(\S+)", raw):
            types.setdefault(str(int(ch)), val)
        return types

    def _parse_direct_out(self, raw):
        points = {}
        for ch, pt in re.findall(r"REP\s+(\d+)\s+DIRECTOUT_POINT\s+(\d+)", raw):
            points[str(int(ch))] = int(pt)
        return points

    def query_status(self, ip, port=PORT, display_id=None):
        try:
            raw = self._tcp_send(ip, "< GET 00 ALL >", timeout=10)
            # ── ADD THIS: if full query fails, try lightweight probe ──
            if not raw:
                if self._probe(ip):
                    # Device responds to basic commands but not GET 00 ALL
                    # Return minimal online status instead of falsely reporting offline
                    return {"reachable": True, "error": "Partial response only"}
                return {"reachable": False, "error": "No response"}
            if not raw:
                return {"reachable": False, "error": "No response"}
            model  = self._get_value(raw, "MODEL")
            fw     = self._get_value(raw, "FW_VER")
            mute   = self._get_value(raw, "DEVICE_AUDIO_MUTE")
            preset = self._get_value(raw, "PRESET")
            encrypt = self._get_value(raw, "ENCRYPTION")
            mutesync = self._get_value(raw, "MUTESYNC")
            usb_conn = self._get_value(raw, "USB_CONNECT")
            onhook  = self._get_value(raw, "ONHOOK_STATE")
            onhook_enable = self._get_value(raw, "ONHOOK_ENABLE")
            led_br  = self._get_value(raw, "LED_BRIGHTNESS")
            in_meter_mode = self._get_value(raw, "INPUT_METER_MODE")
            out_meter_mode = self._get_value(raw, "OUTPUT_METER_MODE")
            flash = self._get_value(raw, "FLASH")
            compressor = self._get_value(raw, "COMPRESSOR")
            gate_inhibit = self._get_value(raw, "GATE_INHIBIT")
            usb_type = self._get_value(raw, "USB_DEVICE_TYPE")

            # Fallbacks for matrix routes
            if "MATRIX_MXR_ROUTE" not in raw:
                res = self._tcp_send(ip, "< GET 00 MATRIX_MXR_ROUTE 00 >", timeout=2)
                if res: raw += res
            if "MATRIX_MXR_GAIN" not in raw:
                res = self._tcp_send(ip, "< GET 00 MATRIX_MXR_GAIN 00 >", timeout=2)
                if res: raw += res

            # Use _fetch_channels for reliable channel data — individual batched
            # TCP queries avoid the truncation risk of a single GET 00 ALL on
            # devices with many channels (BUFFER=8192, 0.1s read gap).
            channels = self._fetch_channels(ip)

            network = self._parse_network(raw)

            if "AUTOMXR_MODE" not in raw:
                for cmd in ["AUTOMXR_MODE", "AUTOMXR_HOLDTIME", "AUTOMXR_OFF_ATT", "AUTOMXR_MAX_NOM", "AUTOMXR_GATE_SEN"]:
                    res = self._tcp_send(ip, f"< GET 21 {cmd} >", timeout=1)
                    if res: raw += res
            automixer = self._parse_automixer(raw)

            matrix_routes = self._parse_matrix_routes(raw)
            matrix_gains = self._parse_matrix_gains(raw)
            peq = self._parse_peq(raw)
            output_types = self._parse_output_types(raw)
            direct_out = self._parse_direct_out(raw)

            # Per-channel automixer settings
            auto_priority = {}
            auto_always_on = {}
            auto_gate = {}

            if "AUTOMXR_PRIORITY" not in raw:
                res = self._tcp_send(ip, "< GET 00 AUTOMXR_PRIORITY >", timeout=2)
                if res: raw += res
            if "AUTOMXR_ALWAYS_ON" not in raw:
                res = self._tcp_send(ip, "< GET 00 AUTOMXR_ALWAYS_ON >", timeout=2)
                if res: raw += res
            if "AUTOMXR_GATE" not in raw:
                res = self._tcp_send(ip, "< GET 00 AUTOMXR_GATE >", timeout=2)
                if res: raw += res

            for ch, val in re.findall(r"REP\s+(\d+)\s+AUTOMXR_PRIORITY\s+(ON|OFF)", raw):
                auto_priority[str(int(ch))] = val == "ON"
            for ch, val in re.findall(r"REP\s+(\d+)\s+AUTOMXR_ALWAYS_ON\s+(ON|OFF)", raw):
                auto_always_on[str(int(ch))] = val == "ON"
            for ch, val in re.findall(r"REP\s+(\d+)\s+AUTOMXR_GATE\s+(ON|OFF)", raw):
                auto_gate[str(int(ch))] = val == "ON"

            # Channel names from device
            chan_names = {}
            for ch, name in re.findall(r"REP\s+(\d+)\s+NA_CHAN_NAME\s+\{([^}]*)\}", raw):
                chan_names[str(int(ch))] = name.strip()

            return {
                "reachable": True,
                "version": fw,
                "model": model,
                "muted": mute == "ON",
                "active_preset": preset,
                "encryption": encrypt == "ON",
                "mute_sync": mutesync == "ON",
                "usb_connected": usb_conn == "ON",
                "usb_device_type": usb_type,
                "call_status": "ON" if onhook == "OFFHOOK" else ("OFF" if onhook == "ONHOOK" else onhook),
                "onhook_enable": onhook_enable,
                "led_brightness": led_br,
                "input_meter_mode": in_meter_mode,
                "output_meter_mode": out_meter_mode,
                "flash": flash,
                "compressor": compressor,
                "gate_inhibit": gate_inhibit,
                "channels": channels,
                "network": network,
                "automixer": automixer,
                "automixer_channels": {
                    "priority": auto_priority,
                    "always_on": auto_always_on,
                    "gate": auto_gate,
                },
                "matrix_routes": matrix_routes,
                "matrix_gains": matrix_gains,
                "peq": peq,
                "output_types": output_types,
                "direct_out_points": direct_out,
                "channel_names": chan_names,
            }
        except Exception as e:
            return {"reachable": False, "error": str(e)}

    def _parse_channels_batch(self, raw):
        channels = {}
        for ch, state in re.findall(r"REP\s+(\d+)\s+AUDIO_MUTE\s+(ON|OFF)", raw):
            channels.setdefault(str(int(ch)), {})["mute"] = state == "ON"
        for ch, gain in re.findall(r"REP\s+(\d+)\s+AUDIO_GAIN_HI_RES\s+(\d+)", raw):
            channels.setdefault(str(int(ch)), {})["gain"] = int(gain)
        for ch, state in re.findall(r"REP\s+(\d+)\s+AEC\s+(ON|OFF)", raw):
            channels.setdefault(str(int(ch)), {})["aec"] = state == "ON"
        for ch, state in re.findall(r"REP\s+(\d+)\s+NOISE_RED\s+(ON|OFF)", raw):
            channels.setdefault(str(int(ch)), {})["noise_red"] = state == "ON"
        for ch, state in re.findall(r"REP\s+(\d+)\s+AGC\s+(ON|OFF)", raw):
            channels.setdefault(str(int(ch)), {})["agc"] = state == "ON"
        return channels

    # ── send_command ─────────────────────────────────────────

    def send_command(self, ip, port, display_id, command, params=None):
        try:
            if isinstance(command, dict):
                action = command.get("action", "")
                cmd_params = command.get("params", {}) or {}
            else:
                action = command
                cmd_params = params or {}

            if action == "log_export":
                log_data = self._tcp_send(ip, "< GET LOG >", timeout=10)
                return True, log_data

            ok = self._send_tcp_command(ip, action, cmd_params)
            msg = f"{action} {'success' if ok else 'failed'}"
            return ok, msg
        except Exception as e:
            return False, str(e)

    def _send_tcp_command(self, ip, action, params):
        channel = params.get("channel", 0)
        mapping = {
            "device_mute_on":  lambda: self._send_ok(ip, "< SET DEVICE_AUDIO_MUTE ON >"),
            "device_mute_off": lambda: self._send_ok(ip, "< SET DEVICE_AUDIO_MUTE OFF >"),
            "device_mute_toggle": lambda: self._send_ok(ip, "< SET DEVICE_AUDIO_MUTE TOGGLE >"),
            "channel_mute_on":  lambda: self._send_ok(ip, f"< SET {channel:02d} AUDIO_MUTE ON >"),
            "channel_mute_off": lambda: self._send_ok(ip, f"< SET {channel:02d} AUDIO_MUTE OFF >"),
            "channel_mute_toggle": lambda: self._send_ok(ip, f"< SET {channel:02d} AUDIO_MUTE TOGGLE >"),
            "channel_gain_set": lambda: self._send_ok(ip, f"< SET {channel:02d} AUDIO_GAIN_HI_RES {params.get('gain', 700):04d} >"),
            "channel_gain_inc": lambda: self._send_ok(ip, f"< SET {channel:02d} AUDIO_GAIN_HI_RES DEC {params.get('amount', 10)} >"),
            "channel_gain_dec": lambda: self._send_ok(ip, f"< SET {channel:02d} AUDIO_GAIN_HI_RES INC {params.get('amount', 10)} >"),
            "aec_on":  lambda: self._send_ok(ip, f"< SET {channel:02d} AEC ON >"),
            "aec_off": lambda: self._send_ok(ip, f"< SET {channel:02d} AEC OFF >"),
            "aec_toggle": lambda: self._send_ok(ip, f"< SET {channel:02d} AEC TOGGLE >"),
            "noise_red_on":  lambda: self._send_ok(ip, f"< SET {channel:02d} NOISE_RED ON >"),
            "noise_red_off": lambda: self._send_ok(ip, f"< SET {channel:02d} NOISE_RED OFF >"),
            "agc_on":  lambda: self._send_ok(ip, f"< SET {channel:02d} AGC ON >"),
            "agc_off": lambda: self._send_ok(ip, f"< SET {channel:02d} AGC OFF >"),
            "agc_toggle": lambda: self._send_ok(ip, f"< SET {channel:02d} AGC TOGGLE >"),
            "peq_on":  lambda: self._send_ok(ip, f"< SET {params.get('block', channel):02d} PEQ {params.get('filter', 1):02d} ON >"),
            "peq_off": lambda: self._send_ok(ip, f"< SET {params.get('block', channel):02d} PEQ {params.get('filter', 1):02d} OFF >"),
            "preset_load": lambda: self._send_ok(ip, f"< SET PRESET {params.get('preset', 1):02d} >"),
            "matrix_route_on":  lambda: self._send_ok(ip, f"< SET {params.get('input', 0):02d} MATRIX_MXR_ROUTE {params.get('output', 15):02d} ON >"),
            "matrix_route_off": lambda: self._send_ok(ip, f"< SET {params.get('input', 0):02d} MATRIX_MXR_ROUTE {params.get('output', 15):02d} OFF >"),
            "matrix_gain_set":  lambda: self._send_ok(ip, f"< SET {params.get('input', 0):02d} MATRIX_MXR_GAIN {params.get('output', 15):02d} {params.get('gain', 700):04d} >"),
            "automixer_mode_set": lambda: self._send_ok(ip, f"< SET 21 AUTOMXR_MODE {params.get('mode', 'GATING')} >"),
            "compressor_on":  lambda: self._send_ok(ip, "< SET 21 COMPRESSOR ON >"),
            "compressor_off": lambda: self._send_ok(ip, "< SET 21 COMPRESSOR OFF >"),
            "delay_set": lambda: self._send_ok(ip, f"< SET {channel:02d} DELAY {params.get('ms', 0):04d} >"),
            "flash_on":  lambda: self._send_ok(ip, "< SET FLASH ON >"),
            "flash_off": lambda: self._send_ok(ip, "< SET FLASH OFF >"),
            "reboot":           lambda: self._tcp_send(ip, "< SET REBOOT >", timeout=3) or True,
            "restore_defaults": lambda: self._tcp_send(ip, "< SET DEFAULT_SETTINGS >", timeout=3) or True,
            "raw": lambda: self._tcp_send(ip, params.get("command", ""), timeout=5) or True,
            "mute_sync_on":  lambda: self._send_ok(ip, "< SET MUTESYNC ON >"),
            "mute_sync_off": lambda: self._send_ok(ip, "< SET MUTESYNC OFF >"),
            "usb_device_type_set": lambda: self._send_ok(ip, f"< SET USB_DEVICE_TYPE {params.get('type', 'SPEAKERPHONE')} >"),
            "meter_mode_input_set":  lambda: self._send_ok(ip, f"< SET INPUT_METER_MODE {params.get('mode', 'POST_FADER')} >"),
            "meter_mode_output_set": lambda: self._send_ok(ip, f"< SET OUTPUT_METER_MODE {params.get('mode', 'POST_FADER')} >"),
            "output_type_set": lambda: self._send_ok(ip, f"< SET {channel:02d} AUDIO_OUT_LVL_SWITCH {params.get('type', 'LINE_LVL')} >"),
            "automixer_priority_on":  lambda: self._send_ok(ip, f"< SET {channel:02d} AUTOMXR_PRIORITY ON >"),
            "automixer_priority_off": lambda: self._send_ok(ip, f"< SET {channel:02d} AUTOMXR_PRIORITY OFF >"),
            "automixer_always_on_on":  lambda: self._send_ok(ip, f"< SET {channel:02d} AUTOMXR_ALWAYS_ON ON >"),
            "automixer_always_on_off": lambda: self._send_ok(ip, f"< SET {channel:02d} AUTOMXR_ALWAYS_ON OFF >"),
            "automixer_off_att_set": lambda: self._send_ok(ip, f"< SET 21 AUTOMXR_OFF_ATT {params.get('value', 100):03d} >"),
            "automixer_sensitivity_set": lambda: self._send_ok(ip, f"< SET 21 AUTOMXR_GATE_SEN {params.get('value', 5)} >"),
            "automixer_last_mic_hold_set": lambda: self._send_ok(ip, f"< SET 21 AUTOMXR_HOLDTIME {params.get('ms', 400):04d} >"),
            "automixer_max_mics_set": lambda: self._send_ok(ip, f"< SET 21 AUTOMXR_MAX_NOM {params.get('count', 8)} >"),
            "compressor_threshold_set": lambda: self._send_ok(ip, f"< SET 21 COMP_THRESHOLD {params.get('value', 300):03d} >"),
            "compressor_ratio_set": lambda: self._send_ok(ip, f"< SET 21 COMP_RATIO {params.get('value', 20):04d} >"),
            "gate_inhibit_on":  lambda: self._send_ok(ip, "< SET 22 GATE_INHIBIT ON >"),
            "gate_inhibit_off": lambda: self._send_ok(ip, "< SET 22 GATE_INHIBIT OFF >"),
            "directout_point_set": lambda: self._send_ok(ip, f"< SET {channel:02d} DIRECTOUT_POINT {params.get('point', 0)} >"),
            "aec_reference_set": lambda: self._send_ok(ip, f"< SET {channel:02d} AEC_REF {params.get('ref', 'DANTEOUT1')} >"),
            "aec_nlp_set": lambda: self._send_ok(ip, f"< SET {channel:02d} AEC_NLP {params.get('level', 'MEDIUM')} >"),
            "noise_red_level_set": lambda: self._send_ok(ip, f"< SET {channel:02d} NOISE_RED_LVL {params.get('level', 'MEDIUM')} >"),
            "log_export": lambda: self._tcp_send(ip, "< GET LOG >", timeout=10),
        }
        fn = mapping.get(action)
        if not fn:
            return False
        return fn()


def get_plugin(config=None):
    return ShureP300Plugin(config)