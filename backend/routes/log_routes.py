import os

from flask import Blueprint, jsonify, request
 
log_bp   = Blueprint('logs', __name__)

LOG_FILE = os.path.join(

    os.path.dirname(__file__), '../../logs/edge-collector.log'

)
 
 
@log_bp.route('/', methods=['GET'])

def get_logs():

    """

    Returns recent log entries.

    Supports filtering by level: INFO, WARNING, ERROR, DEBUG

    Supports limiting number of lines returned.

    """

    lines = int(request.args.get('lines', 100))

    level = request.args.get('level', 'ALL').upper()
 
    if not os.path.exists(LOG_FILE):

        return jsonify({'logs': [], 'total': 0})
 
    with open(LOG_FILE, 'r') as f:

        all_lines = f.readlines()
 
    # Filter by level if requested

    if level != 'ALL':

        all_lines = [

            line for line in all_lines

            if f'[{level}]' in line

        ]
 
    # Take last N lines

    recent = all_lines[-lines:]
 
    # Parse each log line into structured format

    parsed = []

    for line in recent:

        parts = line.strip().split(' ', 3)

        parsed.append({

            'timestamp': f"{parts[0]} {parts[1]}" if len(parts) > 1 else '',

            'level':     parts[2].strip('[]') if len(parts) > 2 else 'INFO',

            'message':   parts[3] if len(parts) > 3 else line.strip()

        })
 
    # Return newest first

    return jsonify({

        'logs':  list(reversed(parsed)),

        'total': len(all_lines)

    })
 