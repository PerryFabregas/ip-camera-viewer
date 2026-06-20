# h264_hp — Décodeur H.264 **High Profile** léger pour ESP32-P4

Composant interne fournissant un décodeur H.264 **Baseline / Main / High**
(« comme VLC », en logiciel) pour l'ESP32-P4, là où le décodeur Espressif
(`esp_h264_dec_sw` → tinyH264/h264bsd) ne gère que le **Constrained Baseline**.

Il s'appuie sur **[edge264](https://github.com/tvlabs/edge264)** (décodeur H.264
open-source, **licence BSD**, axé légèreté/vitesse), encapsulé dans une API C++
simple et orienté ESPHome.

---

## Pourquoi ce composant existe

| Décodeur | Profils | Sur P4 |
| -------- | ------- | ------ |
| Bloc matériel ESP32-P4 | — | ❌ **pas de décodeur HW** (encodeur seul) |
| tinyH264 / h264bsd (`esp_h264_dec_sw`, actuel) | **Baseline only** | ✅ mais échoue sur Main/High |
| **edge264 (ce composant)** | **Baseline / Main / High** (CABAC, 8×8, B-slices) | ✅ logiciel, scalaire |

C'est la raison du symptôme classique : **VLC lit le flux, l'ESP32-P4 non** —
parce que la caméra émet du Main/High et que seul le Baseline était décodé.

---

## ⚠️ Réalité de performance (à lire avant d'espérer du 1080p)

edge264 tire sa vitesse du **SIMD** (SSE/AVX sur x86, NEON sur ARM). L'**ESP32-P4
est RISC-V sans SIMD** → edge264 tourne en **code scalaire**. Conséquences :

- Performances **bien inférieures** au benchmark desktop d'edge264.
- Estimation **non garantie, à mesurer sur hardware** : exploitable en
  **basse/moyenne résolution** (VGA ~10-20 fps), **pas en 1080p30**.
- CABAC (Main/High) est séquentiel et coûteux : c'est le facteur limitant.
- Limites edge264 actuelles : **8 bits, 4:2:0** uniquement ; pré-production
  (gel d'API visé 2027). Suffisant pour des flux IP-cam standards.

Si la perf est insuffisante, l'alternative pragmatique reste de **transcoder en
amont** (go2rtc/ffmpeg → Baseline), que le chemin tinyH264 existant décode déjà.

---

## Installation d'edge264 (sous-module)

Les sources edge264 ne sont **pas** incluses ici (licence BSD à conserver telle
quelle). Ajoutez-les sous `edge264/` :

```sh
cd ip-camera-viewer
git submodule add https://github.com/tvlabs/edge264 components/h264_hp/edge264
git submodule update --init --recursive
```

Dès que `components/h264_hp/edge264/edge264.h` est présent :
- `__init__.py` définit automatiquement `-DUSE_H264_HP_EDGE264`,
- `CMakeLists.txt` compile les `edge264/*.c`,
- le wrapper bascule du mode no-op au vrai décodeur.

### Portage RISC-V (le vrai travail restant)

edge264 ne cible pas nativement l'ESP32-P4. Étapes de portage :

1. **Toolchain** : edge264 s'appuie sur les *vector extensions* du compilateur.
   - Chemin recommandé : **toolchain Clang d'ESP-IDF** (`idf.py` avec Clang),
     car le backend générique « Other ISAs » d'edge264 exige **Clang ≥ 15**.
   - Avec GCC RISC-V : prévoir un fallback scalaire des intrinsics vectorielles.
2. **Mémoire** : toutes les allocations passent par les callbacks
   `psram_alloc_cb` / `psram_free_cb` du wrapper → **PSRAM** (`MALLOC_CAP_SPIRAM`).
   Vérifier la taille du DPB (frames de référence) selon la résolution.
3. **Threads** : `begin(n_threads=2)` exploite les 2 cœurs du P4.
4. **Mapping des dimensions** : finaliser `get_frame()` (width/height/stride à
   partir de `Edge264Frame.frame_crop_offsets` et du stride interne edge264 —
   à fixer sur la version exacte vendorisée).

---

## API (wrapper `H264HpDecoder`)

```cpp
#include "h264_hp_decoder.h"
using esphome::h264_hp::H264HpDecoder;
using esphome::h264_hp::DecodedFrame;

H264HpDecoder dec;
dec.begin(/*n_threads=*/2);          // alloue le décodeur en PSRAM

// Flux Annex-B (start-codes 00 00 00 01) : SPS, PPS, slices...
dec.decode_annexb(buf, len);         // ou decode_nal(nal_body, nal_len)

DecodedFrame f;
while (dec.get_frame(&f)) {           // I420 : f.y / f.cb / f.cr
  // ... afficher / convertir ...
  dec.release_frame();                // rendre les buffers empruntés
}
```

Sortie = **3 plans Y/Cb/Cr 4:2:0** (I420), exactement le format déjà attendu par
`ip_camera_viewer` (configuré `ESP_H264_RAW_FMT_I420`).

---

## Intégration dans `ip_camera_viewer`

Remplacer le chemin tinyH264 (`init_h264_decoder_` / `decode_h264_to_yuv_`) par
ce décodeur quand le flux n'est pas Baseline. Le `profile_idc` lu dans le SPS
(déjà extrait par `ip_camera_viewer.cpp`) peut servir d'aiguillage :
Baseline → tinyH264 (léger) ; Main/High → h264_hp (edge264).

> ⚠️ Le code actuel de `ip_camera_viewer` logue à tort « openh264 supports
> Baseline/Main/High » : le `libopenh264.a` fourni est **encodeur seul** et le
> décodage passe en réalité par tinyH264 (Baseline). Ce composant corrige ce
> manque côté décodage.

---

## Licences

- **edge264** : BSD (Thibault Raffaillac / TVLabs). Conserver l'en-tête.
- Rappel **brevets** H.264 : la *norme* reste couverte par un pool de brevets
  (Via LA), indépendamment de la licence du code (de moins en moins de brevets
  actifs, beaucoup expirant ~2023-2026). À évaluer selon usage commercial.
