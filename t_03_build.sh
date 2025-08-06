#!/bin/bash

for i in $(find po -type f -name '*.po'); do
  j=$(echo "$i" | sed "s|\.\/||g" | sed "s|\.po||g" | cut -f 2 -d "/")
  mkdir -p trelby/locales/"$j"/LC_MESSAGES
  msgfmt -otrelby/locales/"$j"/LC_MESSAGES/trelby.mo "$i"
done
rm -f po/*.mo
