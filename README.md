我是用的是wsl2，ubuntu版本24.04.3进行部署，无法进行硬件编码和调用摄像头，因此利用ffmepg工具和mediamtx进行的以网络为基础的rtsp推流，成功部署并进行推理。

deepstream环境配置和部署：
cuda下载：https://developer.nvidia.com/cuda-downloads
Cudnn: https://developer.nvidia.com/cudnn-downloads
tensorrt: https://developer.nvidia.com/tensorrt/download
deepstream: https://catalog.ngc.nvidia.com/orgs/nvidia/collections/deepstream_sdk
注意！注意！注意！：
deepstream的部署有着严苛的版本要求，配置之前先要知道自己的系统版本，nvidia驱动版本，python绑定，适配版本查询（cuda,Cudnn ...）,用发及下载，参考：https://catalog.ngc.nvidia.com/orgs/nvidia/collections/deepstream_sdk
推荐下载tbz2文件，适配性较好。ex：（deepstream_sdk_v8.0.0_x86_64.tbz2）
配置完成后有时会发现缺少依赖，先在终端搜索可用的相关依赖，再下载，re:有时会提示找不到相关依赖的下载路径
完成之后：deepstream-app --version验证
没问题的话下载deepstream-yolo：https://github.com/marcoslucianops/DeepStream-Yolo
（有详细教程）

rtsp：
1.确保网络良好，ip不加密。
mediamtx: https://github.com/bluenviron/mediamtx/releases
mediamtx作为一个ffmpeg的服务端，可以将视频流发送到mediamtx服务器上，再在其他地方进行推流输出结果。
ffmpeg下载：直接在终端输入sudo apt install ffmpeg即可。
使用：看情况修改mediamtx的yaml配置文件，再运行meidamtx，打开另一个终端进行ffmpeg推流，示例：ffmpeg -f dshow -rtbufsize 1024M -i video="USB2.0 HD UVC WebCam" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://localhost:8554/camerastream
正常情况下视频流会成功传到服务其中，我们可以进行调用，调用需要修改localhost主机IP（在配置文件里）该文件里的配置即版本图片仅供参考。
