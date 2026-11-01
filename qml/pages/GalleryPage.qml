import QtQuick 2.2
import Sailfish.Silica 1.0
import "../components"
import "../components/Util.js" as Util

// Pictures of a cache. mode "web": the gallery of geocaching.com is loaded here instead of opening the browser;
// mode "list": the given `images` ({url, title, description}) are shown (e.g. the listing images).
Page {
    id: page
    allowedOrientations: Orientation.All

    property string geocode
    property string mode: "list"
    property var images: []
    property bool loading: false
    property string errorText: ""
    property string debugText: ""        // what was downloaded (shown when no image was found)

    function load() {
        errorText = ""
        loading = true
        Backend.call("load_gallery", [geocode])
    }

    Component.onCompleted: if (mode === "web") load()

    Connections {
        target: Backend
        onGalleryLoaded: {
            if (result.geocode !== page.geocode) return
            page.loading = false
            if (result.error === "unknown_guid")
                page.errorText = qsTr("Download the cache from geocaching.com first.")
            else if (result.error)
                page.errorText = Util.statusText(result.error) + (result.detail ? " [" + result.detail + "]" : "")
            else {
                page.images = result.images
                page.debugText = result.debug || ""
            }
        }
        onErrorOccurred: if (event === "gallery") {
            page.loading = false
            page.errorText = message
        }
    }

    SilicaListView {
        id: view
        anchors.fill: parent
        model: page.images

        header: PageHeader {
            title: qsTr("Images")
            description: qsTr("%1 images").arg(page.images.length)
        }

        PullDownMenu {
            visible: page.mode === "web"
            MenuItem {
                text: qsTr("Reload")
                onClicked: page.load()
            }
        }

        delegate: BackgroundItem {
            id: item
            width: view.width
            height: picture.height + captions.height + 2 * Theme.paddingMedium
            onClicked: pageStack.push(Qt.resolvedUrl("ImageViewPage.qml"),
                                      { url: modelData.url, title: modelData.title })

            Image {
                id: picture
                x: Theme.horizontalPageMargin
                y: Theme.paddingSmall
                width: item.width - 2 * Theme.horizontalPageMargin
                // the decoded size is limited, large photos would eat the memory of the phone
                sourceSize.width: 1024
                height: status === Image.Ready ? paintedHeight : Theme.itemSizeHuge
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                source: modelData.url

                BusyIndicator {
                    anchors.centerIn: parent
                    size: BusyIndicatorSize.Medium
                    running: picture.status === Image.Loading
                }
                Label {
                    anchors.centerIn: parent
                    visible: picture.status === Image.Error
                    text: qsTr("The image cannot be loaded")
                    color: Theme.secondaryColor
                    font.pixelSize: Theme.fontSizeSmall
                }
            }

            Column {
                id: captions
                anchors { left: picture.left; right: picture.right; top: picture.bottom; topMargin: Theme.paddingSmall }

                Label {
                    visible: text !== ""
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: Util.stripHtml(modelData.title)
                    font.pixelSize: Theme.fontSizeSmall
                    color: item.highlighted ? Theme.highlightColor : Theme.primaryColor
                }
                Label {
                    visible: text !== ""
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: Util.stripHtml(modelData.description)
                    font.pixelSize: Theme.fontSizeExtraSmall
                    color: Theme.secondaryColor
                }
            }
        }

        footer: Item {
            width: view.width
            height: page.debugText !== "" ? footerLabel.height + 2 * Theme.paddingLarge : 0
            Label {
                id: footerLabel
                visible: page.debugText !== ""
                x: Theme.horizontalPageMargin
                y: Theme.paddingLarge
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.WrapAnywhere
                font.pixelSize: Theme.fontSizeTiny
                color: Theme.secondaryColor
                text: page.debugText
            }
        }

        ViewPlaceholder {
            enabled: !page.loading && page.images.length === 0
            text: page.errorText !== "" ? page.errorText : qsTr("No images found.")
            hintText: page.debugText
        }

        VerticalScrollDecorator {}
    }

    BusyIndicator {
        anchors.centerIn: parent
        size: BusyIndicatorSize.Large
        running: page.loading
    }
}
