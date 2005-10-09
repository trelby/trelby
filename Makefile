PROG := blyte

.PHONY = dist clean

$(PROG): linux.c Makefile
	@echo Compiling...
	@gcc -Wall -ansi -pedantic -D_GNU_SOURCE linux.c -O2 -o $(PROG) -lz
	@strip $(PROG)

prep: $(PROG)
	cd tools && ./make_names.py
	make -C doc pdf && mv doc/manual.pdf .
	gzip -c dict_en.dat > dict_en.dat.gz

dist: $(PROG)
	./gen_linux_dist.sh

clean:
	rm -f $(PROG)
