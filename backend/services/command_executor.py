import logging

from executors.tcp_executor import TCPExecutor

from executors.http_executor import HTTPExecutor

from executors.serial_executor import SerialExecutor
 
logger = logging.getLogger(__name__)
 
# Map protocol name → executor class

EXECUTORS = {

    'tcp':    TCPExecutor,

    'http':   HTTPExecutor,

    'https':  HTTPExecutor,

    'serial': SerialExecutor,

    'rs232':  SerialExecutor,

}
 
 
class CommandExecutor:

    """

    Receives a command packet from the cloud.

    Looks at the protocol field.

    Routes to the correct executor.

    Returns the result back to cloud.
 
    The edge does NOT know what device it is.

    The edge does NOT know what the command means.

    It just sends bytes and returns the response.

    """
 
    def execute(self, command_packet: dict) -> dict:

        command_id  = command_packet.get('command_id', 'unknown')

        device_id   = command_packet.get('device_id')

        device_name = command_packet.get('device_name', 'Unknown Device')

        connection  = command_packet.get('connection', {})

        payload     = command_packet.get('payload', {})

        protocol    = connection.get('protocol', 'tcp').lower()
 
        logger.info(

            f"Executing command [{command_id}] "

            f"on device [{device_name}] "

            f"via [{protocol}]"

        )
 
        # Find the right executor

        executor_class = EXECUTORS.get(protocol)
 
        if not executor_class:

            logger.error(f"Unknown protocol: {protocol}")

            return {

                'command_id': command_id,

                'device_id':  device_id,

                'status':     'failed',

                'error':      f"Unknown protocol: {protocol}",

                'result':     None

            }
 
        # Execute the command

        try:

            executor = executor_class()

            result   = executor.execute(connection, payload)
 
            status = 'success' if result.get('success') else 'failed'
 
            logger.info(

                f"Command [{command_id}] → {status}"

            )
 
            return {

                'command_id': command_id,

                'device_id':  device_id,

                'status':     status,

                'error':      result.get('error'),

                'result':     result

            }
 
        except Exception as e:

            logger.error(

                f"Command [{command_id}] crashed: {e}"

            )

            return {

                'command_id': command_id,

                'device_id':  device_id,

                'status':     'failed',

                'error':      str(e),

                'result':     None

            }
 