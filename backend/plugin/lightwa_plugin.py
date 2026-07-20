# import re
# import socket
# import time

# import requests

# from .base import ManualPlatformPlugin


# MODEL_CAPS = {
#     "UCX-2X1-H20":    {"inputs": 2, "outputs": 1, "audio_out": "O3", "has_audio": True, "has_tps": True,  "has_usbc": True, "has_gpio": True, "has_rs232": True, "protocol": "lw3"},
#     "UCX-4X2-HC40":   {"inputs": 4, "outputs": 2, "audio_out": "O3", "has_audio": True, "has_tps": True,  "has_usbc": True, "has_gpio": True, "has_rs232": True, "protocol": "lw3"},
#     "UCX-4X3-HC30":   {"inputs": 4, "outputs": 3, "audio_out": "O3", "has_audio": True, "has_tps": True,  "has_usbc": True, "has_gpio": True, "has_rs232": True, "protocol": "lw3"},
# }

# # Audio crosspoint notes (from UCX manual §7.10):
# #   - Audio inputs  : I1–I4  (de-embedded from HDMI/USB-C inputs)
# #   - Audio output  : O3     (analog 5-pole Phoenix connector, the only audio XP output)
# #   - Switch path   : POST /api/V1/MEDIA/AUDIO/XP/switch   body: "<in>:O3"
# #   - Mute (XP)     : POST /api/V1/MEDIA/AUDIO/XP/<port>/Mute   (inputs I1-I4 or output O3)
# #   - Mute (port)   : POST /api/V1/MEDIA/AUDIO/O3/Mute           (analog out only)
# #   - Embedded mute : POST /api/V1/MEDIA/VIDEO/<port>/EmbeddedAudioMute  (video outputs O1/O2)
# #   - Volume (%)    : POST /api/V1/MEDIA/AUDIO/O3/VolumePercent
# #   - Volume (dB)   : POST /api/V1/MEDIA/AUDIO/O3/VolumedB        (-95.62 dB … 0 dB)
# #   - Volume step dB: POST /api/V1/MEDIA/AUDIO/O3/stepVolumedB
# #   - Volume step %: POST /api/V1/MEDIA/AUDIO/O3/stepVolumePercent
# #   - Balance       : POST /api/V1/MEDIA/AUDIO/O3/Balance         (-100 … 100, 0=centre)
# #   - Balance step  : POST /api/V1/MEDIA/AUDIO/O3/stepBalance
# #   - Lock          : POST /api/V1/MEDIA/AUDIO/XP/<port>/Lock
# #   - Signal query  : GET  /api/V1/MEDIA/AUDIO/<port>/SignalPresent
# #   - Autoselect    : POST /api/V1/MEDIA/AUDIO/AUTOSELECT/O3/Policy  ("Follow video" | "Off")
# #   - Follow video  : POST /api/V1/MEDIA/AUDIO/AUTOSELECT/O3/VideoFollowPort  (e.g. "O1")


# def _detect_caps(model_str):
#     if not model_str:
#         return {}
#     upper = str(model_str).upper().strip()
#     if upper in MODEL_CAPS:
#         return MODEL_CAPS[upper]
#     for key, caps in MODEL_CAPS.items():
#         if key in upper or upper in key:
#             return caps
#     if upper.startswith("UCX"):
#         return {
#             "inputs": 4, "outputs": 2, "audio_out": "O3",
#             "has_audio": True, "has_tps": True, "has_usbc": True,
#             "has_gpio": True, "has_rs232": True, "protocol": "lw3",
#         }
#     return {}


# def _safe_int(value, fallback=1):
#     try:
#         return int(value)
#     except Exception:
#         return fallback


# def _safe_float(value, fallback=0.0):
#     try:
#         return float(value)
#     except Exception:
#         return fallback


# def _text_bool(value, default="true"):
#     if isinstance(value, bool):
#         return "true" if value else "false"
#     if value is None:
#         return default
#     text = str(value).strip().lower()
#     if text in {"1", "true", "on", "yes", "enabled", "enable"}:
#         return "true"
#     if text in {"0", "false", "off", "no", "disabled", "disable"}:
#         return "false"
#     return text


