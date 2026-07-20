
"""
Manual Platform Plugin: LG55EF5GLPlugin
"""

import socket
import json
import threading
import time
import re
import asyncio
import subprocess
import platform
import requests
import xml.etree.ElementTree as ET

from .base import ManualPlatformPlugin


class LG55EF5GLPlugin(ManualPlatformPlugin):
    """LG 55EF5GL Display plugin with control support over TCP 9761."""

    name = "lg_55ef5gl"
    display_name = "LG 55EF5GL Display"
    description = "LG 55EF5GL Display (IP + Set ID) with control"
    supports_display_id = True  # Reused as Set ID in UI
    supports_port = False
    default_port = 9761
    SUPPORTED_MODELS = ["55EF5GL Display"]

    COMMANDS = {
        "power_on": ("ka", "01"),
        "power_off": ("ka", "00"),
        "hdmi1": ("xb", "90"),
        "hdmi2": ("xb", "91"),
        "hdmi3": ("xb", "92"),
        "hdmi4": ("xb", "93"),
        "mute_on": ("ke", "01"),
        "mute_off": ("ke", "00"),
    }

    QUERY_COMMANDS = {
        "serial": "fy",
        "sw_version": "fz",
        "temperature": "dn",
        "power": "ka",
        "input": "xb",
        "volume": "kf",
        "mute": "ke",
    }

    def _parse_set_id(self, display_id):
        try:
            if display_id in (None, "", "00"):
                return 1
            return int(str(display_id), 16) if str(display_id).lower().startswith("0x") else int(str(display_id))
        except Exception:
            return 1

    def _build_cmd(self, cmd, set_id, value):
        return f"{cmd} {set_id:02d} {value}\r".encode()

    def _send_raw(self, ip, port, payload):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((ip, port))
            sock.sendall(payload)
            time.sleep(0.12)
            data = sock.recv(256).decode(errors="ignore").strip()
            sock.close()
            return data
        except Exception:
            return None

    def _query(self, ip, port, set_id, cmd):
        raw = self._send_raw(ip, port, self._build_cmd(cmd, set_id, "FF"))
        if raw and "OK" in raw:
            return raw.split("OK")[-1].replace("x", "").strip()
        return None

    def get_device_info(self, ip, port=9761, display_id=None):
        set_id = self._parse_set_id(display_id)
        serial = self._query(ip, port, set_id, self.QUERY_COMMANDS["serial"])
        firmware = self._query(ip, port, set_id, self.QUERY_COMMANDS["sw_version"])

        status = "Online" if (serial or firmware) else "Offline"
        device_name = "LG 55EF5GL Display"

        return {
            "ip_address": ip,
            "port": port,
            "display_id": str(set_id),
            "make": "LG",
            "device_name": device_name,
            "model": "55EF5GL Display",
            "serial_number": serial or None,
            "firmware": firmware or None,
            "device_type": "LG Display",
            "current_status": status,
        }

    def send_command(self, ip, port, display_id, command):
        if command not in self.COMMANDS:
            return False, f"Unknown command: {command}"

        set_id = self._parse_set_id(display_id)
        cmd, value = self.COMMANDS[command]
        raw = self._send_raw(ip, int(port or self.default_port), self._build_cmd(cmd, set_id, value))
        if raw is None:
            return False, "No response from device"
        return True, f"Command sent ({command})"

    def query_status(self, ip, port=9761, display_id="1"):
        set_id = self._parse_set_id(display_id)
        status = {
            "serial_number": self._query(ip, port, set_id, self.QUERY_COMMANDS["serial"]),
            "firmware": self._query(ip, port, set_id, self.QUERY_COMMANDS["sw_version"]),
            "power_raw": self._query(ip, port, set_id, self.QUERY_COMMANDS["power"]),
            "input_raw": self._query(ip, port, set_id, self.QUERY_COMMANDS["input"]),
            "volume_raw": self._query(ip, port, set_id, self.QUERY_COMMANDS["volume"]),
            "mute_raw": self._query(ip, port, set_id, self.QUERY_COMMANDS["mute"]),
        }
        temp_hex = self._query(ip, port, set_id, self.QUERY_COMMANDS["temperature"])
        if temp_hex:
            try:
                status["temperature_f"] = int(temp_hex, 16)
            except Exception:
                status["temperature_f"] = None

        # Friendly conversions for UI / DB
        def _power(val):
            if not val:
                return None
            return "ON" if val.strip().endswith("1") else "OFF"

        INPUT_MAP = {
            "90": "HDMI 1", "91": "HDMI 2", "92": "HDMI 3", "93": "HDMI 4",
            "90x": "HDMI 1", "91x": "HDMI 2", "92x": "HDMI 3", "93x": "HDMI 4",
        }

        def _input(val):
            if not val:
                return None
            v = val.replace("x", "").strip()
            return INPUT_MAP.get(v, v)

        def _volume(val):
            if val is None:
                return None
            try:
                return int(val, 16)
            except Exception:
                try:
                    return int(val)
                except Exception:
                    return None

        def _mute(val):
            if not val:
                return None
            return "ON" if val.strip().endswith("1") else "OFF"

        friendly = {
            "power": _power(status.pop("power_raw")),
            "input": _input(status.pop("input_raw")),
            "volume": _volume(status.pop("volume_raw")),
            "mute": _mute(status.pop("mute_raw")),
        }
        status.update(friendly)
        status["reachable"] = bool(status.get("serial_number") or status.get("firmware"))
        return status
