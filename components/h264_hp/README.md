# h264_hp — Décodeur H.264 **High Profile** léger pour ESP32-P4

Décodeur H.264 **Baseline / Main / High** (« comme VLC », en logiciel) pour
ESP32-P4, là où le décodeur Espressif (`esp_h264_dec_sw` → tinyH264/h264bsd) ne
gère que le **Constrained Baseline**.

S'appuie sur **[edge264](https://github.com/tvlabs/edge264)** (décodeur H.264
open-source, **licence BSD**, axé légèreté/vitesse), **vendorisé** ici sous
`edge264/` (552 Ko de source), encapsulé dans une API C++ orientée ESPHome.

---

## ✅ État

- **Source edge264 vendorisée** (`edge264/edge264.h` + `edge264/src/`).
- **Wrapper C++** `H264HpDecoder` prêt (PSRAM, threads, sortie I420).
- **Compilation edge264 désactivée par défaut** → ton build GCC reste vert.
- Reste à faire : **passer en toolchain Clang** puis activer (voir plus bas).

---

## 🚧 LE point bloquant : toolchain Clang obligatoire

Vérifié dans la source edge264 (`src/edge264_internal.h`, lignes 30-42) :

```c
#ifndef SIMD
    #if defined(__SSE2__)        // x86
    #elif defined(__ARM_NEON)    // ARM
    #elif defined(__clang__)     // backend générique (vector extensions Clang)
    #else
        #error "No supported vector intrinsics found (SSE, NEON, WASM, clang)"
    #endif
#endif
```

- **ESP32-P4 = RISC-V** : ni SSE, ni NEON, ni WASM.
- En **GCC** (toolchain ESPHome/PlatformIO par défaut) → `#error`, **ne compile pas**.
- Le backend générique repose sur `__builtin_shufflevector` / `__builtin_convertvector`,
  **builtins propres à Clang** (le code note lui-même : *« no way to make clang use
  __builtin_shufflevector, and GCC performs worse »*). Les réécrire pour GCC =
  réécrire tout le cœur vectoriel → non réaliste.

➡️ **edge264 sur P4 n'est exploitable qu'avec la toolchain Clang d'ESP-IDF.**

### Activation (après passage à Clang)

```sh
# 1) Build ESP-IDF avec Clang (toolchain expérimentale espressif/llvm)
idf.py --preview set-target esp32p4
# configurer la toolchain Clang (esp-clang) dans l'environnement IDF

# 2) Activer la compilation edge264 dans ce composant
touch components/h264_hp/edge264/ENABLE_EDGE264
```

Le marqueur `ENABLE_EDGE264` déclenche, côté CMake :
- compilation du **seul** `edge264/src/edge264.c` (unity build : il #include les autres),
- `-DUSE_H264_HP_EDGE264` → le wrapper bascule du no-op au vrai décodeur.

Tant que le marqueur est absent : wrapper **no-op**, build inchangé.

---

## ⚠️ Performance (à mesurer sur hardware)

Même sous Clang, le P4 n'a **pas de SIMD** : edge264 tourne en **scalaire**.
Estimation **non garantie** : exploitable en **basse/moyenne résolution**
(VGA ~10-20 fps), **pas en 1080p30**. CABAC (Main/High) est le facteur limitant.
Limites edge264 : **8 bits, 4:2:0** uniquement ; pré-production (gel d'API 2027).

---

## 🅱️ Alternative si tu restes en GCC : openh264 (décodeur depuis la source)

Si passer à Clang n'est pas envisageable, le chemin High-profile compatible
**GCC** est **openh264** compilé **depuis la source** (C++ portable, fallbacks
scalaires, BSD) :

- Plus **lourd et plus lent** qu'edge264, mais **compile en GCC** et **sans
  risque d'ABI** (contrairement au `libopenh264.a` encodeur-seul fourni, qui
  ne décode pas).
- Il faut vendoriser l'arbre `codec/decoder/` d'openh264 (non inclus ici) et le
  compiler ; l'API décodeur (`WelsCreateDecoder` / `ISVCDecoder`) est déjà
  déclarée dans `../esp_h264/sw/libs/openh264_inc/codec_api.h`.

| Critère | edge264 | openh264 (décodeur source) |
| ------- | ------- | -------------------------- |
| Légèreté | ✅ 552 Ko | ❌ lourd |
| Vitesse | ✅ (relative) | ❌ plus lent |
| Toolchain P4 | **Clang only** | ✅ **GCC ok** |
| Profils | Baseline/Main/High | Baseline/Main/High |
| Licence | BSD | BSD |

---

## API (wrapper `H264HpDecoder`)

```cpp
#include "h264_hp_decoder.h"
using esphome::h264_hp::H264HpDecoder;
using esphome::h264_hp::DecodedFrame;

H264HpDecoder dec;
dec.begin(/*n_threads=*/2);          // alloue le décodeur en PSRAM
dec.decode_annexb(buf, len);         // flux Annex-B (start-codes), ou decode_nal()

DecodedFrame f;
while (dec.get_frame(&f)) {           // I420 : f.y / f.cb / f.cr
  // ... afficher / convertir ...
  dec.release_frame();
}
```

Sortie = **3 plans Y/Cb/Cr 4:2:0** (I420), déjà attendu par `ip_camera_viewer`.

---

## Intégration prévue dans `ip_camera_viewer`

Aiguillage selon le `profile_idc` lu dans le SPS (déjà extrait par
`ip_camera_viewer.cpp`) : Baseline → tinyH264 (léger) ; Main/High → h264_hp.
À brancher une fois la toolchain choisie.

---

## Licences

- **edge264** : BSD (Thibault Raffaillac / TVLabs) — voir `edge264/LICENSE_BSD.txt`.
- Rappel **brevets** : la *norme* H.264 reste couverte par un pool de brevets
  (Via LA), indépendamment de la licence du code (beaucoup expirant ~2023-2026).
