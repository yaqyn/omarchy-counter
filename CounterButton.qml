import QtQuick
import qs.Commons
import qs.Ui

// Extend the native shell primitive with Qt accessibility semantics.
Button {
    id: root
    clip: true
    focusable: true
    bordered: true
    height: Math.max(implicitHeight, Style.space(32))
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.focusable: true
    Accessible.onPressAction: if (enabled) clicked()
}
