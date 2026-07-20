"""
Manual Platform Plugin: LogitechCollabOSPlugin
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


class LogitechCollabOSPlugin(ManualPlatformPlugin):
    """Logitech CollabOS plugin via local REST API."""

    name = "logitech_collabos"
    display_name = "Logitech CollabOS"
    description = "Logitech Rally/RoomMate/Tap/Sight devices"
    supports_display_id = False
    supports_port = False
    default_port = 443
    SUPPORTED_MODELS = [
        "Rally Board 65","Rally Bar","Rally Bar Mini","Rally Bar Huddle","MeetUp 2","Rally Bar No-Radio","RoomMate","Tap Scheduler","Tap IP","Sight","Logi Dock Flex","Rally AI Camera Pro","Rally AI Camera",
    ]

    COMMANDS = {}
    QUERY_COMMANDS = {}

    def _login(self, session, host, username, password, port):
        url = f"https://{host}:{port}/api/v1/signin"
        response = session.post(
            url,
            json={"username": username, "password": password},
            timeout=10
        )
        response.raise_for_status()

        token = (response.json().get("result") or {}).get("auth_token")
        if not token:
            raise Exception("Login failed - No auth token ")

        session.headers.update({"Authorization": f"Bearer {token}"})

    def _get_device(self, session, host, port):
        url = f"https://{host}:{port}/api/v1/device"
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("result") or {}

    def get_device_info(self, ip, port=443, display_id=None):
        username = self.config.get("username")
        password = self.config.get("password")

        if not username or not password:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Logitech",
                "device_type": "Logitech Device",
                "current_status": "Offline",
                "error": "Missing credentials: username and password are required. "
            }

        session = requests.Session()
        session.verify = False
        session.headers.update({"Content-Type": "application/json"})

        try:
            self._login(session, ip, username, password, port)
            device = self._get_device(session, ip, port)

            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Logitech",
                "device_name": device.get("deviceName") or device.get("modelName") or "Logitech Device",
                "model": device.get("modelName"),
                "serial_number": device.get("serialNumber"),
                "firmware": device.get("collabOSVersion"),
                "hardware_version": device.get("hwVersion"),
                "system_name": device.get("systemName"),
                "mac_address": device.get("ethernetMAC") or device.get("wifiMAC"),
                "wifi_mac": device.get("wifiMAC"),
                "service_provider": device.get("serviceProvider"),
                "device_configuration": device.get("deviceConfiguration"),
                "device_type": "Logitech CollabOS",
                "current_status": "Online",
                "raw_data": device
            }
        except Exception as e:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Logitech",
                "device_type": "Logitech Device",
                "current_status": "Offline",
                "error": str(e)
            }
        finally:
            try:
                session.close()
            except Exception:
                pass

    def send_command(self, ip, port, display_id, command):
        return False, "Logitech plugin is monitoring-only."

    def query_status(self, ip, port=443, display_id=None):
        info = self.get_device_info(ip, port, display_id)
        return {
            "reachable": info.get("current_status") == "Online",
            "device_name": info.get("device_name"),
            "model": info.get("model"),
            "serial_number": info.get("serial_number"),
            "firmware": info.get("firmware"),
            "error": info.get("error")
        }
