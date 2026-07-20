"""
Manual Platform Plugin SDK
==========================
Package for manual platform plugins (Samsung MDC, Q-SYS, etc.)
"""

import os
import pkgutil
import importlib
import inspect
import logging

from .base import ManualPlatformPlugin

logger = logging.getLogger(__name__)

# Plugin registry (populated dynamically)
PLUGIN_REGISTRY = {}

def discover_plugins():
    """Dynamically discover and register all plugin classes in this package."""
    global PLUGIN_REGISTRY
    PLUGIN_REGISTRY = {}
    
    plugin_dir = os.path.dirname(__file__)
    
    # Use pkgutil to find modules in the current directory and subdirectories
    for loader, module_name, is_pkg in pkgutil.walk_packages([plugin_dir]):
        if module_name in ["base", "__init__"]:
            continue
            
        try:
            # Import the module relative to this package
            module = importlib.import_module(f".{module_name}", package=__package__)
            
            # Find all classes that inherit from ManualPlatformPlugin
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, ManualPlatformPlugin) and 
                    obj is not ManualPlatformPlugin):
                    
                    # Use the 'name' attribute of the plugin class as the registry key
                    # Fallback to module name if 'name' attribute is missing
                    plugin_key = getattr(obj, "name", module_name.replace("_plugin", ""))
                    
                    if plugin_key in PLUGIN_REGISTRY:
                        logger.debug(f"Overwriting plugin registry key '{plugin_key}' with {obj.__name__} from {module_name}")
                    
                    PLUGIN_REGISTRY[plugin_key] = obj
                    logger.debug(f"Registered plugin: {plugin_key} -> {obj.__name__}")
                    
        except Exception as e:
            logger.error(f"Failed to load plugin module {module_name}: {e}")

# Initial discovery
discover_plugins()
logger.info(f"Loaded {len(PLUGIN_REGISTRY)} plugins: {', '.join(sorted(PLUGIN_REGISTRY.keys()))}")

def get_plugin(plugin_name, config=None):
    """Get plugin instance by name."""
    plugin_class = PLUGIN_REGISTRY.get(plugin_name)
    if plugin_class:
        plugin = plugin_class(config)
        _wrap_plugin_device_info(plugin)
        return plugin
    return None

def get_available_plugins():
    """Get list of available plugins with metadata."""
    plugins = []
    for name, plugin_class in PLUGIN_REGISTRY.items():
        try:
            instance = plugin_class()
            plugins.append({
                "name": getattr(instance, "name", name),
                "display_name": getattr(instance, "display_name", name),
                "description": getattr(instance, "description", ""),
                "supports_display_id": getattr(instance, "supports_display_id", True),
                "supports_port": getattr(instance, "supports_port", True),
                "default_port": getattr(instance, "default_port", 1515),
                "supported_models": getattr(instance, "SUPPORTED_MODELS", []),
            })
        except Exception as e:
            logger.error(f"Failed to instantiate plugin {name} for metadata: {e}")
    return plugins

def _normalize_device_info(info, ip, port, display_id, plugin):
    """Ensure device info always includes name/model/status with safe defaults."""
    if info is None:
        info = {}

    info.setdefault("ip_address", ip)
    info.setdefault("port", port)
    info.setdefault("display_id", display_id)

    make = info.get("make") or getattr(plugin, "display_name", None) or "Unknown"
    info["make"] = make

    model = info.get("model") or "Unknown"
    info["model"] = model

    device_name = info.get("device_name")
    if not device_name:
        if make and model and model != "Unknown":
            device_name = f"{make} {model}"
        elif make and make != "Unknown":
            device_name = f"{make} Device"
        else:
            device_name = f"Device {ip}"
    info["device_name"] = device_name

    if not info.get("serial_number") and info.get("mac_address"):
        info["serial_number"] = info.get("mac_address")

    if "current_status" not in info or not info.get("current_status"):
        reachable = info.get("reachable")
        if reachable is True:
            info["current_status"] = "Online"
        elif reachable is False:
            info["current_status"] = "Offline"
        else:
            info["current_status"] = "Unknown"

    return info

def _wrap_plugin_device_info(plugin):
    """Wrap plugin.get_device_info to enforce normalized output."""
    if hasattr(plugin, "_device_info_wrapped") and plugin._device_info_wrapped:
        return

    original = getattr(plugin, "get_device_info", None)
    if not callable(original):
        return

    def _wrapped_get_device_info(ip, port=None, display_id=None):
        info = original(ip, port, display_id)
        return _normalize_device_info(info, ip, port, display_id, plugin)

    plugin.get_device_info = _wrapped_get_device_info
    plugin._device_info_wrapped = True

__all__ = [
    "ManualPlatformPlugin",
    "PLUGIN_REGISTRY",
    "get_plugin",
    "get_available_plugins",
    "discover_plugins"
]
