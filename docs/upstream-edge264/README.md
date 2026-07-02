# Upstream contribution to tvlabs/edge264

Patch series extracted from this repository's vendored edge264 tree
(components/h264_hp/edge264/src/), rebased onto tvlabs/edge264 master
and verified to apply cleanly with `git am`.

## How to submit

```sh
git clone https://github.com/youkorr/edge264   # your fork of tvlabs/edge264
cd edge264
git checkout -b riscv-esp32p4 origin/master
git am /path/to/docs/upstream-edge264/00*.patch
git push -u origin riscv-esp32p4
```

Then open a pull request against tvlabs/edge264 `master` using
`PR_DESCRIPTION.md` as the PR body (it references issue #28).
