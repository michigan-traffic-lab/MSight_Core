import pytest
from msight_core import ImageData
from msight_core.utils import get_redis_client
from msight_core.topics import Topic, get_topic
import redis


def test_topic_register():
    redis_client = get_redis_client()
    topic = Topic("test_register", ImageData)
    assert topic.name == "test_register"
    assert topic.data_type == ImageData
    retrieved_topic = get_topic(redis_client, "test_register")
    # print(f"retrieved_topic: {retrieved_topic}")
    assert retrieved_topic.name == "test_register"
    assert retrieved_topic.data_type == ImageData

