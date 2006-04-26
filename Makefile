PROG := blyte

.PHONY = dist clean dists_prep

$(PROG): linux.c Makefile
	@echo Compiling...
	@gcc -Wall -ansi -pedantic -D_GNU_SOURCE linux.c -O2 -o $(PROG) -lz
	@strip $(PROG)

prep:
	cd tools && ./make_names.py
	make -C doc pdf && mv doc/manual.pdf .
	gzip -c dict_en.dat > dict_en.dat.gz

dist: $(PROG)
	./gen_linux_dist.sh

dists_prep:
	./prep_linux_dists.sh

clean:
	rm -f $(PROG)
