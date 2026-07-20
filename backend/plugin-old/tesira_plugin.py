"""
TesiraPlugin — Final version.

Architecture:
  query_status()    → 1 SSH command  → called every 10s by poller   → ~200ms
  get_device_info() → 7 SSH commands → called ONCE on panel open     → ~1-2s (cached after)
  send_command()    → 1 SSH command  → every button press            → ~200ms

Key rules:
  - ONE persistent SSH session per device IP:port
  - Poller uses NON-BLOCKING lock → NEVER delays user commands
  - No fixed time.sleep() in command path
  - deviceModel parsed from nested +OK "info":{...}
  - info_cache: device info cached on session → panel open is instant after first load
"""

import json
import re
import threading
import time

import paramiko

from .base import ManualPlatformPlugin

# Timing constants
_FIRST_BYTE_TIMEOUT  = 4.0
_INTER_CHUNK_TIMEOUT = 0.15
_BANNER_IDLE_TIMEOUT = 0.8
_IDLE_TTL            = 180
_TERMINATORS         = ("+OK", "-ERR", "+DEVICE")


class _SessionEntry:
    def __init__(self, ssh, shell):
        self.ssh        = ssh
        self.shell      = shell
        self.lock       = threading.Lock()
        self.last_used  = time.monotonic()
        self.info_cache = None  # cached get_device_info result

    def alive(self):
        try:
            t = self.ssh.get_transport()
            return t is not None and t.is_active()
        except Exception:
            return False

    def close(self):
        for obj in (self.shell, self.ssh):
            try:
                obj.close()
            except Exception:
                pass


def _offline(ip, port, display_id, error):
    return {
        "ip_address": ip, "port": port, "display_id": display_id,
        "make": "Biamp", "device_type": "Tesira DSP",
        "current_status": "Offline", "reachable": False, "error": error,
    }


