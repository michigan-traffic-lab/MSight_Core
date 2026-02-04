import pytest

from msight_core.nodes import LocalImageSourceNode
from msight_core import ImageData, Topic
from pathlib import Path

def test_image_publish():
    image_path = Path(__file__).parent / "sample_image.jpg"
    topic = Topic("test_image_publish", ImageData)
    LocalImageSourceNode("test_image_publish", topic, "test_publish_image_sensor", str(image_path), 10).spin(life_span=10)

