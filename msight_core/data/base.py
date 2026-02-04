import os
import time
import json as _json
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Dict, List, Type, ClassVar, Tuple, Callable, TypeVar, get_origin, get_args, Optional
from .utils import BytesEncoder
from datetime import datetime
import msgpack as _msgpack

MSIGHT_EDGE_DEVICE_NAME = os.getenv("MSIGHT_EDGE_DEVICE_NAME")

T = TypeVar("T", bound="Data")

class FieldCodec:
    """Wrapper for per-field encode/decode functions.

    This helper class provides an encoder/decoder pair that can be attached to a
    dataclass field via the `__field_codecs__` mapping on a `Data` subclass, to customize serialization and deserialization of specific fields.

    Attributes:
        encode: Callable that converts a Python value into a JSON/msgpack-safe
            representation. If `context` is True the function will receive the
            parent object as a second argument.
        decode: Callable that converts an encoded value back into a Python
            object. If `context` is True the function will receive the raw
            payload (or parent) as a second argument.
        context: Whether encoder/decoder expect (value, context) instead of
            single-argument call signature.
    """
    def __init__(self, encode: Callable[[Any], Any], decode: Callable[[Any], Any], context: bool=False):
        """Create a FieldCodec.

        Args:
            encode: Function(value) or Function(value, context) that returns a
                serializable representation of ``value``.
            decode: Function(encoded) or Function(encoded, context) that
                returns the original Python value.
            context: If True, pass contextual information (parent object or
                payload) as a second argument to encode/decode.
        """
        self.encode = encode
        self.decode = decode
        self.context = context
# ----------------------------------------------------------------------
# Utilities for class <-> tag round-trip
# ----------------------------------------------------------------------

def get_class_path(cls: type) -> str:
    """Return the fully-qualified class path used as a type tag.

    The returned string is used as the ``data_type`` tag embedded in
    serialized payloads. It is intentionally the module + qualname so the
    tag remains stable even if the class is moved between modules during
    refactors.

    Args:
        cls: Class object to create a tag for.

    Returns:
        A string of the form ``{module}.{qualname}``.
    """
    return f"{cls.__module__}.{cls.__qualname__}"


def generate_frame_id() -> int:
    """Generate a unique frame identifier.

    Uses a Snowflake-like generator to produce monotonically-increasing 64-bit
    IDs suitable for frame identification across processes. The worker id is
    derived from the current process id to reduce collision probability when
    multiple processes are running on the same host.

    Returns:
        An integer representing a unique frame id.
    """
    from snowflake import SnowflakeGenerator
    worker_id = os.getpid() % 1024
    gen = SnowflakeGenerator(worker_id)
    return next(gen)


# ----------------------------------------------------------------------
# Base Data class with dataclass-based schema + codecs + registry
# ----------------------------------------------------------------------


