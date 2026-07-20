
# # #  Samsung_mdc_plugin.py 

# # """
# # Manual Platform Plugin: SamsungMDCPlugin
# # """
# # import socket
# # import json
# # import threading
# # import time
# # import re
# # import asyncio
# # import subprocess
# # import platform
# # import requests
# # import xml.etree.ElementTree as ET

# # from .base import ManualPlatformPlugin


# # class SamsungMDCPlugin(ManualPlatformPlugin):
# #     """Samsung MDC Protocol Plugin"""
    
# #     name = "samsung_mdc"
# #     display_name = "Samsung MDC"
# #     description = "Samsung MDC Display Control"
# #     supports_display_id = True
# #     supports_port = True
# #     default_port = 1515
    
# #     # Commands: {key: (bytes, description)}
# #     COMMANDS = {
# #         "power_on": (b"\xAA\x11\xFE\x01\x01\x11", "Power ON"),
# #         "power_off": (b"\xAA\x11\xFE\x01\x00\x10", "Power OFF"),
# #         "hdmi_1": (b"\xAA\x14\xFE\x01\x21\x34", "HDMI 1"),
# #         "hdmi_2": (b"\xAA\x14\xFE\x01\x23\x36", "HDMI 2"),
# #         "hdmi_3": (b"\xAA\x14\xFE\x01\x31\x44", "HDMI 3"),
# #         "display_port": (b"\xAA\x14\xFE\x01\x0F\x22", "DisplayPort"),
# #         "dvi": (b"\xAA\x14\xFE\x01\x0C\x1F", "DVI"),
# #         "pc": (b"\xAA\x14\xFE\x01\x04\x17", "PC (RGB)"),
# #         "av": (b"\xAA\x14\xFE\x01\x08\x1B", "AV"),
# #         "volume_up": (b"\xAA\x62\xFE\x01\x00\x61", "Volume Up"),
# #         "volume_down": (b"\xAA\x62\xFE\x01\x01\x62", "Volume Down"),
# #         "mute_on": (b"\xAA\x13\xFE\x01\x01\x13", "Mute ON"),
# #         "mute_off": (b"\xAA\x13\xFE\x01\x00\x12", "Mute OFF"),
# #         # ✅ Brightness — MDC command 0x52
# #         "brightness_up":   (b"\xAA\x52\xFE\x01\x01\x52", "Brightness Up"),
# #         "brightness_down": (b"\xAA\x52\xFE\x01\x00\x51", "Brightness Down"),
# #     }
    
# #     QUERY_COMMANDS = {
# #         "power": b"\xAA\x11\xFE\x00\x11",
# #         "input": b"\xAA\x14\xFE\x00\x14",
# #         "volume": b"\xAA\x12\xFE\x00\x12",
# #         "mute": b"\xAA\x13\xFE\x00\x13",
# #          # ✅ Brightness query — MDC command 0x52
# #         "brightness": b"\xAA\x52\xFE\x00\x52",
# #     }
    
# #     def get_device_info(self, ip, port=1515, display_id=None):
# #         """Get device info via UPnP/SSDP discovery"""
# #         import subprocess
# #         import platform
# #         import requests
# #         import xml.etree.ElementTree as ET
# #         import re
        
# #         def ping_host():
# #             param = "-n" if platform.system().lower() == "windows" else "-c"
# #             result = subprocess.run(["ping", param, "1", ip], capture_output=True)
# #             return result.returncode == 0
        
# #         def get_mac():
# #             try:
# #                 if platform.system().lower() == "windows":
# #                     output = subprocess.check_output(["arp", "-a", ip], text=True)
# #                     match = re.search(r"([0-9a-fA-F]{2}[-:]){5}[0-9a-fA-F]{2}", output)
# #                 else:
# #                     output = subprocess.check_output(["arp", "-n", ip], text=True)
# #                     match = re.search(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", output)
# #                 return match.group(0).lower() if match else None
# #             except:
# #                 return None
        
# #         is_online = ping_host()
# #         mac = get_mac() if is_online else None
        
# #         # Try UPnP discovery
# #         upnp_info = self._discover_upnp(ip) if is_online else None
        
# #         # Get serial - prefer UPnP serial, fallback to MAC
# #         serial = upnp_info.get("serialNumber") if upnp_info else None
# #         if not serial or serial == "serialNumber":
# #             serial = mac  # Use MAC as fallback
        
# #         return {
# #             "ip_address": ip,
# #             "port": port,
# #             "display_id": display_id,
# #             "make": "Samsung",
# #             "model": upnp_info.get("model", "QB Series") if upnp_info else "QB Series",
# #             "serial_number": serial,
# #             "mac_address": mac,
# #             "current_status": "Online" if is_online else "Offline",
# #         }
    
# #     def _discover_upnp(self, ip):
# #         """Discover device via SSDP"""
# #         MSEARCH = (
# #             'M-SEARCH * HTTP/1.1\r\n'
# #             'HOST:239.255.255.250:1900\r\n'
# #             'MAN:"ssdp:discover"\r\n'
# #             'MX:2\r\n'
# #             'ST: ssdp:all\r\n'
# #             '\r\n'
# #         )
        
# #         try:
# #             sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.SOCK_DGRAM)
# #             sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
# #             sock.settimeout(3)
# #             sock.sendto(MSEARCH.encode("utf-8"), ("239.255.255.250", 1900))
            
# #             location = None
# #             while True:
# #                 data, addr = sock.recvfrom(65507)
# #                 if addr[0] == ip:
# #                     response = data.decode("utf-8", errors="ignore")
# #                     for line in response.split("\r\n"):
# #                         if line.lower().startswith("location:"):
# #                             location = line.split(":", 1)[1].strip()
# #                             break
# #                     break
# #             sock.close()
            
# #             if location:
# #                 resp = requests.get(location, timeout=3)
# #                 if resp.status_code == 200:
# #                     root = ET.fromstring(resp.text)
# #                     ns = {'upnp': 'urn:schemas-upnp-org:device-1-0'}
# #                     device = root.find(".//upnp:device", ns)
# #                     if device is not None:
# #                         return {
# #                             "model": device.findtext("upnp:modelName", ""),
# #                             "serial": device.findtext("upnp:serialNumber", ""),
# #                             "name": device.findtext("upnp:friendlyName", ""),
# #                         }
# #         except:
# #             pass
# #         return {}
    
