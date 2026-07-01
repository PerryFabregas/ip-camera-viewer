# h264_hp — composant ESP-IDF (décodeur H.264 High Profile via edge264)
#
# Le wrapper C++ est TOUJOURS compilé (mode no-op si edge264 absent).
#
# STRATÉGIE edge264 sur ESP32-P4 (RISC-V) :
#   edge264 n'a pas de backend GCC (builtins Clang-only). On NE compile donc PAS
#   sa source ici. À la place, on LINKE une lib statique precompilée avec esp-clang :
#       edge264/lib/esp32p4/libedge264.a
#   (à générer une fois via edge264/build_libedge264_esp32p4.sh — voir README).
#   L'ABI RISC-V Clang/GCC est compatible : on linke ce .a dans le build GCC,
#   exactement comme libtinyh264.a / libopenh264.a.

set(H264_HP_SRCS "h264_hp_decoder.cpp")
set(H264_HP_INCS ".")

set(_edge264_lib "${CMAKE_CURRENT_LIST_DIR}/edge264/lib/esp32p4/libedge264.a")
set(_edge264_enabled FALSE)
if(EXISTS "${_edge264_lib}" AND EXISTS "${CMAKE_CURRENT_LIST_DIR}/edge264/edge264.h")
    set(_edge264_enabled TRUE)
    list(APPEND H264_HP_INCS "edge264")  # pour <edge264.h>
endif()

idf_component_register(
    SRCS ${H264_HP_SRCS}
    INCLUDE_DIRS ${H264_HP_INCS}
    REQUIRES esp_common
    PRIV_REQUIRES heap pthread
)

if(_edge264_enabled)
    target_compile_definitions(${COMPONENT_LIB} PUBLIC USE_H264_HP_EDGE264=1)
    # add_prebuilt_library inscrit libedge264.a dans le groupe de link d'ESP-IDF,
    # ce qui résout les dépendances croisées avec newlib (ex. sysconf) quel que
    # soit l'ordre. edge264 utilise pthread.
    add_prebuilt_library(edge264 "${_edge264_lib}" PRIV_REQUIRES pthread)
    target_link_libraries(${COMPONENT_LIB} PUBLIC edge264)
    message(STATUS "[h264_hp] edge264 ACTIVÉ — link de libedge264.a (High Profile).")
else()
    message(STATUS "[h264_hp] edge264 inactif (no-op). Génère edge264/lib/esp32p4/"
                   "libedge264.a avec build_libedge264_esp32p4.sh — voir README.")
endif()
