import requests

import logging
 
logger = logging.getLogger(__name__)
 
 
class HTTPExecutor:

    """

    Sends HTTP request to a device (REST API devices).

    No device knowledge — cloud provides the full URL,

    method, headers and body.

    """
 
    def execute(self, connection: dict, payload: dict) -> dict:

        ip = connection['ip_address']

        port = connection.get('port', 80)

        timeout = connection.get('timeout', 5)
 
        method = payload.get('method', 'GET').upper()

        path = payload.get('path', '/')

        headers = payload.get('headers', {})

        body = payload.get('body', None)
 
        scheme = 'https' if port == 443 else 'http'

        url = f"{scheme}://{ip}:{port}{path}"
 
        logger.info(f"HTTP {method} → {url}")
 
        try:

            response = requests.request(

                method=method,

                url=url,

                headers=headers,

                json=body if isinstance(body, dict) else None,

                data=body if isinstance(body, str) else None,

                timeout=timeout,

                verify=False  # Allow self-signed certs on devices

            )
 
            logger.info(f"HTTP ← {url} | status: {response.status_code}")
 
            return {

                'success': True,

                'status_code': response.status_code,

                'url': url,

                'response': response.text[:500]  # Limit response size

            }
 
        except requests.Timeout:

            logger.warning(f"HTTP timeout → {url}")

            return {'success': False, 'error': 'timeout', 'url': url}
 
        except requests.ConnectionError:

            logger.warning(f"HTTP connection error → {url}")

            return {'success': False, 'error': 'connection_error', 'url': url}
 
        except Exception as e:

            logger.error(f"HTTP error → {url} | {e}")

            return {'success': False, 'error': str(e), 'url': url}
 