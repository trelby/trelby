#!/bin/bash

set -eu

# return true if the given file exists and its contents match the second
# parameter, which is a regexp
file_contains() {
  if test -f $1 && grep -Eq "$2" $1; then
    return 0
  else
    return 1
  fi
}

# set $DIST_NAME to the linux distribution name/version the script is run
# on
set_dist_name() {
  if file_contains "/etc/debian_version" "^3.1$"; then
    DIST_NAME="debian-3.1"
  elif file_contains "/etc/issue" "^Ubuntu 5\.10 "; then
    DIST_NAME="ubuntu-5.10"
  elif file_contains "/etc/fedora-release" "^Fedora Core release 5 "; then
    DIST_NAME="fedora-5"
  elif file_contains "/etc/issue" " SUSE LINUX 10\.0 "; then
    DIST_NAME="suse-10.0"
  else
    echo "Error: Unknown distribution!"
    exit 1
  fi
}

set_dist_name

VER=$(grep 'misc.version =' blyte.py | cut -b24- | perl -pe 's/"//g;')
DIR="linux-dist/blyte-$VER"

./compile_all.sh

rm -rf linux-dist
mkdir -p $DIR

cp blyte data.dat icon16.png icon32.png logo.jpg names.dat dict_en.dat.gz sample.blyte manual.pdf fileformat.txt license.txt INSTALL $DIR
cp Makefile.install $DIR/Makefile
cd linux-dist
tar cvf "blyte-$VER.tar" "blyte-$VER"
gzip -9 "blyte-$VER.tar"

fname="blyte-$VER-$DIST_NAME.tar.gz"
mv "blyte-$VER.tar.gz" "../$fname"

cd ..
rm -rf linux-dist

if ! test $DIST_NAME = "debian-3.1"; then
  cp $fname /mnt/debian-3.1/home/osku
fi

echo "Status: '$fname' created"
