# h264_hp — composant ESP-IDF (décodeur H.264 High Profile via edge264)
#
# Le wrapper C++ est toujours compilé. Les sources edge264 ne sont compilées
# que si le sous-module est présent (components/h264_hp/edge264/).

set(H264_HP_SRCS "h264_hp_decoder.cpp")
set(H264_HP_INCS "." )

# Détection d'edge264 vendorisé
if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/edge264/edge264.h")
    file(GLOB EDGE264_SRCS "${CMAKE_CURRENT_LIST_DIR}/edge264/*.c")
    list(APPEND H264_HP_SRCS ${EDGE264_SRCS})
    list(APPEND H264_HP_INCS "edge264")
endif()

idf_component_register(
    SRCS ${H264_HP_SRCS}
    INCLUDE_DIRS ${H264_HP_INCS}
    REQUIRES esp_common
    PRIV_REQUIRES heap
)

if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/edge264/edge264.h")
    target_compile_definitions(${COMPONENT_LIB} PUBLIC USE_H264_HP_EDGE264=1)
    # RISC-V P4 : pas de SIMD natif. edge264 requiert les vector extensions
    # (Clang >= 15). Avec GCC, fournir un fallback scalaire / -mno-* selon test.
    # Optimisation perf : indispensable vu le coût CABAC.
    set_source_files_properties(${EDGE264_SRCS} PROPERTIES COMPILE_OPTIONS "-O3")
endif()
