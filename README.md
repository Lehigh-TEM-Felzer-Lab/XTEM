# XTEM

XTEM is version 4.5 of the Terrestrial Ecosystem Model (TEM): carbon, nitrogen and water pools and fluxes of vegetation and soil for land-cover cohorts in each grid cell. The science follows [GDSTEM](https://github.com/Lehigh-TEM-Felzer-Lab/GDSTEM) with the fire module of GDSTEM-FIRE. Inputs and outputs are NetCDF, configuration and parameters are YAML, and cells are shared between MPI ranks. [TEM_UW_APP](https://github.com/Lehigh-TEM-Felzer-Lab/TEM_UW_APP) builds inputs and launches runs.

## Build

Requires g++ 9 or later (C++17), make, libyaml and libnetcdf. `make mpi` also needs an MPI C++ compiler and an MPI-enabled netCDF.

```bash
sudo apt-get install g++ make pkg-config libyaml-dev libnetcdf-dev   # MPI: libnetcdf-mpi-dev openmpi-bin libopenmpi-dev
make -j4        # build/xtem
make mpi -j4    # build_mpi/xtem
make test       # unit tests
```

Compile-time options go to `make`, for example `make mpi OPEN_N=0 FIRE=0`: `OPEN_N` (1 open, 0 closed nitrogen cycle), `FIRE` (wildfire) and `STORM` (storm damage), all default 1.

## Run

```bash
cd examples/test && mkdir -p OUTPUT
../../build/xtem                  # or: mpirun -np 2 ../../build_mpi/xtem
```

`xtem` reads `tem_config.yaml` from the working directory, or the file given as its first argument. Paths in it are relative to that directory, and `OUTPUT/` must exist. The result is `OUTPUT/tem.nc`; progress and errors go to `tem_<id>.out` and `tem_<id>.log`. Start a new case from `templates/tem_config.yaml`, which documents every key.

## Where things are

| Path | Content |
|---|---|
| `src/physics/` | model science |
| `src/io/` | YAML, NetCDF, restart, logging, MPI |
| `src/driver/` | main program |
| `params/` | YAML parameter files |
| `examples/test/` | runnable example: 50 cells, 4 years |
| `tests/` | unit tests and a reference output for local checks |

`physics` includes nothing from `io` or `driver`; CI enforces this. GDSTEM and TEM have the same split.

## Documentation

- [config_desc.md](config_desc.md): configuration keys
- [technical_desc.md](technical_desc.md): input and output layouts, time step, MPI, restart, logs, source files
- [flowchart.md](flowchart.md): call hierarchy
- [CONTRIBUTING.md](CONTRIBUTING.md): checks, and how GDSTEM science is carried over


