SHELL = /bin/sh
EXE = icloud-photo-dl
BINDIR = /usr/local/bin
ETCDIR = /usr/local/etc/$(EXE)

install:
	install $(EXE).py -o root -g root -m 755 $(BINDIR)
	install -o root -g root -m 755 -d $(ETCDIR)

uninstall:
	rm $(BINDIR)/$(EXE).py

clean:
	rm -f *~
	test -d albums && rm -rf albums

clean-album:
	rm -rf albums
