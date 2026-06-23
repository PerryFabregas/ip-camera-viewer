"""
Build script for ip_camera_viewer component.

Compiles the esp_h264 software decoder sources, adds their (nested) include
dirs, and links the prebuilt H.264 libraries (openh264 / tinyh264 / edge264).

WHY THIS SCRIPT IS THE ROBUST PLACE TO DO IT
--------------------------------------------
ESPHome only copies a component's TOP-LEVEL .c/.h/.cpp files into the build
tree (non-recursive, extension-filtered). The headers and prebuilt libs we
need live in NESTED folders (esp_h264/interface/include, h264_hp/edge264/…),
so they are never copied — they must be reached through include flags that
point back at the ORIGINAL component checkout.

At *codegen* time __init__.py also adds those -I flags, but the path it computes
(from the Python module's __file__) can be a git-clone location that is stale by
*compile* time, or the custom project option carrying it may not be honored by
every ESPHome version. GCC silently ignores a non-existent -I dir, which is
exactly how a build ends up with "esp_h264_dec.h / edge264.h: No such file"
even though the matching -D flag clearly took effect.

This script, by contrast, is executed by PlatformIO from the very file path it
was loaded from, so `__file__` here ALWAYS resolves to the real, present
component directory at compile time. We anchor everything to that and stop
trusting codegen-time paths.
"""

import os
Import("env")


def _resolve_component_dir():
    """Return ip_camera_viewer's dir, validated by the presence of a sibling
    esp_h264/ dir. Tries the most reliable source first."""
    candidates = []
    # 1) This script's own location — PlatformIO loaded it from here, so it is
    #    guaranteed to exist NOW (at build time), unlike codegen-time paths.
    try:
        candidates.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    # 2) Path passed by __init__.py via a custom project option (codegen time).
    try:
        opt = env.GetProjectOption("custom_ipcv_component_dir")
        if opt:
            candidates.append(opt)
    except Exception:
        pass
    # 3) Last resort: SCons current dir (usually the project dir — rarely right).
    try:
        candidates.append(Dir('.').srcnode().abspath)
    except Exception:
        pass

    for c in candidates:
        if c and os.path.isdir(os.path.join(os.path.dirname(c), "esp_h264")):
            return c
    # Nothing validated — fall back to the first non-empty candidate so the
    # diagnostics below still print something useful.
    return next((c for c in candidates if c), os.getcwd())


component_dir = _resolve_component_dir()
parent_components_dir = os.path.dirname(component_dir)

print(f"[IP Camera Viewer] Build script running... (component_dir={component_dir})")

