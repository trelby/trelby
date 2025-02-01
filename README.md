# Trelby
## Screenplay writing software
Trelby is a screenplay writing program. See https://www.trelby.org/ for
more details.

### About this project
This project is a fork of https://github.com/trelby/trelby 2.4.14 version

Updates in this fork:
- html-stylesheet-mac.xsl
- manual-mac.xml
- regentry-mac.xml
- doc/Makefile updated to work with Mac

### Installation

#### Fedora

`sudo dnf install trelby`

#### From PyPi

`pip (or pip3) install trelby`

#### Build from source on Mac

1. `git clone https://github.com/Dave-and-Isaac/trelby.git`

2. `cd trelby`

3. `python3 -m venv venv`

4. `source venv/bin/activate`

5. `pip3 install -r requirements.txt`

6. `make`

7. `./trelby.py`