# #     def send_command(self, ip, port, display_id, command_key):
# #         """Send control command to device"""
# #         if command_key not in self.COMMANDS:
# #             return False, f"Unknown command: {command_key}"

# #         # Quick reachability check to return a friendly error instead of a long socket timeout
# #         try:
# #             socket.create_connection((ip, port), timeout=3).close()
# #         except Exception as e:
# #             return False, f"Device unreachable at {ip}:{port} ({e})"

# #         raw_bytes, label = self.COMMANDS[command_key]
        
# #         # Adjust display ID if needed
# #         if display_id != "00":
# #             raw_bytes = bytes([raw_bytes[0], int(display_id, 16)]) + raw_bytes[2:]
        
# #         try:
# #             sock = self.connect(ip, port)
# #             sock.sendall(raw_bytes)
            
# #             # Try to read response
# #             try:
# #                 sock.settimeout(2)
# #                 response = sock.recv(64)
# #                 resp_hex = " ".join(f"{b:02X}" for b in response)
# #             except socket.timeout:
# #                 resp_hex = None
# #             except Exception:
# #                 resp_hex = None
            
# #             sock.close()
# #             return True, f"{label} - Response: {resp_hex or 'None'}"
# #         except Exception as e:
# #             return False, f"Send failed: {e}"
    
# #     def query_status(self, ip, port=1515, display_id="00"):
# #         """Query device status"""
# #         status = {}
        
# #         for label, raw_bytes in self.QUERY_COMMANDS.items():
# #             # Adjust display ID
# #             cmd = bytes([raw_bytes[0], int(display_id, 16)]) + raw_bytes[2:] if display_id != "00" else raw_bytes
            
# #             try:
# #                 sock = self.connect(ip, port)
# #                 sock.sendall(cmd)
# #                 sock.settimeout(3)
# #                 response = sock.recv(64)
# #                 sock.close()
                
# #                 # Parse response
# #                 if len(response) >= 6 and response[0] == 0xAA and response[1] == 0xFF:
# #                     # Samsung MDC replies: AA FF ID LEN CMD DATA CHK
# #                     data_byte = None
# #                     if len(response) >= 7:
# #                         data_byte = response[5]          # typical data position
# #                     elif len(response) >= 2:
# #                         data_byte = response[-2]         # fallback: second last byte

# #                     if label == "power":
# #                         status["power"] = "ON" if (data_byte or 0) == 0x01 else "OFF"
# #                         status["is_powered_on"] = status["power"] == "ON"
# #                     elif label == "input":
# #                         input_map = {
# #                             0x14: "HDMI 1", 0x1E: "HDMI 2", 0x0C: "DVI",
# #                             0x04: "PC", 0x08: "AV", 0x18: "DisplayPort"
# #                         }
# #                         status["input"] = input_map.get(data_byte or 0, "Unknown")
# #                     elif label == "volume":
# #                         status["volume"] = data_byte or 0
# #                     elif label == "mute":
# #                         status["mute"] = "ON" if (data_byte or 0) == 0x01 else "OFF"
# #                     elif label == "brightness":
# #                         status["brightness"] = data_byte or 0
# #             except:
# #                 pass
        
# #         return status




# #  Samsung_mdc_plugin.py 

# """
# Manual Platform Plugin: SamsungMDCPlugin
# """
# import socket
# import json
# import os
# import logging
# import threading
# import time
# import re
# import asyncio
# import subprocess
# import platform
# import shutil
# import requests
# import xml.etree.ElementTree as ET

# from .base import ManualPlatformPlugin


# logger = logging.getLogger(__name__)


# class SamsungMDCPlugin(ManualPlatformPlugin):
#     """Samsung MDC Protocol Plugin"""
    
#     name = "samsung_mdc"
#     display_name = "Samsung MDC"
#     description = "Samsung MDC Display Control"
#     supports_display_id = True
#     supports_port = True
#     default_port = 1515
    
#     # Commands: {key: (bytes, description)}
#     COMMANDS = {
#         "power_on":  (b"\xAA\x11\xFE\x01\x01\x11", "Power ON"),
#         "power_off": (b"\xAA\x11\xFE\x01\x00\x10", "Power OFF"),
#         "hdmi_1":    (b"\xAA\x14\xFE\x01\x21\x34", "HDMI 1"),
#         "hdmi_2":    (b"\xAA\x14\xFE\x01\x23\x36", "HDMI 2"),
#         "hdmi_3":    (b"\xAA\x14\xFE\x01\x31\x44", "HDMI 3"),
#         "display_port": (b"\xAA\x14\xFE\x01\x0F\x22", "DisplayPort"),
#         "dvi":       (b"\xAA\x14\xFE\x01\x0C\x1F", "DVI"),
#         "pc":        (b"\xAA\x14\xFE\x01\x04\x17", "PC (RGB)"),
#         "av":        (b"\xAA\x14\xFE\x01\x08\x1B", "AV"),
#         "volume_up":   (b"\xAA\x62\xFE\x01\x00\x61", "Volume Up"),
#         "volume_down": (b"\xAA\x62\xFE\x01\x01\x62", "Volume Down"),
#         "mute_on":  (b"\xAA\x13\xFE\x01\x01\x13", "Mute ON"),
#         "mute_off": (b"\xAA\x13\xFE\x01\x00\x12", "Mute OFF"),
#         # FIX: Samsung QB brightness = command 0x61, NOT 0x52
#         # 0x52 is "Safety Lock" — sending it was locking/unlocking the panel, not changing brightness.
#         # Brightness has no native inc/dec — we query current level then set ±10.
#         # These sentinel entries trigger the _brightness_step() path in send_command().
#         "brightness_up":   None,   # handled dynamically — see send_command()
#         "brightness_down": None,   # handled dynamically — see send_command()
#     }
    
#     QUERY_COMMANDS = {
#         "power":  b"\xAA\x11\xFE\x00\x11",
#         "input":  b"\xAA\x14\xFE\x00\x14",
#         "volume": b"\xAA\x12\xFE\x00\x12",
#         "mute":   b"\xAA\x13\xFE\x00\x13",
#         # FIX: brightness query uses command 0x61, NOT 0x52
#         "brightness": b"\xAA\x61\xFE\x00\x5F",
#     }

