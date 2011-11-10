.PHONY = dist

BINDIR = $(DESTDIR)/opt/blyte
DESKTOPDIR = $(DESTDIR)/usr/share/applications

dist: names.dat dict_en.dat.gz manual.pdf
	./gen_linux_dist.sh linux
	debuild -b

src:
	./gen_linux_dist.sh src

names.dat: names.txt
	cd tools && ./make_names.py

dict_en.dat.gz: dict_en.dat
	gzip -c dict_en.dat > dict_en.dat.gz

manual.pdf: doc/*
	make -C doc && mv doc/book.html manual.html

clean:
	rm -f *.pyc
	dh_clean

install:
	mkdir -p $(BINDIR)
	cp -r *.py blyte.desktop names.dat dict_en.dat.gz sample.blyte manual.html fileformat.txt LICENSE INSTALL resources $(BINDIR)
	cp blyte.desktop $(DESKTOPDIR)
	rm $(BINDIR)/setup.py

uninstall:
	rm -f $(BINDIR)
