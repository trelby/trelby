XSLTPROC = xsltproc
GZIP = gzip -n -9

BOOK_HTML_TARGET = manual.html

BOOK_XML_SOURCE = manual.xml
BOOK_VERSION_SOURCE = version.xml
BOOK_ALL_SOURCE = *.xml

MANPAGE_SOURCE = refentry.xml
MANPAGE = trelby.1
MANPAGE_GZIP_TARGET = $(MANPAGE).gz

XSL_MANPAGE = /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl
XSL_HTML = html-stylesheet.xsl

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
