PREFIX = $(DESTDIR)/usr

.PHONY : clean dist deb

dist: names.txt.gz dict_en.dat.gz manual.html trelby.1.gz
	python3 setup.py sdist && cp trelby.1.gz doc/

deb: dist
	debuild -us -uc -b

names.txt.gz: names.txt
	gzip -c names.txt > names.txt.gz

dict_en.dat.gz: dict_en.dat
	gzip -c dict_en.dat > dict_en.dat.gz

manual.html: doc/*
	make -C doc html && mv doc/manual.html .

trelby.1.gz: doc/*
	make -C doc manpage && mv doc/trelby.1.gz .

rpm: dist
	python3 setup.py bdist_rpm

clean:
	rm -f bin/*.pyc src/*.pyc tests/*.pyc names.txt.gz dict_en.dat.gz manual.html MANIFEST trelby.1.gz doc/trelby.1.gz
	rm -rf build dist
	dh_clean

install: dist
	python3 setup.py install

test:
	cd tests && ./all.sh
