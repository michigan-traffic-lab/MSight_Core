# Local Image Viewer in MSight Core

This is a minimum showcase on how MSight works, this example spin up two node, one read a local image from disk, and another node display the node.

This example uses Docker compose to configure each container. Since the image will be shown on the user interface, you need to run the following command to enable Docker container to connect to host's X server:

```bash
xhost +local:docker
```

Then you can do 
```bash
docker compose up
```

We also contain an example on how using unix socket (for potentially better latency):
```bash
docker compose -f docker-compose-unix-socket.yml up
```