@dataclass
class Data:
    """Base class for all serializable MSight messages.

    Responsibilities:
        - Provide generic ``to_dict`` / ``from_dict`` implementations that add a
          ``data_type`` tag, handle nested ``Data`` instances, and support
          per-field codecs via ``__field_codecs__``.
        - Provide convenience ``serialize`` / ``deserialize`` (MessagePack) and
          ``to_json`` / ``from_json`` helpers.
        - Maintain an in-memory registry mapping ``data_type`` -> class so
          deserialization uses fast dictionary lookup instead of dynamic
          imports.
    """

    # Global registry of all subclasses, keyed by data_type string
    __registry__: ClassVar[Dict[str, Type["Data"]]] = {}

    # Optional per-field codecs: name -> (encode_fn, decode_fn)
    # encode_fn: python_value -> JSON/msgpack-safe value
    # decode_fn: encoded_value -> python_value
    __field_codecs__: ClassVar[
        Dict[str, FieldCodec]
    ] = {}

    # Cached tag for this class; filled in automatically in __init_subclass__
    __data_type__: ClassVar[str]

    def __init_subclass__(cls, **kwargs):  # type: ignore[override]
        """Set up subclass metadata and merge field codecs.

        This hook runs when a subclass is created and performs two tasks:
        1. Compute and cache a ``__data_type__`` tag for the subclass and
           register it in ``Data.__registry__`` for fast lookup during
           deserialization.
        2. Merge ``__field_codecs__`` from base classes into the subclass so
           codecs defined on parents won't be overridden in default behavior.
        """
        super().__init_subclass__(**kwargs)
        tag = get_class_path(cls)
        cls.__data_type__ = tag
        Data.__registry__[tag] = cls

        # 2) Merge __field_codecs__ from base classes and subclass
        #    - Parent codecs first
        #    - Then subclass' own codecs override parents on key conflict
        merged = {}

        # Walk MRO from base to derived (excluding cls itself)
        for base in reversed(cls.__mro__[1:]):
            parent_codecs = getattr(base, "__field_codecs__", None)
            if parent_codecs:
                merged.update(parent_codecs)

        # Subclass-specific codecs defined directly on the class (if any)
        own_codecs = cls.__dict__.get("__field_codecs__", None)
        if own_codecs:
            merged.update(own_codecs)

        cls.__field_codecs__ = merged

    # ------------------------------------------------------------------
    # Dict <-> object conversion
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert this dataclass instance into a serializable dict.

        The resulting dict contains a ``data_type`` key that identifies the
        concrete subclass. Fields marked with a ``FieldCodec`` will be
        transformed by their encoder prior to recursive encoding.

        Returns:
            A dictionary suitable for JSON/MessagePack encoding.

        Raises:
            TypeError: If the instance is not a dataclass.
        """
        if not is_dataclass(self):
            raise TypeError(f"{self.__class__.__name__} must be a dataclass")

        result: Dict[str, Any] = {"data_type": self.__class__.__data_type__}

        for f in fields(self):
            name = f.name
            value = getattr(self, name)

            # Apply field-specific encoder if configured
            codec = self.__field_codecs__.get(name)
            if codec is not None:
                if codec.context:
                    value = codec.encode(value, self)
                else:
                    value = codec.encode(value)

            result[name] = self._encode_value(value)

        return result

    @classmethod
    def from_dict(cls: Type[T], payload: Dict[str, Any]) -> T:
        """Construct a Data instance (or subclass) from a dict payload.

        If called on the base ``Data`` class it will dispatch to the concrete
        subclass specified by the payload's ``data_type`` tag using the
        internal registry. When invoked on a concrete subclass it will
        instantiate that class, apply any per-field decode codecs, and
        recursively decode nested structures.

        Args:
            payload: A dictionary produced by ``to_dict`` or an equivalent
                source.

        Returns:
            An instance of ``cls`` (or the dispatched subclass for calls on ``Data``).

        Raises:
            TypeError: If ``payload`` is not a dict.
            ValueError: If ``data_type`` key is missing in the payload dict or unknown when dispatching
                from the base ``Data`` class.
        """
        if not isinstance(payload, dict):
            raise TypeError(f"Expected dict, got {type(payload)!r}")

        if cls is Data or cls is SensorData:
            tag = payload.get("data_type")
            if not tag:
                raise ValueError("Missing 'data_type' in payload")
            subcls = Data.__registry__.get(tag)
            if subcls is None:
                raise ValueError(f"Unknown data_type {tag!r}")
            return subcls.from_dict(payload)  # type: ignore[return-value]

        if not is_dataclass(cls):
            raise TypeError(f"{cls.__name__} must be a dataclass")

        kwargs: Dict[str, Any] = {}

        for f in fields(cls):
            name = f.name
            if name not in payload:
                # leave it to dataclass default / default_factory
                continue

            raw_value = payload[name]
            # value = cls._decode_field(name, raw_value, f.type)
            codec = cls.__field_codecs__.get(name)
            if codec is not None:
                if codec.context:
                    value = codec.decode(raw_value, payload)
                else:
                    value = codec.decode(raw_value)
            else:
                value = raw_value
            value = cls._decode_value(value, f.type)
            kwargs[name] = value

        return cls(**kwargs)  # type: ignore[call-arg]

    # ------------------------------------------------------------------
    # Helpers for nested / typed decoding
    # ------------------------------------------------------------------

    @classmethod
    def _decode_value(cls, value: Any, typ: Any) -> Any:
        """Decode a value according to the expected typing annotation.

        This is a recursive helper that handles typing constructs such as ``List[T]`` and
        ``Dict[K, V]`` and will recursively reconstruct nested ``Data``
        instances from their dict representations.

        Args:
            value: The raw decoded value (e.g. from JSON/msgpack).
            typ: The expected typing annotation for the value.

        Returns:
            The decoded Python object matching ``typ``.
        """
        if value is None:
            return None

        origin = get_origin(typ)
        args = get_args(typ)

        # List[...] handling
        if origin is list and args:
            inner = args[0]
            return [cls._decode_value(v, inner) for v in value]

        # Dict[KT, VT] handling
        if origin is dict and args and isinstance(value, dict):
            k_t, v_t = args
            return {
                cls._decode_value(k, k_t): cls._decode_value(v, v_t)
                for k, v in value.items()
            }

        # Nested Data encoded as dict with data_type
        if isinstance(value, dict) and "data_type" in value:
            return Data.from_dict(value)

        # Fallback: primitive or unannotated type
        return value

    @classmethod
    def _encode_value(cls, value: Any) -> Any:
        """Recursively encode Python values into serializable containers.

        - ``Data`` instances become dicts via ``to_dict``.
        - Lists/dicts are processed recursively.
        - Primitive values are returned unchanged.

        Args:
            value: The Python value to encode.

        Returns:
            A JSON/MessagePack-safe representation of ``value``.
        """
        if isinstance(value, Data):
            return value.to_dict()
        if isinstance(value, list):
            return [cls._encode_value(v) for v in value]
        if isinstance(value, dict):
            return {k: cls._encode_value(v) for k, v in value.items()}
        return value

    # ------------------------------------------------------------------
    # Convenience serialization helpers
    # ------------------------------------------------------------------

    def serialize(self) -> bytes:
        """Serialize this object to MessagePack bytes.

        Internally calls :meth:`to_dict` and packs the result using
        ``msgpack.packb`` with ``use_bin_type=True``.

        Returns:
            Bytes containing the MessagePack-encoded representation.
        """
        return _msgpack.packb(self.to_dict(), use_bin_type=True)

    @classmethod
    def deserialize(cls: Type[T], data: bytes) -> T:
        """Deserialize MessagePack bytes into a ``Data`` instance.

        Args:
            data: MessagePack-encoded bytes representing a serialized
                ``Data`` object.

        Returns:
            A concrete ``Data`` subclass instance reconstructed from the payload.
        """
        payload = _msgpack.unpackb(data, raw=False)
        return Data.from_dict(payload)  # type: ignore[return-value]

    def to_json(self) -> str:
        """Convert this object to a JSON string.

        Uses ``to_dict`` and a custom ``BytesEncoder`` to ensure byte
        sequences are JSON serializable.

        Returns:
            A JSON string.
        """
        return _json.dumps(self.to_dict(), cls=BytesEncoder)

    @classmethod
    def from_json(cls: Type[T], data: str) -> T:
        """Create a ``Data`` instance from a JSON string.

        Args:
            data: JSON string produced by :meth:`to_json` or an equivalent
                source.

        Returns:
            A concrete ``Data`` instance.
        """
        payload = _json.loads(data)
        return Data.from_dict(payload)  # type: ignore[return-value]


# ----------------------------------------------------------------------
# SensorData and concrete examples
# ----------------------------------------------------------------------


@dataclass(kw_only=True)
class SensorData(Data):
    """Base class for sensor data messages.

    Shared fields across all sensor payloads.

    Attributes:
        sensor_name (Optional[str]): Identifier for the sensor that produced
            the measurement (e.g. camera or lidar name).
        capture_timestamp (float): POSIX timestamp (seconds, float) when the
            sensor actually captured the measurement. Defaults to the current
            time via ``time.time()``.
        creation_timestamp (float): POSIX timestamp (seconds, float) when the
            sensor data object was created. Defaults to the current time via
            ``time.time()`` and normally should not be set manually.
        frame_id (int): Monotonically-increasing numeric id generated by
            :func:`generate_frame_id` (Snowflake-like). Useful to correlate
            frames across messages and processes. Defaults to a new id at
            creation time.
        device_name (Optional[str]): Logical name of the device producing the
            data. Read from the ``MSIGHT_EDGE_DEVICE_NAME`` environment
            variable at module import time; Normally should not be set manually.
    """

    sensor_name: Optional[str] = None
    capture_timestamp: float = field(default_factory=time.time)
    creation_timestamp: float = field(default_factory=time.time)
    frame_id: int = field(default_factory=generate_frame_id)
    device_name: Optional[str] = MSIGHT_EDGE_DEVICE_NAME

    @property
    def time(self) -> str:
        """ISO 8601 formatted capture timestamp."""
        return datetime.fromtimestamp(self.capture_timestamp).isoformat()
    
    @property
    def capture_time(self) -> str:
        """ISO 8601 formatted capture timestamp. The same as `time`."""
        return datetime.fromtimestamp(self.capture_timestamp).isoformat()

    @property
    def creation_time(self) -> str:
        """ISO 8601 formatted creation timestamp."""
        return datetime.fromtimestamp(self.creation_timestamp).isoformat()


@dataclass
class SensorDataSequence(SensorData):
    """A sequence container for sensor messages.

    The ``obj_list`` field may contain heterogeneous ``Data`` subclasses,
    allowing sequences of mixed message types.
    """

    obj_list: List[Data] = field(default_factory=list)



