"""Point-cloud data container and helpers.

This module provides container for structured NumPy point-cloud
arrays and helpers to (de)serialize the array dtype/shape and compress the
binary payload. The class ``PointCloudData`` extends
:class:`~msight_core.data.SensorData` and registers per-field codecs to
allow efficient MessagePack/JSON encoding of large point-cloud buffers.

The serialization strategy is:

- ``dtype`` header: JSON-encoded metadata describing the structured dtype
  (names, formats, offsets, itemsize) and the array "shape". This header is
  small and is stored as UTF-8 bytes.
- ``points`` payload: raw bytes of the array compressed with Zstandard.

The module exposes the following utilities and codecs that are referenced by
``PointCloudData.__field_codecs__``:

- ``dtype_codec``: FieldCodec responsible for packing/unpacking dtype header.
- ``point_cloud_codec``: FieldCodec responsible for (de)compressing the
  points buffer.
"""

import numpy as np
import time
import json
import zstandard as zstd
from typing import Optional
from dataclasses import dataclass, field
from .base import SensorData, FieldCodec

def pack_dtype(dt: np.dtype, data: "PointCloudData") -> bytes:
    """Serialize the structured dtype and shape into a JSON bytes header.

    This function is intended to be used as the ``encode`` callable for a
    :class:`~msight_core.data.FieldCodec` and therefore accepts the
    ``dt`` / ``data`` signature. The function reads the structured numpy
    ``points`` array from ``data`` and returns a small JSON header describing
    the array layout.

    Args:
        dt: Unused; present for FieldCodec call signature compatibility.
        data: An object with a ``points`` attribute containing a structured
            NumPy array (e.g. :class:`PointCloudData`).

    Returns:
        bytes: UTF-8 encoded JSON describing names, formats, offsets,
        shape and itemsize of the structured array.
    """
    arr = data.points
    if arr.dtype.fields is None:
        raise TypeError("Expected a structured array with named fields.")
    names = list(arr.dtype.names)                     # preserves '' if present
    formats = [arr.dtype.fields[n][0].str for n in names]   # includes endianness, kind, size
    offsets = [arr.dtype.fields[n][1] for n in names]
    header = {
        "shape": arr.shape,
        "names": names,
        "formats": formats,
        "offsets": offsets,
        "itemsize": arr.dtype.itemsize,
    }
    header_bytes = json.dumps(header).encode("utf-8")
    return header_bytes

def unpack_dtype(buf: bytes, payload: dict) -> np.ndarray:
    """Reconstruct a NumPy dtype from the previously packed JSON header.

    Args:
        buf: UTF-8 encoded JSON header created by :func:`pack_dtype`.
        payload: Optional context payload provided by the FieldCodec
            (not used here).

    Returns:
        np.dtype: A NumPy dtype object that matches the original structured
        array layout.
    """
    header = json.loads(buf.decode("utf-8"))
    dt = np.dtype({
        "names": header["names"],
        "formats": header["formats"],
        "offsets": header["offsets"],
        "itemsize": header["itemsize"],
    })
    
    return dt


dtype_codec = FieldCodec(
    encode=pack_dtype,
    decode=unpack_dtype,
    context=True,
)

def compress_pointcloud(points: np.ndarray, data: "PointCloudData") -> bytes:
    """Compress a NumPy array's raw bytes using Zstandard.

    This function is used as the ``encode`` callable for ``point_cloud_codec``
    and expects ``points`` to be a NumPy array. The compression level is
    read from ``data.compress_level`` which allows per-instance tuning.

    Args:
        points (np.ndarray): NumPy array to compress (the function will call ``tobytes()``).
        data (PointCloudData): The PointCloudData instance; used to read compression parameters.

    Returns:
        bytes: Zstandard-compressed bytes of the array payload.
    """
    points_bytes = points.tobytes(order="C")
    # print(f"Compressing point cloud data of size {len(points_bytes)} bytes")
    cctx = zstd.ZstdCompressor(data.compress_level) if hasattr(data, 'compress_level') else zstd.ZstdCompressor()
    points = cctx.compress(points_bytes)
    return points

