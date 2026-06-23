# edge264 — composant ESP-IDF minimal (décodeur H.264 High Profile).
#
# Pas de SRCS : edge264 n'a pas de backend GCC (builtins Clang-only), il est
# précompilé en lib statique (lib/esp32p4/libedge264.a). On expose seulement
# l'en-tête public edge264.h et on inscrit la lib dans le groupe de link ESP-IDF.
#
# Enregistré par h264_hp/__init__.py via esp32.add_idf_component(name="edge264"),
# ce CMakeLists est utilisé aussi bien par le moteur PlatformIO que par le moteur
# CMake/Ninja natif d'ESPHome (2026.7+) — contrairement à un extra_script
# PlatformIO, qui ne s'exécute pas dans le build CMake natif.
idf_component_register(INCLUDE_DIRS ".")

set(_edge264_lib "${CMAKE_CURRENT_LIST_DIR}/lib/esp32p4/libedge264.a")
if(EXISTS "${_edge264_lib}")
    # add_prebuilt_library inscrit libedge264.a dans le groupe de link d'ESP-IDF :
    # les symboles croisés avec newlib (ex. sysconf) se résolvent quel que soit
    # l'ordre. edge264 utilise pthread.
    add_prebuilt_library(edge264_prebuilt "${_edge264_lib}" PRIV_REQUIRES pthread)
    target_link_libraries(${COMPONENT_LIB} INTERFACE edge264_prebuilt)
    message(STATUS "[edge264] libedge264.a inscrit dans le link (High Profile).")
else()
    message(STATUS "[edge264] libedge264.a absent — High Profile indisponible.")
endif()
