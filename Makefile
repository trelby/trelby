.PHONY : clean dist dmg

dist: trelby/names.txt.gz trelby/dict_en.dat.gz trelby/manual.html trelby/trelby.1.gz
	cp trelby/trelby.1.gz doc/

dmg:
	./build_dmg.sh $(VERSION)

trelby/names.txt.gz: trelby/names.txt
	gzip -c trelby/names.txt > trelby/names.txt.gz

trelby/dict_en.dat.gz: trelby/dict_en.dat
	gzip -c trelby/dict_en.dat > trelby/dict_en.dat.gz

trelby/manual.html: doc/*
	make -C doc html && mv doc/manual.html trelby/

trelby/trelby.1.gz: doc/*
	make -C doc manpage && mv doc/trelby.1.gz trelby/

clean:
	rm -f trelby/*.pyc tests/*.pyc trelby/names.txt.gz trelby/dict_en.dat.gz trelby/manual.html trelby/trelby.1.gz doc/trelby.1.gz
	rm -rf build dist *.egg-info trelby/*.egg-info tests/__pycache__ trelby/__pycache__

test:
	pytest