class TesiraPlugin(ManualPlatformPlugin):

    name                = "tesira"
    display_name        = "Biamp Tesira"
    description         = "Biamp Tesira DSP via SSH"
    supports_display_id = False
    supports_port       = False
    default_port        = 22

    SUPPORTED_MODELS = [
        "TesiraFORTE", "TesiraFORTE X", "Tesira SERVER",
        "Tesira SERVER-IO", "TesiraLUX", "TesiraAMP", "Voltera",
    ]

    COMMANDS = {
        "list_audio_blocks": {"description": "List aliases",       "params": []},
        "get_audio_level":   {"description": "Get level",          "params": [{"name":"tag","type":"str"},{"name":"channel","type":"str"}]},
        "set_audio_level":   {"description": "Set level",          "params": [{"name":"tag","type":"str"},{"name":"channel","type":"str"},{"name":"value_db","type":"str"}]},
        "mute_on":           {"description": "Mute channel",       "params": [{"name":"tag","type":"str"},{"name":"channel","type":"str"}]},
        "mute_off":          {"description": "Unmute channel",     "params": [{"name":"tag","type":"str"},{"name":"channel","type":"str"}]},
        "recall_preset":     {"description": "Recall preset",      "params": [{"name":"preset_number","type":"str"}]},
        "reboot":            {"description": "Reboot device",      "params": []},
        "start_audio":       {"description": "Start audio",        "params": []},
        "stop_audio":        {"description": "Stop audio",         "params": []},
        "raw_command":       {"description": "Raw Tesira command", "params": [{"name":"command","type":"str"}]},
    }

    QUERY_COMMANDS = {
        "device_info":  "get_device_info",
        "audio_blocks": "list_audio_blocks",
    }

    _pool      = {}
    _pool_lock = threading.Lock()

    # ── Fast recv ────────────────────────────────────────────────

    def _recv_until_done(self, shell, first_byte_timeout=_FIRST_BYTE_TIMEOUT,
                         inter_chunk_timeout=_INTER_CHUNK_TIMEOUT):
        output    = ""
        got_first = False
        deadline  = time.monotonic() + first_byte_timeout

        while True:
            if shell.recv_ready():
                chunk     = shell.recv(65535).decode(errors="ignore")
                output   += chunk
                got_first = True
                deadline  = time.monotonic() + inter_chunk_timeout
                for line in output.splitlines():
                    if any(line.strip().startswith(t) for t in _TERMINATORS):
                        return re.sub(r"[^\x20-\x7E\r\n]", "", output).strip()
            else:
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.02)

        return re.sub(r"[^\x20-\x7E\r\n]", "", output).strip()

    # ── Send one command ─────────────────────────────────────────

    def _send_command(self, shell, command):
        while shell.recv_ready():
            shell.recv(65535)
        shell.sendall((command + "\r\n").encode())
        raw     = self._recv_until_done(shell)
        cleaned = re.sub(r"[^\x20-\x7E\r\n]", "", raw.replace(command, "")).strip()
        print(f"[TESIRA] {command!r} -> {cleaned[:120]!r}")
        return cleaned

    # ── SSH connect + SESSION start ──────────────────────────────

    def _connect(self, ip, port, username, password):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, port=port, username=username, password=password,
                    timeout=self.timeout, look_for_keys=False, allow_agent=False)
        shell = ssh.invoke_shell()

        banner = self._recv_until_done(shell, first_byte_timeout=5.0,
                                       inter_chunk_timeout=_BANNER_IDLE_TIMEOUT)
        print(f"[TESIRA BANNER] {banner[:150]!r}")

        shell.sendall(b"\r\n")
        self._recv_until_done(shell, first_byte_timeout=0.5, inter_chunk_timeout=0.2)

        shell.sendall(b"SESSION start\r\n")
        resp = self._recv_until_done(shell, first_byte_timeout=4.0,
                                     inter_chunk_timeout=_BANNER_IDLE_TIMEOUT)
        print(f"[TESIRA SESSION] {resp[:150]!r}")
        return ssh, shell

    def _credentials(self):
        u = self.config.get("username")
        p = self.config.get("password")
        if not u or not p:
            raise ValueError("Tesira: username and password required in config")
        return u, p

    # ── Session pool ─────────────────────────────────────────────

    def _pool_key(self, ip, port):
        return f"{ip}:{port}"

    def _get_or_create_session(self, ip, port):
        key = self._pool_key(ip, port)
        username, password = self._credentials()

        with self._pool_lock:
            now  = time.monotonic()
            dead = [k for k, e in self._pool.items()
                    if not e.alive() or (now - e.last_used) > _IDLE_TTL]
            for k in dead:
                self._pool[k].close()
                del self._pool[k]
                print(f"[TESIRA POOL] Pruned: {k}")

            entry = self._pool.get(key)
            if entry and entry.alive():
                entry.last_used = now
                return entry

            print(f"[TESIRA POOL] New session -> {key}")
            ssh, shell = self._connect(ip, port, username, password)
            entry = _SessionEntry(ssh, shell)
            self._pool[key] = entry
            return entry

    def _invalidate_session(self, ip, port):
        key = self._pool_key(ip, port)
        with self._pool_lock:
            entry = self._pool.pop(key, None)
            if entry:
                entry.close()
                print(f"[TESIRA POOL] Invalidated: {key}")

    # ── _run: blocks until done (for user commands) ──────────────

    def _run(self, ip, port, command):
        for attempt in (1, 2):
            try:
                entry = self._get_or_create_session(ip, port)
                with entry.lock:
                    result = self._send_command(entry.shell, command)
                entry.last_used = time.monotonic()

                if "No existing session" in result:
                    print(f"[TESIRA] No session attempt {attempt}, reconnecting")
                    self._invalidate_session(ip, port)
                    if attempt == 2:
                        return result
                    continue
                return result

            except Exception as e:
                print(f"[TESIRA] _run error attempt {attempt}: {e}")
                self._invalidate_session(ip, port)
                if attempt == 2:
                    raise

    # ── _run_poll: NON-BLOCKING (for poller — never delays commands) ──

    def _run_poll(self, ip, port, command):
        """
        Tries to acquire the lock with 2s timeout.
        If a user command is running, returns None immediately.
        Poller gets skipped — it does NOT queue behind user commands.
        """
        try:
            entry    = self._get_or_create_session(ip, port)
            acquired = entry.lock.acquire(timeout=2.0)
            if not acquired:
                print(f"[TESIRA POLL] Skipped — command running on {ip}")
                return None
            try:
                result = self._send_command(entry.shell, command)
            finally:
                entry.lock.release()

            entry.last_used = time.monotonic()

            if "No existing session" in result:
                self._invalidate_session(ip, port)
                return None

            return result

        except Exception as e:
            print(f"[TESIRA POLL] Error: {e}")
            self._invalidate_session(ip, port)
            return None

    # ── Parse helpers ────────────────────────────────────────────

    def _parse_value(self, response, key):
        if not response:
            return None
        m = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]+)"', response)
        if m:
            return m.group(1)
        m = re.search(rf'"{re.escape(key)}"\s*:\s*([^\s"{{}},:]+)', response)
        if m:
            return m.group(1)
        return None

    def _parse_nested(self, response, outer_key, inner_key):
        """
        Handles:  +OK "info":{"deviceModel":"TesiraFORT VT" ...}
                  +OK "value":{"hostname":"..." "macAddress":"..." ...}
        """
        if not response:
            return None
        m = re.search(rf'"{re.escape(outer_key)}"\s*:\s*\{{([^}}]+)\}}', response)
        if not m:
            return None
        block = m.group(1)
        m2 = re.search(rf'"{re.escape(inner_key)}"\s*:\s*"([^"]+)"', block)
        if m2:
            return m2.group(1)
        m2 = re.search(rf'"{re.escape(inner_key)}"\s*:\s*([^\s"{{}},:]+)', block)
        if m2:
            return m2.group(1)
        return None

    def _infer_model_from_hostname(self, hostname):
        for pat, label in [
            (r"TesiraForteX",       "TesiraFORTE X"),
            (r"TesiraForte(?!X)",   "TesiraFORTE"),
            (r"TesiraServerIO",     "Tesira SERVER-IO"),
            (r"TesiraServer(?!IO)", "Tesira SERVER"),
            (r"TesiraLUX",          "TesiraLUX"),
            (r"Voltera",            "Voltera"),
            (r"TesiraAMP",          "TesiraAMP"),
        ]:
            if re.search(pat, hostname or "", re.IGNORECASE):
                return label
        return None

    # ── query_status — FAST, 1 command, poller path ──────────────

    def query_status(self, ip, port=22, display_id=None):
        """
        1 command only. Uses _run_poll so it never blocks user commands.
        Called every 10s by the frontend poller.
        Model / firmware NOT fetched here — see get_device_info().
        """
        try:
            resp = self._run_poll(ip, port, "DEVICE get networkStatus")

            if resp is None:
                # Lock was busy — keep last known online status
                return {"reachable": True, "poll_skipped": True}

            reachable = "+OK" in resp
            if not reachable:
                self._invalidate_session(ip, port)

            return {"reachable": reachable, "error": None}

        except Exception as e:
            self._invalidate_session(ip, port)
            return {"reachable": False, "error": str(e)}

    # ── get_device_info — 7 commands, once on panel open ─────────

    def get_device_info(self, ip, port=22, display_id=None):
        """
        Full device info. Called once when Tesira panel opens.
        Result is cached on the session entry — subsequent calls
        within the same session return instantly without SSH.
        """
        try:
            self._credentials()
        except ValueError as e:
            return _offline(ip, port, display_id, str(e))

        try:
            entry = self._get_or_create_session(ip, port)

            # Return cached result if session still alive
            if entry.info_cache is not None:
                return entry.info_cache

            with entry.lock:
                sh = entry.shell

                fw_resp   = self._send_command(sh, "DEVICE get version")
                ser_resp  = self._send_command(sh, "DEVICE get serialNumber")
                host_resp = self._send_command(sh, "DEVICE get hostname")
                net_resp  = self._send_command(sh, "DEVICE get networkStatus")
                flt_resp  = self._send_command(sh, "DEVICE get activeFaultList")

                firmware = self._parse_value(fw_resp,   "value")
                serial   = self._parse_value(ser_resp,  "value")
                hostname = self._parse_value(host_resp, "value")

                try:
                    major = int(str(firmware or "").split(".")[0])
                except (TypeError, ValueError):
                    major = 0

                if major >= 4:
                    di_resp = self._send_command(sh, "DEVICE get deviceInfo")
                    model = (
                        self._parse_nested(di_resp, "info", "deviceModel") or
                        self._parse_value(di_resp, "deviceModel") or
                        self._infer_model_from_hostname(hostname)
                    )
                else:
                    di_resp = ""
                    model   = self._infer_model_from_hostname(hostname)

                if not model:
                    pt_resp = self._send_command(sh, "DEVICE get partNumber")
                    model   = self._parse_value(pt_resp, "value")

                model = (model or
                         re.sub(r"\d{6,}$", "", hostname or "").strip() or
                         f"Tesira (fw {firmware})")

                alias_resp = self._send_command(sh, "SESSION get aliases")

            entry.last_used = time.monotonic()

            def nf(key):
                return (self._parse_nested(net_resp, "value", key) or
                        self._parse_value(net_resp, key))

            mac        = nf("macAddress")
            device_ip  = nf("ip") or ip
            fault_name = self._parse_value(flt_resp, "name")

            result = {
                "ip_address":             device_ip,
                "port":                   port,
                "display_id":             display_id,
                "make":                   "Biamp",
                "device_type":            "Tesira DSP",
                "device_name":            hostname or model or "Biamp Tesira",
                "model":                  model,
                "serial_number":          serial or mac,
                "firmware":               firmware,
                "hostname":               hostname,
                "mac_address":            mac,
                "subnet_mask":            nf("netmask"),
                "gateway":                nf("gateway"),
                "default_gateway_status": nf("defaultGatewayStatus"),
                "link_status":            nf("linkStatus"),
                "address_source":         nf("addressSource"),
                "telnet_enabled":         nf("telnetDisabled") == "false",
                "ssh_enabled":            nf("sshDisabled")    == "false",
                "mdns_enabled":           nf("mDNSEnabled")    == "true",
                "fault_status":           "No Faults" if fault_name in (
                                              "No fault", "No fault in device", None
                                          ) else fault_name,
                "reachable":              True,
                "raw_network":            net_resp,
                "raw_faults":             flt_resp,
                "raw_audio_blocks":       alias_resp,
            }

            entry.info_cache = result
            return result

        except Exception as e:
            self._invalidate_session(ip, port)
            return _offline(ip, port, display_id, str(e))

    # ── Command wrappers ─────────────────────────────────────────

    def list_audio_blocks(self, ip, port=22):
        return self._run(ip, port, "SESSION get aliases")

    def get_audio_level(self, ip, tag, channel, port=22):
        return self._run(ip, port, f"{tag} get level {channel}")

    def set_audio_level(self, ip, tag, channel, value_db, port=22):
        return self._run(ip, port, f"{tag} set level {channel} {value_db}")

    def mute_on(self, ip, tag, channel, port=22):
        return self._run(ip, port, f"{tag} set mute {channel} true")

    def mute_off(self, ip, tag, channel, port=22):
        return self._run(ip, port, f"{tag} set mute {channel} false")
    

    def recall_preset(self, ip, preset_number, port=22):
        return self._run(ip, port, f"DEVICE recallPreset {preset_number}")

    def reboot(self, ip, port=22):
        try:
            self._run(ip, port, "DEVICE reboot")
        finally:
            self._invalidate_session(ip, port)

    def start_audio(self, ip, port=22):
        return self._run(ip, port, "DEVICE startAudio")

    def stop_audio(self, ip, port=22):
        return self._run(ip, port, "DEVICE stopAudio")

    # ── send_command (entry point from device_control_routes.py) ─

    def _decode_command(self, command):
        if isinstance(command, dict):
            return command.get("action"), command.get("params") or {}
        if isinstance(command, str):
            s = command.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    p = json.loads(s)
                    if isinstance(p, dict):
                        return p.get("action"), p.get("params") or {}
                except Exception:
                    pass
            return s, {}
        return None, {}

    def send_command(self, ip, port, display_id, command, params=None):
        try:
            action, decoded_params = self._decode_command(command)  # ← different variable name
            # Merge: explicit params kwarg wins over anything decoded from command string
            p = {**(decoded_params or {}), **(params or {})}
            target_port = int(port or self.default_port)

            if action == "raw_command":
                cmd = p.get("command")
                if not cmd:
                    return False, "raw_command requires params.command"
                result = self._run(ip, target_port, cmd)
                if result and ("-ERR" in result or "No existing session" in result):
                    return False, result
                return True, result

            if action not in self.COMMANDS:
                return False, f"Unknown command: {action}"

            if action in {"get_audio_level", "set_audio_level", "mute_on", "mute_off"}:
                if not p.get("tag") or not p.get("channel"):
                    return False, f"{action} requires tag and channel"

            if action == "set_audio_level" and not p.get("value_db"):
                return False, "set_audio_level requires value_db"

            if action == "recall_preset" and not p.get("preset_number"):
                return False, "recall_preset requires preset_number"

            dispatch = {
                "list_audio_blocks": lambda: self.list_audio_blocks(ip, target_port),
                "get_audio_level":   lambda: self.get_audio_level(ip, p["tag"], p["channel"], target_port),
                "set_audio_level":   lambda: self.set_audio_level(ip, p["tag"], p["channel"], p["value_db"], target_port),
                "mute_on":           lambda: self.mute_on(ip,  p["tag"], p["channel"], target_port),
                "mute_off":          lambda: self.mute_off(ip, p["tag"], p["channel"], target_port),
                "recall_preset":     lambda: self.recall_preset(ip, p["preset_number"], target_port),
                "reboot":            lambda: self.reboot(ip, target_port),
                "start_audio":       lambda: self.start_audio(ip, target_port),
                "stop_audio":        lambda: self.stop_audio(ip, target_port),
            }

            result = dispatch[action]()

            if not result:
                return False, "Empty response from device"
            if "-ERR" in result or "No existing session" in result:
                return False, result
            return True, result

        except Exception as e:
            return False, str(e)