def decompress_pointcloud(compressed_points: bytes, data: dict) -> np.ndarray:
    """Decompress Zstandard bytes and reconstruct a NumPy array.

    The function expects the caller to provide enough context to reconstruct
    the array shape and dtype (typically via the companion ``dtype`` header
    that is decoded separately).

    Args:
        compressed_points: Compressed bytes produced by :func:`compress_pointcloud`.
        data: Context data containing ``dtype`` and ``shape`` keys to
            reconstruct the NumPy array.

    Returns:
        np.ndarray: The reconstructed NumPy array.
    """
    dctx = zstd.ZstdDecompressor()
    points_bytes = dctx.decompress(compressed_points)
    points = np.frombuffer(points_bytes, dtype=unpack_dtype(data['dtype'], None)).reshape(data['shape'])
    return points

point_cloud_codec = FieldCodec(
    encode=compress_pointcloud,
    decode=decompress_pointcloud,
    context=True,
)

@dataclass
class PointCloudData(SensorData):
    """Container for structured point-cloud arrays.

    Fields
    ------
    points: np.ndarray
        A NumPy structured array containing per-point fields (e.g. x, y, z,
        intensity). The array is large and therefore is excluded from the
        ``repr`` to avoid huge console prints.

    shape: Optional[tuple]
        The shape of the array (kept in sync with ``points.shape``).

    dtype: Optional[np.dtype]
        The NumPy dtype describing the structure of ``points``. When
        serializing, the dtype is converted to a compact JSON header via
        :func:`pack_dtype`.

    compress_level: int
        Zstandard compression level used when encoding the raw bytes. Higher
        numbers increase compression ratio at the cost of CPU.

    Notes
    -----
    The class registers two field codecs via ``__field_codecs__``:

    - ``points`` uses :data:`point_cloud_codec` to compress/decompress the
      raw bytes.
    - ``dtype`` uses :data:`dtype_codec` to emit the structured-dtype header.

    Use :meth:`from_ndarray` to create instances from an existing NumPy array
    and rely on automatic shape/dtype synchronization performed in
    ``__post_init__``.
    """
    points: np.ndarray = field(repr=False)
    shape: Optional[tuple] = field(default=None)
    dtype: Optional[np.dtype] = field(default=None)
    compress_level: int = field(default=3)
    
    __field_codecs__ = {
        "points": point_cloud_codec,
        "dtype": dtype_codec,
    }

    def __post_init__(self):
        # Ensure shape and dtype are always consistent with points
        if self.points is not None:
            self.shape = self.points.shape
            self.dtype = self.points.dtype

    @classmethod
    def from_ndarray(
        cls,
        points: np.ndarray,
        sensor_name: str,
        capture_timestamp: str = None, 
        creation_timestamp: str = None,
        compress_level=3, # compression level is used when convert to dict and convert back
    ):
        """Create a PointCloudData from a NumPy array.

        Args:
            points(np.ndarray): Structured NumPy array containing point-cloud data.
            sensor_name (str): Name of the sensor producing the data.
            capture_timestamp (float, optional): Optional capture timestamp (defaults to now).
            creation_timestamp (float, optional): Optional creation timestamp (defaults to now).
            compress_level (int, optional): Zstandard compression level to use on encoding.

        Returns:
            PointCloudData (PointCloudData): Initialized dataclass instance.
        """
        if capture_timestamp is None:
            capture_timestamp = time.time()
        if creation_timestamp is None:
            creation_timestamp = time.time()
        return cls(
            sensor_name=sensor_name,
            points=points,
            capture_timestamp=capture_timestamp,
            compress_level=compress_level,
            creation_timestamp=creation_timestamp,
        )


