import QtQuick 2.2
import Sailfish.Silica 1.0
import "../components"

Page {
    id: page
    allowedOrientations: Orientation.All

    property var lists: []

    function reload() {
        Backend.call("get_lists", [], function(r) { page.lists = r })
    }

    function createList() {
        var dialog = pageStack.push(Qt.resolvedUrl("../components/TextInputDialog.qml"),
                                    { placeholder: qsTr("List name") })
        dialog.accepted.connect(function() {
            Backend.call("create_list", [dialog.value.trim()], function() { page.reload() })
        })
    }

    Component.onCompleted: reload()

    Connections {
        target: Backend
        onDataVersionChanged: page.reload()
    }

    SilicaListView {
        id: view
        anchors.fill: parent
        model: page.lists

        header: PageHeader { title: qsTr("My lists") }

        PullDownMenu {
            MenuItem {
                text: qsTr("New list")
                onClicked: page.createList()
            }
        }

        delegate: ListItem {
            id: item
            width: view.width
            contentHeight: Theme.itemSizeMedium

            menu: ContextMenu {
                MenuItem {
                    text: qsTr("Rename")
                    onClicked: {
                        var dialog = pageStack.push(Qt.resolvedUrl("../components/TextInputDialog.qml"),
                                                    { placeholder: qsTr("List name"), value: modelData.name })
                        dialog.accepted.connect(function() {
                            Backend.call("rename_list", [modelData.id, dialog.value.trim()], function() { page.reload() })
                        })
                    }
                }
                MenuItem {
                    text: qsTr("Delete list (keep the caches)")
                    onClicked: item.remorseAction(qsTr("Deleting list"), function() {
                        Backend.call("delete_list", [modelData.id, false], function() { page.reload() })
                    })
                }
                MenuItem {
                    text: qsTr("Delete list and caches")
                    onClicked: item.remorseAction(qsTr("Deleting list and caches"), function() {
                        Backend.call("delete_list", [modelData.id, true], function() { Backend.dataVersion++ })
                    })
                }
            }

            onClicked: pageStack.push(Qt.resolvedUrl("CacheListPage.qml"),
                                      { mode: "list", listId: modelData.id, title: modelData.name })

            Label {
                anchors {
                    left: parent.left; leftMargin: Theme.horizontalPageMargin
                    right: countLabel.left; rightMargin: Theme.paddingMedium
                    verticalCenter: parent.verticalCenter
                }
                text: modelData.name
                color: item.highlighted ? Theme.highlightColor : Theme.primaryColor
                truncationMode: TruncationMode.Fade
            }
            Label {
                id: countLabel
                anchors { right: parent.right; rightMargin: Theme.horizontalPageMargin; verticalCenter: parent.verticalCenter }
                text: modelData.count
                color: Theme.highlightColor
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
