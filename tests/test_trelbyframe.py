import trelby.trelbyframe as trelbyframe
import trelby.translations as translations


_ = translations.trelby_translations_load()


def test_setting_mnemonics_first_letter():
    assert trelbyframe.to_mnemonics('N', 'New') == '&New'
    assert trelbyframe.to_mnemonics('n', 'New') == '&New'

def test_setting_mnemonics_not_first_letter():
    assert trelbyframe.to_mnemonics('e', 'New') == 'N&ew'
    assert trelbyframe.to_mnemonics('E', 'New') == 'N&ew'

def test_setting_mnemonics_not_in():
    assert trelbyframe.to_mnemonics('x', 'New') == 'New (&X)'
    assert trelbyframe.to_mnemonics('X', 'New') == 'New (&X)'

def test_setting_mnemonics_first_upper_not_first_letter():
    assert trelbyframe.to_mnemonics('N', 'not New') == 'not &New'
    assert trelbyframe.to_mnemonics('n', 'not New') == 'not &New'

def test_setting_mnemonics_all_lower():
    assert trelbyframe.to_mnemonics('N', 'not new') == '&not new'
    assert trelbyframe.to_mnemonics('n', 'not new') == '&not new'

def test_setting_mnemonics_with_shortcut_first_letter():
    assert trelbyframe.to_mnemonics('N', 'New\tCTRL-L') == '&New\tCTRL-L'
    assert trelbyframe.to_mnemonics('n', 'New\tCTRL-L') == '&New\tCTRL-L'

def test_setting_mnemonics_with_shortcut_not_first_letter():
    assert trelbyframe.to_mnemonics('e', 'New\tCTRL-L') == 'N&ew\tCTRL-L'
    assert trelbyframe.to_mnemonics('E', 'New\tCTRL-L') == 'N&ew\tCTRL-L'

def test_setting_mnemonics_with_shortcut_not_in():
    assert trelbyframe.to_mnemonics('x', 'New\tCTRL-L') == 'New (&X)\tCTRL-L'
    assert trelbyframe.to_mnemonics('X', 'New\tCTRL-L') == 'New (&X)\tCTRL-L'
