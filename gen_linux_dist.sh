#!/bin/bash
#
# this script handles preparing the linux installable package

set -eu

VER=$(grep 'version =' src/misc.py | cut -d'"' -f2)
BASE_DIR="linux-dist/trelby-$VER/"
DIR="$BASE_DIR/trelby"

rm -rf linux-dist
mkdir -p $DIR

FNAME="trelby-$VER.tar"
rm -f src/*.pyc
cp -r src/ trelby.desktop names.txt.gz dict_en.dat.gz sample.trelby manual.html fileformat.txt LICENSE README resources/ $DIR
cp README.linux $BASE_DIR/README

cd linux-dist
tar cvf $FNAME "trelby-$VER"
gzip -9 $FNAME

mv "${FNAME}.gz" ..

cd ..
rm -rf linux-dist