#     # ── MDC packet builders ──────────────────────────────────────

#     @staticmethod
#     def _build_set(cmd: int, id_byte: int, data: int) -> bytes:
#         """
#         Build a 6-byte MDC set packet:
#           AA  CMD  ID  LEN  DATA  CHK
#         LEN = 0x01 (one data byte).
#         CHK = (CMD + ID + LEN + DATA) & 0xFF
#         """
#         chk = (cmd + id_byte + 0x01 + data) & 0xFF
#         return bytes([0xAA, cmd, id_byte, 0x01, data, chk])

#     @staticmethod
#     def _build_query(cmd: int, id_byte: int) -> bytes:
#         """
#         Build a 5-byte MDC query packet:
#           AA  CMD  ID  LEN=00  CHK
#         CHK = (CMD + ID) & 0xFF
#         """
#         chk = (cmd + id_byte) & 0xFF
#         return bytes([0xAA, cmd, id_byte, 0x00, chk])

#     @staticmethod
#     def _inject_id(raw_bytes: bytes, id_byte: int) -> bytes:
#         """Replace the ID byte (index 2) and recompute the checksum (last byte)."""
#         pkt = bytearray(raw_bytes)
#         pkt[2] = id_byte
#         pkt[-1] = sum(pkt[1:-1]) & 0xFF
#         return bytes(pkt)

#     @staticmethod
#     def _parse_id(display_id) -> int:
#         """Convert display_id string/int to int. '00', '01', 'FE', None → int."""
#         if display_id is None or str(display_id).strip().upper() in ("", "FE"):
#             return 0xFE
#         try:
#             s = str(display_id).strip()
#             return int(s) if s.isdigit() else int(s, 16)
#         except ValueError:
#             return 0xFE

#     # ── Socket helpers ───────────────────────────────────────────

#     def connect(self, ip, port, timeout=5):
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         sock.settimeout(timeout)
#         sock.connect((ip, port))
#         return sock

#     def _recv(self, sock, min_bytes=7, timeout=3) -> bytes:
#         """Read until min_bytes received or timeout."""
#         sock.settimeout(timeout)
#         buf = b""
#         deadline = time.time() + timeout
#         while len(buf) < min_bytes and time.time() < deadline:
#             try:
#                 chunk = sock.recv(64)
#                 if not chunk:
#                     break
#                 buf += chunk
#             except socket.timeout:
#                 break
#         return buf

#     def _query_mdc_data(self, ip, port, id_byte: int, command: int, subcommand=None):
#         """Return the data bytes from a successful Samsung MDC query."""
#         payload = [command, id_byte]
#         if subcommand is None:
#             payload.append(0)
#         else:
#             payload.extend([1, subcommand])
#         packet = bytes([0xAA, *payload, sum(payload) & 0xFF])

#         try:
#             with self.connect(ip, port) as sock:
#                 sock.sendall(packet)
#                 response = b""
#                 deadline = time.time() + 3
#                 while time.time() < deadline:
#                     sock.settimeout(max(deadline - time.time(), 0.1))
#                     try:
#                         chunk = sock.recv(256)
#                     except socket.timeout:
#                         break
#                     if not chunk:
#                         break
#                     response += chunk
#                     if len(response) >= 4 and len(response) >= 4 + response[3] + 1:
#                         break
#         except OSError:
#             return None

#         if len(response) < 7 or response[:2] != b"\xAA\xFF":
#             return None

#         length = response[3]
#         if len(response) < 4 + length + 1 or response[4] != 0x41:
#             return None

#         data = response[6:6 + max(length - 2, 0)]
#         if subcommand is not None and data[:1] == bytes([subcommand]):
#             data = data[1:]
#         return data

#     def _query_mdc_string(self, ip, port, id_byte: int, command: int):
#         data = self._query_mdc_data(ip, port, id_byte, command)
#         if not data:
#             return None
#         value = data.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
#         return value or None

#     def _parse_reply(self, response: bytes):
#         """
#         Extract the DATA byte from a Samsung MDC reply.

#         Samsung MDC reply layout:
#           [0] 0xAA  header
#           [1] 0xFF  reply marker
#           [2] ID
#           [3] LEN   bytes that follow before checksum
#           [4] CMD   echoed command byte
#           [5] ACK   0x41 = 'A' (OK),  0x4E = 'N' (error)
#           [6] DATA  ← brightness / power / input / volume / mute value
#           [-1] CHK

#         Returns data byte (int) on success, None on failure.
#         """
#         if len(response) < 7:
#             return None
#         if response[0] != 0xAA or response[1] != 0xFF:
#             return None
#         if response[4] != 0x41:   # not ACK
#             return None
#         return response[6]

#     def _is_ack(self, response: bytes) -> bool:
#         return (
#             len(response) >= 5
#             and response[0] == 0xAA
#             and response[1] == 0xFF
#             and response[4] == 0x41
#         )

#     def _candidate_ids(self, display_id):
#         primary = self._parse_id(display_id)
#         candidates = [primary]
#         for fallback in (0xFE, 0x01, 0x00):
#             if fallback not in candidates:
#                 candidates.append(fallback)
#         return candidates

#     # ── Brightness step (query → clamp → set) ───────────────────

#     def _brightness_step(self, ip, port, id_byte: int, direction: int) -> tuple:
#         """
#         Brightness has no native MDC increment command on QB series.
#         Strategy: query current level → add ±10 → clamp 0-100 → set absolute.
#         direction: +1 = up, -1 = down
#         """
#         # 1. Query current brightness (command 0x61)
#         current = 50   # safe default if query fails
#         try:
#             q = self._build_query(0x61, id_byte)
#             sock = self.connect(ip, port)
#             sock.sendall(q)
#             resp = self._recv(sock, min_bytes=7, timeout=3)
#             sock.close()
#             data = self._parse_reply(resp)
#             if data is not None:
#                 current = int(data)
#         except Exception:
#             pass   # proceed with default

#         # 2. Step ±10, clamp
#         new_level = max(0, min(100, current + direction * 10))

#         # 3. Set absolute brightness (command 0x61)
#         try:
#             pkt = self._build_set(0x61, id_byte, new_level)
#             sock = self.connect(ip, port)
#             sock.sendall(pkt)
#             resp = self._recv(sock, min_bytes=6, timeout=2)
#             sock.close()
#             label = "Brightness Up" if direction > 0 else "Brightness Down"
#             return True, f"{label}: {current} → {new_level} — {resp.hex() if resp else 'no reply'}"
#         except Exception as e:
#             return False, f"Brightness set failed: {e}"

