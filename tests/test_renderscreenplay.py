import u
import util

def testRenderScreenplay() -> None:
    sp = u.load()
    data = sp.generatePDF(True)

    assert len(data) > 200
    assert data[:8] == util.toLatin1("%PDF-1.5")

def testRenderScreenplayWithCustomFont() -> None:
    sp = u.load()
    for pfi in sp.cfg.getPDFFontIds():
        pf = sp.cfg.getPDFFont(pfi)
        pf.pdfName = "Jost"
        pf.filename = u.fixtureFilePath('custom-font/Jost-400-Book.ttf')

    data = sp.generatePDF(True)

    assert len(data) > 200
    assert data[:8] == util.toLatin1("%PDF-1.5")