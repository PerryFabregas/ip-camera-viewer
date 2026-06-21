"""
Composant ESPHome pour ESP H.264 Encoder (esp_h264)
Dépendance d'ESP-Video
"""

import esphome.codegen as cg
import esphome.config_validation as cv
import os

CODEOWNERS = ["@youkorr"]
DEPENDENCIES = ["esp32"]

# Ce composant est une bibliothèque uniquement, pas de configuration utilisateur
CONFIG_SCHEMA = cv.invalid("esp_h264 est un composant interne, ne pas l'utiliser directement dans le YAML")

async def to_code(config):
    """Configure le composant esp_h264 pour ESPHome"""
    component_dir = os.path.dirname(os.path.abspath(__file__))

    # Ajouter les includes
    includes = [
        "interface/include",
        "port/include",
        "port/inc",
        "sw/include",
        "hw/include",
    ]

    for inc in includes:
        inc_path = os.path.join(component_dir, inc)
        if os.path.exists(inc_path):
            cg.add_build_flag(f"-I{inc_path}")

    # DIAGNOSTIC / FIX — "Instruction address misaligned on core 1" at boot.
    # The tinyH264 dual-task worker (prebuilt libtinyh264.a) is spawned on core 1
    # by h264bsdAlloc() during init_h264_decoder_(), which runs unconditionally in
    # setup() (regardless of the switch / RESTORE_DEFAULT_OFF). On ESP32-P4 that
    # worker faults with a misaligned-instruction exception (prebuilt-lib ABI/ISA
    # mismatch or a threading bug). Disabling the dual task removes the core-1
    # worker: if the boot crash disappears, the cause is confirmed.
    # NOTE: single-task tinyH264 is slower and still Baseline-only — the real fix
    # is the edge264-based h264_hp decoder (compiled from source, no prebuilt .a).
    cg.add_build_flag("-DCONFIG_ESP_H264_DUAL_TASK=0")
    cg.add_build_flag("-DCONFIG_ESP_H264_DUAL_TASK_CORE=1")
    cg.add_build_flag("-DCONFIG_ESP_H264_DUAL_TASK_PRIORITY=17")

    # NOTE: Les sources sont compilées par esp_video_build.py (script PlatformIO)
    # Ne pas utiliser cg.add_library() ici pour éviter la double compilation
