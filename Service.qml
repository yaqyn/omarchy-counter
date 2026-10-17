import QtQuick
import Quickshell
import Quickshell.Io

Item {
    id: root
    function newToken() {
        return (Date.now().toString(16) + Math.random().toString(16).slice(2) + "00000000000000000000000000000000").slice(0, 32);
    }
    property bool stopping: false
    property string ownerToken: newToken()
    // Teardown must survive removal of this directory and Quickshell killing the helper.
    Component.onDestruction: {
        stopping = true;
        Quickshell.execDetached(["hyprctl", "eval", "local token = " + JSON.stringify(root.ownerToken) + "; " + "_G.yaqyn_counter_cancelled = _G.yaqyn_counter_cancelled or {}; _G.yaqyn_counter_cancelled[token] = true; " + "local v = _G.yaqyn_counter; if v and v.token == token then " + "pcall(function() v.binding:remove() end); _G.yaqyn_counter = nil end"]);
    }
    readonly property string backend: decodeURIComponent(Qt.resolvedUrl("counter.py").toString().slice(7))
    property int failures: 0
    Timer {
        id: retry
        interval: 1000
        onTriggered: worker.running = true
    }
    Process {
        id: worker
        command: ["python3", root.backend, "serve", root.ownerToken]
        stdinEnabled: true
        running: true
        onExited: function (code, status) {
            if (root.stopping)
                return;
            if (code !== 0 && root.failures++ < 3) {
                root.ownerToken = root.newToken();
                retry.restart();
            } else if (code !== 0)
                console.warn("Counter service stopped; check python3, libxkbcommon and Hyprland Lua support.");
        }
    }
}
