#pragma once
//
// h264_hp — Décodeur H.264 *High Profile* léger pour ESP32-P4
// Wrapper C++ autour d'edge264 (https://github.com/tvlabs/edge264, licence BSD).
//
// Pourquoi ce composant ?
//   Le décodeur logiciel d'Espressif (esp_h264_dec_sw -> tinyH264/h264bsd) ne
//   gère QUE le Constrained Baseline. Les flux IP-cam en Main/High échouent
//   (alors que VLC les lit, car VLC utilise un décodeur complet type FFmpeg).
//   edge264 est le décodeur *léger* qui gère Baseline/Main/High (CABAC, IDCT
//   8x8, matrices de quantification, B-slices) — donc « comme VLC », en embarqué.
//
// Cible : ESP32-P4 (RISC-V). edge264 n'a pas de SIMD RISC-V : code scalaire,
//   donc viser des résolutions basses/moyennes. Toute la mémoire passe en PSRAM.
//
// Sortie : 3 plans Y/Cb/Cr 4:2:0 8 bits (= I420), exactement le format attendu
//   par ip_camera_viewer.
//
#include <cstdint>
#include <cstddef>

namespace esphome {
namespace h264_hp {

// Décrit une image décodée (plans pointant dans la mémoire interne d'edge264).
// Valide jusqu'au prochain release_frame()/decode. Ne pas free() ces pointeurs.
struct DecodedFrame {
  const uint8_t *y{nullptr};   // plan luma
  const uint8_t *cb{nullptr};  // plan chroma bleu
  const uint8_t *cr{nullptr};  // plan chroma rouge
  int width{0};                // largeur utile (après crop)
  int height{0};               // hauteur utile (après crop)
  int stride_y{0};             // pas mémoire du plan Y (octets/ligne)
  int stride_c{0};             // pas mémoire des plans chroma
};

// Codes de retour de decode_nal().
enum class DecodeStatus {
  OK = 0,          // NAL consommée, une ou plusieurs frames peuvent être prêtes
  NEED_MORE,       // NAL consommée, pas (encore) de frame complète
  NO_DECODER,      // décodeur non initialisé / edge264 absent du build
  ERROR,           // erreur de décodage
};

class H264HpDecoder {
 public:
  H264HpDecoder() = default;
  ~H264HpDecoder();

  // n_threads : 0 = mono-thread ; sur P4 dual-core, 2 recommandé.
  // Retourne false si l'allocation du décodeur échoue.
  bool begin(int n_threads = 2);

  // Détruit le décodeur et libère la PSRAM associée.
  void end();

  // Fournit UNE NAL unit (sans le start-code Annex-B 00 00 00 01).
  // `data`/`len` = corps de la NAL. À appeler SPS, PPS, puis slices.
  DecodeStatus decode_nal(const uint8_t *data, size_t len);

  // Variante Annex-B : `data`/`len` peut contenir plusieurs NAL séparées par
  // des start-codes ; le wrapper les découpe via edge264_find_start_code().
  DecodeStatus decode_annexb(const uint8_t *data, size_t len);

  // Récupère la prochaine frame décodée disponible. Retourne false si aucune.
  // `out` reste valide jusqu'au prochain get_frame()/release_frame()/decode_*.
  bool get_frame(DecodedFrame *out);

  // Rend la frame empruntée au décodeur (à appeler après usage de get_frame()).
  void release_frame();

  bool is_ready() const { return dec_ != nullptr; }

  // Statistiques simples
  uint32_t frames_decoded() const { return frames_decoded_; }
  uint32_t decode_errors() const { return decode_errors_; }

 private:
  // Opaque vers Edge264Decoder pour ne pas imposer l'include edge264.h ici.
  void *dec_{nullptr};
  bool frame_borrowed_{false};
  uint32_t frames_decoded_{0};
  uint32_t decode_errors_{0};
};

}  // namespace h264_hp
}  // namespace esphome
