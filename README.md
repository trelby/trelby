# Trelby
## Screenplay writing software
Trelby is a screenplay writing program. See http://www.trelby.org/ for
more details.

### About this project
This is a fork of the original codebase from https://github.com/trelby/trelby, which as of this writing appears to be dormant.

The major difference of this fork is conversion to Python 3.  I also have a list of possible enhancements in mind, and I'd love help updating the Windows packaging so that I can provide a Windows build.

### Installation

#### From source

1. git clone https://github.com/limburgher/trelby.git

2. cd trelby

3. pip3 install -r requirements.txt  
   *Depending on your python version, you might run into https://github.com/wxWidgets/Phoenix/issues/2296. We recommend executing `pip3 install attrdict3` before installing the requirements in that case. If that still doesn't work, we recommend upgrading your python version.*

4. ./bin/trelby

#### Debian and variants

Download and install the .deb file for Ubuntu, Debian, or Raspian here:

https://software.opensuse.org//download.html?project=home%3Agwync&package=trelby

- or -

1. make deb

2. Install the resulting .deb file.

#### Fedora

sudo dnf install trelby

#### Windows

Currently unsupported, see above.
