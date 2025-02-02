import tests.u as u
import trelby.scriptreport as scriptreport
import trelby.util as util

# tests script report (just that it runs without exceptions, for now)


def testBasic():
    sp = u.load()
    report = scriptreport.ScriptReport(sp)
    data = report.generate()

    # try to catch cases where generate returns something other than a PDF
    # document
    assert len(data) > 200
    assert data[:8] == util.toLatin1("%PDF-1.5")
