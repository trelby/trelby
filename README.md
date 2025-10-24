# Trelby
## Screenplay writing software
Trelby is a screenplay writing program. See https://www.trelby.org/ for
more details.

### About this project
This project has recently been updated by merging the fork: https://github.com/Dave-and-Isaac/trelby.

Updates include:
- a conversion to Python 3
- enhancements
- updating the Windows packaging to provide a Windows build (still in progress)
- doc/Makefile updated to work with MacOS

### Installation

#### Fedora

`sudo dnf install trelby`

#### Windows (Chocolatey)

Once chocolatey is set up (https://chocolatey.org/install):

`choco install trelby`

#### Flatpak

`flatpak install trelby`

#### From PyPi

`pip (or pip3) install trelby`

#### From source

1. `git clone https://github.com/trelby/trelby.git`

2. `cd trelby`

3. `python3 -m venv venv`

4. `source venv/bin/activate`

5. `pip3 install -r requirements.txt`
   *Depending on your python version, you might run into https://github.com/wxWidgets/Phoenix/issues/2296. We recommend executing `pip3 install attrdict3` before installing the requirements in that case. If that still doesn't work, we recommend upgrading your python version.*

6. `make`

7. `./trelby.py`

#### Build MacOS Trelby.app
To build a application version of Trelby follow the below instructions

1. Follow the 'Build from source on Mac' steps

2. Run `pyinstaller --name 'Trelby' --icon 'trelby.ico' --windowed --add-data='trelby:trelby' trelby.py`

3. Open the 'dist' folder and open 'Trelby.app'
  - or run `open dist`
  - When opened it may tell you the program could be malicious. This isn't malicious just unsigned.
  - To still open the app to go settings -> privacy and security -> scroll to the bottom and allow the application.
  - re-open `Trelby.app`

4. Copy `Trelby.app` your applications folder
