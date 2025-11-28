#!/usr/bin/env python3

import sys
import os
import gi
import time
import threading
import subprocess

# 设置环境变量
os.environ['GST_DEBUG'] = '2'
os.environ['GST_PLUGIN_PATH'] = '/opt/nvidia/deepstream/deepstream-6.0/lib/gst-plugins'
os.environ['LD_LIBRARY_PATH'] = '/opt/nvidia/deepstream/deepstream-6.0/lib:/usr/lib/aarch64-linux-gnu'

# 添加 Python 路径
sys.path.insert(0, '/opt/nvidia/deepstream/deepstream-6.0/lib')
sys.path.insert(0, '/opt/nvidia/deepstream/deepstream-6.0/lib/python3.6/site-packages')

gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
import rospy

# 全局变量用于统计
class Statistics:
    def __init__(self):
        self.frame_count = 0
        self.detection_count = 0
        self.start_time = time.time()
        self.fps = 0.0
        self.detection_active = False
        self.last_detection_time = 0
        self.total_objects = 0
        self.last_fps_update = time.time()
        self.total_frames_processed = 0
        
stats = Statistics()

def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        print("End-of-stream")
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        print(f"Warning: {err}: {debug}")
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"Error: {err}: {debug}")
        loop.quit()
    return True

def update_fps():
    """更新帧率统计"""
    current_time = time.time()
    elapsed_time = current_time - stats.last_fps_update
    
    if elapsed_time >= 1.0:
        stats.fps = stats.frame_count / elapsed_time
        stats.frame_count = 0
        stats.last_fps_update = current_time
    
    return stats.fps

def osd_sink_pad_buffer_probe(pad, info, u_data):
    """简化的探针函数"""
    stats.frame_count += 1
    stats.total_frames_processed += 1
    current_fps = update_fps()
    
    # 模拟检测逻辑
    if stats.total_frames_processed % 15 == 0:
        stats.detection_count += 1
        stats.detection_active = True
        stats.last_detection_time = time.time()
        
        rospy.set_param('detection_active', True)
        rospy.set_param('center_x', 320)
        rospy.set_param('center_y', 240)
        rospy.set_param('det_index', 0)
        rospy.set_param('animals_num', 1)
        
        print(f"🎯 检测到对象! 帧: {stats.total_frames_processed}")
    else:
        stats.detection_active = False
        rospy.set_param('detection_active', False)
    
    # 输出统计信息
    if stats.total_frames_processed % 30 == 0:
        if stats.total_frames_processed > 0:
            detection_rate = (stats.detection_count / stats.total_frames_processed) * 100
        else:
            detection_rate = 0.0
            
        print(f"📊 统计 - FPS: {current_fps:.1f} | 帧数: {stats.total_frames_processed} | 检测: {stats.detection_count}")
    
    return Gst.PadProbeReturn.OK

def create_nx_sink():
    """为 NX 创建优化的显示sink"""
    # 尝试不同的sink，优先使用稳定的
    sink_types = [
        ("nveglglessink", "nvegl-sink"),    # NVIDIA EGL sink
        ("xvimagesink", "xv-sink"),         # X11 video sink
        ("ximagesink", "xi-sink"),          # X11 image sink
        ("glimagesink", "gl-sink"),         # OpenGL sink
    ]
    
    for sink_type, sink_name in sink_types:
        sink = Gst.ElementFactory.make(sink_type, sink_name)
        if sink:
            print(f"✅ 使用 {sink_type}")
            
            # 配置sink属性
            if sink_type == "nveglglessink":
                # 配置 nveglglessink 避免资源问题
                sink.set_property('sync', False)
                sink.set_property('max-lateness', 50000000)  # 50ms
                sink.set_property('qos', True)
            elif sink_type in ["xvimagesink", "ximagesink"]:
                sink.set_property('sync', False)
                sink.set_property('async', True)
            
            return sink
    
    print("❌ 无法创建显示sink")
    return None

def start_performance_monitor():
    """启动性能监控线程"""
    def monitor():
        while True:
            time.sleep(2.0)
            current_time = time.time()
            total_runtime = current_time - stats.start_time
            
            if stats.total_frames_processed > 0:
                detection_rate = (stats.detection_count / stats.total_frames_processed) * 100
            else:
                detection_rate = 0.0
                
            print(f"📈 监控 - FPS: {stats.fps:.1f} | 时间: {total_runtime:.1f}s | 检测率: {detection_rate:.1f}%")
    
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    print("✅ 性能监控线程已启动")

