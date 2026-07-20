
# """
# Manual Platform Plugin: CloudConnector
# """

# import socketio
# import logging
# import time
# import threading
# import platform
# import psutil
# import socket
# import json
# import base64
# import io
# import os
# import shutil
# import tempfile
# import zipfile
# import hashlib
# import subprocess
# import sys

# from socketio import exceptions as sio_exceptions

# from utils.config import Config

# from utils.state import EdgeState

# logger = logging.getLogger(__name__)


# class CloudConnector:

#     def __init__(self, config: dict):

#         self.config        = config

#         self.cloud_url     = config.get('CLOUD_URL', '')

#         self.api_key       = config.get('API_KEY', '')

#         self.edge_name     = config.get('EDGE_NAME', 'Edge-Collector')

#         self.location      = config.get('LOCATION', 'Unknown')

#         self.socketio_path = config.get('SOCKETIO_PATH', 'socket.io') or 'socket.io'

#         self.namespace     = config.get('SOCKETIO_NAMESPACE') or '/'

#         self.sio = socketio.Client(
#             reconnection=True,
#             reconnection_attempts=0,
#             reconnection_delay=5,
#             reconnection_delay_max=60
#         )

#         self.connected        = False

#         self.edge_id          = None

#         self.command_handlers = {}

#         self._watchlist      = []

#         self._watchlist_lock = threading.Lock()

#         self._polling_thread = None

#         self._polling_active = False

#         _current_file = os.path.abspath(__file__)
#         _services_dir = os.path.dirname(_current_file)
#         _backend_dir  = os.path.dirname(_services_dir)
#         _root_dir     = os.path.dirname(_backend_dir)

#         self.backend_dir   = _backend_dir
#         self.edge_root_dir = _root_dir

#         if _root_dir not in sys.path:
#             sys.path.insert(0, _root_dir)
#         if _backend_dir not in sys.path:
#             sys.path.insert(0, _backend_dir)

#         self._setup_socket_events()


#     # ══════════════════════════════════════════════════════════════
#     # SOCKET.IO EVENT SETUP
#     # ══════════════════════════════════════════════════════════════

#     def _setup_socket_events(self):

#         @self.sio.event(namespace=self.namespace)
#         def connect():
#             self.connected = True
#             EdgeState.set('cloud_connected', True)
#             logger.info(f"Connected to cloud: {self.cloud_url}")
#             self._register_edge()

#         @self.sio.event(namespace=self.namespace)
#         def disconnect():
#             self.connected       = False
#             self._polling_active = False
#             EdgeState.set('cloud_connected', False)
#             logger.warning("Disconnected from cloud. Will reconnect...")

#         @self.sio.on('registered', namespace=self.namespace)
#         def on_registered(data):
#             edge_id = (data or {}).get('edge_id')
#             if not edge_id:
#                 logger.warning("Registered event received without edge_id; keeping existing edge_id")
#                 return
#             self.edge_id = edge_id
#             EdgeState.set('edge_id', self.edge_id)
#             logger.info(f"Registered with cloud. edge_id={self.edge_id}")
#             self._start_polling()
#             threading.Thread(
#                 target=self._check_plugin_version,
#                 daemon=True
#             ).start()

#         @self.sio.on('registration_failed', namespace=self.namespace)
#         def on_registration_failed(data):
#             logger.error(f"Registration failed: {data.get('error')}. Check your API key.")
#             self.sio.disconnect()

#         @self.sio.on('sync_devices', namespace=self.namespace)
#         def on_sync_devices(data):
#             devices = data.get('devices', [])
#             with self._watchlist_lock:
#                 self._watchlist = devices
#             EdgeState.set('watchlist', devices)
#             try:
#                 summary = []
#                 for d in devices:
#                     summary.append({
#                         "ip": d.get("ip_address"),
#                         "port": d.get("port"),
#                         "plugin": d.get("plugin_name"),
#                         "protocol": d.get("protocol"),
#                     })
#                 logger.info(
#                     f"Watchlist synced: {len(devices)} devices to monitor | "
#                     f"devices={summary}"
#                 )
#             except Exception:
#                 logger.info(f"Watchlist synced: {len(devices)} devices to monitor")

#         @self.sio.on('plugin_update_bundle', namespace=self.namespace)
#         def on_plugin_update_bundle(data):
#             threading.Thread(
#                 target=self._apply_plugin_update,
#                 args=(data,),
#                 daemon=True
#             ).start()

#         @self.sio.on('command', namespace=self.namespace)
#         def on_command(data):
#             logger.info(f"Received command: {data.get('command_type')}")
#             threading.Thread(
#                 target=self._handle_command,
#                 args=(data,),
#                 daemon=True
#             ).start()

#         @self.sio.on('ping_edge', namespace=self.namespace)
#         def on_ping(data):
#             self._emit_safe('pong_edge', {
#                 'edge_id':   self.edge_id,
#                 'timestamp': time.time()
#             })


#     # ══════════════════════════════════════════════════════════════
#     # REGISTRATION
#     # ══════════════════════════════════════════════════════════════

#     def _register_edge(self):
#         """Send registration payload to cloud right after connecting."""
#         payload = {
#             'api_key':         self.api_key,
#             'edge_name':       self.edge_name,
#             'location':        self.location,
#             'os':              platform.system(),
#             'os_version':      platform.version(),
#             'hostname':        platform.node(),
#             'cpu_count':       psutil.cpu_count(),
#             'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
#             'agent_version':   '1.0.0',
#         }
#         self._emit_safe('register_edge', payload)
#         logger.info("Registration payload sent")

#     _MODEL_PLUGIN_MAP = {
#         # Occupancy Sensors
#         "CEN-ODT-C-POE":   "crestron_occupancy_sensor",
#         "CEN-ODT-C-POE-W": "crestron_occupancy_sensor",
#         "GLS-ODT-C-CN":    "crestron_occupancy_sensor",
#         # CP4N / 4-Series Control Systems
#         "CP4N":     "crestron_ssh",
#         "CP4":      "crestron_ssh",
#         "CP3":      "crestron_ssh",
#         "MC4":      "crestron_ssh",
#         "AV4":      "crestron_ssh",
#         "AM-3200":  "crestron_airmedia",
#         "RMC4":     "crestron_ssh",
#         "RMC3":     "crestron_ssh",
#         "4-SERIES": "crestron_ssh",
#         "AM-3000-WF-I":   "crestron_airmedia",
#         "AM-3200-WF":     "crestron_airmedia",
#         "AM-3200-WF-I":   "crestron_airmedia",
#         "AM-TX3-100-I":   "crestron_airmedia",
#         "AIRMEDIA":       "crestron_airmedia",
#         "TS-1070":     "crestron_ts1070",
#         "TST-1080":    "crestron_ts1070",
#         "TSW-1070":    "crestron_ts1070",
#         "TS-1542":     "crestron_ts1070",
#         "TS-770":      "crestron_ts1070",
#         "TSS-1070":    "crestron_ts1070",
#         "TSS-770":     "crestron_ts1070",
#         "TSS-752":     "crestron_ts1070",
#         "TSS-1060":    "crestron_ts1070",
#         "MMX4X2-HDMI":         "lightware_mmx",
#         "MMX4X2-HT200":        "lightware_mmx",
#         "MMX4X2-HDMI-USB20-L": "lightware_mmx",
#         "TesiraFORTE":     "tesira",
#         "TesiraFORTE X":   "tesira",
#         "Tesira SERVER":   "tesira",
#         "Tesira SERVER-IO":"tesira",
#         "TesiraLUX":       "tesira",
#         "TesiraAMP":       "tesira",
#         "Voltera":         "tesira",
#         "Room Bar Pro":    "cisco_roomos",
#         "Room Bar":        "cisco_roomos",
#         "Webex Room Kit":  "cisco_roomos",
#         "Room Kit":        "cisco_roomos",
#         "TCBarM":          "sennheiser_tcbarm",
#         "TC Bar M":        "sennheiser_tcbarm",
#         "VIA":             "kramer_via",
#         "Connect 2":       "kramer_via",
#         "Connect 2 (VIA)": "kramer_via",
#         "VIA Connect 2":   "kramer_via",
#         "P300":          "shure_p300",
#         "ANIUSB-MATRIX": "shure_p300",
#         "ANIUSB":        "shure_p300",
#          "DM-NVX-350":   "crestron_nvx",
#         "DM-NVX-351":   "crestron_nvx",
#         "DM-NVX-352":   "crestron_nvx",
#         "DM-NVX-360":   "crestron_nvx",
#         "DM-NVX-361":   "crestron_nvx",
#         "DM-NVX-362":   "crestron_nvx",
#         "DM-NVX-363":   "crestron_nvx",
#         "DM-NVX-364":   "crestron_nvx",
#         "DM-NVX-365":   "crestron_nvx",
#         "DM-NVX-366":   "crestron_nvx",
#         "DM-NVX-370":   "crestron_nvx",
#         "DM-NVX-371":   "crestron_nvx",
#         "DM-NVX-372":   "crestron_nvx",
#         "DM-NVX-373":   "crestron_nvx",
#         "DM-NVX-374":   "crestron_nvx",
#         "DM-NVX-375":   "crestron_nvx",
#         "DM-NVX-376":   "crestron_nvx",
#         "DM-NVX-380":   "crestron_nvx",
#         "DM-NVX-381":   "crestron_nvx",
#         "DM-NVX-382":   "crestron_nvx",
#         "DM-NVX-383":   "crestron_nvx",
#         "DM-NVX-384":   "crestron_nvx",
#         "DM-NVX-385":   "crestron_nvx",
#         "DM-NVX-386":   "crestron_nvx",
#         "DM-NVX-D30":   "crestron_nvx",
#         "DM-NVX-D30C":  "crestron_nvx",
#         "DM-NVX-E30":   "crestron_nvx",
#         "DM-NVX-E30C":  "crestron_nvx",
 
#     }
#     _PLUGIN_ALIASES = {
#         # Samsung
#         "samsung":     "samsung_mdc",
#         "samsung_mdc": "samsung_mdc",
#         "lg":         "lg_55ef5gl",
#         "lg_55ef5gl": "lg_55ef5gl",
#         "sennheiser":          "sennheiser_tccm",
#         "sennheiser_tccm":     "sennheiser_tccm",
#         "sennheiser_tcbar_m":  "sennheiser_tcbarm",
#         "sennheiser_tcbarm":   "sennheiser_tcbarm",
#         "sennheiser tcbar m":  "sennheiser_tcbarm",
#         "sennheiser tc bar m": "sennheiser_tcbarm",
#         "sennheiser tcbarm":   "sennheiser_tcbarm",
#         "tcbar m":             "sennheiser_tcbarm",
#         "tc bar m":            "sennheiser_tcbarm",
#         "tcc m":               "sennheiser_tccm",
#         "tccm":                "sennheiser_tccm",
#         "shure":        "shure_mxa920",
#         "shure_mxa920": "shure_mxa920",
#         "mxa920":       "shure_mxa920",
#         "shure_p300":    "shure_p300",
#         "p300":          "shure_p300",
#         "aniusb":        "shure_p300",
#         "aniusb-matrix": "shure_p300",
#         "aniusb_matrix": "shure_p300",
#         "brightsign": "brightsign",
#         "crestron_occupancy_sensor": "crestron_occupancy_sensor",
#         "crestron_cp4n":             "crestron_ssh",
#         "crestron_ssh":              "crestron_ssh",
#         "cp4n":                      "crestron_ssh",
#         "crestron":                  "crestron_ssh",
#         "crestron_ts1070":           "crestron_ts1070",
#         "ts1070":                    "crestron_ts1070",
#         "ts-1070":                   "crestron_ts1070",
#         "crestron_ts-1070":          "crestron_ts1070",
#         "touchpanel":                "crestron_ts1070",
#         "touch panel":               "crestron_ts1070",
#         "crestron_airmedia":         "crestron_airmedia",
#         "airmedia":                  "crestron_airmedia",
#         "am-3200":                   "crestron_airmedia",
#         "am3200":                    "crestron_airmedia",
#         "am-3000":                   "crestron_airmedia",
#         "am3000":                    "crestron_airmedia",
#         "am-tx3":                    "crestron_airmedia",
#         "tx3":                       "crestron_airmedia",
#         "barco":                      "barco_clickshare",
#         "barco_clickshare":           "barco_clickshare",
#         "barco_clickshare_c_series":  "barco_clickshare",
#         "barco_clickshare_cx_series": "barco_clickshare",
#         "lightware_ucx": "lightware",
#         "lightware_mmx": "lightware_mmx",

#         "poly_videoos": "poly_videoos",
#         "poly":         "poly_videoos",

#         "tesira":       "tesira",
#         "biamp":        "tesira",

#         "power_conditioner": "power_conditioner",
#         "vector":            "power_conditioner",
#         "powerconditioner":  "power_conditioner",

#         "cisco_roomos": "cisco_roomos",
#         "cisco":        "cisco_roomos",

#         "kramer":     "kramer_via",
#         "kramer_via": "kramer_via",
#         "via":        "kramer_via",
#         "connect 2":  "kramer_via",
#         "crestron_nvx":          "crestron_nvx",
#         "nvx":                   "crestron_nvx",
#         "dm-nvx":                "crestron_nvx",
#         "dm_nvx":                "crestron_nvx",
#         "crestron_nvx_360":      "crestron_nvx",
#         "crestron_nvx_350":      "crestron_nvx",
#         "nvx_360":               "crestron_nvx",
#         "nvx_350":               "crestron_nvx",
 
#     }

#     def _model_plugin_match(self, params: dict = None) -> str:
#         if not params:
#             return ""

#         config = params.get("plugin_config") if isinstance(params.get("plugin_config"), dict) else {}
#         values = [
#             params.get("model"),
#             params.get("device_type"),
#             params.get("device_name"),
#             config.get("model"),
#             config.get("device_type"),
#             config.get("device_name"),
#         ]
#         haystack = " ".join(
#             str(v or "").upper().replace("-", "").replace(" ", "") for v in values
#         )

#         for model, plugin_key in self._MODEL_PLUGIN_MAP.items():
#             normalised_model = model.upper().replace("-", "").replace(" ", "")
#             if normalised_model in haystack:
#                 logger.debug(f"[PLUGIN] Model-based resolution: '{model}' -> '{plugin_key}'")
#                 return plugin_key

#         oem_name = str(params.get("oem_name") or config.get("oem_name") or "").lower()

