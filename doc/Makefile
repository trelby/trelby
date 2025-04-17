XSLTPROC = xsltproc
GZIP = gzip -n -9

DOCBOOK_DEB = /usr/share/sgml/docbook/stylesheet/xsl
DOCBOOK_ALT = /usr/share/sgml/docbook/xsl-stylesheets
DOCBOOK_MAC = /opt/homebrew/opt/docbook-xsl/docbook-xsl

ifneq ($(wildcard $(DOCBOOK_DEB)),)
    XSL_MANPAGE = $(DOCBOOK_DEB)/docbook-xsl/manpages/docbook.xsl
    XSL_HTML = html-stylesheet-deb.xsl
    BOOK_XML_SOURCE = manual.xml
    MANPAGE_SOURCE = refentry.xml
    BOOK_ALL_SOURCE = *.xml
else ifneq ($(wildcard $(DOCBOOK_ALT)),)
    XSL_MANPAGE = $(DOCBOOK_ALT)/manpages/docbook.xsl
    XSL_HTML = html-stylesheet.xsl
    BOOK_XML_SOURCE = manual.xml
    MANPAGE_SOURCE = refentry.xml
    BOOK_ALL_SOURCE = *.xml
else
    XSL_MANPAGE = $(DOCBOOK_MAC)/manpages/docbook.xsl
    XSL_HTML = html-stylesheet-mac.xsl
    BOOK_XML_SOURCE = manual-mac.xml
    MANPAGE_SOURCE = refentry-mac.xml
    BOOK_ALL_SOURCE = *-mac.xml
endif

BOOK_HTML_TARGET = manual.html

BOOK_VERSION_SOURCE = version.xml

MANPAGE = trelby.1
MANPAGE_GZIP_TARGET = $(MANPAGE).gz

# Book xsltproc options for HTML output
# Note: --stringparam arguments no longer go here;
# see tools/html-stylesheet.xsl and tools/chunk-stylesheet.xsl
BOOK_HTML_XSLTPROC_OPTS =

all: html manpage

clean: book-clean manpage-clean

html: $(BOOK_HTML_TARGET)

manpage: $(MANPAGE_GZIP_TARGET)

$(BOOK_HTML_TARGET): $(BOOK_ALL_SOURCE) $(BOOK_VERSION_SOURCE)
	$(XSLTPROC) $(BOOK_HTML_XSLTPROC_OPTS) \
           --output $(BOOK_HTML_TARGET) $(XSL_HTML) $(BOOK_XML_SOURCE)

$(MANPAGE_GZIP_TARGET): $(MANPAGE_SOURCE) $(BOOK_VERSION_SOURCE)
	$(XSLTPROC) --output $(MANPAGE) $(XSL_MANPAGE) $(MANPAGE_SOURCE)
	$(GZIP) $(MANPAGE)

book-clean:
	rm -f $(BOOK_HTML_TARGET)

manpage-clean:
	rm -f $(MANPAGE_GZIP_TARGET)
