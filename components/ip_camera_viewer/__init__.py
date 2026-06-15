import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_URL
import os

DEPENDENCIES = ["wifi"]
CODEOWNERS = ["@youkorr"]

CONF_CANVAS_ID = "canvas_id"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_WIDTH = "width"
CONF_HEIGHT = "height"
CONF_PROTOCOL = "protocol"

ip_camera_viewer_ns = cg.esphome_ns.namespace("ip_camera_viewer")
IPCameraViewer = ip_camera_viewer_ns.class_("IPCameraViewer", cg.Component)

def _validate_url_protocol(config):
    """Catch the common url/protocol mismatch at compile time."""
    url = config[CONF_URL]
    proto = config[CONF_PROTOCOL]
    scheme = url.split("://", 1)[0].lower() if "://" in url else ""
    if scheme == "rtsp" and proto == "mjpeg":
        raise cv.Invalid(
            "An 'rtsp://' URL requires 'protocol: rtsp' (or 'h264'). "
            "'protocol: mjpeg' is only for http:// MJPEG streams (e.g. via go2rtc)."
        )
    if scheme in ("http", "https") and proto in ("rtsp", "h264"):
        raise cv.Invalid(
            "An 'http(s)://' URL is not valid with 'protocol: rtsp/h264'. "
            "Use 'protocol: mjpeg' for http MJPEG streams, or an 'rtsp://' URL for RTSP."
        )
    return config


# Single camera schema
IP_CAMERA_VIEWER_SCHEMA = cv.All(cv.Schema({
    cv.GenerateID(): cv.declare_id(IPCameraViewer),
    cv.Required(CONF_URL): cv.string,
    cv.Required(CONF_CANVAS_ID): cv.string,
    cv.Required(CONF_WIDTH): cv.int_range(min=16, max=1920),
    cv.Required(CONF_HEIGHT): cv.int_range(min=16, max=1080),
    cv.Optional(CONF_PROTOCOL, default="mjpeg"): cv.one_of("mjpeg", "rtsp", "h264", lower=True),
    cv.Optional(CONF_UPDATE_INTERVAL, default="100ms"): cv.positive_time_period_milliseconds,
}).extend(cv.COMPONENT_SCHEMA), _validate_url_protocol)

# Support multiple cameras as a list
CONFIG_SCHEMA = cv.All(
    cv.ensure_list(IP_CAMERA_VIEWER_SCHEMA),
)


async def to_code(config):
    # ESP32-P4 specific build flags for hardware decoders (once for all cameras)
    # Note: H264/JPEG decoders are built-in ESP-IDF components for ESP32-P4
    cg.add_build_flag("-DCONFIG_IDF_TARGET_ESP32P4=1")
    cg.add_build_flag("-DCONFIG_JPEG_ENABLE_DEBUG_LOG=0")
    cg.add_build_flag("-DCONFIG_ESP_H264_DECODER=1")

    # Add esp_h264 include paths for H.264 decoder headers
    component_dir = os.path.dirname(__file__)
    parent_components_dir = os.path.dirname(component_dir)
    esp_h264_dir = os.path.join(parent_components_dir, "esp_h264")
    if os.path.exists(esp_h264_dir):
        h264_includes = [
            "interface/include",
            "port/include",
            "port/inc",
            "sw/include",
            "hw/include",
            "sw/libs/openh264_inc",
            "sw/libs/tinyh264_inc",
        ]
        for inc in h264_includes:
            inc_path = os.path.join(esp_h264_dir, inc)
            if os.path.exists(inc_path):
                cg.add_build_flag(f"-I{inc_path}")

    # Add PlatformIO build script for H.264 library linking and source compilation
    build_script = os.path.join(os.path.dirname(__file__), "ip_camera_viewer_build.py")
    cg.add_platformio_option("extra_scripts", ["post:" + build_script])

    # Process each camera in the list
    for cam_config in config:
        var = cg.new_Pvariable(cam_config[CONF_ID])
        await cg.register_component(var, cam_config)

        cg.add(var.set_url(cam_config[CONF_URL]))
        cg.add(var.set_width(cam_config[CONF_WIDTH]))
        cg.add(var.set_height(cam_config[CONF_HEIGHT]))
        cg.add(var.set_protocol(cam_config[CONF_PROTOCOL]))

        update_interval_ms = cam_config[CONF_UPDATE_INTERVAL].total_milliseconds
        cg.add(var.set_update_interval(int(update_interval_ms)))
