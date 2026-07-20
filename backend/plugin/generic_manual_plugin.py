"""
Manual Platform Plugin: GenericManualPlugin
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


class GenericManualPlugin(ManualPlatformPlugin):
    """Generic manual device plugin: metadata entered by user, status via ping."""

    name = "generic_manual"
    display_name = "Generic"
    description = "Generic device (manual metadata + ping status)"
    supports_display_id = False
    supports_port = False
    default_port = 0
    SUPPORTED_MODELS = ["Generic"]

    COMMANDS = {}
    QUERY_COMMANDS = {}

    def _ping_host(self, ip):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        try:
            result = subprocess.run(["ping", param, "1", ip], capture_output=True, timeout=3)
            return result.returncode == 0
        except Exception:
            return False

    def get_device_info(self, ip, port=0, display_id=None):
        online = self._ping_host(ip)
        return {
            "ip_address": ip,
            "port": port,
            "display_id": display_id,
            "make": "Generic",
            "device_name": "Generic Device",
            "model": "Generic",
            "serial_number": None,
            "firmware": None,
            "current_status": "Online" if online else "Offline"
        }

    def send_command(self, ip, port, display_id, command):
        return False, "Generic plugin is monitoring-only."

    def query_status(self, ip, port=0, display_id=None):
        online = self._ping_host(ip)
        return {
            "reachable": online,
            "status": "Online" if online else "Offline"
        }
