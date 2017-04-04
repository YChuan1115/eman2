#!/usr/bin/env bash

set -xe

source activate
echo $EMAN_CONDA
export EMAN_PYDUSA_FLAGS="${@}"

RECIPE_DIR="${CONDA_PREFIX}/recipes"
conda build ${RECIPE_DIR}/fftw-mpi
conda build ${RECIPE_DIR}/pydusa
conda install pydusa --use-local --yes

# Cleanup
conda build purge
