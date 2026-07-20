"""
Manual Platform Plugin: LightwareMMXPlugin
Lightware MMX4x2 series – LW2 protocol over TCP port 10001

Supported models:
  MMX4x2-HDMI          – 4 inputs, 2 video outputs, 3 audio outputs
  MMX4x2-HT200         – 4 inputs, 2 video outputs, 3 audio outputs (TPS)
  MMX4x2-HDMI-USB20-L  – 4 inputs, 2 video outputs, 3 audio outputs (USB 2.0)

LW2 protocol summary (§6 of user manual):
  TCP port  : 10001
  Frame     : {COMMAND}\r\n  → response wrapped in ( )
  Layers    : V = video, A = audio, AV = both
  Ports     : inputs I1–I4, video outputs O1–O2, audio outputs O1–O3
  Crosspoint: video 4×2, audio 3×3

Command quick-reference used in this file:
  General     : {i} {LABEL} {S} {F} {FC} {IS} {ST} {CT} {P_?} {PING} {LCMD}
  Switch      : {<in>@<out> <layer>}         e.g. {2@1 AV}
  Mute out    : {#<out> <layer>}             e.g. {#01 V}
  Unmute out  : {+<out> <layer>}             e.g. {+01 V}
  Lock out    : {#><out> <layer>}            e.g. {#>01 V}
  Unlock out  : {+<<out> <layer>}            e.g. {+<01 V}
  View XP     : {VC <layer>}                 e.g. {VC AV}
  XP size     : {GETSIZE <layer>}
  Autoselect V: {AS_V<out>=<E|D>;<F|L|P>}   e.g. {AS_V1=E;P}
  Autoselect A: {AS_A<out>=<E|D>;<F|L|P>}
  Priority V  : {PRIO_V<out>=<p1>;<p2>;…}   e.g. {PRIO_V1=1;0;2;3}
  Priority A  : {PRIO_A<out>=<p1>;<p2>;…}
  IP query    : {IP_STAT=?}
  IP set      : {IP_ADDRESS=<0|1>;<addr>}    0=static, 1=DHCP
  Netmask     : {IP_NETMASK=<mask>}
  Gateway     : {IP_GATEWAY=<addr>}
  Apply net   : {IP_APPLY}
  Eth enable  : {ETH_ENABLE=<0|1>}
  RS232 mode  : {RS232=<PASS|CONTROL|CI>}
  RS232 fmt   : {RS232_LOCAL_FORMAT=<baud>;<data>;<parity>;<stop>}
  GPIO        : {GPIO<pin>=<I|O>;<H|L|T>}   pin 0–6
  Reboot      : {RST}
  Factory     : {FACTORY=ALL}
"""

import re
import socket
import time

from .base import ManualPlatformPlugin


# ─────────────────────────────────────────────────────────────────────────────
#  Model capability table
#  video_outputs : O1–O2 (video XP)
#  audio_outputs : O1–O3 (audio XP – 3 outputs including analog phoenix)
# ─────────────────────────────────────────────────────────────────────────────
MODEL_CAPS = {
    "MMX4X2-HDMI": {
        "inputs": 4, "video_outputs": 2, "audio_outputs": 3,
        "has_tps": False, "has_usb": False, "has_gpio": True, "has_rs232": True,
    },
    "MMX4X2-HT200": {
        "inputs": 4, "video_outputs": 2, "audio_outputs": 3,
        "has_tps": True,  "has_usb": False, "has_gpio": True, "has_rs232": True,
    },
    "MMX4X2-HDMI-USB20-L": {
        "inputs": 4, "video_outputs": 2, "audio_outputs": 3,
        "has_tps": False, "has_usb": True,  "has_gpio": True, "has_rs232": True,
    },
}

_FALLBACK_CAPS = {
    "inputs": 4, "video_outputs": 2, "audio_outputs": 3,
    "has_tps": False, "has_usb": False, "has_gpio": True, "has_rs232": True,
}


