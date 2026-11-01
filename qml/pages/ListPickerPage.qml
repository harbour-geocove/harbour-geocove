import QtQuick 2.2
import Sailfish.Silica 1.0
import "../components"

// Pick a list; emits picked(listId) and closes.
Page {
    id: page
    allowedOrientations: Orientation.All

    signal picked(int listId)

    property var lists: []

    function reload() {
        Backend.call("get_lists", [], function(r) { page.lists = r })
    }

    Component.onCompleted: reload()

    SilicaListView {
        id: view
        anchors.fill: parent
        model: page.lists

        header: PageHeader { title: qsTr("Choose a list") }

        PullDownMenu {
            MenuItem {
                text: qsTr("New list")
                onClicked: {
                    var dialog = pageStack.push(Qt.resolvedUrl("../components/TextInputDialog.qml"),
                                                { placeholder: qsTr("List name") })
                    dialog.accepted.connect(function() {
                        Backend.call("create_list", [dialog.value.trim()], function() { page.reload() })
                    })
                }
            }
        }

        delegate: BackgroundItem {
            width: view.width
            onClicked: {
                page.picked(modelData.id)
                pageStack.pop()
            }
            Label {
                anchors {
                    left: parent.left; right: parent.right; leftMargin: Theme.horizontalPageMargin
                    rightMargin: Theme.horizontalPageMargin; verticalCenter: parent.verticalCenter
                }
                text: modelData.name + " (" + modelData.count + ")"
                color: highlighted ? Theme.highlightColor : Theme.primaryColor
                truncationMode: TruncationMode.Fade
            }
        }

        ViewPlaceholder {
            enabled: page.lists.length === 0
            text: qsTr("No lists")
            hintText: qsTr("Pull down the menu to create a list")
        }

        VerticalScrollDecorator {}
    }
}