# def _tcp_send_recv(ip, port, commands, timeout=5, inter_cmd_delay=0.1):
#     data = b""
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
#         sock.settimeout(timeout)
#         sock.connect((ip, port))
#         for command in commands:
#             sock.sendall(command.encode("ascii", errors="ignore"))
#             time.sleep(inter_cmd_delay)
#         while True:
#             try:
#                 chunk = sock.recv(4096)
#                 if not chunk:
#                     break
#                 data += chunk
#             except socket.timeout:
#                 break
#     return data.decode(errors="ignore").splitlines()


# def _lw3_cmd(ip, port, command, timeout=5):
#     return _tcp_send_recv(ip, port, [command.strip() + "\r\n"], timeout=timeout)


# def _lw3_success(lines):
#     return any(
#         ("ok" in line.lower()) or ("pw " in line.lower()) or ("pr " in line.lower())
#         for line in lines
#     )


# class LightwarePlugin(ManualPlatformPlugin):

#     name = "lightware"
#     display_name = "UCX"
#     description = "Lightware UCX family via LW3 and REST"
#     supports_display_id = False
#     supports_port = True
#     default_port = 6107
#     SUPPORTED_MODELS = list(MODEL_CAPS.keys())

#     COMMANDS = {
#         # ── Video ──────────────────────────────────────────────────────────
#         "switch":                   "Route video input to output",
#         "multi_switch":             "Route multiple video outputs at once",
#         "mute":                     "Mute video input (embedded signal)",
#         "mute_output":              "Mute video output",
#         "unmute_output":            "Unmute video output",
#         "lock_output":              "Lock video output",
#         "unlock_output":            "Unlock video output",
#         "mute_all_outputs":         "Mute all video outputs",
#         "unmute_all_outputs":       "Unmute all video outputs",
#         "mute_embedded_audio":      "Mute embedded audio on video output (O1/O2)",
#         "unmute_embedded_audio":    "Unmute embedded audio on video output (O1/O2)",
#         # ── Audio (analog O3 crosspoint) ───────────────────────────────────
#         "switch_audio":             "Route audio input (I1-I4) to analog output O3",
#         "get_audio_route":          "Query which audio input is routed to O3",
#         "mute_audio_input":         "Mute an audio input in the audio crosspoint (I1-I4)",
#         "unmute_audio_input":       "Unmute an audio input in the audio crosspoint (I1-I4)",
#         "mute_audio_output":        "Mute the analog audio output (O3) at port level",
#         "unmute_audio_output":      "Unmute the analog audio output (O3) at port level",
#         "lock_audio_port":          "Lock an audio port (I1-I4 or O3)",
#         "unlock_audio_port":        "Unlock an audio port (I1-I4 or O3)",
#         "set_volume":               "Set analog audio output volume (0-100 %)",
#         "set_volume_db":            "Set analog audio output volume in dB (-95.62 … 0)",
#         "step_volume_db":           "Step analog audio output volume up/down in dB",
#         "step_volume_percent":      "Step analog audio output volume up/down in percent",
#         "set_balance":              "Set analog audio output balance (-100 left … 100 right)",
#         "step_balance":             "Step analog audio output balance",
#         "get_audio_signal":         "Query audio signal presence on an input (I1-I4) or output (O3)",
#         "set_audio_autoselect":     "Set audio autoselect policy for O3 ('Follow video' or 'Off')",
#         "set_audio_follow_video":   "Set which video output O3 audio follows when autoselect is on",
#         # ── Misc ───────────────────────────────────────────────────────────
#         "load_preset":              "Load a saved crosspoint preset",
#         "dp_mode":                  "Set DisplayPort alt-mode policy",
#         "restart_dp":               "Restart DP link training on an input",
#         "rs232":                    "Send a raw RS-232 message via P1",
#         "get_network":              "Read current network configuration",
#         "enable_dhcp":              "Enable DHCP and apply",
#         "disable_dhcp":             "Disable DHCP and apply",
#         "set_static_ip":            "Set static IP / mask / gateway and apply",
#         "reboot":                   "Reboot the device",
#         "factory_reset":            "Restore factory defaults",
#     }

#     # ─────────────────────────────────────────────────────────────────────
#     #  Internal helpers
#     # ─────────────────────────────────────────────────────────────────────

