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

#### Run instructions after build

1. `cd trelby`

2. `source venv/bin/activate`

3. `./trelby.py`

Alternatively follow the below instructions to create an application version of Trelby.

#### Build Trelby.app
To build a application version of Trelby follow the below instructions

1. Follow the 'Build from source on Mac' steps

2. Run `pyinstaller --name 'Trelby' --icon 'trelby.ico' --windowed --add-data='trelby:trelby' trelby.py`

3. Open the 'dist' folder and open 'Trelby.app'
  - or run `open dist`

4. Copy `Trelby.app` your applications folder