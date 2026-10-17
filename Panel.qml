import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Ui
import "KeyCapture.js" as Capture

Panel {
    id: root
    moduleName: "yaqyn.counter"
    manageIpc: false

    property var anchorItem: null
    property var hostWidget: null
    property string appliedKey: ""
    property string selectedKey: ""
    property bool capturing: false
    onOpenedChanged: if (!opened)
        capturing = false
    property string message: ""
    property bool failed: false
    readonly property bool busy: operation.running || readKey.running
    readonly property bool hasCount: hostWidget && /^[0-9]+$/.test(hostWidget.count) && Number(hostWidget.count) > 0
    readonly property string executable: decodeURIComponent(Qt.resolvedUrl("counter.py").toString().slice(7))

    function open() {
        capturing = false;
        message = "";
        failed = false;
        if (!readKey.running && !operation.running)
            readKey.running = true;
        controller.show();
    }

    function execute(action, key) {
        if (busy)
            return;
        message = "";
        failed = false;
        operation.command = key === undefined ? ["python3", executable, action] : ["python3", executable, action, key];
        operation.running = true;
    }

    function applyKey() {
        if (!capturing && selectedKey !== "" && selectedKey !== appliedKey)
            execute("set-key", selectedKey);
    }

    function beginCapture() {
        if (busy)
            return;
        message = "";
        failed = false;
        chooser.forceActiveFocus();
        // Start after the activation event, so Enter/Space is not captured itself.
        Qt.callLater(function () {
            if (root.opened && !root.busy)
                root.capturing = true;
        });
    }

    function captureKey(event) {
        if (!capturing)
            return;
        event.accepted = true;
        if (event.isAutoRepeat)
            return;
        if (event.key === Qt.Key_Escape) {
            capturing = false;
            message = "";
            return;
        }
        if (Capture.isModifier(event.key)) {
            message = "Press a key other than Shift, Ctrl, Alt or a lock modifier.";
            return;
        }
        if (!inhibitor.active) {
            failed = true;
            message = "Key capture is unavailable. Close the panel and try again.";
            capturing = false;
            return;
        }
        var name = Capture.keyName(event.key, (event.modifiers & Qt.KeypadModifier) !== 0);
        if (name === "") {
            failed = true;
            message = "That key is not supported. Press another key, or Esc to cancel.";
            return;
        }
        selectedKey = name;
        capturing = false;
        message = "";
        failed = false;
    }

    ShortcutInhibitor {
        id: inhibitor
        window: popup
        enabled: root.opened && root.capturing
        onCancelled: {
            root.capturing = false;
            root.failed = true;
            root.message = "Key selection cancelled. Click the key to try again.";
        }
    }

    Process {
        id: readKey
        command: ["python3", root.executable, "key"]
        property string output: ""
        property string error: ""
        onStarted: {
            output = "";
            error = "";
        }
        stdout: StdioCollector {
            onStreamFinished: readKey.output = text.trim()
        }
        stderr: StdioCollector {
            onStreamFinished: readKey.error = text.trim()
        }
        onExited: function (code, status) {
            if (code === 0 && output !== "") {
                root.appliedKey = output;
                root.selectedKey = output;
            } else {
                root.failed = true;
                root.message = error || "Could not read the counting key. Reopen to retry.";
            }
        }
    }

    Process {
        id: operation
        property string error: ""
        onStarted: error = ""
        stderr: StdioCollector {
            onStreamFinished: operation.error = text.trim()
        }
        onExited: function (code, status) {
            root.failed = code !== 0;
            if (code !== 0) {
                root.message = error || "Could not complete the change. Try again.";
            } else if (command[2] === "set-key") {
                root.message = "Key saved";
                readKey.running = true;
            } else {
                root.message = command[2] === "reset" ? "Count reset" : "One count removed";
            }
        }
    }

    KeyboardPanel {
        id: popup
        anchorItem: root.anchorItem
        owner: root.hostWidget || root
        bar: root.bar
        open: root.opened
        focusTarget: body
        contentWidth: popup.fittedContentWidth(Style.space(300))
        contentHeight: popup.fittedContentHeight(content.implicitHeight)

        Item {
            id: body
            anchors.fill: parent
            Keys.onEscapePressed: root.close()

            Column {
                id: content
                width: parent.width
                spacing: Style.space(12)

                Text {
                    text: "Counter"
                    textFormat: Text.PlainText
                    color: Color.foreground
                    font.family: Style.font.family
                    font.pixelSize: Style.font.body
                }
                Text {
                    width: parent.width
                    height: Style.space(56)
                    text: root.hostWidget ? root.hostWidget.count : "—"
                    textFormat: Text.PlainText
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    fontSizeMode: Text.Fit
                    minimumPixelSize: Style.font.body
                    color: Color.foreground
                    font.family: Style.font.family
                    font.pixelSize: Style.font.body * 3
                    Accessible.name: "Count: " + text
                }
                Row {
                    width: parent.width
                    spacing: Style.space(8)
                    Button {
                        text: "Reset"
                        width: (parent.width - parent.spacing) / 2
                        focusable: true
                        bordered: true
                        enabled: !root.busy && !root.capturing && (root.hasCount || (root.hostWidget && root.hostWidget.count === "—"))
                        onClicked: root.execute("reset")
                    }
                    Button {
                        text: "Undo"
                        width: (parent.width - parent.spacing) / 2
                        focusable: true
                        bordered: true
                        enabled: !root.busy && !root.capturing && root.hasCount
                        onClicked: root.execute("undo")
                    }
                }
                Text {
                    text: "Counting key"
                    textFormat: Text.PlainText
                    color: Color.foreground
                    font.family: Style.font.family
                    font.pixelSize: Style.font.body
                }
                Row {
                    width: parent.width
                    spacing: Style.space(8)
                    Button {
                        id: chooser
                        width: parent.width - apply.implicitWidth - parent.spacing
                        text: root.capturing ? "Press a key…" : (root.selectedKey || "Choose key")
                        focusable: true
                        bordered: true
                        selected: root.capturing
                        enabled: !root.busy
                        Accessible.name: root.capturing ? "Press the counting key. Escape cancels." : "Choose counting key: " + root.selectedKey
                        onClicked: root.capturing ? root.capturing = false : root.beginCapture()
                        Keys.priority: Keys.BeforeItem
                        Keys.onPressed: function (event) {
                            if (root.capturing)
                                root.captureKey(event);
                            else
                                event.accepted = false;
                        }
                        Keys.onReturnPressed: function (event) {
                            if (root.capturing)
                                root.captureKey(event);
                            else if (!event.isAutoRepeat)
                                root.beginCapture();
                            event.accepted = true;
                        }
                        Keys.onEnterPressed: function (event) {
                            if (root.capturing)
                                root.captureKey(event);
                            else if (!event.isAutoRepeat)
                                root.beginCapture();
                            event.accepted = true;
                        }
                        Keys.onSpacePressed: function (event) {
                            if (root.capturing)
                                root.captureKey(event);
                            else if (!event.isAutoRepeat)
                                root.beginCapture();
                            event.accepted = true;
                        }
                        Keys.onReleased: function (event) {
                            if (root.capturing)
                                event.accepted = true;
                        }
                    }
                    Button {
                        id: apply
                        text: "Apply"
                        focusable: true
                        bordered: true
                        enabled: !root.busy && !root.capturing && root.selectedKey !== "" && root.selectedKey !== root.appliedKey
                        onClicked: root.applyKey()
                    }
                }
                Text {
                    width: parent.width
                    text: "Current key: " + (root.appliedKey || "—") + "\nReserved for counting, even with Shift, Ctrl or Alt."
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: Color.foreground
                    opacity: 0.72
                    font.family: Style.font.family
                    font.pixelSize: Style.font.body
                }
                Text {
                    width: parent.width
                    height: Style.space(52)
                    text: operation.running ? "Saving…" : (readKey.running ? "Loading…" : (root.message || (root.hostWidget && root.hostWidget.serviceError) || (root.capturing ? "Press one key. Esc to cancel." : "")))
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    elide: Text.ElideRight
                    maximumLineCount: 3
                    color: root.failed ? Color.urgent : Color.foreground
                    font.family: Style.font.family
                    font.pixelSize: Style.font.body
                    Accessible.name: text
                }
            }
        }
    }
}
