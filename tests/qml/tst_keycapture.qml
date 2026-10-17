import QtQuick
import QtTest
import "../../KeyCapture.js" as Capture

TestCase {
    name: "KeyCapture"
    function test_functionKeys() {
        compare(Capture.keyName(Qt.Key_F1, false), "F1");
        compare(Capture.keyName(Qt.Key_F8, false), "F8");
        compare(Capture.keyName(Qt.Key_F35, false), "F35");
    }
    function test_printableAndKeypad() {
        compare(Capture.keyName(Qt.Key_A, false), "a");
        compare(Capture.keyName(Qt.Key_9, false), "9");
        compare(Capture.keyName(Qt.Key_9, true), "KP_9");
        compare(Capture.keyName(Qt.Key_Period, false), "period");
        compare(Capture.keyName(Qt.Key_Period, true), "KP_Decimal");
        compare(Capture.keyName(Qt.Key_Space, false), "space");
    }
    function test_navigationAndMedia() {
        compare(Capture.keyName(Qt.Key_PageDown, false), "Next");
        compare(Capture.keyName(Qt.Key_Enter, true), "KP_Enter");
        compare(Capture.keyName(Qt.Key_Pause, false), "Pause");
        compare(Capture.keyName(Qt.Key_VolumeUp, false), "XF86AudioRaiseVolume");
    }
    function test_modifiers() {
        verify(Capture.isModifier(Qt.Key_Shift));
        verify(Capture.isModifier(Qt.Key_Control));
        verify(Capture.isModifier(Qt.Key_Alt));
        verify(Capture.isModifier(Qt.Key_AltGr));
        verify(Capture.isModifier(Qt.Key_NumLock));
        verify(!Capture.isModifier(Qt.Key_F1));
    }
    function test_escapeIsReservedForCancellation() {
        compare(Capture.keyName(Qt.Key_Escape, false), "");
    }
    function test_nonLatinLayout() {
        compare(Capture.keyName(0x0636, false), "U0636");
        compare(Capture.keyName(0x00E9, false), "U00E9");
    }
}
