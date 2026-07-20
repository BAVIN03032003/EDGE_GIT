import time
 
import platform
 
import psutil
 
from flask import Blueprint, jsonify
 
from utils.state import EdgeState
 
status_bp = Blueprint('status', __name__)
 
 
@status_bp.route('/', methods=['GET'])
 
def get_status():
 
    """
 
    Returns full system status.
 
    Used by Dashboard page to show:
 
    - Cloud connection status
 
    - CPU / Memory / Disk usage
 
    - Device list
 
    - Edge info
 
    """
 
    disk = psutil.disk_usage('/' if platform.system() != 'Windows' else 'C:\\')
 
    return jsonify({
 
        'cloud_connected': EdgeState.get('cloud_connected', False),
 
        'edge_id':         EdgeState.get('edge_id'),
 
        'edge_name':       EdgeState.get('edge_name'),
 
        'registered':      EdgeState.get('registered', False),
 
        'cloud_url':       EdgeState.get('cloud_url', ''),
 
        'devices':         EdgeState.get('devices', []),
 
        'system': {
 
            'cpu_percent':    psutil.cpu_percent(interval=1),
 
            'memory_percent': psutil.virtual_memory().percent,
 
            'memory_total_gb': round(
 
                psutil.virtual_memory().total / (1024 ** 3), 2
 
            ),
 
            'disk_percent':   disk.percent,
 
            'uptime_seconds': int(time.time() - psutil.boot_time()),
 
            'os':             platform.system(),
 
            'os_version':     platform.version(),
 
            'hostname':       platform.node(),
 
            'cpu_count':      psutil.cpu_count(),
 
        },
 
        'timestamp': time.time()
 
    })
 
 