#     def _rest(self, ip, method, endpoint, data=None):
#         url = f"http://{ip}/api{endpoint}"
#         headers = {"Content-Type": "text/plain"}
#         try:
#             if method == "GET":
#                 response = requests.get(url, headers=headers, timeout=5)
#             else:
#                 response = requests.post(
#                     url,
#                     data=data if data is not None else "",
#                     headers=headers,
#                     timeout=5,
#                 )
#             return {
#                 "success": 200 <= response.status_code < 300,
#                 "code": response.status_code,
#                 "response": response.text.strip(),
#             }
#         except Exception as exc:
#             return {"success": False, "error": str(exc)}

#     def _lw3_info(self, ip):
#         try:
#             sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             sock.settimeout(5)
#             sock.connect((ip, 6107))
#             sock.sendall(b"GET /.*\r\n")
#             time.sleep(0.3)
#             data = b""
#             while True:
#                 try:
#                     chunk = sock.recv(4096)
#                     if not chunk:
#                         break
#                     data += chunk
#                 except socket.timeout:
#                     break
#             sock.close()
#             parsed = {}
#             for line in data.decode(errors="ignore").splitlines():
#                 if "=" in line:
#                     key, value = line.split("=", 1)
#                     key = key.replace("pr /.", "").strip()
#                     parsed[key] = value.strip()
#             return parsed
#         except Exception as exc:
#             return {"error": str(exc)}

#     def _caps_for_model(self, model=None):
#         return dict(_detect_caps(model or self.config.get("model") or ""))

#     def _audio_out(self, caps):
#         """Return the audio output port name for this model (always O3 on UCX)."""
#         return caps.get("audio_out", "O3")

#     # ─────────────────────────────────────────────────────────────────────
#     #  Public API
#     # ─────────────────────────────────────────────────────────────────────

#     def get_device_info(self, ip, port=6107, display_id=None):
#         lw3  = self._lw3_info(ip)
#         caps = self._caps_for_model(lw3.get("ProductName"))

#         if lw3.get("error"):
#             return {
#                 "ip_address": ip, "port": port, "display_id": display_id,
#                 "make": "Lightware", "device_type": "Lightware UCX",
#                 "model_family": "UCX", "current_status": "Offline",
#                 "capabilities": caps or None,
#                 "input_count": caps.get("inputs", 4),
#                 "output_count": caps.get("outputs", 2),
#                 "error": lw3.get("error"),
#             }

#         hostname = self._rest(ip, "GET", "/V1/MANAGEMENT/NETWORK/Hostname")
#         ip_addr  = self._rest(ip, "GET", "/V1/MANAGEMENT/NETWORK/IpAddress")

#         return {
#             "ip_address": ip, "port": port, "display_id": display_id,
#             "make": "Lightware", "device_type": "Lightware UCX",
#             "model_family": "UCX",
#             "device_name": hostname.get("response") or lw3.get("ProductName") or self.display_name,
#             "model": lw3.get("ProductName"),
#             "serial_number": lw3.get("SerialNumber"),
#             "firmware": lw3.get("PackageVersion"),
#             "hostname": hostname.get("response"),
#             "ip": ip_addr.get("response"),
#             "capabilities": caps or None,
#             "input_count": caps.get("inputs", 4),
#             "output_count": caps.get("outputs", 2),
#             "current_status": "Online",
#         }

#     # ─────────────────────────────────────────────────────────────────────

#     def send_command(self, ip, port, display_id, command, params=None):  # noqa: C901
#         params       = params or {}
#         base_command = (command or "").split(":", 1)[0]
#         input_number  = _safe_int(params.get("input")  or params.get("inp"),  1)
#         output_number = _safe_int(params.get("output") or params.get("out"),  1)
#         port_number   = _safe_int(params.get("port"),  1)
#         preset        = _safe_int(params.get("preset"), 1)
#         level         = _safe_int(
#             params.get("level") if params.get("level") is not None else params.get("volume"), 50
#         )
#         db_level = _safe_float(params.get("db") or params.get("level_db"), 0.0)
#         step     = _safe_float(params.get("step"), 1.0)
#         balance  = _safe_int(params.get("balance"), 0)
#         state    = _text_bool(
#             params.get("state") if params.get("state") is not None else params.get("enabled")
#         )
#         payload = params.get("payload")

#         caps     = self._caps_for_model(params.get("model"))
#         audio_out = self._audio_out(caps)   # "O3" on all current UCX models

#         try:
#             # ══════════════════════════════════════════════════════════════
#             #  VIDEO commands  (unchanged from original)
#             # ══════════════════════════════════════════════════════════════