def _detect_caps(model_str: str) -> dict:
    if not model_str:
        return _FALLBACK_CAPS
    key = str(model_str).upper().replace("-", "").replace(" ", "")
    for k, caps in MODEL_CAPS.items():
        if k.replace("-", "") in key or key in k.replace("-", ""):
            return caps
    return _FALLBACK_CAPS


def _safe_int(value, fallback: int = 1) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _validate_layer(layer: str) -> str:
    """Normalise layer arg to V / A / AV."""
    return layer.upper() if str(layer).upper() in ("V", "A", "AV") else "V"


def _validate_autoselect_state(state: str) -> str:
    return "E" if str(state).upper() in ("E", "ENABLE", "ENABLED", "ON", "TRUE", "1") else "D"


def _validate_autoselect_mode(mode: str) -> str:
    m = str(mode).upper()
    return m if m in ("F", "L", "P") else "P"


# ─────────────────────────────────────────────────────────────────────────────
#  Plugin
# ─────────────────────────────────────────────────────────────────────────────
class LightwareMMXPlugin(ManualPlatformPlugin):
    """Lightware MMX4x2 series via LW2 TCP (port 10001)."""

    name = "lightware_mmx"
    display_name = "MMX"
    description = "Lightware MMX4x2 series via LW2 TCP"
    supports_display_id = False
    supports_port = True
    default_port = 10001

    SUPPORTED_MODELS = list(MODEL_CAPS.keys())

    # Full command catalogue – mirrors UCX plugin structure
    COMMANDS = {
        # ── Video routing ──────────────────────────────────────────────────
        "switch_video":           "Route video input to output  (params: input, output)",
        "switch_audio":           "Route audio input to output  (params: input, output)",
        "switch_av":              "Route audio+video together   (params: input, output)",
        # ── Output mute / lock ────────────────────────────────────────────
        "mute_output":            "Mute an output port          (params: output, layer=V|A|AV)",
        "unmute_output":          "Unmute an output port        (params: output, layer=V|A|AV)",
        "lock_output":            "Lock an output port          (params: output, layer=V|A|AV)",
        "unlock_output":          "Unlock an output port        (params: output, layer=V|A|AV)",
        "mute_all_outputs":       "Mute all video outputs",
        "unmute_all_outputs":     "Unmute all video outputs",
        "mute_all_audio_outputs": "Mute all audio outputs",
        "unmute_all_audio_outputs":"Unmute all audio outputs",
        # ── Crosspoint queries ────────────────────────────────────────────
        "get_route":              "Query crosspoint state       (params: layer=V|A|AV)",
        "get_xp_size":            "Query crosspoint dimensions  (params: layer=V|A|AV)",
        # ── Autoselect ───────────────────────────────────────────────────
        "set_video_autoselect":   "Set video autoselect mode    (params: output, state=E|D, mode=F|L|P)",
        "get_video_autoselect":   "Query video autoselect       (params: output)",
        "set_audio_autoselect":   "Set audio autoselect mode    (params: output, state=E|D, mode=F|L|P)",
        "get_audio_autoselect":   "Query audio autoselect       (params: output)",
        # ── Input priorities ─────────────────────────────────────────────
        "set_video_priority":     "Set video input priorities   (params: output, priorities='1;0;2;3')",
        "get_video_priority":     "Query video input priorities (params: output)",
        "set_audio_priority":     "Set audio input priorities   (params: output, priorities='1;0;2')",
        "get_audio_priority":     "Query audio input priorities (params: output)",
        # ── Network ──────────────────────────────────────────────────────
        "get_network":            "Query current IP/DHCP status",
        "set_static_ip":          "Set static IP                (params: ipaddr, subnet, gateway)",
        "enable_dhcp":            "Enable DHCP and apply",
        "disable_dhcp":           "Set static IP mode (no apply) (params: ipaddr)",
        "apply_network":          "Apply staged network settings (restarts network interface)",
        "eth_enable":             "Enable Ethernet port",
        "eth_disable":            "Disable Ethernet port  ⚠ loses connectivity",
        # ── RS-232 ───────────────────────────────────────────────────────
        "get_rs232_mode":         "Query RS-232 control mode",
        "set_rs232_mode":         "Set RS-232 mode              (params: mode=PASS|CONTROL|CI)",
        "set_rs232_format":       "Set RS-232 port format       (params: baud, databit, parity, stopbit)",
        "get_rs232_format":       "Query RS-232 port format",
        # ── GPIO ─────────────────────────────────────────────────────────
        "set_gpio":               "Set GPIO pin direction+level (params: pin=0-6, direction=I|O, level=H|L|T)",
        "get_gpio":               "Query GPIO pin state         (params: pin=0-6)",
        # ── System ───────────────────────────────────────────────────────
        "ping":                   "Connection test (PING→PONG)",
        "get_health":             "Query internal voltages and temperature",
        "get_firmware":           "Query CPU firmware version",
        "get_all_firmware":       "Query all controller firmware versions",
        "get_serial":             "Query serial number",
        "get_model":              "Query product type / model",
        "get_label":              "Query device label",
        "get_protocol":           "Query active control protocol",
        "get_compile_time":       "Query firmware compile timestamp",
        "get_board":              "Query installed board hardware",
        "list_commands":          "List all supported LW2 commands (from device)",
        "reboot":                 "Restart device (no response sent)",
        "factory_reset":          "Restore factory defaults",
        "raw":                    "Send any raw LW2 command     (params: command)",
    }

    QUERY_COMMANDS = {
        "get_route":          "VC AV",
        "get_xp_size":        "GETSIZE AV",
        "get_network":        "IP_STAT=?",
        "get_health":         "ST",
        "get_firmware":       "F",
        "get_all_firmware":   "FC",
        "get_serial":         "S",
        "get_model":          "i",
        "get_label":          "LABEL",
        "get_protocol":       "P_?",
        "get_compile_time":   "CT",
        "get_board":          "IS",
        "list_commands":      "LCMD",
        "ping":               "PING",
    }

    # ─────────────────────────────────────────────────────────────────────
    #  LW2 response helpers
    # ─────────────────────────────────────────────────────────────────────

    def _clean_lw2_value(self, value: str) -> str:
        if not value or not isinstance(value, str):
            return value
        clean = value.strip().strip("()")
        if "=" in clean:
            _, clean = clean.split("=", 1)
        return clean.strip()

    def _extract_response_value(self, payload) -> str | None:
        if not isinstance(payload, dict):
            return None
        return self._clean_lw2_value(payload.get("response"))

    def _lw2_ok(self, response_text: str) -> bool:
        """Return True if the LW2 response looks like a success."""
        if not response_text:
            return False
        t = response_text.strip().upper()
        # Success indicators: response starts with "(", contains expected echo,
        # or contains PONG / FACTORY / IP_ etc.
        fail_tokens = ("ERROR", "UNKNOWN", "INVALID", "NOT SUPPORTED")
        return not any(tok in t for tok in fail_tokens)

    def _parse_ip_stat(self, raw: str) -> dict:
        """Parse (IP_STAT=<type>;<ip>;<mask>;<gw>) into a dict."""
        if not raw:
            return {}
        # strip surrounding parens / prefix
        clean = raw.strip().strip("()").replace("IP_STAT=", "")
        parts = clean.split(";")
        if len(parts) < 4:
            return {"raw": raw}
        return {
            "type":    "static" if parts[0].strip() == "0" else "dhcp",
            "ip":       parts[1].strip(),
            "subnet":   parts[2].strip(),
            "gateway":  parts[3].strip(),
        }

    # ─────────────────────────────────────────────────────────────────────
    #  TCP transport
    # ─────────────────────────────────────────────────────────────────────

    def _send_lw2(self, ip: str, port, command: str, timeout=None) -> dict:
        """
        Wrap command in { }, send over TCP port 10001, read full response.
        Returns: {"success": bool, "command": str, "response": str, "error"?: str}
        """
        target_port = int(port or self.default_port)
        effective_timeout = timeout or getattr(self, "timeout", 5)

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(effective_timeout)
                sock.connect((ip, target_port))
                sock.sendall(f"{{{command}}}\r\n".encode("ascii"))
                time.sleep(0.15)

                response = b""
                while True:
                    try:
                        chunk = sock.recv(4096)
                    except socket.timeout:
                        break
                    if not chunk:
                        break
                    response += chunk
                    decoded = response.decode("ascii", errors="ignore")
                    if "END)" in decoded or (
                        decoded.count("(") > 0 and decoded.endswith(")\r\n")
                    ):
                        break

            text = response.decode("ascii", errors="ignore").strip()
            return {"success": True, "command": command, "response": text}

        except Exception as exc:
            return {"success": False, "command": command, "error": str(exc), "response": ""}

    def _send_many(self, ip: str, port, commands: list[str]) -> list[dict]:
        """Send multiple LW2 commands in separate TCP calls, return list of results."""
        return [self._send_lw2(ip, port, cmd) for cmd in commands]

    # ─────────────────────────────────────────────────────────────────────
    #  Device info
    # ─────────────────────────────────────────────────────────────────────

    def get_device_info(self, ip: str, port=10001, display_id=None) -> dict:
        product_resp = self._send_lw2(ip, port, "i")

        if not product_resp.get("success"):
            return {
                "ip_address": ip, "port": port, "display_id": display_id,
                "make": "Lightware", "device_type": "Lightware MMX",
                "model_family": "MMX", "current_status": "Offline",
                "error": product_resp.get("error", "Connection failed"),
            }

        # Gather all info in parallel calls
        results = self._send_many(ip, port, ["S", "IS", "F", "FC", "LABEL", "ST", "CT", "P_?", "IP_STAT=?", "GETSIZE AV"])
        serial_r, board_r, fw_r, fw_all_r, label_r, health_r, ct_r, proto_r, net_r, size_r = results

        # Parse model
        raw_product = self._extract_response_value(product_resp) or ""
        model = raw_product.replace("I:", "").strip() or self.display_name

        # Parse serial
        serial = self._extract_response_value(serial_r) or ""
        serial = serial.replace("SN:", "").strip()

        # Parse firmware
        firmware = self._extract_response_value(fw_r) or ""
        firmware = firmware.replace("FW:", "").strip()

        caps = _detect_caps(model)
        ip_info = self._parse_ip_stat(self._extract_response_value(net_r) or "")

        return {
            "ip_address": ip, "port": port, "display_id": display_id,
            "make": "Lightware", "device_type": "Lightware MMX",
            "model_family": "MMX",
            "device_name":    self._extract_response_value(label_r) or model,
            "model":          model,
            "serial_number":  serial,
            "firmware":       firmware,
            "all_firmware":   self._extract_response_value(fw_all_r),
            "board":          self._extract_response_value(board_r),
            "health":         self._extract_response_value(health_r),
            "compile_time":   self._extract_response_value(ct_r),
            "protocol":       self._extract_response_value(proto_r),
            "xp_size":        self._extract_response_value(size_r),
            "network_status": ip_info or self._extract_response_value(net_r),
            "capabilities":   caps,
            "input_count":    caps.get("inputs", 4),
            "video_output_count": caps.get("video_outputs", 2),
            "audio_output_count": caps.get("audio_outputs", 3),
            "current_status": "Online",
        }

    # ─────────────────────────────────────────────────────────────────────
    #  send_command  – full parity with UCX plugin structure
    # ─────────────────────────────────────────────────────────────────────

    def send_command(self, ip: str, port, display_id, command: str, params: dict = None):  # noqa: C901
        params = params or {}
        base   = (command or "").split(":", 1)[0].strip()

        inp    = _safe_int(params.get("input")  or params.get("inp"),  1)
        out    = _safe_int(params.get("output") or params.get("out"),  1)
        layer  = _validate_layer(params.get("layer", "V"))
        pin    = _safe_int(params.get("pin"), 0)

        try:
            # ── Simple query commands ──────────────────────────────────────
            if base in self.QUERY_COMMANDS:
                # Allow layer override for get_route / get_xp_size
                lw2_cmd = self.QUERY_COMMANDS[base]
                if base in ("get_route", "get_xp_size"):
                    lw2_cmd = f"{lw2_cmd.split()[0]} {layer}"
                if base in ("get_video_autoselect",):
                    lw2_cmd = f"AS_V{out}=?"
                if base in ("get_audio_autoselect",):
                    lw2_cmd = f"AS_A{out}=?"
                result = self._send_lw2(ip, port, lw2_cmd)
                return result["success"], self._extract_response_value(result) or result.get("error")

            # ── Video / Audio / AV switch ──────────────────────────────────
            if base == "switch_video":
                result = self._send_lw2(ip, port, f"{inp}@{out} V")
                return result["success"], {
                    "command": base, "input": inp, "output": out, "layer": "V",
                    "response": self._extract_response_value(result),
                }

            if base == "switch_audio":
                result = self._send_lw2(ip, port, f"{inp}@{out} A")
                return result["success"], {
                    "command": base, "input": inp, "output": out, "layer": "A",
                    "response": self._extract_response_value(result),
                }

            if base == "switch_av":
                result = self._send_lw2(ip, port, f"{inp}@{out} AV")
                return result["success"], {
                    "command": base, "input": inp, "output": out, "layer": "AV",
                    "response": self._extract_response_value(result),
                }

            # ── Output mute / unmute ───────────────────────────────────────
            # LW2: {#<out> <layer>} = mute, {+<out> <layer>} = unmute
            if base == "mute_output":
                result = self._send_lw2(ip, port, f"#{out} {layer}")
                return result["success"], {
                    "command": base, "output": out, "layer": layer, "muted": True,
                    "response": self._extract_response_value(result),
                }

            if base == "unmute_output":
                result = self._send_lw2(ip, port, f"+{out} {layer}")
                return result["success"], {
                    "command": base, "output": out, "layer": layer, "muted": False,
                    "response": self._extract_response_value(result),
                }

            # ── Output lock / unlock ───────────────────────────────────────
            # LW2: {#><out> <layer>} = lock, {+<<out> <layer>} = unlock
            if base == "lock_output":
                result = self._send_lw2(ip, port, f"#>{out} {layer}")
                return result["success"], {
                    "command": base, "output": out, "layer": layer, "locked": True,
                    "response": self._extract_response_value(result),
                }

            if base == "unlock_output":
                result = self._send_lw2(ip, port, f"+<{out} {layer}")
                return result["success"], {
                    "command": base, "output": out, "layer": layer, "locked": False,
                    "response": self._extract_response_value(result),
                }

            # ── Mute / unmute all video outputs ───────────────────────────
            if base == "mute_all_outputs":
                caps  = _detect_caps(params.get("model") or "")
                n_out = caps.get("video_outputs", 2)
                for i in range(1, n_out + 1):
                    self._send_lw2(ip, port, f"#{i} V")
                return True, {"command": base, "outputs_affected": n_out, "layer": "V"}

            if base == "unmute_all_outputs":
                caps  = _detect_caps(params.get("model") or "")
                n_out = caps.get("video_outputs", 2)
                for i in range(1, n_out + 1):
                    self._send_lw2(ip, port, f"+{i} V")
                return True, {"command": base, "outputs_affected": n_out, "layer": "V"}

            # ── Mute / unmute all audio outputs ───────────────────────────
            if base == "mute_all_audio_outputs":
                caps  = _detect_caps(params.get("model") or "")
                n_out = caps.get("audio_outputs", 3)
                for i in range(1, n_out + 1):
                    self._send_lw2(ip, port, f"#{i} A")
                return True, {"command": base, "outputs_affected": n_out, "layer": "A"}

            if base == "unmute_all_audio_outputs":
                caps  = _detect_caps(params.get("model") or "")
                n_out = caps.get("audio_outputs", 3)
                for i in range(1, n_out + 1):
                    self._send_lw2(ip, port, f"+{i} A")
                return True, {"command": base, "outputs_affected": n_out, "layer": "A"}

            # ── Autoselect video ───────────────────────────────────────────
            # {AS_V<out>=<E|D>;<F|L|P>}
            if base == "set_video_autoselect":
                state = _validate_autoselect_state(params.get("state", "E"))
                mode  = _validate_autoselect_mode(params.get("mode", "P"))
                result = self._send_lw2(ip, port, f"AS_V{out}={state};{mode}")
                return result["success"], {
                    "command": base, "output": out, "state": state, "mode": mode,
                    "response": self._extract_response_value(result),
                }

            if base == "get_video_autoselect":
                result = self._send_lw2(ip, port, f"AS_V{out}=?")
                return result["success"], {
                    "command": base, "output": out,
                    "response": self._extract_response_value(result),
                }

            # ── Autoselect audio ───────────────────────────────────────────
            # {AS_A<out>=<E|D>;<F|L|P>}
            if base == "set_audio_autoselect":
                state = _validate_autoselect_state(params.get("state", "E"))
                mode  = _validate_autoselect_mode(params.get("mode", "P"))
                result = self._send_lw2(ip, port, f"AS_A{out}={state};{mode}")
                return result["success"], {
                    "command": base, "output": out, "state": state, "mode": mode,
                    "response": self._extract_response_value(result),
                }

            if base == "get_audio_autoselect":
                result = self._send_lw2(ip, port, f"AS_A{out}=?")
                return result["success"], {
                    "command": base, "output": out,
                    "response": self._extract_response_value(result),
                }

            # ── Input priorities ───────────────────────────────────────────
            # {PRIO_V<out>=<p1>;<p2>;<p3>;<p4>}   all 4 inputs required
            # {PRIO_A<out>=<p1>;<p2>;<p3>}         all 3 audio inputs required
            if base == "set_video_priority":
                priorities = params.get("priorities") or params.get("priority", "")
                if not priorities:
                    return False, {"command": base, "error": "param 'priorities' required e.g. '1;0;2;3'"}
                result = self._send_lw2(ip, port, f"PRIO_V{out}={priorities}")
                return result["success"], {
                    "command": base, "output": out, "priorities": priorities,
                    "response": self._extract_response_value(result),
                }

            if base == "get_video_priority":
                result = self._send_lw2(ip, port, f"PRIO_V{out}=?")
                return result["success"], {
                    "command": base, "output": out,
                    "response": self._extract_response_value(result),
                }

            if base == "set_audio_priority":
                priorities = params.get("priorities") or params.get("priority", "")
                if not priorities:
                    return False, {"command": base, "error": "param 'priorities' required e.g. '1;0;2'"}
                result = self._send_lw2(ip, port, f"PRIO_A{out}={priorities}")
                return result["success"], {
                    "command": base, "output": out, "priorities": priorities,
                    "response": self._extract_response_value(result),
                }

            if base == "get_audio_priority":
                result = self._send_lw2(ip, port, f"PRIO_A{out}=?")
                return result["success"], {
                    "command": base, "output": out,
                    "response": self._extract_response_value(result),
                }

            # ── Network ───────────────────────────────────────────────────
            if base == "get_network":
                result = self._send_lw2(ip, port, "IP_STAT=?")
                ip_info = self._parse_ip_stat(self._extract_response_value(result) or "")
                return result["success"], {
                    "command": base,
                    "network": ip_info,
                    "raw": self._extract_response_value(result),
                }

            if base == "set_static_ip":
                ipaddr  = params.get("ipaddr")  or params.get("ip_address") or ""
                subnet  = params.get("subnet")  or params.get("mask")       or ""
                gateway = params.get("gateway") or ""
                if not ipaddr or not subnet:
                    return False, {"command": base, "error": "params 'ipaddr' and 'subnet' are required"}

                # Stage all three, then apply
                r_ip  = self._send_lw2(ip, port, f"IP_ADDRESS=0;{ipaddr}")
                r_sub = self._send_lw2(ip, port, f"IP_NETMASK={subnet}")
                r_gw  = self._send_lw2(ip, port, f"IP_GATEWAY={gateway}") if gateway else {"success": True, "response": "skipped"}
                r_apl = self._send_lw2(ip, port, "IP_APPLY")

                success = all(r.get("success") for r in [r_ip, r_sub, r_apl])
                return success, {
                    "command": base, "ipaddr": ipaddr, "subnet": subnet, "gateway": gateway,
                    "ip_result":      self._extract_response_value(r_ip),
                    "subnet_result":  self._extract_response_value(r_sub),
                    "gateway_result": self._extract_response_value(r_gw),
                    "apply_result":   self._extract_response_value(r_apl),
                    "applied": success,
                }

            if base == "enable_dhcp":
                # type=1 → DHCP
                r_ip  = self._send_lw2(ip, port, "IP_ADDRESS=1;0.0.0.0")
                r_apl = self._send_lw2(ip, port, "IP_APPLY")
                success = r_ip.get("success") and r_apl.get("success")
                return success, {
                    "command": base, "dhcp": True, "applied": success,
                    "apply_result": self._extract_response_value(r_apl),
                }

            if base == "disable_dhcp":
                # type=0 → static; caller must also call set_static_ip or apply_network
                ipaddr = params.get("ipaddr") or params.get("ip_address") or "192.168.0.100"
                result = self._send_lw2(ip, port, f"IP_ADDRESS=0;{ipaddr}")
                return result["success"], {
                    "command": base, "dhcp": False, "ipaddr": ipaddr,
                    "response": self._extract_response_value(result),
                    "note": "Call apply_network to activate the new setting.",
                }

            if base == "apply_network":
                result = self._send_lw2(ip, port, "IP_APPLY")
                return result["success"], {
                    "command": base,
                    "response": self._extract_response_value(result),
                }

            if base == "eth_enable":
                result = self._send_lw2(ip, port, "ETH_ENABLE=1")
                return result["success"], {
                    "command": base, "enabled": True,
                    "response": self._extract_response_value(result),
                }

            if base == "eth_disable":
                result = self._send_lw2(ip, port, "ETH_ENABLE=0")
                return result["success"], {
                    "command": base, "enabled": False,
                    "response": self._extract_response_value(result),
                    "warning": "Ethernet is now disabled; reconnect via serial or physical reset.",
                }

            # ── RS-232 ────────────────────────────────────────────────────
            if base == "get_rs232_mode":
                result = self._send_lw2(ip, port, "RS232=?")
                return result["success"], {
                    "command": base, "response": self._extract_response_value(result),
                }

            if base == "set_rs232_mode":
                mode = str(params.get("mode", "CONTROL")).upper()
                if mode not in ("PASS", "CONTROL", "CI"):
                    return False, {"command": base, "error": "mode must be PASS | CONTROL | CI"}
                result = self._send_lw2(ip, port, f"RS232={mode}")
                return result["success"], {
                    "command": base, "mode": mode,
                    "response": self._extract_response_value(result),
                }

            if base == "set_rs232_format":
                baud    = str(params.get("baud",    "X"))
                databit = str(params.get("databit", "X"))
                parity  = str(params.get("parity",  "X"))
                stopbit = str(params.get("stopbit", "X"))
                result = self._send_lw2(ip, port, f"RS232_LOCAL_FORMAT={baud};{databit};{parity};{stopbit}")
                return result["success"], {
                    "command": base, "baud": baud, "databit": databit,
                    "parity": parity, "stopbit": stopbit,
                    "response": self._extract_response_value(result),
                }

            if base == "get_rs232_format":
                result = self._send_lw2(ip, port, "RS232_LOCAL_FORMAT=?")
                return result["success"], {
                    "command": base, "response": self._extract_response_value(result),
                }

            # ── GPIO ──────────────────────────────────────────────────────
            # {GPIO<pin>=<I|O>;<H|L|T>}  pin 0–6
            if base == "set_gpio":
                direction = str(params.get("direction", "O")).upper()
                level     = str(params.get("level", "H")).upper()
                if direction not in ("I", "O"):
                    return False, {"command": base, "error": "direction must be I (input) or O (output)"}
                if level not in ("H", "L", "T"):
                    return False, {"command": base, "error": "level must be H (high), L (low), or T (toggle)"}
                if not (0 <= pin <= 6):
                    return False, {"command": base, "error": "pin must be 0–6"}
                result = self._send_lw2(ip, port, f"GPIO{pin}={direction};{level}")
                return result["success"], {
                    "command": base, "pin": pin, "direction": direction, "level": level,
                    "response": self._extract_response_value(result),
                }

            if base == "get_gpio":
                if not (0 <= pin <= 6):
                    return False, {"command": base, "error": "pin must be 0–6"}
                result = self._send_lw2(ip, port, f"GPIO{pin}=?")
                return result["success"], {
                    "command": base, "pin": pin,
                    "response": self._extract_response_value(result),
                }

            # ── System ────────────────────────────────────────────────────
            if base == "reboot":
                self._send_lw2(ip, port, "RST")          # no response expected
                return True, {"command": base, "note": "No response is sent after reboot."}

            if base == "factory_reset":
                result = self._send_lw2(ip, port, "FACTORY=ALL")
                return result["success"], {
                    "command": base,
                    "response": self._extract_response_value(result),
                }

            # ── Raw passthrough ───────────────────────────────────────────
            if base == "raw":
                raw_cmd = params.get("command") or params.get("cmd") or ""
                if not raw_cmd:
                    return False, {"command": base, "error": "param 'command' required"}
                result = self._send_lw2(ip, port, raw_cmd)
                return result["success"], {
                    "command": base, "sent": raw_cmd,
                    "response": self._extract_response_value(result),
                }

            return False, f"Unsupported command: {command}"

        except Exception as exc:
            return False, {"command": command, "error": str(exc)}

    # ─────────────────────────────────────────────────────────────────────
    #  query_status  – mirrors UCX plugin's output shape
    # ─────────────────────────────────────────────────────────────────────

    def query_status(self, ip: str, port=10001, display_id=None) -> dict:
        results = self._send_many(ip, port, [
            "VC V",       # video crosspoint state
            "VC A",       # audio crosspoint state
            "ST",         # health (voltages + temps)
            "IP_STAT=?",  # network
            "i",          # model
            "S",          # serial
            "F",          # firmware
        ])
        v_r, a_r, h_r, net_r, model_r, sn_r, fw_r = results

        reachable = v_r.get("success") or h_r.get("success")

        raw_model = self._extract_response_value(model_r) or ""
        model     = raw_model.replace("I:", "").strip()
        serial    = (self._extract_response_value(sn_r) or "").replace("SN:", "").strip()
        firmware  = (self._extract_response_value(fw_r) or "").replace("FW:", "").strip()
        caps      = _detect_caps(model)
        ip_info   = self._parse_ip_stat(self._extract_response_value(net_r) or "")

        return {
            "make":          "Lightware",
            "model_family":  "MMX",
            "model":         model or None,
            "serial_number": serial or None,
            "firmware":      firmware or None,
            "reachable":     reachable,
            "current_status": "Online" if reachable else "Offline",
            # crosspoint state – "ALLV 01 02" / "ALLA 02 02 02"
            "video_route":   self._extract_response_value(v_r),
            "audio_route":   self._extract_response_value(a_r),
            "health":        self._extract_response_value(h_r),
            "network":       ip_info,
            "capabilities":  caps,
            "input_count":   caps.get("inputs", 4),
            "video_output_count": caps.get("video_outputs", 2),
            "audio_output_count": caps.get("audio_outputs", 3),
            "error": (
                v_r.get("error") or a_r.get("error") or h_r.get("error")
            ),
        }