"""Types characters on X11 through XTest, like a real keyboard.

pynput types characters with XSendEvent, and many apps ignore those events since they're
flagged as synthetic. Its named keys and modifiers already go through XTest, so only
characters need this. python-xlib is installed with pynput on Linux.
"""
from Xlib import X, XK
from Xlib.display import Display
from Xlib.ext import xtest

display = Display()
borrowed_keycodes = []  # unused keycodes given a character the keyboard layout doesn't have


def keycode_for(keysym):
    """Finds the keycode typing keysym, and whether it needs Shift"""
    first = display.display.info.min_keycode
    mapping = display.get_keyboard_mapping(first, display.display.info.max_keycode - first + 1)
    for offset, keysyms in enumerate(mapping):
        if keysym in keysyms[:2]:
            return first + offset, keysyms.index(keysym) == 1
    # Not on the layout (or only behind AltGr): map it to an unused keycode, or reuse the oldest borrowed one
    spare = next((first + offset for offset, keysyms in enumerate(mapping) if not any(keysyms)), None)
    keycode = spare if spare is not None else borrowed_keycodes.pop(0)
    display.change_keyboard_mapping(keycode, [(keysym, keysym)])
    display.sync()
    borrowed_keycodes.append(keycode)
    return keycode, False


def type_character(char):
    code = ord(char)
    keysym = code if 0x20 <= code <= 0x7E or 0xA0 <= code <= 0xFF else 0x01000000 | code  # X11's keysym for it
    keycode, shift = keycode_for(keysym)
    shift_keycode = display.keysym_to_keycode(XK.XK_Shift_L)
    if shift:
        xtest.fake_input(display, X.KeyPress, shift_keycode)
    xtest.fake_input(display, X.KeyPress, keycode)
    xtest.fake_input(display, X.KeyRelease, keycode)
    if shift:
        xtest.fake_input(display, X.KeyRelease, shift_keycode)
    display.sync()
