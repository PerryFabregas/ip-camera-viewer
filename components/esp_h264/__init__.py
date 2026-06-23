"""
esp_h264 — composant ESP-IDF (décodeur/encodeur H.264 Espressif) vendorisé.

Enregistré comme COMPOSANT ESP-IDF via add_idf_component : c'est son
CMakeLists.txt qui compile les sources, expose les en-têtes publics
(interface/include, sw/include, port/include, hw/include) et linke les libs
précompilées (libtinyh264.a, libopenh264.a).

Cette voie fonctionne avec le moteur PlatformIO ET le moteur CMake/Ninja natif
d'ESPHome (2026.7+). L'ancienne approche (extra_script PlatformIO + -I bricolés)
ne tournait pas dans le build CMake natif, d'où "esp_h264_dec.h: No such file"
sur esphome dev.

Composant interne, tiré par ip_camera_viewer (AUTO_LOAD) — pas de config YAML.
"""

import os

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components.esp32 import add_idf_component

CODEOWNERS = ["@youkorr"]
DEPENDENCIES = ["esp32"]

CONFIG_SCHEMA = cv.Schema({})  # composant interne tiré par ip_camera_viewer (AUTO_LOAD)


async def to_code(config):
    component_dir = os.path.dirname(os.path.abspath(__file__))

    # Enregistre esp_h264 comme composant ESP-IDF local. Son CMakeLists.txt gère
    # sources + includes publics + link des libs. Les includes publics remontent
    # au code esphome (le composant src REQUIERT les composants idf ajoutés via
    # get_managed_component_require_names), donc `#include "esp_h264_dec.h"` se
    # résout sans -I bricolé, dans les deux moteurs de build.
    add_idf_component(name="esp_h264", path=component_dir)

    # Défauts runtime : sur ESP32-P4 le worker dual-task de tinyH264 (lib
    # précompilée) faute en "Instruction address misaligned on core 1" au boot.
    # Désactiver le dual-task supprime ce worker (le vrai décodage High Profile
    # passe de toute façon par edge264 / h264_hp).
    cg.add_build_flag("-DCONFIG_ESP_H264_DUAL_TASK=0")
    cg.add_build_flag("-DCONFIG_ESP_H264_DUAL_TASK_CORE=1")
    cg.add_build_flag("-DCONFIG_ESP_H264_DUAL_TASK_PRIORITY=17")
