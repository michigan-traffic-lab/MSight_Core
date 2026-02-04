"""Utilities for encoding/decoding images carried as Data messages.

This module provides :class:`ImageData`, a :class:`SensorData` subclass that
wraps an encoded (e.g. JPEG) or raw numpy image together with the common
sensor metadata (timestamps, frame id, device name). It includes helper
constructors and conversion utilities to move between ``numpy.ndarray`` and
wire-friendly byte representations.

Key functions / behavior:
    - ``from_ndarray``: Create an ``ImageData`` from a numpy array, optionally
      encoding to JPEG with configurable quality.
    - ``to_array``: Decode the stored bytes back into a ``numpy.ndarray``.
    - ``from_json``: Support JSON deserialization where the image bytes are
      base64-encoded.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import cv2
import time
from .base import SensorData
from .detection_result import DetectionResultsData
import base64
import json



@dataclass
class ImageData(SensorData):
    """Container for image sensor payloads.

    The dataclass stores an image payload together with timestamps and other
    metadata inherited from :class:`SensorData`.

    Attributes:
        image (Optional[bytes]): Encoded image bytes (e.g. JPEG) or raw
            bytes depending on ``is_encoded``. Hidden from ``repr`` to avoid
            large binary dumps in logs.
        is_encoded (bool): Whether ``image`` contains an encoded image format
            (True) or raw numpy bytes (False). When encoded, ``to_array`` will
            decode using OpenCV; when not encoded the consumer must know the
            original dtype/shape, which is provided in ``size``.
        detection_results (Optional[DetectionResultsData]): Optional
            detection output associated with this image/frame.
        size (Optional[tuple[int, int, int]]): Shape of the original numpy
            array (height, width, channels). Required when ``is_encoded`` is
            False to reconstruct the array from raw bytes.
    """

    # raw encoded bytes to send over the wire (JPEG or other)
    image: Optional[bytes] = field(repr=False, default=None)
    is_encoded: bool = True
    detection_results: Optional[DetectionResultsData] = None
    size: Optional[tuple[int, int, int]] = field(default=None)

    @classmethod
    def from_ndarray(
        cls,
        image: np.ndarray,
        sensor_name: str,
        capture_timestamp: float = None,
        creation_timestamp: float = None,
        is_encoded: bool = True,
        detection_results: Optional[DetectionResultsData] = None,
        jpeg_quality: int = 50,
    ) -> "ImageData":
        """Create an ImageData instance from a numpy array.

        Args:
            image (np.ndarray): The image data as a numpy array.
            sensor_name (str): The name of the sensor.
            capture_timestamp (float, optional): The capture timestamp. Defaults to None.
            creation_timestamp (float, optional): The creation timestamp. Defaults to None.
            is_encoded (bool, optional): Flag indicating if the image is encoded. Defaults to True. When flag is True, the function will encode the image to JPEG format.
            detection_results (Optional[DetectionResultsData], optional): Detection results data. Defaults to None.
            jpeg_quality (int, optional): JPEG quality for encoding. Defaults to 50.

        Returns:
            ImageData: An instance of ImageData containing the image and metadata.
        """
        if capture_timestamp is None:
            capture_timestamp = time.time()
        if creation_timestamp is None:
            creation_timestamp = time.time()
        if is_encoded:
            retval, buffer = cv2.imencode(
                ".jpg",
                image,
                [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality,
                 cv2.IMWRITE_JPEG_OPTIMIZE, 1],
            )
            if not retval:
                raise ValueError(
                    "Failed to encode image, make sure the image is valid and the format is supported."
                )
            image_ = buffer.tobytes()
        else:
            # if you really want to send raw image bytes; consumer must know how to interpret
            image_ = image.tobytes()

        return cls(
            sensor_name=sensor_name,
            image=image_,
            capture_timestamp=capture_timestamp,
            creation_timestamp=creation_timestamp,
            is_encoded=is_encoded,
            detection_results=detection_results,
            size=image.shape,
        )
    
    def to_ndarray(self) -> np.ndarray:
        """Decode JPEG bytes back into a numpy array."""
        if not self.is_encoded:
            return np.frombuffer(self.image, dtype=np.uint8).reshape(self.size)
        else:
            buffer = np.frombuffer(self.image, dtype=np.uint8)
            img = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image from encoded bytes.")
        return img
    
    @property
    def decoded_image(self) -> np.ndarray:
        """Get the decoded image as a numpy array.
        
        Returns:
            np.ndarray: The decoded image.
            
        Raises:
            ValueError: If the image cannot be decoded from encoded bytes.
        """
        return self.to_ndarray()
    
    @classmethod
    def from_json(cls, data):
        """Deserialize a JSON string into a concrete Data subclass."""
        payload = json.loads(data)
        if payload.get("image"):
            payload["image"] = base64.b64decode(payload["image"])
        return Data.from_dict(payload)  # type: ignore[return-value]

