# power_conditioner_services.py
"""

Cloud Connector Service

Maintains persistent WebSocket connection to the Cloud Platform.
 
- Registers edge on startup using API key

- Receives 'sync_devices' from cloud → builds local watchlist

- Receives 'probe_device' command → uses real plugin package to probe device → returns full device_info

- Status polling loop → every 60s pings all watchlist devices → sends status_update

- Heartbeat every 30s → keeps connection alive, updates last_seen on cloud

"""

 
import socketio

import logging

import time

import threading

import platform

import psutil

import socket

import json

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
 
        # Watchlist: list of dicts pushed by cloud via sync_devices

        # Each entry: { ip_address, port, protocol, plugin_name, plugin_config? }

        self._watchlist      = []

        self._watchlist_lock = threading.Lock()
 
        # Status polling thread

        self._polling_thread = None

        self._polling_active = False
 
        self._setup_socket_events()
 
 
    # ════════════════════════════════════════════════════════════

    # SOCKET.IO EVENT SETUP

    # ════════════════════════════════════════════════════════════
 
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
 
        @self.sio.on('registration_failed', namespace=self.namespace)

        def on_registration_failed(data):

            logger.error(f"Registration failed: {data.get('error')}. Check your API key.")

            self.sio.disconnect()
 
        @self.sio.on('sync_devices', namespace=self.namespace)

        def on_sync_devices(data):

            """

            Cloud pushes the full device list for this edge to monitor.

            data = {

                devices: [

                    { ip_address, port, protocol, plugin_name, plugin_config? },

                    ...

                ]

            }

            """

            devices = data.get('devices', [])

            with self._watchlist_lock:

                self._watchlist = devices

            EdgeState.set('watchlist', devices)

            logger.info(f"Watchlist synced: {len(devices)} devices to monitor")
 
        @self.sio.on('command', namespace=self.namespace)

        def on_command(data):

            """

            Cloud sends a command. Runs in a separate thread so

            the socket event loop is never blocked.

            """

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
 
 
    # ════════════════════════════════════════════════════════════

    # REGISTRATION

    # ════════════════════════════════════════════════════════════
 
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
 
 
    # ════════════════════════════════════════════════════════════

    # COMMAND HANDLING

    # ════════════════════════════════════════════════════════════
 
    def _handle_command(self, data: dict):

        """Route incoming command to the correct handler."""

        command_type = data.get('command_type', '')

        command_id   = data.get('command_id')

        params       = data.get('params', {})
 
        if command_type == 'probe_device':

            self._handle_probe_device(command_id, params)

            return
 
        # Other command types use registered handlers

        handler = self.command_handlers.get(command_type)

        if handler:

            try:

                result = handler(data.get('device_id'), params)

                self.send_command_result(command_id, 'success', result)

            except Exception as e:

                logger.error(f"Command '{command_type}' failed: {e}")

                self.send_command_result(command_id, 'failed', str(e))

        else:

            logger.warning(f"No handler registered for command: {command_type}")

            self.send_command_result(command_id, 'failed', f'Unknown command: {command_type}')
 
 
    def _handle_probe_device(self, command_id: str, params: dict):

        """

        Cloud asks edge to probe a local device and return its full info.
 
        params = {

            ip,

            port,

            protocol,

            plugin_name,       e.g. "manual_qsys" or "manual_samsung_mdc"

            plugin_config      optional dict: { username, password, ... }

        }
 
        Sends command_result back to cloud:

          success → full device_info dict (model, serial, firmware, status, etc.)

          failed  → { error, ip_address, current_status: "Offline" }

        """

        ip            = params.get('ip')

        port          = params.get('port')

        plugin_name   = params.get('plugin_name', '')

        plugin_config = params.get('plugin_config') or {}
 
        logger.info(f"Probing device: {ip}:{port} plugin={plugin_name}")
 
        try:

            device_info = self._probe_device(ip, port, plugin_name, plugin_config)

            self.send_command_result(command_id, 'success', device_info)

            logger.info(

                f"Probe success: {ip} -> "

                f"model={device_info.get('model', '?')} "

                f"serial={device_info.get('serial_number', '?')} "

                f"status={device_info.get('current_status', '?')}"

            )
 
            logger.info(f"Probe device_info: {device_info}")

        except Exception as e:

            logger.error(f"Probe failed for {ip}:{port} — {e}")

            self.send_command_result(command_id, 'failed', {

                'error':          str(e),

                'ip_address':     ip,

                'current_status': 'Offline'

            })
 
 
    def _probe_device(self, ip: str, port, plugin_name: str, plugin_config: dict) -> dict:

        """

        Use the real plugin (from plugin package) to probe the device.
 
        This is the same plugin code the cloud uses, but running here on the

        edge PC where the device is actually reachable on the local network.
 
        plugin_name arrives as "manual_qsys", "manual_samsung_mdc", etc.

        Strip "manual_" prefix to get the PLUGIN_REGISTRY key.
 
        plugin_config from cloud contains credentials:

          { "username": "admin", "password": "pass123" }
 
        Merged with local defaults from config.json PLUGIN_CONFIGS.

        Cloud-passed config takes priority.

        """

        # Step 1: clean plugin name

        clean_name = plugin_name.replace('manual_', '').strip()
 
        # Step 2: merge credentials

        local_plugin_configs = self.config.get('PLUGIN_CONFIGS', {})

        local_config         = local_plugin_configs.get(clean_name, {})

        merged_config        = {**local_config, **plugin_config}
 
        # Step 3: load plugin from plugin package (same file as cloud)

        try:

            from plugin import get_plugin

        except ImportError:

            logger.error("plugin package not found in backend/. Make sure it exists.")

            return self._tcp_only_probe(ip, port)
 
        plugin = get_plugin(clean_name, config=merged_config)
 
        if not plugin:

            logger.warning(f"Plugin '{clean_name}' not in registry. Falling back to TCP ping.")

            return self._tcp_only_probe(ip, port)
 
        # Step 4: resolve port — use plugin default if not provided

        if port is None or str(port).strip() == '' or int(port) <= 0:

            port = getattr(plugin, 'default_port', 1515)

        port = int(port)
 
        # Step 5: call plugin exactly like cloud does

        logger.info(f"Running plugin '{clean_name}' on {ip}:{port}")

        device_info = plugin.get_device_info(ip, port, "00")
 
        # Always ensure ip_address is in result

        if not device_info.get('ip_address'):

            device_info['ip_address'] = ip
 
        return device_info
 
 
    def _tcp_only_probe(self, ip: str, port) -> dict:

        """

        Fallback when no matching plugin found.

        Just checks TCP reachability and returns minimal device info.

        """

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
 
 
    # ════════════════════════════════════════════════════════════

    # STATUS POLLING LOOP

    # ════════════════════════════════════════════════════════════
 
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

        """

        Every 60 seconds:

        1. Snapshot current watchlist

        2. TCP ping each device — fast Online/Offline check

        3. Push status_update to cloud

        """

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
 
            # Wait 60s, wake every second to check stop signal

            for _ in range(60):

                if not self._polling_active or not self.connected:

                    break

                time.sleep(1)
 
 
    def _poll_all_devices(self, watchlist: list) -> list:

        """

        TCP ping every device in the watchlist.

        Fast check only — full plugin probe only happens on onboarding.

        Returns list of { ip_address, status } dicts.

        """

        statuses = []

        for dev in watchlist:

            ip   = dev.get('ip_address')

            port = dev.get('port')
 
            if not ip:

                continue
 
            if not port or int(port) <= 0:

                port = 443

            port = int(port)
 
            reachable = self._tcp_ping(ip, port)

            statuses.append({

                'ip_address': ip,

                'status':     'Online' if reachable else 'Offline',

            })
 
        return statuses
 
 
    def _tcp_ping(self, ip: str, port: int, timeout: int = 3) -> bool:

        """TCP connect check. Returns True if reachable, False if not."""

        try:

            sock = socket.create_connection((ip, port), timeout=timeout)

            sock.close()

            return True

        except (socket.timeout, ConnectionRefusedError, OSError):

            return False
 
 
    def _send_status_update(self, statuses: list):

        """Push status_update event to cloud."""

        if self.connected and self.edge_id:

            self._emit_safe('status_update', {

                'edge_id': self.edge_id,

                'devices': statuses,

            })
 
 
    # ════════════════════════════════════════════════════════════

    # SEND HELPERS

    # ════════════════════════════════════════════════════════════
 
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

        """

        Return a namespace that is actually connected.

        Falls back to any connected namespace if configured one isn't connected.

        """

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
 
 
    # ════════════════════════════════════════════════════════════

    # MAIN LOOP

    # ════════════════════════════════════════════════════════════
 
    def start(self):

        """Connect to cloud and maintain connection forever with auto-reconnect."""

        while True:

            # Reload config each attempt — picks up any settings changes

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

                    'transports':    ['websocket'],

                    'socketio_path': self.socketio_path,

                }

                if self.namespace != '/':

                    connect_kwargs['namespaces'] = [self.namespace]
 
                self.sio.connect(self.cloud_url, **connect_kwargs)
 
                # Keep sending heartbeats while connected

                while self.connected:

                    self.send_heartbeat()

                    time.sleep(30)
 
            except Exception as e:

                logger.error(f"Cloud connection error: {e}")

                self.connected       = False

                self._polling_active = False

                EdgeState.set('cloud_connected', False)

                time.sleep(10)





 
