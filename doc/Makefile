XSLTPROC = xsltproc

BOOK_HTML_TARGET = book.html

BOOK_XML_SOURCE = book.xml
BOOK_VERSION_SOURCE = version.xml
BOOK_ALL_SOURCE = *.xml

XSL_HTML = html-stylesheet.xsl

# Book xsltproc options for HTML output
# Note: --stringparam arguments no longer go here; 
# see tools/html-stylesheet.xsl and tools/chunk-stylesheet.xsl
BOOK_HTML_XSLTPROC_OPTS = 

all: html

clean: book-clean

html: $(BOOK_HTML_TARGET)

$(BOOK_HTML_TARGET): $(BOOK_ALL_SOURCE) $(BOOK_VERSION_SOURCE)
	$(XSLTPROC) $(BOOK_HTML_XSLTPROC_OPTS) \
           --output $(BOOK_HTML_TARGET) $(XSL_HTML) $(BOOK_XML_SOURCE)

book-clean:
	rm -f $(BOOK_HTML_TARGET)
