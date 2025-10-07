XSLTPROC = xsltproc
GZIP = gzip -n -9

BOOK_HTML_TARGET = manual.html

BOOK_XML_SOURCE = manual.xml
BOOK_VERSION_SOURCE = version.xml
BOOK_ALL_SOURCE = *.xml

MANPAGE_SOURCE = refentry.xml
MANPAGE = trelby.1
MANPAGE_GZIP_TARGET = $(MANPAGE).gz

ifneq ($(wildcard /usr/share/sgml/docbook/stylesheet/xsl/),)
  XSLROOT = /usr/share/sgml/docbook/stylesheet/xsl/
  XSL_PATH = $(XSLROOT)/docbook-xsl/xhtml/
  XSL_MANPAGE = $(XSLROOT)/docbook-xsl/manpages/docbook.xsl
  XSL_HTML = html-stylesheet-deb.xsl
else ifneq ("$(shell brew --prefix docbook-xsl 2>/dev/null)","")
  XSLROOT := $(shell brew --prefix docbook-xsl)/docbook-xsl
  XSL_PATH = $(XSLROOT)/docbook-xsl/xhtml/
  XSL_MANPAGE = $(XSLROOT)/docbook-xsl/manpages/docbook.xsl
  XSL_HTML = html-stylesheet.xsl
else
  XSL_PATH = /usr/share/sgml/docbook/xsl-stylesheets/xhtml
  XSL_MANPAGE = /usr/share/sgml/docbook/xsl-stylesheets/manpages/docbook.xsl
  XSL_HTML = html-stylesheet.xsl
endif


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
		   --path $(XSL_PATH) \
           --output $(BOOK_HTML_TARGET) $(XSL_HTML) $(BOOK_XML_SOURCE)

$(MANPAGE_GZIP_TARGET): $(MANPAGE_SOURCE) $(BOOK_VERSION_SOURCE)
	$(XSLTPROC) \
		--path $(XSL_PATH) \
		--output $(MANPAGE) $(XSL_MANPAGE) $(MANPAGE_SOURCE)
	$(GZIP) $(MANPAGE)

book-clean:
	rm -f $(BOOK_HTML_TARGET)

manpage-clean:
	rm -f $(MANPAGE_GZIP_TARGET)