# """
# Manual Platform Plugin: TesiraPlugin
# """
 
# import json
# import re
# import time
 
# import paramiko
 
# from .base import ManualPlatformPlugin
 
 
# class TesiraPlugin(ManualPlatformPlugin):
#     """Biamp Tesira monitoring plugin over SSH."""
 
#     name = "tesira"
#     display_name = "Biamp Tesira"
#     description = "Biamp Tesira DSP devices via SSH"
#     supports_display_id = False
#     supports_port = False
#     default_port = 22
#     SUPPORTED_MODELS = [
#         "TesiraFORTE",
#         "TesiraFORTE X",
#         "Tesira SERVER",
#         "Tesira SERVER-IO",
#         "TesiraLUX",
#         "TesiraAMP",
#         "Voltera",
#     ]
 
#     COMMANDS = {
#         "list_audio_blocks": {"description": "List Tesira aliases / audio blocks", "params": []},
#         "get_audio_level": {
#             "description": "Get audio level for a tag/channel",
#             "params": [{"name": "tag", "type": "str"}, {"name": "channel", "type": "str"}],
#         },
#         "set_audio_level": {
#             "description": "Set audio level for a tag/channel",
#             "params": [
#                 {"name": "tag", "type": "str"},
#                 {"name": "channel", "type": "str"},
#                 {"name": "value_db", "type": "str"},
#             ],
#         },
#         "mute_on": {
#             "description": "Mute tag/channel",
#             "params": [{"name": "tag", "type": "str"}, {"name": "channel", "type": "str"}],
#         },
#         "mute_off": {
#             "description": "Unmute tag/channel",
#             "params": [{"name": "tag", "type": "str"}, {"name": "channel", "type": "str"}],
#         },
#         "recall_preset": {
#             "description": "Recall device preset",
#             "params": [{"name": "preset_number", "type": "str"}],
#         },
#         "reboot": {"description": "Reboot device", "params": []},
#         "start_audio": {"description": "Start audio", "params": []},
#         "stop_audio": {"description": "Stop audio", "params": []},
#         "raw_command": {"description": "Send raw Tesira command", "params": [{"name": "command", "type": "str"}]},
#     }
#     QUERY_COMMANDS = {
#         "device_info": "get_device_info",
#         "audio_blocks": "list_audio_blocks",
#     }
 
