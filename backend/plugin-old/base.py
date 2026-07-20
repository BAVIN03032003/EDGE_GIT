"""
Manual Platform Plugin SDK - Base
"""

import socket
from abc import ABC, abstractmethod


class ManualPlatformPlugin(ABC):
    """Base class for manual platform plugins"""
    
    name = "base"
    display_name = "Base Plugin"
    description = "Base plugin"
    supports_port = True
    default_port = 1515
    
    # Default commands
    COMMANDS = {}
    QUERY_COMMANDS = {}
    
    def __init__(self, config=None):
        self.config = config or {}
        self.timeout = self.config.get('timeout', 5)
    
    @abstractmethod
    def get_device_info(self, ip, port, display_id):
        """Get device information"""
        pass
    
    @abstractmethod
    def send_command(self, ip, port, display_id, command):
        """Send command to device"""
        pass
    
    @abstractmethod
    def query_status(self, ip, port, display_id):
        """Query device status"""
        pass
    
    def connect(self, ip, port):
        """Create socket connection"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((ip, port))
        return sock
    
    def build_command(self, display_id, cmd_byte, data_byte=0x00):
        """Build Samsung MDC command packet"""
        # AA [ID] FE [Length] [Cmd] [Data] [Check]
        packet = bytes([
            0xAA,
            int(display_id, 16) if isinstance(display_id, str) else display_id,
            0xFE,
            0x01,  # Length
            cmd_byte,
            data_byte
        ])
        return packet
    
    def send_raw(self, ip, port, data):
        """Send raw bytes to device"""
        try:
            sock = self.connect(ip, port)
            sock.sendall(data)
            sock.close()
            return True, "Command sent"
        except Exception as e:
            return False, str(e)
    
    def receive_response(self, ip, port, timeout=3):
        """Receive response from device"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))
            data = sock.recv(64)
            sock.close()
            return True, data
        except Exception as e:
            return False, str(e)
