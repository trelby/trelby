import copy
import io
import re
import zipfile
from typing import List, Optional

import wx
from lxml import etree

import trelby.config as config
import trelby.gutil as gutil
import trelby.misc as misc
import trelby.screenplay as screenplay
import trelby.titles as titles
import trelby.util as util
from trelby.importreviewdlg import TextImportReviewDlg
from trelby.line import Line

# special linetype that means don't import those lines; useful for page
# numbers etc
IGNORE = -3


# like importTextFile, but for Adobe Story files.
def importAstx(fileName, frame):
    # astx files are xml files. The textlines can be found under
    # AdobeStory/document/stream/section/scene/paragraph which contain
    # one or more textRun/break elements, to be joined. The paragraph
    # attribute "element" gives us the element style.

    data = util.loadFile(fileName, frame, -1)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox(_("File is empty."), _("Error"), wx.OK, frame)

        return None

    elemMap = {
        "Action": screenplay.ACTION,
        "Character": screenplay.CHARACTER,
        "Dialog": screenplay.DIALOGUE,
        "Parenthetical": screenplay.PAREN,
        "SceneHeading": screenplay.SCENE,
        "Shot": screenplay.SHOT,
        "Transition": screenplay.TRANSITION,
    }

    try:
        root = etree.XML(data)
    except etree.XMLSyntaxError as e:
        wx.MessageBox(_("Error parsing file: {}".format(e)), _("Error"), wx.OK, frame)
        return None

    lines = []

    def addElem(eleType, items):
        # if elem ends in a newline, last line is empty and useless;
        # get rid of it
        if not items[-1] and (len(items) > 1):
            items = items[:-1]

        for s in items[:-1]:
            lines.append(Line(screenplay.LB_FORCED, eleType, util.cleanInput(s)))

        lines.append(Line(screenplay.LB_LAST, eleType, util.cleanInput(items[-1])))

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
        wx.MessageBox(_("File has no content."), _("Error"), wx.OK, frame)
        return None

    return lines


# like importTextFile, but for fadein files.
def importFadein(fileName, frame):
    # Fadein file is a zipped document.xml file.
    # the .xml is in open screenplay format:
    # http://sourceforge.net/projects/openscrfmt/files/latest/download

    try:
        with zipfile.ZipFile(fileName) as fadein_file:
            with fadein_file.open("document.xml") as fadein_document:
                data = fadein_document.read()
    except:
        wx.MessageBox(_("File is not a valid .fadein file."), _("Error"), wx.OK, frame)
        return None

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox(_("File is empty."), _("Error"), wx.OK, frame)
        return None

    elemMap = {
        "Action": screenplay.ACTION,
        "Character": screenplay.CHARACTER,
        "Dialogue": screenplay.DIALOGUE,
        "Parenthetical": screenplay.PAREN,
        "Scene Heading": screenplay.SCENE,
        "Shot": screenplay.SHOT,
        "Transition": screenplay.TRANSITION,
    }

    try:
        root = etree.XML(data)
    except etree.XMLSyntaxError as e:
        wx.MessageBox(_("Error parsing file: {}".format(e)), _("Error"), wx.OK, frame)
        return None

    lines = []

    def addElem(eleType, lns):
        # if elem ends in a newline, last line is empty and useless;
        # get rid of it
        if not lns[-1] and (len(lns) > 1):
            lns = lns[:-1]

        for s in lns[:-1]:
            lines.append(Line(screenplay.LB_FORCED, eleType, util.cleanInput(s)))

        lines.append(Line(screenplay.LB_LAST, eleType, util.cleanInput(lns[-1])))

    # removes html formatting from s, and returns list of lines.
    # if s is None, return a list with single empty string.
    re_rem = [r"<font[^>]*>", r"<size[^>]*>", r"<bgcolor[^>]*>"]
    rem = [
        "<b>",
        "</b>",
        "<i>",
        "</i>",
        "<u>",
        "</u>",
        "</font>",
        "</size>",
        "</bgcolor>",
    ]

    def sanitizeStr(s):
        if s:
            s = "" + s
            for r in re_rem:
                s = re.sub(r, "", s)
            for r in rem:
                s = s.replace(r, "")

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
        wx.MessageBox(
            _("The file contains no importable lines"), _("Error"), wx.OK, frame
        )
        return None

    return lines


# like importTextFile, but for Celtx files.
def importCeltx(fileName, frame):
    # Celtx files are zipfiles, and the script content is within a file
    # called "script-xxx.html", where xxx can be random.
    try:
        z = zipfile.ZipFile(fileName)
    except:
        wx.MessageBox(
            _("File is not a valid Celtx script file."), _("Error"), wx.OK, frame
        )
        return None

    files = z.namelist()
    scripts = [s for s in files if s.startswith("script")]

    if len(scripts) == 0:
        wx.MessageBox(
            _("Unable to find script in this Celtx file."), _("Error"), wx.OK, frame
        )
        return None

    f = z.open(scripts[0])
    content = f.read()
    z.close()

    if not content:
        wx.MessageBox(_("Script seems to be empty."), _("Error"), wx.OK, frame)
        return None

    elemMap = {
        "action": screenplay.ACTION,
        "character": screenplay.CHARACTER,
        "dialog": screenplay.DIALOGUE,
        "parenthetical": screenplay.PAREN,
        "sceneheading": screenplay.SCENE,
        "shot": screenplay.SHOT,
        "transition": screenplay.TRANSITION,
        "act": screenplay.ACTBREAK,
    }

    try:
        parser = etree.HTMLParser()
        root = etree.XML(content, parser)
    except etree.XMLSyntaxError as e:
        wx.MessageBox(_("Error parsing file: {}".format(e)), _("Error"), wx.OK, frame)
        return None

    lines = []

    def addElem(eleType, lns):
        # if elem ends in a newline, last line is empty and useless;
        # get rid of it
        if not lns[-1] and (len(lns) > 1):
            lns = lns[:-1]

        for s in lns[:-1]:
            lines.append(Line(screenplay.LB_FORCED, eleType, util.cleanInput(s)))

        lines.append(Line(screenplay.LB_LAST, eleType, util.cleanInput(lns[-1])))

    for para in root.xpath("/html/body/p"):
        items = []
        for line in para.itertext():
            text = line.replace("\n", " ").strip()
            if text != "":
                items.append(text)

        lt = elemMap.get(para.get("class"), screenplay.ACTION)

        if items:
            addElem(lt, items)

    if len(lines) == 0:
        wx.MessageBox(
            _("The file contains no importable lines"), _("Error"), wx.OK, frame
        )
        return None

    return lines


