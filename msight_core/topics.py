"""Topic registry helpers.

This module defines a Topic with helpers to register and
retrieve topic metadata from Redis. Topics basic information is stored as JSON strings in the
hash key identified by :data:`REDIS_TOPICS_FIELD` and follow a small schema:

- name: topic name (string)
- description: optional textual description
- data_type: fully-qualified import path for the data class

The :class:`Topic` object provides convenience methods to serialize to/from
this dict schema and to register the topic in Redis. Use
:meth:`get_topic` to load topic metadata from Redis and optionally register a
new topic when it does not exist.
"""

from .data import Data
from .utils import get_class_path, dynamic_import
import json
from msight_core.utils import get_redis_client
from redis import Redis
from typing import Type, Optional
REDIS_TOPICS_FIELD = "MSIGHT:TOPICS"

class Topic:
    """
    The Topic holds the topic name, a human-friendly description and the
    data type (a subclass of :class:`~msight_core.data.Data`). The
    :meth:`to_dict` / :meth:`from_dict` pair provide a stable JSON-serializable
    representation used for storage in Redis.
    """
    def __init__(self, name: str, data_type: Data, description: str = None):
        self.name = name
        self.description = description
        assert issubclass(
            data_type, Data), "data_type should be a subclass of Data"
        self.data_type = data_type
        # self.register()

    def to_dict(self) -> dict:
        """Return a JSON-serializable mapping for this topic.

        Returns:
            dict: Contains keys ``name``, ``description`` and ``data_type``.
                  ``data_type`` is the fully-qualified import path for the
                  data class (e.g. ``msight_core.data.ImageData``).
        """
        return {
            "name": self.name,
            "description": self.description,
            "data_type": get_class_path(self.data_type)
        }
    
    def register(self) -> None:
        """Register (or update) this topic in Redis.

        The topic is stored in the hash named by :data:`REDIS_TOPICS_FIELD`.
        If the topic already exists the value will be overwritten.
        """
        redis_client  = get_redis_client()
        if redis_client.hexists(REDIS_TOPICS_FIELD, self.name):
            print(f"Topic {self.name} already exists, update it.")
        redis_client.hset(REDIS_TOPICS_FIELD, self.name, json.dumps(
            self.to_dict()))
        # release the connection
        redis_client.close()

    @staticmethod
    def from_dict(d: dict) -> "Topic":
        """Create a :class:`Topic` from a deserialized mapping.

        Args:
            d (dict): Mapping with keys ``name``, ``data_type`` and optional
                      ``description``.

        Returns:
            Topic: Constructed Topic instance with the resolved data_type.
        """
        data_type_path = d["data_type"]
        # import the data type
        data_type = dynamic_import(data_type_path)
        return Topic(d["name"], data_type, d["description"])


def get_topic(redis_client: Redis, topic_name: str, register_if_not_exist: bool = False, data_type: Optional[Type[Data]] = None, description: str = None) -> Topic:
    """Lookup a Topic by name in Redis and optionally register it.

    Args:
        redis_client: Redis client instance (supports ``hget``/``hset``/``hexists``).
        topic_name (str): Name of the topic to retrieve.
        register_if_not_exist (bool): If True and the topic is missing, a new
            topic will be created using the provided ``data_type`` and
            ``description`` and stored in Redis.
        data_type: Class object to use when registering a new topic (required
            when ``register_if_not_exist`` is True).
        description (str): Optional description used when registering.

    Returns:
        Topic or None: The Topic instance when found or created; otherwise
        ``None`` if the topic does not exist and ``register_if_not_exist`` is
        False.
    """
    # use hget to get the topic data by name
    topic_data_json = redis_client.hget(REDIS_TOPICS_FIELD, topic_name)
    # print(topic_data_json)
    if topic_data_json is None and register_if_not_exist:
        if data_type is None:
            raise ValueError(
                "data_type should be provided if register_if_not_exist is True")
        topic = Topic(topic_name, data_type, description=description)
        topic.register()
        # register_topic(redis_client, topic)
        return topic
    # print(f"topic_data_json: {topic_data_json}")
    if topic_data_json is None:
        return None
    topic_data = json.loads(topic_data_json)
    return Topic.from_dict(topic_data)




