#!/bin/sh

set -eu

# list of mounted distros
DISTS="/mnt/ubuntu-5.10 /mnt/suse-10.0 /mnt/fedora-5"

for d in $DISTS; do
  echo "Doing $d"

  if ! test -d $d/tmp; then
    mount $d;
  fi

  path="$d/home/osku/blyte-dist-tmp"
  rm -rf $path
  mkdir -p $path
  cp *.py *.sh linux.c icon16.png icon32.png logo.jpg names.dat dict_en.dat.gz sample.blyte manual.pdf fileformat.txt license.txt INSTALL Makefile* $path
done