#     # ── Public API ───────────────────────────────────────────────

#     def get_device_info(self, ip, port=1515, display_id="00"):
#         """Get device info via ICMP/TCP reachability + ARP + optional UPnP."""
        
#         def ping_host():
#             if not shutil.which("ping"):
#                 return None
#             param = "-n" if platform.system().lower() == "windows" else "-c"
#             try:
#                 result = subprocess.run(
#                     ["ping", param, "1", ip],
#                     capture_output=True,
#                     timeout=3,
#                 )
#                 return result.returncode == 0
#             except (FileNotFoundError, subprocess.SubprocessError, OSError):
#                 return None

#         def tcp_probe():
#             try:
#                 with socket.create_connection((ip, int(port)), timeout=3):
#                     return True
#             except Exception:
#                 return False
        
#         def get_mac():
#             mac_pattern = r"(?<![0-9a-fA-F])(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}(?![0-9a-fA-F])"
#             try:
#                 if platform.system().lower() == "windows":
#                     if not shutil.which("arp"):
#                         return None
#                     output = subprocess.check_output(["arp", "-a", ip], text=True)
#                     match = re.search(mac_pattern, output)
#                     return match.group(0).replace("-", ":").lower() if match else None

#                 # Containers often do not include the legacy arp executable. The
#                 # kernel neighbor table is available on standard Linux images.
#                 arp_path = "/proc/net/arp"
#                 if os.path.exists(arp_path):
#                     with open(arp_path, encoding="utf-8") as arp_table:
#                         for line in arp_table.readlines()[1:]:
#                             fields = line.split()
#                             if len(fields) >= 4 and fields[0] == ip:
#                                 mac = fields[3]
#                                 if re.fullmatch(mac_pattern, mac):
#                                     return mac.replace("-", ":").lower()

#                 if shutil.which("ip"):
#                     output = subprocess.check_output(
#                         ["ip", "neigh", "show", ip], text=True, stderr=subprocess.DEVNULL
#                     )
#                     match = re.search(mac_pattern, output)
#                     if match:
#                         return match.group(0).replace("-", ":").lower()

#                 if shutil.which("arp"):
#                     output = subprocess.check_output(["arp", "-n", ip], text=True)
#                     match = re.search(mac_pattern, output)
#                     if match:
#                         return match.group(0).replace("-", ":").lower()
#             except Exception:
#                 pass
#             return None
        
#         ping_online = ping_host()
#         is_online = ping_online if ping_online is not None else tcp_probe()
#         # The reachability check creates the ARP/neighbor entry on hosts where it
#         # is visible to this process, so look up the MAC after that check.
#         mac = get_mac() if is_online else None
#         upnp_info = self._discover_upnp(ip) if is_online else {}

#         # Samsung MDC exposes serial/model identity on port 1515. This is more
#         # reliable in containers than multicast UPnP discovery.
#         id_byte = self._parse_id(display_id)
#         mdc_serial = self._query_mdc_string(ip, port, id_byte, 0x0B) if is_online else None
#         mdc_model = self._query_mdc_string(ip, port, id_byte, 0x8A) if is_online else None
#         mdc_name = self._query_mdc_string(ip, port, id_byte, 0x67) if is_online else None

#         configured_mac = self.config.get("mac_address") or self.config.get("mac")
#         configured_serial = self.config.get("serial_number") or self.config.get("serial")
#         mac = mac or configured_mac
#         serial = mdc_serial or upnp_info.get("serial") or configured_serial or mac
#         model = mdc_model or upnp_info.get("model") or "QB Series"
#         logger.info(
#             "Samsung MDC identity: ip=%s serial_source=%s mac_source=%s",
#             ip,
#             "mdc" if mdc_serial else ("upnp" if upnp_info.get("serial") else ("config" if configured_serial else "mac-or-unavailable")),
#             "network" if mac and not configured_mac else ("config" if configured_mac else "unavailable"),
#         )
        
#         return {
#             "ip_address":    ip,
#             "port":          port,
#             "display_id":    display_id,
#             "make":          "Samsung",
#             "model":         model,
#             "device_name":   mdc_name or upnp_info.get("name") or f"Samsung {model}",
#             "serial_number": serial,
#             "mac_address":   mac,
#             "current_status": "Online" if is_online else "Offline",
#         }
    
#     def _discover_upnp(self, ip):
#         """Discover device via SSDP."""
#         MSEARCH = (
#             'M-SEARCH * HTTP/1.1\r\n'
#             'HOST:239.255.255.250:1900\r\n'
#             'MAN:"ssdp:discover"\r\n'
#             'MX:2\r\n'
#             'ST: ssdp:all\r\n'
#             '\r\n'
#         )
#         try:
#             # FIX: original had socket.SOCK_DGRAM twice (invalid third arg)
#             sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
#             sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
#             sock.settimeout(3)
#             sock.sendto(MSEARCH.encode("utf-8"), ("239.255.255.250", 1900))
            
#             location = None
#             deadline = time.time() + 3
#             while time.time() < deadline:
#                 try:
#                     data, addr = sock.recvfrom(65507)
#                 except socket.timeout:
#                     break
#                 if addr[0] == ip:
#                     response = data.decode("utf-8", errors="ignore")
#                     for line in response.split("\r\n"):
#                         if line.lower().startswith("location:"):
#                             location = line.split(":", 1)[1].strip()
#                             break
#                     if location:
#                         break
#             sock.close()
            
#             if location:
#                 resp = requests.get(location, timeout=3)
#                 if resp.status_code == 200:
#                     root = ET.fromstring(resp.text)
#                     ns = {'upnp': 'urn:schemas-upnp-org:device-1-0'}
#                     device = root.find(".//upnp:device", ns)
#                     if device is not None:
#                         return {
#                             "model":  device.findtext("upnp:modelName",    "", ns),
#                             "serial": device.findtext("upnp:serialNumber", "", ns),
#                             "name":   device.findtext("upnp:friendlyName", "", ns),
#                         }
#         except Exception:
#             pass
#         return {}
    
