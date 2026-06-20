"""
h264_hp — Décodeur H.264 High Profile léger pour ESP32-P4 (basé sur edge264).

Composant INTERNE (bibliothèque) : il n'a pas de configuration YAML propre.
Il est destiné à être utilisé par ip_camera_viewer comme remplaçant du chemin
tinyH264 (Baseline only) afin de décoder les flux Main/High profile.

Intégration edge264 :
  Les sources d'edge264 (licence BSD) doivent être présentes dans
  components/h264_hp/edge264/ (sous-module git — voir README.md).
  Quand elles sont là, ce composant les compile et définit USE_H264_HP_EDGE264.
  Sinon, le wrapper compile en mode no-op (begin() renvoie false) pour ne pas
  casser le build.
"""

import os

import esphome.codegen as cg
import esphome.config_validation as cv

CODEOWNERS = ["@youkorr"]
DEPENDENCIES = ["esp32"]

# Pas d'utilisation directe dans le YAML.
CONFIG_SCHEMA = cv.invalid(
    "h264_hp est un composant interne (bibliothèque de décodage). "
    "Ne le déclarez pas dans le YAML ; il est tiré par ip_camera_viewer."
)


async def to_code(config):
    component_dir = os.path.dirname(os.path.abspath(__file__))
    edge264_dir = os.path.join(component_dir, "edge264")

    # Include du wrapper
    cg.add_build_flag(f"-I{component_dir}")

    if os.path.isdir(edge264_dir) and os.path.exists(os.path.join(edge264_dir, "edge264.h")):
        # edge264 vendorisé : on active le vrai décodeur.
        cg.add_build_flag(f"-I{edge264_dir}")
        cg.add_build_flag("-DUSE_H264_HP_EDGE264")

        # edge264 s'appuie sur les "vector extensions" du compilateur. Sur P4
        # (RISC-V, pas de SIMD), Clang >= 15 mappe en scalaire. La compilation
        # des .c edge264 est faite par le script PlatformIO h264_hp_build.py
        # (comme esp_h264) pour maîtriser les flags par fichier.
        print("[h264_hp] edge264 détecté : décodeur High Profile activé")
    else:
        print(
            "[h264_hp] edge264 absent (components/h264_hp/edge264/). "
            "Décodeur High Profile DÉSACTIVÉ — voir README.md pour le sous-module."
        )
