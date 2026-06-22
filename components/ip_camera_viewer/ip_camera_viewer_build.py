"""
Build script for ip_camera_viewer component
Compiles esp_h264 decoder sources and links openh264 library
"""

import os
Import("env")

# Le répertoire du composant est transmis par __init__.py via une option custom.
# Dans un extra_script PlatformIO, Dir('.') pointe sur le répertoire PROJET, pas sur
# le composant : on ne peut donc pas retrouver esp_h264/ et h264_hp/ par ce biais.
component_dir = None
try:
    component_dir = env.GetProjectOption("custom_ipcv_component_dir")
except Exception:
    component_dir = None
if not component_dir or not os.path.isdir(component_dir):
    # Repli : ancien comportement (au cas où l'option ne serait pas disponible).
    component_dir = Dir('.').srcnode().abspath
parent_components_dir = os.path.dirname(component_dir)

print(f"[IP Camera Viewer] Build script running... (component_dir={component_dir})")

# ========================================================================
# H.264 decoder: compile sources + link library
# ========================================================================
esp_h264_dir = os.path.join(parent_components_dir, "esp_h264")
if os.path.exists(esp_h264_dir):
    # Add all esp_h264 include paths
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
    print(f"[IP Camera Viewer]  esp_h264 component not found")

# ========================================================================
# edge264 (High Profile) — composant h264_hp auto-chargé, lib précompilée Clang
# ESPHome n'utilise pas le CMakeLists.txt du composant : on linke la lib ici.
# ========================================================================
h264_hp_dir = os.path.join(parent_components_dir, "h264_hp")
edge264_lib = os.path.join(h264_hp_dir, "edge264", "lib", "esp32p4", "libedge264.a")
if os.path.exists(edge264_lib):
    # -Wl,-u,sysconf : force l'inclusion de sysconf (newlib) que référence edge264,
    # indépendamment de l'ordre de link (cf. validation CI).
    env.Append(LINKFLAGS=["-Wl,-u,sysconf", edge264_lib])
    print(f"[IP Camera Viewer] Linked libedge264.a (edge264 High Profile)")
else:
    print(f"[IP Camera Viewer]  libedge264.a not found (edge264 High Profile disabled)")

print("[IP Camera Viewer] Build script completed")
