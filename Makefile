PROG := blyte

.PHONY = dist clean

$(PROG): linux.c Makefile
	@echo Compiling...
	@gcc -Wall -ansi -pedantic -D_GNU_SOURCE linux.c -O2 -o $(PROG) -lz
	@strip $(PROG)

dist: $(PROG)
	./gen_linux_dist.sh

clean:
	rm -f $(PROG)