#     def send_command(self, ip, port, display_id, command_key):
#         """Send control command to device."""
#         if command_key not in self.COMMANDS:
#             return False, f"Unknown command: {command_key}"

#         # Reachability check
#         try:
#             socket.create_connection((ip, port), timeout=3).close()
#         except Exception as e:
#             return False, f"Device unreachable at {ip}:{port} ({e})"

#         id_byte = self._parse_id(display_id)

#         # ── Brightness: query-then-set because MDC has no native inc/dec ──
#         if command_key == "brightness_up":
#             return self._brightness_step(ip, port, id_byte, +1)
#         if command_key == "brightness_down":
#             return self._brightness_step(ip, port, id_byte, -1)

#         # ── All other commands: inject real ID, send, read response ──
#         raw_bytes, label = self.COMMANDS[command_key]
#         cmd = self._inject_id(raw_bytes, id_byte)

#         try:
#             sock = self.connect(ip, port)
#             sock.sendall(cmd)
#             resp = self._recv(sock, min_bytes=6, timeout=2)
#             sock.close()
#             resp_hex = resp.hex() if resp else "no response"
#             return True, f"{label} — {resp_hex}"
#         except Exception as e:
#             return False, f"Send failed: {e}"
    
#     def _brightness_step(self, ip, port, id_byte: int, direction: int) -> tuple:
#         """Query current brightness, step it, then require a Samsung ACK."""
#         current = 50
#         try:
#             q = self._build_query(0x61, id_byte)
#             sock = self.connect(ip, port)
#             sock.sendall(q)
#             resp = self._recv(sock, min_bytes=7, timeout=3)
#             sock.close()
#             data = self._parse_reply(resp)
#             if data is not None:
#                 current = int(data)
#         except Exception:
#             pass

#         new_level = max(0, min(100, current + direction * 10))
#         try:
#             pkt = self._build_set(0x61, id_byte, new_level)
#             sock = self.connect(ip, port)
#             sock.sendall(pkt)
#             resp = self._recv(sock, min_bytes=6, timeout=2)
#             sock.close()
#             label = "Brightness Up" if direction > 0 else "Brightness Down"
#             if self._is_ack(resp):
#                 return True, f"{label}: {current} -> {new_level} ACK {resp.hex()}"
#             return False, f"{label} not acknowledged by display - {resp.hex() if resp else 'no response'}"
#         except Exception as e:
#             return False, f"Brightness set failed: {e}"

#     def send_command(self, ip, port, display_id, command_key):
#         """Send control command and require Samsung MDC ACK before reporting success."""
#         if command_key not in self.COMMANDS:
#             return False, f"Unknown command: {command_key}"

#         try:
#             socket.create_connection((ip, port), timeout=3).close()
#         except Exception as e:
#             return False, f"Device unreachable at {ip}:{port} ({e})"

#         candidate_ids = self._candidate_ids(display_id)

#         if command_key in ("brightness_up", "brightness_down"):
#             direction = +1 if command_key == "brightness_up" else -1
#             last_msg = ""
#             for id_byte in candidate_ids:
#                 ok, msg = self._brightness_step(ip, port, id_byte, direction)
#                 if ok:
#                     return True, f"{msg} (display_id={id_byte:02X})"
#                 last_msg = msg
#             return False, last_msg or "Brightness command not acknowledged by Samsung display"

#         raw_bytes, label = self.COMMANDS[command_key]
#         last_error = ""
#         sent_without_ack = None

#         for id_byte in candidate_ids:
#             cmd = self._inject_id(raw_bytes, id_byte)
#             try:
#                 sock = self.connect(ip, port)
#                 sock.sendall(cmd)
#                 resp = self._recv(sock, min_bytes=6, timeout=2)
#                 sock.close()
#                 resp_hex = resp.hex() if resp else "no response"
#                 if self._is_ack(resp):
#                     return True, f"{label} ACK from display_id={id_byte:02X} - {resp_hex}"
#                 last_error = f"display_id={id_byte:02X} returned {resp_hex}"
#                 if not resp and sent_without_ack is None:
#                     sent_without_ack = id_byte
#             except Exception as e:
#                 last_error = f"display_id={id_byte:02X} send failed: {e}"

#         if sent_without_ack is not None:
#             return True, (
#                 f"{label} sent to Samsung display_id={sent_without_ack:02X}; "
#                 "display did not return MDC ACK"
#             )

#         return False, f"{label} not acknowledged by Samsung display ({last_error})"

#     def query_status(self, ip, port=1515, display_id="00"):
#         """Query device status (power / input / volume / mute / brightness)."""
#         status = {}
#         id_byte = self._parse_id(display_id)

#         INPUT_MAP = {
#             0x04: "PC (RGB)",
#             0x08: "AV",
#             0x0C: "DVI",
#             0x0F: "DisplayPort",
#             0x14: "HDMI 1",
#             0x18: "DisplayPort",
#             0x1E: "HDMI 2",
#             0x1F: "HDMI 3",
#             0x21: "HDMI 1",
#             0x23: "HDMI 2",
#             0x31: "HDMI 3",
#         }
        
#         for label, raw_bytes in self.QUERY_COMMANDS.items():
#             # Inject real display ID into query packet
#             cmd = self._inject_id(raw_bytes, id_byte)
            
#             try:
#                 sock = self.connect(ip, port)
#                 sock.sendall(cmd)
#                 response = self._recv(sock, min_bytes=7, timeout=3)
#                 sock.close()

#                 # FIX: use _parse_reply() which reads DATA from index 6 (not 5)
#                 data_byte = self._parse_reply(response)
#                 if data_byte is None:
#                     continue

#                 if label == "power":
#                     status["power"] = "ON" if data_byte == 0x01 else "OFF"
#                     status["is_powered_on"] = (data_byte == 0x01)
#                 elif label == "input":
#                     status["input"] = INPUT_MAP.get(data_byte, f"Unknown (0x{data_byte:02X})")
#                 elif label == "volume":
#                     status["volume"] = int(data_byte)
#                 elif label == "mute":
#                     status["mute"] = "ON" if data_byte == 0x01 else "OFF"
#                 elif label == "brightness":
#                     status["brightness"] = int(data_byte)

#             except Exception:
#                 pass
        
#         return status


#  Samsung_mdc_plugin.py
 
