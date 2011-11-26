#!/bin/bash
#
# this script handles preparing either the source package or the linux
# installable package

set -eu

VER=$(grep 'version =' misc.py | cut -d'"' -f2)
DIR="linux-dist/blyte-$VER"

rm -rf linux-dist
mkdir -p $DIR

if test $1 = "src"; then
 FNAME="blyte-src-$VER.tar"
 svn export --force . $DIR
else
 FNAME="blyte-$VER.tar"
 cp -r *.py blyte.desktop names.txt.gz dict_en.dat.gz sample.trelby manual.html fileformat.txt LICENSE INSTALL resources/ $DIR
 rm $DIR/setup.py
 cp Makefile.install $DIR/Makefile
fi

cd linux-dist
tar cvf $FNAME "blyte-$VER"
gzip -9 $FNAME

mv "${FNAME}.gz" ..

cd ..
rm -rf linux-dist
