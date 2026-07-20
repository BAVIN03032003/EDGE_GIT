"""
Manual Platform Plugin: CrestronOccupancySensorPlugin (RMM Edge Collector)
"""

import re
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .base import ManualPlatformPlugin


class CrestronOccupancySensorPlugin(ManualPlatformPlugin):
    """Crestron CEN-ODT-C-POE occupancy sensor via authenticated Crestron web API."""

    name = "crestron_occupancy_sensor"
    display_name = "Crestron Occupancy Sensor"
    description = "Crestron CEN-ODT-C-POE (IP + username + password)"
    supports_display_id = False
    supports_port = False
    default_port = 443
    SUPPORTED_MODELS = ["CEN-ODT-C-POE"]

    COMMANDS = {
        # Occupancy
        "set_timeout": {"params": ["seconds"], "description": "Set timeout in seconds (5-1800)"},
        "set_led_flash": {"params": ["enabled"], "description": "Enable/disable LED flash"},
        "set_short_timeout": {"params": ["enabled"], "description": "Enable/disable short timeout"},
        "set_sensor_logic": {"params": ["occupancy_or", "vacancy_or"], "description": "Set sensor logic"},
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
        "set_dark_to_bright_threshold": {"params": ["value"], "description": "Set dark to bright threshold"},
        "set_bright_to_dark_threshold": {"params": ["value"], "description": "Set bright to dark threshold"},
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
        # System
        "reboot": {"params": [], "description": "Reboot the device"},
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
        base_url = f"https://{ip}"
        login_url = f"{base_url}/userlogin.html"
        session = requests.Session()
        session.verify = False

        session.get(login_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        trackid = session.cookies.get("TRACKID")
        if not trackid:
            raise Exception("TRACKID not found on login page")

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

        xsrf = r2.headers.get("CREST-XSRF-TOKEN")
        if xsrf:
            session.headers.update({
                "CREST-XSRF-TOKEN": xsrf,
                "X-CREST-XSRF-TOKEN": xsrf,
            })
        return session

    def _fetch_json(self, session, ip, path):
        url = f"https://{ip}{path}"
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _fetch_json_safe(self, session, ip, *paths):
        last_exc = None
        for path in paths:
            try:
                return self._fetch_json(session, ip, path)
            except Exception as e:
                last_exc = e
        raise last_exc

    def _post_json(self, session, ip, path, data):
        url = f"https://{ip}{path}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        resp = session.post(url, headers=headers, json=data, timeout=10)
        resp.raise_for_status()
        if not resp.content or not resp.content.strip():
            return {}
        try:
            return resp.json()
        except ValueError:
            return {"_raw": resp.text.strip()}

    def _get_session(self, ip):
        username = self.config.get("username")
        password = self.config.get("password")
        if not username or not password:
            raise Exception("Missing credentials: username and password are required.")
        return self._crestron_login(ip, username, password)

    # ─────────────────────── update methods ───────────────────────

    def update_occupancy_sensor(self, ip, updates):
        session = None
        try:
            session = self._get_session(ip)
            return self._post_json(session, ip, "/Device/OccupancySensor/", updates)
        finally:
            if session:
                session.close()

    def update_photo_sensor(self, ip, updates):
        session = None
        try:
            session = self._get_session(ip)
            return self._post_json(session, ip, "/Device/PhotoSensor/", updates)
        finally:
            if session:
                session.close()

    def update_ethernet(self, ip, payload):
        session = None
        try:
            session = self._get_session(ip)
            return self._post_json(session, ip, "/Device/Ethernet/",
                                   {"Device": {"Ethernet": payload}})
        finally:
            if session:
                session.close()

    # ========== REBOOT METHOD ==========

    def reboot_device(self, ip):
        """Reboot the Crestron occupancy sensor"""
        session = None
        try:
            session = self._get_session(ip)
            # Try multiple reboot endpoints
            reboot_endpoints = [
                ("/Device/DeviceOperations/", {"Device": {"DeviceOperations": {"Reboot": True}}}),
                ("/Device/Reboot/", {"Device": {"Reboot": True}}),
                ("/System/Reboot/", {"System": {"Reboot": True}}),
            ]
            for endpoint, payload in reboot_endpoints:
                try:
                    result = self._post_json(session, ip, endpoint, payload)
                    # Check if reboot was accepted
                    if result and (result.get("status") in [200, 202, 204] or "OK" in str(result)):
                        return True, f"Reboot command sent successfully via {endpoint}"
                except Exception as e:
                    continue
            return False, "All reboot endpoints failed"
        except Exception as e:
            return False, f"Reboot failed: {str(e)}"
        finally:
            if session:
                session.close()
 

    # ─────────── OCCUPANCY CONTROL (MATCHES STANDALONE) ───────────

    def set_timeout(self, ip, seconds):
        seconds = int(seconds)
        if not (5 <= seconds <= 1800):
            return False, "Timeout must be between 5 and 1800 seconds"
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"TimeoutSeconds": seconds}}
            })
            return True, f"Timeout set to {seconds} seconds"
        except Exception as e:
            return False, str(e)

    def set_led_flash(self, ip, enabled):
        enabled = bool(enabled)
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"IsLedFlashEnabled": enabled}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"LED flash {status}"
        except Exception as e:
            return False, str(e)

    def set_short_timeout(self, ip, enabled):
        enabled = bool(enabled)
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"IsShortTimeoutEnabled": enabled}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"Short timeout {status}"
        except Exception as e:
            return False, str(e)

    def set_sensor_logic(self, ip, occupancy_or=None, vacancy_or=None):
        try:
            payload = {}
            if occupancy_or is not None:
                payload["IsSingleSensorDeterminingOccupancy"] = bool(occupancy_or)
            if vacancy_or is not None:
                payload["IsSingleSensorDeterminingVacancy"] = bool(vacancy_or)
            
            if payload:
                self.update_occupancy_sensor(ip, {"Device": {"OccupancySensor": payload}})
            
            changes = []
            if occupancy_or is not None:
                changes.append(f"occupancy={'OR' if occupancy_or else 'AND'}")
            if vacancy_or is not None:
                changes.append(f"vacancy={'OR' if vacancy_or else 'AND'}")
            
            return True, f"Sensor logic updated: {', '.join(changes)}"
        except Exception as e:
            return False, str(e)

    # ─────────── ULTRASONIC (MATCHES STANDALONE) ───────────

    def set_ultrasonic_sensors(self, ip, sensor1=None, sensor2=None):
        try:
            payload = {}
            if sensor1 is not None:
                payload["IsSensor1Enabled"] = bool(sensor1)
            if sensor2 is not None:
                payload["IsSensor2Enabled"] = bool(sensor2)
            
            if payload:
                self.update_occupancy_sensor(ip, {
                    "Device": {"OccupancySensor": {"Ultrasonic": payload}}
                })
            
            changes = []
            if sensor1 is not None:
                changes.append(f"sensor1={'enabled' if sensor1 else 'disabled'}")
            if sensor2 is not None:
                changes.append(f"sensor2={'enabled' if sensor2 else 'disabled'}")
            
            return True, f"Ultrasonic sensors updated: {', '.join(changes)}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_sensitivity(self, ip, occupied=None, vacancy=None):
        valid = ["Low", "Medium", "High", "LowX", "Low2X", "Low3X"]
        
        if occupied and occupied not in valid:
            return False, f"Occupied sensitivity must be one of: {', '.join(valid)}"
        if vacancy and vacancy not in valid:
            return False, f"Vacancy sensitivity must be one of: {', '.join(valid)}"
        
        try:
            payload = {}
            if occupied:
                payload["OccupiedSensitivity"] = occupied
            if vacancy:
                payload["VacancySensitivity"] = vacancy
            
            if payload:
                self.update_occupancy_sensor(ip, {
                    "Device": {"OccupancySensor": {"Ultrasonic": payload}}
                })
            
            changes = []
            if occupied:
                changes.append(f"occupied={occupied}")
            if vacancy:
                changes.append(f"vacancy={vacancy}")
            
            return True, f"Ultrasonic sensitivity updated: {', '.join(changes)}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_sensor1(self, ip, enabled):
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": {"IsSensor1Enabled": bool(enabled)}}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"Ultrasonic sensor 1 {status}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_sensor2(self, ip, enabled):
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": {"IsSensor2Enabled": bool(enabled)}}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"Ultrasonic sensor 2 {status}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_occupied_sensitivity(self, ip, level):
        valid = ["Low", "Medium", "High", "LowX", "Low2X", "Low3X"]
        if level not in valid:
            return False, f"Sensitivity must be one of: {', '.join(valid)}"
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": {"OccupiedSensitivity": level}}}
            })
            return True, f"Ultrasonic occupied sensitivity set to {level}"
        except Exception as e:
            return False, str(e)

    def set_ultrasonic_vacancy_sensitivity(self, ip, level):
        valid = ["Low", "Medium", "High", "LowX", "Low2X", "Low3X"]
        if level not in valid:
            return False, f"Sensitivity must be one of: {', '.join(valid)}"
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"Ultrasonic": {"VacancySensitivity": level}}}
            })
            return True, f"Ultrasonic vacancy sensitivity set to {level}"
        except Exception as e:
            return False, str(e)

    # ─────────── PIR (MATCHES STANDALONE) ───────────

    def set_pir_sensor(self, ip, enabled):
        enabled = bool(enabled)
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"Pir": {"IsSensor1Enabled": enabled}}}
            })
            status = "enabled" if enabled else "disabled"
            return True, f"PIR sensor {status}"
        except Exception as e:
            return False, str(e)

    def set_pir_sensitivity(self, ip, occupied=None, vacancy=None):
        valid = ["Low", "Medium", "High"]
        
        if occupied and occupied not in valid:
            return False, f"Occupied sensitivity must be one of: {', '.join(valid)}"
        if vacancy and vacancy not in valid:
            return False, f"Vacancy sensitivity must be one of: {', '.join(valid)}"
        
        try:
            payload = {}
            if occupied:
                payload["OccupiedSensitivity"] = occupied
            if vacancy:
                payload["VacancySensitivity"] = vacancy
            
            if payload:
                self.update_occupancy_sensor(ip, {
                    "Device": {"OccupancySensor": {"Pir": payload}}
                })
            
            changes = []
            if occupied:
                changes.append(f"occupied={occupied}")
            if vacancy:
                changes.append(f"vacancy={vacancy}")
            
            return True, f"PIR sensitivity updated: {', '.join(changes)}"
        except Exception as e:
            return False, str(e)

    def set_pir_occupied_sensitivity(self, ip, level):
        valid = ["Low", "Medium", "High"]
        if level not in valid:
            return False, f"Sensitivity must be one of: {', '.join(valid)}"
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"Pir": {"OccupiedSensitivity": level}}}
            })
            return True, f"PIR occupied sensitivity set to {level}"
        except Exception as e:
            return False, str(e)

    def set_pir_vacancy_sensitivity(self, ip, level):
        valid = ["Low", "Medium", "High"]
        if level not in valid:
            return False, f"Sensitivity must be one of: {', '.join(valid)}"
        try:
            self.update_occupancy_sensor(ip, {
                "Device": {"OccupancySensor": {"Pir": {"VacancySensitivity": level}}}
            })
            return True, f"PIR vacancy sensitivity set to {level}"
        except Exception as e:
            return False, str(e)

    # ─────────── PHOTO SENSOR (MATCHES STANDALONE) ───────────

    def set_min_light_change(self, ip, value):
        value = int(value)
        if not (655 <= value <= 65535):
            return False, "MinLightChange must be between 655 and 65535"
        try:
            self.update_photo_sensor(ip, {
                "Device": {"PhotoSensor": {"LevelReading": {"MinLightChange": value}}}
            })
            return True, f"Min light change set to {value}"
        except Exception as e:
            return False, str(e)

    def set_dark_to_bright_threshold(self, ip, value):
        value = int(value)
        if not (0 <= value <= 65535):
            return False, "DarkToBrightThreshold must be between 0 and 65535"
        try:
            self.update_photo_sensor(ip, {
                "Device": {"PhotoSensor": {"ThresholdDetection": {"DarkToBrightThreshold": value}}}
            })
            return True, f"Dark to bright threshold set to {value}"
        except Exception as e:
            return False, str(e)

    def set_bright_to_dark_threshold(self, ip, value):
        value = int(value)
        if not (0 <= value <= 65535):
            return False, "BrightToDarkThreshold must be between 0 and 65535"
        try:
            self.update_photo_sensor(ip, {
                "Device": {"PhotoSensor": {"ThresholdDetection": {"BrightToDarkThreshold": value}}}
            })
            return True, f"Bright to dark threshold set to {value}"
        except Exception as e:
            return False, str(e)

    def set_photo_thresholds(self, ip, dark_to_bright=None, bright_to_dark=None):
        try:
            payload = {"Device": {"PhotoSensor": {"ThresholdDetection": {}}}}
            if dark_to_bright is not None:
                payload["Device"]["PhotoSensor"]["ThresholdDetection"]["DarkToBrightThreshold"] = int(dark_to_bright)
            if bright_to_dark is not None:
                payload["Device"]["PhotoSensor"]["ThresholdDetection"]["BrightToDarkThreshold"] = int(bright_to_dark)
            self.update_photo_sensor(ip, payload)
            return True, "Photo thresholds updated"
        except Exception as e:
            return False, str(e)

    # ─────────── ETHERNET ───────────

    def set_hostname(self, ip, hostname):
        try:
            self.update_ethernet(ip, {"HostName": hostname})
            return True, f"Hostname set to {hostname}"
        except Exception as e:
            return False, str(e)

    def set_domain(self, ip, domain):
        try:
            self.update_ethernet(ip, {"DomainName": domain})
            return True, f"Domain set to {domain}"
        except Exception as e:
            return False, str(e)

    def set_ping(self, ip, enabled):
        enabled = bool(enabled)
        try:
            self.update_ethernet(ip, {"IsIcmpPingEnabled": enabled})
            status = "enabled" if enabled else "disabled"
            return True, f"ICMP ping {status}"
        except Exception as e:
            return False, str(e)

    def set_ssh(self, ip, enabled):
        enabled = bool(enabled)
        try:
            self.update_ethernet(ip, {"IsSshEnabled": enabled})
            status = "enabled" if enabled else "disabled"
            return True, f"SSH {status}"
        except Exception as e:
            return False, str(e)

    def set_autoneg(self, ip, enabled):
        enabled = bool(enabled)
        try:
            self.update_ethernet(ip, {"AutoNegotiationEnabled": enabled})
            status = "enabled" if enabled else "disabled"
            return True, f"Auto-negotiation {status}"
        except Exception as e:
            return False, str(e)

    def set_igmp(self, ip, version):
        version = str(version).lower()
        if version not in ("v2", "v3"):
            return False, "IGMP version must be 'v2' or 'v3'"
        try:
            self.update_ethernet(ip, {"IgmpVersion": version})
            return True, f"IGMP version set to {version}"
        except Exception as e:
            return False, str(e)

    def set_dhcp(self, ip, enabled, adapter_index=0):
        enabled = bool(enabled)
        try:
            adapters = [{} for _ in range(adapter_index + 1)]
            adapters[adapter_index] = {"IPv4": {"IsDhcpEnabled": enabled}}
            self.update_ethernet(ip, {"Adapters": adapters})
            status = "enabled" if enabled else "disabled"
            return True, f"DHCP {status}"
        except Exception as e:
            return False, str(e)

    # def set_static_ip(self, ip, address, mask, adapter_index=0):
    #     try:
    #         adapters = [{} for _ in range(adapter_index + 1)]
    #         adapters[adapter_index] = {
    #             "IPv4": {"StaticAddresses": [{"Address": address, "SubnetMask": mask}]}
    #         }
    #         self.update_ethernet(ip, {"Adapters": adapters})
    #         return True, f"Static IP set to {address}/{mask}"
    #     except Exception as e:
    #         return False, str(e)

    def set_static_ip(self, ip, address, mask, gateway=None, dns_list=None, adapter_index=0):
        """
        Set static IP + subnet, optionally gateway + DNS, then auto-reboot.
        Accepts address/mask from params. Gateway and DNS are best-effort
        (sent before reboot; device may drop connection mid-write).
        """
        if not address or not mask:
            return False, "address and mask are required for set_static_ip"

        session = None
        try:
            session = self._get_session(ip)

            # ── Step 1: Set static IP + subnet ──────────────────────────
            adapters_ip = [{} for _ in range(adapter_index + 1)]
            adapters_ip[adapter_index] = {
                "IPv4": {"StaticAddresses": [{"Address": address, "SubnetMask": mask}]}
            }
            self._post_json(session, ip, "/Device/Ethernet/",
                            {"Device": {"Ethernet": {"Adapters": adapters_ip}}})
            print(f"[STATIC_IP] Set IP {address}/{mask} OK")

            # ── Step 2: Set gateway (best-effort) ────────────────────────
            if gateway:
                try:
                    adapters_gw = [{} for _ in range(adapter_index + 1)]
                    adapters_gw[adapter_index] = {"IPv4": {"StaticDefaultGateway": gateway}}
                    self._post_json(session, ip, "/Device/Ethernet/",
                                    {"Device": {"Ethernet": {"Adapters": adapters_gw}}})
                    print(f"[STATIC_IP] Set gateway {gateway} OK")
                except Exception as gw_err:
                    print(f"[STATIC_IP] Gateway set failed (non-fatal): {gw_err}")

            # ── Step 3: Set DNS (best-effort) ────────────────────────────
            if dns_list:
                if isinstance(dns_list, str):
                    dns_list = [dns_list]
                try:
                    adapters_dns = [{} for _ in range(adapter_index + 1)]
                    adapters_dns[adapter_index] = {"IPv4": {"StaticDns": dns_list}}
                    self._post_json(session, ip, "/Device/Ethernet/",
                                    {"Device": {"Ethernet": {"Adapters": adapters_dns}}})
                    print(f"[STATIC_IP] Set DNS {dns_list} OK")
                except Exception as dns_err:
                    print(f"[STATIC_IP] DNS set failed (non-fatal): {dns_err}")

            # ── Step 4: Auto-reboot so new IP takes effect ───────────────
            reboot_endpoints = [
                ("/Device/DeviceOperations/", {"Device": {"DeviceOperations": {"Reboot": True}}}),
                ("/Device/Reboot/",           {"Device": {"Reboot": True}}),
                ("/System/Reboot/",           {"System": {"Reboot": True}}),
            ]
            reboot_ok = False
            for endpoint, payload in reboot_endpoints:
                try:
                    self._post_json(session, ip, endpoint, payload)
                    print(f"[STATIC_IP] Reboot triggered via {endpoint}")
                    reboot_ok = True
                    break
                except Exception:
                    continue

            if not reboot_ok:
                print("[STATIC_IP][WARN] Reboot endpoint not confirmed — device may need manual reboot")

            return True, f"Static IP set to {address}/{mask} and device is rebooting"

        except Exception as e:
            return False, f"set_static_ip failed: {str(e)}"
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass



    def set_static_gateway(self, ip, gateway, adapter_index=0):
        try:
            adapters = [{} for _ in range(adapter_index + 1)]
            adapters[adapter_index] = {"IPv4": {"StaticDefaultGateway": gateway}}
            self.update_ethernet(ip, {"Adapters": adapters})
            return True, f"Static gateway set to {gateway}"
        except Exception as e:
            return False, str(e)

    def set_static_dns(self, ip, dns_list, adapter_index=0):
        if isinstance(dns_list, str):
            dns_list = [dns_list]
        try:
            adapters = [{} for _ in range(adapter_index + 1)]
            adapters[adapter_index] = {"IPv4": {"StaticDns": dns_list}}
            self.update_ethernet(ip, {"Adapters": adapters})
            return True, f"Static DNS set to {', '.join(dns_list)}"
        except Exception as e:
            return False, str(e)

    def set_adapter_enabled(self, ip, enabled, adapter_index=0):
        enabled = bool(enabled)
        try:
            adapters = [{} for _ in range(adapter_index + 1)]
            adapters[adapter_index] = {"IsAdapterEnabled": enabled}
            self.update_ethernet(ip, {"Adapters": adapters})
            status = "enabled" if enabled else "disabled"
            return True, f"Adapter {status}"
        except Exception as e:
            return False, str(e)

    # ─────────────────── SEND COMMAND ───────────────────

    def send_command(self, ip, port, display_id, command, params=None):
        if params is None:
            params = {}

        # Shorthand aliases
        shorthand_map = {
            "timeout": "set_timeout",
            "led": "set_led_flash",
            "led_flash": "set_led_flash",
            "short_timeout": "set_short_timeout",
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
            "reboot": "reboot",
            "restart": "reboot",
 
        }

        normalized = shorthand_map.get(command.lower(), command)

        # Command dispatch
        command_map = {
            "reboot": lambda: self.reboot_device(ip),
            "set_timeout": lambda: self.set_timeout(ip, params.get("seconds", 120)),
            "set_led_flash": lambda: self.set_led_flash(ip, params.get("enabled", True)),
            "set_short_timeout": lambda: self.set_short_timeout(ip, params.get("enabled", True)),
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
            # "set_static_ip": lambda: self.set_static_ip(ip, params.get("address", ""), params.get("mask", "")),
            "set_static_ip": lambda: self.set_static_ip(
            ip,
            address   = params.get("address") or params.get("ipaddr") or params.get("ip") or "",
            mask      = params.get("mask") or params.get("subnet") or params.get("subnet_mask") or "",
            gateway   = params.get("gateway") or None,
            dns_list  = [x for x in [params.get("dns1"), params.get("dns2")] if x] or None,
        ),
            "set_static_gateway": lambda: self.set_static_gateway(ip, params.get("gateway", "")),
            "set_static_dns": lambda: self.set_static_dns(ip, params.get("dns_list", [])),
            "set_adapter_enabled": lambda: self.set_adapter_enabled(ip, params.get("enabled", True)),
        }

        handler = command_map.get(normalized)
        if not handler:
            available = ", ".join(command_map.keys())
            return False, f"Unknown command: '{command}'. Available: {available}"

        try:
            return handler()
        except Exception as e:
            return False, f"Command failed: {str(e)}"

    # ─────────────────── GET DEVICE INFO ───────────────────

    def get_device_info(self, ip, port=443, display_id=None):
        username = self.config.get("username")
        password = self.config.get("password")
        if not username or not password:
            return {
                "ip_address": ip, "port": port, "display_id": display_id,
                "make": "Crestron", "device_type": "Occupancy Sensor",
                "current_status": "Offline",
                "error": "Missing credentials: username and password are required.",
            }

        session = None
        try:
            session = self._crestron_login(ip, username, password)
            info_payload = self._fetch_json(session, ip, "/Device/DeviceInfo")
            occ_payload = self._fetch_json_safe(session, ip, "/Device/OccupancySensor/", "/Device/OccupancySensor")
            try:
                photo_payload = self._fetch_json_safe(session, ip, "/Device/PhotoSensor/", "/Device/PhotoSensor")
            except Exception:
                photo_payload = {}
        except Exception as e:
            return {
                "ip_address": ip, "port": port, "display_id": display_id,
                "make": "Crestron", "device_type": "Occupancy Sensor",
                "current_status": "Offline", "error": str(e),
            }
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass

        device_info = ((info_payload or {}).get("Device") or {}).get("DeviceInfo") or {}
        occupancy = ((occ_payload or {}).get("Device") or {}).get("OccupancySensor") or {}
        photo = ((photo_payload or {}).get("Device") or {}).get("PhotoSensor") or {}

        level_reading = photo.get("LevelReading", {})
        threshold_detection = photo.get("ThresholdDetection", {})

        return {
            "ip_address": ip, "port": port, "display_id": display_id,
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
            "is_room_occupied": occupancy.get("IsRoomOccupied"),
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
            "current_status": "Online",
        }

    # ─────────────────── QUERY STATUS ───────────────────

    def query_status(self, ip, port=443, display_id=None):
        import traceback
        print(f"[DEBUG] === query_status called for {ip} ===")
        
        username = self.config.get("username")
        password = self.config.get("password")
        print(f"[DEBUG] Username: {username}, Password: {'***' if password else 'None'}")
        
        if not username or not password:
            print("[DEBUG] Missing credentials")
            return {"reachable": False, "error": "Missing credentials: username and password are required."}

        session = None
        try:
            print("[DEBUG] Attempting login...")
            session = self._crestron_login(ip, username, password)
            print("[DEBUG] Login successful")
            
            print("[DEBUG] Fetching DeviceInfo...")
            info_payload = self._fetch_json(session, ip, "/Device/DeviceInfo")
            print(f"[DEBUG] DeviceInfo response: {info_payload}")
            
            print("[DEBUG] Fetching OccupancySensor...")
            occ_payload = self._fetch_json_safe(session, ip, "/Device/OccupancySensor/", "/Device/OccupancySensor")
            print(f"[DEBUG] OccupancySensor response: {occ_payload}")
            
            print("[DEBUG] Fetching PhotoSensor...")
            try:
                photo_payload = self._fetch_json_safe(session, ip, "/Device/PhotoSensor/", "/Device/PhotoSensor")
                print(f"[DEBUG] PhotoSensor response: {photo_payload}")
            except Exception as e:
                print(f"[DEBUG] PhotoSensor error (non-fatal): {e}")
                photo_payload = {}
                
            print("[DEBUG] Fetching Ethernet...")
            try:
                eth_payload = self._fetch_json_safe(session, ip, "/Device/Ethernet/", "/Device/Ethernet")
                print(f"[DEBUG] Ethernet response: {eth_payload}")
            except Exception as e:
                print(f"[DEBUG] Ethernet error (non-fatal): {e}")
                eth_payload = {}
                
        except Exception as e:
            print(f"[DEBUG] ERROR: {e}")
            traceback.print_exc()
            return {"reachable": False, "error": str(e)}
        finally:
            if session:
                session.close()
                print("[DEBUG] Session closed")

        # Parse the data
        device_info = ((info_payload or {}).get("Device") or {}).get("DeviceInfo") or {}
        occupancy = ((occ_payload or {}).get("Device") or {}).get("OccupancySensor") or {}
        photo = ((photo_payload or {}).get("Device") or {}).get("PhotoSensor") or {}
        eth = ((eth_payload or {}).get("Device") or {}).get("Ethernet") or {}

        print(f"[DEBUG] Parsed device_info: {device_info}")
        print(f"[DEBUG] Parsed occupancy: {occupancy}")
        
        level_reading = photo.get("LevelReading", {})
        threshold_detection = photo.get("ThresholdDetection", {})
        adapters = eth.get("Adapters", [])
        ipv4 = (adapters[0] if adapters else {}).get("IPv4", {})
        current_addrs = ipv4.get("Addresses", [])
        current_ip = (current_addrs[0] if current_addrs else {}).get("Address")
        subnet_mask = (current_addrs[0] if current_addrs else {}).get("SubnetMask")
        us = occupancy.get("Ultrasonic") or {}
        pir = occupancy.get("Pir") or {}

        result = {
            "reachable": True,
            "power": "ON",
            "device_name": device_info.get("Name") or device_info.get("Model"),
            "model": device_info.get("Model"),
            "serial_number": device_info.get("SerialNumber"),
            "firmware": self._clean_value(device_info.get("DeviceVersion")),
            "api_version": device_info.get("Version"),
            "build_date": device_info.get("BuildDate"),
            "category": device_info.get("Category"),
            "puf_version": device_info.get("PufVersion"),
            "device_key": device_info.get("Devicekey"),
            "mac_address": self._normalize_mac(device_info.get("MacAddress") or device_info.get("DeviceId")),
            "is_room_occupied": occupancy.get("IsRoomOccupied"),
            "is_grace_occupancy_detected": occupancy.get("IsGraceOccupancyDetected"),
            "timeout_seconds": occupancy.get("TimeoutSeconds"),
            "is_led_flash_enabled": occupancy.get("IsLedFlashEnabled"),
            "is_short_timeout_enabled": occupancy.get("IsShortTimeoutEnabled"),
            "current_ip": current_ip,
            "subnet_mask": subnet_mask,
            "gateway": ipv4.get("DefaultGateway"),
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
            "raw_occupancy": occupancy,
            "photo_sensor": {
                "level_reading": {
                    "light_value": level_reading.get("LightValue"),
                    "min_light_change": level_reading.get("MinLightChange"),
                },
                "threshold_detection": {
                    "is_room_bright": threshold_detection.get("IsRoomBright"),
                    "dark_to_bright_threshold": threshold_detection.get("DarkToBrightThreshold"),
                    "bright_to_dark_threshold": threshold_detection.get("BrightToDarkThreshold"),
                },
            },
            "raw_photo_sensor": photo,
            "ethernet_config": {
                "host_name": eth.get("HostName"),
                "domain_name": eth.get("DomainName"),
                "igmp_version": eth.get("IgmpVersion"),
                "ping_enabled": eth.get("IsIcmpPingEnabled"),
                "ssh_enabled": eth.get("IsSshEnabled"),
                "auto_neg": eth.get("AutoNegotiationEnabled"),
                "adapters": [{
                    "ipv4": {
                        "is_dhcp_enabled": ipv4.get("IsDhcpEnabled"),
                        "addresses": current_addrs,
                        "default_gateway": ipv4.get("DefaultGateway"),
                        "dns_servers": ipv4.get("DnsServers", []),
                    }
                }],
            },
        }
        
        print(f"[DEBUG] Final result: {result}")
        return result
        