from flask import Blueprint, jsonify

from utils.state import EdgeState
 
device_bp = Blueprint('devices', __name__)
 
 
@device_bp.route('/', methods=['GET'])

def get_devices():

    """

    Returns device list cached from cloud.

    Cloud sends device list after edge registers.

    Edge stores it in EdgeState.

    """

    devices = EdgeState.get('devices', [])

    return jsonify({

        'devices': devices,

        'count':   len(devices),

        'online':  len([d for d in devices if d.get('status') == 'online']),

        'offline': len([d for d in devices if d.get('status') == 'offline']),

    })
 
 
@device_bp.route('/<int:device_id>', methods=['GET'])

def get_device(device_id):

    """Returns a single device by ID."""

    devices = EdgeState.get('devices', [])

    device = next(

        (d for d in devices if d.get('id') == device_id),

        None

    )

    if not device:

        return jsonify({'error': f'Device {device_id} not found'}), 404

    return jsonify(device)
 