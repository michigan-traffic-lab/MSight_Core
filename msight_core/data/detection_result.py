"""Data containers for detection results and road-user lists.

This module defines ``SensorData`` subclasses used to carry object
detection outputs and associated metadata across the MSight messaging
infrastructure. It uses types from the ``msight_base`` package for
structured detection objects and attach a
:class:`FieldCodec` to a field to customize serialization/deserialization.

Provided classes:
    - DetectionResultsData: Holds a detection result object and optional raw
      sensor payload linkage.
    - RoadUserListData: Carries a list of ``RoadUserPoint`` objects with a
      codec that serializes each object via its ``to_dict`` / ``from_dict``
      helpers.
"""

from .base import SensorData
from typing import Optional
from dataclasses import dataclass
from msight_base import DetectionResultBase, RoadUserPoint
from .base import FieldCodec

road_user_list_codec = FieldCodec(
    lambda lst: [user.to_dict() for user in lst],
    lambda lst: [RoadUserPoint.from_dict(obj) for obj in lst],
    context=False,
)

@dataclass
class DetectionResultsData(SensorData):
    """Container for detection outputs linked to a sensor frame.

    This dataclass carries the detection result produced for an image/frame
    along with optional references to the originating sensor payload.

    Attributes:
        image_frame_id (Optional[int]): Identifier of the image/frame the
            detection was produced for. 
        detection_result (Optional[DetectionResultBase]): Structured
            detection result object coming from ``msight_base``. The object
            may include bounding boxes, classes, scores and additional
            metadata.
        raw_sensor_data (Optional[SensorData]): Optional pointer to the raw
            sensor message (e.g. compressed image) that produced this
            detection. When present this allows consumers to fetch the
            original payload alongside detections.
    """
    # image_frame_id: Optional[int] = None
    __field_codecs__ = {
        "detection_result": FieldCodec(
            lambda dr: dr.to_dict() if dr is not None else None,
            lambda d: DetectionResultBase.from_dict(d) if d is not None else None,
            context=False,
        ),
        "raw_sensor_data": FieldCodec(
            lambda sd: sd.to_dict() if sd is not None else None,  
            lambda d: SensorData.from_dict(d) if d is not None else None,
            context=False,
        ),
    }
    detection_result: Optional[DetectionResultBase] = None
    raw_sensor_data: Optional[SensorData] = None
    sensor_frame_id: Optional[int] = None


@dataclass
class RoadUserListData(SensorData):
    """Holds a list of road-user points with custom serialization.

    The ``road_user_list`` field contains a list of ``RoadUserPoint`` objects
    from ``msight_base``. A :class:`FieldCodec` is attached to perform
    element-wise conversion to/from dicts during serialization so the list
    can be embedded in standard JSON/MessagePack payloads.

    Attributes:
        road_user_list (list[RoadUserPoint]): List of road user points.

    Notes:
        The module-level ``road_user_list_codec`` implements the codec used
        for ``road_user_list`` and is registered on the class via
        ``__field_codecs__``.
    """

    road_user_list: list[RoadUserPoint]
    __field_codecs__ = {
        "road_user_list": road_user_list_codec
    }


