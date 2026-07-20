import time

from flask import Blueprint, jsonify, request, current_app

from services.command_executor import CommandExecutor
 
command_bp  = Blueprint('commands', __name__)

executor    = CommandExecutor()
 
 
@command_bp.route('/test/', methods=['POST'])

def test_command():

    """

    LOCAL TEST ONLY — lets you manually test a raw command

    without going through the cloud.
 
    Use this to verify a device is reachable and responding

    before connecting to the cloud.
 
    Example request body:

    {

        "command_id": "test_001",

        "device_id": 1,

        "device_name": "Main Display",

        "connection": {

            "protocol": "tcp",

            "ip_address": "192.168.1.10",

            "port": 1515,

            "timeout": 5,

            "expect_response": true

        },

        "payload": {

            "type": "hex",

            "data": "AA 11 01 00 11"

        }

    }

    """

    data = request.get_json()
 
    if not data:

        return jsonify({'error': 'No JSON body provided'}), 400
 
    # Validate required fields

    required = ['connection', 'payload']

    missing  = [f for f in required if f not in data]

    if missing:

        return jsonify({

            'error': f'Missing required fields: {missing}'

        }), 400
 
    # Add test command_id if not provided

    if 'command_id' not in data:

        data['command_id'] = f"test_{int(time.time())}"
 
    result = executor.execute(data)
 
    return jsonify({

        'success':    result.get('status') == 'success',

        'command_id': result.get('command_id'),

        'status':     result.get('status'),

        'result':     result.get('result'),

        'error':      result.get('error'),

        'timestamp':  time.time()

    })
 