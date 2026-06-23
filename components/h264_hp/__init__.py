"""
h264_hp — Décodeur H.264 High Profile léger pour ESP32-P4 (basé sur edge264, BSD).

Composant INTERNE (bibliothèque) : pas de configuration YAML propre. Destiné à
remplacer le chemin tinyH264 (Baseline only) de ip_camera_viewer pour décoder
les flux Main/High profile.

STRATÉGIE : edge264 n'a pas de backend GCC ; il est précompilé en lib statique
(edge264/lib/esp32p4/libedge264.a). On l'expose via un COMPOSANT ESP-IDF
"edge264" (edge264/CMakeLists.txt) enregistré avec add_idf_component :
- l'en-tête edge264.h devient public (résolu par #include "edge264.h") ;
- libedge264.a est inscrite dans le groupe de link ESP-IDF.
Cette voie fonctionne avec le moteur PlatformIO ET le moteur CMake/Ninja natif
d'ESPHome (2026.7+). L'ancien extra_script PlatformIO ne tournait pas dans le
build CMake natif — d'où les "edge264.h: No such file" sur esphome dev.

Si libedge264.a est absent -> wrapper no-op, build inchangé.
"""

import os

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components.esp32 import add_idf_component, add_idf_sdkconfig_option

CODEOWNERS = ["@youkorr"]
DEPENDENCIES = ["esp32"]

CONFIG_SCHEMA = cv.Schema({})  # composant interne tiré par ip_camera_viewer (AUTO_LOAD)


async def to_code(config):
    component_dir = os.path.dirname(os.path.abspath(__file__))
    edge264_dir = os.path.join(component_dir, "edge264")
    lib = os.path.join(edge264_dir, "lib", "esp32p4", "libedge264.a")

    if os.path.exists(lib):
        # Enregistre edge264/ comme composant ESP-IDF local. Son CMakeLists.txt
        # expose edge264.h (include public) et linke libedge264.a. Le define
        # active le code edge264 dans le wrapper (h264_hp_decoder.cpp).
        add_idf_component(name="edge264", path=edge264_dir)
        cg.add_build_flag("-DUSE_H264_HP_EDGE264")

        # --- PSRAM pour l'allocation du décodeur ------------------------------
        # edge264_alloc() alloue sa structure (~41 Ko) via aligned_alloc(). Par
        # défaut le composant `psram` d'ESPHome configure la PSRAM en
        # CONFIG_SPIRAM_USE_CAPS_ALLOC : la PSRAM n'est alors atteignable que par
        # heap_caps_*, PAS par malloc/aligned_alloc -> edge264 ne voit que la DRAM
        # interne (épuisée au runtime avec LVGL + MIPI-DSI) et echoue.
        # On bascule le choix Kconfig sur USE_MALLOC : malloc/aligned_alloc peuvent
        # alors puiser dans la PSRAM. Les petites allocations (< 16 Ko, souvent DMA)
        # restent en interne. Indépendant de la propagation de -Wl,--wrap (qui peut
        # ne pas passer selon le snapshot d'ESPHome dev).
        add_idf_sdkconfig_option("CONFIG_SPIRAM_USE_CAPS_ALLOC", False)
        add_idf_sdkconfig_option("CONFIG_SPIRAM_USE_MALLOC", True)
        add_idf_sdkconfig_option("CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL", 16384)

        # --- Pile des threads worker edge264 ----------------------------------
        # edge264 crée ses threads worker via pthread_create(..., NULL, ...) =>
        # pile = CONFIG_PTHREAD_TASK_STACK_SIZE_DEFAULT (~3 Ko par défaut). Le
        # décodage H.264 (CABAC, IDCT, déblocage) déborde largement -> "Fault" dans
        # worker_loop sur le core 1. On agrandit la pile pthread par défaut.
        add_idf_sdkconfig_option("CONFIG_PTHREAD_TASK_STACK_SIZE_DEFAULT", 32768)

        print("[h264_hp] libedge264.a présent — High Profile ACTIVÉ (composant idf edge264).")
    else:
        print(
            "[h264_hp] libedge264.a ABSENT — décodeur High Profile no-op. "
            "Génère-la : components/h264_hp/edge264/build_libedge264_esp32p4.sh (esp-clang)."
        )
