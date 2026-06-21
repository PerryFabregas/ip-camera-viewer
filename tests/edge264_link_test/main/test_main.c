// Test de LINK : valide que libedge264.a (compilé esp-clang) se linke dans un
// build ESP32-P4 GCC, et que ses dépendances système (pthread/sysconf/malloc/
// clock_gettime...) sont résolues. On ne fait que BUILD (idf.py build) — pas
// d'exécution. Référencer tous les symboles publics force le linker à résoudre
// edge264.o entièrement.
#include <stdint.h>
#include <stddef.h>
#include "edge264.h"

void app_main(void) {
  const uint8_t buf[4] = {0, 0, 0, 1};
  Edge264Decoder *dec = edge264_alloc(0, NULL, NULL, 0, NULL, NULL, NULL);
  if (dec != NULL) {
    edge264_decode_NAL(dec, buf, buf + sizeof(buf), NULL, NULL);
    Edge264Frame frame;
    edge264_get_frame(dec, &frame, 0);
    edge264_return_frame(dec, NULL);
    edge264_flush(dec);
    edge264_free(&dec);
  }
  (void) edge264_find_start_code(buf, buf + sizeof(buf), 1);
}
