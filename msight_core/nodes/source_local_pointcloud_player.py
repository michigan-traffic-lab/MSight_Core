from .base import SourceNode, NodeConfig
from ..data import PointCloudData
import numpy as np
from pathlib import Path
from datetime import datetime
import time


# Matches the dtype written by PointCloudLocalDumperSinkNode
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


def _parse_pcd_timestamp(stem: str) -> datetime | None:
    """Parse a datetime from a PCD filename stem.

    The dumper saves files as ``<ISO-datetime>.pcd`` with colons in the time
    portion replaced by dashes, e.g. ``2024-01-15T14-30-05.123456.pcd``.
    """
    try:
        if "T" in stem:
            date_part, time_part = stem.split("T", 1)
            # Normalize both "-" and "_" used as ":" replacements in time part
            time_part = time_part.replace("-", ":").replace("_", ":")
            return datetime.fromisoformat(f"{date_part}T{time_part}")
        return datetime.fromisoformat(stem)
    except ValueError:
        return None


def _get_all_pcd_timestamps(sensor_dir: Path) -> list[tuple[datetime, Path]]:
    """Recursively find all PCD files under *sensor_dir* and return a sorted
    list of ``(timestamp, path)`` pairs."""
    entries = []
    for pcd_file in sensor_dir.rglob("*.pcd"):
        ts = _parse_pcd_timestamp(pcd_file.stem)
        if ts is not None:
            entries.append((ts, pcd_file))
    return sorted(entries, key=lambda x: x[0])


def _binary_search_closest(sorted_list: list[tuple[datetime, Path]], target: datetime) -> int:
    """Return the index of the entry whose timestamp is closest to *target*."""
    low, high = 0, len(sorted_list) - 1
    best = 0
    while low <= high:
        mid = (low + high) // 2
        t = sorted_list[mid][0]
        if t < target:
            low = mid + 1
        elif t > target:
            high = mid - 1
        else:
            return mid
        if abs((sorted_list[mid][0] - target).total_seconds()) < \
           abs((sorted_list[best][0] - target).total_seconds()):
            best = mid
    return best


def _load_pcd(path: Path) -> np.ndarray:
    """Read a binary PCD file written by :class:`PointCloudLocalDumperSinkNode`
    and return a structured NumPy array with :data:`PCD_DTYPE`."""
    with open(path, "rb") as f:
        # Skip ASCII header lines until we hit "DATA binary"
        while True:
            line = f.readline().decode("ascii", errors="replace").strip()
            if line == "DATA binary":
                break
        raw = f.read()
    if not raw:
        return np.empty(0, dtype=PCD_DTYPE)
    n = len(raw) // PCD_DTYPE.itemsize
    return np.frombuffer(raw[: n * PCD_DTYPE.itemsize], dtype=PCD_DTYPE).copy()