#             if base_command == "switch":
#                 route_payload = payload or params.get("route") or f"I{input_number}:O{output_number}"
#                 result = self._rest(ip, "POST", "/V1/MEDIA/VIDEO/XP/switch", route_payload)
#                 if result.get("success"):
#                     return True, {"command": base_command, "input": input_number, "output": output_number}
#                 lines = _lw3_cmd(ip, port, f"CALL /MEDIA/VIDEO/XP:switch(I{input_number}:O{output_number})")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "input": input_number, "output": output_number}
#                 return False, {
#                     "command": base_command, "input": input_number, "output": output_number,
#                     "error": result.get("error") or result.get("response") or "Switch failed",
#                     "raw": lines,
#                 }

#             if base_command == "multi_switch":
#                 route_payload = payload or params.get("route") or ""
#                 result = self._rest(ip, "POST", "/V1/MEDIA/VIDEO/XP/switch", route_payload)
#                 if result.get("success"):
#                     return True, {"command": base_command, "payload": route_payload}
#                 lines = _lw3_cmd(ip, port, f"CALL /MEDIA/VIDEO/XP:switch({route_payload})")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "payload": route_payload}
#                 return False, {
#                     "command": base_command, "payload": route_payload,
#                     "error": result.get("error") or result.get("response") or "Multi-switch failed",
#                     "raw": lines,
#                 }

#             if base_command == "mute":
#                 # Mute/unmute embedded audio on a VIDEO input port
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/XP/I{input_number}/Mute", state)
#                 if result.get("success"):
#                     return True, {"command": base_command, "input": input_number, "muted": state == "true"}
#                 lines = _lw3_cmd(ip, port, f"SET /MEDIA/VIDEO/I{input_number}.Mute={state}")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "input": input_number, "muted": state == "true"}
#                 return False, {
#                     "command": base_command, "input": input_number,
#                     "error": result.get("error") or result.get("response") or "Mute failed",
#                     "raw": lines,
#                 }

#             if base_command == "mute_output":
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/XP/O{output_number}/Mute", "true")
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": output_number, "muted": True}
#                 lines = _lw3_cmd(ip, port, f"SET /MEDIA/VIDEO/O{output_number}.Mute=true")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "output": output_number, "muted": True}
#                 return False, {
#                     "command": base_command, "output": output_number,
#                     "error": result.get("error") or result.get("response") or "Mute output failed",
#                     "raw": lines,
#                 }

#             if base_command == "unmute_output":
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/XP/O{output_number}/Mute", "false")
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": output_number, "muted": False}
#                 lines = _lw3_cmd(ip, port, f"SET /MEDIA/VIDEO/O{output_number}.Mute=false")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "output": output_number, "muted": False}
#                 return False, {
#                     "command": base_command, "output": output_number,
#                     "error": result.get("error") or result.get("response") or "Unmute output failed",
#                     "raw": lines,
#                 }

#             if base_command == "lock_output":
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/XP/O{output_number}/Lock", "true")
#                 return result.get("success", False), {"command": base_command, "output": output_number, "locked": True}

#             if base_command == "unlock_output":
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/XP/O{output_number}/Lock", "false")
#                 return result.get("success", False), {"command": base_command, "output": output_number, "locked": False}

#             if base_command == "mute_all_outputs":
#                 n_out = caps.get("outputs", 2)
#                 for i in range(1, n_out + 1):
#                     self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/XP/O{i}/Mute", "true")
#                 return True, {"command": base_command, "outputs_affected": n_out}

#             if base_command == "unmute_all_outputs":
#                 n_out = caps.get("outputs", 2)
#                 for i in range(1, n_out + 1):
#                     self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/XP/O{i}/Mute", "false")
#                 return True, {"command": base_command, "outputs_affected": n_out}

#             # ── Embedded audio on video outputs (O1 / O2) ─────────────────
#             if base_command == "mute_embedded_audio":
#                 # Mute the embedded audio track carried by a VIDEO output
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/O{output_number}/EmbeddedAudioMute", "true")
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": output_number, "muted": True}
#                 return False, {
#                     "command": base_command, "output": output_number,
#                     "error": result.get("error") or result.get("response") or "Embedded audio mute failed",
#                 }