#         if "airmedia" in oem_name or "am-" in oem_name:
#             logger.info(f"[PLUGIN] AirMedia detected via oem_name: '{oem_name}' -> crestron_airmedia")
#             return "crestron_airmedia"
#         if "occupancy" in oem_name:
#             return "crestron_occupancy_sensor"
#         if "cp4n" in oem_name or "crestron_ssh" in oem_name:
#             return "crestron_ssh"
#         if any(x in oem_name for x in ("ts1070", "tss", "tst", "tsw", "touchpanel", "touch")):
#             logger.info(f"[PLUGIN] TS-1070 detected via oem_name: '{oem_name}' -> crestron_ts1070")
#             return "crestron_ts1070"
#         if "mmx" in oem_name:
#             return "lightware_mmx"
#         # ── FIX: P300/ANIUSB must be checked BEFORE the generic "shure" guard ──
#         if any(x in oem_name for x in ("p300", "aniusb")):
#             return "shure_p300"
#         if "shure" in oem_name:
#             return "shure_mxa920"
#         if any(x in oem_name for x in ("mxa920", "mxa910", "mxa902", "mxa710")):
#             return "shure_mxa920"
#         if "samsung" in oem_name and "mdc" in oem_name:
#             return "samsung_mdc"
#         if "cisco" in oem_name and "room" in oem_name:
#             return "cisco_roomos"
#         if any(x in oem_name for x in ("Room Bar Pro", "Room Bar", "Webex Room Kit", "Room Kit")):
#             return "cisco_roomos"
#         if "sennheiser" in oem_name and ("tcbarm" in oem_name or "tcbar" in oem_name or "tc bar" in oem_name):
#             return "sennheiser_tcbarm"
#         if any(x in oem_name for x in ("tcbarm", "tcbar", "tc bar m", "sennheiser_tcbar_m")):
#             return "sennheiser_tcbarm"
#         if "kramer" in oem_name and "via" in oem_name:
#             return "kramer_via"
#         if any(x in oem_name for x in ("via", "connect 2", "kramer")) and "kramer" in oem_name:
#             return "kramer_via"

#         return ""

#     def _normalize_plugin_name(self, raw_name: str, params: dict = None) -> str:
#         """
#         Resolve a raw plugin name / make string to the exact plugin registry key.

#         Resolution order:
#           1. If raw_name is already a known specific key → return it directly.
#           2. If raw_name is a generic make (e.g. 'crestron') AND a model is present
#              in params → look up model in _MODEL_PLUGIN_MAP for precision.
#           3. Fall back to _PLUGIN_ALIASES generic make entry.
#           4. Return the cleaned name as-is.
#         """
#         name = (raw_name or "").strip().lower().replace("manual_", "")
#         model_plugin = self._model_plugin_match(params)

#         # Step 1: direct alias lookup
#         if name in self._PLUGIN_ALIASES:
#             resolved = self._PLUGIN_ALIASES[name]
#             # Model-based resolution takes priority for ambiguous generic names
#             if name in ["crestron_ssh", "crestron_occupancy_sensor",
#                         "crestron_cp4n", "crestron_ts1070"]:
#                 return name
#             if params and resolved == self._PLUGIN_ALIASES.get("crestron"):
#                 model = (params.get("model") or "").strip()
#                 if model and model in self._MODEL_PLUGIN_MAP:
#                     logger.debug(
#                         f"[PLUGIN] Model-based resolution: '{model}' → "
#                         f"'{self._MODEL_PLUGIN_MAP[model]}'"
#                     )
#                     return self._MODEL_PLUGIN_MAP[model]
#             return resolved

#         if model_plugin:
#             return model_plugin

#         # Step 2: try model-based resolution directly
#         if params:
#             model = (params.get("model") or "").strip()
#             if model and model in self._MODEL_PLUGIN_MAP:
#                 logger.debug(
#                     f"[PLUGIN] Model-based resolution (no alias): '{model}' → "
#                     f"'{self._MODEL_PLUGIN_MAP[model]}'"
#                 )
#                 return self._MODEL_PLUGIN_MAP[model]

#         # Step 3: return cleaned name as-is
#         logger.debug(f"[PLUGIN] No alias found for '{name}', using as-is")
#         return name


#     # ══════════════════════════════════════════════════════════════
#     # COMMAND HANDLING
#     # ══════════════════════════════════════════════════════════════

#     # def _handle_command(self, data: dict):
#     #     """Route incoming command to the correct handler."""
#     #     command_type = data.get('command_type', '')
#     #     command_id   = data.get('command_id')
#     #     params       = data.get('params', {})

#     #     try:
#     #         if command_type == 'probe_device':
#     #             self._handle_probe_device(command_id, params)
#     #             return

#     #         if command_type in ('query_device_status', 'device_status', 'query_status',
#     #                            'get_status', 'device_query', 'query_device', 'status'):
#     #             self._handle_device_status(command_id, params)
#     #             return

#     #         if command_type in ('device_command', 'device_control', 'send_command',
#     #                            'control_device', 'execute_command', 'run_command', 'command'):
#     #             self._handle_device_control(command_id, params)
#     #             return

#     #         handler = self.command_handlers.get(command_type)

#     #         if handler:
#     #             try:
#     #                 result = handler(data.get('device_id'), params)
#     #                 self.send_command_result(command_id, 'success', result)
#     #             except Exception as e:
#     #                 logger.error(f"Command '{command_type}' failed: {e}")
#     #                 self.send_command_result(command_id, 'failed', str(e))
#     #         else:
#     #             logger.warning(f"No handler registered for command: {command_type}")
#     #             self.send_command_result(command_id, 'failed', f'Unknown command: {command_type}')

#     #     except Exception as e:
#     #         logger.exception(f"Command '{command_type}' failed")
#     #         self.send_command_result(command_id, 'failed', {'error': str(e)})


#     def _handle_command(self, data: dict):
#         command_type = data.get('command_type', '')
#         command_id = data.get('command_id')
#         params = data.get('params', {})

#         try:
#             # Device probe
#             if command_type == 'probe_device':
#                 self._handle_probe_device(command_id, params)
#                 return

#             # Device status commands
#             if command_type in (
#                 'query_device_status',
#                 'device_status',
#                 'query_status',
#                 'get_status',
#                 'device_query',
#                 'query_device',
#                 'status'
#             ):
#                 self._handle_device_status(command_id, params)
#                 return

#             # Device control commands
#             if command_type in (
#                 'device_command',
#                 'device_control',
#                 'send_command',
#                 'control_device',
#                 'execute_command',
#                 'run_command',
#                 'command'
#             ):
#                 self._handle_device_control(command_id, params)
#                 return

#             # Registered custom handlers
#             handler = self.command_handlers.get(command_type)

#             if handler:
#                 try:
#                     result = handler(data.get('device_id'), params)
#                     self.send_command_result(command_id, 'success', result)
#                 except Exception as e:
#                     logger.error(f"Command '{command_type}' failed: {e}")
#                     self.send_command_result(command_id, 'failed', str(e))

#             else:
#                 logger.warning(
#                     f"No handler registered for command: {command_type}"
#                 )

#                 # Safety net: route unknown commands that look like device commands
#                 if params.get('ip') and (
#                     params.get('plugin_name') or params.get('make')
#                 ):
#                     logger.warning(
#                         f"[EDGE] Routing unrecognized "
#                         f"command_type='{command_type}' "
#                         f"to device_control handler as fallback"
#                     )

#                     if not params.get('command_key') and not params.get('command'):
#                         params['command_key'] = command_type
#                         params['command'] = command_type

#                     self._handle_device_control(command_id, params)

#                 else:
#                     self.send_command_result(
#                         command_id,
#                         'failed',
#                         f'Unknown command: {command_type}'
#                     )

#         except Exception as e:
#             logger.exception(f"Command '{command_type}' failed")
#             self.send_command_result(
#                 command_id,
#                 'failed',
#                 {'error': str(e)}
#         )
   
   
#     def _load_plugin_for_command(self, params: dict):
#         """Load the appropriate plugin based on command parameters."""
#         plugin_name   = params.get('plugin_name') or params.get('make') or ''
#         clean_name    = self._normalize_plugin_name(plugin_name, params)
#         plugin_config = params.get('plugin_config') or {}

#         local_plugin_configs = self.config.get('PLUGIN_CONFIGS', {})
#         merged_config = {**local_plugin_configs.get(clean_name, {}), **plugin_config}

#         logger.debug(f"[PLUGIN] Loading plugin: raw='{plugin_name}' → resolved='{clean_name}'")

#         try:
#             if self.backend_dir not in sys.path:
#                 sys.path.insert(0, self.backend_dir)
#             from plugin import get_plugin
#             logger.info(f"[PLUGIN] Successfully imported get_plugin from backend/plugin")
#         except ImportError as e:
#             logger.error(f"Failed to import from backend.plugin: {e}")
#             try:
#                 import importlib.util
#                 plugin_init_path = os.path.join(self.backend_dir, 'plugin', '__init__.py')
#                 logger.info(f"[PLUGIN] Trying to load from: {plugin_init_path}")
#                 if os.path.exists(plugin_init_path):
#                     spec = importlib.util.spec_from_file_location("plugin_module", plugin_init_path)
#                     plugin_module = importlib.util.module_from_spec(spec)
#                     spec.loader.exec_module(plugin_module)
#                     get_plugin = plugin_module.get_plugin
#                     logger.info(f"[PLUGIN] Loaded from file: {plugin_init_path}")
#                 else:
#                     raise ImportError(f"plugin __init__.py not found at {plugin_init_path}")
#             except Exception as e2:
#                 logger.error(f"All import attempts failed: {e2}")
#                 raise RuntimeError(f"Plugin system not available: {e2}")

#         plugin = get_plugin(clean_name, config=merged_config)
#         if not plugin:
#             raise RuntimeError(f"Plugin not found for '{plugin_name}' (normalized='{clean_name}')")

#         return plugin, clean_name

#     def _handle_device_status(self, command_id: str, params: dict):
#         """Handle device status query command."""
#         try:
#             plugin, clean_name = self._load_plugin_for_command(params)

#             ip = params.get('ip')
#             if not ip:
#                 self.send_command_result(command_id, 'failed', {'error': 'ip is required'})
#                 return

#             port       = int(params.get('port') or getattr(plugin, 'default_port', None))
#             display_id = str(params.get('display_id') or "00")

#             logger.info(f"Querying status for {ip}:{port} using plugin '{clean_name}'")

#             status = plugin.query_status(ip=ip, port=port, display_id=display_id)

#             if not status:
#                 status = {}

#             if 'reachable' not in status:
#                 status['reachable'] = status.get('current_status') in ('Normal', 'Online', 'Ready')

#             self.send_command_result(command_id, 'success', status)
#             logger.info(f"Status query success for {ip}: reachable={status.get('reachable')}")

#         except Exception as e:
#             logger.error(f"Device status query failed: {e}")
#             self.send_command_result(command_id, 'failed', {'error': str(e)})

#     def _handle_device_control(self, command_id: str, params: dict):
#         """Handle device control command."""
#         try:
#             plugin, clean_name = self._load_plugin_for_command(params)

#             ip      = params.get('ip')
#             command = params.get('command_key') or params.get('command')
#              # ADD THIS:
#             logger.info(f"[DEBUG _handle_device_control] clean_name={clean_name!r} ip={ip!r} command={command!r} params_keys={list(params.keys())}")

#             if not ip or not command:
#                 self.send_command_result(
#                     command_id, 'failed',
#                     {'error': 'ip and command are required'}
#                 )
#                 return

#             port       = int(params.get('port') or getattr(plugin, 'default_port', 443))
#             display_id = str(params.get('display_id') or "00")
#             cmd_params = params.get('params') or {}

#             logger.info(
#                 f"Executing command '{command}' on {ip}:{port} "
#                 f"using plugin '{clean_name}' with params={cmd_params}"
#             )

#             # ── helper: unwrap ManualPlatformPlugin dict response ──────────
#             def _unpack_manual(raw):
#                 """
#                 ManualPlatformPlugin.send_command returns
#                   {"success": bool, "result": ..., "error": ...}
#                 Convert to (ok, msg) tuple.
#                 """
#                 if isinstance(raw, dict):
#                     ok  = bool(raw.get("success", False))
#                     _r  = raw.get("result")
#                     if isinstance(_r, str) and _r:
#                         msg = _r
#                     elif isinstance(_r, dict):
#                         msg = _r.get("message") or str(_r)
#                     else:
#                         msg = raw.get("error") or ("ok" if ok else "Command failed")
#                     return ok, msg
#                 # legacy tuple fallback
#                 return raw

#             # ── Route to correct send_command signature per plugin ─────────
#             if "samsung" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command_key=command
#                 )
#             elif "brightsign" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command={"action": command, "params": cmd_params}
#                 )
#             elif "lg" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command
#                 )
#             elif "crestron" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command, params=cmd_params
#                 )
#             elif "barco" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command
#                 )
#             elif "lightware" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command, params=cmd_params
#                 )
#             elif "poly" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command, params=cmd_params
#                 )
#             elif "tesira" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command, params=cmd_params
#                 )
#             elif "power_conditioner" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command, params=cmd_params
#                 )
#             elif "shure" in clean_name:
#                 # ── FIX: ManualPlatformPlugin returns {"success":..., "result":...}
#                 # NOT a tuple. Also pass command as a dict so ShureP300Plugin's
#                 # isinstance(command, dict) branch fires correctly, which then
#                 # dispatches to the right action handler (inc_channel_gain etc.)
#                 _raw = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command={"action": command, "params": cmd_params}
#                 )
#                 ok, msg = _unpack_manual(_raw)
#             elif "cisco_roomos" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command, params=cmd_params
#                 )
#             elif "sennheiser_tcbarm" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command, params=cmd_params
#                 )
#             elif "kramer_via" in clean_name:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command, params=cmd_params
#                 )
#             else:
#                 ok, msg = plugin.send_command(
#                     ip=ip, port=port, display_id=display_id,
#                     command=command, params=cmd_params
#                 )

#             if ok:
#                 if isinstance(msg, (dict, list)):
#                     self.send_command_result(command_id, 'success', msg)
#                 else:
#                     self.send_command_result(command_id, 'success', {'message': str(msg)})
#                 logger.info(f"Command '{command}' succeeded on {ip}")
#             else:
#                 self.send_command_result(command_id, 'failed', {'error': str(msg)})
#                 logger.warning(f"Command '{command}' failed on {ip}: {msg}")

#         except Exception as e:
#             logger.error(f"Device control command failed: {e}")
#             self.send_command_result(command_id, 'failed', {'error': str(e)})


#     def _handle_probe_device(self, command_id: str, params: dict):
#         """
#         Cloud asks edge to probe a local device and return its full info.
#         """
#         ip            = params.get('ip')
#         port          = params.get('port')
#         display_id    = str(params.get('display_id') or "00")
#         plugin_name   = params.get('plugin_name', '')
#         plugin_config = params.get('plugin_config') or {}

#         logger.info(f"=== PROBE REQUEST === IP: {ip}, Port: {port}, Plugin: {plugin_name}")
#         logger.info(f"Probing device: {ip}:{port} plugin={plugin_name}")

#         try:
#             device_info = self._probe_device(ip, port, plugin_name, display_id, plugin_config)
#             logger.info(f"=== PROBE RESULT === Model: {device_info.get('model')}, Status: {device_info.get('current_status')}")
#             self.send_command_result(command_id, 'success', device_info)
#             logger.info(
#                 f"Probe success: {ip} -> "
#                 f"model={device_info.get('model', '?')} "
#                 f"serial={device_info.get('serial_number', '?')} "
#                 f"status={device_info.get('current_status', '?')}"
#             )
#             logger.info(f"Probe device_info: {device_info}")
#         except Exception as e:
#             logger.error(f"Probe failed for {ip}:{port} – {e}")
#             self.send_command_result(command_id, 'failed', {
#                 'error':          str(e),
#                 'ip_address':     ip,
#                 'current_status': 'Offline'
#             })


