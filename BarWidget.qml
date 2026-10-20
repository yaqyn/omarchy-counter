import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
    id: root
    moduleName: "yaqyn.counter"
    property string count: "—"
    property string goal: "0"
    readonly property bool goalReached: goal !== "0" && count !== "—" && (count.length > goal.length || (count.length === goal.length && count >= goal))
    property bool countingActive: false
    property string serviceError: ""
    FileView {
        id: health
        path: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/counter/service.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try {
                var data = JSON.parse(text());
                root.serviceError = data.error || "";
                root.countingActive = data.active === true;
            } catch (error) {
                root.countingActive = false;
                root.serviceError = "Could not read counter status.";
            }
        }
        onLoadFailed: {
            root.countingActive = false;
            root.serviceError = "Counter service is starting or unavailable.";
        }
    }
    implicitWidth: root.vertical ? root.barSize : label.implicitWidth
    implicitHeight: root.vertical ? label.implicitHeight : root.barSize
    readonly property bool opened: panel.item ? panel.item.opened : false
    function injectPanel() {
        if (!panel.item)
            return;
        panel.item.bar = root.bar;
        panel.item.anchorItem = label;
        panel.item.hostWidget = root;
    }
    function open() {
        if (panel.item)
            panel.item.open();
    }
    function close() {
        if (panel.item)
            panel.item.close();
    }
    function toggle() {
        opened ? close() : open();
    }
    function closeForPopoutSwitch() {
        if (panel.item)
            panel.item.closeForPopoutSwitch();
    }
    readonly property bool popoutSwitchClosing: panel.item ? panel.item.popoutSwitchClosing : false
    onBarChanged: injectPanel()
    Loader {
        id: panel
        active: true
        source: Qt.resolvedUrl("Panel.qml")
        visible: false
        onLoaded: {
            root.injectPanel();
            Qt.callLater(root.injectPanel);
        }
    }
    FileView {
        path: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/counter/goal"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            var value = text().trim();
            root.goal = /^[0-9]{1,100}$/.test(value) ? (value.replace(/^0+(?=\d)/, "")) : "0";
        }
        onLoadFailed: root.goal = "0"
    }
    FileView {
        id: counter
        path: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/counter/count"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            var value = text().trim();
            root.count = /^[0-9]{1,100}$/.test(value) ? value : "—";
        }
        onLoadFailed: root.count = "—"
    }
    WidgetButton {
        id: label
        anchors.fill: parent
        bar: root.bar
        text: (root.count.length > 12 ? root.count.slice(0, 5) + "…" + root.count.slice(-5) : root.count) + (root.countingActive ? "" : " off")
        interactive: true
        pressable: true
        textRotation: root.vertical ? 270 : 0
        fixedWidth: root.vertical ? root.barSize : Math.max(Style.space(44), label.labelWidth + Style.spaceReal(17.5))
        fixedHeight: root.vertical ? Math.max(root.barSize, label.labelWidth + Style.spaceReal(17.5)) : root.barSize
        horizontalMargin: 8.75
        verticalPadding: 8.75
        tooltipText: root.count === "—" ? "Counter unavailable · click to reset" : "Counter · " + root.count + (root.countingActive ? " · On" : " · Off") + " · click for controls"
        onPressed: function (button) {
            if (button === Qt.LeftButton)
                root.toggle();
        }
        activeFocusOnTab: true
        Keys.onReturnPressed: root.toggle()
        Keys.onSpacePressed: root.toggle()
        Accessible.role: Accessible.Button
        Accessible.focusable: true
        Accessible.name: "Counter: " + root.count + (root.countingActive ? ", on" : ", off")
        Accessible.onPressAction: root.toggle()
        BorderSurface {
            anchors.fill: parent
            visible: label.activeFocus
            color: "transparent"
            borderSpec: Border.controlSpec("focus", label.foreground, Color.accent)
            radius: Style.cornerRadius
        }
    }
}