#     def _parse_value(self, response, key):
#         if not response:
#             return None
 
#         match = re.search(rf'"{re.escape(key)}":"([^"]+)"', response)
#         if match:
#             return match.group(1)
 
#         match = re.search(rf'"{re.escape(key)}":([^\s"{{}},]+)', response)
#         if match:
#             return match.group(1)
 
#         return None
 
#     def _send_command(self, shell, command, delay=1.5):
#         shell.send(command + "\n")
#         time.sleep(delay)
 
#         output = ""
#         while shell.recv_ready():
#             output += shell.recv(65535).decode(errors="ignore")
 
#         output = output.replace(command, "")
#         return re.sub(r"[^\x20-\x7E\r\n]", "", output).strip()
 
#     def _connect(self, ip, port, username, password):
#         ssh = paramiko.SSHClient()
#         ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#         ssh.connect(
#             hostname=ip,
#             port=port,
#             username=username,
#             password=password,
#             timeout=self.timeout,
#             look_for_keys=False,
#             allow_agent=False,
#         )
 
#         shell = ssh.invoke_shell()
#         time.sleep(2.0)
#         if shell.recv_ready():
#             shell.recv(65535)
#         return ssh, shell
 
#     def _credentials(self):
#         username = self.config.get("username")
#         password = self.config.get("password")
#         if not username or not password:
#             raise ValueError("Missing credentials: username and password are required.")
#         return username, password
 
