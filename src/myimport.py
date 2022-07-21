import config
import gutil
import misc
import screenplay
import titles
import util

from lxml import etree
import wx

import io
import re
import zipfile

# special linetype that means that indent contains action and scene lines,
# and scene lines are the ones that begin with "EXT." or "INT."
SCENE_ACTION = -2

# special linetype that means don't import those lines; useful for page
# numbers etc
IGNORE = -3

#like importTextFile, but for Adobe Story files.
def importAstx(fileName, frame):
    # astx files are xml files. The textlines can be found under
    # AdobeStory/document/stream/section/scene/paragraph which contain
    # one or more textRun/break elements, to be joined. The paragraph
    # attribute "element" gives us the element style.

    data = util.loadFile(fileName, frame, 5000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    elemMap = {
        "Action" : screenplay.ACTION,
        "Character" : screenplay.CHARACTER,
        "Dialog" : screenplay.DIALOGUE,
        "Parenthetical" : screenplay.PAREN,
        "SceneHeading" : screenplay.SCENE,
        "Shot" : screenplay.SHOT,
        "Transition" : screenplay.TRANSITION,
    }

    try:
        root = etree.XML(data)
    except etree.XMLSyntaxError as e:
        wx.MessageBox("Error parsing file: %s" %e, "Error", wx.OK, frame)
        return None

    lines = []

    def addElem(eleType, items):
        # if elem ends in a newline, last line is empty and useless;
        # get rid of it
        if not items[-1] and (len(items) > 1):
            items = items[:-1]

        for s in items[:-1]:
            lines.append(screenplay.Line(
                    screenplay.LB_FORCED, eleType, util.cleanInput(s)))

        lines.append(screenplay.Line(
                screenplay.LB_LAST, eleType, util.cleanInput(items[-1])))

    for para in root.xpath("/AdobeStory/document/stream/section/scene/paragraph"):
        lt = elemMap.get(para.get("element"), screenplay.ACTION)

        items = []
        s = ""

        for text in para:
            if text.tag == "textRun" and text.text:
                s += text.text
            elif text.tag == "break":
                items.append(s.rstrip())
                s = ""

        items.append(s.rstrip())

        addElem(lt, items)

    if not lines:
        wx.MessageBox("File has no content.", "Error", wx.OK, frame)
        return None

    return lines

# like importTextFile, but for fadein files.
def importFadein(fileName, frame):
    # Fadein file is a zipped document.xml file.
    # the .xml is in open screenplay format:
    # http://sourceforge.net/projects/openscrfmt/files/latest/download

    # the 5 MB limit is arbitrary, we just want to avoid getting a
    # MemoryError exception for /dev/zero etc.
    data = util.loadFile(fileName, frame, 5000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    buf = io.StringIO(data)

    try:
        z = zipfile.ZipFile(buf)
        f = z.open("document.xml")
        content = f.read()
        z.close()
    except:
        wx.MessageBox("File is not a valid .fadein file.", "Error", wx.OK, frame)
        return None

    if not content:
        wx.MessageBox("Script seems to be empty.", "Error", wx.OK, frame)
        return None

    elemMap = {
        "Action" : screenplay.ACTION,
        "Character" : screenplay.CHARACTER,
        "Dialogue" : screenplay.DIALOGUE,
        "Parenthetical" : screenplay.PAREN,
        "Scene Heading" : screenplay.SCENE,
        "Shot" : screenplay.SHOT,
        "Transition" : screenplay.TRANSITION,
    }

    try:
        root = etree.XML(content)
    except etree.XMLSyntaxError as e:
        wx.MessageBox("Error parsing file: %s" %e, "Error", wx.OK, frame)
        return None

    lines = []

    def addElem(eleType, lns):
        # if elem ends in a newline, last line is empty and useless;
        # get rid of it
        if not lns[-1] and (len(lns) > 1):
            lns = lns[:-1]

        for s in lns[:-1]:
            lines.append(screenplay.Line(
                    screenplay.LB_FORCED, eleType, util.cleanInput(s)))

        lines.append(screenplay.Line(
                screenplay.LB_LAST, eleType, util.cleanInput(lns[-1])))

    # removes html formatting from s, and returns list of lines.
    # if s is None, return a list with single empty string.
    re_rem = [r'<font[^>]*>', r'<size[^>]*>', r'<bgcolor[^>]*>']
    rem = ["<b>", "</b>", "<i>", "</i>", "<u>",
           "</u>", "</font>", "</size>", "</bgcolor>"]
    def sanitizeStr(s):
        if s:
            s = "" + s
            for r in re_rem:
                s = re.sub(r, "", s)
            for r in rem:
                s = s.replace(r,"")

            if s:
                return s.split("<br>")
            else:
                return [""]
        else:
            return [""]

    for para in root.xpath("paragraphs/para"):
        # check for notes/synopsis, import as Note.
        if para.get("note"):
            lt = screenplay.NOTE
            items = sanitizeStr("" + para.get("note"))
            addElem(lt, items)

        if para.get("synopsis"):
            lt = screenplay.NOTE
            items = sanitizeStr("" + para.get("synopsis"))
            addElem(lt, items)

        # look for the <style> and <text> tags. Bail if no <text> found.
        styl = para.xpath("style")
        txt = para.xpath("text")
        if txt:
            if styl:
                lt = elemMap.get(styl[0].get("basestylename"), screenplay.ACTION)
            else:
                lt = screenplay.ACTION

            items = sanitizeStr(txt[0].text)

            if (lt == screenplay.PAREN) and items and (items[0][0] != "("):
                items[0] = "(" + items[0]
                items[-1] = items[-1] + ")"
        else:
            continue

        addElem(lt, items)

    if len(lines) == 0:
        wx.MessageBox("The file contains no importable lines", "Error", wx.OK, frame)
        return None

    return lines

# like importTextFile, but for Celtx files.
def importCeltx(fileName, frame):
    # Celtx files are zipfiles, and the script content is within a file
    # called "script-xxx.html", where xxx can be random.

    # the 5 MB limit is arbitrary, we just want to avoid getting a
    # MemoryError exception for /dev/zero etc.
    data = util.loadFile(fileName, frame, 5000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    buf = io.StringIO(data)

    try:
        z = zipfile.ZipFile(buf)
    except:
        wx.MessageBox("File is not a valid Celtx script file.", "Error", wx.OK, frame)
        return None

    files = z.namelist()
    scripts = [s for s in files if s.startswith("script") ]

    if len(scripts) == 0:
        wx.MessageBox("Unable to find script in this Celtx file.", "Error", wx.OK, frame)
        return None

    f = z.open(scripts[0])
    content = f.read()
    z.close()

    if not content:
        wx.MessageBox("Script seems to be empty.", "Error", wx.OK, frame)
        return None

    elemMap = {
        "action" : screenplay.ACTION,
        "character" : screenplay.CHARACTER,
        "dialog" : screenplay.DIALOGUE,
        "parenthetical" : screenplay.PAREN,
        "sceneheading" : screenplay.SCENE,
        "shot" : screenplay.SHOT,
        "transition" : screenplay.TRANSITION,
        "act" : screenplay.ACTBREAK,
    }

    try:
        parser = etree.HTMLParser()
        root = etree.XML(content, parser)
    except etree.XMLSyntaxError as e:
        wx.MessageBox("Error parsing file: %s" %e, "Error", wx.OK, frame)
        return None

    lines = []

    def addElem(eleType, lns):
        # if elem ends in a newline, last line is empty and useless;
        # get rid of it
        if not lns[-1] and (len(lns) > 1):
            lns = lns[:-1]

        for s in lns[:-1]:
            lines.append(screenplay.Line(
                    screenplay.LB_FORCED, eleType, util.cleanInput(s)))

        lines.append(screenplay.Line(
                screenplay.LB_LAST, eleType, util.cleanInput(lns[-1])))

    for para in root.xpath("/html/body/p"):
        items = []
        for line in para.itertext():
            items.append(str(line.replace("\n", " ")))

        lt = elemMap.get(para.get("class"), screenplay.ACTION)

        if items:
            addElem(lt, items)

    if len(lines) == 0:
        wx.MessageBox("The file contains no importable lines", "Error", wx.OK, frame)
        return None

    return lines

# like importTextFile, but for Final Draft files.
def importFDX(fileName, frame):
    elemMap = {
        "Action" : screenplay.ACTION,
        "Character" : screenplay.CHARACTER,
        "Dialogue" : screenplay.DIALOGUE,
        "Parenthetical" : screenplay.PAREN,
        "Scene Heading" : screenplay.SCENE,
        "Shot" : screenplay.SHOT,
        "Transition" : screenplay.TRANSITION,
    }

    # the 5 MB limit is arbitrary, we just want to avoid getting a
    # MemoryError exception for /dev/zero etc.
    data = util.loadFile(fileName, frame, 5000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    try:
        root = etree.XML(data.encode("UTF-8"))
        lines = []

        def addElem(eleType, eleText):
            lns = eleText.split("\n")

            # if elem ends in a newline, last line is empty and useless;
            # get rid of it
            if not lns[-1] and (len(lns) > 1):
                lns = lns[:-1]

            for s in lns[:-1]:
                lines.append(screenplay.Line(
                        screenplay.LB_FORCED, eleType, util.cleanInput(s)))

            lines.append(screenplay.Line(
                    screenplay.LB_LAST, eleType, util.cleanInput(lns[-1])))

        for para in root.xpath("Content//Paragraph"):
            addedNote = False
            et = para.get("Type")

            # Check for script notes
            s = ""
            for notes in para.xpath("ScriptNote/Paragraph/Text"):
                if notes.text:
                    s += notes.text

                # FD has AdornmentStyle set to "0" on notes with newline.
                if notes.get("AdornmentStyle") == "0":
                    s += "\n"

            if s:
                addElem(screenplay.NOTE, s)
                addedNote = True

            # "General" has embedded Dual Dialogue paragraphs inside it;
            # nothing to do for the General element itself.
            #
            # If no type is defined (like inside scriptnote), skip.
            if (et == "General") or (et is None):
                continue

            s = ""
            for text in para.xpath("Text"):
                # text.text is None for paragraphs with no text, and +=
                # blows up trying to add a string object and None, so
                # guard against that
                if text.text:
                    s += text.text

            # don't remove paragraphs with no text, unless that paragraph
            # contained a scriptnote
            if s or not addedNote:
                lt = elemMap.get(et, screenplay.ACTION)
                addElem(lt, s)

        if len(lines) == 0:
            wx.MessageBox("The file contains no importable lines", "Error", wx.OK, frame)
            return None

        return lines

    except etree.XMLSyntaxError as e:
        wx.MessageBox("Error parsing file: %s" %e, "Error", wx.OK, frame)
        return None

# import Fountain files.
# http://fountain.io
def importFountain(fileName, frame, titlePages):
    # regular expressions for fountain markdown.
    # https://github.com/vilcans/screenplain/blob/master/screenplain/richstring.py
    ire = re.compile(
            # one star
            r'\*'
            # anything but a space, then text
            r'([^\s].*?)'
            # finishing with one star
            r'\*'
            # must not be followed by star
            r'(?!\*)'
        )
    bre = re.compile(
            # two stars
            r'\*\*'
            # must not be followed by space
            r'(?=\S)'
            # inside text
            r'(.+?[*_]*)'
            # finishing with two stars
            r'(?<=\S)\*\*'
        )
    ure = re.compile(
            # underline
            r'_'
            # must not be followed by space
            r'(?=\S)'
            # inside text
            r'([^_]+)'
            # finishing with underline
            r'(?<=\S)_'
        )
    boneyard_re = re.compile('/\\*.*?\\*/', flags=re.DOTALL)

    # random magicstring used to escape literal star '\*'
    literalstar = "Aq7RR"

    # returns s with markdown formatting removed.
    def unmarkdown(s):
        s = s.replace("\\*", literalstar)
        for style in (bre, ire, ure):
            s = style.sub(r'\1', s)
        return s.replace(literalstar, "*")

    data = util.loadFile(fileName, frame, 1000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)
        return None

    inf = []
    inf.append(misc.CheckBoxItem("Import titles to title page."))
    inf.append(misc.CheckBoxItem("Import titles as action lines.",selected=False))
    inf.append(misc.CheckBoxItem("Remove unsupported formatting markup."))
    inf.append(misc.CheckBoxItem("Import section/synopsis as notes."))

    dlg = misc.CheckBoxDlg(frame, "Fountain import options", inf,
        "Import options:", False)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        return None, titlePages

    importTitlePage = inf[0].selected
    importTitles = inf[1].selected
    removeMarkdown = inf[2].selected
    importSectSyn = inf[3].selected

    # pre-process data - fix newlines, remove boneyard.
    data = util.fixNL(data)
    data = boneyard_re.sub('', data)
    prelines = data.split("\n")
    for i in range(len(prelines)):
        try:
            util.toLatin1(prelines[i])
        except:
            prelines[i] = util.cleanInput("" + prelines[i].decode('UTF-8', "ignore"))
    lines = []

    tabWidth = 4
    lns = []
    TWOSPACE = "  "
    skipone = False

    # First check if title lines are present:
    c = 0
    while c < len(prelines):
        if prelines[c] != "":
            c = c+1
        else:
            break

    # prelines[0:i] are the first bunch of lines, that could be titles.
    # Our check for title is simple:
    #   - the line does not start with 'fade'
    #   - the first line has a single ':'

    if c > 0:
        l = util.toInputStr(prelines[0].expandtabs(tabWidth).lstrip().lower())
        if not l.startswith("fade") and l.count(":") == 1:
            # these are title lines. Now do what the user requested.
            if importTitlePage:
                #Extract usable title page lines
                kwPattern = re.compile(r'^([A-za-z][^:]+:)')
                continuePattern = re.compile(r'^\s\s\s+') # line begins with 3 or more spaces
                titleIdx=0
                gatheredTitles=[]
                rejects=[]
                l = prelines[0]
                while l != '':
                    match=kwPattern.split(l)
                    match=[ll.strip() for ll in match]
                    if len(match) == 3: # keyword line
                        if match[2] == '':
                            follows=[]
                            titleIdx+=1 # gather indented prelines
                            nextline = continuePattern.match(prelines[titleIdx])
                            while nextline:
                                follows.append(prelines[titleIdx].strip('_* \t'))
                                titleIdx+=1
                                nextline = continuePattern.match(prelines[titleIdx])
                            titleIdx-=1
                            gatheredTitles.append([match[1],follows])
                        else:
                            gatheredTitles.append([match[1],[match[2].strip('_* \t')]])
                    else:
                        l += TWOSPACE
                        rejects.append(l)
                    titleIdx+=1
                    l=prelines[titleIdx]
                # replace default titles with imported ones
                leftX = 15.0
                leftY = 220.0
                centreX = 0.0
                centreY = 150.0
                for t in gatheredTitles:
                    titlenr=-1
                    if t[0] == 'Title:':
                        titlenr=0
                    elif t[0] == 'Author:' or t[0]=='Authors:':
                        titlenr=1
                        t[1]=["by",""]+t[1]
                    elif t[0] == 'Contact:':
                        titlenr=2
                    else:
                        titlenr=len(titlePages[0])
                        if t[0] == 'Credit:' or t[0] == 'Source:':
                            centred = True
                            thisX = centreX
                            thisY = centreY
                            centreY += 5
                        else:
                            centred = False
                            thisX = leftX
                            thisY=leftY
                            leftY -= 5
                        if len(t[1])==1:
                            newItems = [t[0]+" "+t[1][0]]
                        else:
                            newItems = [t[0]]+t[1]
                        newTitleString = titles.TitleString(newItems, y = thisY, isCentered = centred)
                        titlePages[0].append( newTitleString)
                        continue
                    targetTitle=titlePages[0][titlenr]
                    targetTitle.items=t[1]
                # user might request that titles go into both title page & script
                if not importTitles:
                    rejects += prelines[c+1:]
                    prelines=rejects
            if importTitles:
                # add TWOSPACE to all the title lines.
                for i in range(c):
                    prelines[i] += TWOSPACE
            elif not importTitlePage:
                #remove these lines
                prelines = prelines[c+1:]

    for l in prelines:
        if l != TWOSPACE:
            lines.append(util.toInputStr(l.expandtabs(tabWidth)))
        else:
            lines.append(TWOSPACE)

    linesLen = len(lines)

    def isPrevEmpty():
        if lns and lns[-1].text == "":
            return True
        return False

    def isPrevType(ltype):
        return (lns and lns[-1].lt == ltype)

    # looks ahead to check if next line is not empty
    def isNextEmpty(i):
        return  (i+1 < len(lines) and lines[i+1] == "")

    def getPrevType():
        if lns:
            return lns[-1].lt
        else:
            return screenplay.ACTION

    def isParen(s):
        return (s.startswith('(') and s.endswith(')'))

    def isScene(s):
        if s.endswith(TWOSPACE):
            return False
        if s.startswith(".") and not s.startswith(".."):
            return True
        tmp = s.upper()
        if (re.match(r'^(INT|EXT|EST)[ .]', tmp) or
            re.match(r'^(INT\.?/EXT\.?)[ .]', tmp) or
            re.match(r'^I/E[ .]', tmp)):
            return True
        return False

    def isTransition(s):
        return ((s.isupper() and s.endswith("TO:")) or
                (s.startswith(">") and not s.endswith("<")))

    def isCentered(s):
        return s.startswith(">") and s.endswith("<")

    def isPageBreak(s):
        return s.startswith('===') and s.lstrip('=') == ''

    def isNote(s):
        return s.startswith("[[") and s.endswith("]]")

    def isSection(s):
        return s.startswith("#")

    def isSynopsis(s):
        return s.startswith("=") and not s.startswith("==")

    # first pass - identify linetypes
    for i in range(linesLen):
        if skipone:
            skipone = False
            continue

        s = lines[i]
        sl = s.lstrip()
        # mark as ACTION by default.
        line = screenplay.Line(screenplay.LB_FORCED, screenplay.ACTION, s)

        # Start testing lines for element type. Go in order:
        # Scene Character, Paren, Dialog, Transition, Note.

        if s == "" or isCentered(s) or isPageBreak(s):
            # do nothing - import as action.
            pass

        elif s == TWOSPACE:
            line.lt = getPrevType()

        elif isScene(s):
            line.lt = screenplay.SCENE
            if sl.startswith('.'):
                line.text = sl[1:]
            else:
                line.text = sl

        elif isTransition(sl) and isPrevEmpty() and isNextEmpty(i):
            line.lt = screenplay.TRANSITION
            if line.text.startswith('>'):
                line.text = sl[1:].lstrip()

        elif s.isupper() and isPrevEmpty() and not isNextEmpty(i):
            line.lt = screenplay.CHARACTER
            if s.endswith(TWOSPACE):
                line.lt = screenplay.ACTION

        elif isParen(sl) and (isPrevType(screenplay.CHARACTER) or
                                isPrevType(screenplay.DIALOGUE)):
            line.lt = screenplay.PAREN

        elif (isPrevType(screenplay.CHARACTER) or
             isPrevType(screenplay.DIALOGUE) or
             isPrevType(screenplay.PAREN)):
            line.lt = screenplay.DIALOGUE

        elif isNote(sl):
            line.lt = screenplay.NOTE
            line.text = sl.strip('[]')

        elif isSection(s) or isSynopsis(s):
            if not importSectSyn:
                if isNextEmpty(i):
                    skipone = True
                continue

            line.lt = screenplay.NOTE
            line.text = sl.lstrip('=#')

        if line.text == TWOSPACE:
            pass

        elif line.lt != screenplay.ACTION:
            line.text = line.text.lstrip()

        else:
            tmp = line.text.rstrip()
            # we don't support center align, so simply add required indent.
            if isCentered(tmp):
                tmp = tmp[1:-1].strip()
                width = frame.panel.ctrl.sp.cfg.getType(screenplay.ACTION).width
                if len(tmp) < width:
                    tmp = ' ' * ((width - len(tmp)) // 2) + tmp
            line.text = tmp

        if removeMarkdown:
            line.text = unmarkdown(line.text)
            if line.lt == screenplay.CHARACTER and line.text.endswith('^'):
                line.text = line.text[:-1]

        lns.append(line)

    ret = []

    # second pass helper functions.
    def isLastLBForced():
        return ret and ret[-1].lb == screenplay.LB_FORCED

    def makeLastLBLast():
        if ret:
            ret[-1].lb = screenplay.LB_LAST

    def isRetPrevType(t):
        return ret and ret[-1].lt == t

    # second pass - remove unneeded empty lines, and fix the linebreaks.
    for ln in lns:
        if ln.text == '':
            if isLastLBForced():
                makeLastLBLast()
            else:
                ret.append(ln)

        elif not isRetPrevType(ln.lt):
            makeLastLBLast()
            ret.append(ln)

        else:
            ret.append(ln)

    makeLastLBLast()
    return ret, titlePages

# import text file from fileName, return list of Line objects for the
# screenplay or None if something went wrong. returned list always
# contains at least one line.
def importTextFile(fileName, frame):

    # the 1 MB limit is arbitrary, we just want to avoid getting a
    # MemoryError exception for /dev/zero etc.
    data = util.loadFile(fileName, frame, 1000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    data = util.fixNL(data)
    lines = data.split("\n")

    tabWidth = 4

    # key = indent level, value = Indent
    indDict = {}

    for i in range(len(lines)):
        s = util.toInputStr(lines[i].rstrip().expandtabs(tabWidth))

        # don't count empty lines towards indentation statistics
        if s.strip() == "":
            lines[i] = ""

            continue

        cnt = util.countInitial(s, " ")

        ind = indDict.get(cnt)
        if not ind:
            ind = Indent(cnt)
            indDict[cnt] = ind

        tmp = s.upper()

        if util.multiFind(tmp, ["EXT.", "INT."]):
            ind.sceneStart += 1

        if util.multiFind(tmp, ["CUT TO:", "DISSOLVE TO:"]):
            ind.trans += 1

        if re.match(r"^ +\(.*\)$", tmp):
            ind.paren += 1

        ind.lines.append(s.lstrip())
        lines[i] = s

    if len(indDict) == 0:
        wx.MessageBox("File contains only empty lines.", "Error", wx.OK, frame)

        return None

    # scene/action indent
    setType(SCENE_ACTION, indDict, lambda v: v.sceneStart)

    # indent with most lines is dialogue in non-pure-action scripts
    setType(screenplay.DIALOGUE, indDict, lambda v: len(v.lines))

    # remaining indent with lines is character most likely
    setType(screenplay.CHARACTER, indDict, lambda v: len(v.lines))

    # transitions
    setType(screenplay.TRANSITION, indDict, lambda v: v.trans)

    # parentheticals
    setType(screenplay.PAREN, indDict, lambda v: v.paren)

    # some text files have this type of parens:
    #
    #        JOE
    #      (smiling and
    #       hopping along)
    #
    # this handles them.
    parenIndent = findIndent(indDict, lambda v: v.lt == screenplay.PAREN)
    if parenIndent != -1:
        paren2Indent = findIndent(indDict,
            lambda v, var: (v.lt == -1) and (v.indent == var),
            parenIndent + 1)

        if paren2Indent != -1:
            indDict[paren2Indent].lt = screenplay.PAREN

    # set line type to ACTION for any indents not recognized
    for v in indDict.values():
        if v.lt == -1:
            v.lt = screenplay.ACTION

    dlg = ImportDlg(frame, list(indDict.values()))

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()

        return None

    dlg.Destroy()

    ret = []

    for i in range(len(lines)):
        s = lines[i]
        cnt = util.countInitial(s, " ")
        s = s.lstrip()
        sUp = s.upper()

        if s:
            lt = indDict[cnt].lt

            if lt == IGNORE:
                continue

            if lt == SCENE_ACTION:
                if s.startswith("EXT.") or s.startswith("INT."):
                    lt = screenplay.SCENE
                else:
                    lt = screenplay.ACTION

            if ret and (ret[-1].lt != lt):
                ret[-1].lb = screenplay.LB_LAST

            if lt == screenplay.CHARACTER:
                if sUp.endswith("(CONT'D)"):
                    s = sUp[:-8].rstrip()

            elif lt == screenplay.PAREN:
                if s == "(continuing)":
                    s = ""

            if s:
                line = screenplay.Line(screenplay.LB_SPACE, lt, s)
                ret.append(line)

        elif ret:
            ret[-1].lb = screenplay.LB_LAST

    if len(ret) == 0:
        ret.append(screenplay.Line(screenplay.LB_LAST, screenplay.ACTION))

    # make sure the last line ends an element
    ret[-1].lb = screenplay.LB_LAST

    return ret

# go through indents, find the one with maximum value in something, and
# set its linetype to given lt.
def setType(lt, indDict, func):
    maxCount = 0
    found = -1

    for v in indDict.values():
        # don't touch indents already set
        if v.lt != -1:
            continue

        val = func(v)

        if val > maxCount:
            maxCount = val
            found = v.indent

    if found != -1:
        indDict[found].lt = lt

# go through indents calling func(it, *vars) on each. return indent count
# for the indent func returns True, or -1 if it returns False for each.
def findIndent(indDict, func, *vars):
    for v in indDict.values():
        if func(v, *vars):
            return v.indent

    return -1

# information about one indent level in imported text files.
class Indent:
    def __init__(self, indent):

        # indent level, i.e. spaces at the beginning
        self.indent = indent

        # lines with this indent, leading spaces removed
        self.lines = []

        # assigned line type, or -1 if not assigned yet.
        self.lt = -1

        # how many of the lines start with "EXT." or "INT."
        self.sceneStart = 0

        # how many of the lines have "CUT TO:" or "DISSOLVE TO:"
        self.trans = 0

        # how many of the lines have a form of "^ +\(.*)$", i.e. are most
        # likely parentheticals
        self.paren = 0


class ImportDlg(wx.Dialog):
    def __init__(self, parent, indents):
        wx.Dialog.__init__(self, parent, -1, "Adjust styles",
                           style = wx.DEFAULT_DIALOG_STYLE)

        indents.sort(key=lambda indent: indent.lines)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        tmp = wx.StaticText(self, -1, "Input:")
        vsizer.Add(tmp)

        self.inputLb = wx.ListBox(self, -1, size = (400, 200))
        for it in indents:
            self.inputLb.Append("%d lines (indented %d characters)" %
                                (len(it.lines), it.indent), it)

        vsizer.Add(self.inputLb, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Style:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.styleCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        self.styleCombo.Append("Scene / Action", SCENE_ACTION)
        for t in config.getTIs():
            self.styleCombo.Append(t.name, t.lt)

        self.styleCombo.Append("Ignore", IGNORE)

        util.setWH(self.styleCombo, w = 150)

        hsizer.Add(self.styleCombo, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.TOP | wx.BOTTOM, 10)

        vsizer.Add(wx.StaticText(self, -1, "Lines:"))

        self.linesEntry = wx.TextCtrl(self, -1, size = (400, 200),
            style = wx.TE_MULTILINE | wx.TE_DONTWRAP)
        vsizer.Add(self.linesEntry, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        self.Bind(wx.EVT_COMBOBOX, self.OnStyleCombo, id=self.styleCombo.GetId())
        self.Bind(wx.EVT_LISTBOX, self.OnInputLb, id=self.inputLb.GetId())

        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancelBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okBtn.GetId())

        self.inputLb.SetSelection(0)
        self.OnInputLb()

    def OnOK(self, event):
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnInputLb(self, event = None):
        self.selected = self.inputLb.GetClientData(self.inputLb.GetSelection())

        util.reverseComboSelect(self.styleCombo, self.selected.lt)
        self.linesEntry.SetValue("\n".join(self.selected.lines))

    def OnStyleCombo(self, event):
        self.selected.lt = self.styleCombo.GetClientData(
            self.styleCombo.GetSelection())
