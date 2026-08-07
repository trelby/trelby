#!/bin/bash

# Compile the PO files and move compiled MO files to `locales` directory

for i in $(find po -type f -name '*.po'); do

    j=$(echo "$i" | sed "s|\.\/||g" | sed "s|\.po||g" | cut -f 2 -d "/")

    echo ""
    echo "Compiling $j at trelby/locales/$j/LC_MESSAGES/trelby.mo"

    mkdir -p trelby/locales/"$j"/LC_MESSAGES
    msgfmt --verbose --statistics --output-file=trelby/locales/"$j"/LC_MESSAGES/trelby.mo "$i"

done

rm -f po/*.mo

echo ""
echo "End."