#     def _with_shell(self, ip, port, fn):
#         username, password = self._credentials()
#         ssh = None
#         shell = None
#         try:
#             ssh, shell = self._connect(ip, port, username, password)
#             return fn(shell)
#         finally:
#             try:
#                 if shell:
#                     shell.close()
#             except Exception:
#                 pass
#             try:
#                 if ssh:
#                     ssh.close()
#             except Exception:
#                 pass
 
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
 
#     def _infer_model_from_hostname(self, hostname):
#         host = hostname or ""
#         patterns = [
#             (r"TesiraForteX", "TesiraFORTE X"),
#             (r"TesiraForte(?!X)", "TesiraFORTE"),
#             (r"TesiraServerIO", "Tesira SERVER-IO"),
#             (r"TesiraServer(?!IO)", "Tesira SERVER"),
#             (r"TesiraLUX", "TesiraLUX"),
#             (r"Voltera", "Voltera"),
#             (r"TesiraAMP", "TesiraAMP"),
#         ]
#         for pattern, model in patterns:
#             if re.search(pattern, host, re.IGNORECASE):
#                 return model
#         return None
 
#     def _get_device_model(self, shell, hostname, firmware):
#         try:
#             major_version = int(str(firmware or "").split(".")[0])
#         except (TypeError, ValueError):
#             major_version = 0
 
