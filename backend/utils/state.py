import threading
 
_state = {}

_lock = threading.Lock()
 
 
class EdgeState:

    """

    Thread-safe shared memory.

    Used by CloudConnector, CommandExecutor, and Flask routes

    to share live data without conflicts.

    """
 
    @staticmethod

    def set(key: str, value):

        with _lock:

            _state[key] = value
 
    @staticmethod

    def get(key: str, default=None):

        with _lock:

            return _state.get(key, default)
 
    @staticmethod

    def get_all() -> dict:

        with _lock:

            return dict(_state)
 