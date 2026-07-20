
#     devices = EdgeState.get('power_conditioners', [])
#     device = next(
#         (
#             d for d in devices
#             if (serial and d.get('serial_number') == serial) or
#                (unique_id and d.get('unique_id') == unique_id)
#         ),
#         None
#     )

#     if not device:
#         return jsonify({'error': 'Power conditioner not found'}), 404

#     ip = device.get('ip_address')
#     serial_number = device.get('serial_number')

#     headers = {'x-api-key': serial_number}

#     try:
#         # ---------------------------------------------------
#         # 1. Send control command to actual device
#         # ---------------------------------------------------
#         control_url = f'http://{ip}:5000/powerconditioner/control'

#         control_payload = {
#             'relay_id': relay_id,
#             'action': action
#         }

#         control_response = requests.post(
#             control_url,
#             headers=headers,
#             json=control_payload,
#             timeout=10
#         )
#         control_response.raise_for_status()

#         control_result = control_response.json()

#         # ---------------------------------------------------
#         # 2. Fetch updated outlet status after control
#         # ---------------------------------------------------
#         outlet_response = requests.get(
#             f'http://{ip}:5000/powerconditioner/outlet-status',
#             headers=headers,
#             timeout=10
#         )
#         outlet_response.raise_for_status()
#         relays = outlet_response.json()

#         # ---------------------------------------------------
#         # 3. Fetch updated statistical report
#         # ---------------------------------------------------
#         stat = fetch_statistical_report(ip, headers, timeout=10)

#         yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
#         yesterday_consumption = extract_yesterday_consumption_from_stat(stat, yesterday)

#         active_relay_count = len([
#             1 for r in (relays or {}).values()
#             if str(r.get('state', '')).lower() == 'on'
#         ])

#         # ---------------------------------------------------
#         # 4. Update device state
#         # ---------------------------------------------------
#         device['relay_statuses'] = format_relay_statuses(relays)
#         device['device_connected'] = active_relay_count
#         device['current_status'] = 'Online'
#         device['yesterday_consumption'] = yesterday_consumption
#         device['energy_saved'] = calculate_energy_saved(
#             _safe_float(device.get('estimate_btu', 0), 0.0),
#             yesterday_consumption
#         )
#         device['last_synced_at'] = datetime.now().isoformat()
#         device['last_control_action'] = action
#         device['last_control_relay'] = relay_id
#         device['last_control_at'] = datetime.now().isoformat()

#         EdgeState.set('power_conditioners', devices)

#         # ---------------------------------------------------
#         # 5. Add logs
#         # ---------------------------------------------------
#         logs = EdgeState.get('power_conditioner_logs', [])
#         logs.append({
#             'timestamp': datetime.now().isoformat(),
#             'event': 'control',
#             'serial_number': serial_number,
#             'relay_id': relay_id,
#             'action': action,
#             'result': 'success'
#         })
#         EdgeState.set('power_conditioner_logs', logs)

#         return jsonify({
#             'success': True,
#             'message': f'Relay {relay_id} turned {action}',
#             'device': device,
#             'device_response': control_result
#         }), 200

#     except Exception as exc:
#         # mark device offline only if communication failed
#         device['current_status'] = 'Offline'
#         device['last_synced_at'] = datetime.now().isoformat()
#         EdgeState.set('power_conditioners', devices)

#         logs = EdgeState.get('power_conditioner_logs', [])
#         logs.append({
#             'timestamp': datetime.now().isoformat(),
#             'event': 'control',
#             'serial_number': serial_number,
#             'relay_id': relay_id,
#             'action': action,
#             'result': 'failed',
#             'error': str(exc)
#         })
#         EdgeState.set('power_conditioner_logs', logs)

#         return jsonify({
#             'success': False,
#             'error': str(exc)
#         }), 









from flask import Blueprint, request, jsonify
import requests
from datetime import datetime, timedelta

pc_bp = Blueprint("power_conditioner", __name__)


def format_relay_statuses(relays):
    return ", ".join([
        f"{info.get('device_name', 'Unknown')} ({info.get('state', 'Unknown')})"
        for info in relays.values()
    ])


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def calculate_energy_saved(estimate_btu, consumption_kwh):
    consumption_watt = consumption_kwh * 1000
    return max(0.0, estimate_btu - consumption_watt)


