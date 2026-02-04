import pytest
from dataclasses import dataclass
from msight_core.data.base import SensorData

def test_data_field_codec_merge():
    @dataclass
    class Data1(SensorData):
        field1: str
        __field_codecs__ = {'field1': (None, None)}

    @dataclass
    class Data2(Data1):
        field2: int
        __field_codecs__ = {'field2': (None, None)}

    # Check that the merged codecs include both base and subclass
    assert 'field1' in Data2.__field_codecs__ and 'field2' in Data2.__field_codecs__, "Field codecs not merged correctly in subclass."