# ========================================================================
# H.264 decoder: include paths + compile sources + link libraries
# ========================================================================
esp_h264_dir = os.path.join(parent_components_dir, "esp_h264")
if os.path.exists(esp_h264_dir):
    # Add all esp_h264 include paths (nested — never copied by ESPHome, so this
    # is what actually makes esp_h264_dec.h & friends resolvable).
    h264_includes = [
        os.path.join(esp_h264_dir, "interface", "include"),
        os.path.join(esp_h264_dir, "port", "include"),
        os.path.join(esp_h264_dir, "port", "inc"),
        os.path.join(esp_h264_dir, "sw", "include"),
        os.path.join(esp_h264_dir, "hw", "include"),
        os.path.join(esp_h264_dir, "sw", "libs", "openh264_inc"),
        os.path.join(esp_h264_dir, "sw", "libs", "tinyh264_inc"),
        os.path.join(esp_h264_dir, "hw", "src"),
        os.path.join(esp_h264_dir, "hw", "hal", "esp32p4"),
        os.path.join(esp_h264_dir, "hw", "soc", "esp32p4"),
    ]
    for inc_path in h264_includes:
        if os.path.exists(inc_path):
            env.Append(CPPPATH=[inc_path])

    # ========================================================================
    # Compile esp_h264 decoder sources (previously done by esp_video_build.py)
    # ========================================================================
    esp_h264_decoder_sources = [
        "port/src/esp_h264_alloc.c",
        "port/src/esp_h264_cache.c",
        "sw/src/esp_h264_dec_sw.c",
        "sw/src/h264_color_convert.c",
        # esp_h264 1.3.6 moved interface sources: interface/include/src -> interface/src
        "interface/src/esp_h264_dec.c",
        "interface/src/esp_h264_dec_param.c",
        "interface/src/esp_h264_version.c",
    ]

    h264_objects = []
    for src in esp_h264_decoder_sources:
        src_path = os.path.join(esp_h264_dir, src)
        if os.path.exists(src_path):
            obj = env.Object(src_path)
            h264_objects.extend(obj)
            print(f"[IP Camera Viewer] + esp_h264/{src}")

    if h264_objects:
        h264_dec_lib = env.StaticLibrary(
            os.path.join("$BUILD_DIR", "libh264_decoder_nc"),
            h264_objects
        )
        env.Prepend(LIBS=[h264_dec_lib])
        print(f"[IP Camera Viewer] Created libh264_decoder_nc.a with decoder sources")

    # ========================================================================
    # Link H.264 libraries: openh264 (encoder/decoder) + tinyh264 (h264bsd decoder)
    # ========================================================================
    h264_lib_dir = os.path.join(esp_h264_dir, "sw", "libs", "esp32p4")
    openh264_lib = os.path.join(h264_lib_dir, "libopenh264.a")
    tinyh264_lib = os.path.join(h264_lib_dir, "libtinyh264.a")

    if os.path.exists(h264_lib_dir):
        env.Append(LIBPATH=[h264_lib_dir])

    if os.path.exists(openh264_lib):
        env.Append(LINKFLAGS=[
            "-Wl,--allow-multiple-definition",
            "-Wl,--whole-archive",
            openh264_lib,
            "-Wl,--no-whole-archive"
        ])
        print(f"[IP Camera Viewer] Linked openh264 (Baseline/Main/High profiles)")
    else:
        print(f"[IP Camera Viewer]  openh264 not found at {openh264_lib}")

    # tinyh264 provides h264bsd* symbols needed by esp_h264_dec_sw.c
    if os.path.exists(tinyh264_lib):
        env.Append(LIBS=["tinyh264"])
        print(f"[IP Camera Viewer] Linked tinyh264 (h264bsd decoder symbols)")
    else:
        print(f"[IP Camera Viewer]  tinyh264 not found at {tinyh264_lib}")
else:
    print(f"[IP Camera Viewer] !! esp_h264 component not found next to "
          f"{component_dir} — esp_h264_dec.h will not resolve. Check that the "
          f"component checkout is complete and lists [ip_camera_viewer, h264_hp, esp_h264].")

# ========================================================================
# edge264 (High Profile) — composant h264_hp auto-chargé, lib précompilée Clang
# ESPHome n'utilise pas le CMakeLists.txt du composant : on gère ici à la fois
# le chemin d'include (edge264/edge264.h) ET le link de la lib précompilée.
# ========================================================================
h264_hp_dir = os.path.join(parent_components_dir, "h264_hp")
edge264_header = os.path.join(h264_hp_dir, "edge264", "edge264.h")
edge264_lib = os.path.join(h264_hp_dir, "edge264", "lib", "esp32p4", "libedge264.a")

# Add the include dir so `#include "edge264/edge264.h"` (in h264_hp_decoder.cpp,
# active when USE_H264_HP_EDGE264 is defined at codegen) resolves from a path
# that is GUARANTEED present at build time — independent of any codegen -I flag.
if os.path.exists(edge264_header):
    env.Append(CPPPATH=[h264_hp_dir, os.path.join(h264_hp_dir, "edge264")])

if os.path.exists(edge264_lib):
    # -Wl,-u,sysconf : force l'inclusion de sysconf (newlib) que référence edge264.
    env.Append(LINKFLAGS=["-Wl,-u,sysconf"])
    # IMPORTANT : libedge264.a doit être en position BIBLIOTHÈQUE (après les objets),
    # pas dans LINKFLAGS. SCons place LINKFLAGS AVANT $SOURCES ; or ld ne tire d'une
    # archive que les membres résolvant un symbole *déjà* indéfini. Placée avant
    # h264_hp_decoder.cpp.o (qui référence edge264_*), l'archive est ignorée ->
    # "undefined reference to edge264_alloc". En LIBS (via un noeud File), elle est
    # scannée après les objets et les symboles edge264_* sont résolus (cf. link-test CI).
    env.Append(LIBS=[File(edge264_lib)])
    print(f"[IP Camera Viewer] Linked libedge264.a (edge264 High Profile)")
else:
    print(f"[IP Camera Viewer]  libedge264.a not found (edge264 High Profile disabled)")

print("[IP Camera Viewer] Build script completed")
