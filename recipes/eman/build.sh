#!/bin/bash

build_dir="${SRC_DIR}/../build_eman"

rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

cmake $SRC_DIR -DENABLE_RT=OFF -DENABLE_OPTIMIZE_X86_64=ON

make -j${CPU_COUNT}
make install

ln -s $PREFIX/bin/e2version.py $SP_DIR/e2version.py
ln -s $PREFIX/bin/sxgui.py     $PREFIX/bin/sphire
ln -s $PREFIX/bin/sx.py        $PREFIX/bin/sparx