#             if base_command == "unmute_embedded_audio":
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/O{output_number}/EmbeddedAudioMute", "false")
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": output_number, "muted": False}
#                 return False, {
#                     "command": base_command, "output": output_number,
#                     "error": result.get("error") or result.get("response") or "Embedded audio unmute failed",
#                 }

#             # ══════════════════════════════════════════════════════════════
#             #  AUDIO commands  (new / corrected)
#             #
#             #  The UCX audio crosspoint has inputs I1-I4 and a single
#             #  analog output O3.  All audio XP REST calls go to:
#             #    /api/V1/MEDIA/AUDIO/XP/...
#             #  Volume / balance live on the port node itself:
#             #    /api/V1/MEDIA/AUDIO/O3/...
#             # ══════════════════════════════════════════════════════════════

#             if base_command == "switch_audio":
#                 # Route audio input I<n> to analog output O3
#                 # body format: "<in>:O3"
#                 audio_in = f"I{input_number}"
#                 route_payload = payload or params.get("route") or f"{audio_in}:{audio_out}"
#                 result = self._rest(ip, "POST", "/V1/MEDIA/AUDIO/XP/switch", route_payload)
#                 if result.get("success"):
#                     return True, {"command": base_command, "input": audio_in, "output": audio_out}
#                 # LW3 fallback
#                 lines = _lw3_cmd(ip, port, f"CALL /MEDIA/AUDIO/XP:switch({audio_in}:{audio_out})")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "input": audio_in, "output": audio_out}
#                 return False, {
#                     "command": base_command, "input": audio_in, "output": audio_out,
#                     "error": result.get("error") or result.get("response") or "Audio switch failed",
#                     "raw": lines,
#                 }

#             if base_command == "get_audio_route":
#                 # GET /api/V1/MEDIA/AUDIO/XP/O3/ConnectedSource → e.g. "I2"
#                 result = self._rest(ip, "GET", f"/V1/MEDIA/AUDIO/XP/{audio_out}/ConnectedSource")
#                 return result.get("success", False), {
#                     "command": base_command,
#                     "output": audio_out,
#                     "connected_source": result.get("response"),
#                 }

#             if base_command == "mute_audio_input":
#                 # Suspend the connection of an audio input in the audio XP.
#                 # Endpoint: POST /api/V1/MEDIA/AUDIO/XP/I<n>/Mute  body: "true"
#                 audio_port = f"I{input_number}"
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/XP/{audio_port}/Mute", "true")
#                 if result.get("success"):
#                     return True, {"command": base_command, "input": audio_port, "muted": True}
#                 lines = _lw3_cmd(ip, port, f"SET /MEDIA/AUDIO/XP/{audio_port}.Mute=true")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "input": audio_port, "muted": True}
#                 return False, {
#                     "command": base_command, "input": audio_port,
#                     "error": result.get("error") or result.get("response") or "Audio input mute failed",
#                     "raw": lines,
#                 }

#             if base_command == "unmute_audio_input":
#                 audio_port = f"I{input_number}"
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/XP/{audio_port}/Mute", "false")
#                 if result.get("success"):
#                     return True, {"command": base_command, "input": audio_port, "muted": False}
#                 lines = _lw3_cmd(ip, port, f"SET /MEDIA/AUDIO/XP/{audio_port}.Mute=false")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "input": audio_port, "muted": False}
#                 return False, {
#                     "command": base_command, "input": audio_port,
#                     "error": result.get("error") or result.get("response") or "Audio input unmute failed",
#                     "raw": lines,
#                 }

#             if base_command == "mute_audio_output":
#                 # Two equivalent paths for muting the analog output O3:
#                 #   1. POST /api/V1/MEDIA/AUDIO/XP/O3/Mute  "true"  (XP-level)
#                 #   2. POST /api/V1/MEDIA/AUDIO/O3/Mute     "true"  (port-level)
#                 # We try both; the manual says they are separate properties.
#                 result_xp   = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/XP/{audio_out}/Mute", "true")
#                 result_port = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/{audio_out}/Mute", "true")
#                 success = result_xp.get("success") or result_port.get("success")
#                 if not success:
#                     lines = _lw3_cmd(ip, port, f"SET /MEDIA/AUDIO/{audio_out}.Mute=true")
#                     success = _lw3_success(lines)
#                 return success, {"command": base_command, "output": audio_out, "muted": True}

