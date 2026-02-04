"""Data containers for various sensor data types.

- :class:`~msight_core.data.Data` — Base class for all data containers. Handles
  registration, serialization to/from dict/msgpack/JSON, and per-field codecs.

- :class:`~msight_core.data.SensorData` — Extends :class:`~msight_core.data.Data`
  with common sensor fields such as ``sensor_name``, ``capture_timestamp``,,
  ``creation_timestamp``, ``frame_id``, and ``device_name``. Use this as the
  base for any sensor-originated payloads.

- :class:`~msight_core.data.SensorDataSequence` — Sequence wrapper
  for grouping ordered sensor data frames.

- :class:`~msight_core.data.ImageData` — Image container.

- :class:`~msight_core.data.DetectionResultsData` — Container for detection
  outputs that associates a detection result object with its source image
  frame id and optional raw sensor payload.

- :class:`~msight_core.data.RoadUserListData` — Stores a list of road-user
  points (e.g. pedestrian/vehicle positions). Includes a field codec for
  serialization of the list.

- :class:`~msight_core.data.BytesData` — Generic opaque binary payload. Useful
  when you need to store or transmit arbitrary bytes without interpreting
  their contents.

- :class:`~msight_core.data.VideoData` — Video container. 

- :class:`~msight_core.data.PointCloudData` — Point-cloud data container for
  lidar/depth sensors.

Examples
--------
Import a specific class::

    from msight_core.data import ImageData

Import multiple classes for type annotations::

    from msight_core.data import Data, SensorData, BytesData

"""
from .base import Data, SensorData, SensorDataSequence
from .image import ImageData
from .detection_result import DetectionResultsData, RoadUserListData
from .bytes import BytesData
from .video import VideoData
from .pointcloud import PointCloudData

__all__ = [
    "Data",
    "SensorData",
    "SensorDataSequence",
    "ImageData",
    "DetectionResultsData",
    "RoadUserListData",
    "BytesData",
    "VideoData",
    "PointCloudData",
]

