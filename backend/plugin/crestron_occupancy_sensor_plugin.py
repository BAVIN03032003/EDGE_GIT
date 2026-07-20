"""
Manual Platform Plugin: CrestronOccupancySensorPlugin (RMM Cloud Side)
Based on the working standalone Crestron CEN-ODT-C-POE plugin
"""

import re
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .base import ManualPlatformPlugin
from .crestron_firmware_mixin import CrestronFirmwareMixin


class CrestronOccupancySensorPlugin(CrestronFirmwareMixin, ManualPlatformPlugin):
    """Crestron CEN-ODT-C-POE occupancy sensor via authenticated Crestron web API."""

    name = "crestron_occupancy_sensor"
    display_name = "Crestron Occupancy Sensor"
    description = "Crestron CEN-ODT-C-POE (IP + username + password)"
    supports_display_id = False
    supports_port = False
    default_port = 443
    SUPPORTED_MODELS = ["CEN-ODT-C-POE"]
    SUPPORTED_FIRMWARE_MODELS = {
        "CEN-ODT-C-POE": {"extensions": [".puf"]},
    }

    COMMANDS = {
        # Occupancy
        "set_timeout": {"params": ["seconds"], "description": "Set timeout in seconds (5-1800)"},
        "set_led_flash": {"params": ["enabled"], "description": "Enable/disable LED flash"},
        "set_short_timeout": {"params": ["enabled"], "description": "Enable/disable short timeout"},
        "set_occupancy_logic": {"params": ["logic"], "description": "Set occupancy logic (AND/OR)"},
        "set_vacancy_logic": {"params": ["logic"], "description": "Set vacancy logic (AND/OR)"},
        "set_sensor_logic": {"params": ["occupancy_or", "vacancy_or"], "description": "Set sensor logic (OR=true, AND=false)"},
        # Ultrasonic
        "set_ultrasonic_sensors": {"params": ["sensor1", "sensor2"], "description": "Enable/disable ultrasonic sensors"},
        "set_ultrasonic_sensitivity": {"params": ["occupied", "vacancy"], "description": "Set ultrasonic sensitivity"},
        "set_ultrasonic_sensor1": {"params": ["enabled"], "description": "Enable/disable ultrasonic sensor 1"},
        "set_ultrasonic_sensor2": {"params": ["enabled"], "description": "Enable/disable ultrasonic sensor 2"},
        "set_ultrasonic_occupied_sensitivity": {"params": ["level"], "description": "Set ultrasonic occupied sensitivity"},
        "set_ultrasonic_vacancy_sensitivity": {"params": ["level"], "description": "Set ultrasonic vacancy sensitivity"},
        # PIR
        "set_pir_sensor": {"params": ["enabled"], "description": "Enable/disable PIR sensor"},
        "set_pir_sensitivity": {"params": ["occupied", "vacancy"], "description": "Set PIR sensitivity"},
        "set_pir_occupied_sensitivity": {"params": ["level"], "description": "Set PIR occupied sensitivity"},
        "set_pir_vacancy_sensitivity": {"params": ["level"], "description": "Set PIR vacancy sensitivity"},
        # Photo sensor
        "set_min_light_change": {"params": ["value"], "description": "Set minimum light change (655-65535)"},
        "set_dark_to_bright_threshold": {"params": ["value"], "description": "Set dark to bright threshold (0-65535)"},
        "set_bright_to_dark_threshold": {"params": ["value"], "description": "Set bright to dark threshold (0-65535)"},
        "set_photo_thresholds": {"params": ["dark_to_bright", "bright_to_dark"], "description": "Set both photo thresholds"},
        # Ethernet
        "set_hostname": {"params": ["hostname"], "description": "Set device hostname"},
        "set_domain": {"params": ["domain"], "description": "Set domain name"},
        "set_ping": {"params": ["enabled"], "description": "Enable/disable ICMP ping"},
        "set_ssh": {"params": ["enabled"], "description": "Enable/disable SSH"},
        "set_autoneg": {"params": ["enabled"], "description": "Enable/disable auto-negotiation"},
        "set_igmp": {"params": ["version"], "description": "Set IGMP version (v2/v3)"},
        "set_dhcp": {"params": ["enabled"], "description": "Enable/disable DHCP"},
        "set_static_ip": {"params": ["address", "mask"], "description": "Set static IP address and subnet mask"},
        "set_static_gateway": {"params": ["gateway"], "description": "Set static default gateway"},
        "set_static_dns": {"params": ["dns_list"], "description": "Set static DNS servers"},
        "set_adapter_enabled": {"params": ["enabled"], "description": "Enable/disable network adapter"},
    }
    
    QUERY_COMMANDS = {}

    # ─────────────────────────── helpers ────────────────────────────

    def _normalize_mac(self, raw_mac):
        if not raw_mac:
            return None
        raw_value = str(raw_mac).strip()
        if raw_value.startswith("<") and raw_value.endswith(">"):
            return None
        cleaned = re.sub(r"[^0-9A-Fa-f]", "", str(raw_mac))
        if len(cleaned) < 12:
            return str(raw_mac).replace(".", ":")
        cleaned = cleaned[:12]
        return ":".join(cleaned[i:i+2] for i in range(0, 12, 2)).lower()

    def _clean_value(self, value):
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        if value.startswith("<") and value.endswith(">"):
            return None
        return value

    def _crestron_login(self, ip, username, password):
        """Authenticate with Crestron device - returns session with XSRF token"""
        base_url = f"https://{ip}"
        login_url = f"{base_url}/userlogin.html"
        session = requests.Session()
        session.verify = False

        # Step 1: GET login page to get TRACKID cookie
        session.get(login_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        trackid = session.cookies.get("TRACKID")
        if not trackid:
            raise Exception("TRACKID not found on login page")

        # Step 2: POST credentials
        login_headers = {
            "Cookie": f"TRACKID={trackid}",
            "Origin": base_url,
            "Referer": login_url,
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        }
        payload = f"login={username}&&passwd={password}"
        r2 = session.post(login_url, headers=login_headers, data=payload, timeout=10)
        if r2.status_code != 200:
            raise Exception(f"Login failed (HTTP {r2.status_code})")

        # Get XSRF token from response headers
        xsrf = r2.headers.get("CREST-XSRF-TOKEN")
        if xsrf:
            session.headers.update({
                "CREST-XSRF-TOKEN": xsrf,
                "X-CREST-XSRF-TOKEN": xsrf,
            })

        return session

    def _make_request(self, session, ip, method, endpoint, data=None):
        """Make authenticated API request to the device"""
        url = f"https://{ip}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            if method == "GET":
                response = session.get(url, headers=headers, timeout=10, verify=False)
            elif method == "POST":
                response = session.post(url, headers=headers, json=data, timeout=10, verify=False)
            else:
                raise Exception(f"Unsupported HTTP method: {method}")

            if response.status_code not in (200, 204):
                return {"error": f"HTTP {response.status_code}", "message": response.text[:300]}

            if not response.content or not response.content.strip():
                return {}
            try:
                return response.json()
            except ValueError:
                return {"_raw": response.text.strip()}

        except requests.exceptions.ConnectionError:
            return {"error": "Connection refused — check device IP and network"}
        except requests.exceptions.Timeout:
            return {"error": "Request timed out"}
        except Exception as e:
            return {"error": str(e)}

    def _get_session_and_make_request(self, ip, method, endpoint, data=None):
        """Get authenticated session and make request"""
        username = self.config.get("username")
        password = self.config.get("password")
        if not username or not password:
            raise Exception("Missing credentials: username and password are required.")
        
        session = None
        try:
            session = self._crestron_login(ip, username, password)
            return self._make_request(session, ip, method, endpoint, data)
        finally:
            if session:
                session.close()

    # ─────────────────────── API wrapper methods ───────────────────────

    def get_device_info_api(self, ip):
        """Get device information from API"""
        return self._get_session_and_make_request(ip, "GET", "/Device/DeviceInfo/")

    def get_occupancy_sensor_api(self, ip):
        """Get occupancy sensor status from API"""
        return self._get_session_and_make_request(ip, "GET", "/Device/OccupancySensor/")

    def update_occupancy_sensor_api(self, ip, updates):
        """Update occupancy sensor settings via API"""
        return self._get_session_and_make_request(ip, "POST", "/Device/OccupancySensor/", updates)

    def get_photo_sensor_api(self, ip):
        """Get photo sensor status from API"""
        return self._get_session_and_make_request(ip, "GET", "/Device/PhotoSensor/")

    def update_photo_sensor_api(self, ip, updates):
        """Update photo sensor settings via API"""
        return self._get_session_and_make_request(ip, "POST", "/Device/PhotoSensor/", updates)

    def get_ethernet_config_api(self, ip):
        """Get ethernet configuration from API"""
        return self._get_session_and_make_request(ip, "GET", "/Device/Ethernet/")

    def update_ethernet_api(self, ip, payload):
        """Update ethernet configuration via API"""
        return self._get_session_and_make_request(ip, "POST", "/Device/Ethernet/", {"Device": {"Ethernet": payload}})

    # ─────────── OCCUPANCY CONTROL METHODS ───────────

    def set_timeout(self, ip, seconds: int) -> tuple:
        if not (5 <= seconds <= 1800):
            return False, "Timeout must be between 5 and 1800 seconds"
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"TimeoutSeconds": seconds}}
            })
            return True, f"Timeout set to {seconds} seconds"
        except Exception as e:
            return False, str(e)

    def set_led_flash(self, ip, enabled: bool) -> tuple:
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"IsLedFlashEnabled": enabled}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"LED flash {status}"
        except Exception as e:
            return False, str(e)

    def set_short_timeout(self, ip, enabled: bool) -> tuple:
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"IsShortTimeoutEnabled": enabled}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"Short timeout {status}"
        except Exception as e:
            return False, str(e)

    def set_occupancy_logic(self, ip, logic: str) -> tuple:
        """Set occupancy logic (AND/OR)"""
        use_or = logic.upper() == "OR"
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"IsSingleSensorDeterminingOccupancy": use_or}}
            })
            return True, f"Occupancy logic set to {logic.upper()}"
        except Exception as e:
            return False, str(e)

    def set_vacancy_logic(self, ip, logic: str) -> tuple:
        """Set vacancy logic (AND/OR)"""
        use_or = logic.upper() == "OR"
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"IsSingleSensorDeterminingVacancy": use_or}}
            })
            return True, f"Vacancy logic set to {logic.upper()}"
        except Exception as e:
            return False, str(e)

    def set_sensor_logic(self, ip, occupancy_or: bool = None, vacancy_or: bool = None) -> tuple:
        try:
            payload = {}
            changes = []
            if occupancy_or is not None:
                payload["IsSingleSensorDeterminingOccupancy"] = occupancy_or
                changes.append(f"occupancy={'OR' if occupancy_or else 'AND'}")
            if vacancy_or is not None:
                payload["IsSingleSensorDeterminingVacancy"] = vacancy_or
                changes.append(f"vacancy={'OR' if vacancy_or else 'AND'}")
            
            if not payload:
                return False, "No changes specified"
            
            self.update_occupancy_sensor_api(ip, {"Device": {"OccupancySensor": payload}})
            return True, f"Sensor logic updated: {', '.join(changes)}"
        except Exception as e:
            return False, str(e)

    # ─────────── ULTRASONIC METHODS ───────────

    def set_ultrasonic_sensors(self, ip, sensor1: bool = None, sensor2: bool = None) -> tuple:
        try:
            payload = {}
            changes = []
            if sensor1 is not None:
                payload["IsSensor1Enabled"] = sensor1
                changes.append(f"sensor1={'enabled' if sensor1 else 'disabled'}")
            if sensor2 is not None:
                payload["IsSensor2Enabled"] = sensor2
                changes.append(f"sensor2={'enabled' if sensor2 else 'disabled'}")
            
            if not payload:
                return False, "No changes specified"
            
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": payload}}
            })
            return True, f"Ultrasonic sensors updated: {', '.join(changes)}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_sensitivity(self, ip, occupied: str = None, vacancy: str = None) -> tuple:
        valid_levels = ["Low", "Medium", "High", "LowX", "Low2X", "Low3X"]
        changes = []
        payload = {}
        
        if occupied:
            if occupied not in valid_levels:
                return False, f"Occupied sensitivity must be one of: {', '.join(valid_levels)}"
            payload["OccupiedSensitivity"] = occupied
            changes.append(f"occupied={occupied}")
        if vacancy:
            if vacancy not in valid_levels:
                return False, f"Vacancy sensitivity must be one of: {', '.join(valid_levels)}"
            payload["VacancySensitivity"] = vacancy
            changes.append(f"vacancy={vacancy}")
        
        if not payload:
            return False, "No changes specified"
        
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": payload}}
            })
            return True, f"Ultrasonic sensitivity updated: {', '.join(changes)}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_sensor1(self, ip, enabled: bool) -> tuple:
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": {"IsSensor1Enabled": enabled}}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"Ultrasonic sensor 1 {status}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_sensor2(self, ip, enabled: bool) -> tuple:
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": {"IsSensor2Enabled": enabled}}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"Ultrasonic sensor 2 {status}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_occupied_sensitivity(self, ip, level: str) -> tuple:
        valid = ["Low", "Medium", "High", "LowX", "Low2X", "Low3X"]
        if level not in valid:
            return False, f"Sensitivity must be one of: {', '.join(valid)}"
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": {"OccupiedSensitivity": level}}}
            })
            return True, f"Ultrasonic occupied sensitivity set to {level}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_vacancy_sensitivity(self, ip, level: str) -> tuple:
        valid = ["Low", "Medium", "High", "LowX", "Low2X", "Low3X"]
        if level not in valid:
            return False, f"Sensitivity must be one of: {', '.join(valid)}"
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": {"VacancySensitivity": level}}}
            })
            return True, f"Ultrasonic vacancy sensitivity set to {level}"
        except Exception as e:
            return False, str(e)

    # ─────────── PIR METHODS ───────────

    def set_pir_sensor(self, ip, enabled: bool) -> tuple:
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Pir": {"IsSensor1Enabled": enabled}}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"PIR sensor {status}"
        except Exception as e:
            return False, str(e)

    def set_pir_sensitivity(self, ip, occupied: str = None, vacancy: str = None) -> tuple:
        valid_levels = ["Low", "Medium", "High"]
        changes = []
        payload = {}
        
        if occupied:
            if occupied not in valid_levels:
                return False, f"Occupied sensitivity must be one of: {', '.join(valid_levels)}"
            payload["OccupiedSensitivity"] = occupied
            changes.append(f"occupied={occupied}")
        if vacancy:
            if vacancy not in valid_levels:
                return False, f"Vacancy sensitivity must be one of: {', '.join(valid_levels)}"
            payload["VacancySensitivity"] = vacancy
            changes.append(f"vacancy={vacancy}")
        
        if not payload:
            return False, "No changes specified"
        
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Pir": payload}}
            })
            return True, f"PIR sensitivity updated: {', '.join(changes)}"
        except Exception as e:
            return False, str(e)

    def set_pir_occupied_sensitivity(self, ip, level: str) -> tuple:
        valid = ["Low", "Medium", "High"]
        if level not in valid:
            return False, f"Sensitivity must be one of: {', '.join(valid)}"
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Pir": {"OccupiedSensitivity": level}}}
            })
            return True, f"PIR occupied sensitivity set to {level}"
        except Exception as e:
            return False, str(e)

    def set_pir_vacancy_sensitivity(self, ip, level: str) -> tuple:
        valid = ["Low", "Medium", "High"]
        if level not in valid:
            return False, f"Sensitivity must be one of: {', '.join(valid)}"
        try:
            self.update_occupancy_sensor_api(ip, {
                "Device": {"OccupancySensor": {"Pir": {"VacancySensitivity": level}}}
            })
            return True, f"PIR vacancy sensitivity set to {level}"
        except Exception as e:
            return False, str(e)

    # ─────────── PHOTO SENSOR METHODS ───────────

    def set_min_light_change(self, ip, value: int) -> tuple:
        if not (655 <= value <= 65535):
            return False, "MinLightChange must be between 655 and 65535"
        try:
            self.update_photo_sensor_api(ip, {
                "Device": {"PhotoSensor": {"LevelReading": {"MinLightChange": value}}}
            })
            return True, f"Min light change set to {value}"
        except Exception as e:
            return False, str(e)

    def set_dark_to_bright_threshold(self, ip, value: int) -> tuple:
        if not (0 <= value <= 65535):
            return False, "DarkToBrightThreshold must be between 0 and 65535"
        try:
            self.update_photo_sensor_api(ip, {
                "Device": {"PhotoSensor": {"ThresholdDetection": {"DarkToBrightThreshold": value}}}
            })
            return True, f"Dark to bright threshold set to {value}"
        except Exception as e:
            return False, str(e)

    def set_bright_to_dark_threshold(self, ip, value: int) -> tuple:
        if not (0 <= value <= 65535):
            return False, "BrightToDarkThreshold must be between 0 and 65535"
        try:
            self.update_photo_sensor_api(ip, {
                "Device": {"PhotoSensor": {"ThresholdDetection": {"BrightToDarkThreshold": value}}}
            })
            return True, f"Bright to dark threshold set to {value}"
        except Exception as e:
            return False, str(e)

    def set_photo_thresholds(self, ip, dark_to_bright: int = None, bright_to_dark: int = None) -> tuple:
        try:
            payload = {"Device": {"PhotoSensor": {"ThresholdDetection": {}}}}
            changes = []
            if dark_to_bright is not None:
                if not (0 <= dark_to_bright <= 65535):
                    return False, "DarkToBrightThreshold must be between 0 and 65535"
                payload["Device"]["PhotoSensor"]["ThresholdDetection"]["DarkToBrightThreshold"] = dark_to_bright
                changes.append(f"dark→bright={dark_to_bright}")
            if bright_to_dark is not None:
                if not (0 <= bright_to_dark <= 65535):
                    return False, "BrightToDarkThreshold must be between 0 and 65535"
                payload["Device"]["PhotoSensor"]["ThresholdDetection"]["BrightToDarkThreshold"] = bright_to_dark
                changes.append(f"bright→dark={bright_to_dark}")
            
            if not changes:
                return False, "No changes specified"
            
            self.update_photo_sensor_api(ip, payload)
            return True, f"Photo thresholds updated: {', '.join(changes)}"
        except Exception as e:
            return False, str(e)

    # ─────────── ETHERNET METHODS ───────────

    def set_hostname(self, ip, hostname: str) -> tuple:
        if not hostname:
            return False, "Hostname cannot be empty"
        try:
            self.update_ethernet_api(ip, {"HostName": hostname})
            return True, f"Hostname set to {hostname}"
        except Exception as e:
            return False, str(e)

    def set_domain(self, ip, domain: str) -> tuple:
        try:
            self.update_ethernet_api(ip, {"DomainName": domain})
            return True, f"Domain set to {domain}"
        except Exception as e:
            return False, str(e)

    def set_ping(self, ip, enabled: bool) -> tuple:
        try:
            self.update_ethernet_api(ip, {"IsIcmpPingEnabled": enabled})
            status = "enabled" if enabled else "disabled"
            return True, f"ICMP ping {status}"
        except Exception as e:
            return False, str(e)

    def set_ssh(self, ip, enabled: bool) -> tuple:
        try:
            self.update_ethernet_api(ip, {"IsSshEnabled": enabled})
            status = "enabled" if enabled else "disabled"
            return True, f"SSH {status}"
        except Exception as e:
            return False, str(e)

    def set_autoneg(self, ip, enabled: bool) -> tuple:
        try:
            self.update_ethernet_api(ip, {"AutoNegotiationEnabled": enabled})
            status = "enabled" if enabled else "disabled"
            return True, f"Auto-negotiation {status}"
        except Exception as e:
            return False, str(e)

    def set_igmp(self, ip, version: str) -> tuple:
        version = version.lower()
        if version not in ("v2", "v3"):
            return False, "IGMP version must be 'v2' or 'v3'"
        try:
            self.update_ethernet_api(ip, {"IgmpVersion": version})
            return True, f"IGMP version set to {version}"
        except Exception as e:
            return False, str(e)

    def set_dhcp(self, ip, enabled: bool, adapter_index: int = 0) -> tuple:
        try:
            adapters = [{} for _ in range(adapter_index + 1)]
            adapters[adapter_index] = {"IPv4": {"IsDhcpEnabled": enabled}}
            self.update_ethernet_api(ip, {"Adapters": adapters})
            status = "enabled" if enabled else "disabled"
            return True, f"DHCP {status}"
        except Exception as e:
            return False, str(e)

    def set_static_ip(self, ip, address: str, mask: str, adapter_index: int = 0) -> tuple:
        if not address or not mask:
            return False, "Both IP address and subnet mask are required"
        try:
            adapters = [{} for _ in range(adapter_index + 1)]
            adapters[adapter_index] = {
                "IPv4": {"StaticAddresses": [{"Address": address, "SubnetMask": mask}]}
            }
            self.update_ethernet_api(ip, {"Adapters": adapters})
            return True, f"Static IP set to {address}/{mask}"
        except Exception as e:
            return False, str(e)

    def set_static_gateway(self, ip, gateway: str, adapter_index: int = 0) -> tuple:
        if not gateway:
            return False, "Gateway address is required"
        try:
            adapters = [{} for _ in range(adapter_index + 1)]
            adapters[adapter_index] = {"IPv4": {"StaticDefaultGateway": gateway}}
            self.update_ethernet_api(ip, {"Adapters": adapters})
            return True, f"Static gateway set to {gateway}"
        except Exception as e:
            return False, str(e)

    def set_static_dns(self, ip, dns_list: list, adapter_index: int = 0) -> tuple:
        if not dns_list:
            return False, "DNS server list cannot be empty"
        if isinstance(dns_list, str):
            dns_list = [dns_list]
        try:
            adapters = [{} for _ in range(adapter_index + 1)]
            adapters[adapter_index] = {"IPv4": {"StaticDns": dns_list}}
            self.update_ethernet_api(ip, {"Adapters": adapters})
            return True, f"Static DNS set to {', '.join(dns_list)}"
        except Exception as e:
            return False, str(e)

    def set_adapter_enabled(self, ip, enabled: bool, adapter_index: int = 0) -> tuple:
        try:
            adapters = [{} for _ in range(adapter_index + 1)]
            adapters[adapter_index] = {"IsAdapterEnabled": enabled}
            self.update_ethernet_api(ip, {"Adapters": adapters})
            status = "enabled" if enabled else "disabled"
            return True, f"Adapter {status}"
        except Exception as e:
            return False, str(e)

    # ─────────────────── SEND COMMAND ───────────────────

    def send_command(self, ip, port, display_id, command, params=None):
        """
        Execute a command on the Crestron occupancy sensor.
        
        Args:
            ip: Device IP address
            port: Device port (ignored, uses 443)
            display_id: Display ID (ignored)
            command: Command name
            params: Dict of parameters for the command
        
        Returns:
            tuple: (success, message)
        """
        if params is None:
            params = {}

        # Shorthand command mappings
        shorthand_map = {
            "timeout": "set_timeout",
            "led": "set_led_flash",
            "led_flash": "set_led_flash",
            "short_timeout": "set_short_timeout",
            "occ_logic": "set_occupancy_logic",
            "vac_logic": "set_vacancy_logic",
            "sensor_logic": "set_sensor_logic",
            "us_sensors": "set_ultrasonic_sensors",
            "us_sensitivity": "set_ultrasonic_sensitivity",
            "us_sensor1": "set_ultrasonic_sensor1",
            "us_sensor2": "set_ultrasonic_sensor2",
            "us_occ_sens": "set_ultrasonic_occupied_sensitivity",
            "us_vac_sens": "set_ultrasonic_vacancy_sensitivity",
            "pir": "set_pir_sensor",
            "pir_sensitivity": "set_pir_sensitivity",
            "pir_occ_sens": "set_pir_occupied_sensitivity",
            "pir_vac_sens": "set_pir_vacancy_sensitivity",
            "min_light": "set_min_light_change",
            "dark2bright": "set_dark_to_bright_threshold",
            "bright2dark": "set_bright_to_dark_threshold",
            "photo_thresholds": "set_photo_thresholds",
            "hostname": "set_hostname",
            "domain": "set_domain",
            "ping": "set_ping",
            "ssh": "set_ssh",
            "autoneg": "set_autoneg",
            "igmp": "set_igmp",
            "dhcp": "set_dhcp",
            "staticip": "set_static_ip",
            "staticgw": "set_static_gateway",
            "staticdns": "set_static_dns",
            "adapter": "set_adapter_enabled",
        }

        # Handle frontend parameter name conversions
        cmd_lower = command.lower()
        
        if cmd_lower == "set_sensor_logic":
            if "occupancy_logic" in params:
                val = params.pop("occupancy_logic")
                params["occupancy_or"] = str(val).upper() == "OR"
            if "vacancy_logic" in params:
                val = params.pop("vacancy_logic")
                params["vacancy_or"] = str(val).upper() == "OR"
        
        if cmd_lower in ["set_static_dns", "set_dns"] and "primary" in params:
            dns_list = [params["primary"]]
            if params.get("secondary"):
                dns_list.append(params["secondary"])
            params = {"dns_list": dns_list}
            command = "set_static_dns"
        
        if cmd_lower in ["set_gateway"]:
            command = "set_static_gateway"
        
        if cmd_lower in ["set_dark_to_bright"]:
            command = "set_dark_to_bright_threshold"
        
        if cmd_lower in ["set_bright_to_dark"]:
            command = "set_bright_to_dark_threshold"
        
        # Normalize command name
        normalized_command = shorthand_map.get(cmd_lower, command)
        
        # Command routing
        command_map = {
            "set_timeout": lambda: self.set_timeout(ip, params.get("seconds", 120)),
            "set_led_flash": lambda: self.set_led_flash(ip, params.get("enabled", True)),
            "set_short_timeout": lambda: self.set_short_timeout(ip, params.get("enabled", True)),
            "set_occupancy_logic": lambda: self.set_occupancy_logic(ip, params.get("logic", "OR")),
            "set_vacancy_logic": lambda: self.set_vacancy_logic(ip, params.get("logic", "OR")),
            "set_sensor_logic": lambda: self.set_sensor_logic(
                ip,
                params.get("occupancy_or"),
                params.get("vacancy_or")
            ),
            "set_ultrasonic_sensors": lambda: self.set_ultrasonic_sensors(
                ip,
                params.get("sensor1"),
                params.get("sensor2")
            ),
            "set_ultrasonic_sensitivity": lambda: self.set_ultrasonic_sensitivity(
                ip,
                params.get("occupied"),
                params.get("vacancy")
            ),
            "set_ultrasonic_sensor1": lambda: self.set_ultrasonic_sensor1(ip, params.get("enabled", True)),
            "set_ultrasonic_sensor2": lambda: self.set_ultrasonic_sensor2(ip, params.get("enabled", True)),
            "set_ultrasonic_occupied_sensitivity": lambda: self.set_ultrasonic_occupied_sensitivity(
                ip, params.get("level", "Medium")
            ),
            "set_ultrasonic_vacancy_sensitivity": lambda: self.set_ultrasonic_vacancy_sensitivity(
                ip, params.get("level", "Medium")
            ),
            "set_pir_sensor": lambda: self.set_pir_sensor(ip, params.get("enabled", True)),
            "set_pir_sensitivity": lambda: self.set_pir_sensitivity(
                ip,
                params.get("occupied"),
                params.get("vacancy")
            ),
            "set_pir_occupied_sensitivity": lambda: self.set_pir_occupied_sensitivity(
                ip, params.get("level", "Medium")
            ),
            "set_pir_vacancy_sensitivity": lambda: self.set_pir_vacancy_sensitivity(
                ip, params.get("level", "Medium")
            ),
            "set_min_light_change": lambda: self.set_min_light_change(ip, params.get("value", 655)),
            "set_dark_to_bright_threshold": lambda: self.set_dark_to_bright_threshold(ip, params.get("value", 20000)),
            "set_bright_to_dark_threshold": lambda: self.set_bright_to_dark_threshold(ip, params.get("value", 40000)),
            "set_photo_thresholds": lambda: self.set_photo_thresholds(
                ip,
                params.get("dark_to_bright"),
                params.get("bright_to_dark")
            ),
            "set_hostname": lambda: self.set_hostname(ip, params.get("hostname", "")),
            "set_domain": lambda: self.set_domain(ip, params.get("domain", "")),
            "set_ping": lambda: self.set_ping(ip, params.get("enabled", True)),
            "set_ssh": lambda: self.set_ssh(ip, params.get("enabled", True)),
            "set_autoneg": lambda: self.set_autoneg(ip, params.get("enabled", True)),
            "set_igmp": lambda: self.set_igmp(ip, params.get("version", "v2")),
            "set_dhcp": lambda: self.set_dhcp(ip, params.get("enabled", True)),
            "set_static_ip": lambda: self.set_static_ip(ip, params.get("address", ""), params.get("mask", "")),
            "set_static_gateway": lambda: self.set_static_gateway(ip, params.get("gateway", "")),
            "set_static_dns": lambda: self.set_static_dns(ip, params.get("dns_list", [])),
            "set_adapter_enabled": lambda: self.set_adapter_enabled(ip, params.get("enabled", True)),
        }
        
        handler = command_map.get(normalized_command)
        if not handler:
            available = ', '.join(command_map.keys())
            return False, f"Unknown command: '{command}'. Available: {available}"
        
        try:
            return handler()
        except Exception as e:
            return False, f"Command failed: {str(e)}"

    # ─────────────────── GET DEVICE INFO ───────────────────

    def get_device_info(self, ip, port=443, display_id=None):
        """Get comprehensive device information"""
        username = self.config.get("username")
        password = self.config.get("password")
        
        if not username or not password:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "Occupancy Sensor",
                "current_status": "Offline",
                "error": "Missing credentials: username and password are required."
            }

        try:
            # Get device info
            device_info_result = self.get_device_info_api(ip)
            device_info = device_info_result.get("Device", {}).get("DeviceInfo", {})
            
            # Get occupancy sensor info
            occ_result = self.get_occupancy_sensor_api(ip)
            occupancy = occ_result.get("Device", {}).get("OccupancySensor", {})
            
            # Get photo sensor info
            photo_result = self.get_photo_sensor_api(ip)
            photo = photo_result.get("Device", {}).get("PhotoSensor", {})
            
            is_occupied = occupancy.get("IsRoomOccupied")
            level_reading = photo.get("LevelReading", {})
            threshold_detection = photo.get("ThresholdDetection", {})

            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": device_info.get("Manufacturer", "Crestron"),
                "device_name": device_info.get("Name") or device_info.get("Model") or "Crestron Occupancy Sensor",
                "model": device_info.get("Model"),
                "serial_number": self._clean_value(device_info.get("SerialNumber")),
                "mac_address": self._normalize_mac(device_info.get("MacAddress") or device_info.get("DeviceId")),
                "firmware": self._clean_value(device_info.get("DeviceVersion")) or self._clean_value(device_info.get("Version")),
                "device_id": device_info.get("DeviceId"),
                "build_date": device_info.get("BuildDate"),
                "device_type": "Crestron Occupancy Sensor",
                "category": device_info.get("Category"),
                "puf_version": device_info.get("PufVersion"),
                "reboot_reason": device_info.get("RebootReason"),
                "device_key": device_info.get("Devicekey"),
                "api_version": device_info.get("Version"),
                "is_room_occupied": is_occupied,
                "is_grace_occupancy_detected": occupancy.get("IsGraceOccupancyDetected"),
                "timeout_seconds": occupancy.get("TimeoutSeconds"),
                "is_led_flash_enabled": occupancy.get("IsLedFlashEnabled"),
                "occupancy_sensor": occupancy,
                "photo_sensor": {
                    "light_value": level_reading.get("LightValue"),
                    "min_light_change": level_reading.get("MinLightChange"),
                    "is_room_bright": threshold_detection.get("IsRoomBright"),
                    "dark_to_bright_threshold": threshold_detection.get("DarkToBrightThreshold"),
                    "bright_to_dark_threshold": threshold_detection.get("BrightToDarkThreshold"),
                },
                "raw_data": {
                    "DeviceInfo": device_info,
                    "OccupancySensor": occupancy,
                    "PhotoSensor": photo,
                },
                "current_status": "Online"
            }
        except Exception as e:
            return {
                "ip_address": ip,
                "port": port,
                "display_id": display_id,
                "make": "Crestron",
                "device_type": "Occupancy Sensor",
                "current_status": "Offline",
                "error": str(e)
            }

    # ─────────────────── QUERY STATUS ───────────────────

    def query_status(self, ip, port=443, display_id=None):
        """Quick status query - returns essential device status"""
        username = self.config.get("username")
        password = self.config.get("password")
        
        if not username or not password:
            return {"reachable": False, "error": "Missing credentials: username and password are required."}

        try:
            # Get occupancy sensor info (fastest)
            occ_result = self.get_occupancy_sensor_api(ip)
            occupancy = occ_result.get("Device", {}).get("OccupancySensor", {})
            
            # Get device info for name/model
            device_info_result = self.get_device_info_api(ip)
            device_info = device_info_result.get("Device", {}).get("DeviceInfo", {})
            
            # Try to get ethernet config
            try:
                eth_result = self.get_ethernet_config_api(ip)
                eth = eth_result.get("Device", {}).get("Ethernet", {})
                adapters = eth.get("Adapters", [])
                ipv4 = (adapters[0] if adapters else {}).get("IPv4", {})
                current_addrs = ipv4.get("Addresses", [])
                current_ip = (current_addrs[0] if current_addrs else {}).get("Address")
                subnet_mask = (current_addrs[0] if current_addrs else {}).get("SubnetMask")
                gateway = ipv4.get("DefaultGateway")
            except Exception:
                current_ip = None
                subnet_mask = None
                gateway = None

            us = occupancy.get("Ultrasonic") or {}
            pir = occupancy.get("Pir") or {}

            return {
                "reachable": True,
                "power": "ON",
                "device_name": device_info.get("Name") or device_info.get("Model"),
                "model": device_info.get("Model"),
                "serial_number": device_info.get("SerialNumber"),
                "firmware": self._clean_value(device_info.get("DeviceVersion")),
                "mac_address": self._normalize_mac(device_info.get("MacAddress") or device_info.get("DeviceId")),
                "is_room_occupied": occupancy.get("IsRoomOccupied"),
                "is_grace_occupancy_detected": occupancy.get("IsGraceOccupancyDetected"),
                "timeout_seconds": occupancy.get("TimeoutSeconds"),
                "is_led_flash_enabled": occupancy.get("IsLedFlashEnabled"),
                "is_short_timeout_enabled": occupancy.get("IsShortTimeoutEnabled"),
                "current_ip": current_ip,
                "subnet_mask": subnet_mask,
                "gateway": gateway,
                "occupancy_sensor": {
                    "is_room_occupied": occupancy.get("IsRoomOccupied"),
                    "is_grace_occupancy_detected": occupancy.get("IsGraceOccupancyDetected"),
                    "timeout_seconds": occupancy.get("TimeoutSeconds"),
                    "is_led_flash_enabled": occupancy.get("IsLedFlashEnabled"),
                    "is_short_timeout_enabled": occupancy.get("IsShortTimeoutEnabled"),
                    "occupancy_logic": "OR" if occupancy.get("IsSingleSensorDeterminingOccupancy") else "AND",
                    "vacancy_logic": "OR" if occupancy.get("IsSingleSensorDeterminingVacancy") else "AND",
                    "ultrasonic": {
                        "is_sensor1_enabled": us.get("IsSensor1Enabled"),
                        "is_sensor2_enabled": us.get("IsSensor2Enabled"),
                        "occupied_sensitivity": us.get("OccupiedSensitivity"),
                        "vacancy_sensitivity": us.get("VacancySensitivity"),
                    },
                    "pir": {
                        "is_sensor1_enabled": pir.get("IsSensor1Enabled"),
                        "occupied_sensitivity": pir.get("OccupiedSensitivity"),
                        "vacancy_sensitivity": pir.get("VacancySensitivity"),
                    },
                },
            }
        except Exception as e:
            return {"reachable": False, "error": str(e)}