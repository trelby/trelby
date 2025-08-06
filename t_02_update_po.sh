#!/bin/bash

for i in $(find po -type f -name '*.po'); do
  msgmerge -vU "$i" po/trelby.pot
done