"""
Manual Platform Plugin: SamsungMDCPlugin
"""
import socket
import json
import threading
import time
import re
import logging
import asyncio
import subprocess
import platform
import requests
import xml.etree.ElementTree as ET
 
from .base import ManualPlatformPlugin


logger = logging.getLogger(__name__)
 
 
class SamsungMDCPlugin(ManualPlatformPlugin):
    """Samsung MDC Protocol Plugin"""
    name = "samsung_mdc"
    display_name = "Samsung MDC"
    description = "Samsung MDC Display Control"
    supports_display_id = True
    supports_port = True
    default_port = 1515
    # Commands: {key: (bytes, description)}
    COMMANDS = {
        "power_on":  (b"\xAA\x11\xFE\x01\x01\x11", "Power ON"),
        "power_off": (b"\xAA\x11\xFE\x01\x00\x10", "Power OFF"),
        "hdmi_1":    (b"\xAA\x14\xFE\x01\x21\x34", "HDMI 1"),
        "hdmi_2":    (b"\xAA\x14\xFE\x01\x23\x36", "HDMI 2"),
        "hdmi_3":    (b"\xAA\x14\xFE\x01\x31\x44", "HDMI 3"),
        "display_port": (b"\xAA\x14\xFE\x01\x0F\x22", "DisplayPort"),
        "dvi":       (b"\xAA\x14\xFE\x01\x0C\x1F", "DVI"),
        "pc":        (b"\xAA\x14\xFE\x01\x04\x17", "PC (RGB)"),
        "av":        (b"\xAA\x14\xFE\x01\x08\x1B", "AV"),
        "volume_up":   (b"\xAA\x62\xFE\x01\x00\x61", "Volume Up"),
        "volume_down": (b"\xAA\x62\xFE\x01\x01\x62", "Volume Down"),
        "mute_on":  (b"\xAA\x13\xFE\x01\x01\x13", "Mute ON"),
        "mute_off": (b"\xAA\x13\xFE\x01\x00\x12", "Mute OFF"),
        # FIX: Samsung QB brightness = command 0x61, NOT 0x52
        # 0x52 is "Safety Lock" — sending it was locking/unlocking the panel, not changing brightness.
        # Brightness has no native inc/dec — we query current level then set ±10.
        # These sentinel entries trigger the _brightness_step() path in send_command().
        "brightness_up":   None,   # handled dynamically — see send_command()
        "brightness_down": None,   # handled dynamically — see send_command()
    }
    QUERY_COMMANDS = {
        "power":  b"\xAA\x11\xFE\x00\x11",
        "input":  b"\xAA\x14\xFE\x00\x14",
        "volume": b"\xAA\x12\xFE\x00\x12",
        "mute":   b"\xAA\x13\xFE\x00\x13",
        # FIX: brightness query uses command 0x61, NOT 0x52
        "brightness": b"\xAA\x61\xFE\x00\x5F",
    }
    IDENTITY_COMMANDS = {
        "serial_number": 0x0B,
        "software_version": 0x0E,
        "model_name": 0x8A,
        "device_name": 0x67,
    }
 
    # ── MDC packet builders ──────────────────────────────────────
 
    @staticmethod
    def _build_set(cmd: int, id_byte: int, data: int) -> bytes:
        """
        Build a 6-byte MDC set packet:
          AA  CMD  ID  LEN  DATA  CHK
        LEN = 0x01 (one data byte).
        CHK = (CMD + ID + LEN + DATA) & 0xFF
        """
        chk = (cmd + id_byte + 0x01 + data) & 0xFF
        return bytes([0xAA, cmd, id_byte, 0x01, data, chk])
 
    @staticmethod
    def _build_query(cmd: int, id_byte: int) -> bytes:
        """
        Build a 5-byte MDC query packet:
          AA  CMD  ID  LEN=00  CHK
        CHK = (CMD + ID) & 0xFF
        """
        chk = (cmd + id_byte) & 0xFF
        return bytes([0xAA, cmd, id_byte, 0x00, chk])
 
    @staticmethod
    def _inject_id(raw_bytes: bytes, id_byte: int) -> bytes:
        """Replace the ID byte (index 2) and recompute the checksum (last byte)."""
        pkt = bytearray(raw_bytes)
        pkt[2] = id_byte
        pkt[-1] = sum(pkt[1:-1]) & 0xFF
        return bytes(pkt)
 
    @staticmethod
    def _parse_id(display_id) -> int:
        """Convert display_id string/int to int. '00', '01', 'FE', None → int."""
        if display_id is None or str(display_id).strip().upper() in ("", "FE"):
            return 0xFE
        try:
            s = str(display_id).strip()
            return int(s) if s.isdigit() else int(s, 16)
        except ValueError:
            return 0xFE
 
    # ── Socket helpers ───────────────────────────────────────────
 
    def connect(self, ip, port, timeout=5):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        return sock
 
    def _recv(self, sock, min_bytes=7, timeout=3) -> bytes:
        """Read until a full MDC reply is received or timeout."""
        sock.settimeout(timeout)
        buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = sock.recv(64)
                if not chunk:
                    break
                buf += chunk
                if len(buf) >= 4 and len(buf) >= 4 + buf[3] + 1:
                    break
                if len(buf) >= min_bytes and len(buf) < 4:
                    break
            except socket.timeout:
                break
        return buf
 
    def _parse_reply(self, response: bytes):
        """
        Extract the DATA byte from a Samsung MDC reply.
 
        Samsung MDC reply layout:
          [0] 0xAA  header
          [1] 0xFF  reply marker
          [2] ID
          [3] LEN   bytes that follow before checksum
          [4] CMD   echoed command byte
          [5] ACK   0x41 = 'A' (OK),  0x4E = 'N' (error)
          [6] DATA  ← brightness / power / input / volume / mute value
          [-1] CHK
 
        Returns data byte (int) on success, None on failure.
        """
        if len(response) < 7:
            return None
        if response[0] != 0xAA or response[1] != 0xFF:
            return None
        if response[4] != 0x41:   # not ACK
            return None
        return response[6]
 
    def _parse_reply_data(self, response: bytes, expected_cmd=None):
        """Return all MDC data bytes from an ACK reply."""
        if len(response) < 6:
            return None
        if response[0] != 0xAA or response[1] != 0xFF:
            return None
        length = response[3]
        if len(response) < 4 + length + 1:
            return None
        if response[4] != 0x41:
            return None
        echoed_cmd = response[5]
        if expected_cmd is not None and echoed_cmd != expected_cmd:
            return None
        return response[6:6 + max(length - 2, 0)]
 
    def _is_ack(self, response: bytes) -> bool:
        return (
            len(response) >= 5
            and response[0] == 0xAA
            and response[1] == 0xFF
            and response[4] == 0x41
        )
 
    def _candidate_ids(self, display_id):
        primary = self._parse_id(display_id)
        candidates = [primary]
        for fallback in (0xFE, 0x01, 0x00):
            if fallback not in candidates:
                candidates.append(fallback)
        return candidates
 
    def _query_mdc_data(self, ip, port, display_id, cmd, timeout=3):
        for id_byte in self._candidate_ids(display_id):
            sock = None
            try:
                sock = self.connect(ip, port, timeout=timeout)
                sock.sendall(self._build_query(cmd, id_byte))
                response = self._recv(sock, min_bytes=7, timeout=timeout)
                data = self._parse_reply_data(response, expected_cmd=cmd)
                if data is not None:
                    return data
            except Exception:
                pass
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
        return None
 
    def _query_mdc_string(self, ip, port, display_id, cmd):
        data = self._query_mdc_data(ip, port, display_id, cmd)
        if not data:
            return None
        value = data.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
        return value or None
 
    def _get_mdc_identity(self, ip, port, display_id):
        identity = {}
        for field, cmd in self.IDENTITY_COMMANDS.items():
            # QB series occasionally drops the first software-version reply.
            # Retrying this read avoids losing firmware during onboarding.
            attempts = 2 if field == "software_version" else 1
            value = None
            for _ in range(attempts):
                value = self._query_mdc_string(ip, port, display_id, cmd)
                if value:
                    break
            if value:
                identity[field] = value
        return identity
 
    # ── Brightness step (query → clamp → set) ───────────────────
 
    def _brightness_step(self, ip, port, id_byte: int, direction: int) -> tuple:
        """
        Brightness has no native MDC increment command on QB series.
        Strategy: query current level → add ±10 → clamp 0-100 → set absolute.
        direction: +1 = up, -1 = down
        """
        # 1. Query current brightness (command 0x61)
        current = 50   # safe default if query fails
        try:
            q = self._build_query(0x61, id_byte)
            sock = self.connect(ip, port)
            sock.sendall(q)
            resp = self._recv(sock, min_bytes=7, timeout=3)
            sock.close()
            data = self._parse_reply(resp)
            if data is not None:
                current = int(data)
        except Exception:
            pass   # proceed with default
 
        # 2. Step ±10, clamp
        new_level = max(0, min(100, current + direction * 10))
 
        # 3. Set absolute brightness (command 0x61)
        try:
            pkt = self._build_set(0x61, id_byte, new_level)
            sock = self.connect(ip, port)
            sock.sendall(pkt)
            resp = self._recv(sock, min_bytes=6, timeout=2)
            sock.close()
            label = "Brightness Up" if direction > 0 else "Brightness Down"
            return True, f"{label}: {current} → {new_level} — {resp.hex() if resp else 'no reply'}"
        except Exception as e:
            return False, f"Brightness set failed: {e}"
 
    # ── Public API ───────────────────────────────────────────────
 
    def get_device_info(self, ip, port=1515, display_id="00"):
        """Get device info, preferring Samsung MDC identity over discovery fallbacks."""
        def ping_host():
            param = "-n" if platform.system().lower() == "windows" else "-c"
            result = subprocess.run(["ping", param, "1", ip], capture_output=True)
            return result.returncode == 0
        def mdc_reachable():
            try:
                socket.create_connection((ip, port), timeout=3).close()
                return True
            except Exception:
                return False
        def get_mac():
            try:
                if platform.system().lower() == "windows":
                    output = subprocess.check_output(["arp", "-a", ip], text=True)
                    match = re.search(r"([0-9a-fA-F]{2}[-:]){5}[0-9a-fA-F]{2}", output)
                else:
                    output = subprocess.check_output(["arp", "-n", ip], text=True)
                    match = re.search(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", output)
                return match.group(0).lower() if match else None
            except Exception:
                return None
        is_online = ping_host() or mdc_reachable()
        mac = get_mac() if is_online else None
        upnp_info = self._discover_upnp(ip) if is_online else {}
        mdc_info = self._get_mdc_identity(ip, port, display_id) if is_online else {}
        serial = mdc_info.get("serial_number") or upnp_info.get("serial") or mac
        model = mdc_info.get("model_name") or upnp_info.get("model") or "QB Series"
        device_name = mdc_info.get("device_name") or upnp_info.get("name") or model
        firmware = mdc_info.get("software_version")
        logger.info(
            "Samsung MDC identity ip=%s serial=%s model=%s firmware=%s",
            ip,
            bool(serial),
            model,
            firmware or "unavailable",
        )
        return {
            "ip_address":    ip,
            "port":          port,
            "display_id":    display_id,
            "make":          "Samsung",
            "model":         model,
            "device_name":   device_name,
            "serial_number": serial,
            "mac_address":   mac,
            "firmware_version": firmware,
            "firmware":      firmware,
            "current_status": "Online" if is_online else "Offline",
        }
    def _discover_upnp(self, ip):
        """Discover device via SSDP."""
        MSEARCH = (
            'M-SEARCH * HTTP/1.1\r\n'
            'HOST:239.255.255.250:1900\r\n'
            'MAN:"ssdp:discover"\r\n'
            'MX:2\r\n'
            'ST: ssdp:all\r\n'
            '\r\n'
        )
        try:
            # FIX: original had socket.SOCK_DGRAM twice (invalid third arg)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(3)
            sock.sendto(MSEARCH.encode("utf-8"), ("239.255.255.250", 1900))
            location = None
            deadline = time.time() + 3
            while time.time() < deadline:
                try:
                    data, addr = sock.recvfrom(65507)
                except socket.timeout:
                    break
                if addr[0] == ip:
                    response = data.decode("utf-8", errors="ignore")
                    for line in response.split("\r\n"):
                        if line.lower().startswith("location:"):
                            location = line.split(":", 1)[1].strip()
                            break
                    if location:
                        break
            sock.close()
            if location:
                resp = requests.get(location, timeout=3)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    ns = {'upnp': 'urn:schemas-upnp-org:device-1-0'}
                    device = root.find(".//upnp:device", ns)
                    if device is not None:
                        return {
                            "model":  device.findtext("upnp:modelName",    "", ns),
                            "serial": device.findtext("upnp:serialNumber", "", ns),
                            "name":   device.findtext("upnp:friendlyName", "", ns),
                        }
        except Exception:
            pass
        return {}
    def send_command(self, ip, port, display_id, command_key):
        """Send control command to device."""
        if command_key not in self.COMMANDS:
            return False, f"Unknown command: {command_key}"
 
        # Reachability check
        try:
            socket.create_connection((ip, port), timeout=3).close()
        except Exception as e:
            return False, f"Device unreachable at {ip}:{port} ({e})"
 
        id_byte = self._parse_id(display_id)
 
        # ── Brightness: query-then-set because MDC has no native inc/dec ──
        if command_key == "brightness_up":
            return self._brightness_step(ip, port, id_byte, +1)
        if command_key == "brightness_down":
            return self._brightness_step(ip, port, id_byte, -1)
 
        # ── All other commands: inject real ID, send, read response ──
        raw_bytes, label = self.COMMANDS[command_key]
        cmd = self._inject_id(raw_bytes, id_byte)
 
        try:
            sock = self.connect(ip, port)
            sock.sendall(cmd)
            resp = self._recv(sock, min_bytes=6, timeout=2)
            sock.close()
            resp_hex = resp.hex() if resp else "no response"
            return True, f"{label} — {resp_hex}"
        except Exception as e:
            return False, f"Send failed: {e}"
    def _brightness_step(self, ip, port, id_byte: int, direction: int) -> tuple:
        """Query current brightness, step it, then require a Samsung ACK."""
        current = 50
        try:
            q = self._build_query(0x61, id_byte)
            sock = self.connect(ip, port)
            sock.sendall(q)
            resp = self._recv(sock, min_bytes=7, timeout=3)
            sock.close()
            data = self._parse_reply(resp)
            if data is not None:
                current = int(data)
        except Exception:
            pass
 
        new_level = max(0, min(100, current + direction * 10))
        try:
            pkt = self._build_set(0x61, id_byte, new_level)
            sock = self.connect(ip, port)
            sock.sendall(pkt)
            resp = self._recv(sock, min_bytes=6, timeout=2)
            sock.close()
            label = "Brightness Up" if direction > 0 else "Brightness Down"
            if self._is_ack(resp):
                return True, f"{label}: {current} -> {new_level} ACK {resp.hex()}"
            return False, f"{label} not acknowledged by display - {resp.hex() if resp else 'no response'}"
        except Exception as e:
            return False, f"Brightness set failed: {e}"
 
    def send_command(self, ip, port, display_id, command_key):
        """Send control command and require Samsung MDC ACK before reporting success."""
        if command_key not in self.COMMANDS:
            return False, f"Unknown command: {command_key}"
 
        try:
            socket.create_connection((ip, port), timeout=3).close()
        except Exception as e:
            return False, f"Device unreachable at {ip}:{port} ({e})"
 
        candidate_ids = self._candidate_ids(display_id)
 
        if command_key in ("brightness_up", "brightness_down"):
            direction = +1 if command_key == "brightness_up" else -1
            last_msg = ""
            for id_byte in candidate_ids:
                ok, msg = self._brightness_step(ip, port, id_byte, direction)
                if ok:
                    return True, f"{msg} (display_id={id_byte:02X})"
                last_msg = msg
            return False, last_msg or "Brightness command not acknowledged by Samsung display"
 
        raw_bytes, label = self.COMMANDS[command_key]
        last_error = ""
        sent_without_ack = None
 
        for id_byte in candidate_ids:
            cmd = self._inject_id(raw_bytes, id_byte)
            try:
                sock = self.connect(ip, port)
                sock.sendall(cmd)
                resp = self._recv(sock, min_bytes=6, timeout=2)
                sock.close()
                resp_hex = resp.hex() if resp else "no response"
                if self._is_ack(resp):
                    return True, f"{label} ACK from display_id={id_byte:02X} - {resp_hex}"
                last_error = f"display_id={id_byte:02X} returned {resp_hex}"
                if not resp and sent_without_ack is None:
                    sent_without_ack = id_byte
            except Exception as e:
                last_error = f"display_id={id_byte:02X} send failed: {e}"
 
        if sent_without_ack is not None:
            return True, (
                f"{label} sent to Samsung display_id={sent_without_ack:02X}; "
                "display did not return MDC ACK"
            )
 
        return False, f"{label} not acknowledged by Samsung display ({last_error})"
 
    def query_status(self, ip, port=1515, display_id="00"):
        """Query device status (power / input / volume / mute / brightness)."""
        status = {}
        id_byte = self._parse_id(display_id)
 
        INPUT_MAP = {
            0x04: "PC (RGB)",
            0x08: "AV",
            0x0C: "DVI",
            0x0F: "DisplayPort",
            0x14: "HDMI 1",
            0x18: "DisplayPort",
            0x1E: "HDMI 2",
            0x1F: "HDMI 3",
            0x21: "HDMI 1",
            0x23: "HDMI 2",
            0x31: "HDMI 3",
        }
        for label, raw_bytes in self.QUERY_COMMANDS.items():
            # Inject real display ID into query packet
            cmd = self._inject_id(raw_bytes, id_byte)
            try:
                sock = self.connect(ip, port)
                sock.sendall(cmd)
                response = self._recv(sock, min_bytes=7, timeout=3)
                sock.close()
 
                # FIX: use _parse_reply() which reads DATA from index 6 (not 5)
                data_byte = self._parse_reply(response)
                if data_byte is None:
                    continue
 
                if label == "power":
                    status["power"] = "ON" if data_byte == 0x01 else "OFF"
                    status["is_powered_on"] = (data_byte == 0x01)
                elif label == "input":
                    status["input"] = INPUT_MAP.get(data_byte, f"Unknown (0x{data_byte:02X})")
                elif label == "volume":
                    status["volume"] = int(data_byte)
                elif label == "mute":
                    status["mute"] = "ON" if data_byte == 0x01 else "OFF"
                elif label == "brightness":
                    status["brightness"] = int(data_byte)
 
            except Exception:
                pass
        return status
