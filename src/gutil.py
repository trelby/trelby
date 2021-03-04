from error import MiscError,TrelbyError
import misc
import util

import os
import tempfile

if "TRELBY_TESTING" in os.environ:
    import unittest.mock as mock
    wx = mock.Mock()
else:
    import wx

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
        if util.cmpfunc(cdata, lb.GetClientData(i)) < 0:
            lb.InsertItems([name], i)
            lb.SetClientData(i, cdata)

            return

    lb.Append(name, cdata)

# create stock button.
def createStockButton(parent, label):
    # wxMSW does not really have them: it does not have any icons and it
    # inconsistently adds the shortcut key to some buttons, but not to
    # all, so it's better not to use them at all on Windows.
    if misc.isUnix:
        ids = {
            "OK" : wx.ID_OK,
            "Cancel" : wx.ID_CANCEL,
            "Apply" : wx.ID_APPLY,
            "Add" : wx.ID_ADD,
            "Delete" : wx.ID_DELETE,
            "Preview" : wx.ID_PREVIEW
            }

        return wx.Button(parent, ids[label])
    else:
        return wx.Button(parent, -1, label)

# wxWidgets has a bug in 2.6 on wxGTK2 where double clicking on a button
# does not send two wx.EVT_BUTTON events, only one. since the wxWidgets
# maintainers do not seem interested in fixing this
# (http://sourceforge.net/tracker/index.php?func=detail&aid=1449838&group_id=9863&atid=109863),
# we work around it ourselves by binding the left mouse button double
# click event to the same callback function on the buggy platforms.
def btnDblClick(btn, func):
    if misc.isUnix:
        btn.Bind(wx.EVT_LEFT_DCLICK, func)

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
                os.write(fd, pdfData.encode("UTF-8"))
            finally:
                os.close(fd)

            util.showPDF(filename, cfgGl, mainFrame)

        except IOError as xxx_todo_changeme:
            (errno, strerror) = xxx_todo_changeme.args
            raise MiscError("IOError: %s" % strerror)

    except TrelbyError as e:
        wx.MessageBox("Error writing temporary PDF file: %s" % e,
                      "Error", wx.OK, mainFrame)
