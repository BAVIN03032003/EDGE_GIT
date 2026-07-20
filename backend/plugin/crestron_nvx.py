"""
crestron_nvx.py - Crestron DM-NVX Endpoint Plugin for Edge Collector
"""

import json
import time
import re
import sys
import subprocess
import logging
import requests
from requests.auth import HTTPDigestAuth

from .base import ManualPlatformPlugin
from .crestron_firmware_mixin import CrestronFirmwareMixin

logger = logging.getLogger(__name__)

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class CrestronNVXPlugin(CrestronFirmwareMixin, ManualPlatformPlugin):
    """Crestron DM-NVX Endpoint Plugin for Edge Collector."""

    name = "crestron_nvx"
    display_name = "Crestron DM-NVX Endpoint"
    description = "Crestron DM-NVX 360 Series Encoder/Decoder Manager"
    supports_display_id = False
    supports_port = False
    default_port = 443
    
    SUPPORTED_MODELS = [
        "DM-NVX-350", "DM-NVX-351", "DM-NVX-352", "DM-NVX-360", "DM-NVX-361", "DM-NVX-362",
        "DM-NVX-363", "DM-NVX-364", "DM-NVX-365", "DM-NVX-366", "DM-NVX-370", "DM-NVX-371",
        "DM-NVX-372", "DM-NVX-373", "DM-NVX-374", "DM-NVX-375", "DM-NVX-376", "DM-NVX-380",
        "DM-NVX-381", "DM-NVX-382", "DM-NVX-383", "DM-NVX-384", "DM-NVX-385", "DM-NVX-386",
        "DM-NVX-D30", "DM-NVX-D30C", "DM-NVX-E30", "DM-NVX-E30C",
    ]
    SUPPORTED_FIRMWARE_MODELS = {
        model: {"extensions": [".puf", ".zip"]}
        for model in [
            "DM-NVX-350", "DM-NVX-351", "DM-NVX-352", "DM-NVX-360", "DM-NVX-361", "DM-NVX-362",
            "DM-NVX-363", "DM-NVX-364", "DM-NVX-365", "DM-NVX-366", "DM-NVX-370", "DM-NVX-371",
            "DM-NVX-372", "DM-NVX-373", "DM-NVX-374", "DM-NVX-375", "DM-NVX-376", "DM-NVX-380",
            "DM-NVX-381", "DM-NVX-382", "DM-NVX-383", "DM-NVX-384", "DM-NVX-385", "DM-NVX-386",
            "DM-NVX-D30", "DM-NVX-D30C", "DM-NVX-E30", "DM-NVX-E30C",
        ]
    }

    def __init__(self, config=None):
        super().__init__(config)
        self.username = self.config.get("username") if self.config else None
        self.password = self.config.get("password") if self.config else None
        self.session = None
        self._xsrf_token = None
        logger.info(f"[CrestronNVX] Initialized")

    def _login(self, ip):
        """Login and return session with proper XSRF token handling"""
        if not self.username or not self.password:
            raise Exception("Missing credentials")
            
        base_url = f"https://{ip}"
        login_url = f"{base_url}/userlogin.html"
        session = requests.Session()
        session.verify = False
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        r = session.get(login_url, timeout=8)
        r.raise_for_status()
        trackid = session.cookies.get("TRACKID")
        if not trackid:
            raise Exception("TRACKID cookie not found on login page.")

        r2 = session.post(
            login_url,
            headers={
                "Cookie": f"TRACKID={trackid}",
                "Origin": base_url,
                "Referer": login_url,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"login": self.username, "passwd": self.password},
            timeout=10,
        )

        if r2.status_code == 403:
            raise Exception("Invalid credentials (403).")
        if r2.status_code != 200:
            raise Exception(f"Login failed (HTTP {r2.status_code})")

        xsrf = r2.headers.get("CREST-XSRF-TOKEN")
        if xsrf:
            session.headers.update({
                "CREST-XSRF-TOKEN": xsrf,
                "X-CREST-XSRF-TOKEN": xsrf,
            })
            self._xsrf_token = xsrf

        logger.info(f"[CrestronNVX] Login successful for {ip}")
        return session

    def _safe_get(self, session, ip, path):
        """Safe GET request that handles string responses"""
        url = f"https://{ip}{path}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }
        if self._xsrf_token:
            headers["CREST-XSRF-TOKEN"] = self._xsrf_token
            headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token
        
        try:
            r = session.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            try:
                return r.json()
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"[CrestronNVX] Non-JSON response from {path}: {r.text[:100]}")
                return {}
        except Exception as e:
            logger.error(f"[CrestronNVX] GET {path} failed: {e}")
            return {}

    def _get(self, session, ip, path):
        """Make API request - alias for _safe_get"""
        return self._safe_get(session, ip, path)

    def _post(self, session, ip, path, payload):
        url = f"https://{ip}{path}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._xsrf_token:
            headers["CREST-XSRF-TOKEN"] = self._xsrf_token
            headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token
        
        try:
            r = session.post(url, json=payload, headers=headers, timeout=15)
            
            if r.status_code == 403:
                logger.warning("[CrestronNVX] Session expired, re-authenticating...")
                session = self._login(ip)
                if self._xsrf_token:
                    headers["CREST-XSRF-TOKEN"] = self._xsrf_token
                    headers["X-CREST-XSRF-TOKEN"] = self._xsrf_token
                r = session.post(url, json=payload, headers=headers, timeout=15)
            
            r.raise_for_status()
            try:
                return r.json()
            except (json.JSONDecodeError, ValueError):
                return {"status": r.status_code, "text": r.text}
        except Exception as e:
            logger.error(f"[CrestronNVX] POST {path} failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def _clean_value(value):
        if value is None:
            return None
        value = str(value).strip()
        if not value or value in {"-", "—", "â€”"}:
            return None
        return value

    # ========== DEVICE INFO ==========
    
    def get_device_info(self, ip, port=443, display_id=None):
        """Get device information"""
        if not self.username or not self.password:
            return {
                "ip_address": ip,
                "make": "Crestron",
                "device_type": "Crestron DM-NVX",
                "current_status": "Offline",
                "error": "Missing credentials",
            }

        session = None
        try:
            session = self._login(ip)
            
            # Get device info
            data = self._get(session, ip, "/Device/DeviceInfo")
            di = data.get("Device", {}).get("DeviceInfo", {}) if isinstance(data, dict) else {}
            
            # Get device mode
            spec_data = self._get(session, ip, "/Device/DeviceSpecific")
            ds = spec_data.get("Device", {}).get("DeviceSpecific", {}) if isinstance(spec_data, dict) else {}
            
            # Get device name from localization (this is the UI display name)
            loc_data = self._get(session, ip, "/Device/Localization")
            loc = loc_data.get("Device", {}).get("Localization", {}) if isinstance(loc_data, dict) else {}
            device_name = loc.get("Name", di.get("Name", "DM-NVX"))
            
            # Get ethernet info for hostname
            eth_data = self._get(session, ip, "/Device/Ethernet")
            eth = eth_data.get("Device", {}).get("Ethernet", {}) if isinstance(eth_data, dict) else {}
            hostname = eth.get("HostName", "")
            
            return {
                "ip_address": ip,
                "make": "Crestron",
                "device_name": self._clean_value(device_name),
                "model": self._clean_value(di.get("Model")),
                "serial_number": self._clean_value(di.get("SerialNumber")),
                "mac_address": self._clean_value(di.get("MacAddress")),
                "firmware": self._clean_value(di.get("DeviceVersion")),
                "puf_version": self._clean_value(di.get("PufVersion")),
                "build_date": self._clean_value(di.get("BuildDate")),
                "device_mode": self._clean_value(ds.get("DeviceMode", "Receiver")),
                "audio_mode": self._clean_value(ds.get("AudioMode", "Insert")),
                "hostname": self._clean_value(hostname),
                "device_type": "Crestron DM-NVX",
                "current_status": "Online",
            }
        except Exception as e:
            logger.error(f"[CrestronNVX] get_device_info failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "ip_address": ip,
                "make": "Crestron",
                "device_type": "Crestron DM-NVX",
                "current_status": "Offline",
                "error": str(e),
            }
        finally:
            if session:
                session.close()

    # ========== ETHERNET INFO ==========
    
    def get_ethernet_info(self, ip, port=443):
        """Get Ethernet/IP settings"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/Ethernet")
            
            if not isinstance(data, dict):
                return {"current_ip": ip}
                
        except Exception as e:
            logger.warning(f"[CrestronNVX] get_ethernet_info failed: {e}")
            return {"current_ip": ip}
        finally:
            if session:
                session.close()

        eth_root = data.get("Device", {}).get("Ethernet", {}) if isinstance(data, dict) else {}
        hostname = eth_root.get("HostName", "")
        domain = eth_root.get("DomainName", "")
        ssh_enabled = eth_root.get("IsSshEnabled", False)
        icmp_enabled = eth_root.get("IsIcmpPingEnabled", True)
        igmp_version = eth_root.get("IgmpVersion", "v2")
        
        # Get IPv6 status
        ipv6_enabled = self.get_ipv6_status(ip, port)
        
        adapters = eth_root.get("Adapters", [])
        lan_ip = ip
        lan_subnet = ""
        lan_gateway = ""
        lan_mac = ""
        dhcp_enabled = True
        dns_servers = []
        
        for adapter in adapters:
            if adapter.get("Type") == "EthernetLan" or adapter.get("Name") == "FEC1":
                ipv4 = adapter.get("IPv4", {})
                addresses = ipv4.get("Addresses", [])
                if addresses and addresses[0].get("Address"):
                    lan_ip = addresses[0].get("Address")
                    lan_subnet = addresses[0].get("SubnetMask", "")
                lan_gateway = ipv4.get("DefaultGateway", "")
                lan_mac = adapter.get("MacAddress", "")
                dhcp_enabled = ipv4.get("IsDhcpEnabled", True)
                dns_servers = ipv4.get("DnsServers", [])
                break
        
        return {
            "hostname": self._clean_value(hostname),
            "domain": self._clean_value(domain),
            "current_ip": lan_ip,
            "subnet_mask": lan_subnet,
            "gateway": lan_gateway,
            "mac_address": lan_mac,
            "dhcp_enabled": dhcp_enabled,
            "dns_servers": dns_servers,
            "ssh_enabled": ssh_enabled,
            "icmp_enabled": icmp_enabled,
            "igmp_version": igmp_version,
            "ipv6_enabled": ipv6_enabled,
        }

    def get_ipv6_status(self, ip, port=443):
        """Get IPv6 enabled status"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/NetworkAdapters")
            if isinstance(data, dict):
                schema = data.get("Device", {}).get("NetworkAdapters", {}).get("AddressSchema", "IPv4")
                return schema == "IPv4AndIPv6"
            return False
        except:
            return False
        finally:
            if session:
                session.close()

    # ========== STREAM STATUS ==========
    
    def get_stream_status(self, ip, port=443):
        """Get stream transmitter and receiver status"""
        session = None
        try:
            session = self._login(ip)
            
            tx_status = {}
            rx_status = {}
            
            # Transmitter status
            tx_data = self._get(session, ip, "/Device/StreamTransmit")
            if isinstance(tx_data, dict):
                tx_streams = tx_data.get("Device", {}).get("StreamTransmit", {}).get("Streams", [])
                if tx_streams and isinstance(tx_streams, list) and len(tx_streams) > 0:
                    s = tx_streams[0]
                    if isinstance(s, dict):
                        tx_status = {
                            "status": s.get("Status", "Stopped"),
                            "started": s.get("Start", False),
                            "multicast_address": s.get("MulticastAddress", ""),
                            "bitrate_mode": s.get("BitrateMode", "Fixed"),
                            "bitrate": s.get("Bitrate", 0),
                            "active_bitrate": s.get("ActiveBitrate", 0),
                            "ttl": s.get("MultiCastTtl", 5),
                            "rtsp_port": s.get("RtspPort", 554),
                            "ts_port": s.get("TsPort", 4570),
                            "stream_location": f"rtsp://{ip}:{s.get('RtspPort', 554)}/live.sdp",
                        }
            
            # Receiver status
            rx_data = self._get(session, ip, "/Device/StreamReceive")
            if isinstance(rx_data, dict):
                rx_streams = rx_data.get("Device", {}).get("StreamReceive", {}).get("Streams", [])
                if rx_streams and isinstance(rx_streams, list) and len(rx_streams) > 0:
                    s = rx_streams[0]
                    if isinstance(s, dict):
                        rx_status = {
                            "status": s.get("Status", "Stopped"),
                            "started": s.get("Start", False),
                            "source": s.get("StreamLocation", ""),
                            "rtsp_port": s.get("RtspPort", 554),
                        }
            
            return {
                "transmitter": tx_status,
                "receiver": rx_status,
            }
        except Exception as e:
            logger.warning(f"[CrestronNVX] get_stream_status failed: {e}")
            return {"transmitter": {}, "receiver": {}}
        finally:
            if session:
                session.close()

    # ========== INPUT/OUTPUT STATUS ==========
    
    def get_input_output_status(self, ip, port=443):
        """Get input and output status"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/AudioVideoInputOutput")
            
            if not isinstance(data, dict):
                return {"inputs": [], "outputs": []}
                
            avio = data.get("Device", {}).get("AudioVideoInputOutput", {})
            
            inputs = []
            for inp in avio.get("Inputs", []):
                if not isinstance(inp, dict):
                    continue
                ports = inp.get("Ports", [])
                input_data = {
                    "name": inp.get("Name", "Unknown"),
                    "endpoint_id": inp.get("EndpointId", ""),
                    "video_type": inp.get("VideoPortTypeSelect", "Hdmi"),
                    "ports": []
                }
                for port in ports:
                    if not isinstance(port, dict):
                        continue
                    input_data["ports"].append({
                        "type": port.get("PortType", ""),
                        "sync_detected": port.get("IsSyncDetected", False),
                        "source_detected": port.get("IsSourceDetected", False),
                        "resolution": f"{port.get('HorizontalResolution', 0)}x{port.get('VerticalResolution', 0)}",
                        "fps": port.get("FramesPerSecond", 0),
                        "edid": port.get("Edid", {}).get("CurrentEdid", ""),
                        "hdcp_state": port.get("Hdmi", {}).get("HdcpState", ""),
                    })
                inputs.append(input_data)
            
            outputs = []
            for out in avio.get("Outputs", []):
                if not isinstance(out, dict):
                    continue
                ports = out.get("Ports", [])
                output_data = {
                    "name": out.get("Name", "Unknown"),
                    "endpoint_id": out.get("EndpointId", ""),
                    "video_type": out.get("VideoPortTypeSelect", "Hdmi"),
                    "ports": []
                }
                for port in ports:
                    if not isinstance(port, dict):
                        continue
                    output_data["ports"].append({
                        "type": port.get("PortType", ""),
                        "sink_connected": port.get("IsSinkConnected", False),
                        "resolution": f"{port.get('HorizontalResolution', 0)}x{port.get('VerticalResolution', 0)}",
                        "volume": port.get("Audio", {}).get("Volume", 0),
                        "mute": port.get("Audio", {}).get("Mute", False),
                        "hdcp_mode": port.get("Hdmi", {}).get("HdcpTransmitterMode", "Auto"),
                        "hdcp_state": port.get("Hdmi", {}).get("HdcpState", ""),
                    })
                outputs.append(output_data)
            
            return {
                "inputs": inputs,
                "outputs": outputs,
            }
        except Exception as e:
            logger.warning(f"[CrestronNVX] get_input_output_status failed: {e}")
            return {"inputs": [], "outputs": []}
        finally:
            if session:
                session.close()

    # ========== DM NAX (AES67) AUDIO ==========
    
    def get_nax_rx_status(self, ip, port=443):
        """Get DM NAX Receiver status"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/NaxAudio/NaxRx")
            
            if not isinstance(data, dict):
                return {}
                
            nax_rx = data.get("Device", {}).get("NaxAudio", {}).get("NaxRx", {})
            
            rx_streams = nax_rx.get("NaxRxStreams", {})
            rx_data = {}
            for stream_name, stream in rx_streams.items():
                if isinstance(stream, dict):
                    rx_data = {
                        "session_name": stream.get("SessionNameStatus", ""),
                        "multicast_address": stream.get("NetworkAddressStatus", "0.0.0.0"),
                        "port": stream.get("PortStatus", 5004),
                        "status": stream.get("StreamStatus", "Stopped"),
                        "encoding_format": stream.get("EncodingFormat", "LPCM"),
                        "sample_rate": stream.get("EncodingSampleRate", 48000),
                        "bitrate": stream.get("BitRate", 3072),
                        "channels": stream.get("Channels", 2),
                        "started": stream.get("StartRequested", False),
                    }
                    break
            
            return rx_data
        except Exception as e:
            logger.warning(f"[CrestronNVX] get_nax_rx_status failed: {e}")
            return {}
        finally:
            if session:
                session.close()

    # ========== EDID LIST ==========
    
    def get_edid_list(self, ip, port=443):
        """Get available EDIDs"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/EdidMgmnt")
            
            if not isinstance(data, dict):
                return {"system_edids": [], "copy_edids": []}
                
            edid_mgmt = data.get("Device", {}).get("EdidMgmnt", {})
            
            system_edids = []
            for key, edid in edid_mgmt.get("SystemEdidList", {}).items():
                if isinstance(edid, dict):
                    system_edids.append(edid.get("Name", key))
                else:
                    system_edids.append(str(key))
            
            copy_edids = []
            for key, edid in edid_mgmt.get("CopyEdidList", {}).items():
                if isinstance(edid, dict):
                    copy_edids.append(edid.get("Name", key))
                else:
                    copy_edids.append(str(key))
            
            return {
                "system_edids": system_edids,
                "copy_edids": copy_edids,
            }
        except Exception as e:
            logger.warning(f"[CrestronNVX] get_edid_list failed: {e}")
            return {"system_edids": [], "copy_edids": []}
        finally:
            if session:
                session.close()

    # ========== PREVIEW SETTINGS ==========
    
    def get_preview_settings(self, ip, port=443):
        """Get preview settings"""
        session = None
        try:
            session = self._login(ip)
            data = self._get(session, ip, "/Device/Preview")
            
            if not isinstance(data, dict):
                return {"enabled": False, "base_filename": "preview", "images": [], "local_path": "/preview"}
                
            preview = data.get("Device", {}).get("Preview", {})
            
            return {
                "enabled": preview.get("IsPreviewOutputEnabled", False),
                "base_filename": preview.get("BaseFileName", "preview"),
                "images": list(preview.get("ImageList", {}).keys()),
                "local_path": preview.get("LocalPreview", {}).get("RelativePath", "/preview"),
            }
        except Exception as e:
            logger.warning(f"[CrestronNVX] get_preview_settings failed: {e}")
            return {"enabled": False, "base_filename": "preview", "images": [], "local_path": "/preview"}
        finally:
            if session:
                session.close()

    # ========== NETWORK CONFIGURATION ==========
    
    def enable_dhcp(self, ip, port=443):
        """Enable DHCP on primary LAN"""
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "Ethernet": {
                        "Adapters": [
                            {
                                "Name": "FEC1",
                                "IPv4": {"IsDhcpEnabled": True}
                            }
                        ]
                    }
                }
            }
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                session.close()

    def set_static_ip(self, ip, ip_address, subnet_mask, gateway, dns1="8.8.8.8", dns2="8.8.4.4", port=443):
        """Set static IP configuration"""
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "Ethernet": {
                        "Adapters": [
                            {
                                "Name": "FEC1",
                                "IPv4": {
                                    "IsDhcpEnabled": False,
                                    "StaticAddresses": [{"Address": ip_address, "SubnetMask": subnet_mask}],
                                    "StaticDefaultGateway": gateway,
                                    "StaticDns": [dns1, dns2],
                                }
                            }
                        ]
                    }
                }
            }
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                session.close()

    def set_hostname(self, ip, hostname, port=443):
        """Set device hostname"""
        try:
            if not re.match(r'^[A-Z0-9]([A-Z0-9-]*[A-Z0-9])?$', hostname.upper()):
                raise Exception("Invalid hostname format")
            
            hostname_upper = hostname.upper()
            
            session = None
            try:
                session = self._login(ip)
                payload = {"Device": {"Ethernet": {"HostName": hostname_upper}}}
                self._post(session, ip, "/Device/Ethernet", payload)
                time.sleep(1)
                return {"success": True, "message": f"Hostname set to '{hostname_upper}'"}
            finally:
                if session:
                    session.close()
        except Exception as e:
            logger.error(f"[CrestronNVX] set_hostname failed: {e}")
            raise

    def set_domain(self, ip, domain, port=443):
        """Set device domain name (requires DHCP disabled)"""
        try:
            session = None
            try:
                session = self._login(ip)
                payload = {"Device": {"Ethernet": {"DomainName": domain}}}
                self._post(session, ip, "/Device/Ethernet", payload)
                return {"success": True, "message": f"Domain set to '{domain}'"}
            finally:
                if session:
                    session.close()
        except Exception as e:
            logger.error(f"[CrestronNVX] set_domain failed: {e}")
            raise

    def set_dns_servers(self, ip, primary, secondary="", port=443):
        """Set DNS servers (when using static IP)"""
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "Ethernet": {
                        "Adapters": [{
                            "Name": "FEC1",
                            "IPv4": {"StaticDns": [primary, secondary]}
                        }]
                    }
                }
            }
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                session.close()

    def set_icmp_ping(self, ip, enabled, port=443):
        """Enable/disable ICMP ping responses"""
        session = None
        try:
            session = self._login(ip)
            payload = {"Device": {"Ethernet": {"IsIcmpPingEnabled": enabled}}}
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                session.close()

    def set_ssh(self, ip, enabled, port=443):
        """Enable/disable SSH access"""
        session = None
        try:
            session = self._login(ip)
            payload = {"Device": {"Ethernet": {"IsSshEnabled": enabled}}}
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                session.close()

    def set_igmp_version(self, ip, version, port=443):
        """Set IGMP version (v2 or v3)"""
        session = None
        try:
            session = self._login(ip)
            payload = {"Device": {"Ethernet": {"IgmpVersion": version}}}
            return self._post(session, ip, "/Device/Ethernet", payload)
        finally:
            if session:
                session.close()

    def set_ipv6(self, ip, enabled, port=443):
        """Enable/disable IPv6"""
        session = None
        try:
            session = self._login(ip)
            address_schema = "IPv4AndIPv6" if enabled else "IPv4"
            payload = {"Device": {"NetworkAdapters": {"AddressSchema": address_schema}}}
            return self._post(session, ip, "/Device/NetworkAdapters", payload)
        finally:
            if session:
                session.close()

    # ========== DEVICE MODE ==========
    
    def set_device_mode(self, ip, mode, port=443):
        """Set device mode: 'Transmitter' or 'Receiver'"""
        try:
            session = None
            try:
                session = self._login(ip)
                payload = {"Device": {"DeviceSpecific": {"DeviceMode": mode}}}
                result = self._post(session, ip, "/Device/DeviceSpecific", payload)
                return {"success": True, "message": f"Device mode set to {mode}", "result": result}
            finally:
                if session:
                    session.close()
        except Exception as e:
            logger.error(f"[CrestronNVX] set_device_mode failed: {e}")
            raise

    # ========== TEST PATTERN ==========
    
    def set_test_pattern(self, ip, pattern, port=443):
        """Set test pattern on output"""
        patterns = {
            "off": "Off",
            "smpte": "SMPTE ColorBars",
            "black": "Black",
            "white": "White",
            "vertical": "Vertical Lines",
            "grid": "Grid",
            "color_bars": "Color Bars",
            "gray": "Gray Gradient",
            "rgb": "RGB Gradient"
        }
        pattern_name = patterns.get(pattern.lower(), pattern)
        
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "TestPatternConfig": {
                        "Outputs": {
                            "OUTPUT 1": {"CurrentTestPattern": pattern_name}
                        }
                    }
                }
            }
            return self._post(session, ip, "/Device/TestPatternConfig", payload)
        finally:
            if session:
                session.close()

    # ========== STREAM CONTROL ==========
    
    def start_stream(self, ip, port=443):
        """Start stream transmission"""
        session = None
        try:
            session = self._login(ip)
            payload = {"Device": {"StreamTransmit": {"Streams": [{"Start": True}]}}}
            return self._post(session, ip, "/Device/StreamTransmit", payload)
        finally:
            if session:
                session.close()

    def stop_stream(self, ip, port=443):
        """Stop stream transmission"""
        session = None
        try:
            session = self._login(ip)
            payload = {"Device": {"StreamTransmit": {"Streams": [{"Start": False}]}}}
            return self._post(session, ip, "/Device/StreamTransmit", payload)
        finally:
            if session:
                session.close()

    def set_multicast_address(self, ip, address, port=443):
        """Set multicast address for stream"""
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "StreamTransmit": {
                        "Streams": [{"MulticastAddress": address}]
                    }
                }
            }
            return self._post(session, ip, "/Device/StreamTransmit", payload)
        finally:
            if session:
                session.close()

    def set_bitrate(self, ip, bitrate, mode="Fixed", port=443):
        """Set stream bitrate"""
        session = None
        try:
            session = self._login(ip)
            payload = {
                "Device": {
                    "StreamTransmit": {
                        "Streams": [{
                            "BitrateMode": mode,
                            "Bitrate": bitrate
                        }]
                    }
                }
            }
            return self._post(session, ip, "/Device/StreamTransmit", payload)
        finally:
            if session:
                session.close()

    def set_ttl(self, ip, ttl, port=443):
        """Set multicast TTL"""
        session = None
        try:
            session = self._login(ip)
            payload = {"Device": {"StreamTransmit": {"Streams": [{"MultiCastTtl": ttl}]}}}
            return self._post(session, ip, "/Device/StreamTransmit", payload)
        finally:
            if session:
                session.close()

    # ========== REBOOT ==========
    
    def _check_ping(self, ip):
        """Check if device responds to ping"""
        try:
            param = "-n" if sys.platform.startswith("win") else "-c"
            response = subprocess.run(
                ["ping", param, "1", "-w", "2000", ip],
                capture_output=True,
                timeout=3,
            )
            return response.returncode == 0
        except:
            return False


    # ========== ADD THESE TWO METHODS HERE ==========
    
    def check_web_interface(self, ip):
        """Check if web interface is accessible"""
        try:
            response = requests.get(
                f"https://{ip}/userlogin.html",
                verify=False,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    def wait_for_reboot(self, ip, max_wait_seconds=180):
        """Wait for NVX device to reboot using ping detection"""
        print(f"\n[Reboot] Phase 1: Waiting for {ip} to go offline...")
        
        went_offline = False
        
        for i in range(60):
            if not self._check_ping(ip):
                print(f"[Reboot] Device went offline after {i} seconds")
                went_offline = True
                break
            time.sleep(1)
        
        if not went_offline:
            print("[Reboot] Device never went offline.")
            return False
        
        print(f"\n[Reboot] Phase 2: Waiting for {ip} to come back online...")
        
        for i in range(180):
            if self._check_ping(ip):
                print(f"[Reboot] Device responding after {i * 2} seconds")
                break
            time.sleep(2)
        else:
            print("[Reboot] Device never returned to network.")
            return False
        
        print(f"\n[Reboot] Phase 3: Waiting for Web Interface at {ip}...")
        
        for i in range(max_wait_seconds):
            if self.check_web_interface(ip):
                print(f"[Reboot] Web UI ready after {i * 2} seconds")
                return True
            time.sleep(2)
        
        print("[Reboot] Web interface never became available.")
        return False

    # ========== END OF ADDED METHODS ==========

    def reboot_via_ssh(self, ip):
        """Reboot via SSH - send command only, no waiting"""
        if not PARAMIKO_AVAILABLE:
            return {"success": False, "message": "Paramiko not installed"}
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=self.username, password=self.password, timeout=10)
            ssh.exec_command("reboot")
            ssh.close()
            logger.info(f"[CrestronNVX] Reboot command sent to {ip}")
            return {"success": True, "message": "Reboot command sent successfully"}
        except Exception as e:
            logger.error(f"[CrestronNVX] SSH reboot failed: {e}")
            return {"success": False, "message": str(e)}


    def reboot_device(self, ip, port=443):
        """Reboot the NVX device - send command and return immediately"""
        result = self.reboot_via_ssh(ip)
        return result    
    
    # ========== QUERY STATUS ==========
    
    def query_status(self, ip, port=443, display_id=None):
        """Quick status query - returns full device data for frontend"""
        try:
            logger.info(f"[CrestronNVX] query_status called for {ip}")
            
            # Get all data with error handling
            device_info = self.get_device_info(ip, port, display_id)
            eth_info = self.get_ethernet_info(ip, port)
            
            # Try to get stream status (may fail if device is in receiver mode)
            stream_status = {}
            try:
                stream_status = self.get_stream_status(ip, port)
            except Exception as e:
                logger.warning(f"Stream status failed: {e}")
            
            # Try to get IO status
            io_status = {}
            try:
                io_status = self.get_input_output_status(ip, port)
            except Exception as e:
                logger.warning(f"IO status failed: {e}")
            
            # Try to get NAX status
            nax_rx = {}
            try:
                nax_rx = self.get_nax_rx_status(ip, port)
            except Exception as e:
                logger.warning(f"NAX status failed: {e}")
            
            # Try to get EDID list
            edid_list = {}
            try:
                edid_list = self.get_edid_list(ip, port)
            except Exception as e:
                logger.warning(f"EDID list failed: {e}")
            
            # Try to get preview settings
            preview = {}
            try:
                preview = self.get_preview_settings(ip, port)
            except Exception as e:
                logger.warning(f"Preview settings failed: {e}")
            
            result = {
                "reachable": device_info.get("current_status") == "Online" if device_info else False,
                "power": "ON" if device_info.get("current_status") == "Online" else "OFF",
                "device_name": device_info.get("device_name", ""),
                "model": device_info.get("model", ""),
                "serial_number": device_info.get("serial_number", ""),
                "firmware": device_info.get("firmware", ""),
                "puf_version": device_info.get("puf_version", ""),
                "build_date": device_info.get("build_date", ""),
                "device_mode": device_info.get("device_mode", "Receiver"),
                "audio_mode": device_info.get("audio_mode", "Insert"),
                "current_ip": eth_info.get("current_ip", ip) if eth_info else ip,
                "mac_address": device_info.get("mac_address", ""),
                "hostname": eth_info.get("hostname", "") if eth_info else "",
                "domain": eth_info.get("domain", "") if eth_info else "",
                "subnet_mask": eth_info.get("subnet_mask", "") if eth_info else "",
                "gateway": eth_info.get("gateway", "") if eth_info else "",
                "dhcp_enabled": eth_info.get("dhcp_enabled", True) if eth_info else True,
                "dns_servers": eth_info.get("dns_servers", []) if eth_info else [],
                "ssh_enabled": eth_info.get("ssh_enabled", False) if eth_info else False,
                "icmp_enabled": eth_info.get("icmp_enabled", True) if eth_info else True,
                "igmp_version": eth_info.get("igmp_version", "v2") if eth_info else "v2",
                "ipv6_enabled": eth_info.get("ipv6_enabled", False) if eth_info else False,
                "stream": stream_status if stream_status else {"transmitter": {}, "receiver": {}},
                "inputs": io_status.get("inputs", []) if io_status else [],
                "outputs": io_status.get("outputs", []) if io_status else [],
                "nax_audio": {"receiver": nax_rx if nax_rx else {}},
                "edid_list": edid_list if edid_list else {"system_edids": [], "copy_edids": []},
                "preview": preview if preview else {"enabled": False, "base_filename": "preview", "images": [], "local_path": "/preview"},
                "device_info": {
                    "Model": device_info.get("model", ""),
                    "Name": device_info.get("device_name", ""),
                    "SerialNumber": device_info.get("serial_number", ""),
                    "MacAddress": device_info.get("mac_address", ""),
                    "DeviceVersion": device_info.get("firmware", ""),
                    "PufVersion": device_info.get("puf_version", ""),
                    "BuildDate": device_info.get("build_date", ""),
                    "Manufacturer": "Crestron",
                } if device_info else {},
                "ethernet_info": eth_info if eth_info else {"current_ip": ip},
            }
            
            return result
            
        except Exception as e:
            logger.error(f"[CrestronNVX] query_status failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "reachable": False,
                "power": "OFF",
                "error": str(e),
                "device_info": {},
                "ethernet_info": {"current_ip": ip},
                "stream": {"transmitter": {}, "receiver": {}},
                "inputs": [],
                "outputs": [],
                "nax_audio": {},
                "edid_list": {"system_edids": [], "copy_edids": []},
                "preview": {"enabled": False, "base_filename": "preview", "images": [], "local_path": "/preview"},
                "device_name": "",
                "model": "",
                "serial_number": "",
                "firmware": "",
                "current_ip": ip,
                "mac_address": "",
                "hostname": "",
                "domain": "",
                "subnet_mask": "",
                "gateway": "",
                "dhcp_enabled": True,
                "dns_servers": [],
                "ssh_enabled": False,
                "icmp_enabled": True,
                "igmp_version": "v2",
                "ipv6_enabled": False,
                "device_mode": "Receiver",
                "audio_mode": "Insert",
            }

    # ========== SEND COMMAND ==========
    
    def send_command(self, ip, port, display_id, command, params=None):
        """Handle all NVX commands."""
        if not self.username or not self.password:
            return False, "Missing credentials"

        logger.info(f"[CrestronNVX] Command: {command} to {ip}, params: {params}")
        cmd_params = params or {}

        try:
            # ========== Status Commands ==========
            if command == "get_status":
                result = self.query_status(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_device_info":
                result = self.get_device_info(ip, port, display_id)
                return True, json.dumps(result)

            elif command == "get_ethernet_info":
                result = self.get_ethernet_info(ip, port)
                return True, json.dumps(result)

            elif command == "get_stream_status":
                result = self.get_stream_status(ip, port)
                return True, json.dumps(result)

            elif command == "get_input_output_status":
                result = self.get_input_output_status(ip, port)
                return True, json.dumps(result)

            elif command == "get_nax_rx_status":
                result = self.get_nax_rx_status(ip, port)
                return True, json.dumps(result)

            elif command == "get_edid_list":
                result = self.get_edid_list(ip, port)
                return True, json.dumps(result)

            elif command == "get_preview_settings":
                result = self.get_preview_settings(ip, port)
                return True, json.dumps(result)

            # ========== Network Commands ==========
            elif command == "set_hostname":
                hostname = cmd_params.get('hostname', '')
                if not hostname:
                    return False, "Missing hostname"
                result = self.set_hostname(ip, hostname, port)
                return True, json.dumps(result)

            elif command == "set_domain":
                domain = cmd_params.get('domain', '')
                if not domain:
                    return False, "Missing domain"
                result = self.set_domain(ip, domain, port)
                return True, json.dumps(result)

            elif command == "enable_dhcp":
                result = self.enable_dhcp(ip, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_static_ip":
                ip_address = cmd_params.get('ip_address', cmd_params.get('address', ''))
                subnet_mask = cmd_params.get('subnet_mask', cmd_params.get('mask', '255.255.255.0'))
                gateway = cmd_params.get('gateway', '')
                dns1 = cmd_params.get('dns1', '8.8.8.8')
                dns2 = cmd_params.get('dns2', '8.8.4.4')
                result = self.set_static_ip(ip, ip_address, subnet_mask, gateway, dns1, dns2, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_dns_servers":
                primary = cmd_params.get('primary', '')
                secondary = cmd_params.get('secondary', '')
                if not primary:
                    return False, "Missing primary DNS"
                result = self.set_dns_servers(ip, primary, secondary, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_icmp_ping":
                enabled = cmd_params.get('enabled', True)
                result = self.set_icmp_ping(ip, enabled, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_ssh":
                enabled = cmd_params.get('enabled', False)
                result = self.set_ssh(ip, enabled, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_igmp_version":
                version = cmd_params.get('version', 'v3')
                if version not in ['v2', 'v3']:
                    return False, "IGMP version must be v2 or v3"
                result = self.set_igmp_version(ip, version, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_ipv6":
                enabled = cmd_params.get('enabled', False)
                result = self.set_ipv6(ip, enabled, port)
                return True, json.dumps({"success": True, "result": result})

            # ========== Device Mode Commands ==========
            elif command == "set_device_mode":
                mode = cmd_params.get('mode', 'Receiver')
                if mode not in ['Transmitter', 'Receiver']:
                    return False, "Mode must be Transmitter or Receiver"
                result = self.set_device_mode(ip, mode, port)
                return True, json.dumps(result)

            # ========== Stream Commands ==========
            elif command == "start_stream":
                result = self.start_stream(ip, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "stop_stream":
                result = self.stop_stream(ip, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_multicast_address":
                address = cmd_params.get('address', '')
                if not address:
                    return False, "Missing multicast address"
                result = self.set_multicast_address(ip, address, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_bitrate":
                bitrate = cmd_params.get('bitrate', 750)
                mode = cmd_params.get('mode', 'Fixed')
                result = self.set_bitrate(ip, bitrate, mode, port)
                return True, json.dumps({"success": True, "result": result})

            elif command == "set_ttl":
                ttl = cmd_params.get('ttl', 5)
                result = self.set_ttl(ip, ttl, port)
                return True, json.dumps({"success": True, "result": result})

            # ========== Test Pattern Commands ==========
            elif command == "set_test_pattern":
                pattern = cmd_params.get('pattern', 'off')
                result = self.set_test_pattern(ip, pattern, port)
                return True, json.dumps({"success": True, "result": result})

            # ========== Reboot Commands ==========
            elif command == "reboot":
                result = self.reboot_device(ip, port)
                return result.get("success", False), result.get("message", "")

            else:
                return False, f"Unknown command: {command}"

        except Exception as e:
            logger.error(f"[CrestronNVX] Command failed: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)


def get_plugin(config=None):
    return CrestronNVXPlugin(config)