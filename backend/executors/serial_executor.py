import logging
 
logger = logging.getLogger(__name__)
 
 
class SerialExecutor:

    """

    Sends bytes over RS232/serial (COM port).

    Used for older AV devices that use serial control.

    Cloud provides the COM port, baud rate and bytes to send.

    """
 
    def execute(self, connection: dict, payload: dict) -> dict:

        try:

            import serial

        except ImportError:

            return {

                'success': False,

                'error': 'pyserial not installed. Run: pip install pyserial'

            }
 
        com_port = connection.get('com_port', 'COM1')

        baud_rate = connection.get('baud_rate', 9600)

        timeout = connection.get('timeout', 3)

        expect_response = connection.get('expect_response', True)
 
        raw_bytes = self._build_bytes(payload)
 
        logger.info(f"Serial → {com_port} @ {baud_rate} baud | bytes: {raw_bytes.hex()}")
 
        try:

            with serial.Serial(

                port=com_port,

                baudrate=baud_rate,

                timeout=timeout

            ) as ser:

                ser.write(raw_bytes)
 
                response_hex = ''

                if expect_response:

                    response = ser.read(1024)

                    response_hex = response.hex()
 
            return {

                'success': True,

                'com_port': com_port,

                'sent_bytes': raw_bytes.hex(),

                'response': response_hex

            }
 
        except Exception as e:

            logger.error(f"Serial error → {com_port} | {e}")

            return {

                'success': False,

                'error': str(e),

                'com_port': com_port

            }
 
    def _build_bytes(self, payload: dict) -> bytes:

        payload_type = payload.get('type', 'hex')

        if payload_type == 'hex':

            return bytes.fromhex(payload['data'].replace(' ', ''))

        elif payload_type == 'ascii':

            return payload['data'].encode('ascii')

        elif payload_type == 'bytes':

            return bytes(payload['data'])

        else:

            raise ValueError(f"Unknown payload type: {payload_type}")
 