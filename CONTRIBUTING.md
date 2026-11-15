# Contributing

## Source layout

```
src/physics/   the science and the records it uses (vegetation, soil, microbes, evapotranspiration, fire, land use,
               cell and cohort classes, constants, time step)
src/io/        files and processes: YAML, NetCDF, restart state, input checks, log, diagnostics transport, MPI layer
src/driver/    xtem_gds.cpp, the main program, which wires physics and io together
```

- `io` and `driver` may include from `physics`. `physics` includes nothing from `io` or `driver`. `io` includes nothing from `driver`.
- `python3 .github/scripts/check_layering.py` checks this. The includes that break the rule today are the `exceptions` of `.github/layering.yaml`
  (YAML readers in the `getecd` methods, NetCDF reads in the record classes, the restart state in `Telm45`). A new violation
  fails, and so does an entry that is gone: delete it with `python3 .github/scripts/check_layering.py --update`. The list may only shrink.
- All three directories are on the include path, so `#include "tem_yaml.h"` needs no directory. File names must stay unique across them.
- A new file goes where its role puts it: if it reads a file, calls NetCDF, YAML or MPI, or writes the log, it is `io`; if it
  computes the model, it is `physics`. Do not reformat or rename files in `physics` for style: the science is carried over from GDSTEM by diff,
  and every changed line becomes a possible conflict.

## Checks

`make && make test` builds and runs the unit tests. CI builds `xtem` only after a merge to `main` and once every three months (it runs no tests and no model); pull requests get the source and layering checks. To check that a change leaves results unchanged, run `examples/test` locally and compare with `tests/golden/tem.nc`:

```bash
cd examples/test && mkdir -p OUTPUT && ../../build/xtem
python3 ../../tests/compare_nc.py OUTPUT/tem.nc ../../tests/golden/tem.nc
```

The golden file was written with g++ 13 on Ubuntu 24.04 at `-O2`; other compilers, libm versions and unoptimised builds differ in the last digits, so the comparison tolerance is rtol 1e-6. Replace it only
in a commit whose message says why results change, for example a science change from GDSTEM.

## Science from GDSTEM

[GDSTEM](https://github.com/Lehigh-TEM-Felzer-Lab/GDSTEM) is the reference for the model science; this repository replaces its XML
and text input and output. GDSTEM is never changed from here. Its changes are carried over by diff, not by a Git merge:

1. `.github/gdstem_sync.yaml` holds `last_synced`, the GDSTEM commit whose changes are already in `src/`.
2. `.github/scripts/sync_gdstem.py` takes the diff of every GDSTEM file changed since then and applies it with `git apply --3way` to the
   file of the same name in `src/physics`, `src/io` or `src/driver`. Lines that only XTEM has (YAML, NetCDF, log, MPI) are not in
   the diff, so they stay. Then it sets `last_synced` to the new commit.
3. `.github/workflows/sync-gdstem.yml` does this on the 1st of every month, or on demand (Actions, sync-gdstem, Run workflow), and
   opens a pull request labelled `science-sync` whose text lists what happened. It is a draft when something did not apply.

Locally: `git remote add gdstem <url> && git fetch gdstem && python3 .github/scripts/sync_gdstem.py` (needs `pip install pyyaml`).

What the pull request lists, and what to do:

| Section | Meaning | Action |
|---|---|---|
| Applied | the diff applied cleanly | read it: Git does not catch `col`, `row` (now `lon`, `lat`), `MAXCYCLE`-style sizes or a hard-coded 12 steps per year; the build catches most of them |
| Not applied: conflict | the diff overlaps lines XTEM changed | `git apply --3way -p3 --directory=src/physics sync/rejected/<sha>/<file>.patch`, fix the markers, delete the patch file |
| Not applied: XTEM replaced these files | the driver and the record readers (`manual:` in `gdstem_sync.yaml`) | port a science change by hand into `src/driver/xtem_gds.cpp` or the record class |
| Parameter files | a file in GDSTEM `params/` changed | make the same change in `params/*.yaml` and note it in `params/provenance.md` |
| New, deleted, renamed in GDSTEM | nothing is done automatically | place, delete or rename the file in `src/` |

`ci.yml` fails while `sync/rejected/` has files. If the local golden comparison changes, the science changed: say so in the pull request and update
`tests/golden/tem.nc` deliberately. A squash merge of the pull request is fine: nothing depends on the Git history.
