import socket

import logging
 
logger = logging.getLogger(__name__)
 
 
class TCPExecutor:

    """

    Sends raw bytes to a device over TCP.

    No device knowledge — just send and receive bytes.

    The cloud decides what bytes to send.

    """
 
    def execute(self, connection: dict, payload: dict) -> dict:

        ip = connection['ip_address']

        port = connection['port']

        timeout = connection.get('timeout', 5)

        expect_response = connection.get('expect_response', True)
 
        # Build bytes from payload

        raw_bytes = self._build_bytes(payload)
 
        logger.info(f"TCP → {ip}:{port} | bytes: {raw_bytes.hex()}")
 
        try:

            with socket.socket(

                socket.AF_INET, socket.SOCK_STREAM

            ) as s:

                s.settimeout(timeout)

                s.connect((ip, port))

                s.sendall(raw_bytes)
 
                response_hex = ''

                if expect_response:

                    response = s.recv(1024)

                    response_hex = response.hex()

                    logger.info(f"TCP ← {ip}:{port} | response: {response_hex}")
 
            return {

                'success': True,

                'ip': ip,

                'port': port,

                'sent_bytes': raw_bytes.hex(),

                'response': response_hex

            }
 
        except socket.timeout:

            logger.warning(f"TCP timeout → {ip}:{port}")

            return {

                'success': False,

                'error': 'timeout',

                'ip': ip,

                'port': port

            }
 
        except ConnectionRefusedError:

            logger.warning(f"TCP connection refused → {ip}:{port}")

            return {

                'success': False,

                'error': 'connection_refused',

                'ip': ip,

                'port': port

            }
 
        except Exception as e:

            logger.error(f"TCP error → {ip}:{port} | {e}")

            return {

                'success': False,

                'error': str(e),

                'ip': ip,

                'port': port

            }
 
    def _build_bytes(self, payload: dict) -> bytes:

        payload_type = payload.get('type', 'hex')
 
        if payload_type == 'hex':

            # Example: "AA 11 01 01 01 14" or "AA110101011400"

            hex_str = payload['data'].replace(' ', '')

            return bytes.fromhex(hex_str)
 
        elif payload_type == 'ascii':

            # Example: "PON\r\n"

            return payload['data'].encode('ascii')
 
        elif payload_type == 'bytes':

            # Example: [170, 17, 1, 1, 1, 20]

            return bytes(payload['data'])
 
        else:

            raise ValueError(f"Unknown payload type: {payload_type}")
 