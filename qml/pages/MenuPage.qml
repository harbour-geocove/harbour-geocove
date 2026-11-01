import QtQuick 2.0
import Sailfish.Silica 1.0
import "../components"

Page {
    id: page
    allowedOrientations: Orientation.All

    SilicaListView {
        anchors.fill: parent

        header: PageHeader { title: qsTr("GeoCove") }

        model: [
            { title: qsTr("Map filter"), page: "MapFilterPage.qml", args: {} },
            { title: qsTr("Nearby"), page: "CacheListPage.qml", args: { mode: "nearby", title: qsTr("Nearby") } },
            { title: qsTr("Search caches"), page: "CacheListPage.qml", args: { mode: "search", title: qsTr("Search"), searchKind: 0 } },
            { title: qsTr("Find a place on the map"), page: "CacheListPage.qml", args: { mode: "search", title: qsTr("Find place"), searchKind: 1 } },
            { title: qsTr("My lists"), page: "ListsPage.qml", args: {} },
            { title: qsTr("Import GPX (Pocket Query)"), page: "ImportPage.qml", args: {} },
            { title: qsTr("Offline logs"), page: "OfflineLogsPage.qml", args: {} },
            { title: qsTr("geocaching.com account"), page: "LoginPage.qml", args: {} },
            { title: qsTr("Settings"), page: "SettingsPage.qml", args: {} },
            { title: qsTr("About"), page: "AboutPage.qml", args: {} }
        ]

        delegate: BackgroundItem {
            width: ListView.view.width
            onClicked: pageStack.push(Qt.resolvedUrl(modelData.page), modelData.args)

            Label {
                anchors {
                    left: parent.left; right: parent.right; leftMargin: Theme.horizontalPageMargin
                    rightMargin: Theme.horizontalPageMargin; verticalCenter: parent.verticalCenter
                }
                text: modelData.title
                color: highlighted ? Theme.highlightColor : Theme.primaryColor
                truncationMode: TruncationMode.Fade
            }
        }

        VerticalScrollDecorator {}
    }
}
