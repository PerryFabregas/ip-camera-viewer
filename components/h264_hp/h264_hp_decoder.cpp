#include "h264_hp_decoder.h"

#include "esphome/core/log.h"
#include "esp_heap_caps.h"

// edge264 (vendorisé sous components/h264_hp/edge264/). Voir README pour le
// sous-module. Tant que la source n'est pas présente, le composant compile en
// mode "no-op" pour ne pas casser le build (USE_H264_HP_EDGE264 non défini).
#if defined(USE_H264_HP_EDGE264)
extern "C" {
// Chemin relatif au sous-dossier vendorisé : robuste sans dépendre d'un -I
// (ESPHome copie h264_hp/ et son sous-dossier edge264/ dans l'arbre de build).
#include "edge264/edge264.h"
}
#endif

namespace esphome {
namespace h264_hp {

static const char *const TAG = "h264_hp";

#if defined(USE_H264_HP_EDGE264)
// --- Callbacks d'allocation : tout en PSRAM -------------------------------
// edge264 demande deux buffers par image : `samples` (plans YCbCr) et `mbs`
// (état macrobloc). Sur P4 ils sont volumineux -> PSRAM obligatoire.
static void psram_alloc_cb(void **samples, unsigned samples_size, void **mbs,
                           unsigned mbs_size, int /*errno_on_fail*/, void * /*arg*/) {
  *samples = heap_caps_aligned_alloc(64, samples_size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  *mbs = heap_caps_aligned_alloc(64, mbs_size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
}

static void psram_free_cb(void *samples, void *mbs, void * /*arg*/) {
  heap_caps_free(samples);
  heap_caps_free(mbs);
}

static int log_cb(const char *str, void * /*arg*/) {
  ESP_LOGV(TAG, "edge264: %s", str);
  return 0;
}

static inline Edge264Decoder *dec_of(void *p) { return static_cast<Edge264Decoder *>(p); }
#endif

H264HpDecoder::~H264HpDecoder() { this->end(); }

bool H264HpDecoder::begin(int n_threads) {
#if defined(USE_H264_HP_EDGE264)
  if (this->dec_ != nullptr)
    return true;
  // edge264_alloc(n_threads, log_cb, log_arg, log_mbs, alloc_cb, free_cb, alloc_arg)
  this->dec_ = edge264_alloc(n_threads, log_cb, nullptr, 0, psram_alloc_cb, psram_free_cb, nullptr);
  if (this->dec_ == nullptr) {
    ESP_LOGE(TAG, "edge264_alloc a échoué (PSRAM insuffisante ?)");
    return false;
  }
  ESP_LOGI(TAG, "Décodeur H.264 High Profile prêt (edge264, %d thread(s))", n_threads);
  return true;
#else
  ESP_LOGE(TAG, "edge264 non vendorisé : ajoutez le sous-module et -DUSE_H264_HP_EDGE264 (voir README)");
  (void) n_threads;
  return false;
#endif
}

void H264HpDecoder::end() {
#if defined(USE_H264_HP_EDGE264)
  if (this->frame_borrowed_)
    this->release_frame();
  if (this->dec_ != nullptr) {
    Edge264Decoder *d = dec_of(this->dec_);
    edge264_free(&d);
    this->dec_ = nullptr;
  }
#endif
}

DecodeStatus H264HpDecoder::decode_nal(const uint8_t *data, size_t len) {
#if defined(USE_H264_HP_EDGE264)
  if (this->dec_ == nullptr)
    return DecodeStatus::NO_DECODER;
  // edge264_decode_NAL attend [buf, end) du *corps* de la NAL.
  int ret = edge264_decode_NAL(dec_of(this->dec_), data, data + len, nullptr, nullptr);
  if (ret < 0) {
    this->decode_errors_++;
    return DecodeStatus::ERROR;
  }
  return DecodeStatus::OK;
#else
  (void) data; (void) len;
  return DecodeStatus::NO_DECODER;
#endif
}

DecodeStatus H264HpDecoder::decode_annexb(const uint8_t *data, size_t len) {
#if defined(USE_H264_HP_EDGE264)
  if (this->dec_ == nullptr)
    return DecodeStatus::NO_DECODER;
  const uint8_t *buf = data;
  const uint8_t *end = data + len;
  DecodeStatus last = DecodeStatus::NEED_MORE;
  // Découpe Annex-B : avance de start-code en start-code.
  const uint8_t *nal = edge264_find_start_code(buf, end, 0);
  while (nal < end) {
    const uint8_t *next = edge264_find_start_code(nal, end, 0);
    int ret = edge264_decode_NAL(dec_of(this->dec_), nal, next, nullptr, nullptr);
    if (ret < 0) {
      this->decode_errors_++;
      last = DecodeStatus::ERROR;
    } else if (last != DecodeStatus::ERROR) {
      last = DecodeStatus::OK;
    }
    nal = next;
  }
  return last;
#else
  (void) data; (void) len;
  return DecodeStatus::NO_DECODER;
#endif
}

bool H264HpDecoder::get_frame(DecodedFrame *out) {
#if defined(USE_H264_HP_EDGE264)
  if (this->dec_ == nullptr || out == nullptr)
    return false;
  if (this->frame_borrowed_)
    this->release_frame();

  Edge264Frame f;
  // borrow=1 : on emprunte les buffers (pas de copie). Rendre via release_frame().
  int ret = edge264_get_frame(dec_of(this->dec_), &f, 1);
  if (ret != 0)
    return false;  // pas de frame disponible

  this->frame_borrowed_ = true;
  this->frames_decoded_++;

  out->y = f.samples[0];
  out->cb = f.samples[1];
  out->cr = f.samples[2];
  // frame_crop_offsets = {top, right, bottom, left} (en pixels). La taille codée
  // (width_Y/height_Y) est alignée macrobloc ; on retire le crop pour la taille
  // d'affichage. Les plans pointent sur l'origine codée ; pour des flux caméra
  // le crop gauche/haut est généralement nul (seuls bas/droite alignent au MB).
  const int crop_top = f.frame_crop_offsets[0];
  const int crop_right = f.frame_crop_offsets[1];
  const int crop_bottom = f.frame_crop_offsets[2];
  const int crop_left = f.frame_crop_offsets[3];
  out->width = f.width_Y - crop_left - crop_right;
  out->height = f.height_Y - crop_top - crop_bottom;
  out->stride_y = f.stride_Y;
  out->stride_c = f.stride_C;
  return true;
#else
  (void) out;
  return false;
#endif
}

void H264HpDecoder::release_frame() {
#if defined(USE_H264_HP_EDGE264)
  if (this->dec_ != nullptr && this->frame_borrowed_) {
    edge264_return_frame(dec_of(this->dec_), nullptr);
    this->frame_borrowed_ = false;
  }
#endif
}

}  // namespace h264_hp
}  // namespace esphome
