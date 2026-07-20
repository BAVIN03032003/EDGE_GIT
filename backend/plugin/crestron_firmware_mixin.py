"""
CrestronFirmwareMixin — firmware upgrade logic for Crestron devices.
Used by the edge collector's firmware_upgrade command handler.
"""

import json
import logging
import requests
import urllib3

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CrestronFirmwareMixin:
    """
    Mixin that adds Crestron firmware upgrade capabilities.
    All methods are static so they can be called without instantiating a plugin.
    """

    STATUS_PROGRESS_MAP = [
        ("Puf Upgrade Success", 100, "Firmware upgrade complete!"),
        ("Firmware Upgrade Rebooting", 90, "Rebooting device..."),
        ("Puf Upgrade InProgress", 70, "Upgrade in progress..."),
        ("Firmware Upgrade Loading", 55, "Loading firmware to device..."),
        ("Inflating", 40, "Decompressing firmware..."),
        ("PUF Started", 25, "Package unpack started..."),
        ("Firmware Upgrade Started", 10, "Firmware upgrade started..."),
    ]

    FAILURE_STATUSES = ["PUF Failed", "Firmware Upgrade Failed"]

    @classmethod
    def parse_upgrade_status(cls, raw_status):
        if not raw_status:
            return "Unknown", 0, False, False, ""
        text = raw_status.strip()
        is_failure = any(text == f for f in cls.FAILURE_STATUSES)
        is_success = text == "Puf Upgrade Success"
        progress = 0
        matched = text
        label = ""
        for keyword, pct, friendly in cls.STATUS_PROGRESS_MAP:
            if text == keyword:
                progress = pct
                matched = keyword
                label = friendly
                break
        return matched, progress, is_success, is_failure, label

    @staticmethod
    def login_device(ip, username, password):
        base_url = f"https://{ip}"
        login_url = f"{base_url}/userlogin.html"
        session = requests.Session()
        session.verify = False

        resp_a = session.get(login_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        trackid = session.cookies.get("TRACKID")
        if not trackid:
            session.close()
            raise Exception("TRACKID not found on login page")

        headers_b = {
            "Cookie": f"TRACKID={trackid}",
            "Origin": base_url,
            "Referer": login_url,
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        }
        payload = f"login={username}&&passwd={password}"
        resp_b = session.post(login_url, headers=headers_b, data=payload, timeout=10)
        if resp_b.status_code != 200:
            session.close()
            raise Exception(f"Login failed (HTTP {resp_b.status_code})")

        xsrf = resp_b.headers.get("CREST-XSRF-TOKEN")
        if not xsrf:
            has_session_cookies = any(
                c.name in ("PHPSESSIONID", "SID", "TRACKID")
                for c in session.cookies
            )
            if not has_session_cookies:
                session.close()
                raise Exception("Login failed — no CREST-XSRF-TOKEN and no session cookies")
            logger.warning(f"[CrestronFirmwareMixin] CREST-XSRF-TOKEN missing, proceeding with cookies only")

        if xsrf:
            session.headers.update({
                "CREST-XSRF-TOKEN": xsrf,
                "X-CREST-XSRF-TOKEN": xsrf,
            })
        session.headers.update({"Referer": base_url})
        return session, xsrf

    @staticmethod
    def _headers_with_xsrf(base, xsrf_token):
        if xsrf_token:
            base["X-CREST-XSRF-TOKEN"] = xsrf_token
        return base

    @staticmethod
    def get_firmware_directory(session, ip, xsrf_token):
        url = f"https://{ip}/Device/FilePaths/"
        try:
            resp = session.get(url, headers=CrestronFirmwareMixin._headers_with_xsrf({"Accept": "application/json"}, xsrf_token), timeout=10, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                return (data.get("Device", {}).get("FilePaths", {}).get("Firmware", {}).get("FirmwareFile", "") or "/data/web/tmp/firmware")
        except Exception:
            pass
        return "/data/web/tmp/firmware"

    @staticmethod
    def upload_firmware(session, xsrf_token, ip, filepath, filename):
        url = f"https://{ip}/Device/DeviceOperations/"
        headers = CrestronFirmwareMixin._headers_with_xsrf({
            "User-Agent": "Mozilla/5.0",
            "Connection": "keep-alive",
            "Accept-Encoding": "identity",
            "Accept": "application/json",
        }, xsrf_token)
        try:
            with open(filepath, "rb") as f:
                files = [
                    ("FirmwareUpgradeType", (None, "HTTP")),
                    ("FirmwareUpgrade", (filename, f, "application/octet-stream")),
                ]
                response = session.post(
                    url, headers=headers, files=files,
                    timeout=600, verify=False,
                )
            if response.status_code in (200, 202):
                fw_dir = CrestronFirmwareMixin.get_firmware_directory(session, ip, xsrf_token)
                device_path = f"{fw_dir}/{filename}"
                return True, {"status_code": response.status_code, "device_path": device_path}
            return False, {"error": f"HTTP {response.status_code}", "message": response.text[:300]}
        except requests.exceptions.RequestException as e:
            fw_dir = CrestronFirmwareMixin.get_firmware_directory(session, ip, xsrf_token)
            device_path = f"{fw_dir}/{filename}"
            return True, {"status_code": 0, "device_path": device_path, "warning": f"Upload may have succeeded despite {type(e).__name__}"}

    @staticmethod
    def trigger_upgrade(session, xsrf_token, ip, device_path):
        url = f"https://{ip}/Device/DeviceOperations/"
        payload = {"Device": {"DeviceOperations": {"FirmwareUpgrade": device_path}}}
        headers = CrestronFirmwareMixin._headers_with_xsrf({
            "Content-Type": "application/json",
            "Accept": "application/json",
        }, xsrf_token)
        try:
            resp = session.post(url, json=payload, headers=headers, timeout=30, verify=False)
            if resp.status_code == 200:
                return True, {"response": resp.text[:500]}
            return False, {"error": f"HTTP {resp.status_code}", "message": resp.text[:300]}
        except Exception as e:
            return False, {"error": str(e)}

    @staticmethod
    def get_upgrade_status(session, xsrf_token, ip):
        urls = [
            f"https://{ip}/Device/DeviceOperations/UpgradeStatus",
            f"https://{ip}/Device/DeviceOperations/",
        ]
        cookie_str = "; ".join(f"{k}={v}" for k, v in session.cookies.items() if v)
        base_headers = CrestronFirmwareMixin._headers_with_xsrf({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Origin": f"https://{ip}",
            "Referer": f"https://{ip}",
        }, xsrf_token)
        if cookie_str:
            base_headers["Cookie"] = cookie_str

        for url in urls:
            try:
                resp = session.get(url, headers=base_headers, timeout=10, verify=False)
                body = resp.text or ""

                ct = (resp.headers.get("Content-Type") or "").lower()
                body_lower = body.strip().lower()
                if ("html" in ct or
                    body_lower.startswith("<!doctype html") or
                    body_lower.startswith("<html") or
                    "<html" in body_lower):
                    return {"status": "Unknown", "raw_status": "", "progress": 0,
                            "completed": False, "success": False,
                            "error": "Non-JSON response", "_recoverable": True, "_needs_login": True}

                if resp.status_code in (401, 403):
                    return {"status": "Unknown", "raw_status": "", "progress": 0,
                            "completed": False, "success": False,
                            "error": f"HTTP {resp.status_code}", "_recoverable": True, "_needs_login": True}

                data = None
                if body.strip():
                    try:
                        data = resp.json()
                    except (json.JSONDecodeError, ValueError):
                        pass

                if data:
                    raw_status = (data.get("Device", {})
                                  .get("DeviceOperations", {})
                                  .get("UpgradeStatus", ""))
                    if raw_status or url.endswith("UpgradeStatus"):
                        matched, progress, is_success, is_failure, label = CrestronFirmwareMixin.parse_upgrade_status(raw_status)
                        return {
                            "status": matched,
                            "raw_status": raw_status,
                            "progress": progress,
                            "label": label,
                            "completed": is_success or is_failure,
                            "success": is_success,
                            "error": raw_status if is_failure else None,
                        }

                continue

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                continue
            except Exception:
                continue

        return {"status": "Unknown", "raw_status": "", "progress": 0,
                "completed": False, "success": False,
                "error": "No valid status endpoint", "_recoverable": True, "_needs_login": True}

    @staticmethod
    def fetch_firmware_version(session, xsrf_token, ip):
        url = f"https://{ip}/Device/DeviceInfo/"
        cookie_str = "; ".join(f"{k}={v}" for k, v in session.cookies.items() if v)
        headers = CrestronFirmwareMixin._headers_with_xsrf({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Origin": f"https://{ip}",
            "Referer": f"https://{ip}",
        }, xsrf_token)
        if cookie_str:
            headers["Cookie"] = cookie_str
        try:
            resp = session.get(url, headers=headers, timeout=10, verify=False)
            if resp.status_code != 200:
                return ""
            data = resp.json()
            info = data.get("Device", {}).get("DeviceInfo", {})
            return (info.get("PufVersion")
                    or info.get("FirmwareVersion")
                    or info.get("DeviceVersion")
                    or "")
        except Exception:
            return ""
