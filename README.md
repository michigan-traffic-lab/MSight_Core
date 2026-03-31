# MSight Core

MSight Core is the distributed runtime backbone of the MSight ecosystem. It provides the node orchestration, data transport, and deployment primitives required to run real-time roadside perception pipelines on edge devices.

The project is designed for connected and automated mobility applications where camera, LiDAR, and V2X data must be ingested, processed, and forwarded with low latency.

## Overview

MSight Core standardizes how edge applications are assembled and operated:

- Node-based pipeline execution model
- Topic-based pub/sub communication
- Unified data model transport and serialization
- Source, processing, and sink node abstractions
- Deployment-ready CLI launch tools

In a typical deployment, MSight Core sits between sensor-facing modules (for example, MSight Vision or LiDAR decoders) and downstream consumers such as cloud storage, V2X interfaces, and visualization tools.

## Key Capabilities

- Real-time ingestion from local files, RTSP streams, UDP servers, WebSocket feeds, and LiDAR packet streams
- Pluggable processing nodes for buffering, sorting, aggregation, and transformation
- Output sinks for local persistence, visualization, HTTP/Kinesis/S3 forwarding, and RSU IFM transmission
- Consistent node lifecycle with registration, heartbeat, and monitoring support
- Flexible pub/sub backend selection via environment configuration

## Installation

### Prerequisites

- Python 3.9+
- pip
- Redis (recommended for local development/runtime)

### Install from source

```bash
git clone https://github.com/michigan-traffic-lab/MSight_Core.git
cd MSight_Core
pip install -e .
```

For a standard (non-editable) install:

```bash
pip install .
```

## Environment Setup

MSight Core expects a device identity and supports broker configuration via environment variables.

Minimum required variable:

```bash
export MSIGHT_EDGE_DEVICE_NAME=<your_edge_device_name>
```

PowerShell equivalent:

```powershell
$env:MSIGHT_EDGE_DEVICE_NAME = "<your_edge_device_name>"
```

Common broker/runtime variables:

- `MSIGHT_REDIS_MESSAGE_BROKER_HOST` (default: `localhost`)
- `MSIGHT_REDIS_MESSAGE_BROKER_PORT` (default: `6379`)
- `MSIGHT_REDIS_MESSAGE_BROKER_DB` (default: `0`)
- `MSIGHT_LOGGING_LEVEL` (default: `INFO`)

## Command-Line Tools

MSight Core exposes launch scripts for many built-in nodes and utilities, including:

- `msight_launch_local_image`
- `msight_launch_image_viewer`
- `msight_launch_rtsp`
- `msight_launch_udp_server`
- `msight_launch_websocket_client`
- `msight_launch_aggregator`
- `msight_launch_buffering_sort`
- `msight_launch_image_to_video_aggregator`
- `msight_launch_sdsm_encoder`
- `msight_launch_http`
- `msight_launch_kinesis_pusher`
- `msight_launch_aws_sequence_pusher`
- `msight_launch_aws_video_pusher`
- `msight_launch_ifm`
- `msight_launch_pointcloud_viewer`
- `msight_launch_pointcloud_local_dumper`
- `msight_launch_video_local_dumper`
- `msight_reset_redis`
- `msight_status`
- `msight_download_data`

Inspect arguments for any command with:

```bash
msight_launch_rtsp --help
msight_launch_aggregator --help
```

## Quick Start

The `examples/local_image` directory contains a minimal two-node pipeline example:

1. A source node publishes images from local disk.
2. A sink node displays incoming images.

This example includes Docker Compose configurations (TCP and Unix socket variants) to help validate runtime setup quickly.

A larger demonstration is also available in `examples/mcity_det` for detection-oriented workflows.

## Documentation

Documentation is built with MkDocs and published via GitHub Pages.

Install docs dependencies:

```bash
pip install mkdocs mkdocs-material mkdocs-gen-files mkdocs-literate-nav mkdocstrings[python] pymdown-extensions
```

Serve docs locally:

```bash
mkdocs serve
mkdocs serve -a localhost:8080
mkdocs serve -a 0.0.0.0:8080
```

Build static documentation:

```bash
mkdocs build
```

Published docs URL:

https://michigan-traffic-lab.github.io/MSight_Core/

## Repository Structure

- `msight_core/data`: shared data containers and serialization
- `msight_core/nodes`: base classes and built-in source/process/sink nodes
- `msight_core/pubsub`: backend communication layer
- `cli`: runnable node and utility entry points
- `examples`: local and end-to-end usage examples
- `docs`: MkDocs source files

## License

This project is licensed under the BSD 3-Clause License. See the LICENSE file for details.

## Developers

- Rusheng Zhang

## Contact

- Henry Liu (henryliu@umich.edu)

