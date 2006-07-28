.PHONY = dist

dist: names.dat dict_en.dat.gz manual.pdf
	./gen_linux_dist.sh

names.dat: names.txt
	cd tools && ./make_names.py

dict_en.dat.gz: dict_en.dat
	gzip -c dict_en.dat > dict_en.dat.gz

manual.pdf: doc/*
	make -C doc pdf && mv doc/manual.pdf .