#             if base_command == "unmute_audio_output":
#                 result_xp   = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/XP/{audio_out}/Mute", "false")
#                 result_port = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/{audio_out}/Mute", "false")
#                 success = result_xp.get("success") or result_port.get("success")
#                 if not success:
#                     lines = _lw3_cmd(ip, port, f"SET /MEDIA/AUDIO/{audio_out}.Mute=false")
#                     success = _lw3_success(lines)
#                 return success, {"command": base_command, "output": audio_out, "muted": False}

#             if base_command == "lock_audio_port":
#                 # Locks an audio XP port (input I1-I4 or output O3)
#                 audio_port = (
#                     params.get("audio_port")
#                     or (f"I{input_number}" if params.get("input") else audio_out)
#                 )
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/XP/{audio_port}/Lock", "true")
#                 return result.get("success", False), {
#                     "command": base_command, "audio_port": audio_port, "locked": True,
#                 }

#             if base_command == "unlock_audio_port":
#                 audio_port = (
#                     params.get("audio_port")
#                     or (f"I{input_number}" if params.get("input") else audio_out)
#                 )
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/XP/{audio_port}/Lock", "false")
#                 return result.get("success", False), {
#                     "command": base_command, "audio_port": audio_port, "locked": False,
#                 }

#             if base_command == "set_volume":
#                 # POST /api/V1/MEDIA/AUDIO/O3/VolumePercent  body: "50"
#                 volume = max(0, min(100, level))
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/{audio_out}/VolumePercent", str(volume))
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": audio_out, "volume_percent": volume}
#                 lines = _lw3_cmd(ip, port, f"SET /MEDIA/AUDIO/{audio_out}.VolumePercent={volume}")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "output": audio_out, "volume_percent": volume}
#                 return False, {
#                     "command": base_command, "output": audio_out, "volume_percent": volume,
#                     "error": result.get("error") or result.get("response") or "Volume (%) failed",
#                     "raw": lines,
#                 }

#             if base_command == "set_volume_db":
#                 # POST /api/V1/MEDIA/AUDIO/O3/VolumedB  body: "-15"
#                 # Range: -95.62 dB … 0 dB, step 0.375 dB
#                 clamped_db = max(-95.62, min(0.0, db_level))
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/{audio_out}/VolumedB", str(clamped_db))
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": audio_out, "volume_db": clamped_db}
#                 lines = _lw3_cmd(ip, port, f"SET /MEDIA/AUDIO/{audio_out}.VolumedB={clamped_db}")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "output": audio_out, "volume_db": clamped_db}
#                 return False, {
#                     "command": base_command, "output": audio_out, "volume_db": clamped_db,
#                     "error": result.get("error") or result.get("response") or "Volume (dB) failed",
#                     "raw": lines,
#                 }

#             if base_command == "step_volume_db":
#                 # POST /api/V1/MEDIA/AUDIO/O3/stepVolumedB  body: "-1" (decrease 1 dB)
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/{audio_out}/stepVolumedB", str(step))
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": audio_out, "step_db": step}
#                 return False, {
#                     "command": base_command, "output": audio_out, "step_db": step,
#                     "error": result.get("error") or result.get("response") or "Step volume (dB) failed",
#                 }

#             if base_command == "step_volume_percent":
#                 # POST /api/V1/MEDIA/AUDIO/O3/stepVolumePercent  body: "5"
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/{audio_out}/stepVolumePercent", str(step))
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": audio_out, "step_percent": step}
#                 return False, {
#                     "command": base_command, "output": audio_out, "step_percent": step,
#                     "error": result.get("error") or result.get("response") or "Step volume (%) failed",
#                 }

#             if base_command == "set_balance":
#                 # POST /api/V1/MEDIA/AUDIO/O3/Balance  body: "0"
#                 # Range: -100 (full left) … 100 (full right), 0 = centre
#                 clamped_bal = max(-100, min(100, balance))
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/{audio_out}/Balance", str(clamped_bal))
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": audio_out, "balance": clamped_bal}
#                 return False, {
#                     "command": base_command, "output": audio_out, "balance": clamped_bal,
#                     "error": result.get("error") or result.get("response") or "Balance failed",
#                 }

