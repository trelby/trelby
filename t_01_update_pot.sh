#!/bin/bash
xgettext -j -L Python -o po/trelby.pot \
	--package-name=trelby \
        --package-version=2.4.16 \
        --copyright-holder="Gwyn Ciesla <gwync@protonmail.com>" \
	$(find ./trelby -type f -name '*.py')
