.PHONY = dist

BINDIR = $(DESTDIR)/opt/blyte
DESKTOPDIR = $(DESTDIR)/usr/share/applications

dist: names.txt.gz dict_en.dat.gz manual.pdf
	./gen_linux_dist.sh linux
	debuild -b

src:
	./gen_linux_dist.sh src

names.txt.gz: names.txt
	gzip -c names.txt > names.txt.gz

dict_en.dat.gz: dict_en.dat
	gzip -c dict_en.dat > dict_en.dat.gz

manual.pdf: doc/*
	make -C doc && mv doc/book.html manual.html

clean:
	rm -f *.pyc
	dh_clean

install:
	mkdir -p $(BINDIR)
	cp -r *.py trelby.desktop names.txt.gz dict_en.dat.gz sample.trelby manual.html fileformat.txt LICENSE INSTALL resources $(BINDIR)
	cp trelby.desktop $(DESKTOPDIR)
	rm $(BINDIR)/setup.py

uninstall:
	rm -f $(BINDIR)