#     def _probe_device(self, ip: str, port, plugin_name: str, display_id: str, plugin_config: dict) -> dict:
#         """Use the real plugin to probe the device."""
#         clean_name = self._normalize_plugin_name(plugin_name, {"plugin_config": plugin_config})

#         logger.info(f"=== PROBE DEVICE === IP: {ip}, Display ID: {display_id}, Original plugin: {plugin_name}, Clean name: {clean_name}")

#         local_plugin_configs = self.config.get('PLUGIN_CONFIGS', {})
#         local_config         = local_plugin_configs.get(clean_name, {})
#         merged_config        = {**local_config, **plugin_config}

#         try:
#             from plugin import get_plugin, PLUGIN_REGISTRY
#         except ImportError:
#             logger.error("[PROBE] plugin package not found in backend/. Falling back to TCP ping.")
#             return self._tcp_only_probe(ip, port)

#         plugin = get_plugin(clean_name, config=merged_config)

#         if not plugin:
#             available = list(PLUGIN_REGISTRY.keys())
#             logger.warning(
#                 f"[PROBE] Plugin '{clean_name}' not found in registry. "
#                 f"Available plugins: {available}. Falling back to TCP ping."
#             )
#             return self._tcp_only_probe(ip, port)

#         if port is None or str(port).strip() == '' or int(port) <= 0:
#             port = getattr(plugin, 'default_port', 1515)
#         port = int(port)

#         logger.info(f"[PROBE] Running plugin '{clean_name}' on {ip}:{port}")
#         try:
#             device_info = plugin.get_device_info(ip, port, display_id)
#             logger.info(f"=== DEVICE INFO === {device_info}")
#             if not device_info.get('ip_address'):
#                 device_info['ip_address'] = ip
#             return device_info
#         except Exception as e:
#             logger.error(f"[PROBE] Plugin '{clean_name}' execution failed: {e}")
#             raise


#     def _tcp_only_probe(self, ip: str, port) -> dict:
#         """Fallback when no matching plugin found."""
#         port = int(port) if port else 80
#         try:
#             sock = socket.create_connection((ip, port), timeout=5)
#             sock.close()
#             status = 'Online'
#         except Exception:
#             status = 'Offline'
#         return {
#             'device_name':    f"Device at {ip}",
#             'make':           'Unknown',
#             'model':          'Unknown',
#             'serial_number':  '',
#             'firmware':       '',
#             'mac_address':    '',
#             'ip_address':     ip,
#             'current_status': status,
#         }


#     def _start_polling(self):
#         """Start background thread that polls watchlist devices every 60s."""
#         if self._polling_thread and self._polling_thread.is_alive():
#             return
#         self._polling_active = True
#         self._polling_thread = threading.Thread(
#             target=self._polling_loop,
#             daemon=True
#         )
#         self._polling_thread.start()
#         logger.info("Status polling loop started (every 60s)")


#     def _polling_loop(self):
#         """Every 60 seconds: snapshot watchlist, TCP ping each device, push status."""
#         while self._polling_active and self.connected:
#             try:
#                 with self._watchlist_lock:
#                     watchlist = list(self._watchlist)
#                 if watchlist:
#                     statuses = self._poll_all_devices(watchlist)
#                     self._send_status_update(statuses)
#                     online_count = sum(1 for s in statuses if s['status'] == 'Online')
#                     logger.info(f"Status poll: {online_count}/{len(statuses)} devices online")
#                 else:
#                     logger.debug("Watchlist empty, skipping poll")
#             except Exception as e:
#                 logger.error(f"Polling loop error: {e}")
#             for _ in range(60):
#                 if not self._polling_active or not self.connected:
#                     break
#                 time.sleep(1)


#     def _poll_all_devices(self, watchlist: list) -> list:
#         """TCP ping every device. Deep poll Samsung for live power/input/volume."""
#         statuses = []
#         for dev in watchlist:
#             ip   = dev.get('ip_address')
#             port = dev.get('port')
#             if not ip:
#                 continue
#             if not port or int(port) <= 0:
#                 port = 443
#             port = int(port)

#             plugin_name = (dev.get('plugin_name') or '').lower()
#             reachable   = self._tcp_ping(ip, port)

#             entry = {
#                 'ip_address': ip,
#                 'status':     'Online' if reachable else 'Offline',
#             }

#             if reachable and 'samsung' in plugin_name:
#                 try:
#                     from plugin import get_plugin
#                     samsung = get_plugin('samsung_mdc')
#                     if samsung:
#                         display_id = str(dev.get('display_id') or 'FE')
#                         live = samsung.query_status(ip=ip, port=port, display_id=display_id)
#                         if live:
#                             entry.update(live)
#                 except Exception:
#                     pass

#             statuses.append(entry)
#         return statuses


#     def _tcp_ping(self, ip: str, port: int, timeout: int = 3) -> bool:
#         """TCP connect check."""
#         try:
#             sock = socket.create_connection((ip, port), timeout=timeout)
#             sock.close()
#             return True
#         except (socket.timeout, ConnectionRefusedError, OSError):
#             return False


#     def _send_status_update(self, statuses: list):
#         """Push status_update event to cloud."""
#         if self.connected and self.edge_id:
#             try:
#                 logger.info(
#                     f"Emitting status_update edge_id={self.edge_id} devices={statuses}"
#                 )
#             except Exception:
#                 logger.info(
#                     f"Emitting status_update edge_id={self.edge_id} devices_count={len(statuses)}"
#                 )
#             self._emit_safe('status_update', {
#                 'edge_id': self.edge_id,
#                 'devices': statuses,
#             })


#     # ══════════════════════════════════════════════════════════════
#     # PLUGIN UPDATE
#     # ══════════════════════════════════════════════════════════════

#     def _get_plugin_dir(self):
#         return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugin"))

#     def _get_local_plugin_version(self):
#         version_path = os.path.join(self._get_plugin_dir(), "version.json")
#         if not os.path.exists(version_path):
#             return ""
#         try:
#             with open(version_path, "r", encoding="utf-8") as f:
#                 data = json.load(f)
#             if isinstance(data, dict):
#                 return data.get("version", "")
#         except Exception as e:
#             logger.warning(f"[EDGE] Failed to read local plugin version: {e}")
#         return ""

#     def _check_plugin_version(self):
#         if not self.connected:
#             return
#         current_version = self._get_local_plugin_version()
#         self._emit_safe('plugin_version_check', {
#             'version': current_version,
#             'timestamp': time.time(),
#         })

#     def _apply_plugin_update(self, payload: dict):
#         if not payload:
#             return
#         version = payload.get('version') or ''
#         zip_b64 = payload.get('zip_b64')
#         manifest = payload.get('manifest') or []
#         if not zip_b64:
#             return

#         plugin_dir = self._get_plugin_dir()
#         os.makedirs(plugin_dir, exist_ok=True)
#         temp_dir = tempfile.mkdtemp(prefix="plugin_update_")
#         added_files = []
#         updated_files = []
#         try:
#             def _hash_file(path):
#                 h = hashlib.sha256()
#                 with open(path, "rb") as fh:
#                     for chunk in iter(lambda: fh.read(8192), b""):
#                         h.update(chunk)
#                 return h.hexdigest()

#             zip_bytes = base64.b64decode(zip_b64.encode('ascii'))
#             with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
#                 zf.extractall(temp_dir)

#             for root, _, files in os.walk(temp_dir):
#                 for name in files:
#                     if name == "__init__.py":
#                         continue
#                     if not (name.endswith(".py") or name == "version.json"):
#                         continue
#                     src = os.path.join(root, name)
#                     dst = os.path.join(plugin_dir, name)
#                     if name.endswith(".py"):
#                         if os.path.exists(dst):
#                             try:
#                                 if _hash_file(src) != _hash_file(dst):
#                                     updated_files.append(name)
#                             except Exception:
#                                 updated_files.append(name)
#                         else:
#                             added_files.append(name)
#                     shutil.copy2(src, dst)

#             if version:
#                 version_path = os.path.join(plugin_dir, "version.json")
#                 version_doc = {
#                     "version": version,
#                     "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
#                 }
#                 if manifest:
#                     version_doc["manifest"] = manifest
#                 with open(version_path, "w", encoding="utf-8") as f:
#                     json.dump(version_doc, f, indent=2)

#             if manifest:
#                 self._write_plugin_init(manifest)

#             added_files_label   = ",".join(sorted(set(added_files)))   if added_files   else "none"
#             updated_files_label = ",".join(sorted(set(updated_files))) if updated_files else "none"
#             logger.info(
#                 f"[EDGE] Plugin update applied: version={version} "
#                 f"added_files={added_files_label} updated_files={updated_files_label}"
#             )

#             if (added_files or updated_files) and self.config.get("RESTART_ON_PLUGIN_UPDATE", True):
#                 logger.info("[EDGE] Plugin update detected changes; restarting Edge Collector")
#                 self._restart_self()
#         except Exception as e:
#             logger.error(f"[EDGE] Plugin update failed: {e}")
#         finally:
#             try:
#                 shutil.rmtree(temp_dir)
#             except Exception:
#                 pass

#     def _restart_self(self):
#         """Restart the Edge Collector process after plugin updates."""
#         try:
#             backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
#             args = [sys.executable] + sys.argv
#             subprocess.Popen(args, cwd=backend_dir)
#         except Exception as e:
#             logger.error(f"[EDGE] Failed to restart Edge Collector: {e}")
#             return
#         os._exit(0)

#     # def _write_plugin_init(self, manifest):
#     #     """Write a dynamic __init__.py for the plugin package."""
#     #     plugin_dir = self._get_plugin_dir()

#     #     content = (
#     #         "\"\"\"\n"
#     #         "Manual Platform Plugin SDK\n"
#     #         "==========================\n"
#     #         "Package for manual platform plugins (Samsung MDC, Q-SYS, etc.)\n"
#     #         "\"\"\"\n\n"
#     #         "import os\n"
#     #         "import pkgutil\n"
#     #         "import importlib\n"
#     #         "import inspect\n"
#     #         "import logging\n\n"
#     #         "from .base import ManualPlatformPlugin\n\n"
#     #         "logger = logging.getLogger(__name__)\n\n"
#     #         "# Plugin registry (populated dynamically)\n"
#     #         "PLUGIN_REGISTRY = {}\n\n"
#     #         "def discover_plugins():\n"
#     #         "    \"\"\"Dynamically discover and register all plugin classes in this package.\"\"\"\n"
#     #         "    global PLUGIN_REGISTRY\n"
#     #         "    PLUGIN_REGISTRY = {}\n"
#     #         "    plugin_dir = os.path.dirname(__file__)\n"
#     #         "    for loader, module_name, is_pkg in pkgutil.walk_packages([plugin_dir]):\n"
#     #         "        if module_name in [\"base\", \"__init__\"]:\n"
#     #         "            continue\n"
#     #         "        try:\n"
#     #         "            module = importlib.import_module(f\".{module_name}\", package=__package__)\n"
#     #         "            for name, obj in inspect.getmembers(module):\n"
#     #         "                if (inspect.isclass(obj) and issubclass(obj, ManualPlatformPlugin) and obj is not ManualPlatformPlugin):\n"
#     #         "                    plugin_key = getattr(obj, \"name\", module_name.replace(\"_plugin\", \"\"))\n"
#     #         "                    PLUGIN_REGISTRY[plugin_key] = obj\n"
#     #         "        except Exception as e:\n"
#     #         "            logger.error(f\"Failed to load plugin module {module_name}: {e}\")\n\n"
#     #         "discover_plugins()\n"
#     #         "logger.info(f\"Loaded {len(PLUGIN_REGISTRY)} plugins: {', '.join(sorted(PLUGIN_REGISTRY.keys()))}\")\n\n"
#     #         "def get_plugin(plugin_name, config=None):\n"
#     #         "    plugin_class = PLUGIN_REGISTRY.get(plugin_name)\n"
#     #         "    if plugin_class:\n"
#     #         "        plugin = plugin_class(config)\n"
#     #         "        _wrap_plugin_device_info(plugin)\n"
#     #         "        return plugin\n"
#     #         "    return None\n\n"
#     #         "def get_available_plugins():\n"
#     #         "    plugins = []\n"
#     #         "    for name, plugin_class in PLUGIN_REGISTRY.items():\n"
#     #         "        try:\n"
#     #         "            instance = plugin_class()\n"
#     #         "            plugins.append({\n"
#     #         "                \"name\": getattr(instance, \"name\", name),\n"
#     #         "                \"display_name\": getattr(instance, \"display_name\", name),\n"
#     #         "                \"description\": getattr(instance, \"description\", \"\"),\n"
#     #         "                \"supports_display_id\": getattr(instance, \"supports_display_id\", True),\n"
#     #         "                \"supports_port\": getattr(instance, \"supports_port\", True),\n"
#     #         "                \"default_port\": getattr(instance, \"default_port\", 1515),\n"
#     #         "                \"supported_models\": getattr(instance, \"SUPPORTED_MODELS\", []),\n"
#     #         "            })\n"
#     #         "        except Exception: pass\n"
#     #         "    return plugins\n\n"
#     #         "def _normalize_device_info(info, ip, port, display_id, plugin):\n"
#     #         "    if info is None: info = {}\n"
#     #         "    info.setdefault(\"ip_address\", ip)\n"
#     #         "    info.setdefault(\"port\", port)\n"
#     #         "    info.setdefault(\"display_id\", display_id)\n"
#     #         "    make = info.get(\"make\") or getattr(plugin, \"display_name\", None) or \"Unknown\"\n"
#     #         "    info[\"make\"] = make\n"
#     #         "    model = info.get(\"model\") or \"Unknown\"\n"
#     #         "    info[\"model\"] = model\n"
#     #         "    if not info.get(\"device_name\"):\n"
#     #         "        if make and model and model != \"Unknown\": info[\"device_name\"] = f\"{make} {model}\"\n"
#     #         "        elif make and make != \"Unknown\": info[\"device_name\"] = f\"{make} Device\"\n"
#     #         "        else: info[\"device_name\"] = f\"Device {ip}\"\n"
#     #         "    if not info.get(\"serial_number\") and info.get(\"mac_address\"): info[\"serial_number\"] = info.get(\"mac_address\")\n"
#     #         "    if \"current_status\" not in info or not info.get(\"current_status\"):\n"
#     #         "        reachable = info.get(\"reachable\")\n"
#     #         "        if reachable is True: info[\"current_status\"] = \"Online\"\n"
#     #         "        elif reachable is False: info[\"current_status\"] = \"Offline\"\n"
#     #         "        else: info[\"current_status\"] = \"Unknown\"\n"
#     #         "    return info\n\n"
#     #         "def _wrap_plugin_device_info(plugin):\n"
#     #         "    if hasattr(plugin, \"_device_info_wrapped\") and plugin._device_info_wrapped: return\n"
#     #         "    original = getattr(plugin, \"get_device_info\", None)\n"
#     #         "    if not callable(original): return\n"
#     #         "    def _wrapped_get_device_info(ip, port=None, display_id=None):\n"
#     #         "        info = original(ip, port, display_id)\n"
#     #         "        return _normalize_device_info(info, ip, port, display_id, plugin)\n"
#     #         "    plugin.get_device_info = _wrapped_get_device_info\n"
#     #         "    plugin._device_info_wrapped = True\n\n"
#     #         "__all__ = [\"ManualPlatformPlugin\", \"PLUGIN_REGISTRY\", \"get_plugin\", \"get_available_plugins\", \"discover_plugins\"]\n"
#     #     )

