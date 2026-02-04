"""Video container and metadata helpers.

This module defines :class:`VideoData`, a container for encoded video
payloads produced by aggregating image frames. The class extends
:class:`~msight_core.data.SensorData` so it inherits common sensor fields
(sensor name, timestamps, frame id, etc.).

Notes
-----
- The ``video`` field is intended to hold encoded video bytes (for example,
  MP4 or H.264 elementary stream). 
- The optional ``detection_results`` field may contain detection results
  associated with the contained video frames (for example, aggregated
  detection outputs or a summary object).
- ``frame_ids`` is an optional ordered list of frame identifiers that maps the
  encoded video back to the original frame sequence.

Examples
--------
Create a VideoData instance::

    from msight_core.data import VideoData
    vd = VideoData(sensor_name="front_cam", video=b"\x00...", frame_ids=[1,2,3])

"""

import numpy as np
import cv2
# import time
import os
import json
from typing import List, Optional
from dataclasses import dataclass, field
from .detection_result import DetectionResultsData
from .base import SensorData, Data

MSIGHT_EDGE_DEVICE_NAME = os.getenv("MSIGHT_EDGE_DEVICE_NAME")

@dataclass
class VideoData(SensorData):
    """Container for encoded video payloads and optional metadata.

    Fields
    ------
    video: Optional[bytes]
        Encoded video bytes (e.g., MP4, H.264). 

    detection_results: Optional[DetectionResultsData]
        Optional detection results associated with the video. Use this to
        attach aggregated or per-video detection outputs.

    frame_ids: Optional[List[int]]
        Ordered list of frame identifiers corresponding to frames included in
        the encoded video. Helpful for mapping video segments back to
        original frame-level metadata.

    capture_timestamps: Optional[List[float]]
        Ordered list of capture timestamps (in seconds since epoch) for each
        frame included in the encoded video. Corresponds to the
        ``capture_timestamp`` field from individual image frames.

    Notes
    -----
    This container does not implement encoding/decoding helpers itself; use
    external utilities (e.g., OpenCV or ffmpeg wrappers) to produce encoded
    bytes prior to constructing a ``VideoData`` instance.
    """
    video: Optional[bytes] = field(repr=False, default=None)
    detection_results: Optional[DetectionResultsData] = field(default=None, repr=False)
    frame_ids: Optional[List[int]] = field(default=None, repr=False)
    capture_timestamps: Optional[List[float]] = field(default=None, repr=False)


