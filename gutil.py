from error import *
import misc
import util

import os
import tempfile

from wxPython.wx import *

# this contains misc GUI-related functions

# since at least GTK 1.2's single-selection listbox is buggy in that if we
# don't deselect the old item manually, it does multiple selections, we
# have this function that does the following:
#
#  1) deselects current selection, if any
#  2) select the item with the given index
def listBoxSelect(lb, index):
    old = lb.GetSelection()

    if  old!= -1:
        lb.SetSelection(old, False)

    lb.SetSelection(index, True)

# add (name, cdata) to the listbox at the correct place, determined by
# cmp(cdata1, cdata2).
def listBoxAdd(lb, name, cdata):
    for i in range(lb.GetCount()):
        if cmp(cdata, lb.GetClientData(i)) < 0:
            lb.InsertItems([name], i)
            lb.SetClientData(i, cdata)

            return

    lb.Append(name, cdata)

# create stock button. id is wxID_APPLY etc. WX2.6-FIXME: remove this,
# have callers do this directly.
def createStockButton(parent, id, label):
    if misc.wx26:
        return wxButton(parent, id)
    else:
        return wxButton(parent, -1, label)
    
# show PDF document 'pdfData' in an external viewer program. writes out a
# temporary file, first deleting all old temporary files, then opens PDF
# viewer application. 'mainFrame' is used as a parent for message boxes in
# case there are any errors.
def showTempPDF(pdfData, cfgGl, mainFrame):
    try:
        try:
            util.removeTempFiles(misc.tmpPrefix)

            fd, filename = tempfile.mkstemp(prefix = misc.tmpPrefix,
                                            suffix = ".pdf")

            try:
                os.write(fd, pdfData)
            finally:
                os.close(fd)

            util.showPDF(filename, cfgGl, mainFrame)

        except IOError, (errno, strerror):
            raise MiscError("IOError: %s" % strerror)

    except BlyteError, e:
        wxMessageBox("Error writing temporary PDF file: %s" % e,
                     "Error", wxOK, mainFrame)