#     #     init_path = os.path.join(plugin_dir, "__init__.py")
#     #     with open(init_path, "w", encoding="utf-8") as f:
#     #         f.write(content)


#     def _write_plugin_init(self, manifest):
#         """Write a dynamic __init__.py for the plugin package."""
#         plugin_dir = self._get_plugin_dir()

#         content = '''"""
#     Manual Platform Plugin SDK
#     ==========================
#     Package for manual platform plugins (Samsung MDC, Q-SYS, etc.)
#     """

#     import os
#     import pkgutil
#     import importlib
#     import inspect
#     import logging

#     from .base import ManualPlatformPlugin

#     logger = logging.getLogger(__name__)

#     # Plugin registry (populated dynamically)
#     PLUGIN_REGISTRY = {}

#     def discover_plugins():
#         """Dynamically discover and register all plugin classes in this package."""
#         global PLUGIN_REGISTRY
#         PLUGIN_REGISTRY = {}

#         plugin_dir = os.path.dirname(__file__)

#         for loader, module_name, is_pkg in pkgutil.walk_packages([plugin_dir]):
#             if module_name in ["base", "__init__"]:
#                 continue
#             try:
#                 module = importlib.import_module(f".{module_name}", package=__package__)
#                 for name, obj in inspect.getmembers(module):
#                     if (inspect.isclass(obj) and
#                         issubclass(obj, ManualPlatformPlugin) and
#                         obj is not ManualPlatformPlugin):
#                         plugin_key = getattr(obj, "name", module_name.replace("_plugin", ""))
#                         PLUGIN_REGISTRY[plugin_key] = obj
#                         logger.debug(f"Registered plugin: {plugin_key} -> {obj.__name__}")
#             except Exception as e:
#                 logger.error(f"Failed to load plugin module {module_name}: {e}")

#     discover_plugins()
#     logger.info(f"Loaded {len(PLUGIN_REGISTRY)} plugins: {', '.join(sorted(PLUGIN_REGISTRY.keys()))}")

#     def get_plugin(plugin_name, config=None):
#         plugin_class = PLUGIN_REGISTRY.get(plugin_name)
#         if plugin_class:
#             plugin = plugin_class(config)
#             _wrap_plugin_device_info(plugin)
#             return plugin
#         return None

#     def get_available_plugins():
#         plugins = []
#         for name, plugin_class in PLUGIN_REGISTRY.items():
#             try:
#                 instance = plugin_class()
#                 plugins.append({
#                     "name": getattr(instance, "name", name),
#                     "display_name": getattr(instance, "display_name", name),
#                     "description": getattr(instance, "description", ""),
#                     "supports_display_id": getattr(instance, "supports_display_id", True),
#                     "supports_port": getattr(instance, "supports_port", True),
#                     "default_port": getattr(instance, "default_port", 1515),
#                     "supported_models": getattr(instance, "SUPPORTED_MODELS", []),
#                 })
#             except Exception: pass
#         return plugins

#     def _normalize_device_info(info, ip, port, display_id, plugin):
#         if info is None: info = {}
#         info.setdefault("ip_address", ip)
#         info.setdefault("port", port)
#         info.setdefault("display_id", display_id)
#         make = info.get("make") or getattr(plugin, "display_name", None) or "Unknown"
#         info["make"] = make
#         model = info.get("model") or "Unknown"
#         info["model"] = model
#         if not info.get("device_name"):
#             if make and model and model != "Unknown": info["device_name"] = f"{make} {model}"   
#             elif make and make != "Unknown": info["device_name"] = f"{make} Device"
#             else: info["device_name"] = f"Device {ip}"
#         if not info.get("serial_number") and info.get("mac_address"):
#             info["serial_number"] = info.get("mac_address")
#         if "current_status" not in info or not info.get("current_status"):
#             reachable = info.get("reachable")
#             if reachable is True: info["current_status"] = "Online"
#             elif reachable is False: info["current_status"] = "Offline"
#             else: info["current_status"] = "Unknown"
#         return info

#     def _wrap_plugin_device_info(plugin):
#         if hasattr(plugin, "_device_info_wrapped") and plugin._device_info_wrapped: return
#         original = getattr(plugin, "get_device_info", None)
#         if not callable(original): return
#         def _wrapped_get_device_info(ip, port=None, display_id=None):
#             info = original(ip, port, display_id)
#             return _normalize_device_info(info, ip, port, display_id, plugin)
#         plugin.get_device_info = _wrapped_get_device_info
#         plugin._device_info_wrapped = True

#     __all__ = ["ManualPlatformPlugin", "PLUGIN_REGISTRY", "get_plugin", "get_available_plugins", "discover_plugins"]
#     '''

#         init_path = os.path.join(plugin_dir, "__init__.py")
#         with open(init_path, "w", encoding="utf-8") as f:
#             f.write(content)
        
#         logger.info(f"[EDGE] Rewrote plugin __init__.py with dynamic discovery")



#     # ══════════════════════════════════════════════════════════════
#     # SEND HELPERS
#     # ══════════════════════════════════════════════════════════════

#     def register_command_handler(self, command_type: str, handler):
#         """Register a handler for a custom command type."""
#         self.command_handlers[command_type] = handler

#     def send_command_result(self, command_id: str, status: str, result):
#         """Send command execution result back to cloud."""
#         if self.connected:
#             self._emit_safe('command_result', {
#                 'command_id': command_id,
#                 'status':     status,
#                 'result':     result,
#                 'timestamp':  time.time(),
#             })

#     def send_heartbeat(self):
#         """Send heartbeat to cloud every 30s."""
#         if self.connected and self.edge_id:
#             self._emit_safe('heartbeat', {
#                 'edge_id':        self.edge_id,
#                 'cpu_percent':    psutil.cpu_percent(interval=1),
#                 'memory_percent': psutil.virtual_memory().percent,
#                 'timestamp':      time.time(),
#             })

#     def _get_connected_namespace(self) -> str:
#         """Return a namespace that is actually connected."""
#         try:
#             namespaces = getattr(self.sio, 'namespaces', {}) or {}
#             if self.namespace in namespaces:
#                 return self.namespace
#             if namespaces:
#                 return next(iter(namespaces.keys()))
#         except Exception:
#             pass
#         return self.namespace

#     def _emit_safe(self, event: str, payload: dict):
#         """Emit using a connected namespace to avoid BadNamespaceError."""
#         ns = self._get_connected_namespace()
#         try:
#             self.sio.emit(event, payload, namespace=ns)
#         except sio_exceptions.BadNamespaceError:
#             logger.warning(
#                 f"[EDGE] Emit failed: namespace '{ns}' not connected. "
#                 f"Configured namespace='{self.namespace}'."
#             )

#     def start(self):
#         """Connect to cloud and maintain connection forever with auto-reconnect."""
#         while True:
#             self.config        = Config.load()
#             self.cloud_url     = self.config.get('CLOUD_URL', '')
#             self.api_key       = self.config.get('API_KEY', '')
#             self.socketio_path = self.config.get('SOCKETIO_PATH', 'socket.io') or 'socket.io'
#             self.namespace     = self.config.get('SOCKETIO_NAMESPACE') or '/'

#             if not self.cloud_url or not self.api_key:
#                 logger.warning("Cloud URL or API Key not configured. Retrying in 30s...")
#                 time.sleep(30)
#                 continue

#             try:
#                 if self.connected or getattr(self.sio, "connected", False):
#                     time.sleep(5)
#                     continue

#                 logger.info(f"Connecting to cloud: {self.cloud_url}")

#                 connect_kwargs = {
#                     'headers':       {'X-API-Key': self.api_key},
#                     'transports':    ['websocket', 'polling'],
#                     'socketio_path': self.socketio_path,
#                 }

#                 if self.namespace != '/':
#                     connect_kwargs['namespaces'] = [self.namespace]

#                 self.sio.connect(self.cloud_url, **connect_kwargs)

#                 while self.connected:
#                     self.send_heartbeat()
#                     time.sleep(30)

#             except Exception as e:
#                 logger.error(f"Cloud connection error: {e}")
#                 self.connected       = False
#                 self._polling_active = False
#                 EdgeState.set('cloud_connected', False)
#                 time.sleep(10)





"""
Manual Platform Plugin: CloudConnector
"""

import socketio
import logging
import time
import threading
import platform
import psutil
import socket
import json
import requests
import base64
import io
import os
import shutil
import tempfile
import zipfile
import hashlib
import subprocess
import sys

from socketio import exceptions as sio_exceptions

from utils.config import Config

from utils.state import EdgeState

logger = logging.getLogger(__name__)


