# h264_hp — composant ESP-IDF (décodeur H.264 High Profile via edge264)
#
# Le wrapper C++ est TOUJOURS compilé (mode no-op si edge264 inactif).
#
# edge264 est un "unity build" : on compile UNIQUEMENT edge264/src/edge264.c,
# qui #include les autres .c (headers/bitstream/deblock/inter/intra/mvpred/
# residual/sei/slice). Ne JAMAIS compiler les autres .c séparément (doublons),
# ni edge264_check.c / edge264_test.c (mains de test, non vendorisés).
#
# ⚠️ edge264 sur ESP32-P4 (RISC-V) ne compile QU'AVEC Clang (voir README).
# En GCC il déclenche un #error. Donc on ne l'active QUE si le marqueur
# edge264/ENABLE_EDGE264 est présent (créé volontairement après passage à Clang).

set(H264_HP_SRCS "h264_hp_decoder.cpp")
set(H264_HP_INCS ".")

set(_edge264_enabled FALSE)
if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/edge264/ENABLE_EDGE264"
   AND EXISTS "${CMAKE_CURRENT_LIST_DIR}/edge264/src/edge264.c")
    set(_edge264_enabled TRUE)
    list(APPEND H264_HP_SRCS "edge264/src/edge264.c")  # unity build : ce seul .c
    list(APPEND H264_HP_INCS "edge264" "edge264/src")
endif()

idf_component_register(
    SRCS ${H264_HP_SRCS}
    INCLUDE_DIRS ${H264_HP_INCS}
    REQUIRES esp_common
    PRIV_REQUIRES heap
)

if(_edge264_enabled)
    target_compile_definitions(${COMPONENT_LIB} PUBLIC USE_H264_HP_EDGE264=1)
    # edge264 = code vectoriel intensif : -O3 indispensable (coût CABAC sur P4).
    set_source_files_properties("edge264/src/edge264.c"
        PROPERTIES COMPILE_OPTIONS "-O3")
    message(STATUS "[h264_hp] edge264 ACTIVÉ (High Profile). Vérifiez la toolchain Clang.")
else()
    message(STATUS "[h264_hp] edge264 inactif (no-op). Voir README pour activer (Clang requis).")
endif()