#         if major_version >= 4:
#             device_info = self._send_command(shell, "DEVICE get deviceInfo")
#             model = self._parse_value(device_info, "deviceModel")
#             if model:
#                 return model
 
#         hostname_model = self._infer_model_from_hostname(hostname)
#         if hostname_model:
#             return hostname_model
 
#         part = self._send_command(shell, "DEVICE get partNumber")
#         part_number = self._parse_value(part, "value")
#         if part_number:
#             return part_number
 
#         cleaned_hostname = re.sub(r"\d{6,}$", "", hostname or "").strip()
#         if cleaned_hostname:
#             return cleaned_hostname
 
#         return f"Tesira Device (fw {firmware or 'N/A'})"
 
#     def list_audio_blocks(self, ip, port=22):
#         return self._with_shell(ip, port, lambda shell: self._send_command(shell, "SESSION get aliases"))
 
#     def get_audio_level(self, ip, tag, channel, port=22):
#         return self._with_shell(ip, port, lambda shell: self._send_command(shell, f"{tag} get level {channel}"))
 
#     def set_audio_level(self, ip, tag, channel, value_db, port=22):
#         return self._with_shell(ip, port, lambda shell: self._send_command(shell, f"{tag} set level {channel} {value_db}"))
 
#     def mute_on(self, ip, tag, channel, port=22):
#         return self._with_shell(ip, port, lambda shell: self._send_command(shell, f"{tag} set mute {channel} true"))
 
