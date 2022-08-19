import characterreport
import u

# tests character report (just that it runs without exceptions, for now)

def testBasic():
    sp = u.load()
    report = characterreport.CharacterReport(sp)
    data = report.generate()

    # try to catch cases where generate returns something other than a PDF
    # document
    assert len(data) > 200
    assert data[:8] == "%PDF-1.5"
