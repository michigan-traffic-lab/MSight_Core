# Mcity Detection Example
## To Run
To run this example, run the following command in this directory:
```bash
msight_launch_downloaded_image_player -d ./mcity -t mcity_rtsp 
```
Then open another shell, run:
```bash
msight_launch_yolov8_detection -n yolov8 --subscribe-topic mcity_rtsp  --publish-topic detection_result -c ./config.yml
```

If you want to also publish image with detection:
```bash
msight_launch_yolov8_detection -n yolov8 --subscribe-topic mcity_rtsp  --publish-topic detection_result --second-publish-topic detection_image -c ./config.yml -m results_and_image
```