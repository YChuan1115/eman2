#!/bin/bash

export CFLAGS="-I${PREFIX}/include"

./configure --prefix=${SP_DIR}

sed -i.bak 's~\(^LDFLAGS.*$\)~\1 -L/'"${PREFIX}"'/lib -lfftw3_mpi -lfftw3~' src/Makefile

export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

make
make install

rm -rf ${SP_DIR}/mpi_examples
