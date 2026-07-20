
"""
Kramer VIA Platform Plugin for RMM System

Kramer VIA (Connect 2) control using XML-over-Telnet API.
Supports device discovery, status monitoring, and control commands.
"""

import json
import platform
import re
import socket
import subprocess
import telnetlib
import time
from xml.sax.saxutils import escape

from .base import ManualPlatformPlugin


class KramerVIAPlugin(ManualPlatformPlugin):
    """Kramer Connect 2 / VIA plugin with comprehensive status and control support."""

    name = "kramer_via"
    display_name = "Kramer VIA"
    description = "Kramer Connect 2 (VIA) devices - Collaboration solution"
    supports_display_id = False
    supports_port = True
    default_port = 9982
    
    SUPPORTED_MODELS = ["Connect 2 (VIA)", "VIA", "Kramer VIA", "VIA Connect 2"]
    
    KRAMER_OUIS = {
        "00-1D-56", "00-0C-65", "00-13-89", "00-1D-57",
        "00-1D-58", "00-1D-59", "00-10-56", "F4-6A-DD"
    }

    # Available commands for the UI
    COMMANDS = {
        "refresh_status": "Refresh Status",
        "get_device_info": "Get Device Information",
        "get_network_info": "Get Network Information",
        "get_participants": "Get Participant List",
        "get_room_info": "Get Room Information",
        "get_volume": "Get Volume",
        "set_volume": "Set Volume",
        "start_presentation": "Start Presentation",
        "stop_presentation": "Stop Presentation",
        "deny_presentation": "Deny Presentation",
        "screenshare_on": "Enable Screen Sharing",
        "screenshare_off": "Disable Screen Sharing",
        "enable_log_mode": "Enable Log Mode",
        "disable_log_mode": "Disable Log Mode",
        "wake_display": "Wake Display",
        "sleep_display": "Sleep Display",
        "reboot": "Reboot Device",
        "get_room_code": "Get Room Code",
        "get_participant_count": "Get Participant Count",
    }

    def __init__(self, config=None):
        super().__init__(config)
        self.username = self.config.get("username") or self.config.get("user") 
        self.password = self.config.get("password") 
        self.timeout = int(self.config.get("timeout") or 5)
        self.port = int(self.config.get("port") or self.default_port)
        self._resolved_ports = {}

    def _control_port(self, port=None):
        """Get the control port"""
        try:
            p = int(port or self.port or self.config.get("port") or self.default_port)
        except (TypeError, ValueError):
            p = self.default_port
        return p or self.default_port

    def _candidate_ports(self, port=None):
        """Return likely control ports, ordered by preference."""
        candidates = []

        requested = None
        try:
            requested = int(port) if port not in (None, "") else None
        except (TypeError, ValueError):
            requested = None

        configured = None
        try:
            configured = int(self.config.get("port") or self.port or self.default_port)
        except (TypeError, ValueError):
            configured = self.default_port

        default = int(self.default_port)

        # `1515` is a common generic placeholder in this project, but VIA usually
        # answers on `9982`, so prefer the VIA port before retrying the placeholder.
        preferred = [default, configured] if requested == 1515 else [requested, configured, default]
        if requested == 1515:
            preferred.append(requested)

        for candidate in preferred:
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        return candidates or [default]

    def _resolve_active_port(self, ip, port=None):
        """Resolve the live VIA control port, caching successful results per IP."""
        cached = self._resolved_ports.get(ip)
        if cached and self._socket_open(ip, cached):
            return cached

        for candidate in self._candidate_ports(port):
            if self._socket_open(ip, candidate):
                self._resolved_ports[ip] = candidate
                return candidate

        fallback = self._control_port(port)
        self._resolved_ports[ip] = fallback
        return fallback

    def _ping_host(self, ip):
        """Check if host is reachable via ping"""
        param = "-n" if platform.system().lower() == "windows" else "-c"
        try:
            result = subprocess.run(
                ["ping", param, "1", ip],
                capture_output=True,
                timeout=3
            )
            return result.returncode == 0
        except Exception:
            return False

    def _socket_open(self, ip, port, timeout=1.5):
        """Check if TCP port is open"""
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True
        except Exception:
            return False

    def _get_mac_address_from_arp(self, ip):
        """Get MAC address from ARP table"""
        try:
            if platform.system().lower() == "windows":
                output = subprocess.check_output(
                    f"arp -a {ip}",
                    shell=True,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                ).decode(errors="ignore")
            else:
                output = subprocess.check_output(
                    ["arp", "-n", ip],
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                ).decode(errors="ignore")
            match = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", output, re.IGNORECASE)
            if match:
                return match.group(0).upper().replace(":", "-")
        except Exception:
            pass
        return None

    def _get_vendor(self, mac_address):
        """Get vendor from MAC address"""
        if mac_address:
            prefix = mac_address[:8].upper().replace(":", "-")
            if prefix in self.KRAMER_OUIS:
                return "Kramer Electronics Ltd."
        return "Unknown Vendor"

    def _build_xml(self, cmd, params=None):
        """Build XML command for VIA device"""
        params = params or []
        parts = [
            "<P>",
            f"<UN>{escape(str(self.username))}</UN>",
            f"<Pwd>{escape(str(self.password))}</Pwd>",
            f"<Cmd>{escape(str(cmd))}</Cmd>",
        ]
        for idx in range(10):
            value = params[idx] if idx < len(params) else ""
            parts.append(f"<P{idx + 1}>{escape(str(value))}</P{idx + 1}>")
        parts.append("</P>")
        return "".join(parts)

    def _send_command(self, ip, cmd, params=None, port=None, delay=0.35, login=True):
        """Send command to VIA device via Telnet"""
        control_port = self._control_port(port)
        tn = None
        try:
            tn = telnetlib.Telnet(ip, control_port, self.timeout)
            if login and cmd != "Login":
                tn.write(self._build_xml("Login").encode() + b"\r\n")
                time.sleep(0.15)
                tn.read_very_eager()
            tn.write(self._build_xml(cmd, params).encode() + b"\r\n")
            time.sleep(delay)
            return tn.read_very_eager().decode(errors="ignore").strip()
        except Exception as e:
            return ""
        finally:
            if tn:
                tn.close()

    def _safe_query(self, ip, cmd, params=None, port=None, delay=0.35):
        """Safely query device without throwing exceptions"""
        try:
            return self._send_command(ip, cmd, params=params, port=port, delay=delay)
        except Exception:
            return ""

    def _last_pipe_value(self, response):
        """Extract last value from pipe-separated response"""
        if not response:
            return None
        text = re.sub(r"<[^>]+>", "", str(response)).strip()
        parts = [p.strip() for p in text.split("|") if p.strip()]
        value = parts[-1] if parts else text
        if value and value.upper() in {"ERR", "ERROR", "FAILED", "N/A", "NULL", "NONE"}:
            return None
        return value or None

    def _parse_ip_info(self, response):
        """Parse IP information from response"""
        info = {}
        if not response:
            return info
        for part in str(response).split("|"):
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            clean_key = re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")
            info[clean_key or key.strip()] = value.strip()
        return info

    def _normalize_serial(self, value):
        """Normalize serial values and drop empty/placeholder responses."""
        serial = self._last_pipe_value(value)
        if not serial:
            return None
        serial = re.sub(r"\s+", "", serial)
        if serial.upper() in {"N/A", "NA", "UNKNOWN", "NULL", "NONE"}:
            return None
        if self._looks_like_mac(serial):
            return self._serial_from_mac(serial)
        return serial

    def _looks_like_mac(self, value):
        """Return True when a value is a MAC address, not a true serial number."""
        if not value:
            return False

        text = str(value).strip()
        if re.fullmatch(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}", text):
            return True

        compact = re.sub(r"[^0-9A-Fa-f]", "", text)
        return bool(re.fullmatch(r"[0-9A-Fa-f]{12}", compact))

    def _serial_from_mac(self, value):
        """Kramer VIA commonly exposes serial as the Ethernet MAC without separators."""
        if not value:
            return None
        compact = re.sub(r"[^0-9A-Fa-f]", "", str(value))
        if re.fullmatch(r"[0-9A-Fa-f]{12}", compact):
            return compact.upper()
        return None

    def _parse_volume(self, response):
        """Parse volume from response"""
        match = re.search(r"Vol\|Get\|(\d+)", str(response or ""))
        if match:
            return int(match.group(1))
        value = self._last_pipe_value(response)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _parse_participant_count(self, response):
        """Parse participant count from response"""
        matches = re.findall(r"\b\d+\b", str(response or ""))
        return int(matches[-1]) if matches else 0

    def _parse_participants(self, response):
        """Parse participant list from response"""
        if not response:
            return []
        parts = str(response).split("|")
        raw = parts[3] if len(parts) >= 4 else parts[-1]
        return [user.strip() for user in raw.split("#") if user.strip()]

    def _parse_mode(self, response):
        """Parse ON/OFF mode from response"""
        value = self._last_pipe_value(response)
        if value == "1":
            return "ON"
        if value == "0":
            return "OFF"
        return value

    def _success_result(self, command, response, extra=None):
        """Format success result"""
        payload = {"command": command, "raw": response}
        if extra:
            payload.update(extra)
        return True, payload

    def get_device_info(self, ip, port=9982, display_id=None):
        """Get device information for discovery"""
        control_port = self._resolve_active_port(ip, port)
        telnet_available = self._socket_open(ip, control_port)
        is_online = self._ping_host(ip) or telnet_available
        
        status = self.query_status(ip, control_port, display_id) if is_online else {}
        mac = status.get("mac_address") or self._get_mac_address_from_arp(ip)
        serial = status.get("serial_number") or self._serial_from_mac(mac)
        model = status.get("model") or "Connect 2 (VIA)"
        device_name = status.get("room_name") or status.get("device_name") or model

        return {
            "ip_address": ip,
            "port": control_port,
            "display_id": display_id,
            "make": "Kramer",
            "device_name": device_name,
            "model": model,
            "serial_number": serial,
            "mac_address": mac,
            "firmware": status.get("firmware"),
            "vendor": self._get_vendor(mac),
            "open_ports": [control_port] if telnet_available else [],
            "device_type": "Kramer VIA Collaboration Device",
            "current_status": "Online" if is_online else "Offline",
        }

    def send_command(self, ip, port=9982, display_id=None, command=None, params=None):
        """Send a command to the Kramer VIA device"""
        params = params or {}
        if isinstance(command, dict):
            params = command.get("params") or params
            command = command.get("action")
        
        command = str(command or "").strip()
        control_port = self._resolve_active_port(ip, port)

        try:
            # Status and info commands
            if command in ("refresh_status", "get_status", "query_status"):
                return True, self.query_status(ip, control_port, display_id)
            
            if command == "get_device_info":
                status = self.query_status(ip, control_port, display_id)
                return True, {
                    "device_info": {
                        "firmware": status.get("firmware"),
                        "serial_number": status.get("serial_number"),
                        "mac_address": status.get("mac_address"),
                        "model": status.get("model", "Connect 2 (VIA)"),
                        "room_name": status.get("room_name"),
                    }
                }
            
            if command == "get_network_info":
                response = self._safe_query(ip, "IpInfo", port=control_port)
                ip_info = self._parse_ip_info(response)
                return True, {"network_info": ip_info}
            
            if command == "get_participants":
                response = self._safe_query(ip, "PList", ["all", "3"], port=control_port)
                participants = self._parse_participants(response)
                return True, {
                    "participants": participants,
                    "participant_count": len(participants)
                }
            
            if command == "get_participant_count":
                response = self._safe_query(ip, "PList", ["cnt", "3"], port=control_port)
                count = self._parse_participant_count(response)
                return True, {"participant_count": count}
            
            if command == "get_room_info":
                room_name = self._safe_query(ip, "RName", ["Get", "Name"], port=control_port)
                room_code = self._safe_query(ip, "RCode", ["Get", "Code"], port=control_port)
                volume = self._safe_query(ip, "Vol", ["Get"], port=control_port)
                return True, {
                    "room_name": self._last_pipe_value(room_name),
                    "room_code": self._last_pipe_value(room_code),
                    "volume": self._parse_volume(volume)
                }
            
            if command == "get_room_code":
                response = self._safe_query(ip, "RCode", ["Get", "Code"], port=control_port)
                return True, {"room_code": self._last_pipe_value(response)}
            
            if command == "get_volume":
                response = self._safe_query(ip, "Vol", ["Get"], port=control_port)
                volume = self._parse_volume(response)
                return True, {"volume": volume}
            
            if command == "set_volume":
                level = params.get("level") or params.get("volume") or params.get("value")
                if level is None:
                    return False, {"error": "volume level is required"}
                level = max(0, min(100, int(level)))
                response = self._send_command(ip, "Vol", ["Set", str(level)], port=control_port)
                refreshed = self.query_status(ip, control_port, display_id)
                return True, {
                    "volume": refreshed.get("volume", level),
                    "message": f"Volume set to {level}%",
                    "status": refreshed,
                }
            
            # Presentation control
            if command == "start_presentation":
                username = params.get("username") or params.get("user")
                if not username:
                    return False, {"error": "username is required"}
                response = self._send_command(ip, "DisplayStatus", ["Set", username, "1"], port=control_port)
                return True, {"username": username, "presentation": "started"}
            
            if command == "stop_presentation":
                username = params.get("username") or params.get("user")
                if not username:
                    return False, {"error": "username is required"}
                response = self._send_command(ip, "DisplayStatus", ["Set", username, "0"], port=control_port)
                return True, {"username": username, "presentation": "stopped"}
            
            if command == "deny_presentation":
                username = params.get("username") or params.get("user")
                if not username:
                    return False, {"error": "username is required"}
                response = self._send_command(ip, "DisplayStatus", ["Set", username, "2"], port=control_port)
                return True, {"username": username, "presentation": "denied"}
            
            # Screen sharing control
            if command == "screenshare_on":
                username = params.get("username", "")
                response = self._send_command(ip, "ScreenShare", ["On", username], port=control_port)
                return True, {"screen_share": "ON", "message": "Screen sharing enabled"}
            
            if command == "screenshare_off":
                username = params.get("username", "")
                response = self._send_command(ip, "ScreenShare", ["Off", username], port=control_port)
                return True, {"screen_share": "OFF", "message": "Screen sharing disabled"}
            
            # Log mode control
            if command == "enable_log_mode":
                response = self._send_command(ip, "Log", ["Set", "1"], port=control_port)
                refreshed = self.query_status(ip, control_port, display_id)
                return True, {"log_mode": refreshed.get("log_mode", "ON"), "message": "Log mode enabled", "status": refreshed}
            
            if command == "disable_log_mode":
                response = self._send_command(ip, "Log", ["Set", "0"], port=control_port)
                refreshed = self.query_status(ip, control_port, display_id)
                return True, {"log_mode": refreshed.get("log_mode", "OFF"), "message": "Log mode disabled", "status": refreshed}
            
            # Display control
            if command == "wake_display":
                response = self._send_command(ip, "WakeUp", ["1"], port=control_port)
                return True, {"display_awake": True, "message": "Display woken up"}
            
            if command == "sleep_display":
                response = self._send_command(ip, "WakeUp", ["0"], port=control_port)
                return True, {"display_awake": False, "message": "Display put to sleep"}
            
            # System commands
            if command == "reboot":
                response = self._send_command(ip, "Reboot", port=control_port, delay=0.2)
                return True, {"message": "Reboot command sent", "reachable": True}
            
            # Legacy command support
            if command in ("get_ip_info", "ip_info"):
                response = self._safe_query(ip, "IpInfo", port=control_port)
                return True, {"ip_info": self._parse_ip_info(response)}
            
            if command in ("get_version", "version"):
                response = self._safe_query(ip, "GetVersion", port=control_port)
                return True, {"firmware": self._last_pipe_value(response)}
            
            if command == "get_serial_number":
                response = self._safe_query(ip, "GetSerialNo", port=control_port)
                return True, {"serial_number": self._normalize_serial(response)}
            
            if command == "get_mac_address":
                response = self._safe_query(ip, "GetMacAdd", port=control_port)
                return True, {"mac_address": self._last_pipe_value(response)}
            
            if command == "get_log_mode":
                response = self._safe_query(ip, "Log", ["Get"], port=control_port)
                return True, {"log_mode": self._parse_mode(response)}
            
            if command == "get_auto_reboot":
                response = self._safe_query(ip, "AutoReboot", ["Get"], port=control_port)
                return True, {"auto_reboot": self._parse_mode(response)}
            
            return False, {"error": f"Unsupported command '{command}'"}
            
        except Exception as exc:
            return False, {"error": str(exc), "command": command}

    # def query_status(self, ip, port=9982, display_id=None):
    #     """Query comprehensive device status"""
    #     control_port = self._resolve_active_port(ip, port)
    #     telnet_available = self._socket_open(ip, control_port)
    #     reachable = self._ping_host(ip) or telnet_available
        
    #     status = {
    #         "reachable": reachable,
    #         "status": "Online" if reachable else "Offline",
    #         "power": "ON" if reachable else "OFF",
    #         "make": "Kramer",
    #         "model": "Connect 2 (VIA)",
    #         "telnet_port": control_port,
    #         "telnet_available": telnet_available,
    #         "ip_address": ip,
    #     }
        
    #     if not reachable:
    #         return status

    #     # Query all status information
    #     version_raw = self._safe_query(ip, "GetVersion", port=control_port)
    #     serial_raw = self._safe_query(ip, "GetSerialNo", port=control_port)
    #     mac_raw = self._safe_query(ip, "GetMacAdd", port=control_port)
    #     room_name_raw = self._safe_query(ip, "RName", ["Get", "Name"], port=control_port)
    #     volume_raw = self._safe_query(ip, "Vol", ["Get"], port=control_port)
    #     participants_count_raw = self._safe_query(ip, "PList", ["cnt", "3"], port=control_port)
    #     participants_raw = self._safe_query(ip, "PList", ["all", "3"], port=control_port)
    #     log_raw = self._safe_query(ip, "Log", ["Get"], port=control_port)
    #     auto_reboot_raw = self._safe_query(ip, "AutoReboot", ["Get"], port=control_port)
    #     ip_info_raw = self._safe_query(ip, "IpInfo", port=control_port)
    #     room_code_raw = self._safe_query(ip, "RCode", ["Get", "Code"], port=control_port)

    #     participants = self._parse_participants(participants_raw)
    #     ip_info = self._parse_ip_info(ip_info_raw)
    #     mac_address = self._last_pipe_value(mac_raw) or self._get_mac_address_from_arp(ip)
    #     serial_number = self._normalize_serial(serial_raw) or self._serial_from_mac(mac_address)
    #     room_name = self._last_pipe_value(room_name_raw)
    #     room_code = self._last_pipe_value(room_code_raw)

    #     status.update({
    #         "device_name": room_name or "Kramer VIA",
    #         "room_name": room_name,
    #         "room_code": room_code,
    #         "firmware": self._last_pipe_value(version_raw),
    #         "serial_number": serial_number,
    #         "mac_address": mac_address,
    #         "volume": self._parse_volume(volume_raw),
    #         "participant_count": self._parse_participant_count(participants_count_raw) or len(participants),
    #         "participants": participants,
    #         "log_mode": self._parse_mode(log_raw),
    #         "auto_reboot": self._parse_mode(auto_reboot_raw),
    #         "current_ip": ip_info.get("ip") or ip_info.get("ip_address") or ip,
    #         "ip_info": ip_info,
    #     })
        
    #     return status
    def query_status(self, ip, port=9982, display_id=None):
        """Query comprehensive device status"""
        control_port = self._resolve_active_port(ip, port)
        telnet_available = self._socket_open(ip, control_port)
        reachable = self._ping_host(ip) or telnet_available
        
        status = {
            "reachable": reachable,
            "status": "Online" if reachable else "Offline",
            "power": "ON" if reachable else "OFF",
            "make": "Kramer",
            "model": "Connect 2 (VIA)",
            "telnet_port": control_port,
            "telnet_available": telnet_available,
            "ip_address": ip,
        }
        
        if not reachable:
            return status

        # Query all status information
        version_raw = self._safe_query(ip, "GetVersion", port=control_port)
        serial_raw = self._safe_query(ip, "GetSerialNo", port=control_port)
        mac_raw = self._safe_query(ip, "GetMacAdd", port=control_port)
        room_name_raw = self._safe_query(ip, "RName", ["Get", "Name"], port=control_port)
        volume_raw = self._safe_query(ip, "Vol", ["Get"], port=control_port)
        participants_count_raw = self._safe_query(ip, "PList", ["cnt", "3"], port=control_port)
        participants_raw = self._safe_query(ip, "PList", ["all", "3"], port=control_port)
        log_raw = self._safe_query(ip, "Log", ["Get"], port=control_port)
        auto_reboot_raw = self._safe_query(ip, "AutoReboot", ["Get"], port=control_port)
        ip_info_raw = self._safe_query(ip, "IpInfo", port=control_port)
        room_code_raw = self._safe_query(ip, "RCode", ["Get", "Code"], port=control_port)

        participants = self._parse_participants(participants_raw)
        ip_info = self._parse_ip_info(ip_info_raw)
        mac_address = self._last_pipe_value(mac_raw) or self._get_mac_address_from_arp(ip)
        serial_number = self._normalize_serial(serial_raw) or self._serial_from_mac(mac_address)
        
        # Use IP address as room name (matches web interface header)
        room_name = ip
        room_code = self._last_pipe_value(room_code_raw)

        status.update({
            "device_name": room_name or "Kramer VIA",
            "room_name": room_name,
            "room_code": room_code,
            "firmware": self._last_pipe_value(version_raw),
            "serial_number": serial_number,
            "mac_address": mac_address,
            "volume": self._parse_volume(volume_raw),
            "participant_count": self._parse_participant_count(participants_count_raw) or len(participants),
            "participants": participants,
            "log_mode": self._parse_mode(log_raw),
            "auto_reboot": self._parse_mode(auto_reboot_raw),
            "current_ip": ip_info.get("ip") or ip_info.get("ip_address") or ip,
            "ip_info": ip_info,
        })
        
        return status

def run_plugin(ip, port=9982, display_id=None, command="get_status", params=None, config=None):
    """
    Entry point for the RMM system to execute plugin commands
    
    Args:
        ip: Device IP address
        port: Telnet port (default: 9982)
        display_id: Not used for VIA devices
        command: Command to execute
        params: Command parameters
        config: Plugin configuration
    
    Returns:
        Dictionary with command results
    """
    plugin = KramerVIAPlugin(config=config)
    
    if command in ("status", "get_status", "query_status", "refresh_status"):
        return plugin.query_status(ip, port, display_id)
    
    success, message = plugin.send_command(ip, port, display_id, command, params=params)
    
    return {
        "success": success,
        "message": message if isinstance(message, dict) else json.dumps(message)
    }