def extract_yesterday_consumption_from_stat(stat, yesterday):
    if not isinstance(stat, dict):
        return 0.0

    direct_candidates = [
        stat.get("yesterday_consumption"),
        stat.get("yesterday_kwh"),
        stat.get("consumption_yesterday"),
    ]

    for val in direct_candidates:
        if val is not None:
            return _safe_float(val, 0.0)

    list_keys = ["power_usage", "daily_usage", "usage_history", "consumption_history"]
    fallback_value = None
    fallback_date = None

    for key in list_keys:
        records = stat.get(key, [])
        if not isinstance(records, list):
            continue

        for rec in records:
            if not isinstance(rec, dict):
                continue

            date_value = str(rec.get("date") or rec.get("day") or rec.get("log_date") or "").strip()[:10]

            consumption = _safe_float(
                rec.get(
                    "consumption",
                    rec.get(
                        "kwh",
                        rec.get(
                            "usage_kwh",
                            rec.get("total_consumption", rec.get("totalConsumption", 0.0))
                        ),
                    ),
                ),
                0.0,
            )

            if date_value == yesterday:
                return consumption

            try:
                rec_date = datetime.strptime(date_value, "%Y-%m-%d").date()
                y_date = datetime.strptime(yesterday, "%Y-%m-%d").date()

                if rec_date <= y_date and (fallback_date is None or rec_date > fallback_date):
                    fallback_date = rec_date
                    fallback_value = consumption
            except Exception:
                continue

    return fallback_value if fallback_value is not None else 0.0


def fetch_statistical_report(ip, headers, timeout=10):
    endpoints = [
        f"http://{ip}:5000/powerconditioner/statistical-report",
        f"http://{ip}:5000/statistical_report",
    ]

    last_error = None

    for url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            last_error = e

    raise last_error if last_error else Exception("Unable to fetch statistical report")


@pc_bp.route("/api/powerconditioner/onboard", methods=["POST"])
def onboard_power_conditioner():
    try:
        data = request.get_json(silent=True) or {}

        ip = data.get("ipAddress")
        serial = data.get("serialNumber")
        tenant_id = data.get("tenant_id")
        location = data.get("location")
        building = data.get("building", "N/A")
        floor = data.get("floor")
        room_name = data.get("room_name")
        make_name = data.get("make", "Vector")
        estimate_btu = _safe_float(data.get("estimateBTU", 0), 0.0)

        if not ip or not serial or not tenant_id:
            return jsonify({
                "success": False,
                "message": "ipAddress, serialNumber and tenant_id are required"
            }), 400

        headers = {"x-api-key": serial}

        stat = {}
        relays = {}
        relay_string = "Offline"
        active_relay_count = 0

        try:
            stat = fetch_statistical_report(ip, headers, timeout=10)

            outlet_response = requests.get(
                f"http://{ip}:5000/powerconditioner/outlet-status",
                headers=headers,
                timeout=10
            )
            outlet_response.raise_for_status()
            relays = outlet_response.json()

            if isinstance(relays, dict) and relays:
                formatted_relays = []
                sorted_keys = sorted(
                    relays.keys(),
                    key=lambda x: int(x.split('_')[1]) if '_' in x and x.split('_')[1].isdigit() else 0
                )

                for key in sorted_keys:
                    r_info = relays[key]
                    state = str(r_info.get("state", "off")).lower()
                    device_name = r_info.get("device_name", "Unknown")

                    formatted_relays.append(f"{device_name} ({state})")

                    if state == "on":
                        active_relay_count += 1

                relay_string = ", ".join(formatted_relays)

        except requests.exceptions.RequestException as e:
            return jsonify({
                "success": False,
                "message": f"Unable to reach Power Conditioner device: {str(e)}"
            }), 502

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_consumption = extract_yesterday_consumption_from_stat(stat, yesterday)
        energy_saved = calculate_energy_saved(estimate_btu, yesterday_consumption)

        hostname = stat.get("hostname", f"PC-{serial[-4:]}")
        model = stat.get("model", "VE-PC-G1")
        firmware = stat.get("firmware_version", "3.0")
        mac = stat.get("mac_address", "00:00:00:00:00:00")
        current_status = "Online" if active_relay_count > 0 else "Offline"
        unique_id = f"UID-{serial}"

        device_payload = {
            "unique_id": unique_id,
            "tenant_id": tenant_id,
            "hostname": hostname,
            "model": model,
            "firmware_version": firmware,
            "mac_address": mac,
            "relay_statuses": relay_string,
            "device_connected": active_relay_count,
            "current_status": current_status,
            "yesterday_consumption": yesterday_consumption,
            "estimate_btu": estimate_btu,
            "energy_saved": energy_saved,
            "ip_address": ip,
            "serial_number": serial,
            "location": location,
            "building": building,
            "floor": floor,
            "room_name": room_name,
            "make": make_name,
        }

        return jsonify({
            "success": True,
            "message": "Power Conditioner onboard data fetched successfully",
            "device": device_payload
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
