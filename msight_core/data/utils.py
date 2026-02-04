import base64
import json

class BytesEncoder(json.JSONEncoder):
    """JSON encoder that converts bytes to Base64 ASCII strings.

    This encoder can be passed to ``json.dumps`` via the ``cls`` argument to
    automatically encode ``bytes`` objects as Base64-encoded ASCII strings.

    Example:
        json.dumps({'b': b'\x00\x01'}, cls=BytesEncoder)

    Note:
        The decoder must explicitly base64-decode the string to recover the
        original bytes (e.g. ``base64.b64decode(value)``).
    """
    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode(
                "ascii"
            )  # Encode bytes in Base64 and decode to string
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

