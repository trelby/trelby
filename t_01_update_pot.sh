#!/bin/bash

# Update (create) the POT template file for translating Trelby

echo "Creating po/trelby.pot..."

xgettext --language=Python --output=po/trelby.pot --package-name=trelby --package-version=2.4.16 --copyright-holder="Gwyn Ciesla <gwync@protonmail.com>" --keyword=_ --from-code=UTF-8 --sort-by-file $(find ./trelby -type f -name '*.py') trelby.py

echo "File po/trelby.pot created."
