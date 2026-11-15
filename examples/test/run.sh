#!/bin/sh
# Run the test case: 50 grid cells, 4 transient years, 2 MPI ranks (any number works; omit mpirun for serial).
# usage: sh run.sh [/path/to/MPI-built xtem]
mkdir -p OUTPUT logs
mpirun -np 2 "${1:-../../build_mpi/xtem}" tem_config.yaml
