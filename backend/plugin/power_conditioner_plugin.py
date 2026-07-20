# Power Conditioner plugin for Edge RMM
import re
import requests
import os 
from .base import ManualPlatformPlugin
 
 
class PowerConditionerPlugin(ManualPlatformPlugin):
    """Power Conditioner plugin via HTTP API."""
 
    name = "power_conditioner"
    display_name = "Power Conditioner"
    description = "Power Conditioner (HTTP API via Edge)"
 
    supports_display_id = False
    supports_port = True
    default_port = 5000
 
 # WITH THIS:
    COMMANDS = {
    **{f"outlet_{i}_on": {"method": "POST"} for i in range(1, 9)},
    **{f"outlet_{i}_off": {"method": "POST"} for i in range(1, 9)},
    "all_outlets_on": {"method": "POST"},
    "all_outlets_off": {"method": "POST"},
    "get_schedules":          {"method": "GET"},
    "create_schedule":        {"method": "POST"},
    "update_schedule":        {"method": "PATCH"},
    "delete_schedule":        {"method": "DELETE"},
    "get_statistical_report": {"method": "GET"},
}
 
    def _get_headers(self):
        serial = (
            self.config.get("serial_number")
            or self.config.get("serial")
            or self.config.get("x_api_key")
        )
        return {"x-api-key": str(serial).strip()} if serial else {}
 
    def _request_json(self, method, url, headers=None, json_body=None):
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_body,
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body_text = ""
            try:
                body_text = response.text.strip()
            except Exception:
                body_text = ""
            if body_text:
                raise RuntimeError(f"{exc}; response={body_text}") from exc
            raise
 
        if not response.text or not response.text.strip():
            return {}
        return response.json()
 
    def _normalize_schedule(self, item, index):
        status = item.get("status")
        enabled = item.get("enabled")
 
        if enabled is None:
            raw_enabled = item.get("is_enabled", item.get("active"))
            if isinstance(raw_enabled, str):
                enabled = raw_enabled.strip().lower() in {"on", "enabled", "active", "true", "1"}
            elif raw_enabled is not None:
                enabled = bool(raw_enabled)
 
        if enabled is None and isinstance(status, str):
            enabled = status.strip().lower() in {"on", "enabled", "active", "true", "1"}
        elif enabled is None and isinstance(status, (bool, int)):
            enabled = bool(status)
 
        if status is None and enabled is not None:
            status = "enabled" if enabled else "disabled"
 
        return {
            **item,
            "schedule_id": item.get("schedule_id", item.get("id", item.get("index", index))),
            "enabled": enabled,
            "status": status,
        }
 
    def _extract_schedules(self, payload):
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("schedules") or payload.get("data") or payload.get("items") or []
        else:
            items = []
 
        schedules = []
        for index, item in enumerate(items):
            schedules.append(self._normalize_schedule(item, index) if isinstance(item, dict) else {
                "schedule_id": index,
                "raw": item,
                "enabled": None,
                "status": None,
            })
        return schedules
 
    def _extract_schedule_items(self, payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            items = payload.get("schedules") or payload.get("data") or payload.get("items")
            if isinstance(items, list):
                return items
        return []
 
    def _coerce_outlet_numbers(self, values):
        outlet_numbers = []
        for value in values or []:
            if isinstance(value, int):
                outlet_numbers.append(value)
            elif isinstance(value, str) and value.strip().isdigit():
                outlet_numbers.append(int(value.strip()))
        return outlet_numbers
 
    def _build_status_value(self, current_value, enabled, true_value, false_value):
        if enabled is None:
            return current_value
        if isinstance(current_value, str):
            normalized = current_value.strip().lower()
            if normalized in {"on", "off"}:
                return "on" if enabled else "off"
            if normalized in {"enabled", "disabled"}:
                return "enabled" if enabled else "disabled"
            if normalized in {"active", "inactive"}:
                return "active" if enabled else "inactive"
            if normalized in {"true", "false"}:
                return "true" if enabled else "false"
            if normalized in {"1", "0"}:
                return "1" if enabled else "0"
        if isinstance(current_value, bool):
            return enabled
        if isinstance(current_value, int):
            return 1 if enabled else 0
        return true_value if enabled else false_value
 
    def _fetch_schedule_payload(self, ip, port, headers):
        url = f"http://{ip}:{port}/powerconditioner/schedules"
        return self._request_json("GET", url, headers=headers)
 
    def _build_schedule_object(self, payload, existing_items):
        body = dict(payload or {})
        items = existing_items or []
        exemplar = next((item for item in items if isinstance(item, dict)), {})
 
        schedule_id = body.get("schedule_id", body.get("id"))
        if schedule_id is None:
            existing_ids = []
            for item in items:
                if isinstance(item, dict):
                    value = item.get("schedule_id", item.get("id", item.get("index")))
                    if isinstance(value, int):
                        existing_ids.append(value)
            schedule_id = (max(existing_ids) + 1) if existing_ids else len(items)
 
        devices = body.get("devices") or []
        outlets = self._coerce_outlet_numbers(body.get("outlets") or [])
        days = body.get("days") or []
        action = str(body.get("action") or body.get("state") or body.get("status") or "").lower()
        enabled = body.get("enabled")
        if enabled is None and action in {"on", "off"}:
            enabled = action == "on"
 
        new_item = dict(exemplar) if isinstance(exemplar, dict) else {}
 
        if "schedule_id" in new_item or "schedule_id" in body:
            new_item["schedule_id"] = schedule_id
        if "id" in new_item or "id" in body:
            new_item["id"] = schedule_id
        if "index" in new_item and "index" not in body:
            new_item["index"] = schedule_id
 
        if days:
            if "days" in new_item or "days" in body:
                new_item["days"] = days
            if "day_of_week" in new_item:
                new_item["day_of_week"] = days
 
        start_time = body.get("start_time")
        end_time = body.get("end_time")
        if start_time:
            if "start_time" in new_item or "start_time" in body:
                new_item["start_time"] = start_time
            if "start" in new_item:
                new_item["start"] = start_time
            if "from" in new_item:
                new_item["from"] = start_time
            if "time_from" in new_item:
                new_item["time_from"] = start_time
        if end_time:
            if "end_time" in new_item or "end_time" in body:
                new_item["end_time"] = end_time
            if "end" in new_item:
                new_item["end"] = end_time
            if "to" in new_item:
                new_item["to"] = end_time
            if "time_to" in new_item:
                new_item["time_to"] = end_time
 
        if devices:
            if "devices" in new_item or "devices" in body:
                exemplar_devices = exemplar.get("devices")
                if (
                    isinstance(exemplar_devices, list)
                    and exemplar_devices
                    and all(isinstance(value, int) for value in exemplar_devices)
                ):
                    new_item["devices"] = outlets or self._coerce_outlet_numbers(devices)
                else:
                    new_item["devices"] = devices
        if outlets:
            if "outlets" in new_item or "outlets" in body:
                new_item["outlets"] = outlets
 
        resolved_action = action or ("on" if enabled else "off")
        if "action" in new_item or "action" in body:
            new_item["action"] = self._build_status_value(
                new_item.get("action"),
                enabled,
                "on",
                "off",
            ) or resolved_action
        if "state" in new_item or "state" in body:
            new_item["state"] = body.get("state") or self._build_status_value(
                new_item.get("state"),
                enabled,
                "on",
                "off",
            ) or resolved_action
        if "status" in new_item or "status" in body:
            new_item["status"] = body.get("status") or self._build_status_value(
                new_item.get("status"),
                enabled,
                "enabled",
                "disabled",
            ) or ("enabled" if enabled else "disabled")
        if "enabled" in new_item or "enabled" in body:
            new_item["enabled"] = bool(enabled) if enabled is not None else None
        if "is_enabled" in new_item:
            new_item["is_enabled"] = bool(enabled) if enabled is not None else None
        if "active" in new_item:
            new_item["active"] = bool(enabled) if enabled is not None else None
 
        if not new_item:
            new_item = {
                "schedule_id": schedule_id,
                "id": schedule_id,
                "days": days,
                "start_time": start_time,
                "end_time": end_time,
                "devices": devices,
                "outlets": outlets,
                "action": resolved_action,
                "state": body.get("state") or resolved_action,
                "status": body.get("status") or ("enabled" if enabled else "disabled"),
                "enabled": bool(enabled) if enabled is not None else None,
            }
 
        return {key: value for key, value in new_item.items() if value is not None}
 
    def _replace_schedule_list(self, ip, port, headers, items):
        url = f"http://{ip}:{port}/powerconditioner/schedules"
        if not isinstance(items, list):
            raise RuntimeError("Schedule payload must be a list")
        return self._request_json("POST", url, headers=headers, json_body=items)
 
    def _fetch_statistical_report(self, ip, port, headers):
        endpoints = [
            f"http://{ip}:{port}/powerconditioner/statistical-report",
            f"http://{ip}:{port}/statistical_report",
        ]
 
        last_error = None
        for url in endpoints:
            try:
                return self._request_json("GET", url, headers=headers)
            except Exception as exc:
                last_error = exc
 
        if last_error:
            raise last_error
        raise RuntimeError("Unable to fetch statistical report")
 
    def _fetch_outlet_status(self, ip, port, headers):
        url = f"http://{ip}:{port}/powerconditioner/outlet-status"
        return self._request_json("GET", url, headers=headers)
 
    def get_device_info(self, ip, port=5000, display_id=None):
        port = int(port or self.default_port)
        headers = self._get_headers()

        info = {
            "ip_address": ip,
            "port": port,
            "make": "Vector",
            "model": "Power Conditioner",
            "statistical_report": {},
            "outlet_status": {},
        }

        try:
            info["statistical_report"] = self._fetch_statistical_report(ip, port, headers)
        except Exception as exc:
            info["statistical_report_error"] = str(exc)

        try:
            info["outlet_status"] = self._fetch_outlet_status(ip, port, headers)
        except Exception as exc:
            info["outlet_status_error"] = str(exc)

        # ── Fetch logs if requested ──────────────────────────────────────
        if self.config.get("fetch_logs"):
            log_type = self.config.get("log_type", "all")
            types_to_fetch = (
                ["voltage", "temperature", "system-actions"]
                if log_type == "all"
                else [log_type]
            )
            base_url = f"http://{ip}:{port}/powerconditioner/logs"

            for t in types_to_fetch:
                key = "system_action_logs" if t == "system-actions" else f"{t}_logs"
                try:
                    import requests as _req
                    resp = _req.get(f"{base_url}/{t}", headers=headers, timeout=10)
                    resp.raise_for_status()
                    info[key] = resp.json().get("logs", [])
                except Exception as exc:
                    info[key] = []
                    info[f"{key}_error"] = str(exc)
        # ────────────────────────────────────────────────────────────────

        stat = info.get("statistical_report", {})
        info["hostname"]       = stat.get("hostname")
        info["firmware_version"] = stat.get("firmware_version")
        info["mac_address"]    = stat.get("mac_address")
        info["serial_number"]  = (
            stat.get("serial_number")
            or self.config.get("serial_number")
            or self.config.get("serial")
            or self.config.get("x_api_key")
        )
        info["model"]          = stat.get("model", info["model"])
        info["current_status"] = "Online" if (info["statistical_report"] or info["outlet_status"]) else "Offline"
        return info

 
    # def send_command(self, ip, port, display_id, command, params=None):
    #     port = int(port or self.default_port)
    #     headers = self._get_headers()
 
    #     try:
    #         match = re.match(r"outlet_(\d+)_(on|off)", command)
    #         if match:
    #             outlet_ui = int(match.group(1))
    #             state = match.group(2)
    #             api_outlet = outlet_ui - 1
    #             url = f"http://{ip}:{port}/powerconditioner/toggle/{api_outlet}/{state}"
    #             requests.post(url, headers=headers, timeout=self.timeout).raise_for_status()
    #             return True, f"Outlet {outlet_ui} turned {state.upper()}"
 
    #         if command in ("all_outlets_on", "all_outlets_off"):
    #             state = "on" if "on" in command else "off"
    #             success_count = 0
    #             for outlet_index in range(8):
    #                 try:
    #                     url = f"http://{ip}:{port}/powerconditioner/toggle/{outlet_index}/{state}"
    #                     requests.post(url, headers=headers, timeout=self.timeout).raise_for_status()
    #                     success_count += 1
    #                 except Exception:
    #                     pass
    #             return success_count == 8, f"{success_count}/8 outlets turned {state.upper()}"
 
    #         return False, f"Unsupported command: {command}"
    #     except Exception as exc:
    #         return False, str(exc)
 
 
 
# REPLACE THE ENTIRE send_command METHOD WITH THIS:
    def send_command(self, ip, port, display_id, command, params=None):
        port = int(port or self.default_port)
        headers = self._get_headers()
        params = params or {}
 
        try:
            # --- Outlet commands ---
            match = re.match(r"outlet_(\d+)_(on|off)", command)
            if match:
                outlet_ui = int(match.group(1))
                state = match.group(2)
                api_outlet = outlet_ui - 1
                url = f"http://{ip}:{port}/powerconditioner/toggle/{api_outlet}/{state}"
                requests.post(url, headers=headers, timeout=self.timeout).raise_for_status()
                return True, f"Outlet {outlet_ui} turned {state.upper()}"
 
            if command in ("all_outlets_on", "all_outlets_off"):
                state = "on" if "on" in command else "off"
                success_count = 0
                for outlet_index in range(8):
                    try:
                        url = f"http://{ip}:{port}/powerconditioner/toggle/{outlet_index}/{state}"
                        requests.post(url, headers=headers, timeout=self.timeout).raise_for_status()
                        success_count += 1
                    except Exception:
                        pass
                return success_count == 8, f"{success_count}/8 outlets turned {state.upper()}"
 
            # --- Schedule commands ---
            if command == "get_schedules":
                result = self.get_schedules(ip=ip, port=port)
                return True, result
 
            if command == "create_schedule":
                payload = params.get("payload") if isinstance(params.get("payload"), dict) else params
                result = self.create_schedule(ip=ip, port=port, payload=payload)
                return True, result
 
            if command == "update_schedule":
                result = self.update_schedule_status(
                    ip=ip,
                    port=port,
                    schedule_id=params.get("schedule_id"),
                    enabled=params.get("enabled"),
                    status=params.get("status"),
                    payload=params.get("payload") if isinstance(params.get("payload"), dict) else params,
                )
                return True, result
 
            if command == "delete_schedule":
                result = self.delete_schedule(
                    ip=ip,
                    port=port,
                    schedule_id=params.get("schedule_id"),
                    payload=params.get("payload") if isinstance(params.get("payload"), dict) else params,
                )
                return True, result
 
            if command == "get_statistical_report":
                result = self.get_statistical_report(ip=ip, port=port)
                return True, result
 
            return False, f"Unsupported command: {command}"
 
        except Exception as exc:
            return False, str(exc)
 
 
 
 
    def query_status(self, ip, port=5000, display_id=None):
            port = int(port or self.default_port)
            headers = self._get_headers()
 
            try:
                outlet_status = self._fetch_outlet_status(ip, port, headers)
                statistical_report = {}
                schedules = []
                stat_error = None
                schedule_error = None
 
                try:
                    statistical_report = self.get_statistical_report(ip=ip, port=port) or {}
                except Exception as exc:
                    stat_error = str(exc)
 
                try:
                    schedules = self.get_schedules(ip=ip, port=port) or []
                except Exception as exc:
                    schedule_error = str(exc)
                outlets = []
 
                for api_index in range(8):
                    ui_index = api_index + 1
                    raw = (
                        outlet_status.get(f"outlet_{api_index}")
                        or outlet_status.get(str(api_index))
                        or outlet_status.get(f"relay_{api_index}")
                        or {}
                    )
 
                    state = None
                    if isinstance(raw, dict):
                        state = raw.get("state") or raw.get("status") or raw.get("power")
                    else:
                        state = raw
 
                    if isinstance(state, str):
                        state = "ON" if state.lower() in {"on", "1", "true"} else "OFF"
                    elif isinstance(state, (int, bool)):
                        state = "ON" if state else "OFF"
                    else:
                        state = None
 
                    outlets.append({
                        "id": ui_index,
                        "state": state,
                        "name": raw.get("device_name") if isinstance(raw, dict) else None,
                    })
 
                result = {
                    "reachable": True,
                    "power": state,
                    "outlets": outlets,
                    "raw_outlet_status": outlet_status,
                    "statistical_report": statistical_report,
                    "schedules": schedules,
                }
                if stat_error:
                    result["statistical_report_error"] = stat_error
                if schedule_error:
                    result["schedules_error"] = schedule_error
                return result
            except Exception as exc:
                return {
                    "reachable": False,
                    "power": "OFF",
                    "error": str(exc),
                }
 
    def get_statistical_report(self, ip, port=5000, display_id=None):
            port = int(port or self.default_port)
            headers = self._get_headers()
            data = self._fetch_statistical_report(ip, port, headers)
            return {
                "hostname": data.get("hostname"),
                "firmware_version": data.get("firmware_version"),
                "mac_address": data.get("mac_address"),
                "model": data.get("model"),
                "serial_number": data.get("serial_number"),
                "power_usage": data.get("power_usage", []),
                "data": data.get("data", []),
            }
    
    def firmware_upgrade(self, ip, port=5000, firmware_path=None, firmware_filename=None):
        port = int(port or self.default_port)
        headers = self._get_headers()
        if not firmware_path:
            raise ValueError("firmware_path is required")
 
        upload_name = firmware_filename or os.path.basename(firmware_path) or "firmware.zip"
        url = f"http://{ip}:{port}/powerconditioner/firmware-upgrade"
 
        with open(firmware_path, "rb") as firmware_file:
            files = {
                "firmware": (upload_name, firmware_file, "application/octet-stream"),
            }
            response = requests.post(
                url,
                headers=headers,
                files=files,
                timeout=self.timeout,
            )
 
        try:
            response.raise_for_status()
        except Exception as exc:
            body_text = ""
            try:
                body_text = response.text.strip()
            except Exception:
                body_text = ""
            if body_text:
                raise RuntimeError(f"{exc}; response={body_text}") from exc
            raise
 
        payload = {}
        if response.text and response.text.strip():
            try:
                payload = response.json()
            except Exception:
                payload = {"message": response.text.strip()}
 
        return {
            "success": True,
            "response": payload,
            "upstream_method": "POST",
            "upstream_url": url,
            "firmware_filename": upload_name,
        }
 
 
    def get_schedules(self, ip, port=5000, display_id=None):
        port = int(port or self.default_port)
        headers = self._get_headers()
        data = self._fetch_schedule_payload(ip, port, headers)
        return self._extract_schedules(data)
 
    def create_schedule(self, ip, port=5000, payload=None):
        port = int(port or self.default_port)
        headers = self._get_headers()
        current_payload = self._fetch_schedule_payload(ip, port, headers)
        current_items = self._extract_schedule_items(current_payload)
        new_item = self._build_schedule_object(payload, current_items)
        next_items = [*current_items, new_item]
        data = self._replace_schedule_list(ip, port, headers, next_items)
        return {
            "request": next_items,
            "response": data,
            "schedules": self.get_schedules(ip, port),
            "upstream_method": "POST",
            "upstream_url": f"http://{ip}:{port}/powerconditioner/schedules",
        }
 
    def delete_schedule(self, ip, port=5000, schedule_id=None, payload=None):
        port = int(port or self.default_port)
        headers = self._get_headers()
        current_payload = self._fetch_schedule_payload(ip, port, headers)
        current_items = self._extract_schedule_items(current_payload)
 
        next_items = []
        for index, item in enumerate(current_items):
            if not isinstance(item, dict):
                next_items.append(item)
                continue
            item_id = item.get("schedule_id", item.get("id", item.get("index", index)))
            if str(item_id) == str(schedule_id):
                continue
            next_items.append(item)
 
        data = self._replace_schedule_list(ip, port, headers, next_items)
        return {
            "request": next_items,
            "response": data,
            "schedules": self.get_schedules(ip, port),
        }
 
    def update_schedule_status(self, ip, port=5000, schedule_id=None, enabled=None, status=None, payload=None):
        port = int(port or self.default_port)
        headers = self._get_headers()
        current_payload = self._fetch_schedule_payload(ip, port, headers)
        current_items = self._extract_schedule_items(current_payload)
 
        resolved_enabled = enabled
        if resolved_enabled is None and isinstance(status, str):
            normalized_status = status.strip().lower()
            if normalized_status in {"on", "enabled", "active", "true", "1"}:
                resolved_enabled = True
            elif normalized_status in {"off", "disabled", "inactive", "false", "0"}:
                resolved_enabled = False
 
        next_items = []
        for index, item in enumerate(current_items):
            if not isinstance(item, dict):
                next_items.append(item)
                continue
 
            item_id = item.get("schedule_id", item.get("id", item.get("index", index)))
            updated = dict(item)
            if str(item_id) == str(schedule_id):
                if resolved_enabled is not None:
                    updated["enabled"] = resolved_enabled
                    updated["state"] = self._build_status_value(
                        updated.get("state"),
                        resolved_enabled,
                        "on",
                        "off",
                    )
                    updated["status"] = self._build_status_value(
                        updated.get("status"),
                        resolved_enabled,
                        "enabled",
                        "disabled",
                    )
                    updated["action"] = self._build_status_value(
                        updated.get("action"),
                        resolved_enabled,
                        "on",
                        "off",
                    )
                    if "is_enabled" in updated:
                        updated["is_enabled"] = resolved_enabled
                    if "active" in updated:
                        updated["active"] = resolved_enabled
                if status is not None:
                    updated["status"] = status
            next_items.append(updated)
 
        data = self._replace_schedule_list(ip, port, headers, next_items)
        return {
            "request": next_items,
            "response": data,
            "schedules": self.get_schedules(ip, port),
        }
 
 