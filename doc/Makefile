XSLTPROC = xsltproc

BOOK_INSTALL_DIR = install
BOOK_HTML_CHUNK_DIR = html-chunk
BOOK_HTML_TARGET = book.html

# index.html is created last
BOOK_HTML_CHUNK_TARGET = $(BOOK_HTML_CHUNK_DIR)/index.html

BOOK_PDF_TARGET = manual.pdf
BOOK_FO_TARGET = book.fo
BOOK_XML_SOURCE = book.xml
BOOK_VERSION_SOURCE = version.xml
BOOK_ALL_SOURCE = *.xml

#BOOK_IMAGES = images/*.png
BOOK_IMAGES =

BOOK_INSTALL_DIR = $(INSTALL_DIR)/book

XSL_FO = fo-stylesheet.xsl
XSL_HTML = html-stylesheet.xsl
XSL_HTML_CHUNK = chunk-stylesheet.xsl

# Book xsltproc options for HTML output
# Note: --stringparam arguments no longer go here; 
# see tools/html-stylesheet.xsl and tools/chunk-stylesheet.xsl
BOOK_HTML_XSLTPROC_OPTS = 

# Book xsltproc options for PDF and PostScript output
# BOOK_PDF_XSLTPROC_OPTS = --stringparam page.height 9in --stringparam page.width 6.4in
# BOOK_PS_XSLTPROC_OPTS = --stringparam page.height 9in --stringparam page.width 6.4in

# Uncomment the following line if you'd like to print on A4 paper
# BOOK_PDF_XSLTPROC_OPTS = --stringparam paper.type A4

#all: all-html pdf
all: html

all-html: html chunk

install: install-html install-chunk install-pdf

clean: book-clean

#$(BOOK_VERSION_SOURCE): book-version

html: $(BOOK_HTML_TARGET)

$(BOOK_HTML_TARGET): $(BOOK_ALL_SOURCE) $(BOOK_VERSION_SOURCE)
	$(XSLTPROC) $(BOOK_HTML_XSLTPROC_OPTS) \
           --output $(BOOK_HTML_TARGET) $(XSL_HTML) $(BOOK_XML_SOURCE)

chunk: $(BOOK_HTML_CHUNK_TARGET)

# The trailing slash is essential that xsltproc will output pages to the dir
$(BOOK_HTML_CHUNK_TARGET): $(BOOK_ALL_SOURCE) $(BOOK_VERSION_SOURCE) \
                           styles.css $(BOOK_IMAGES)
	mkdir -p $(BOOK_HTML_CHUNK_DIR)
	$(XSLTPROC) $(BOOK_HTML_XSLTPROC_OPTS) \
           --output $(BOOK_HTML_CHUNK_DIR)/ \
	   $(XSL_HTML_CHUNK) $(BOOK_XML_SOURCE)
	cp styles.css $(BOOK_HTML_CHUNK_DIR)
#	cp $(BOOK_IMAGES) $(BOOK_HTML_CHUNK_DIR)

pdf: $(BOOK_PDF_TARGET)

$(BOOK_PDF_TARGET): $(BOOK_ALL_SOURCE) $(BOOK_VERSION_SOURCE) $(BOOK_IMAGES)
	$(XSLTPROC) $(BOOK_PDF_XSLTPROC_OPTS) \
	   --output $(BOOK_FO_TARGET) $(XSL_FO) $(BOOK_XML_SOURCE)
	fop $(BOOK_TOP) -fo $(BOOK_FO_TARGET) -pdf $(BOOK_PDF_TARGET)

$(BOOK_INSTALL_DIR):
	$(INSTALL) -d $(BOOK_INSTALL_DIR)

install-html: $(BOOK_HTML_TARGET)
#	$(INSTALL) -d $(BOOK_INSTALL_DIR)/images
	$(INSTALL) $(BOOK_HTML_TARGET) $(BOOK_INSTALL_DIR)
	$(INSTALL) styles.css $(BOOK_INSTALL_DIR)
#	$(INSTALL) $(BOOK_IMAGES) $(BOOK_INSTALL_DIR)/images

install-chunk: $(BOOK_HTML_CHUNK_TARGET)
#	$(INSTALL) -d $(BOOK_INSTALL_DIR)/images
	$(INSTALL) $(BOOK_HTML_CHUNK_DIR)/*.html $(BOOK_INSTALL_DIR)
	$(INSTALL) styles.css $(BOOK_INSTALL_DIR)
#	$(INSTALL) $(BOOK_IMAGES) $(BOOK_INSTALL_DIR)/images

install-pdf: $(BOOK_PDF_TARGET) $(BOOK_INSTALL_DIR)
	$(INSTALL) $(BOOK_PDF_TARGET) $(BOOK_INSTALL_DIR)

book-clean:
	rm -f $(BOOK_HTML_TARGET) $(BOOK_FO_TARGET)
	rm -rf $(BOOK_HTML_CHUNK_DIR)
	rm -f $(BOOK_PDF_TARGET)
