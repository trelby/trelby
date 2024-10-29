# Trelby
## Screenplay writing software
Trelby is a screenplay writing program. See https://www.trelby.org/ for
more details.

### About this project
This project has recently been updated by merging the fork: https://github.com/limburgher/trelby.

Updates include:
- a conversion to Python 3
- enhancements
- updating the Windows packaging to provide a Windows build (still in progress)

### Installation

#### From source

1. git clone https://github.com/trelby/trelby.git

2. cd trelby

3. pip3 install -r requirements.txt  
   *Depending on your python version, you might run into https://github.com/wxWidgets/Phoenix/issues/2296. We recommend executing `pip3 install attrdict3` before installing the requirements in that case. If that still doesn't work, we recommend upgrading your python version.*

4. ./bin/trelby

#### Debian and variants

1. sudo apt install python3-setuptools wxpython-tools python3-lxml python3-reportlab

2. Download and install the .deb file for Ubuntu, Debian, or Raspian here:

https://software.opensuse.org//download.html?project=home%3Agwync&package=trelby

- or -

1. sudo apt install python3-setuptools wxpython-tools python3-lxml python3-reportlab

2. make deb

3. Install the resulting .deb file

#### Fedora

sudo dnf install trelby

#### Windows

It works on any windows that works with a supported version of python. It currently has to be manually installed. Ensure the dependencies in requirements.txt (either through pip or via msys2) and run the trelby.bat BATCH script.
