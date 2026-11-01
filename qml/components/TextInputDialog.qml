import QtQuick 2.0
import Sailfish.Silica 1.0

Dialog {
    id: dialog

    property string placeholder
    property alias value: field.text

    canAccept: field.text.trim().length > 0

    Column {
        width: parent.width

        DialogHeader { acceptText: qsTr("Save") }

        TextField {
            id: field
            width: parent.width
            label: dialog.placeholder
            placeholderText: dialog.placeholder
            focus: true
            EnterKey.iconSource: "image://theme/icon-m-enter-accept"
            EnterKey.onClicked: dialog.accept()
        }
    }
}
