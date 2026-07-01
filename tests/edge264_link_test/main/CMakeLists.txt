# Composant "main" du test de link edge264.
# On linke libedge264.a via add_prebuilt_library : ça l'inscrit dans le GROUPE de
# link d'ESP-IDF (--start-group/--end-group), ce qui résout les dépendances
# croisées avec newlib (ex. sysconf) indépendamment de l'ordre. PRIV_REQUIRES
# pthread car edge264 utilise les threads.

set(EDGE264_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../components/h264_hp/edge264")

idf_component_register(
    SRCS "test_main.c"
    INCLUDE_DIRS "${EDGE264_DIR}"
    PRIV_REQUIRES pthread
)

add_prebuilt_library(edge264 "${EDGE264_DIR}/lib/esp32p4/libedge264.a" PRIV_REQUIRES pthread)
target_link_libraries(${COMPONENT_LIB} PUBLIC edge264)