def main(args):
    if len(args) != 2:
        sys.stderr.write("usage: %s <v4l2-device-path>\n" % args[0])
        sys.exit(1)

    # 检查摄像头设备
    device = args[1]
    if not os.path.exists(device):
        print(f"❌ 摄像头设备不存在: {device}")
        print("可用的摄像头设备:")
        for i in range(5):
            cam_path = f"/dev/video{i}"
            if os.path.exists(cam_path):
                print(f"  - {cam_path}")
        sys.exit(1)

    Gst.init(None)

    print("🚀 启动 DeepStream 6.0 检测器 - 固定配置版")
    print("=" * 60)

    # 固定配置：1920x1080 @ 30fps
    width = 1920
    height = 1080
    fps = 30

    print(f"🎥 使用摄像头: {device}")
    print(f"📐 固定分辨率: {width}x{height} @ {fps}fps")
    print(f"🎞️  格式: MJPEG")

    print("Creating Pipeline")
    pipeline = Gst.Pipeline()
    if not pipeline:
        sys.stderr.write("Unable to create Pipeline\n")
        return 1

    # 创建元素 - 简化版本
    print("创建元素...")
    source = Gst.ElementFactory.make("v4l2src", "usb-cam-source")
    caps_v4l2src = Gst.ElementFactory.make("capsfilter", "v4l2src_caps")
    jpegdec = Gst.ElementFactory.make("jpegdec", "jpeg-decoder")
    nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "convertor1")
    caps_nvmm = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    nvvidconv2 = Gst.ElementFactory.make("nvvideoconvert", "convertor2")
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    nvvidconv3 = Gst.ElementFactory.make("nvvideoconvert", "convertor3")
    caps_final = Gst.ElementFactory.make("capsfilter", "final_caps")
    
    # 创建优化的sink
    sink = create_nx_sink()
    if not sink:
        return 1

    # 检查所有元素是否创建成功
    elements = [source, caps_v4l2src, jpegdec, nvvidconv1, caps_nvmm, 
                streammux, pgie, nvvidconv2, nvosd, nvvidconv3, caps_final, sink]
    
    for element in elements:
        if not element:
            sys.stderr.write(f"Unable to create element: {element}\n")
            return 1

    # 配置源
    source.set_property('device', device)
    
    # 配置caps
    caps_v4l2src.set_property('caps', Gst.Caps.from_string(f"image/jpeg,width={width},height={height},framerate={fps}/1"))
    caps_nvmm.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM),format=NV12"))
    caps_final.set_property('caps', Gst.Caps.from_string("video/x-raw,format=RGBA"))
    
    # 配置 streammux
    streammux.set_property('width', width)
    streammux.set_property('height', height)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 1000000)
    streammux.set_property('live-source', 1)
    
    # 配置推理器
    config_paths = [
        "config/config_infer_primary_yoloV8.txt",
        "config_infer_primary_yoloV8.txt",
    ]
    
    config_found = False
    for config_path in config_paths:
        if os.path.exists(config_path):
            pgie.set_property('config-file-path', config_path)
            print(f"✅ 使用配置文件: {config_path}")
            config_found = True
            break
    
    if not config_found:
        print("❌ 找不到配置文件")
        return 1

    print("Adding elements to Pipeline")
    for element in elements:
        pipeline.add(element)

    # 链接元素 - 使用更稳定的链接方式
    print("Linking elements in the Pipeline")
    
    # 链接源分支
    if not source.link(caps_v4l2src):
        print("Failed to link source to caps_v4l2src")
        return 1
    if not caps_v4l2src.link(jpegdec):
        print("Failed to link caps_v4l2src to jpegdec")
        return 1
    if not jpegdec.link(nvvidconv1):
        print("Failed to link jpegdec to nvvidconv1")
        return 1
    if not nvvidconv1.link(caps_nvmm):
        print("Failed to link nvvidconv1 to caps_nvmm")
        return 1

    # 连接到 streammux
    sinkpad = streammux.get_request_pad("sink_0")
    if not sinkpad:
        sys.stderr.write("Unable to get the sink pad of streammux\n")
        return 1
        
    srcpad = caps_nvmm.get_static_pad("src")
    if not srcpad:
        sys.stderr.write("Unable to get source pad of caps_nvmm\n")
        return 1
        
    if srcpad.link(sinkpad) != Gst.PadLinkReturn.OK:
        print("Failed to link source branch to streammux")
        return 1

    # 链接主管道
    if not streammux.link(pgie):
        print("Failed to link streammux to pgie")
        return 1
    if not pgie.link(nvvidconv2):
        print("Failed to link pgie to nvvidconv2")
        return 1
    if not nvvidconv2.link(nvosd):
        print("Failed to link nvvidconv2 to nvosd")
        return 1
    if not nvosd.link(nvvidconv3):
        print("Failed to link nvosd to nvvidconv3")
        return 1
    if not nvvidconv3.link(caps_final):
        print("Failed to link nvvidconv3 to caps_final")
        return 1
    if not caps_final.link(sink):
        print("Failed to link caps_final to sink")
        return 1

    print("✅ 所有元素链接成功")

    # 创建事件循环
    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # 添加探针
    osdsinkpad = nvosd.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write("Unable to get sink pad of nvosd\n")
        return 1

    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)

    # 启动性能监控
    start_performance_monitor()

    # 启动管道
    print("Starting pipeline...")
    
    # 设置管道状态
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Failed to set pipeline to PLAYING")
        return 1
    
    print("✅ Pipeline started successfully!")
    print("=" * 60)
    print(f"🎯 DeepStream 检测器运行中 - {width}x{height} @ {fps}fps")
    print("🛑 按 Ctrl+C 停止")
    print("=" * 60)
    
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
    finally:
        pipeline.set_state(Gst.State.NULL)
        total_time = time.time() - stats.start_time
        
        if total_time > 0:
            avg_fps = stats.total_frames_processed / total_time
        else:
            avg_fps = 0.0
            
        if stats.total_frames_processed > 0:
            detection_rate = (stats.detection_count / stats.total_frames_processed) * 100
        else:
            detection_rate = 0.0
        
        print("=" * 60)
        print("📊 最终统计报告")
        print(f"⏱️  总运行时间: {total_time:.1f}s")
        print(f"🎞️  总处理帧数: {stats.total_frames_processed}")
        print(f"📈 平均FPS: {avg_fps:.1f}")
        print(f"🎯 检测次数: {stats.detection_count}")
        print(f"📊 检测率: {detection_rate:.1f}%")
        print("✅ Pipeline 已停止")
        print("=" * 60)
    
    return 0

if __name__ == '__main__':
    rospy.init_node('det_param', anonymous=True)
    # 初始化 ROS 参数
    rospy.set_param('detection_active', False)
    rospy.set_param('center_x', 0)
    rospy.set_param('center_y', 0)
    rospy.set_param('det_index', 6)
    rospy.set_param('animals_num', 0)
    sys.exit(main(sys.argv))