class LocalPointCloudPlayerSourceNode(SourceNode):
    """Replay point-cloud data previously dumped to disk.

    Expected directory layout (output of :class:`PointCloudLocalDumperSinkNode`)::

        root/
            <sensor_A>/          ← one immediate sub-folder per sensor
                <date>/<hour>/
                    <timestamp>.pcd
            <sensor_B>/
                ...

    Pass the folder that sits **directly above** the sensor-name folders as
    *root* (e.g. ``output_folder_path/<date>/<hour>/``).

    Multiple sensors are synchronized to the primary sensor: for each primary
    frame the closest frame from every other sensor (within 1 s) is queued and
    emitted in subsequent :meth:`get_data` calls, so replay appears smooth.

    Args:
        configs (NodeConfig): Node configuration.
        root (str): Path to the folder containing per-sensor sub-folders.
        fps (float): Target replay frame-rate. Default is 10 Hz.
        primary_sensor (str | None): Name of the sensor that drives timing.
            Defaults to the first sensor found alphabetically.
        loop (bool): Whether to loop back to the beginning when the recording
            ends. Default is ``True``.
    """

    default_configs = NodeConfig(
        publish_topic_data_type=PointCloudData,
        sensor_name="local_pointcloud_player",
    )

    def __init__(self, configs: NodeConfig, root: str, fps: float = 10.0,
                 primary_sensor: str | None = None, loop: bool = True):
        super().__init__(configs)
        self.root = Path(root)
        self.fps = fps
        self.loop = loop

        # Discover sensors (immediate sub-directories of root)
        self.sensors = sorted([d.name for d in self.root.iterdir() if d.is_dir()])
        if not self.sensors:
            raise ValueError(f"No sensor sub-directories found in {root!r}")

        self.primary_sensor = primary_sensor if primary_sensor is not None else self.sensors[0]
        if self.primary_sensor not in self.sensors:
            raise ValueError(
                f"Primary sensor {self.primary_sensor!r} not found in {root!r}. "
                f"Available sensors: {self.sensors}"
            )

        # Pre-load all (timestamp, path) pairs per sensor
        self.sensor_frames: dict[str, list[tuple[datetime, Path]]] = {}
        for sensor in self.sensors:
            self.sensor_frames[sensor] = _get_all_pcd_timestamps(self.root / sensor)
            self.logger.info(
                f"Sensor '{sensor}': found {len(self.sensor_frames[sensor])} PCD files."
            )

        if not self.sensor_frames[self.primary_sensor]:
            raise ValueError(
                f"No PCD files found for primary sensor '{self.primary_sensor}' under {root!r}"
            )

        self.pointer = 0
        self.buffer: list[PointCloudData] = []
        self._t_frame_start: float | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_before_spin(self):
        self.logger.info(
            f"LocalPointCloudPlayer '{self.name}' – root={self.root}, "
            f"sensors={self.sensors}, primary='{self.primary_sensor}', "
            f"fps={self.fps}, loop={self.loop}"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _wait_for_next_frame(self):
        if self._t_frame_start is None:
            return
        elapsed = time.time() - self._t_frame_start
        sleep_time = 1.0 / self.fps - elapsed
        if sleep_time < 0:
            self.logger.warning(
                f"Processing took {elapsed:.3f}s, target is {1/self.fps:.3f}s – "
                "replay may be slower than requested fps."
            )
        else:
            time.sleep(sleep_time)

    def _make_pointcloud_data(self, sensor: str, path: Path, ts: datetime) -> PointCloudData:
        pts = _load_pcd(path)
        ts_float = ts.timestamp()
        return PointCloudData.from_ndarray(
            points=pts,
            sensor_name=sensor,
            capture_timestamp=ts_float,
            creation_timestamp=ts_float,
        )

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    def get_data(self) -> PointCloudData:
        # Drain secondary-sensor buffer first
        if self.buffer:
            data = self.buffer.pop(0)
            # Wait for target fps only after draining the last buffered item
            if not self.buffer:
                self._wait_for_next_frame()
            return data

        # Single-sensor path: rate-limit between primary frames
        if len(self.sensors) == 1 and self._t_frame_start is not None:
            self._wait_for_next_frame()

        self._t_frame_start = time.time()

        primary_frames = self.sensor_frames[self.primary_sensor]
        if self.pointer >= len(primary_frames):
            if self.loop:
                self.pointer = 0
                self.logger.info("Looping back to the start of the recording.")
            else:
                # Hold on the last frame indefinitely
                self.pointer = len(primary_frames) - 1
                self.logger.info("Reached end of recording.")

        primary_ts, primary_path = primary_frames[self.pointer]
        primary_data = self._make_pointcloud_data(
            self.primary_sensor, primary_path, primary_ts
        )
        self.logger.info(
            f"Publishing frame {self.pointer}/{len(primary_frames)} "
            f"from '{self.primary_sensor}' at {primary_ts}"
        )

        # Queue synchronized frames from secondary sensors
        for sensor in self.sensors:
            if sensor == self.primary_sensor:
                continue
            frames = self.sensor_frames[sensor]
            if not frames:
                continue
            idx = _binary_search_closest(frames, primary_ts)
            sec_ts, sec_path = frames[idx]
            dt = abs((sec_ts - primary_ts).total_seconds())
            if dt > 1.0:
                self.logger.warning(
                    f"Sensor '{sensor}' nearest frame is {dt:.3f}s away from "
                    f"primary at {primary_ts} – skipping."
                )
                continue
            self.buffer.append(
                self._make_pointcloud_data(sensor, sec_path, sec_ts)
            )

        self.pointer += 1
        return primary_data

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, name: str, publish_topic_name: str, root: str,
               fps: float = 10.0, primary_sensor: str | None = None,
               loop: bool = True) -> "LocalPointCloudPlayerSourceNode":
        """Convenience factory that mirrors the pattern used by other nodes.

        Args:
            name (str): Node name.
            publish_topic_name (str): Topic to publish point clouds to.
            root (str): Folder directly above sensor sub-directories.
            fps (float): Replay frame-rate in Hz. Default 10.
            primary_sensor (str | None): Primary sensor name. Defaults to
                first sensor alphabetically.
            loop (bool): Loop when the recording ends. Default ``True``.
        """
        configs = NodeConfig(
            name=name,
            publish_topic_name=publish_topic_name,
        )
        return cls(configs, root, fps, primary_sensor, loop)
