#!/usr/bin/env python3
"""Two end-to-end checks on 6 grid cells cut from examples/test/INPUT (12 monthly steps).

1. run: serial and 2 ranks give the same OUTPUT/tem.nc; there are two run files, tem_<id>.out (progress of every rank)
   and tem_<id>.log (all other messages), no per-rank log files and nothing on stdout.
2. missing data: an input without data in a land-cover cell stops every rank within seconds, with one error that names the input,
   the number of cells and the first position, in tem_<id>.log.

Run from the XTEM directory after make and make mpi: python3 tests/run_tests.py
"""
import os, re, shutil, subprocess, sys, tempfile
import numpy as np
import netCDF4

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ex = os.path.join(root, "examples", "test")
tmp = tempfile.mkdtemp(prefix="xtem_test_")
serial = os.path.join(root, "build", "xtem")
mpi = os.path.join(root, "build_mpi", "xtem")
cfg0 = open(os.path.join(ex, "tem_config.yaml")).read().replace("../../params", os.path.join(root, "params"))
LAT, LON = slice(0, 3), slice(1, 3)  # 3 x 2 cells, all with land cover in the example


def cut(name, dest):
    src = netCDF4.Dataset(os.path.join(ex, "INPUT", name))
    dst = netCDF4.Dataset(dest, "w")
    for d, dim in src.dimensions.items():
        dst.createDimension(d, 3 if d == "lat" else 2 if d == "lon" else len(dim))
    for k, v in src.variables.items():
        o = dst.createVariable(k, v.dtype, v.dimensions, fill_value=getattr(v, "_FillValue", None))
        o.setncatts({a: v.getncattr(a) for a in v.ncattrs() if a != "_FillValue"})
        o[:] = v[tuple(LAT if d == "lat" else LON if d == "lon" else slice(None) for d in v.dimensions)]
    dst.close()


def runfile(d, ext):
    """The one tem_<id>.<ext> of a case directory."""
    f = [x for x in os.listdir(d) if re.fullmatch(r"tem_\d{8}_\d{6}\." + ext, x)]
    if len(f) != 1:
        fail("expected one tem_<id>.%s in %s, found %s" % (ext, d, f))
    return open(os.path.join(d, f[0])).read()


def case(name, edit=None):
    d = os.path.join(tmp, name)
    os.makedirs(os.path.join(d, "INPUT")); os.makedirs(os.path.join(d, "OUTPUT"))
    for f in os.listdir(os.path.join(ex, "INPUT")):
        cut(f, os.path.join(d, "INPUT", f))
    cfg = cfg0
    for k, v in {"mxnumgrid": 6, "run_length": 12, "run_length_units": "months", "endyr": 2015}.items():
        cfg = re.sub(r"^%s:.*$" % k, "%s: %s" % (k, v), cfg, flags=re.M)
    open(os.path.join(d, "tem_config.yaml"), "w").write(cfg)
    if edit:
        edit(os.path.join(d, "INPUT"))
    return d


def run(d, cmd, timeout=300):
    return subprocess.run(cmd + ["tem_config.yaml"], cwd=d, capture_output=True, text=True, timeout=timeout)


def fail(msg, r=None):
    sys.exit("FAILED: " + msg + ("\n" + (r.stdout + r.stderr)[-1500:] if r else ""))


# ---- 1. run -----------------------------------------------------------------------------------------
d1 = case("serial"); r = run(d1, [serial])
if r.returncode: fail("serial run", r)
d2 = case("mpi"); r2 = run(d2, ["mpirun", "-np", "2", "--oversubscribe", mpi])
if r2.returncode: fail("mpi run", r2)
a, b = netCDF4.Dataset(os.path.join(d1, "OUTPUT", "tem.nc")), netCDF4.Dataset(os.path.join(d2, "OUTPUT", "tem.nc"))
gpp = np.ma.filled(a["gpp"][:].astype(float), np.nan)
if gpp.shape[0] != 12 or int(np.isfinite(gpp[0, 0]).sum()) != 6:
    fail("serial output is not 12 steps on 6 cells, gpp shape %s" % (gpp.shape,))
for k in a.variables:
    x, y = np.ma.filled(a[k][:].astype(float), -1e30), np.ma.filled(b[k][:].astype(float), -1e30)
    if x.shape != y.shape or not np.array_equal(x, y):
        fail("variable %s differs between serial and 2 ranks" % k)
out, text = runfile(d2, "out"), runfile(d2, "log")
if not re.search(r"\| rank 0001 \| cell ", out) or "finished 6 cells" not in out or "all ranks finished" not in out:
    fail("the .out file lacks a cell line from rank 1, the finished cells or the final line")
if "CELL" in text:
    fail("progress lines are in the .log file")
if [f for f in os.listdir(d2) if f.startswith("tem45.") or f in ("tem.log", "tem.out")]:
    fail("per-rank or unnumbered log files were written")
if r.stdout.strip() or r2.stdout.strip():
    fail("stdout is not empty:\n" + r2.stdout[-500:])
print("ok: serial equals 2 ranks, two run files, empty stdout")


# ---- 2. missing data ----------------------------------------------------------------------------------
def hole(inp):
    p = os.path.join(inp, "static.nc")
    ds = netCDF4.Dataset(p, "r+")
    for k in ("sand", "silt", "clay"):
        ds[k][1, 1] = np.ma.masked
    ds.close()

d3 = case("missing", hole)
r3 = run(d3, ["mpirun", "-np", "2", "--oversubscribe", mpi], timeout=60)
err = runfile(d3, "log")
if r3.returncode == 0 or err.count("| ERROR") != 3 or "input error" not in err or err.count("input error") != 1 or "TEXTURE" not in err or "1 of 6 cells" not in err or "first at lon" not in err:
    fail("the missing-data error is not one clear message", r3)
if [f for f in os.listdir(d3) if f.startswith("tem45.")]:
    fail("per-rank log files were written")
print("ok: missing data stops all ranks with one message")


shutil.rmtree(tmp)
print("all tests passed")
