"""Module defining lightweight container for raw byte sensor payloads.

This module provides ``BytesData``, a small convenience subclass of
:class:`SensorData` that carries an opaque ``bytes`` payload. It is useful
for representing binary sensor frames such as compressed images or raw
lidar packets while retaining the shared sensor metadata (capture_timestamps,
frame id, device name) provided by :class:`SensorData`.
"""

from .base import SensorData
from dataclasses import dataclass, field


@dataclass
class BytesData(SensorData):
    """Container for binary sensor payloads.

    This dataclass stores an opaque ``bytes`` payload together with the
    standard sensor metadata inherited from :class:`SensorData`.

    Attributes:
        data (bytes): Binary payload (e.g. compressed image or raw packet).
    """

    data: bytes = field(repr=False)

