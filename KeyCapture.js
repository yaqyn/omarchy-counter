.pragma library

// Qt key events use Unicode for printable keys, and Qt enums for special keys.
// Translate to the XKB names accepted by the existing backend validator.
function keyName(key, keypad) {
    if (key >= Qt.Key_F1 && key <= Qt.Key_F35)
        return "F" + (key - Qt.Key_F1 + 1)
    if (key >= Qt.Key_A && key <= Qt.Key_Z)
        return String.fromCharCode(key).toLowerCase()
    if (key >= Qt.Key_0 && key <= Qt.Key_9)
        return (keypad ? "KP_" : "") + String.fromCharCode(key)

    var named = {}
    named[Qt.Key_Tab] = "Tab"
    named[Qt.Key_Backtab] = "Tab"
    named[Qt.Key_Backspace] = "BackSpace"
    named[Qt.Key_Return] = "Return"
    named[Qt.Key_Enter] = "KP_Enter"
    named[Qt.Key_Insert] = "Insert"
    named[Qt.Key_Delete] = "Delete"
    named[Qt.Key_Pause] = "Pause"
    named[Qt.Key_Print] = "Print"
    named[Qt.Key_SysReq] = "Sys_Req"
    named[Qt.Key_Home] = "Home"
    named[Qt.Key_End] = "End"
    named[Qt.Key_Left] = "Left"
    named[Qt.Key_Up] = "Up"
    named[Qt.Key_Right] = "Right"
    named[Qt.Key_Down] = "Down"
    named[Qt.Key_PageUp] = "Prior"
    named[Qt.Key_PageDown] = "Next"
    named[Qt.Key_ScrollLock] = "Scroll_Lock"
    named[Qt.Key_Menu] = "Menu"
    named[Qt.Key_VolumeDown] = "XF86AudioLowerVolume"
    named[Qt.Key_VolumeUp] = "XF86AudioRaiseVolume"
    named[Qt.Key_VolumeMute] = "XF86AudioMute"
    named[Qt.Key_MediaPlay] = "XF86AudioPlay"
    named[Qt.Key_MediaPause] = "XF86AudioPause"
    named[Qt.Key_MediaStop] = "XF86AudioStop"
    named[Qt.Key_MediaPrevious] = "XF86AudioPrev"
    named[Qt.Key_MediaNext] = "XF86AudioNext"
    named[Qt.Key_MonBrightnessUp] = "XF86MonBrightnessUp"
    named[Qt.Key_MonBrightnessDown] = "XF86MonBrightnessDown"
    if (named[key]) return named[key]

    // XKB provides a Uxxxx name for Unicode symbols, including punctuation.
    // Qt's unmodified key value avoids accidentally binding a shifted glyph.
    if (key >= 0x20 && key <= 0x10ffff) {
        if (key === Qt.Key_Space) return "space"
        if (keypad) {
            var operators = { 42: "KP_Multiply", 43: "KP_Add", 44: "KP_Separator",
                              45: "KP_Subtract", 46: "KP_Decimal", 47: "KP_Divide" }
            if (operators[key]) return operators[key]
        }
        var punctuation = { 33: "exclam", 34: "quotedbl", 35: "numbersign",
                            36: "dollar", 37: "percent", 38: "ampersand", 39: "apostrophe",
                            40: "parenleft", 41: "parenright", 42: "asterisk", 43: "plus",
                            44: "comma", 45: "minus", 46: "period", 47: "slash",
                            58: "colon", 59: "semicolon", 60: "less", 61: "equal",
                            62: "greater", 63: "question", 64: "at", 91: "bracketleft",
                            92: "backslash", 93: "bracketright", 94: "asciicircum",
                            95: "underscore", 96: "grave", 123: "braceleft", 124: "bar",
                            125: "braceright", 126: "asciitilde" }
        if (punctuation[key]) return punctuation[key]
        var hex = key.toString(16).toUpperCase()
        while (hex.length < 4) hex = "0" + hex
        return "U" + hex
    }
    return ""
}

function isModifier(key) {
    return key === Qt.Key_Shift || key === Qt.Key_Control || key === Qt.Key_Alt
        || key === Qt.Key_Meta || key === Qt.Key_AltGr
        || key === Qt.Key_CapsLock || key === Qt.Key_NumLock
}
