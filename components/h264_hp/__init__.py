"""
h264_hp — Décodeur H.264 High Profile léger pour ESP32-P4 (basé sur edge264, BSD).

Composant INTERNE (bibliothèque) : pas de configuration YAML propre. Destiné à
remplacer le chemin tinyH264 (Baseline only) de ip_camera_viewer pour décoder
les flux Main/High profile.

STRATÉGIE (voir README) : edge264 n'a pas de backend GCC. On le compile UNE FOIS
avec esp-clang (RISC-V) en une lib statique edge264/lib/esp32p4/libedge264.a, puis
on la LINKE dans le build ESPHome/GCC. Le linkage est géré par CMakeLists.txt :
- si libedge264.a est présent -> USE_H264_HP_EDGE264 + link, le wrapper décode ;
- sinon -> wrapper no-op, build inchangé.
"""

import os

import esphome.codegen as cg
import esphome.config_validation as cv

CODEOWNERS = ["@youkorr"]
DEPENDENCIES = ["esp32"]

CONFIG_SCHEMA = cv.Schema({})  # composant interne tiré par ip_camera_viewer (AUTO_LOAD)


async def to_code(config):
    component_dir = os.path.dirname(os.path.abspath(__file__))
    lib = os.path.join(component_dir, "edge264", "lib", "esp32p4", "libedge264.a")
    has_header = os.path.exists(os.path.join(component_dir, "edge264", "edge264.h"))

    if os.path.exists(lib):
        # Flag GLOBAL : permet à ip_camera_viewer de router vers edge264 (le link
        # effectif du .a est géré par CMakeLists.txt de ce composant).
        cg.add_build_flag("-DUSE_H264_HP_EDGE264")
        print("[h264_hp] libedge264.a présent — décodeur High Profile ACTIVÉ (link).")
    elif has_header:
        print(
            "[h264_hp] edge264 source vendorisée mais libedge264.a ABSENT (no-op). "
            "Génère-la : components/h264_hp/edge264/build_libedge264_esp32p4.sh (esp-clang)."
        )
    else:
        print("[h264_hp] edge264 absent — décodeur High Profile indisponible.")
