import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
    id: root
    moduleName: "qv.azkar"
    property string count: "—"
    property string serviceError: ""
    FileView {
        id: health
        path: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/azkar/service.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try {
                root.serviceError = JSON.parse(text()).error || "";
            } catch (error) {
                root.serviceError = "Could not read counter status.";
            }
        }
        onLoadFailed: root.serviceError = "Counter service is starting or unavailable."
    }
    implicitWidth: label.implicitWidth
    implicitHeight: root.barSize
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
        id: counter
        path: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/azkar/count"
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
        text: root.count
        interactive: true
        pressable: true
        fixedWidth: Math.max(Style.space(44), label.labelWidth + Style.spaceReal(17.5))
        horizontalMargin: 8.75
        verticalPadding: 8.75
        tooltipText: root.count === "—" ? "Counter unavailable · click to reset" : "Counter · " + root.count + " · click for controls"
        onPressed: function (button) {
            if (button === Qt.LeftButton)
                root.toggle();
        }
        Accessible.name: "Azkar counter: " + root.count
    }
}
