# Composant "main" du test de link edge264.
# - compile test_main.c
# - linke la lib statique edge264 (compilée esp-clang, ABI RISC-V compatible GCC)
# - pthread est requis par edge264 (threads)

set(EDGE264_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../components/h264_hp/edge264")

idf_component_register(
    SRCS "test_main.c"
    INCLUDE_DIRS "${EDGE264_DIR}"
    PRIV_REQUIRES pthread
)

target_link_libraries(${COMPONENT_LIB} "${EDGE264_DIR}/lib/esp32p4/libedge264.a")
