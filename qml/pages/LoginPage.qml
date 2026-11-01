import QtQuick 2.0
import Sailfish.Silica 1.0
import "../components"

Page {
    id: page
    allowedOrientations: Orientation.All

    function openWebLogin() {
        var component = Qt.createComponent(Qt.resolvedUrl("LoginWebPage.qml"))
        if (component.status === Component.Ready) {
            pageStack.push(component)
        } else {
            banner.show(qsTr("The web view is not available: %1").arg(component.errorString()))
        }
    }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: column.height + Theme.paddingLarge

        Column {
            id: column
            width: parent.width

            PageHeader { title: qsTr("geocaching.com account") }

            // results of the last attempt first, so they are visible right after tapping a button
            Label {
                visible: Backend.loginMessage !== ""
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                color: Theme.errorColor !== undefined ? Theme.errorColor : "red"
                text: Backend.loginMessage
            }
            TextArea {
                visible: Backend.loginDebug !== "" && !Backend.loggedIn
                width: parent.width
                readOnly: true
                label: qsTr("Diagnostics (contains no password)")
                text: Backend.loginDebug
                font.pixelSize: Theme.fontSizeExtraSmall
            }

            // --- signed in
            Label {
                visible: Backend.loggedIn
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                color: Theme.highlightColor
                text: qsTr("Signed in as %1 %2").arg(Backend.userName).arg(Backend.memberType ? "(" + Backend.memberType + ")" : "")
            }
            Button {
                visible: Backend.loggedIn
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Sign out")
                onClicked: Backend.logout()
            }

            // --- 1. cookie (works reliably)
            SectionHeader {
                visible: !Backend.loggedIn
                text: qsTr("Sign in with a cookie (recommended)")
            }
            Label {
                visible: !Backend.loggedIn
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("Sign in on geocaching.com in a browser on a computer and copy the \"gspkauth\" cookie (Firefox: F12 → Storage → Cookies; Chrome: F12 → Application → Cookies). You can paste only the value or the whole cookie line. Send it to the phone through the clipboard (e.g. KDE Connect) and tap the first button. The session expires after a while; the app then asks for a new cookie.")
            }
            Button {
                visible: !Backend.loggedIn
                anchors.horizontalCenter: parent.horizontalCenter
                enabled: Clipboard.hasText && !Backend.busy
                text: qsTr("Paste from the clipboard and sign in")
                onClicked: Backend.loginWithCookie(Clipboard.text.trim())
            }
            TextField {
                id: cookieField
                visible: !Backend.loggedIn
                width: parent.width
                label: qsTr("Value of the gspkauth cookie")
                placeholderText: label
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText | Qt.ImhSensitiveData
            }
            Button {
                visible: !Backend.loggedIn
                anchors.horizontalCenter: parent.horizontalCenter
                enabled: cookieField.text.length > 10 && !Backend.busy
                text: qsTr("Use cookie")
                onClicked: Backend.loginWithCookie(cookieField.text.trim())
            }

            // --- 2. web view (experimental)
            SectionHeader {
                visible: !Backend.loggedIn
                text: qsTr("Sign in with the web view (experimental)")
            }
            Label {
                visible: !Backend.loggedIn
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("The embedded browser of Sailfish OS 5.0 (Gecko 91) cannot complete the geocaching.com sign-in; newer system versions may. Even then the session cookie often cannot be read back, so the cookie above is the reliable way.")
            }
            Button {
                visible: !Backend.loggedIn
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Sign in with the web view")
                onClicked: page.openWebLogin()
            }
/*
            // --- 3. password
            SectionHeader {
                visible: !Backend.loggedIn
                text: qsTr("Sign in with a password")
            }
            TextField {
                id: userField
                visible: !Backend.loggedIn
                width: parent.width
                label: qsTr("Username or e-mail")
                placeholderText: label
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
                EnterKey.iconSource: "image://theme/icon-m-enter-next"
                EnterKey.onClicked: passField.focus = true
            }
            PasswordField {
                id: passField
                visible: !Backend.loggedIn
                width: parent.width
                EnterKey.iconSource: "image://theme/icon-m-enter-accept"
                EnterKey.onClicked: loginButton.clicked(null)
            }
            Button {
                id: loginButton
                visible: !Backend.loggedIn
                anchors.horizontalCenter: parent.horizontalCenter
                enabled: userField.text.length > 0 && passField.text.length > 0 && !Backend.busy
                text: qsTr("Sign in")
                onClicked: Backend.login(userField.text.trim(), passField.text)
            }
            Label {
                visible: !Backend.loggedIn
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("Works only when geocaching.com does not ask for a captcha.")
            }*/

            Item { width: 1; height: Theme.paddingLarge }
            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("The password is not stored, only the session (cookie) in dconf. Access through the website is not an official API and may violate the terms of service – use it sparingly and at your own risk. The official and safe way is importing GPX files from Pocket Queries.")
            }
        }

        VerticalScrollDecorator {}
    }

    BusyBar {
        running: Backend.busy
        text: Backend.busyText
    }

    StatusBanner { id: banner }
}
