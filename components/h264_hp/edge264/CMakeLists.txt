# edge264 — composant ESP-IDF minimal (décodeur H.264 High Profile).
#
# edge264 n'a pas de backend GCC (builtins Clang-only) : il est précompilé en lib
# statique (lib/esp32p4/libedge264.a). On expose l'en-tête public edge264.h et on
# inscrit la lib dans le groupe de link ESP-IDF. La seule source compilée ici est
# psram_alloc.c (redirection PSRAM, voir plus bas).
#
# Enregistré par h264_hp/__init__.py via esp32.add_idf_component(name="edge264"),
# ce CMakeLists est utilisé par le moteur PlatformIO ET le moteur CMake/Ninja
# natif d'ESPHome (2026.7+) — contrairement à un extra_script PlatformIO.

set(_edge264_lib "${CMAKE_CURRENT_LIST_DIR}/lib/esp32p4/libedge264.a")

set(_edge264_srcs "")
if(EXISTS "${_edge264_lib}")
    # psram_alloc.c fournit __wrap_aligned_alloc (cf. -Wl,--wrap plus bas).
    set(_edge264_srcs "psram_alloc.c")
endif()

idf_component_register(SRCS ${_edge264_srcs} INCLUDE_DIRS "." REQUIRES heap log)

if(EXISTS "${_edge264_lib}")
    # add_prebuilt_library inscrit libedge264.a dans le groupe de link d'ESP-IDF :
    # les symboles croisés avec newlib (ex. sysconf) se résolvent quel que soit
    # l'ordre. edge264 utilise pthread.
    add_prebuilt_library(edge264_prebuilt "${_edge264_lib}" PRIV_REQUIRES pthread)
    target_link_libraries(${COMPONENT_LIB} PUBLIC edge264_prebuilt)

    # edge264_alloc() alloue sa structure décodeur (~41 Ko) via aligned_alloc, qui
    # sur ESP-IDF ne tire QUE de la DRAM interne — trop juste au runtime (LVGL +
    # MIPI-DSI) -> "edge264_alloc a échoué". On intercepte aligned_alloc pour router
    # les gros blocs vers la PSRAM (voir psram_alloc.c). --wrap doit être un flag de
    # LINK global de l'app, d'où idf_build_set_property.
    # Deux mécanismes pour attacher --wrap au lien de l'app (selon la version
    # d'ESPHome dev, l'un ou l'autre peut ne pas être honoré pour un composant
    # ajouté par chemin) :
    #  1) propriété de build globale ESP-IDF,
    #  2) options de lien INTERFACE du composant (propagées via le graphe de deps).
    # __wrap_aligned_alloc est dans psram_alloc.c (archive de CE composant) ; sans
    # -u, ld résout les appels "wrappés" de libedge264.a AVANT d'examiner ce membre
    # -> "undefined reference to __wrap_aligned_alloc". -u force le chargement.
    idf_build_set_property(LINK_OPTIONS "-Wl,--wrap=aligned_alloc" APPEND)
    idf_build_set_property(LINK_OPTIONS "-Wl,-u,__wrap_aligned_alloc" APPEND)
    target_link_options(${COMPONENT_LIB} INTERFACE
        "-Wl,--wrap=aligned_alloc" "-Wl,-u,__wrap_aligned_alloc")
    message(STATUS "[edge264] libedge264.a linké ; aligned_alloc routé vers la PSRAM.")
else()
    message(STATUS "[edge264] libedge264.a absent — High Profile indisponible.")
endif()