#             if base_command == "step_balance":
#                 # POST /api/V1/MEDIA/AUDIO/O3/stepBalance  body: "5"
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/{audio_out}/stepBalance", str(step))
#                 if result.get("success"):
#                     return True, {"command": base_command, "output": audio_out, "step": step}
#                 return False, {
#                     "command": base_command, "output": audio_out, "step": step,
#                     "error": result.get("error") or result.get("response") or "Step balance failed",
#                 }

#             if base_command == "get_audio_signal":
#                 # GET /api/V1/MEDIA/AUDIO/<port>/SignalPresent  (I1-I4 or O3)
#                 audio_port = (
#                     params.get("audio_port")
#                     or (f"I{input_number}" if params.get("input") else audio_out)
#                 )
#                 result = self._rest(ip, "GET", f"/V1/MEDIA/AUDIO/{audio_port}/SignalPresent")
#                 return result.get("success", False), {
#                     "command": base_command,
#                     "audio_port": audio_port,
#                     "signal_present": result.get("response"),
#                 }

#             if base_command == "set_audio_autoselect":
#                 # POST /api/V1/MEDIA/AUDIO/AUTOSELECT/O3/Policy
#                 # body: "Follow video"  or  "Off"
#                 policy = params.get("policy") or ("Follow video" if state == "true" else "Off")
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/AUDIO/AUTOSELECT/{audio_out}/Policy", policy)
#                 return result.get("success", False), {
#                     "command": base_command, "output": audio_out, "policy": policy,
#                 }

#             if base_command == "set_audio_follow_video":
#                 # POST /api/V1/MEDIA/AUDIO/AUTOSELECT/O3/VideoFollowPort
#                 # body: "O1" or "O2"  — which video output the audio should track
#                 video_out_port = params.get("video_port") or f"O{output_number}"
#                 result = self._rest(
#                     ip, "POST",
#                     f"/V1/MEDIA/AUDIO/AUTOSELECT/{audio_out}/VideoFollowPort",
#                     video_out_port,
#                 )
#                 return result.get("success", False), {
#                     "command": base_command,
#                     "audio_out": audio_out,
#                     "follows_video": video_out_port,
#                 }

#             # ══════════════════════════════════════════════════════════════
#             #  MISC commands
#             # ══════════════════════════════════════════════════════════════

#             if base_command == "load_preset":
#                 lines = _lw3_cmd(ip, port, f"CALL /MEDIA/VIDEO/XP:loadPreset({preset})")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command, "preset": preset}
#                 raw_text = " | ".join(lines)
#                 error = f"Preset {preset} does not exist on the device" if "not exists" in raw_text.lower() else "Preset load failed"
#                 return False, {"command": base_command, "preset": preset, "error": error, "raw": lines}

#             if base_command == "dp_mode":
#                 mode = params.get("mode") or params.get("policy") or ""
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/USB/U{port_number}/DpAltModePolicy", mode)
#                 return result.get("success", False), {"command": base_command, "port": port_number, "mode": mode}

#             if base_command == "restart_dp":
#                 result = self._rest(ip, "POST", f"/V1/MEDIA/VIDEO/I{input_number}/DP/restartLinkTraining")
#                 return result.get("success", False), {"command": base_command, "input": input_number}

#             if base_command == "rs232":
#                 rs232_command = params.get("command") or params.get("data") or ""
#                 result = self._rest(ip, "POST", "/V1/MEDIA/SERIAL/P1/send", rs232_command)
#                 return result.get("success", False), {"command": base_command, "data": rs232_command}

#             if base_command == "get_network":
#                 return True, {
#                     "command": base_command,
#                     "hostname": self._rest(ip, "GET", "/V1/MANAGEMENT/NETWORK/Hostname"),
#                     "ip":       self._rest(ip, "GET", "/V1/MANAGEMENT/NETWORK/IpAddress"),
#                     "dhcp":     self._rest(ip, "GET", "/V1/MANAGEMENT/NETWORK/DhcpEnabled"),
#                 }

#             if base_command == "enable_dhcp":
#                 dhcp_result  = self._rest(ip, "POST", "/V1/MANAGEMENT/NETWORK/DhcpEnabled", "true")
#                 apply_result = self._rest(ip, "POST", "/V1/MANAGEMENT/NETWORK/applySettings")
#                 success = dhcp_result.get("success", False)
#                 return success, {"command": base_command, "applied": success, "apply_result": apply_result}