#     def mute_off(self, ip, tag, channel, port=22):
#         return self._with_shell(ip, port, lambda shell: self._send_command(shell, f"{tag} set mute {channel} false"))
 
#     def recall_preset(self, ip, preset_number, port=22):
#         return self._with_shell(ip, port, lambda shell: self._send_command(shell, f"DEVICE recallPreset {preset_number}"))
 
#     def reboot(self, ip, port=22):
#         return self._with_shell(ip, port, lambda shell: self._send_command(shell, "DEVICE reboot"))
 
#     def start_audio(self, ip, port=22):
#         return self._with_shell(ip, port, lambda shell: self._send_command(shell, "DEVICE startAudio"))
 
#     def stop_audio(self, ip, port=22):
#         return self._with_shell(ip, port, lambda shell: self._send_command(shell, "DEVICE stopAudio"))
 
#     def get_device_info(self, ip, port=22, display_id=None):
#         try:
#             username, password = self._credentials()
#         except ValueError as e:
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "Biamp",
#                 "device_type": "Tesira DSP",
#                 "current_status": "Offline",
#                 "error": str(e),
#             }
 
#         ssh = None
#         shell = None
 
#         try:
#             ssh, shell = self._connect(ip, port, username, password)
 
#             firmware = self._parse_value(self._send_command(shell, "DEVICE get version"), "value")
#             serial = self._parse_value(self._send_command(shell, "DEVICE get serialNumber"), "value")
#             hostname = self._parse_value(self._send_command(shell, "DEVICE get hostname"), "value")
#             network = self._send_command(shell, "DEVICE get networkStatus")
#             faults = self._send_command(shell, "DEVICE get activeFaultList")
 
#             model = self._get_device_model(shell, hostname, firmware)
#             mac = self._parse_value(network, "macAddress")
#             device_ip = self._parse_value(network, "ip") or ip
#             current_fault = self._parse_value(faults, "name")
 
