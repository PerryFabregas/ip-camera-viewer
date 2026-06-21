#!/usr/bin/env bash
#
# build_libedge264_esp32p4.sh — Compile edge264 EN CLANG vers une lib statique
# RISC-V (libedge264.a) pour ESP32-P4, à LINKER ensuite dans le build ESPHome/GCC.
#
# Pourquoi : edge264 n'a pas de backend GCC (il utilise des builtins Clang-only :
# __builtin_shufflevector / __builtin_elementwise_* / __builtin_reduce_*).
# Son backend générique "SIMD=CLANG" est en revanche complet et TESTÉ.
# On compile donc edge264 avec esp-clang (toolchain RISC-V d'ESP-IDF), une seule
# fois, et on linke le .a dans le build GCC (l'ABI RISC-V est compatible) — exactement
# comme le fait déjà libtinyh264.a / libopenh264.a.
#
# PRÉREQUIS :
#   1) ESP-IDF installé, avec la toolchain Clang :
#        idf_tools.py install esp-clang
#        . $IDF_PATH/export.sh
#   2) Lancer ce script depuis ce dossier (components/h264_hp/edge264/).
#
# RÉSULTAT : lib/esp32p4/libedge264.a (+ edge264.h déjà présent).
#
# ⚠️ L'-march/-mabi DOIVENT correspondre à ton build IDF du P4. Les valeurs par
#    défaut ci-dessous ciblent un ESP32-P4 standard ; ajuste si ton build diffère
#    (voir `idf.py ... -v` qui montre les flags réels du compilateur).

set -euo pipefail
cd "$(dirname "$0")"

# --- Toolchain (surchageable par variables d'env) ---------------------------
CLANG="${CLANG:-clang}"                 # esp-clang (dans le PATH après export.sh)
AR="${LLVM_AR:-llvm-ar}"
TARGET="${TARGET:-riscv32-esp-elf}"
MARCH="${MARCH:-rv32imafc_zicsr_zifencei}"
MABI="${MABI:-ilp32f}"

# Sysroot : headers newlib/pthread d'ESP-IDF. Auto-détection depuis la toolchain
# GCC si SYSROOT n'est pas fourni.
if [ -z "${SYSROOT:-}" ]; then
  GCC_RV="$(command -v riscv32-esp-elf-gcc || true)"
  if [ -n "$GCC_RV" ]; then
    SYSROOT="$("$GCC_RV" -print-sysroot)"
  fi
fi
SYSROOT_FLAG=""
[ -n "${SYSROOT:-}" ] && SYSROOT_FLAG="--sysroot=$SYSROOT"

OUT_DIR="lib/esp32p4"
mkdir -p "$OUT_DIR"

echo "[edge264] clang   = $($CLANG --version | head -1)"
echo "[edge264] target  = $TARGET  march=$MARCH  mabi=$MABI"
echo "[edge264] sysroot = ${SYSROOT:-<aucun: ajoute -isystem si la compil échoue>}"

# edge264 est un unity build : on ne compile QUE src/edge264.c (il #include le reste).
"$CLANG" \
  --target="$TARGET" -march="$MARCH" -mabi="$MABI" \
  $SYSROOT_FLAG \
  -std=gnu11 -O3 -ffunction-sections -fdata-sections \
  -fno-exceptions -fno-rtti -DNDEBUG \
  -I. -Isrc \
  -c src/edge264.c -o "$OUT_DIR/edge264.o"

rm -f "$OUT_DIR/libedge264.a"
"$AR" rcs "$OUT_DIR/libedge264.a" "$OUT_DIR/edge264.o"
rm -f "$OUT_DIR/edge264.o"

echo "[edge264] OK -> $OUT_DIR/libedge264.a"
echo "[edge264] Vérifie les symboles : $AR t $OUT_DIR/libedge264.a ; nm ... | grep edge264_alloc"