# like importTextFile, but for Final Draft files.
def importFDX(fileName, frame):
    elemMap = {
        "Action": screenplay.ACTION,
        "Character": screenplay.CHARACTER,
        "Dialogue": screenplay.DIALOGUE,
        "Parenthetical": screenplay.PAREN,
        "Scene Heading": screenplay.SCENE,
        "Shot": screenplay.SHOT,
        "Transition": screenplay.TRANSITION,
    }

    data = util.loadFile(fileName, frame, -1)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox(_("File is empty."), _("Error"), wx.OK, frame)

        return None

    # https://github.com/trelby/trelby/issues/61
    data = data.replace("\u2028", "\n")

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
                lines.append(Line(screenplay.LB_FORCED, eleType, util.cleanInput(s)))

            lines.append(Line(screenplay.LB_LAST, eleType, util.cleanInput(lns[-1])))

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
            wx.MessageBox(
                _("The file contains no importable lines"), _("Error"), wx.OK, frame
            )
            return None

        return lines

    except etree.XMLSyntaxError as e:
        wx.MessageBox(_("Error parsing file: {}".format(e)), _("Error"), wx.OK, frame)
        return None


# import Fountain files.
# http://fountain.io
def importFountain(fileName, frame, titlePages):
    # regular expressions for fountain markdown.
    # https://github.com/vilcans/screenplain/blob/master/screenplain/richstring.py
    ire = re.compile(
        # one star
        r"\*"
        # anything but a space, then text
        r"([^\s].*?)"
        # finishing with one star
        r"\*"
        # must not be followed by star
        r"(?!\*)"
    )
    bre = re.compile(
        # two stars
        r"\*\*"
        # must not be followed by space
        r"(?=\S)"
        # inside text
        r"(.+?[*_]*)"
        # finishing with two stars
        r"(?<=\S)\*\*"
    )
    ure = re.compile(
        # underline
        r"_"
        # must not be followed by space
        r"(?=\S)"
        # inside text
        r"([^_]+)"
        # finishing with underline
        r"(?<=\S)_"
    )
    boneyard_re = re.compile("/\\*.*?\\*/", flags=re.DOTALL)

    # random magicstring used to escape literal star '\*'
    literalstar = "Aq7RR"

    # returns s with markdown formatting removed.
    def unmarkdown(s):
        s = s.replace("\\*", literalstar)
        for style in (bre, ire, ure):
            s = style.sub(r"\1", s)
        return s.replace(literalstar, "*")

    data = _loadImportText(fileName, frame)

    if data == None:
        return None, titlePages

    if len(data) == 0:
        wx.MessageBox(_("File is empty."), _("Error"), wx.OK, frame)
        return None, titlePages

    inf = []
    inf.append(misc.CheckBoxItem(_("Import titles to title page.")))
    inf.append(misc.CheckBoxItem(_("Import titles as action lines."), selected=False))
    inf.append(misc.CheckBoxItem(_("Remove unsupported formatting markup.")))
    inf.append(misc.CheckBoxItem(_("Import section/synopsis as notes.")))

    dlg = misc.CheckBoxDlg(
        frame, _("Fountain import options"), inf, _("Import options:"), False
    )

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        return None, titlePages

    importTitlePage = inf[0].selected
    importTitles = inf[1].selected
    removeMarkdown = inf[2].selected
    importSectSyn = inf[3].selected

    # work on a copy, so cancelling leaves the caller's title pages alone
    titlePages = copy.deepcopy(titlePages)

    # pre-process data - fix newlines, remove boneyard. the boneyard's
    # newlines are replaced by markers, so that original line numbers can
    # be shown in the review.
    data = util.fixNL(data)
    data = boneyard_re.sub(lambda m: "\0" * m.group().count("\n"), data)
    prelines = data.split("\n")

    # nums[i] is the line number in the file of prelines[i]
    nums = []
    lineNo = 1
    for i in range(len(prelines)):
        nums.append(lineNo)
        lineNo += 1 + prelines[i].count("\0")
        prelines[i] = prelines[i].replace("\0", "")

    tabWidth = 4
    lns = []
    TWOSPACE = "  "
    skipone = False

    # lines holding nothing but whitespace are empty lines. the one
    # exception is exactly two spaces, which Fountain uses for an
    # intentionally blank line inside an element.
    for i in range(len(prelines)):
        if prelines[i] != TWOSPACE and prelines[i].strip() == "":
            prelines[i] = ""

    lines = []

    # a single period followed by a letter or digit forces a scene heading.
    # this allows action and dialogue to start with an ellipsis.
    def isForcedScene(s):
        return re.match(r"^\.[^\W_]", s) is not None

    def isScene(s):
        if s.endswith(TWOSPACE):
            return False
        tmp = s.upper()
        if (
            re.match(r"^(INT|EXT|EST)[ .]", tmp)
            or re.match(r"^(INT\.?/EXT\.?)[ .]", tmp)
            or re.match(r"^I/E[ .]", tmp)
        ):
            return True
        return False

    # a character cue is all upper case, apart from extensions such as
    # "(cont'd)" or "(V.O.)", which may be in any case.
    def isCharacter(s):
        if s.endswith(TWOSPACE):
            return False
        name = re.sub(r"\([^)]*\)?", "", s.rstrip().rstrip("^"))
        return name.isupper()

    def isParen(s):
        return s.startswith("(") and s.endswith(")")

    def isTransition(s):
        return (s.isupper() and s.endswith("TO:")) or (
            s.startswith(">") and not s.endswith("<")
        )

    def isCentered(s):
        return s.startswith(">") and s.endswith("<")

    def isPageBreak(s):
        return s.startswith("===") and s.lstrip("=") == ""

    def isNote(s):
        return s.startswith("[[") and s.endswith("]]")

    def isSection(s):
        return s.startswith("#")

    def isSynopsis(s):
        return s.startswith("=") and not s.startswith("==")

    # First check if title lines are present:
    c = 0
    while c < len(prelines):
        if prelines[c] != "":
            c = c + 1
        else:
            break

    # prelines[0:i] are the first bunch of lines, that could be titles.
    # Our check for title is simple:
    #   - the line does not start with 'fade'
    #   - the first line starts with a "Key:" (the value may contain more
    #     colons, e.g. "Title: Alien: Resurrection")
    #   - the first line is not a scene heading or transition

    if c > 0:
        l = util.toInputStr(prelines[0].expandtabs(tabWidth).strip())
        if (
            not l.lower().startswith("fade")
            and re.match(r"^[^\W\d_][\w '-]*:", l)
            and not isScene(l)
            and not isTransition(l)
        ):
            # these are title lines. Now do what the user requested.
            if importTitlePage:
                # Extract usable title page lines
                kwPattern = re.compile(r"^([A-Za-z][^:]+:)")
                # values on their own lines are indented by a tab or 3+ spaces
                continuePattern = re.compile(r"^(\t|   )")
                titleIdx = 0
                gatheredTitles = []
                rejects = []
                rejectNums = []
                l = prelines[0]
                while l != "":
                    match = kwPattern.split(l)
                    match = [ll.strip() for ll in match]
                    if len(match) == 3:  # keyword line
                        if match[2] == "":
                            follows = []
                            titleIdx += 1  # gather indented prelines
                            while titleIdx < c and continuePattern.match(
                                prelines[titleIdx]
                            ):
                                follows.append(prelines[titleIdx].strip("_* \t"))
                                titleIdx += 1
                            titleIdx -= 1
                            gatheredTitles.append([match[1], follows])
                        else:
                            gatheredTitles.append([match[1], [match[2].strip("_* \t")]])
                    else:
                        l += TWOSPACE
                        rejects.append(l)
                        rejectNums.append(nums[titleIdx])
                    titleIdx += 1
                    l = prelines[titleIdx] if titleIdx < c else ""
                # replace default titles with imported ones
                leftX = 15.0
                leftY = 220.0
                centreX = 0.0
                centreY = 150.0
                for t in gatheredTitles:
                    titlenr = -1
                    if t[0] == "Title:":
                        titlenr = 0
                    elif t[0] == "Author:" or t[0] == "Authors:":
                        titlenr = 1
                        t[1] = ["by", ""] + t[1]
                    elif t[0] == "Contact:":
                        titlenr = 2
                    else:
                        titlenr = len(titlePages[0])
                        if t[0] == "Credit:" or t[0] == "Source:":
                            centred = True
                            thisX = centreX
                            thisY = centreY
                            centreY += 5
                        else:
                            centred = False
                            thisX = leftX
                            thisY = leftY
                            leftY -= 5
                        if len(t[1]) == 1:
                            newItems = [t[0] + " " + t[1][0]]
                        else:
                            newItems = [t[0]] + t[1]
                        newTitleString = titles.TitleString(
                            newItems, y=thisY, isCentered=centred
                        )
                        titlePages[0].append(newTitleString)
                        continue
                    targetTitle = titlePages[0][titlenr]
                    targetTitle.items = t[1]
                # user might request that titles go into both title page & script
                if not importTitles:
                    rejects += prelines[c + 1 :]
                    prelines = rejects
                    nums = rejectNums + nums[c + 1 :]
            if importTitles:
                # add TWOSPACE to all the title lines.
                for i in range(c):
                    prelines[i] += TWOSPACE
            elif not importTitlePage:
                # remove these lines
                prelines = prelines[c + 1 :]
                nums = nums[c + 1 :]

    for l in prelines:
        if l != TWOSPACE:
            lines.append(util.toInputStr(l.expandtabs(tabWidth)))
        else:
            lines.append(TWOSPACE)

    linesLen = len(lines)

    # the start of the file counts as an empty line
    def isPrevEmpty():
        return not lns or lns[-1].text == ""

    def isPrevType(ltype):
        return lns and lns[-1].lt == ltype

    # looks ahead to check if next line is empty. the end of the file
    # counts as an empty line.
    def isNextEmpty(i):
        return i + 1 >= len(lines) or lines[i + 1] == ""

    def getPrevType():
        if lns:
            return lns[-1].lt
        else:
            return screenplay.ACTION

    # for each line in lns: line number in the file, and why it needs
    # review (or None)
    lnsNums = []
    lnsIndents = []
    lnsFlags = []

    # line number of the start of a speech that may not be one
    doubtfulSpeech = None

    # line number of a "(" opened in dialogue but not closed on that line
    openParen = None

    # first pass - identify linetypes
    for i in range(linesLen):
        if skipone:
            skipone = False
            continue

        s = lines[i]
        sl = s.lstrip()
        # mark as ACTION by default.
        line = Line(screenplay.LB_FORCED, screenplay.ACTION, s)

        # Start testing lines for element type. Go in order:
        # Scene Character, Paren, Dialog, Transition, Note.

        if s == "" or isCentered(s) or isPageBreak(s):
            # do nothing - import as action.
            pass

        elif s == TWOSPACE:
            line.lt = getPrevType()

        elif sl.startswith("!"):
            # forced action
            line.text = sl[1:]

        elif isForcedScene(sl) or (isScene(sl) and isPrevEmpty() and isNextEmpty(i)):
            # spec: a scene heading has an empty line before and after it
            line.lt = screenplay.SCENE
            if isForcedScene(sl):
                sl = sl[1:]
            line.text = sl
            if removeMarkdown:
                # scene number, e.g. "INT. HOUSE - DAY #1A#"
                line.text = re.sub(r"\s*#[\w.-]+#\s*$", "", line.text)

        elif isTransition(sl) and isPrevEmpty() and isNextEmpty(i):
            line.lt = screenplay.TRANSITION
            if line.text.startswith(">"):
                line.text = sl[1:].lstrip()

        elif sl.startswith("@") and isPrevEmpty() and not isNextEmpty(i):
            # forced character
            line.lt = screenplay.CHARACTER
            line.text = sl[1:]

        elif isCharacter(sl) and isPrevEmpty() and not isNextEmpty(i):
            line.lt = screenplay.CHARACTER

        elif isParen(sl) and (
            isPrevType(screenplay.CHARACTER) or isPrevType(screenplay.DIALOGUE)
        ):
            line.lt = screenplay.PAREN

        elif (
            isPrevType(screenplay.CHARACTER)
            or isPrevType(screenplay.DIALOGUE)
            or isPrevType(screenplay.PAREN)
        ):
            line.lt = screenplay.DIALOGUE

        elif isNote(sl):
            line.lt = screenplay.NOTE
            line.text = sl.strip("[]")

        elif isSection(s) or isSynopsis(s):
            if not importSectSyn:
                if isNextEmpty(i):
                    skipone = True
                continue

            line.lt = screenplay.NOTE
            line.text = sl.lstrip("=#")

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
                    tmp = " " * ((width - len(tmp)) // 2) + tmp
            line.text = tmp

        if removeMarkdown:
            line.text = unmarkdown(line.text)
            if line.lt == screenplay.CHARACTER and line.text.endswith("^"):
                # dual dialogue marker
                line.text = line.text[:-1].rstrip()
            elif line.text.startswith("~"):
                # lyrics marker
                line.text = line.text[1:]

        # lines that follow the Fountain rules, but look like a typing slip
        flag = None

        if line.lt == screenplay.CHARACTER:
            doubtfulSpeech = None
            name = re.sub(r"\([^)]*\)?", "", sl).strip().rstrip("^").strip()

            if isScene(sl):
                flag = _(
                    "Looks like a scene heading, but there's no empty line "
                    "after it, so by the Fountain rules it's a character name."
                )
            elif isTransition(sl):
                flag = _(
                    "Looks like a transition, but there's no empty line after "
                    "it, so by the Fountain rules it's a character name."
                )
            elif not sl.startswith("@") and name[-1:] in (".", "!", "?"):
                flag = _(
                    'An upper case line ending in "{}" with text right after '
                    "it, so by the Fountain rules it's a character name. "
                    "Action in capitals needs an empty line after it."
                ).format(name[-1])

            if flag:
                doubtfulSpeech = nums[i]

        elif line.lt in (screenplay.DIALOGUE, screenplay.PAREN):
            if doubtfulSpeech is not None:
                flag = _(
                    "Part of the speech starting on line {}, which may not "
                    "be a speech."
                ).format(doubtfulSpeech)

            elif openParen is not None:
                flag = _(
                    'Continues the "(" opened on line {}. Fountain '
                    "parentheticals must fit on one line, so it's dialogue."
                ).format(openParen)
                if sl.endswith(")"):
                    openParen = None

            elif sl.startswith("(") and not sl.endswith(")"):
                flag = _(
                    'Starts with "(" but doesn\'t end with ")" on the same '
                    "line, so by the Fountain rules it's dialogue, not a "
                    "parenthetical."
                )
                openParen = nums[i]

            elif isScene(sl):
                flag = _(
                    "Looks like a scene heading, but there's no empty line "
                    "before it, so by the Fountain rules it's dialogue."
                )

            elif sl.isupper() and sl.endswith("TO:"):
                flag = _(
                    "Looks like a transition, but there's no empty line "
                    "before it, so by the Fountain rules it's dialogue."
                )

        else:
            doubtfulSpeech = None
            openParen = None

            if line.lt == screenplay.ACTION and not sl.startswith("!"):
                if isScene(sl):
                    flag = _(
                        "Looks like a scene heading, but it needs an empty "
                        "line before and after it, so by the Fountain rules "
                        "it's action."
                    )
                elif sl.isupper() and sl.endswith("TO:"):
                    flag = _(
                        "Looks like a transition, but it needs an empty line "
                        "before and after it, so by the Fountain rules it's "
                        "action."
                    )

        lns.append(line)
        lnsNums.append(nums[i])
        lnsIndents.append(len(s) - len(sl))
        lnsFlags.append(flag)

    if any(lnsFlags):
        rows = []
        for ln, num, indent, flag in zip(lns, lnsNums, lnsIndents, lnsFlags):
            if ln.text == "":
                rows.append(None)
                continue

            r = ImportRow(num, indent, ln.text)
            r.lt = ln.lt
            r.flag = flag
            r.line = ln
            rows.append(r)

        dlg = TextImportReviewDlg(
            frame,
            rows,
            _(
                "Line types follow the Fountain rules. The highlighted lines "
                "follow them too, but look like typing slips."
            ),
            REMOVE,
        )

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return None, titlePages

        dlg.Destroy()

        for r in rows:
            if r is not None:
                r.line.lt = r.lt

        lns = [ln for ln in lns if ln.lt != REMOVE]

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
        if ln.text == "":
            if not ret:
                # nothing before the script's first line
                continue
            if isLastLBForced():
                makeLastLBLast()
            else:
                ret.append(ln)

        elif not isRetPrevType(ln.lt):
            makeLastLBLast()
            ret.append(ln)

        else:
            ret.append(ln)

    # empty lines at the end of the file
    while ret and ret[-1].text == "":
        ret.pop()

    # a file with only a title page still needs one line in the script
    if not ret:
        ret.append(Line(screenplay.LB_LAST, screenplay.ACTION, ""))

    makeLastLBLast()
    return ret, titlePages


# ---------------------------------------------------------------------------
# Plain text import.
#
# A plain text script has no markup saying what each line is, so the type
# of a line has to be read from its layout and content. That is done with
# the fixed rules below, and nothing is imported before the user has seen
# the result: TextImportReviewDlg shows every line with its proposed type,
# highlights the lines the rules can't settle unambiguously (with the
# reason), and lists every piece of text that would be removed. The user
# corrects what's wrong, and only then is the script imported.
#
# Clean-up. Proposed in the review; nothing is removed unless confirmed.
#   C1  A line that is only a page number, "(MORE)", "CONTINUED:" or
#       "(CONTINUED)" is not imported.
#   C2  Scene numbers in front of a scene heading, and the same number
#       repeated after it, are removed from the heading.
#   C3  "(CONT'D)" after a character name is removed; Trelby adds it itself.
#   C4  A character name repeated after a page break that interrupted a
#       speech ("(MORE)") is not imported, nor is a "(continuing)" right
#       after it, so the speech stays in one piece.
#
# Content.
#   T1  Scene heading: starts with INT. EXT. EST. INT./EXT. or I/E.
#   T2  Transition: all upper case, ending in "TO:", or one of FADE OUT.,
#       FADE TO BLACK., CUT TO BLACK., SMASH CUT:, MATCH CUT:, JUMP CUT:.
#   T3  Character name: all upper case apart from extensions in brackets
#       such as "(V.O.)", at most 40 characters, not ending in punctuation.
#   T4  Speech: a paragraph starting with a character name (T3) and at
#       least one more line. A line starting with "(" begins a
#       parenthetical that lasts until a line ending with ")"; the other
#       lines are dialogue.
#
# Layout, for indented text (IMSDb, PDF text with layout kept).
#   L1  Character indent: the indent where character names (T3) are
#       directly followed by a line at a different indent. At least half of
#       the lines at that indent must be such names. Most names wins.
#   L2  Dialogue indent: the indent those following lines are most often at.
#   L3  Parenthetical indents: indents where at least half of the lines are
#       parentheticals inside speeches.
#   L4  Action indent: the indent most scene headings are at or, without
#       scene headings, the indent with most lines.
#
# A line's type is settled when its content and its indent agree:
#   - A speech whose name is at the character indent and whose next line
#     is at the dialogue or a parenthetical indent.
#   - A scene heading at the action indent.
#   - A transition on a line of its own.
#   - Any other line at the action indent is action.
# Anything else gets the type the nearest rule suggests and is flagged.
#
# Without a character indent (e.g. text copied from a PDF viewer, which
# loses all indentation) only content counts:
#   - Scene headings and transitions on a line of their own are settled.
#   - A speech (T4) is settled when the name has at least two speeches, has
#     an extension such as "(V.O.)", or is followed by a parenthetical.
#     Otherwise the paragraph is flagged: it may be upper case action.
#   - A paragraph starting with an upper case line ending in "." is
#     flagged: it may be a speech.
#   - Everything else is action.
# ---------------------------------------------------------------------------

# special linetype for lines that are not imported
REMOVE = IGNORE

# scene heading prefixes: INT. EXT. EST. INT./EXT. I/E etc.
_SCENE_RE = re.compile(
    r"^(?:INT\.?\s*/\s*EXT|EXT\.?\s*/\s*INT|INT|EXT|EST|I\s*/\s*E|E\s*/\s*I)"
    r"(?:[.\s]|$)",
    re.IGNORECASE,
)

# scene/page number such as 12, 12A, A12, 12.
_NUM = r"[A-Z]?\d+[A-Z]{0,3}\.?"

# scene number in front of a scene heading
_LEAD_SCENE_NUM_RE = re.compile(r"^(" + _NUM + r")\s+")

# scene number and/or revision asterisk set apart at the end of a line
_TRAIL_SCENE_NUM_RE = re.compile(r"(?:\s{2,}(?:" + _NUM + r"|\*))+$")

# page number lines: "12", "12.", "- 12 -", "Page 12"
_PAGE_NUM_RE = re.compile(r"^(?:PAGE\s*)?[-–—]?\s*\d+\s*[-–—]?\.?$", re.I)

# "(MORE)" at the bottom of a page, in the middle of a speech
_MORE_RE = re.compile(r"^\(\s*MORE\s*\)$", re.I)

# "CONTINUED:", "(CONTINUED)", "12 CONTINUED: (2) 12" etc.
_CONTINUED_RE = re.compile(
    r"^(?:" + _NUM + r"\s+)?\(?\s*CONTINUED\s*:?\s*\)?(?:\s*\(\d+\))?"
    r"(?:\s+" + _NUM + r")?$",
    re.I,
)

# "(CONT'D)" style extensions on character names
_CONTD_RE = re.compile(
    r"\s*\(\s*(?:CONT['’]?D|CONT\.?|CONTINUED|CONTINUING)\s*\)\s*$", re.I
)

# transitions
_TRANS_RE = re.compile(
    r"^(?:[A-Z0-9 .'\-]+ TO:|FADE OUT[.:]?|FADE TO BLACK[.:]?|CUT TO BLACK[.:]?"
    r"|SMASH CUT:?|MATCH CUT:?|JUMP CUT:?)$"
)


class ImportRow:
    """One non-empty line of a text file being imported."""

    def __init__(self, lineNo, indent, text):
        # line number in the file, starting from 1
        self.lineNo = lineNo

        # indent level, after any scene number has been removed
        self.indent = indent

        # text as written, without leading spaces
        self.text = text

        # line type, or REMOVE
        self.lt = screenplay.ACTION

        # why the rules can't settle this line's type, or None
        self.flag = None

        # whether the user has checked a flagged line
        self.checked = False

        # text with clean-up applied, if that differs from the text
        self.cleanText = None

        # the user wants the text as written, without clean-up
        self.keepText = False

        # description of the clean-up applied to this line, if any
        self.note = None

        # True if the line is a scene heading (T1)
        self.scene = False

        # True if the line is "(MORE)"
        self.more = False

        # for a character name repeated after a page break: index of the
        # "(MORE)" row before it
        self.joinFrom = None

    def finalText(self):
        if self.cleanText is not None and not self.keepText:
            return self.cleanText

        return self.text

    def needsReview(self):
        return self.flag is not None and not self.checked

    def setType(self, lt):
        self.lt = lt
        if self.flag:
            self.checked = True


def _loadImportText(fileName, frame):
    """Load a text file for import, returning a str or None.

    Accepts UTF-8 (with or without BOM) and falls back to Windows-1252,
    which is what most older .txt scripts floating around the web use."""

    data = util.loadFile(fileName, frame, -1, True)

    if data is None:
        return None

    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass

    return data.decode("latin-1")


def _isSceneText(s):
    return bool(_SCENE_RE.match(s))


def _isTransText(s):
    return bool(_TRANS_RE.match(s))


def _cueName(s):
    """Return s with extensions in brackets such as (V.O.) removed."""
    return re.sub(r"\s*\([^)]*\)?", " ", s).strip()


def _isCapsText(s):
    """Upper case apart from extensions in brackets, at most 40 chars."""
    name = _cueName(s)

    return (
        0 < len(name) <= 40
        and re.search(r"[^\W\d_]", name) is not None
        and name == name.upper()
    )


def _isCueText(s):
    """Rule T3."""
    if not _isCapsText(s) or _isSceneText(s) or _isTransText(s):
        return False

    name = _cueName(s)

    return name[-1] not in ".!?,;:\"'" and name[0] not in "(-–—"


def _speakerName(s):
    return _cueName(_CONTD_RE.sub("", s)).upper()


def _textToRows(data):
    """Split file contents into rows: None for an empty line, ImportRow
    otherwise. Applies the clean-up rules C1 and C2."""

    data = util.fixNL(data)
    data = data.replace("\f", "\n").replace("\xa0", " ").replace("﻿", "")

    rows = []

    for lineNo, s in enumerate(data.split("\n"), 1):
        s = util.toInputStr(s.expandtabs(4)).rstrip()
        text = s.lstrip()

        if not text:
            rows.append(None)
            continue

        r = ImportRow(lineNo, len(s) - len(text), text)
        rows.append(r)

        if _MORE_RE.match(text):
            r.more = True
            r.lt = REMOVE
            r.note = _("Marks a speech broken by a page break.")
            continue

        if _PAGE_NUM_RE.match(text):
            r.lt = REMOVE
            r.note = _("Page number.")
            continue

        if _CONTINUED_RE.match(text):
            r.lt = REMOVE
            r.note = _("Marks a scene continuing after a page break.")
            continue

        m = _LEAD_SCENE_NUM_RE.match(text)
        if m and _isSceneText(text[m.end() :]):
            r.scene = True
            r.indent += m.end()

            # the same number usually repeats at the end
            num = re.escape(m.group(1).rstrip("."))
            clean = re.sub(r"\s+" + num + r"\.?(?:\s+\*)?$", "", text[m.end() :])
            r.cleanText = _TRAIL_SCENE_NUM_RE.sub("", clean)

        elif _isSceneText(text):
            r.scene = True

            clean = _TRAIL_SCENE_NUM_RE.sub("", text)
            if clean != text:
                r.cleanText = clean

        if r.cleanText is not None:
            r.note = _("Scene number removed.")

    return rows


def _isLive(r):
    """True for rows taking part in the analysis, i.e. not empty lines and
    not clean-up removals."""
    return r is not None and r.lt != REMOVE


def _paragraphs(rows):
    """Return the paragraphs of the text as lists of row indexes. Lines
    removed by clean-up are skipped over, so e.g. a page number doesn't
    split a paragraph. "(MORE)" ends a paragraph, as what follows it on the
    next page starts with the character name again."""

    ret = []
    cur = []

    for i, r in enumerate(rows):
        if r is None or r.more:
            if cur:
                ret.append(cur)
                cur = []
        elif _isLive(r):
            cur.append(i)

    if cur:
        ret.append(cur)

    return ret


def _parenRun(rows, para, j):
    """Return the indexes in para of the parenthetical starting at para[j]."""
    ret = []

    while j < len(para):
        ret.append(j)
        if rows[para[j]].text.endswith(")"):
            break
        j += 1

    return ret


def _isSpeechStart(rows, para):
    """Rule T4."""
    return len(para) >= 2 and _isCueText(rows[para[0]].text)


class _Layout:
    """The indents used for each element type (rules L1-L4)."""

    def __init__(self, rows, paras):
        self.char = None
        self.dlg = None
        self.parens = set()
        self.action = None

        lineCnt = {}
        sceneCnt = {}
        cues = {}
        dlgVotes = {}
        parenCnt = {}

        for r in rows:
            if _isLive(r):
                lineCnt[r.indent] = lineCnt.get(r.indent, 0) + 1
                if r.scene:
                    sceneCnt[r.indent] = sceneCnt.get(r.indent, 0) + 1

        for para in paras:
            first = rows[para[0]]

            if not _isSpeechStart(rows, para):
                continue

            if rows[para[1]].indent == first.indent:
                continue

            cues[first.indent] = cues.get(first.indent, 0) + 1

            j = 1
            while j < len(para):
                if rows[para[j]].text.startswith("("):
                    run = _parenRun(rows, para, j)
                    for k in run:
                        ind = rows[para[k]].indent
                        parenCnt[ind] = parenCnt.get(ind, 0) + 1
                    j = run[-1] + 1
                    continue

                ind = rows[para[j]].indent
                if ind != first.indent:
                    dlgVotes[ind] = dlgVotes.get(ind, 0) + 1
                j += 1

        # L1
        best = None
        for ind, cnt in cues.items():
            if cnt * 2 < lineCnt[ind]:
                continue
            if best is None or (cnt, ind) > (cues[best], best):
                best = ind
        self.char = best

        if self.char is None:
            return

        # L2
        best = None
        for ind, cnt in dlgVotes.items():
            if ind == self.char:
                continue
            if best is None or (cnt, -ind) > (dlgVotes[best], -best):
                best = ind
        self.dlg = best

        # L3
        for ind, cnt in parenCnt.items():
            if ind not in (self.char, self.dlg) and cnt * 2 >= lineCnt[ind]:
                self.parens.add(ind)

        # L4
        used = {self.char, self.dlg} | self.parens
        free = [ind for ind in lineCnt if ind not in used]

        if free:
            if any(sceneCnt.get(ind, 0) for ind in free):
                key = lambda ind: (sceneCnt.get(ind, 0), -ind)
            else:
                key = lambda ind: (lineCnt[ind], -ind)
            self.action = max(free, key=key)

    def describe(self):
        if self.char is None:
            return _(
                "No consistent indentation found, so line types are read "
                "from the text alone."
            )

        parts = [_("character names at column {}").format(self.char)]
        if self.dlg is not None:
            parts.append(_("dialogue at column {}").format(self.dlg))
        if self.parens:
            parts.append(
                _("parentheticals at column {}").format(
                    ", ".join(str(p) for p in sorted(self.parens))
                )
            )
        if self.action is not None:
            parts.append(_("action at column {}").format(self.action))

        return _("Layout found: {}.").format(", ".join(parts))

    def nameFor(self, indent):
        """Element the indent is used for, for messages."""
        if indent == self.char:
            return _("character names")
        if indent == self.dlg:
            return _("dialogue")
        if indent in self.parens:
            return _("parentheticals")
        if indent == self.action:
            return _("action")
        return None


def _typeSpeech(rows, para, layout, flag):
    """Give the rows of a speech paragraph their types. If layout is given,
    lines not at the expected indent are flagged. flag, if given, is set
    on every line."""

    first = rows[para[0]]
    first.lt = screenplay.CHARACTER
    first.flag = flag

    clean = _CONTD_RE.sub("", first.text)
    if clean != first.text and clean:
        first.cleanText = clean
        first.note = _("(CONT'D) removed; Trelby adds it where needed.")

    j = 1
    while j < len(para):
        r = rows[para[j]]

        if r.text.startswith("("):
            run = [para[k] for k in _parenRun(rows, para, j)]
            j += len(run)

            for i in run:
                rows[i].lt = screenplay.PAREN
                rows[i].flag = flag

                if (
                    layout
                    and not flag
                    and rows[i].indent not in layout.parens
                    and rows[i].indent != layout.dlg
                ):
                    rows[i].flag = _(
                        "Parenthetical at column {}, which isn't used for "
                        "parentheticals."
                    ).format(rows[i].indent)

            continue

        j += 1
        r.lt = screenplay.DIALOGUE
        r.flag = flag

        if layout and not flag and r.indent != layout.dlg:
            if r.indent == layout.action:
                r.lt = screenplay.ACTION
                r.flag = _(
                    "Action directly after dialogue, with no empty line "
                    "between them."
                )
            else:
                r.flag = _(
                    "In a speech, but at column {} instead of the dialogue "
                    "column {}."
                ).format(r.indent, layout.dlg)


def _typeByIndent(rows, paras, layout):
    for para in paras:
        first = rows[para[0]]

        if _isSpeechStart(rows, para) and not first.scene:
            second = rows[para[1]]
            atChar = first.indent == layout.char
            intoSpeech = second.indent == layout.dlg or second.indent in layout.parens

            if atChar and intoSpeech:
                _typeSpeech(rows, para, layout, None)
                continue

            if intoSpeech:
                _typeSpeech(
                    rows,
                    para,
                    None,
                    _(
                        "Looks like a speech, but the name is at column {} "
                        "instead of the character column {}."
                    ).format(first.indent, layout.char),
                )
                continue

            if atChar:
                _typeSpeech(
                    rows,
                    para,
                    None,
                    _(
                        "Looks like a speech, but the line after the name is "
                        "at column {}, which isn't used for dialogue."
                    ).format(second.indent),
                )
                continue

        for i in para:
            r = rows[i]

            if r.scene:
                r.lt = screenplay.SCENE
                if layout.action is not None and r.indent != layout.action:
                    r.flag = _(
                        "Scene heading at column {} instead of the action " "column {}."
                    ).format(r.indent, layout.action)

            elif len(para) == 1 and _isTransText(r.text):
                r.lt = screenplay.TRANSITION

            elif r.indent == layout.action:
                r.lt = screenplay.ACTION

            else:
                r.lt = screenplay.ACTION
                used = layout.nameFor(r.indent)

                if used:
                    r.flag = _(
                        "At the column used for {}, but not part of a "
                        "speech. Imported as action."
                    ).format(used)
                else:
                    r.flag = _(
                        "Column {} isn't used by any element type. Imported "
                        "as action."
                    ).format(r.indent)


def _typeByContent(rows, paras):
    speeches = {}
    for para in paras:
        if _isSpeechStart(rows, para) and not rows[para[0]].scene:
            name = _speakerName(rows[para[0]].text)
            speeches[name] = speeches.get(name, 0) + 1

    for para in paras:
        first = rows[para[0]]

        if first.scene:
            first.lt = screenplay.SCENE

            for i in para[1:]:
                rows[i].lt = screenplay.SCENE if rows[i].scene else screenplay.ACTION

            continue

        if len(para) == 1 and _isTransText(first.text):
            first.lt = screenplay.TRANSITION
            continue

        if _isSpeechStart(rows, para):
            settled = (
                speeches[_speakerName(first.text)] >= 2
                or "(" in first.text
                or rows[para[1]].text.startswith("(")
            )
            flag = None
            if not settled:
                flag = _(
                    "An upper case line followed by text: a speech, or "
                    "action written in capitals?"
                )

            _typeSpeech(rows, para, None, flag)
            continue

        flag = None
        if len(para) >= 2 and _isCapsText(first.text) and first.text.endswith("."):
            flag = _(
                'Starts with an upper case line ending in ".": action, or a ' "speech?"
            )

        for i in para:
            rows[i].lt = screenplay.SCENE if rows[i].scene else screenplay.ACTION
            rows[i].flag = flag


def _markContinuations(rows):
    """Rule C4."""

    speaker = None
    more = None
    lastLt = None

    for i, r in enumerate(rows):
        if r is None:
            continue

        if r.more:
            if lastLt in (screenplay.DIALOGUE, screenplay.PAREN) and speaker:
                more = i
            continue

        if r.lt == REMOVE:
            continue

        if r.lt == screenplay.CHARACTER:
            name = _speakerName(r.text)

            if more is not None and name == speaker:
                r.lt = REMOVE
                r.flag = None
                r.cleanText = None
                r.joinFrom = more
                r.note = _("Name repeated after a page break; the speech continues.")

                nxt = next((x for x in rows[i + 1 :] if _isLive(x)), None)
                if (
                    nxt is not None
                    and nxt.lt == screenplay.PAREN
                    and nxt.text.lower() in ("(continuing)", "(cont'd)")
                ):
                    nxt.lt = REMOVE
                    nxt.flag = None
                    nxt.note = _("Repeated after a page break.")

                more = None
                continue

            speaker = name

        more = None
        lastLt = r.lt


def analyzeText(data):
    """Work out line types for a text file's contents. Returns (rows,
    description), where rows has None for empty lines and ImportRow
    objects for the others, and description says what layout was found."""

    rows = _textToRows(data)
    paras = _paragraphs(rows)
    layout = _Layout(rows, paras)

    if layout.char is not None:
        _typeByIndent(rows, paras, layout)
    else:
        _typeByContent(rows, paras)

    _markContinuations(rows)

    return rows, layout.describe()


def rowsToLines(rows):
    """Build screenplay lines from reviewed rows."""

    # empty lines between a "(MORE)" and the repeated name after it don't
    # end the speech, as long as both are left out
    gap = set()
    for i, r in enumerate(rows):
        if (
            r is not None
            and r.joinFrom is not None
            and r.lt == REMOVE
            and rows[r.joinFrom].lt == REMOVE
        ):
            gap.update(range(r.joinFrom, i))

    ret = []

    for i, r in enumerate(rows):
        if r is None:
            if i not in gap and ret:
                ret[-1].lb = screenplay.LB_LAST
            continue

        if r.lt == REMOVE:
            continue

        s = r.finalText()

        if not s:
            continue

        if ret and ret[-1].lt != r.lt:
            ret[-1].lb = screenplay.LB_LAST

        ret.append(screenplay.Line(screenplay.LB_SPACE, r.lt, s))

        # consecutive parentheticals are separate elements
        if r.lt == screenplay.PAREN and s.endswith(")"):
            ret[-1].lb = screenplay.LB_LAST

    if len(ret) == 0:
        ret.append(screenplay.Line(screenplay.LB_LAST, screenplay.ACTION))

    # make sure the last line ends an element
    ret[-1].lb = screenplay.LB_LAST

    return ret


# import text file from fileName, return list of Line objects for the
# screenplay or None if something went wrong or the user cancelled.
# returned list always contains at least one line.
def importTextFile(fileName: str, frame: wx.Frame) -> Optional[List[Line]]:

    data = _loadImportText(fileName, frame)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox(_("File is empty."), _("Error"), wx.OK, frame)

        return None

    rows, layout = analyzeText(data)

    if not any(_isLive(r) for r in rows):
        wx.MessageBox(_("File contains only empty lines."), _("Error"), wx.OK, frame)

        return None

    dlg = TextImportReviewDlg(frame, rows, layout, REMOVE)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()

        return None

    dlg.Destroy()

    return rowsToLines(rows)