#             return {
#                 "ip_address": device_ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "Biamp",
#                 "device_type": "Tesira DSP",
#                 "device_name": hostname or model or "Biamp Tesira",
#                 "model": model,
#                 "serial_number": serial or mac,
#                 "firmware": firmware,
#                 "hostname": hostname,
#                 "mac_address": mac,
#                 "subnet_mask": self._parse_value(network, "netmask"),
#                 "gateway": self._parse_value(network, "gateway"),
#                 "default_gateway_status": self._parse_value(network, "defaultGatewayStatus"),
#                 "link_status": self._parse_value(network, "linkStatus"),
#                 "address_source": self._parse_value(network, "addressSource"),
#                 "telnet_enabled": self._parse_value(network, "telnetDisabled") == "false",
#                 "ssh_enabled": self._parse_value(network, "sshDisabled") == "false",
#                 "mdns_enabled": self._parse_value(network, "mDNSEnabled") == "true",
#                 "fault_status": "No Faults" if current_fault == "No fault" else (current_fault or "Unknown"),
#                 "current_status": "Online",
#                 "raw_network": network,
#                 "raw_faults": faults,
#                 "raw_audio_blocks": self._send_command(shell, "SESSION get aliases"),
#             }
#         except Exception as e:
#             return {
#                 "ip_address": ip,
#                 "port": port,
#                 "display_id": display_id,
#                 "make": "Biamp",
#                 "device_type": "Tesira DSP",
#                 "current_status": "Offline",
#                 "error": str(e),
#             }
#         finally:
#             try:
#                 if shell:
#                     shell.close()
#             except Exception:
#                 pass
#             try:
#                 if ssh:
#                     ssh.close()
#             except Exception:
#                 pass
 
#     def send_command(self, ip, port, display_id, command,params=None):
#         try:
#             action, params = self._decode_command(command)
#             params = params or {}
#             target_port = int(port or self.default_port)
 
#             if action == "raw_command":
#                 tcp_command = params.get("command")
#                 if not tcp_command:
#                     return False, "raw_command requires params.command"
#                 return True, self._with_shell(ip, target_port, lambda shell: self._send_command(shell, tcp_command))
 
#             actions = {
#                 "list_audio_blocks": lambda: self.list_audio_blocks(ip, target_port),
#                 "get_audio_level": lambda: self.get_audio_level(ip, params.get("tag"), params.get("channel"), target_port),
#                 "set_audio_level": lambda: self.set_audio_level(ip, params.get("tag"), params.get("channel"), params.get("value_db"), target_port),
#                 "mute_on": lambda: self.mute_on(ip, params.get("tag"), params.get("channel"), target_port),
#                 "mute_off": lambda: self.mute_off(ip, params.get("tag"), params.get("channel"), target_port),
#                 "recall_preset": lambda: self.recall_preset(ip, params.get("preset_number"), target_port),
#                 "reboot": lambda: self.reboot(ip, target_port),
#                 "start_audio": lambda: self.start_audio(ip, target_port),
#                 "stop_audio": lambda: self.stop_audio(ip, target_port),
#             }
 
#             if action not in actions:
#                 return False, f"Unknown command: {action}"
 
#             if action in {"get_audio_level", "set_audio_level", "mute_on", "mute_off"}:
#                 if not params.get("tag") or not params.get("channel"):
#                     return False, f"{action} requires params.tag and params.channel"
#             if action == "set_audio_level" and params.get("value_db") in (None, ""):
#                 return False, "set_audio_level requires params.value_db"
#             if action == "recall_preset" and params.get("preset_number") in (None, ""):
#                 return False, "recall_preset requires params.preset_number"
 
#             return True, actions[action]()
#         except Exception as e:
#             return False, str(e)
 
#     def query_status(self, ip, port=22, display_id=None):
#         info = self.get_device_info(ip, port, display_id)
#         return {
#             "reachable": info.get("current_status") == "Online",
#             "device_name": info.get("device_name"),
#             "model": info.get("model"),
#             "serial_number": info.get("serial_number"),
#             "firmware": info.get("firmware"),
#             "fault_status": info.get("fault_status"),
#             "error": info.get("error"),
#         }
 
 