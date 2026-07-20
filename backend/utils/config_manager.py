import os
import json

CONFIG_FILE = "/app/config/runtime_config.json"


def save_runtime_config(cloud_url, api_key, tenant_id="", device_name="EdgeCollector"):
    os.makedirs("/app/config", exist_ok=True)

    data = {
        "cloud_url": cloud_url,
        "api_key": api_key,
        "tenant_id": tenant_id,
        "device_name": device_name,
        "onboarded": True
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_runtime_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)