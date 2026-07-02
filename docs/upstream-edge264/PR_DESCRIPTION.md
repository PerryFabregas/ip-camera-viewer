# RISC-V support: misaligned-access fixes + scalar fast paths (fixes #28)

## Summary

This series makes edge264 work — and perform — on SIMD-less RISC-V
targets (developed and validated on the ESP32-P4, RV32IMAFC @ 400 MHz,
decoding live RTSP High Profile streams from surveillance cameras).

It contains three commits:

1. **riscv: fix misaligned-trap crashes and harden the slice loop** —
   fixes the crash reported in #28. On RISC-V a misaligned wide access
   traps (x86/ARM tolerate it, and qemu-user emulates it, which is why
   it doesn't reproduce there). The aligned wide accesses of the High
   Profile 8x8 kernels are routed through fixed-size `__builtin_memcpy`
   wrappers under `#ifdef __riscv` — identical values, trap-free
   lowering, zero impact on other ISAs. Also adds a hard bound on the
   slice macroblock loop so a clobbered `pic_width_in_mbs` can no longer
   hang the decoder (watchdog reset on embedded targets).

2. **riscv: scalar deblocking pipeline** — with the vector code
   scalarized by the compiler, the deblocking transposes dominate whole-
   frame cost (62-75% of decode time in a gprof profile). Adds an
   in-place scalar pixel pipeline (exact 8.7.2.3/8.7.2.4 formulas, used
   on `__riscv` only) plus two cheap bS=0 skip fast paths.

3. **riscv: scalar unweighted motion compensation** — same treatment
   for the second hotspot: scalar 6-tap/bilinear kernels for the 15
   fractional positions, full-pel unweighted prediction as plain row
   copies. Weighted/bipred keep the vector path.

## Correctness

Every commit is **bit-exact** against the SSE build, verified with a
decode-and-hash harness (x86 SIMD build as reference, riscv64 build run
under qemu-user) on 12 streams covering: IDR/P, CABAC and CAVLC,
B-frames, weighted prediction (weightp=2), QP 15 and 40, 8x8 transform
on/off, multi-slice frames, and non-zero deblock alpha/beta offsets.

## Performance (640x360 High/CABAC, qemu-riscv64, same machine)

| workload                | before | after | speedup |
|-------------------------|--------|-------|---------|
| IDR frame               | 102 ms | 20 ms | 5.0x    |
| P frame, static scene   | 11.7 ms| 3.1 ms| 3.8x    |
| P frame, moving scene   | 29.7 ms| 7.2 ms| 4.1x    |

On the real target (ESP32-P4 @ 400 MHz, PSRAM frame buffers, live Tapo
camera): first IDR went from ~13 s to ~180 ms, P-frames from ~200 ms to
25-40 ms — real-time decoding of a 15 fps High Profile stream on a
microcontroller.

Non-RISC-V targets are unaffected: the scalar kernels and the memcpy
load wrappers are compiled only under `#ifdef __riscv`; the two bS=0
deblock skip paths are active everywhere but are pure wins.
