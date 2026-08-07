#!/bin/bash

# Update the PO files in the `po` directory with the POT template.

for i in $(find po -type f -name '*.po'); do
    echo ""
    echo "Updating $i"
    msgmerge --verbose --update --previous --sort-by-file "$i" po/trelby.pot
done

echo ""
echo "End."