class CloudConnector:

    def __init__(self, config: dict):

        self.config        = config

        self.cloud_url     = config.get('CLOUD_URL', '')

        self.api_key       = config.get('API_KEY', '')

        self.edge_name     = config.get('EDGE_NAME', 'Edge-Collector')

        self.location      = config.get('LOCATION', 'Unknown')

        self.socketio_path = config.get('SOCKETIO_PATH', 'socket.io') or 'socket.io'

        self.namespace     = config.get('SOCKETIO_NAMESPACE') or '/'

        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,
            reconnection_delay=5,
            reconnection_delay_max=60
        )

        self.connected        = False

        self.edge_id          = None

        self.command_handlers = {}

        self._watchlist      = []

        self._watchlist_lock = threading.Lock()

        self._polling_thread = None

        self._polling_active = False

        _current_file = os.path.abspath(__file__)
        _services_dir = os.path.dirname(_current_file)
        _backend_dir  = os.path.dirname(_services_dir)
        _root_dir     = os.path.dirname(_backend_dir)

        self.backend_dir   = _backend_dir
        self.edge_root_dir = _root_dir

        if _root_dir not in sys.path:
            sys.path.insert(0, _root_dir)
        if _backend_dir not in sys.path:
            sys.path.insert(0, _backend_dir)

        self._setup_socket_events()


    # ══════════════════════════════════════════════════════════════
    # SOCKET.IO EVENT SETUP
    # ══════════════════════════════════════════════════════════════

    def _setup_socket_events(self):

        @self.sio.event(namespace=self.namespace)
        def connect():
            self.connected = True
            EdgeState.set('cloud_connected', True)
            logger.info(f"Connected to cloud: {self.cloud_url}")
            self._register_edge()

        @self.sio.event(namespace=self.namespace)
        def disconnect():
            self.connected       = False
            self._polling_active = False
            EdgeState.set('cloud_connected', False)
            logger.warning("Disconnected from cloud. Will reconnect...")

        @self.sio.on('registered', namespace=self.namespace)
        def on_registered(data):
            edge_id = (data or {}).get('edge_id')
            if not edge_id:
                logger.warning("Registered event received without edge_id; keeping existing edge_id")
                return
            self.edge_id = edge_id
            EdgeState.set('edge_id', self.edge_id)
            logger.info(f"Registered with cloud. edge_id={self.edge_id}")
            self._start_polling()
            threading.Thread(
                target=self._check_plugin_version,
                daemon=True
            ).start()

        @self.sio.on('registration_failed', namespace=self.namespace)
        def on_registration_failed(data):
            logger.error(f"Registration failed: {data.get('error')}. Check your API key.")
            self.sio.disconnect()

        @self.sio.on('sync_devices', namespace=self.namespace)
        def on_sync_devices(data):
            devices = data.get('devices', [])
            with self._watchlist_lock:
                self._watchlist = devices
            EdgeState.set('watchlist', devices)
            try:
                summary = []
                for d in devices:
                    summary.append({
                        "ip": d.get("ip_address"),
                        "port": d.get("port"),
                        "plugin": d.get("plugin_name"),
                        "protocol": d.get("protocol"),
                    })
                logger.info(
                    f"Watchlist synced: {len(devices)} devices to monitor | "
                    f"devices={summary}"
                )
            except Exception:
                logger.info(f"Watchlist synced: {len(devices)} devices to monitor")

        @self.sio.on('plugin_update_bundle', namespace=self.namespace)
        def on_plugin_update_bundle(data):
            threading.Thread(
                target=self._apply_plugin_update,
                args=(data,),
                daemon=True
            ).start()

        @self.sio.on('command', namespace=self.namespace)
        def on_command(data):
            logger.info(f"Received command: {data.get('command_type')}")
            threading.Thread(
                target=self._handle_command,
                args=(data,),
                daemon=True
            ).start()

        @self.sio.on('ping_edge', namespace=self.namespace)
        def on_ping(data):
            self._emit_safe('pong_edge', {
                'edge_id':   self.edge_id,
                'timestamp': time.time()
            })


    # ══════════════════════════════════════════════════════════════
    # REGISTRATION
    # ══════════════════════════════════════════════════════════════

    def _register_edge(self):
        """Send registration payload to cloud right after connecting."""
        payload = {
            'api_key':         self.api_key,
            'edge_name':       self.edge_name,
            'location':        self.location,
            'os':              platform.system(),
            'os_version':      platform.version(),
            'hostname':        platform.node(),
            'cpu_count':       psutil.cpu_count(),
            'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'agent_version':   '1.0.0',
        }
        self._emit_safe('register_edge', payload)
        logger.info("Registration payload sent")


    # ══════════════════════════════════════════════════════════════
    # PLUGIN NAME RESOLUTION
    # ══════════════════════════════════════════════════════════════

    _MODEL_PLUGIN_MAP = {
        # Occupancy Sensors
        "CEN-ODT-C-POE":   "crestron_occupancy_sensor",
        "CEN-ODT-C-POE-W": "crestron_occupancy_sensor",
        "GLS-ODT-C-CN":    "crestron_occupancy_sensor",
        # CP4N / 4-Series Control Systems
        "CP4N":     "crestron_ssh",
        "CP4":      "crestron_ssh",
        "CP3":      "crestron_ssh",
        "MC4":      "crestron_ssh",
        "AV4":      "crestron_ssh",
        "AM-3200":  "crestron_airmedia",
        "RMC4":     "crestron_ssh",
        "RMC3":     "crestron_ssh",
        "4-SERIES": "crestron_ssh",
        "AM-3000-WF-I":   "crestron_airmedia",
        "AM-3200-WF":     "crestron_airmedia",
        "AM-3200-WF-I":   "crestron_airmedia",
        "AM-TX3-100-I":   "crestron_airmedia",
        "AIRMEDIA":       "crestron_airmedia",
        "TS-1070":     "crestron_ts1070",
        "TST-1080":    "crestron_ts1070",
        "TSW-1070":    "crestron_ts1070",
        "TS-1542":     "crestron_ts1070",
        "TS-770":      "crestron_ts1070",
        "TSS-1070":    "crestron_ts1070",
        "TSS-770":     "crestron_ts1070",
        "TSS-752":     "crestron_ts1070",
        "TSS-1060":    "crestron_ts1070",
        "MMX4X2-HDMI":         "lightware_mmx",
        "MMX4X2-HT200":        "lightware_mmx",
        "MMX4X2-HDMI-USB20-L": "lightware_mmx",
        "TesiraFORTE":     "tesira",
        "TesiraFORTE X":   "tesira",
        "Tesira SERVER":   "tesira",
        "Tesira SERVER-IO":"tesira",
        "TesiraLUX":       "tesira",
        "TesiraAMP":       "tesira",
        "Voltera":         "tesira",
        "Room Bar Pro":    "cisco_roomos",
        "Room Bar":        "cisco_roomos",
        "Webex Room Kit":  "cisco_roomos",
        "Room Kit":        "cisco_roomos",
        "TCBarM":          "sennheiser_tcbarm",
        "TC Bar M":        "sennheiser_tcbarm",
        "VIA":             "kramer_via",
        "Connect 2":       "kramer_via",
        "Connect 2 (VIA)": "kramer_via",
        "VIA Connect 2":   "kramer_via",
        # ── Shure P300 / ANIUSB-MATRIX ─────────────────────────────────────
        "P300":          "shure_p300",
        "ANIUSB-MATRIX": "shure_p300",
        "ANIUSB":        "shure_p300",

         "DM-NVX-350":   "crestron_nvx",
        "DM-NVX-351":   "crestron_nvx",
        "DM-NVX-352":   "crestron_nvx",
        "DM-NVX-360":   "crestron_nvx",
        "DM-NVX-361":   "crestron_nvx",
        "DM-NVX-362":   "crestron_nvx",
        "DM-NVX-363":   "crestron_nvx",
        "DM-NVX-364":   "crestron_nvx",
        "DM-NVX-365":   "crestron_nvx",
        "DM-NVX-366":   "crestron_nvx",
        "DM-NVX-370":   "crestron_nvx",
        "DM-NVX-371":   "crestron_nvx",
        "DM-NVX-372":   "crestron_nvx",
        "DM-NVX-373":   "crestron_nvx",
        "DM-NVX-374":   "crestron_nvx",
        "DM-NVX-375":   "crestron_nvx",
        "DM-NVX-376":   "crestron_nvx",
        "DM-NVX-380":   "crestron_nvx",
        "DM-NVX-381":   "crestron_nvx",
        "DM-NVX-382":   "crestron_nvx",
        "DM-NVX-383":   "crestron_nvx",
        "DM-NVX-384":   "crestron_nvx",
        "DM-NVX-385":   "crestron_nvx",
        "DM-NVX-386":   "crestron_nvx",
        "DM-NVX-D30":   "crestron_nvx",
        "DM-NVX-D30C":  "crestron_nvx",
        "DM-NVX-E30":   "crestron_nvx",
        "DM-NVX-E30C":  "crestron_nvx",
 


    }

    # ── Make / plugin-name aliases ──────────────────────────────────────────
    _PLUGIN_ALIASES = {
        # Samsung
        "samsung":     "samsung_mdc",
        "samsung_mdc": "samsung_mdc",

        # LG
        "lg":         "lg_55ef5gl",
        "lg_55ef5gl": "lg_55ef5gl",

        # Sennheiser
        "sennheiser":          "sennheiser_tccm",
        "sennheiser_tccm":     "sennheiser_tccm",
        "sennheiser_tcbar_m":  "sennheiser_tcbarm",
        "sennheiser_tcbarm":   "sennheiser_tcbarm",
        "sennheiser tcbar m":  "sennheiser_tcbarm",
        "sennheiser tc bar m": "sennheiser_tcbarm",
        "sennheiser tcbarm":   "sennheiser_tcbarm",
        "tcbar m":             "sennheiser_tcbarm",
        "tc bar m":            "sennheiser_tcbarm",
        "tcc m":               "sennheiser_tccm",
        "tccm":                "sennheiser_tccm",

        # Shure MXA family
        "shure":        "shure_mxa920",
        "shure_mxa920": "shure_mxa920",
        "mxa920":       "shure_mxa920",

        # ── Shure P300 / ANIUSB-MATRIX ─────────────────────────────────────
        # FIX: these were missing → _normalize_plugin_name("shure_p300") was
        # falling through to the generic "shure" → "shure_mxa920" alias,
        # loading the wrong plugin class and causing "Unknown command" for
        # every P300-specific command (inc_channel_gain, set_channel_mute …)
        "shure_p300":    "shure_p300",
        "p300":          "shure_p300",
        "aniusb":        "shure_p300",
        "aniusb-matrix": "shure_p300",
        "aniusb_matrix": "shure_p300",
        # ───────────────────────────────────────────────────────────────────

        # BrightSign
        "brightsign": "brightsign",

        # Crestron
        "crestron_occupancy_sensor": "crestron_occupancy_sensor",
        "crestron_cp4n":             "crestron_ssh",
        "crestron_ssh":              "crestron_ssh",
        "cp4n":                      "crestron_ssh",
        "crestron":                  "crestron_ssh",
        "crestron_ts1070":           "crestron_ts1070",
        "ts1070":                    "crestron_ts1070",
        "ts-1070":                   "crestron_ts1070",
        "crestron_ts-1070":          "crestron_ts1070",
        "touchpanel":                "crestron_ts1070",
        "touch panel":               "crestron_ts1070",
        "crestron_airmedia":         "crestron_airmedia",
        "airmedia":                  "crestron_airmedia",
        "am-3200":                   "crestron_airmedia",
        "am3200":                    "crestron_airmedia",
        "am-3000":                   "crestron_airmedia",
        "am3000":                    "crestron_airmedia",
        "am-tx3":                    "crestron_airmedia",
        "tx3":                       "crestron_airmedia",

        "barco":                      "barco_clickshare",
        "barco_clickshare":           "barco_clickshare",
        "barco_clickshare_c_series":  "barco_clickshare",
        "barco_clickshare_cx_series": "barco_clickshare",

        "lightware_ucx": "lightware",
        "lightware_mmx": "lightware_mmx",

        "poly_videoos": "poly_videoos",
        "poly":         "poly_videoos",

        "tesira":       "tesira",
        "biamp":        "tesira",

        "power_conditioner": "power_conditioner",
        "vector":            "power_conditioner",
        "powerconditioner":  "power_conditioner",

        "cisco_roomos": "cisco_roomos",
        "cisco":        "cisco_roomos",

        "kramer":     "kramer_via",
        "kramer_via": "kramer_via",
        "via":        "kramer_via",
        "connect 2":  "kramer_via",
        
        "crestron_nvx":          "crestron_nvx",
        "nvx":                   "crestron_nvx",
        "dm-nvx":                "crestron_nvx",
        "dm_nvx":                "crestron_nvx",
        "crestron_nvx_360":      "crestron_nvx",
        "crestron_nvx_350":      "crestron_nvx",
        "nvx_360":               "crestron_nvx",
        "nvx_350":               "crestron_nvx",
 
 
    }

    def _model_plugin_match(self, params: dict = None) -> str:
        if not params:
            return ""

        config = params.get("plugin_config") if isinstance(params.get("plugin_config"), dict) else {}
        values = [
            params.get("model"),
            params.get("device_type"),
            params.get("device_name"),
            config.get("model"),
            config.get("device_type"),
            config.get("device_name"),
        ]
        haystack = " ".join(
            str(v or "").upper().replace("-", "").replace(" ", "") for v in values
        )

        for model, plugin_key in self._MODEL_PLUGIN_MAP.items():
            normalised_model = model.upper().replace("-", "").replace(" ", "")
            if normalised_model in haystack:
                logger.debug(f"[PLUGIN] Model-based resolution: '{model}' -> '{plugin_key}'")
                return plugin_key

        oem_name = str(params.get("oem_name") or config.get("oem_name") or "").lower()

        if "airmedia" in oem_name or "am-" in oem_name:
            logger.info(f"[PLUGIN] AirMedia detected via oem_name: '{oem_name}' -> crestron_airmedia")
            return "crestron_airmedia"
        if "occupancy" in oem_name:
            return "crestron_occupancy_sensor"
        if "cp4n" in oem_name or "crestron_ssh" in oem_name:
            return "crestron_ssh"
        if any(x in oem_name for x in ("ts1070", "tss", "tst", "tsw", "touchpanel", "touch")):
            logger.info(f"[PLUGIN] TS-1070 detected via oem_name: '{oem_name}' -> crestron_ts1070")
            return "crestron_ts1070"
        if "mmx" in oem_name:
            return "lightware_mmx"
        # ── FIX: P300/ANIUSB must be checked BEFORE the generic "shure" guard ──
        if any(x in oem_name for x in ("p300", "aniusb")):
            return "shure_p300"
        if "shure" in oem_name:
            return "shure_mxa920"
        if any(x in oem_name for x in ("mxa920", "mxa910", "mxa902", "mxa710")):
            return "shure_mxa920"
        if "samsung" in oem_name and "mdc" in oem_name:
            return "samsung_mdc"
        if "cisco" in oem_name and "room" in oem_name:
            return "cisco_roomos"
        if any(x in oem_name for x in ("Room Bar Pro", "Room Bar", "Webex Room Kit", "Room Kit")):
            return "cisco_roomos"
        if "sennheiser" in oem_name and ("tcbarm" in oem_name or "tcbar" in oem_name or "tc bar" in oem_name):
            return "sennheiser_tcbarm"
        if any(x in oem_name for x in ("tcbarm", "tcbar", "tc bar m", "sennheiser_tcbar_m")):
            return "sennheiser_tcbarm"
        if "kramer" in oem_name and "via" in oem_name:
            return "kramer_via"
        if any(x in oem_name for x in ("via", "connect 2", "kramer")) and "kramer" in oem_name:
            return "kramer_via"

        return ""

    def _normalize_plugin_name(self, raw_name: str, params: dict = None) -> str:
        """
        Resolve a raw plugin name / make string to the exact plugin registry key.

        Resolution order:
          1. If raw_name is already a known specific key → return it directly.
          2. If raw_name is a generic make (e.g. 'crestron') AND a model is present
             in params → look up model in _MODEL_PLUGIN_MAP for precision.
          3. Fall back to _PLUGIN_ALIASES generic make entry.
          4. Return the cleaned name as-is.
        """
        name = (raw_name or "").strip().lower().replace("manual_", "")
        model_plugin = self._model_plugin_match(params)

        # Step 1: direct alias lookup
        if name in self._PLUGIN_ALIASES:
            resolved = self._PLUGIN_ALIASES[name]
            # Model-based resolution takes priority for ambiguous generic names
            if name in ["crestron_ssh", "crestron_occupancy_sensor",
                        "crestron_cp4n", "crestron_ts1070"]:
                return name
            if params and resolved == self._PLUGIN_ALIASES.get("crestron"):
                model = (params.get("model") or "").strip()
                if model and model in self._MODEL_PLUGIN_MAP:
                    logger.debug(
                        f"[PLUGIN] Model-based resolution: '{model}' → "
                        f"'{self._MODEL_PLUGIN_MAP[model]}'"
                    )
                    return self._MODEL_PLUGIN_MAP[model]
            return resolved

        if model_plugin:
            return model_plugin

        # Step 2: try model-based resolution directly
        if params:
            model = (params.get("model") or "").strip()
            if model and model in self._MODEL_PLUGIN_MAP:
                logger.debug(
                    f"[PLUGIN] Model-based resolution (no alias): '{model}' → "
                    f"'{self._MODEL_PLUGIN_MAP[model]}'"
                )
                return self._MODEL_PLUGIN_MAP[model]

        # Step 3: return cleaned name as-is
        logger.debug(f"[PLUGIN] No alias found for '{name}', using as-is")
        return name


    # ══════════════════════════════════════════════════════════════
    # COMMAND HANDLING
    # ══════════════════════════════════════════════════════════════

    # def _handle_command(self, data: dict):
    #     """Route incoming command to the correct handler."""
    #     command_type = data.get('command_type', '')
    #     command_id   = data.get('command_id')
    #     params       = data.get('params', {})

    #     try:
    #         if command_type == 'probe_device':
    #             self._handle_probe_device(command_id, params)
    #             return

    #         if command_type in ('query_device_status', 'device_status', 'query_status',
    #                            'get_status', 'device_query', 'query_device', 'status'):
    #             self._handle_device_status(command_id, params)
    #             return

    #         if command_type in ('device_command', 'device_control', 'send_command',
    #                            'control_device', 'execute_command', 'run_command', 'command'):
    #             self._handle_device_control(command_id, params)
    #             return

    #         handler = self.command_handlers.get(command_type)

    #         if handler:
    #             try:
    #                 result = handler(data.get('device_id'), params)
    #                 self.send_command_result(command_id, 'success', result)
    #             except Exception as e:
    #                 logger.error(f"Command '{command_type}' failed: {e}")
    #                 self.send_command_result(command_id, 'failed', str(e))
    #         else:
    #             logger.warning(f"No handler registered for command: {command_type}")
    #             self.send_command_result(command_id, 'failed', f'Unknown command: {command_type}')

    #     except Exception as e:
    #         logger.exception(f"Command '{command_type}' failed")
    #         self.send_command_result(command_id, 'failed', {'error': str(e)})


    def _handle_command(self, data: dict):
        command_type = data.get('command_type', '')
        command_id = data.get('command_id')
        params = data.get('params', {})

        try:
            # Device probe
            if command_type == 'probe_device':
                self._handle_probe_device(command_id, params)
                return

            # Firmware upgrade (runs in background thread, reports via custom events)
            if command_type == 'firmware_upgrade':
                threading.Thread(
                    target=self._handle_firmware_upgrade,
                    args=(command_id, params),
                    daemon=True
                ).start()
                return

            # Firmware status check (synchronous)
            if command_type == 'firmware_status_check':
                self._handle_firmware_status_check(command_id, params)
                return

            # Device status commands
            if command_type in (
                'query_device_status',
                'device_status',
                'query_status',
                'get_status',
                'device_query',
                'query_device',
                'status'
            ):
                self._handle_device_status(command_id, params)
                return

            # Device control commands
            if command_type in (
                'device_command',
                'device_control',
                'send_command',
                'control_device',
                'execute_command',
                'run_command',
                'command'
            ):
                self._handle_device_control(command_id, params)
                return

            # Registered custom handlers
            handler = self.command_handlers.get(command_type)

            if handler:
                try:
                    result = handler(data.get('device_id'), params)
                    self.send_command_result(command_id, 'success', result)
                except Exception as e:
                    logger.error(f"Command '{command_type}' failed: {e}")
                    self.send_command_result(command_id, 'failed', str(e))

            else:
                logger.warning(
                    f"No handler registered for command: {command_type}"
                )

                # Safety net: route unknown commands that look like device commands
                if params.get('ip') and (
                    params.get('plugin_name') or params.get('make')
                ):
                    logger.warning(
                        f"[EDGE] Routing unrecognized "
                        f"command_type='{command_type}' "
                        f"to device_control handler as fallback"
                    )

                    if not params.get('command_key') and not params.get('command'):
                        params['command_key'] = command_type
                        params['command'] = command_type

                    self._handle_device_control(command_id, params)

                else:
                    self.send_command_result(
                        command_id,
                        'failed',
                        f'Unknown command: {command_type}'
                    )

        except Exception as e:
            logger.exception(f"Command '{command_type}' failed")
            self.send_command_result(
                command_id,
                'failed',
                {'error': str(e)}
        )
   
   
    def _load_plugin_for_command(self, params: dict):
        """Load the appropriate plugin based on command parameters."""
        plugin_name   = params.get('plugin_name') or params.get('make') or ''
        clean_name    = self._normalize_plugin_name(plugin_name, params)
        plugin_config = params.get('plugin_config') or {}

        local_plugin_configs = self.config.get('PLUGIN_CONFIGS', {})
        merged_config = {**local_plugin_configs.get(clean_name, {}), **plugin_config}

        logger.debug(f"[PLUGIN] Loading plugin: raw='{plugin_name}' → resolved='{clean_name}'")

        try:
            if self.backend_dir not in sys.path:
                sys.path.insert(0, self.backend_dir)
            from plugin import get_plugin
            logger.info(f"[PLUGIN] Successfully imported get_plugin from backend/plugin")
        except ImportError as e:
            logger.error(f"Failed to import from backend.plugin: {e}")
            try:
                import importlib.util
                plugin_init_path = os.path.join(self.backend_dir, 'plugin', '__init__.py')
                logger.info(f"[PLUGIN] Trying to load from: {plugin_init_path}")
                if os.path.exists(plugin_init_path):
                    spec = importlib.util.spec_from_file_location("plugin_module", plugin_init_path)
                    plugin_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(plugin_module)
                    get_plugin = plugin_module.get_plugin
                    logger.info(f"[PLUGIN] Loaded from file: {plugin_init_path}")
                else:
                    raise ImportError(f"plugin __init__.py not found at {plugin_init_path}")
            except Exception as e2:
                logger.error(f"All import attempts failed: {e2}")
                raise RuntimeError(f"Plugin system not available: {e2}")

        plugin = get_plugin(clean_name, config=merged_config)
        if not plugin:
            raise RuntimeError(f"Plugin not found for '{plugin_name}' (normalized='{clean_name}')")

        return plugin, clean_name

    def _handle_device_status(self, command_id: str, params: dict):
        """Handle device status query command."""
        try:
            plugin, clean_name = self._load_plugin_for_command(params)

            ip = params.get('ip')
            if not ip:
                self.send_command_result(command_id, 'failed', {'error': 'ip is required'})
                return

            port       = int(params.get('port') or getattr(plugin, 'default_port', None))
            display_id = str(params.get('display_id') or "00")

            logger.info(f"Querying status for {ip}:{port} using plugin '{clean_name}'")

            status = plugin.query_status(ip=ip, port=port, display_id=display_id)

            if not status:
                status = {}

            if 'reachable' not in status:
                status['reachable'] = status.get('current_status') in ('Normal', 'Online', 'Ready')

            self.send_command_result(command_id, 'success', status)
            logger.info(f"Status query success for {ip}: reachable={status.get('reachable')}")

        except Exception as e:
            logger.error(f"Device status query failed: {e}")
            self.send_command_result(command_id, 'failed', {'error': str(e)})

    def _handle_device_control(self, command_id: str, params: dict):
        """Handle device control command."""
        try:
            plugin, clean_name = self._load_plugin_for_command(params)

            ip      = params.get('ip')
            command = params.get('command_key') or params.get('command')
             # ADD THIS:
            logger.info(f"[DEBUG _handle_device_control] clean_name={clean_name!r} ip={ip!r} command={command!r} params_keys={list(params.keys())}")

            if not ip or not command:
                self.send_command_result(
                    command_id, 'failed',
                    {'error': 'ip and command are required'}
                )
                return

            port       = int(params.get('port') or getattr(plugin, 'default_port', 443))
            display_id = str(params.get('display_id') or "00")
            cmd_params = params.get('params') or {}

            logger.info(
                f"Executing command '{command}' on {ip}:{port} "
                f"using plugin '{clean_name}' with params={cmd_params}"
            )

            # ── helper: unwrap ManualPlatformPlugin dict response ──────────
            def _unpack_manual(raw):
                """
                ManualPlatformPlugin.send_command returns
                  {"success": bool, "result": ..., "error": ...}
                Convert to (ok, msg) tuple.
                """
                if isinstance(raw, dict):
                    ok  = bool(raw.get("success", False))
                    _r  = raw.get("result")
                    if isinstance(_r, str) and _r:
                        msg = _r
                    elif isinstance(_r, dict):
                        msg = _r.get("message") or str(_r)
                    else:
                        msg = raw.get("error") or ("ok" if ok else "Command failed")
                    return ok, msg
                # legacy tuple fallback
                return raw

            # ── Route to correct send_command signature per plugin ─────────
            if "samsung" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command_key=command
                )
            elif "brightsign" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command={"action": command, "params": cmd_params}
                )
            elif "lg" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command
                )
            elif "crestron" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command, params=cmd_params
                )
            elif "barco" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command
                )
            elif "lightware" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command, params=cmd_params
                )
            elif "poly" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command, params=cmd_params
                )
            elif "tesira" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command, params=cmd_params
                )
            elif "power_conditioner" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command, params=cmd_params
                )
            elif "shure" in clean_name:
                # ── FIX: ManualPlatformPlugin returns {"success":..., "result":...}
                # NOT a tuple. Also pass command as a dict so ShureP300Plugin's
                # isinstance(command, dict) branch fires correctly, which then
                # dispatches to the right action handler (inc_channel_gain etc.)
                _raw = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command={"action": command, "params": cmd_params}
                )
                ok, msg = _unpack_manual(_raw)
            elif "cisco_roomos" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command, params=cmd_params
                )
            elif "sennheiser_tcbarm" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command, params=cmd_params
                )
            elif "kramer_via" in clean_name:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command, params=cmd_params
                )
            else:
                ok, msg = plugin.send_command(
                    ip=ip, port=port, display_id=display_id,
                    command=command, params=cmd_params
                )

            if ok:
                if isinstance(msg, (dict, list)):
                    self.send_command_result(command_id, 'success', msg)
                else:
                    self.send_command_result(command_id, 'success', {'message': str(msg)})
                logger.info(f"Command '{command}' succeeded on {ip}")
            else:
                self.send_command_result(command_id, 'failed', {'error': str(msg)})
                logger.warning(f"Command '{command}' failed on {ip}: {msg}")

        except Exception as e:
            logger.error(f"Device control command failed: {e}")
            self.send_command_result(command_id, 'failed', {'error': str(e)})


    def _handle_probe_device(self, command_id: str, params: dict):
        """
        Cloud asks edge to probe a local device and return its full info.
        """
        ip            = params.get('ip')
        port          = params.get('port')
        display_id    = str(params.get('display_id') or "00")
        plugin_name   = params.get('plugin_name', '')
        plugin_config = params.get('plugin_config') or {}

        logger.info(f"=== PROBE REQUEST === IP: {ip}, Port: {port}, Plugin: {plugin_name}")
        logger.info(f"Probing device: {ip}:{port} plugin={plugin_name}")

        try:
            device_info = self._probe_device(ip, port, plugin_name, display_id, plugin_config)
            logger.info(f"=== PROBE RESULT === Model: {device_info.get('model')}, Status: {device_info.get('current_status')}")
            self.send_command_result(command_id, 'success', device_info)
            logger.info(
                f"Probe success: {ip} -> "
                f"model={device_info.get('model', '?')} "
                f"serial={device_info.get('serial_number', '?')} "
                f"status={device_info.get('current_status', '?')}"
            )
            logger.info(f"Probe device_info: {device_info}")
        except Exception as e:
            logger.error(f"Probe failed for {ip}:{port} – {e}")
            self.send_command_result(command_id, 'failed', {
                'error':          str(e),
                'ip_address':     ip,
                'current_status': 'Offline'
            })


    # def _handle_firmware_upgrade(self, command_id: str, params: dict):
    #     """
    #     Handle firmware upgrade command from cloud.
    #     Downloads firmware file from cloud, uploads to Crestron device,
    #     triggers upgrade, polls for completion, reports progress/result.
    #     """
    #     job_id = params.get('job_id')
    #     ip = params.get('ip')
    #     plugin_name = params.get('plugin_name')
    #     username = params.get('username')
    #     password = params.get('password')
    #     firmware_download_url = params.get('firmware_download_url')
    #     firmware_filename = params.get('firmware_filename')

    #     if not all([job_id, ip, plugin_name, firmware_download_url, firmware_filename]):
    #         logger.error(f"[EDGE] Firmware upgrade missing required params: {params}")
    #         self._emit_safe('firmware_upgrade_complete', {
    #             'job_id': job_id,
    #             'success': False,
    #             'error': 'Missing required params',
    #         })
    #         return

    #     self._emit_safe('firmware_upgrade_progress', {
    #         'job_id': job_id,
    #         'progress': 0,
    #         'status': 'Starting',
    #         'label': 'Starting firmware upgrade...',
    #     })

    #     temp_dir = None
    #     try:
    #         if not username or not password:
    #             raise Exception("Device credentials not provided")

    #         cloud_url = self.config.get('CLOUD_URL', '').rstrip('/')
    #         api_key = self.config.get('API_KEY', '')
    #         download_url = firmware_download_url if firmware_download_url.startswith('http') else f"{cloud_url}{firmware_download_url}"

    #         self._emit_safe('firmware_upgrade_progress', {
    #             'job_id': job_id,
    #             'progress': 3,
    #             'status': 'Downloading',
    #             'label': 'Downloading firmware file from cloud...',
    #         })

    #         temp_dir = tempfile.mkdtemp(prefix='fw_upgrade_')
    #         local_path = os.path.join(temp_dir, firmware_filename)

    #         dl_headers = {}
    #         if api_key:
    #             dl_headers['X-API-Key'] = api_key
    #         resp = requests.get(download_url, headers=dl_headers, timeout=300, verify=False)
    #         resp.raise_for_status()
    #         with open(local_path, 'wb') as f:
    #             f.write(resp.content)

    #         from plugin.crestron_firmware_mixin import CrestronFirmwareMixin

    #         self._emit_safe('firmware_upgrade_progress', {
    #             'job_id': job_id,
    #             'progress': 5,
    #             'status': 'LoggingIn',
    #             'label': 'Authenticating with device...',
    #         })

    #         session, xsrf_token = CrestronFirmwareMixin.login_device(ip, username, password)

    #         try:
    #             self._emit_safe('firmware_upgrade_progress', {
    #                 'job_id': job_id,
    #                 'progress': 15,
    #                 'status': 'Uploading',
    #                 'label': 'Uploading firmware to device...',
    #             })

    #             upload_ok, upload_result = CrestronFirmwareMixin.upload_firmware(
    #                 session, xsrf_token, ip, local_path, firmware_filename
    #             )
    #             if not upload_ok:
    #                 raise Exception(f"Upload failed: {upload_result.get('error', 'Unknown error')}")

    #             device_path = upload_result.get('device_path', '')

    #             self._emit_safe('firmware_upgrade_progress', {
    #                 'job_id': job_id,
    #                 'progress': 25,
    #                 'status': 'Triggering',
    #                 'label': 'Triggering firmware upgrade...',
    #             })

    #             trigger_ok, trigger_result = CrestronFirmwareMixin.trigger_upgrade(
    #                 session, xsrf_token, ip, device_path
    #             )
    #             if not trigger_ok:
    #                 raise Exception(f"Trigger failed: {trigger_result.get('error', 'Unknown error')}")

    #             poll_start = time.time()
    #             poll_timeout = 2700

    #             while True:
    #                 elapsed = time.time() - poll_start
    #                 if elapsed > poll_timeout:
    #                     raise Exception("Firmware upgrade timed out")

    #                 status = CrestronFirmwareMixin.get_upgrade_status(session, xsrf_token, ip)

    #                 if status.get('_needs_login'):
    #                     session.close()
    #                     session, xsrf_token = CrestronFirmwareMixin.login_device(ip, username, password)
    #                     continue

    #                 progress = status.get('progress', 0)
    #                 status_text = status.get('status', 'Unknown')
    #                 label = status.get('label', '')
    #                 completed = status.get('completed', False)
    #                 success = status.get('success', False)
    #                 error_text = status.get('error')

    #                 scaled_progress = 25 + int(progress * 0.75)

    #                 self._emit_safe('firmware_upgrade_progress', {
    #                     'job_id': job_id,
    #                     'progress': scaled_progress,
    #                     'status': status_text,
    #                     'label': label or status_text,
    #                     'raw_status': status.get('raw_status', ''),
    #                 })

    #                 if completed:
    #                     if success:
    #                         new_version = CrestronFirmwareMixin.fetch_firmware_version(session, xsrf_token, ip)
    #                         self._emit_safe('firmware_upgrade_complete', {
    #                             'job_id': job_id,
    #                             'success': True,
    #                             'new_version': new_version,
    #                             'status': status_text,
    #                         })
    #                     else:
    #                         self._emit_safe('firmware_upgrade_complete', {
    #                             'job_id': job_id,
    #                             'success': False,
    #                             'error': error_text or 'Firmware upgrade failed',
    #                             'status': status_text,
    #                         })
    #                     return

    #                 time.sleep(5)

    #         finally:
    #             try:
    #                 session.close()
    #             except Exception:
    #                 pass

    #     except Exception as e:
    #         logger.error(f"[EDGE] Firmware upgrade failed: {e}")
    #         self._emit_safe('firmware_upgrade_complete', {
    #             'job_id': job_id,
    #             'success': False,
    #             'error': str(e),
    #         })
    #     finally:
    #         if temp_dir:
    #             try:
    #                 shutil.rmtree(temp_dir)
    #             except Exception:
    #                 pass

    def _handle_firmware_upgrade(self, command_id: str, params: dict):
        """
        Handle firmware upgrade command from cloud.
        Routes to correct plugin based on plugin_name.
        Power Conditioner: POST multipart to /powerconditioner/firmware-upgrade
        Crestron: login → upload → trigger → poll
        """
        job_id = params.get('job_id')
        ip = params.get('ip')
        port = params.get('port') or 443
        plugin_name = params.get('plugin_name', '')
        username = params.get('username', '')
        password = params.get('password', '')
        firmware_download_url = params.get('firmware_download_url')
        firmware_filename = params.get('firmware_filename')

        if not all([job_id, ip, plugin_name, firmware_download_url, firmware_filename]):
            logger.error(f"[EDGE] Firmware upgrade missing required params: {params}")
            self._emit_safe('firmware_upgrade_complete', {
                'job_id': job_id,
                'success': False,
                'error': 'Missing required params',
            })
            return

        self._emit_safe('firmware_upgrade_progress', {
            'job_id': job_id,
            'progress': 0,
            'status': 'Starting',
            'label': 'Starting firmware upgrade...',
        })

        temp_dir = None
        try:
            # ── Step 1: Download firmware from cloud ──────────────────────
            cloud_url = self.config.get('CLOUD_URL', '').rstrip('/')
            api_key = self.config.get('API_KEY', '')
            download_url = (
                firmware_download_url
                if firmware_download_url.startswith('http')
                else f"{cloud_url}{firmware_download_url}"
            )

            self._emit_safe('firmware_upgrade_progress', {
                'job_id': job_id,
                'progress': 3,
                'status': 'Downloading',
                'label': 'Downloading firmware file from cloud...',
            })

            temp_dir = tempfile.mkdtemp(prefix='fw_upgrade_')
            local_path = os.path.join(temp_dir, firmware_filename)

            dl_headers = {}
            if api_key:
                dl_headers['X-API-Key'] = api_key

            resp = requests.get(download_url, headers=dl_headers, timeout=300, verify=False)
            resp.raise_for_status()
            with open(local_path, 'wb') as f:
                f.write(resp.content)

            logger.info(f"[EDGE] Firmware downloaded: {local_path} ({len(resp.content)} bytes)")

            # ── Step 2: Route to correct upgrade handler ──────────────────
            clean_plugin = self._normalize_plugin_name(plugin_name, params)

            if 'power_conditioner' in clean_plugin:
                self._do_power_conditioner_firmware_upgrade(
                    job_id=job_id,
                    ip=ip,
                    port=int(port or 5000),
                    password=password,   # x-api-key = serial_number
                    local_path=local_path,
                    firmware_filename=firmware_filename,
                )
            else:
                # Default: Crestron flow
                self._do_crestron_firmware_upgrade(
                    job_id=job_id,
                    ip=ip,
                    port=int(port or 443),
                    username=username,
                    password=password,
                    local_path=local_path,
                    firmware_filename=firmware_filename,
                )

        except Exception as e:
            logger.error(f"[EDGE] Firmware upgrade failed: {e}")
            self._emit_safe('firmware_upgrade_complete', {
                'job_id': job_id,
                'success': False,
                'error': str(e),
            })
        finally:
            if temp_dir:
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass


    def _do_power_conditioner_firmware_upgrade(
        self, job_id, ip, port, password, local_path, firmware_filename
    ):
        """
        Power Conditioner firmware upgrade:
        POST /powerconditioner/firmware-upgrade
        Header: x-api-key: <serial_number>
        Body: multipart form — firmware=@firmware.zip
        """
        try:
            self._emit_safe('firmware_upgrade_progress', {
                'job_id': job_id,
                'progress': 10,
                'status': 'Uploading',
                'label': 'Uploading firmware to Power Conditioner...',
            })

            headers = {}
            if password:
                headers['x-api-key'] = str(password).strip()

            url = f"http://{ip}:{port}/powerconditioner/firmware-upgrade"

            logger.info(f"[EDGE] Power Conditioner firmware upload → {url}")

            with open(local_path, 'rb') as fw_file:
                files = {
                    'firmware': (firmware_filename, fw_file, 'application/octet-stream'),
                }
                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    timeout=300,   # 5 min — large file upload
                    verify=False,
                )

            self._emit_safe('firmware_upgrade_progress', {
                'job_id': job_id,
                'progress': 80,
                'status': 'Processing',
                'label': 'Device processing firmware...',
            })

            # ── Parse response ────────────────────────────────────────────
            try:
                response.raise_for_status()
            except Exception as http_err:
                body = ""
                try:
                    body = response.text.strip()
                except Exception:
                    pass
                raise RuntimeError(
                    f"HTTP {response.status_code}: {body or str(http_err)}"
                )

            payload = {}
            if response.text and response.text.strip():
                try:
                    payload = response.json()
                except Exception:
                    payload = {'message': response.text.strip()}

            logger.info(f"[EDGE] Power Conditioner firmware response: {payload}")

            self._emit_safe('firmware_upgrade_progress', {
                'job_id': job_id,
                'progress': 95,
                'status': 'Rebooting',
                'label': 'Device rebooting with new firmware...',
            })

            # ── Report success ────────────────────────────────────────────
            new_version = (
                payload.get('firmware_version')
                or payload.get('version')
                or payload.get('new_version')
                or ''
            )

            self._emit_safe('firmware_upgrade_complete', {
                'job_id': job_id,
                'success': True,
                'new_version': new_version,
                'status': 'SUCCESS',
                'response': payload,
            })
            logger.info(f"[EDGE] Power Conditioner firmware upgrade complete for {ip}")

        except Exception as e:
            logger.error(f"[EDGE] Power Conditioner firmware upgrade failed for {ip}: {e}")
            self._emit_safe('firmware_upgrade_complete', {
                'job_id': job_id,
                'success': False,
                'error': str(e),
                'status': 'FAILED',
            })


    def _do_crestron_firmware_upgrade(
        self, job_id, ip, port, username, password, local_path, firmware_filename
    ):
        """
        Crestron firmware upgrade: login → upload → trigger → poll.
        Extracted from old _handle_firmware_upgrade so it's reusable.
        """
        if not username or not password:
            raise Exception("Crestron device credentials (username/password) not provided")

        from plugin.crestron_firmware_mixin import CrestronFirmwareMixin

        self._emit_safe('firmware_upgrade_progress', {
            'job_id': job_id,
            'progress': 5,
            'status': 'LoggingIn',
            'label': 'Authenticating with device...',
        })

        session, xsrf_token = CrestronFirmwareMixin.login_device(ip, username, password)

        try:
            self._emit_safe('firmware_upgrade_progress', {
                'job_id': job_id,
                'progress': 15,
                'status': 'Uploading',
                'label': 'Uploading firmware to device...',
            })

            upload_ok, upload_result = CrestronFirmwareMixin.upload_firmware(
                session, xsrf_token, ip, local_path, firmware_filename
            )
            if not upload_ok:
                raise Exception(f"Upload failed: {upload_result.get('error', 'Unknown error')}")

            device_path = upload_result.get('device_path', '')

            self._emit_safe('firmware_upgrade_progress', {
                'job_id': job_id,
                'progress': 25,
                'status': 'Triggering',
                'label': 'Triggering firmware upgrade...',
            })

            trigger_ok, trigger_result = CrestronFirmwareMixin.trigger_upgrade(
                session, xsrf_token, ip, device_path
            )
            if not trigger_ok:
                raise Exception(f"Trigger failed: {trigger_result.get('error', 'Unknown error')}")

            poll_start = time.time()
            poll_timeout = 2700  # 45 min

            while True:
                elapsed = time.time() - poll_start
                if elapsed > poll_timeout:
                    raise Exception("Firmware upgrade timed out")

                status = CrestronFirmwareMixin.get_upgrade_status(session, xsrf_token, ip)

                if status.get('_needs_login'):
                    session.close()
                    session, xsrf_token = CrestronFirmwareMixin.login_device(ip, username, password)
                    continue

                progress = status.get('progress', 0)
                status_text = status.get('status', 'Unknown')
                label = status.get('label', '')
                completed = status.get('completed', False)
                success = status.get('success', False)
                error_text = status.get('error')

                scaled_progress = 25 + int(progress * 0.75)

                self._emit_safe('firmware_upgrade_progress', {
                    'job_id': job_id,
                    'progress': scaled_progress,
                    'status': status_text,
                    'label': label or status_text,
                    'raw_status': status.get('raw_status', ''),
                })

                if completed:
                    if success:
                        new_version = CrestronFirmwareMixin.fetch_firmware_version(
                            session, xsrf_token, ip
                        )
                        self._emit_safe('firmware_upgrade_complete', {
                            'job_id': job_id,
                            'success': True,
                            'new_version': new_version,
                            'status': status_text,
                        })
                    else:
                        self._emit_safe('firmware_upgrade_complete', {
                            'job_id': job_id,
                            'success': False,
                            'error': error_text or 'Firmware upgrade failed',
                            'status': status_text,
                        })
                    return

                time.sleep(5)

        finally:
            try:
                session.close()
            except Exception:
                pass



    def _handle_firmware_status_check(self, command_id: str, params: dict):
        """Check if a Crestron device is back online after a firmware upgrade reboot."""
        try:
            ip = params.get('ip')
            username = params.get('username')
            password = params.get('password')
            if not ip:
                self.send_command_result(command_id, 'failed', {'error': 'Missing IP'})
                return
            from plugin.crestron_firmware_mixin import CrestronFirmwareMixin
            session, xsrf_token = CrestronFirmwareMixin.login_device(ip, username, password)
            try:
                fw_version = CrestronFirmwareMixin.fetch_firmware_version(session, xsrf_token, ip)
                self.send_command_result(command_id, 'success', {
                    'firmware_version': fw_version,
                    'online': True,
                })
            finally:
                try:
                    session.close()
                except Exception:
                    pass
        except Exception as e:
            self.send_command_result(command_id, 'failed', {
                'error': str(e),
                'online': False,
            })

    def _probe_device(self, ip: str, port, plugin_name: str, display_id: str, plugin_config: dict) -> dict:
        """Use the real plugin to probe the device."""
        clean_name = self._normalize_plugin_name(plugin_name, {"plugin_config": plugin_config})

        logger.info(f"=== PROBE DEVICE === IP: {ip}, Display ID: {display_id}, Original plugin: {plugin_name}, Clean name: {clean_name}")

        local_plugin_configs = self.config.get('PLUGIN_CONFIGS', {})
        local_config         = local_plugin_configs.get(clean_name, {})
        merged_config        = {**local_config, **plugin_config}

        try:
            from plugin import get_plugin, PLUGIN_REGISTRY
        except ImportError:
            logger.error("[PROBE] plugin package not found in backend/. Falling back to TCP ping.")
            return self._tcp_only_probe(ip, port)

        plugin = get_plugin(clean_name, config=merged_config)

        if not plugin:
            available = list(PLUGIN_REGISTRY.keys())
            logger.warning(
                f"[PROBE] Plugin '{clean_name}' not found in registry. "
                f"Available plugins: {available}. Falling back to TCP ping."
            )
            return self._tcp_only_probe(ip, port)

        if port is None or str(port).strip() == '' or int(port) <= 0:
            port = getattr(plugin, 'default_port', 1515)
        port = int(port)

        logger.info(f"[PROBE] Running plugin '{clean_name}' on {ip}:{port}")
        try:
            device_info = plugin.get_device_info(ip, port, display_id)
            logger.info(f"=== DEVICE INFO === {device_info}")
            if not device_info.get('ip_address'):
                device_info['ip_address'] = ip
            return device_info
        except Exception as e:
            logger.error(f"[PROBE] Plugin '{clean_name}' execution failed: {e}")
            raise


    def _tcp_only_probe(self, ip: str, port) -> dict:
        """Fallback when no matching plugin found."""
        port = int(port) if port else 80
        try:
            sock = socket.create_connection((ip, port), timeout=5)
            sock.close()
            status = 'Online'
        except Exception:
            status = 'Offline'
        return {
            'device_name':    f"Device at {ip}",
            'make':           'Unknown',
            'model':          'Unknown',
            'serial_number':  '',
            'firmware':       '',
            'mac_address':    '',
            'ip_address':     ip,
            'current_status': status,
        }


    def _start_polling(self):
        """Start background thread that polls watchlist devices every 60s."""
        if self._polling_thread and self._polling_thread.is_alive():
            return
        self._polling_active = True
        self._polling_thread = threading.Thread(
            target=self._polling_loop,
            daemon=True
        )
        self._polling_thread.start()
        logger.info("Status polling loop started (every 60s)")


    def _polling_loop(self):
        """Every 60 seconds: snapshot watchlist, TCP ping each device, push status."""
        while self._polling_active and self.connected:
            try:
                with self._watchlist_lock:
                    watchlist = list(self._watchlist)
                if watchlist:
                    statuses = self._poll_all_devices(watchlist)
                    self._send_status_update(statuses)
                    online_count = sum(1 for s in statuses if s['status'] == 'Online')
                    logger.info(f"Status poll: {online_count}/{len(statuses)} devices online")
                else:
                    logger.debug("Watchlist empty, skipping poll")
            except Exception as e:
                logger.error(f"Polling loop error: {e}")
            for _ in range(60):
                if not self._polling_active or not self.connected:
                    break
                time.sleep(1)


    def _poll_all_devices(self, watchlist: list) -> list:
        """TCP ping every device. Deep poll Samsung for live power/input/volume."""
        statuses = []
        for dev in watchlist:
            ip   = dev.get('ip_address')
            port = dev.get('port')
            if not ip:
                continue
            if not port or int(port) <= 0:
                port = 443
            port = int(port)

            plugin_name = (dev.get('plugin_name') or '').lower()
            reachable   = self._tcp_ping(ip, port)

            entry = {
                'ip_address': ip,
                'status':     'Online' if reachable else 'Offline',
            }

              # ── ADD THIS: deep poll for Shure P300, same pattern as Samsung ──
            if reachable and 'shure_p300' in plugin_name:
                try:
                    from plugin import get_plugin
                    p300 = get_plugin('shure_p300')
                    if p300:
                        live = p300.query_status(ip=ip, port=port)
                        if live:
                            # Trust the plugin's reachable flag, not the TCP ping
                            entry['status'] = 'Online' if live.get('reachable') else 'Offline'
                            entry.update({k: v for k, v in live.items() if k != 'reachable'})
                except Exception:
                    pass  # TCP ping result is still recorded

            if reachable and 'samsung' in plugin_name:
                try:
                    from plugin import get_plugin
                    samsung = get_plugin('samsung_mdc')
                    if samsung:
                        # Samsung displays do not reply to MDC broadcast (FE) queries.
                        # Use the same default as the probe flow unless the watchlist supplies an ID.
                        display_id = str(dev.get('display_id') or '00')
                        live = samsung.query_status(ip=ip, port=port, display_id=display_id)
                        if live:
                            entry.update(live)
                except Exception:
                    pass

            statuses.append(entry)
        return statuses


    def _tcp_ping(self, ip: str, port: int, timeout: int = 3) -> bool:
        """TCP connect check."""
        try:
            sock = socket.create_connection((ip, port), timeout=timeout)
            sock.close()
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


    def _send_status_update(self, statuses: list):
        """Push status_update event to cloud."""
        if self.connected and self.edge_id:
            try:
                logger.info(
                    f"Emitting status_update edge_id={self.edge_id} devices={statuses}"
                )
            except Exception:
                logger.info(
                    f"Emitting status_update edge_id={self.edge_id} devices_count={len(statuses)}"
                )
            self._emit_safe('status_update', {
                'edge_id': self.edge_id,
                'devices': statuses,
            })


    # ══════════════════════════════════════════════════════════════
    # PLUGIN UPDATE
    # ══════════════════════════════════════════════════════════════

    def _get_plugin_dir(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugin"))

    def _get_local_plugin_version(self):
        version_path = os.path.join(self._get_plugin_dir(), "version.json")
        if not os.path.exists(version_path):
            return ""
        try:
            with open(version_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data.get("version", "")
        except Exception as e:
            logger.warning(f"[EDGE] Failed to read local plugin version: {e}")
        return ""

    def _check_plugin_version(self):
        if not self.connected:
            return
        current_version = self._get_local_plugin_version()
        self._emit_safe('plugin_version_check', {
            'version': current_version,
            'timestamp': time.time(),
        })

    def _apply_plugin_update(self, payload: dict):
        if not payload:
            return
        version = payload.get('version') or ''
        zip_b64 = payload.get('zip_b64')
        manifest = payload.get('manifest') or []
        if not zip_b64:
            return

        plugin_dir = self._get_plugin_dir()
        os.makedirs(plugin_dir, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix="plugin_update_")
        added_files = []
        updated_files = []
        try:
            def _hash_file(path):
                h = hashlib.sha256()
                with open(path, "rb") as fh:
                    for chunk in iter(lambda: fh.read(8192), b""):
                        h.update(chunk)
                return h.hexdigest()

            zip_bytes = base64.b64decode(zip_b64.encode('ascii'))
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(temp_dir)

            for root, _, files in os.walk(temp_dir):
                for name in files:
                    if name == "__init__.py":
                        continue
                    if not (name.endswith(".py") or name == "version.json"):
                        continue
                    src = os.path.join(root, name)
                    dst = os.path.join(plugin_dir, name)
                    if name.endswith(".py"):
                        if os.path.exists(dst):
                            try:
                                if _hash_file(src) != _hash_file(dst):
                                    updated_files.append(name)
                            except Exception:
                                updated_files.append(name)
                        else:
                            added_files.append(name)
                    shutil.copy2(src, dst)

            if version:
                version_path = os.path.join(plugin_dir, "version.json")
                version_doc = {
                    "version": version,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                if manifest:
                    version_doc["manifest"] = manifest
                with open(version_path, "w", encoding="utf-8") as f:
                    json.dump(version_doc, f, indent=2)

            if manifest:
                self._write_plugin_init(manifest)

            added_files_label   = ",".join(sorted(set(added_files)))   if added_files   else "none"
            updated_files_label = ",".join(sorted(set(updated_files))) if updated_files else "none"
            logger.info(
                f"[EDGE] Plugin update applied: version={version} "
                f"added_files={added_files_label} updated_files={updated_files_label}"
            )

            if (added_files or updated_files) and self.config.get("RESTART_ON_PLUGIN_UPDATE", True):
                logger.info("[EDGE] Plugin update detected changes; restarting Edge Collector")
                self._restart_self()
        except Exception as e:
            logger.error(f"[EDGE] Plugin update failed: {e}")
        finally:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def _restart_self(self):
        """Restart the Edge Collector process after plugin updates."""
        try:
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            args = [sys.executable] + sys.argv
            subprocess.Popen(args, cwd=backend_dir)
        except Exception as e:
            logger.error(f"[EDGE] Failed to restart Edge Collector: {e}")
            return
        os._exit(0)

    # def _write_plugin_init(self, manifest):
    #     """Write a dynamic __init__.py for the plugin package."""
    #     plugin_dir = self._get_plugin_dir()

    #     content = (
    #         "\"\"\"\n"
    #         "Manual Platform Plugin SDK\n"
    #         "==========================\n"
    #         "Package for manual platform plugins (Samsung MDC, Q-SYS, etc.)\n"
    #         "\"\"\"\n\n"
    #         "import os\n"
    #         "import pkgutil\n"
    #         "import importlib\n"
    #         "import inspect\n"
    #         "import logging\n\n"
    #         "from .base import ManualPlatformPlugin\n\n"
    #         "logger = logging.getLogger(__name__)\n\n"
    #         "# Plugin registry (populated dynamically)\n"
    #         "PLUGIN_REGISTRY = {}\n\n"
    #         "def discover_plugins():\n"
    #         "    \"\"\"Dynamically discover and register all plugin classes in this package.\"\"\"\n"
    #         "    global PLUGIN_REGISTRY\n"
    #         "    PLUGIN_REGISTRY = {}\n"
    #         "    plugin_dir = os.path.dirname(__file__)\n"
    #         "    for loader, module_name, is_pkg in pkgutil.walk_packages([plugin_dir]):\n"
    #         "        if module_name in [\"base\", \"__init__\"]:\n"
    #         "            continue\n"
    #         "        try:\n"
    #         "            module = importlib.import_module(f\".{module_name}\", package=__package__)\n"
    #         "            for name, obj in inspect.getmembers(module):\n"
    #         "                if (inspect.isclass(obj) and issubclass(obj, ManualPlatformPlugin) and obj is not ManualPlatformPlugin):\n"
    #         "                    plugin_key = getattr(obj, \"name\", module_name.replace(\"_plugin\", \"\"))\n"
    #         "                    PLUGIN_REGISTRY[plugin_key] = obj\n"
    #         "        except Exception as e:\n"
    #         "            logger.error(f\"Failed to load plugin module {module_name}: {e}\")\n\n"
    #         "discover_plugins()\n"
    #         "logger.info(f\"Loaded {len(PLUGIN_REGISTRY)} plugins: {', '.join(sorted(PLUGIN_REGISTRY.keys()))}\")\n\n"
    #         "def get_plugin(plugin_name, config=None):\n"
    #         "    plugin_class = PLUGIN_REGISTRY.get(plugin_name)\n"
    #         "    if plugin_class:\n"
    #         "        plugin = plugin_class(config)\n"
    #         "        _wrap_plugin_device_info(plugin)\n"
    #         "        return plugin\n"
    #         "    return None\n\n"
    #         "def get_available_plugins():\n"
    #         "    plugins = []\n"
    #         "    for name, plugin_class in PLUGIN_REGISTRY.items():\n"
    #         "        try:\n"
    #         "            instance = plugin_class()\n"
    #         "            plugins.append({\n"
    #         "                \"name\": getattr(instance, \"name\", name),\n"
    #         "                \"display_name\": getattr(instance, \"display_name\", name),\n"
    #         "                \"description\": getattr(instance, \"description\", \"\"),\n"
    #         "                \"supports_display_id\": getattr(instance, \"supports_display_id\", True),\n"
    #         "                \"supports_port\": getattr(instance, \"supports_port\", True),\n"
    #         "                \"default_port\": getattr(instance, \"default_port\", 1515),\n"
    #         "                \"supported_models\": getattr(instance, \"SUPPORTED_MODELS\", []),\n"
    #         "            })\n"
    #         "        except Exception: pass\n"
    #         "    return plugins\n\n"
    #         "def _normalize_device_info(info, ip, port, display_id, plugin):\n"
    #         "    if info is None: info = {}\n"
    #         "    info.setdefault(\"ip_address\", ip)\n"
    #         "    info.setdefault(\"port\", port)\n"
    #         "    info.setdefault(\"display_id\", display_id)\n"
    #         "    make = info.get(\"make\") or getattr(plugin, \"display_name\", None) or \"Unknown\"\n"
    #         "    info[\"make\"] = make\n"
    #         "    model = info.get(\"model\") or \"Unknown\"\n"
    #         "    info[\"model\"] = model\n"
    #         "    if not info.get(\"device_name\"):\n"
    #         "        if make and model and model != \"Unknown\": info[\"device_name\"] = f\"{make} {model}\"\n"
    #         "        elif make and make != \"Unknown\": info[\"device_name\"] = f\"{make} Device\"\n"
    #         "        else: info[\"device_name\"] = f\"Device {ip}\"\n"
    #         "    if not info.get(\"serial_number\") and info.get(\"mac_address\"): info[\"serial_number\"] = info.get(\"mac_address\")\n"
    #         "    if \"current_status\" not in info or not info.get(\"current_status\"):\n"
    #         "        reachable = info.get(\"reachable\")\n"
    #         "        if reachable is True: info[\"current_status\"] = \"Online\"\n"
    #         "        elif reachable is False: info[\"current_status\"] = \"Offline\"\n"
    #         "        else: info[\"current_status\"] = \"Unknown\"\n"
    #         "    return info\n\n"
    #         "def _wrap_plugin_device_info(plugin):\n"
    #         "    if hasattr(plugin, \"_device_info_wrapped\") and plugin._device_info_wrapped: return\n"
    #         "    original = getattr(plugin, \"get_device_info\", None)\n"
    #         "    if not callable(original): return\n"
    #         "    def _wrapped_get_device_info(ip, port=None, display_id=None):\n"
    #         "        info = original(ip, port, display_id)\n"
    #         "        return _normalize_device_info(info, ip, port, display_id, plugin)\n"
    #         "    plugin.get_device_info = _wrapped_get_device_info\n"
    #         "    plugin._device_info_wrapped = True\n\n"
    #         "__all__ = [\"ManualPlatformPlugin\", \"PLUGIN_REGISTRY\", \"get_plugin\", \"get_available_plugins\", \"discover_plugins\"]\n"
    #     )

    #     init_path = os.path.join(plugin_dir, "__init__.py")
    #     with open(init_path, "w", encoding="utf-8") as f:
    #         f.write(content)


    def _write_plugin_init(self, manifest):
        """Write a dynamic __init__.py for the plugin package."""
        plugin_dir = self._get_plugin_dir()

        content = '''"""
    Manual Platform Plugin SDK
    ==========================
    Package for manual platform plugins (Samsung MDC, Q-SYS, etc.)
    """

    import os
    import pkgutil
    import importlib
    import inspect
    import logging

    from .base import ManualPlatformPlugin

    logger = logging.getLogger(__name__)

    # Plugin registry (populated dynamically)
    PLUGIN_REGISTRY = {}

    def discover_plugins():
        """Dynamically discover and register all plugin classes in this package."""
        global PLUGIN_REGISTRY
        PLUGIN_REGISTRY = {}

        plugin_dir = os.path.dirname(__file__)

        for loader, module_name, is_pkg in pkgutil.walk_packages([plugin_dir]):
            if module_name in ["base", "__init__"]:
                continue
            try:
                module = importlib.import_module(f".{module_name}", package=__package__)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, ManualPlatformPlugin) and
                        obj is not ManualPlatformPlugin):
                        plugin_key = getattr(obj, "name", module_name.replace("_plugin", ""))
                        PLUGIN_REGISTRY[plugin_key] = obj
                        logger.debug(f"Registered plugin: {plugin_key} -> {obj.__name__}")
            except Exception as e:
                logger.error(f"Failed to load plugin module {module_name}: {e}")

    discover_plugins()
    logger.info(f"Loaded {len(PLUGIN_REGISTRY)} plugins: {', '.join(sorted(PLUGIN_REGISTRY.keys()))}")

    def get_plugin(plugin_name, config=None):
        plugin_class = PLUGIN_REGISTRY.get(plugin_name)
        if plugin_class:
            plugin = plugin_class(config)
            _wrap_plugin_device_info(plugin)
            return plugin
        return None

    def get_available_plugins():
        plugins = []
        for name, plugin_class in PLUGIN_REGISTRY.items():
            try:
                instance = plugin_class()
                plugins.append({
                    "name": getattr(instance, "name", name),
                    "display_name": getattr(instance, "display_name", name),
                    "description": getattr(instance, "description", ""),
                    "supports_display_id": getattr(instance, "supports_display_id", True),
                    "supports_port": getattr(instance, "supports_port", True),
                    "default_port": getattr(instance, "default_port", 1515),
                    "supported_models": getattr(instance, "SUPPORTED_MODELS", []),
                })
            except Exception: pass
        return plugins

    def _normalize_device_info(info, ip, port, display_id, plugin):
        if info is None: info = {}
        info.setdefault("ip_address", ip)
        info.setdefault("port", port)
        info.setdefault("display_id", display_id)
        make = info.get("make") or getattr(plugin, "display_name", None) or "Unknown"
        info["make"] = make
        model = info.get("model") or "Unknown"
        info["model"] = model
        if not info.get("device_name"):
            if make and model and model != "Unknown": info["device_name"] = f"{make} {model}"
            elif make and make != "Unknown": info["device_name"] = f"{make} Device"
            else: info["device_name"] = f"Device {ip}"
        if not info.get("serial_number") and info.get("mac_address"):
            info["serial_number"] = info.get("mac_address")
        if "current_status" not in info or not info.get("current_status"):
            reachable = info.get("reachable")
            if reachable is True: info["current_status"] = "Online"
            elif reachable is False: info["current_status"] = "Offline"
            else: info["current_status"] = "Unknown"
        return info

    def _wrap_plugin_device_info(plugin):
        if hasattr(plugin, "_device_info_wrapped") and plugin._device_info_wrapped: return
        original = getattr(plugin, "get_device_info", None)
        if not callable(original): return
        def _wrapped_get_device_info(ip, port=None, display_id=None):
            info = original(ip, port, display_id)
            return _normalize_device_info(info, ip, port, display_id, plugin)
        plugin.get_device_info = _wrapped_get_device_info
        plugin._device_info_wrapped = True

    __all__ = ["ManualPlatformPlugin", "PLUGIN_REGISTRY", "get_plugin", "get_available_plugins", "discover_plugins"]
    '''

        init_path = os.path.join(plugin_dir, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"[EDGE] Rewrote plugin __init__.py with dynamic discovery")



    # ══════════════════════════════════════════════════════════════
    # SEND HELPERS
    # ══════════════════════════════════════════════════════════════

    def register_command_handler(self, command_type: str, handler):
        """Register a handler for a custom command type."""
        self.command_handlers[command_type] = handler

    def send_command_result(self, command_id: str, status: str, result):
        """Send command execution result back to cloud."""
        if self.connected:
            self._emit_safe('command_result', {
                'command_id': command_id,
                'status':     status,
                'result':     result,
                'timestamp':  time.time(),
            })

    def send_heartbeat(self):
        """Send heartbeat to cloud every 30s."""
        if self.connected and self.edge_id:
            self._emit_safe('heartbeat', {
                'edge_id':        self.edge_id,
                'cpu_percent':    psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'timestamp':      time.time(),
            })

    def _get_connected_namespace(self) -> str:
        """Return a namespace that is actually connected."""
        try:
            namespaces = getattr(self.sio, 'namespaces', {}) or {}
            if self.namespace in namespaces:
                return self.namespace
            if namespaces:
                return next(iter(namespaces.keys()))
        except Exception:
            pass
        return self.namespace

    def _emit_safe(self, event: str, payload: dict):
        """Emit using a connected namespace to avoid BadNamespaceError."""
        ns = self._get_connected_namespace()
        try:
            self.sio.emit(event, payload, namespace=ns)
        except sio_exceptions.BadNamespaceError:
            logger.warning(
                f"[EDGE] Emit failed: namespace '{ns}' not connected. "
                f"Configured namespace='{self.namespace}'."
            )

    def start(self):
        """Connect to cloud and maintain connection forever with auto-reconnect."""
        while True:
            self.config        = Config.load()
            self.cloud_url     = self.config.get('CLOUD_URL', '')
            self.api_key       = self.config.get('API_KEY', '')
            self.socketio_path = self.config.get('SOCKETIO_PATH', 'socket.io') or 'socket.io'
            self.namespace     = self.config.get('SOCKETIO_NAMESPACE') or '/'

            if not self.cloud_url or not self.api_key:
                logger.warning("Cloud URL or API Key not configured. Retrying in 30s...")
                time.sleep(30)
                continue

            try:
                if self.connected or getattr(self.sio, "connected", False):
                    time.sleep(5)
                    continue

                logger.info(f"Connecting to cloud: {self.cloud_url}")

                connect_kwargs = {
                    'headers':       {'X-API-Key': self.api_key},
                    'transports':    ['websocket', 'polling'],
                    'socketio_path': self.socketio_path,
                }

                if self.namespace != '/':
                    connect_kwargs['namespaces'] = [self.namespace]

                self.sio.connect(self.cloud_url, **connect_kwargs)

                while self.connected:
                    self.send_heartbeat()
                    time.sleep(30)

            except Exception as e:
                logger.error(f"Cloud connection error: {e}")
                self.connected       = False
                self._polling_active = False
                EdgeState.set('cloud_connected', False)
                time.sleep(10)
