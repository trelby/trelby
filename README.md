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

#### Fedora

sudo dnf install trelby

#### From PyPi

`pip (or pip3) install trelby`

#### From source

1. git clone https://github.com/trelby/trelby.git

2. cd trelby

3. pip3 install -r requirements.txt  
   *Depending on your python version, you might run into https://github.com/wxWidgets/Phoenix/issues/2296. We recommend executing `pip3 install attrdict3` before installing the requirements in that case. If that still doesn't work, we recommend upgrading your python version.*

4. make

5. ./trelby.py