#             if base_command == "disable_dhcp":
#                 dhcp_result  = self._rest(ip, "POST", "/V1/MANAGEMENT/NETWORK/DhcpEnabled", "false")
#                 apply_result = self._rest(ip, "POST", "/V1/MANAGEMENT/NETWORK/applySettings")
#                 success = dhcp_result.get("success", False)
#                 return success, {"command": base_command, "applied": success, "apply_result": apply_result}

#             if base_command == "set_static_ip":
#                 ipaddr  = params.get("ipaddr")  or params.get("ip_address") or ""
#                 subnet  = params.get("subnet")  or params.get("mask")       or ""
#                 gateway = params.get("gateway") or ""
#                 dhcp_result    = self._rest(ip, "POST", "/V1/MANAGEMENT/NETWORK/DhcpEnabled",      "false")
#                 ip_result      = self._rest(ip, "POST", "/V1/MANAGEMENT/NETWORK/StaticIpAddress",  ipaddr)
#                 subnet_result  = self._rest(ip, "POST", "/V1/MANAGEMENT/NETWORK/StaticSubnetMask", subnet)
#                 gateway_result = (
#                     self._rest(ip, "POST", "/V1/MANAGEMENT/NETWORK/StaticGatewayAddress", gateway)
#                     if gateway else {"success": True}
#                 )
#                 apply_result = self._rest(ip, "POST", "/V1/MANAGEMENT/NETWORK/applySettings")
#                 success = all([
#                     dhcp_result.get("success"),
#                     ip_result.get("success"),
#                     subnet_result.get("success"),
#                     gateway_result.get("success"),
#                 ])
#                 return success, {
#                     "command": base_command, "ipaddr": ipaddr, "subnet": subnet, "gateway": gateway,
#                     "applied": success, "apply_result": apply_result,
#                 }

#             if base_command == "reboot":
#                 result = self._rest(ip, "POST", "/V1/SYS/reboot")
#                 if result.get("success"):
#                     return True, {"command": base_command}
#                 lines = _lw3_cmd(ip, port, "CALL /SYS/MB.restart()")
#                 if _lw3_success(lines):
#                     return True, {"command": base_command}
#                 return False, {
#                     "command": base_command,
#                     "error": result.get("error") or result.get("response") or "Reboot failed",
#                     "raw": lines,
#                 }

#             if base_command == "factory_reset":
#                 result = self._rest(ip, "POST", "/V1/SYS/factoryDefaults")
#                 if result.get("success"):
#                     return True, {"command": base_command}
#                 return False, {
#                     "command": base_command,
#                     "error": result.get("error") or result.get("response") or "Factory reset failed",
#                 }

#             return False, f"Unsupported command: {command}"

#         except Exception as exc:
#             return False, str(exc)

#     # ─────────────────────────────────────────────────────────────────────

#     def query_status(self, ip, port=6107, display_id=None):
#         signal      = self._rest(ip, "GET", "/V1/MEDIA/VIDEO/I1/SignalPresent")
#         route       = self._rest(ip, "GET", "/V1/MEDIA/VIDEO/XP/O1/ConnectedSource")
#         audio_route = self._rest(ip, "GET", "/V1/MEDIA/AUDIO/XP/O3/ConnectedSource")
#         audio_sig   = self._rest(ip, "GET", "/V1/MEDIA/AUDIO/I1/SignalPresent")
#         volume      = self._rest(ip, "GET", "/V1/MEDIA/AUDIO/O3/VolumePercent")
#         info        = self._lw3_info(ip)
#         caps        = self._caps_for_model(info.get("ProductName"))

#         return {
#             "make": "Lightware",
#             "model_family": "UCX",
#             "model": info.get("ProductName"),
#             "serial_number": info.get("SerialNumber"),
#             "firmware": info.get("PackageVersion"),
#             "reachable": signal.get("success"),
#             "current_status": "Online" if signal.get("success") else "Offline",
#             # video
#             "signal_present": signal.get("response"),
#             "route": route.get("response"),
#             # audio
#             "audio_route": audio_route.get("response"),       # which input is feeding O3
#             "audio_signal_i1": audio_sig.get("response"),     # is audio present on I1?
#             "audio_volume_percent": volume.get("response"),   # current O3 volume
#             # caps
#             "capabilities": caps or None,
#             "input_count": caps.get("inputs", 4),
#             "output_count": caps.get("outputs", 2),
#             "error": signal.get("error") or route.get("error") or info.get("error"),
#         }