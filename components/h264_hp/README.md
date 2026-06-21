# h264_hp — Décodeur H.264 **High Profile** pour ESP32-P4 (edge264)

Décodeur H.264 **Baseline / Main / High** pour ESP32-P4, là où le décodeur
Espressif (`esp_h264_dec_sw` → tinyH264) ne gère que le **Constrained Baseline**.

Basé sur **[edge264](https://github.com/tvlabs/edge264)** (BSD), **vendorisé** sous
`edge264/` et encapsulé dans une API C++ (`H264HpDecoder`).

---

## 🎯 Stratégie : compiler edge264 en **Clang**, le **linker** en GCC

edge264 n'a **pas** de backend GCC : sa branche générique utilise des builtins
**Clang-only** (`__builtin_shufflevector`, `__builtin_elementwise_*`,
`__builtin_reduce_*`). Réécrire ça pour GCC = réimplémenter ~30 primitives
vectorielles à l'aveugle → risque de **bug d'image silencieux**.

➡️ On **évite** ça : on compile edge264 **une seule fois avec esp-clang** (backend
`SIMD=CLANG` natif et **testé**) en une lib statique RISC-V, puis on la **linke**
dans le build ESPHome/GCC. **L'ABI RISC-V Clang/GCC est compatible** — c'est
exactement le mécanisme déjà utilisé par `libtinyh264.a` / `libopenh264.a`.

```
edge264 (src) ──[esp-clang, une fois]──► libedge264.a ──┐
                                                        ├─► LINK ─► firmware (build GCC)
wrapper h264_hp + ip_camera_viewer ─────[GCC]───────────┘
```

**Bénéfices :** edge264 conservé · code Clang natif testé (pas de bug silencieux) ·
aucune réécriture · ton ami n'a qu'à **compiler le `.a` une fois**.

---

## 🔧 Mode d'emploi (à faire une fois, sur la machine de build)

```sh
# 1) ESP-IDF + toolchain Clang
idf_tools.py install esp-clang
. $IDF_PATH/export.sh

# 2) Construire la lib (ajuste -march/-mabi si ton build P4 diffère)
cd components/h264_hp/edge264
./build_libedge264_esp32p4.sh
# -> produit edge264/lib/esp32p4/libedge264.a
```

Dès que `edge264/lib/esp32p4/libedge264.a` existe :
- `CMakeLists.txt` le **linke** et définit `-DUSE_H264_HP_EDGE264`,
- le wrapper bascule du no-op au vrai décodeur.

Sans le `.a` : wrapper **no-op**, build ESPHome inchangé (jamais cassé).

> Le `.a` ne doit PAS forcément être commité : ton ami peut le régénérer. Si tu
> veux le distribuer aux utilisateurs (pour qu'ils n'aient pas besoin de Clang),
> commite `edge264/lib/esp32p4/libedge264.a` dans le dépôt.

---

## ⚠️ Performance (à mesurer sur carte)

Le P4 n'a **pas de SIMD** : edge264 tourne en **scalaire** (backend générique).
Estimation **non garantie** : basse/moyenne résolution. CABAC (Main/High) est le
facteur limitant. edge264 : **8 bits, 4:2:0** ; pré-production (gel d'API 2027).
Threads : `begin(n_threads=2)` utilise les 2 cœurs (pthread fourni par ESP-IDF) ;
`n_threads=0` = mono-thread sans pthread.

---

## API (wrapper `H264HpDecoder`)

```cpp
#include "h264_hp_decoder.h"
using esphome::h264_hp::H264HpDecoder;
using esphome::h264_hp::DecodedFrame;

H264HpDecoder dec;
dec.begin(/*n_threads=*/2);          // alloue le décodeur en PSRAM
dec.decode_annexb(buf, len);         // flux Annex-B, ou decode_nal()

DecodedFrame f;
while (dec.get_frame(&f)) {           // I420 : f.y / f.cb / f.cr
  // ... afficher / convertir ...
  dec.release_frame();
}
```

Sortie = **3 plans Y/Cb/Cr 4:2:0** (I420), déjà attendu par `ip_camera_viewer`.

---

## Étapes restantes (suivi)

- [x] Source edge264 vendorisée
- [x] Wrapper C++ (PSRAM, threads, I420)
- [x] Stratégie Clang-lib + linkage GCC + script de build
- [ ] **Générer `libedge264.a`** avec esp-clang (machine de build de ton ami)
- [ ] Finaliser le mapping `get_frame()` (width/height/stride depuis `Edge264Frame`)
- [ ] Brancher l'aiguillage dans `ip_camera_viewer` (Baseline→tinyH264 / Main-High→h264_hp)
- [ ] **Mesurer la perf** sur ESP32-P4 réel

---

## Licences

- **edge264** : BSD — voir `edge264/LICENSE_BSD.txt`.
- Brevets H.264 : la *norme* reste couverte par un pool (Via LA), indépendamment
  de la licence du code.
