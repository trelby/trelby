#!/bin/bash
#
# this script handles preparing either the source package or the linux
# installable package

set -eu

VER=$(grep 'misc.version =' blyte.py | cut -b24- | perl -pe 's/"//g;')
DIR="linux-dist/blyte-$VER"

rm -rf linux-dist
mkdir -p $DIR

if test $1 = "src"; then
 FNAME="blyte-src-$VER.tar"
 svn export --force . $DIR
else
 FNAME="blyte-$VER.tar"
 cp *.py icon16.png icon32.png logo.jpg names.dat dict_en.dat.gz sample.blyte manual.pdf fileformat.txt LICENSE INSTALL $DIR
 rm $DIR/setup.py
 cp Makefile.install $DIR/Makefile
fi

cd linux-dist
tar cvf $FNAME "blyte-$VER"
gzip -9 $FNAME

mv "${FNAME}.gz" ..

cd ..
rm -rf linux-dist
