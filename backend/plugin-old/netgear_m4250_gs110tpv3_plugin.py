"""
Manual Platform Plugin: NetgearM4250GS110TPv3Plugin
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


class NetgearM4250GS110TPv3Plugin(ManualPlatformPlugin):
    """Netgear M4250 / GS110TPv3 plugin via SNMP v2c."""

    name = "netgear_m4250_gs110tpv3"
    display_name = "Netgear M4250 / GS110TPv3"
    description = "Netgear M4250, GS110TPv3 (IP only)"
    supports_display_id = False
    supports_port = False
    default_port = 161
    default_snmp_community = "RMM"
    output_format = "json"
    SUPPORTED_MODELS = ["M4250", "GS110TPv3"]

    STANDARD_OIDS = {
        "sys_descr": "1.3.6.1.2.1.1.1.0",
        "sys_object_id": "1.3.6.1.2.1.1.2.0",
        "sys_uptime": "1.3.6.1.2.1.1.3.0",
        "sys_contact": "1.3.6.1.2.1.1.4.0",
        "sys_name": "1.3.6.1.2.1.1.5.0",
        "sys_location": "1.3.6.1.2.1.1.6.0",
    }

    NETGEAR_OIDS = {
        "product_serial": "1.3.6.1.4.1.4526.10.1.1.2.1.1.1.3.1",
        "product_firmware": "1.3.6.1.4.1.4526.10.1.1.2.1.1.1.5.1",
        "device_mac": "1.3.6.1.4.1.4526.10.1.1.2.1.1.1.4.1",
        "hardware_version": "1.3.6.1.4.1.4526.10.1.1.2.1.1.1.7.1",
    }

    def _parse_value(self, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            if len(value) == 6:
                return ":".join([f"{b:02x}" for b in value]).upper()
            return value.decode("utf-8", errors="ignore").strip()
        return str(value).strip()

    def _extract_firmware(self, desc):
        match = re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b", str(desc or ""))
        return match.group(1) if match else "Unknown"

    def _extract_short_model(self, desc):
        text = str(desc or "")
        gs_match = re.search(r"\bGS110TPv3\b", text, re.IGNORECASE)
        if gs_match:
            return "GS110TPv3"
        m4250_match = re.search(r"\bM4250[-\w]*\b", text, re.IGNORECASE)
        if m4250_match:
            return m4250_match.group(0)
        return "Unknown"

    def _format_uptime(self, ticks):
        try:
            total_seconds = int(ticks) // 100
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{days}d {hours}h {minutes}m {seconds}s"
        except Exception:
            return "Unknown"

    async def _snmp_get(self, engine, auth_data, target, oid):
        try:
            from pysnmp.hlapi.v3arch.asyncio import (
                ContextData,
                ObjectIdentity,
                ObjectType,
                get_cmd,
            )

            error_indication, error_status, _, var_binds = await get_cmd(
                engine,
                auth_data,
                target,
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
            )

            if error_indication or error_status:
                return None

            for _, value in var_binds:
                return value
        except Exception:
            return None
        return None

    async def _collect_info_async(self, ip, community):
        try:
            from pysnmp.hlapi.v3arch.asyncio import (
                CommunityData,
                SnmpEngine,
                UdpTransportTarget,
            )
        except Exception:
            return {
                "ip_address": ip,
                "make": "Netgear",
                "device_name": f"Netgear {ip}",
                "model": "Unknown",
                "serial_number": None,
                "mac_address": None,
                "firmware": None,
                "current_status": "Offline",
                "error": "pysnmp with asyncio support is required for Netgear SNMP plugin."
            }

        engine = SnmpEngine()
        info = {
            "ip_address": ip,
            "make": "Netgear",
            "device_type": "Netgear Switch",
            "device_name": f"Netgear {ip}",
            "system_name": "Unknown",
            "system_description": "Unknown",
            "model": "Unknown",
            "serial_number": "Unknown",
            "mac_address": "Unknown",
            "firmware": "Unknown",
            "firmware_version": "Unknown",
            "hardware_version": "Unknown",
            "uptime": "Unknown",
            "location": "Unknown",
            "contact": "Unknown",
            "notes": "",
            "format": self.output_format,
            "current_status": "Offline",
        }

        try:
            target = await UdpTransportTarget.create((ip, 161), timeout=3, retries=1)
            auth = CommunityData(community, mpModel=1)  # SNMP v2c

            sys_name = await self._snmp_get(engine, auth, target, self.STANDARD_OIDS["sys_name"])
            if sys_name:
                info["system_name"] = self._parse_value(sys_name)
                info["device_name"] = info["system_name"]

            sys_desc = await self._snmp_get(engine, auth, target, self.STANDARD_OIDS["sys_descr"])
            if sys_desc:
                info["system_description"] = self._parse_value(sys_desc)
                info["model"] = self._extract_short_model(info["system_description"])
                firmware = self._extract_firmware(info["system_description"])
                if firmware != "Unknown":
                    info["firmware"] = firmware
                    info["firmware_version"] = firmware

            for key, oid in self.NETGEAR_OIDS.items():
                value = await self._snmp_get(engine, auth, target, oid)
                if not value:
                    continue
                parsed = self._parse_value(value)
                if key == "product_serial" and parsed:
                    info["serial_number"] = parsed
                elif key == "device_mac" and parsed:
                    info["mac_address"] = parsed
                elif key == "product_firmware" and parsed and info["firmware"] == "Unknown":
                    info["firmware"] = parsed
                    info["firmware_version"] = parsed
                elif key == "hardware_version" and parsed:
                    info["hardware_version"] = parsed

            uptime_ticks = await self._snmp_get(engine, auth, target, self.STANDARD_OIDS["sys_uptime"])
            if uptime_ticks is not None:
                info["uptime"] = self._format_uptime(uptime_ticks)

            location = await self._snmp_get(engine, auth, target, self.STANDARD_OIDS["sys_location"])
            if location:
                info["location"] = self._parse_value(location)

            contact = await self._snmp_get(engine, auth, target, self.STANDARD_OIDS["sys_contact"])
            if contact:
                info["contact"] = self._parse_value(contact)

            sys_object_id = await self._snmp_get(engine, auth, target, self.STANDARD_OIDS["sys_object_id"])
            if sys_object_id and "4526" in str(sys_object_id):
                info["notes"] = "Netgear confirmed"

            if info["system_name"] != "Unknown" or info["system_description"] != "Unknown":
                info["current_status"] = "Online"
            else:
                info["error"] = "SNMP response not received. Check IP/community."
        except Exception as e:
            info["error"] = str(e)
        finally:
            try:
                engine.close_dispatcher()
            except Exception:
                pass

        return info

    def get_device_info(self, ip, port=161, display_id=None):
        community = (self.config.get("snmp_community") or self.default_snmp_community).strip()

        try:
            info = asyncio.run(self._collect_info_async(ip, community))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                info = loop.run_until_complete(self._collect_info_async(ip, community))
            finally:
                loop.close()

        model_value = info.get("model")
        if isinstance(model_value, str):
            info["model"] = model_value[:100]
        return info

    def send_command(self, ip, port, display_id, command):
        return False, "Netgear SNMP plugin is monitoring-only."

    def query_status(self, ip, port=161, display_id=None):
        info = self.get_device_info(ip, port, display_id)
        return {
            "reachable": info.get("current_status") == "Online",
            "device_name": info.get("device_name"),
            "model": info.get("model"),
            "serial_number": info.get("serial_number"),
            "firmware": info.get("firmware"),
            "error": info.get("error")
        }
