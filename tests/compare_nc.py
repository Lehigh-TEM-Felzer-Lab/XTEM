#!/usr/bin/env python3
"""Compares every variable of two NetCDF files. usage: compare_nc.py A.nc B.nc [rtol] [atol]  (default 1e-6, 1e-12)"""
import sys

import netCDF4
import numpy as np

a, b = (netCDF4.Dataset(p) for p in sys.argv[1:3])
rtol = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-6
atol = float(sys.argv[4]) if len(sys.argv) > 4 else 1e-12
bad = []
for k in sorted(a.variables.keys() | b.variables.keys()):
    if k not in a.variables or k not in b.variables:
        bad.append(k)
        continue
    x, y = (np.ma.filled(v[k][:].astype(float), np.nan) for v in (a, b))
    err = np.nanmax(np.abs(x - y) / (atol + rtol * np.abs(y)), initial=0)
    if not np.allclose(x, y, rtol=rtol, atol=atol, equal_nan=True):
        bad.append(k)
        print(f"{k}: max |a-b| / (atol + rtol |b|) = {err:.3g}")
print(f"{len(a.variables)} variables, rtol {rtol}, atol {atol}, differ: {bad}")
sys.exit(bool(bad))
