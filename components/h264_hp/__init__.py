"""
h264_hp — Décodeur H.264 High Profile léger pour ESP32-P4 (basé sur edge264, BSD).

Composant INTERNE (bibliothèque) : pas de configuration YAML propre. Destiné à
remplacer le chemin tinyH264 (Baseline only) de ip_camera_viewer pour décoder
les flux Main/High profile.

La compilation des sources edge264 est pilotée par CMakeLists.txt (ESP-IDF) :
elle n'est ACTIVE que si le marqueur edge264/ENABLE_EDGE264 existe — voir README.

⚠️ edge264 sur ESP32-P4 (RISC-V) ne compile qu'avec la toolchain Clang d'ESP-IDF.
En GCC (PlatformIO par défaut), NE PAS créer le marqueur : le wrapper reste en
mode no-op et le build reste vert.
"""

import os

import esphome.codegen as cg
import esphome.config_validation as cv

CODEOWNERS = ["@youkorr"]
DEPENDENCIES = ["esp32"]

CONFIG_SCHEMA = cv.invalid(
    "h264_hp est un composant interne (bibliothèque de décodage H.264 High "
    "Profile). Ne le déclarez pas dans le YAML ; il est tiré par ip_camera_viewer."
)


async def to_code(config):
    component_dir = os.path.dirname(os.path.abspath(__file__))
    edge264_dir = os.path.join(component_dir, "edge264")
    marker = os.path.join(edge264_dir, "ENABLE_EDGE264")

    has_src = os.path.exists(os.path.join(edge264_dir, "src", "edge264.c"))
    enabled = has_src and os.path.exists(marker)

    if enabled:
        print("[h264_hp] edge264 ACTIVÉ (High Profile) — toolchain Clang requise.")
    elif has_src:
        print(
            "[h264_hp] edge264 vendorisé mais INACTIF (no-op). Pour l'activer : "
            "passer en toolchain Clang puis créer components/h264_hp/edge264/ENABLE_EDGE264."
        )
    else:
        print("[h264_hp] sources edge264 absentes — décodeur High Profile indisponible.")
