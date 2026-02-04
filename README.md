# MSight Core
MSight Core is an edge computing software system for connected and automated vehicle applications. It is designed to run on edge devices to integrate with traffic controllers, roadside sensors, road-side unit (RSU) and connected vehicles and infrastructure in real-time.


## Installation and Run
### Docker Installation:
Do the following step to install the project on a edge device.

- [Install docker](https://docs.docker.com/engine/install/ubuntu/)
- [Finish docker post installation](#docker-post-installation)
- (Optional) install [Nvidia Container toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) if GPU is needed.
- write a `.env` file to specify information for the specific edge device, an example `.env` file is [here](.env-example).
- [Setup AWS Cloudwatch](docs/cloudwatch_logging.md)

### Local installation
#### Prerequisites:
- Python 3.10 or later
#### Local installation
For development installation:
```bash
pip install -e .
```

For normal installation:
```bash
pip install .
```
## Running:


## Docker post installation
For more details use [this tutorial](https://docs.docker.com/engine/install/linux-postinstall/). Do the following to complete docker configuration:
```bash
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
sudo systemctl enable docker.service
sudo systemctl enable containerd.service
```

## (Optional) Enable GPU runtime
If you need to run detection on the edge, you'll need to enable Nvidia docker runtime by installing Nvidia container toolkit to allow GPU runtime, follow official document [here](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#installation-guide).

## Miscellaneous
- To deploy the testing system at MCity, here is an [example document](docs/mcity_edge_testing.md)
- In case you'll setup your own Kinesis stream, check [this document](docs/kinesis.md)

## Documentation

Install MkDocs and required plugins:
```bash
pip install mkdocs mkdocs-material mkdocs-gen-files mkdocs-literate-nav mkdocstrings mkdocstrings-python
```

Build and serve documentation:
```bash
# Serve on default port (8000)
mkdocs serve

# Serve on a specific port
mkdocs serve -a localhost:8080

# Serve on all interfaces with custom port
mkdocs serve -a 0.0.0.0:8080
```

Build static documentation:
```bash
mkdocs build
```

