from .base import SinkNode, NodeConfig
from ..data import PointCloudData
import numpy as np
from pathlib import Path
from datetime import datetime
import threading

PCD_FIELDS = ("x", "y", "z", "intensity", "time", "column", "ring", "return_type")
PCD_SIZE   = (4,   4,   4,   4,           4,      2,        1,      1)
PCD_TYPE   = ("F","F","F","F",            "F",    "U",      "U",    "U")
PCD_COUNT  = (1,   1,   1,   1,           1,      1,        1,      1)

# Exact PCD write dtype (little-endian where relevant)
PCD_DTYPE = np.dtype([
    ("x", "<f4"),
    ("y", "<f4"),
    ("z", "<f4"),
    ("intensity", "<f4"),
    ("time", "<f4"),
    ("column", "<u2"),
    ("ring",  "|u1"),
    ("return_type", "|u1"),
])

def _pcd_header(width: int, height: int, points: int) -> bytes:
    header = [
        "# .PCD v0.7 - Point Cloud Data file format",
        "VERSION 0.7",
        "FIELDS " + " ".join(PCD_FIELDS),
        "SIZE "   + " ".join(str(s) for s in PCD_SIZE),
        "TYPE "   + " ".join(PCD_TYPE),
        "COUNT "  + " ".join(str(c) for c in PCD_COUNT),
        f"WIDTH {width}",
        f"HEIGHT {height}",
        "VIEWPOINT 0 0 0 1 0 0 0",
        f"POINTS {points}",
        "DATA binary"
    ]
    return ("\n".join(header) + "\n").encode("ascii")

def save_points_to_pcd(points_struct: np.ndarray, out_path: str) -> None:
    """
    points_struct dtype must include: x,y,z,intensity,time,column,ring,return_type
    Extra fields (e.g., padding) are ignored.
    """
    n = len(points_struct)
    if n == 0:
        return

    # Build a compact array that matches PCD fields/dtypes exactly
    arr = np.empty(n, dtype=PCD_DTYPE)
    for name in PCD_FIELDS:
        if name not in points_struct.dtype.names:
            raise ValueError(f"Missing required field '{name}' in decoded points.")
        arr[name] = points_struct[name].astype(arr.dtype.fields[name][0], copy=False)

    with open(out_path, "wb") as f:
        f.write(_pcd_header(width=n, height=1, points=n))
        f.write(arr.tobytes(order="C"))

class PointCloudLocalDumperSinkNode(SinkNode):
    default_configs = NodeConfig(
        subscribe_topic_data_type=PointCloudData,
    )
    def __init__(self, configs, output_folder_path, use_creation_timestamp=False):
        super().__init__(configs)
        self.output_folder_path = Path(output_folder_path)
        self.output_folder_path.mkdir(parents=True, exist_ok=True)
        self.use_creation_timestamp = use_creation_timestamp
        
    def on_message(self, data):
        self.logger.info(f"Received point cloud data from {data.sensor_name} at {data.time}")
        pts = data.points
        # print(pts)
        if self.use_creation_timestamp:
            timestring = datetime.fromtimestamp(data.creation_timestamp).isoformat()
        else:
            timestring = data.time
        t = datetime.fromisoformat(timestring)
        # now create output path, should be output/year/month/day/hour/str(t).pcd the month, day should be padded to two digits
        out_path = self.output_folder_path / f"{t.year}-{t.month:02}-{t.day:02}/{t.hour:02}/{data.sensor_name}/{timestring}.pcd".replace(":", "-")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        x = threading.Thread(target=save_points_to_pcd, args=(pts, out_path), daemon=True)
        x.start()
        self.logger.info(f"Saved point cloud for sensor {data.sensor_name} at {out_path}")
        #
        # save_points_to_pcd(pts, out_path)

    @classmethod
    def create(cls, name, subscribe_topic, output_folder_path):
        configs = NodeConfig(
            name=name,
            subscribe_topic_name=subscribe_topic,
        )
        return cls(
            configs,
            output_folder_path,
        )

