import QtQuick 2.2
import Sailfish.Silica 1.0
import Sailfish.WebView 1.0
import "../components"
import "../components/Util.js" as Util

// Login on the real geocaching.com page (captcha works there). When the sign-in page is left,
// or when the user taps "Finish login", the session cookie is taken over by the Python side.
Page {
    id: page
    allowedOrientations: Orientation.All

    property bool sawSignIn: false
    property bool finishing: false
    property var navLog: []              // pages visited (without query strings), newest last
    property string pageMessages: ""
    property bool showInfo: false

    // what the page itself says: form errors, captcha presence, cookie support (no values, no passwords)
    readonly property string inspectScript:
        "(function(){var r=[];var q=document.querySelectorAll('.validation-summary-errors,.field-validation-error,.alert,[role=alert]');" +
        "for(var i=0;i<q.length;i++){var t=(q[i].innerText||'').trim();if(t)r.push('message: '+t.substring(0,200));}" +
        "r.push('cookieEnabled='+navigator.cookieEnabled);r.push('document.cookie chars='+document.cookie.length);" +
        "r.push('recaptcha elements='+document.querySelectorAll('iframe[src*=recaptcha],.g-recaptcha').length);" +
        "var f=document.querySelectorAll('form'),n=[];for(i=0;i<f.length;i++){var e=f[i].elements;for(var j=0;j<e.length;j++)if(e[j].name)n.push(e[j].name);}" +
        "r.push('fields='+n.join(','));r.push('UA='+navigator.userAgent);return r.join('\\n');})()"

    function readPage() {
        pageMessages = qsTr("Reading…")
        readTimeout.restart()
        try {
            webView.runJavaScript(inspectScript, function(result) {
                readTimeout.stop()
                page.pageMessages = result ? String(result) : qsTr("(nothing found)")
            })
        } catch (e) {
            readTimeout.stop()
            pageMessages = "runJavaScript: " + e
        }
    }

    function pageInfo() {
        return webView.url.toString().split("?")[0]
    }

    function finish() {
        if (finishing) return
        finishing = true
        autoFinish.stop()
        fallback.start()          // started first: continues without document.cookie if the page never answers
        try {
            // document.cookie does not contain HttpOnly cookies; the Python side then reads the profile
            webView.runJavaScript("document.cookie", function(cookies) {
                if (!fallback.running) return
                fallback.stop()
                Backend.webviewLogin(cookies || "", "runJavaScript answered with " + (cookies || "").length +
                                     " chars; page " + page.pageInfo())
            })
        } catch (e) {
            console.log("runJavaScript not available: " + e)
            fallback.stop()
            Backend.webviewLogin("", "runJavaScript not available (" + e + "); page " + page.pageInfo())
        }
    }

    Connections {
        target: Backend
        onLoginFinished: {
            page.finishing = false
            if (result.ok) {
                pageStack.pop()
            } else {
                banner.show(Util.statusText(result.status) + " " + qsTr("Details are on the account page."))
                pageStack.pop()
            }
        }
    }

    WebView {
        id: webView
        anchors { top: parent.top; left: parent.left; right: parent.right; bottom: buttons.top }
        url: "https://www.geocaching.com/account/signin"

        onUrlChanged: {
            var u = url.toString()
            page.navLog = page.navLog.concat([u.split("?")[0]]).slice(-8)
            if (u.indexOf("/account/signin") >= 0) {
                page.sawSignIn = true
                autoFinish.stop()
            } else if (page.sawSignIn && u.indexOf("geocaching.com") >= 0) {
                autoFinish.restart()     // signed in: give the browser a moment to store the cookies
            }
        }
    }

    Rectangle {
        id: infoPanel
        visible: page.showInfo
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: Math.min(page.height * 0.55, infoColumn.height + 2 * Theme.paddingMedium)
        color: Theme.rgba(Theme.overlayBackgroundColor, 0.95)
        clip: true

        Column {
            id: infoColumn
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.paddingMedium }
            spacing: Theme.paddingSmall

            Label {
                width: parent.width
                wrapMode: Text.WrapAnywhere
                font.pixelSize: Theme.fontSizeTiny
                text: "page: " + page.pageInfo() + "\ntitle: " + webView.title + "\nloading: " + webView.loading +
                      "\nvisited:\n" + page.navLog.join("\n")
            }
            Button {
                text: qsTr("Read page messages")
                onClicked: page.readPage()
            }
            Label {
                visible: page.pageMessages !== ""
                width: parent.width
                wrapMode: Text.WrapAnywhere
                font.pixelSize: Theme.fontSizeTiny
                color: Theme.highlightColor
                text: page.pageMessages
            }
        }
    }

    Timer {
        id: readTimeout
        interval: 4000
        onTriggered: page.pageMessages = qsTr("No answer from the page (runJavaScript does not work here).")
    }

    Rectangle {
        id: buttons
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: Theme.itemSizeLarge
        color: Theme.rgba(Theme.overlayBackgroundColor, 0.95)

        Row {
            anchors.centerIn: parent
            spacing: Theme.paddingLarge

            Button {
                text: qsTr("Info")
                onClicked: page.showInfo = !page.showInfo
            }
            Button {
                text: qsTr("Finish login")
                enabled: !page.finishing
                onClicked: page.finish()
            }
        }
    }

    Timer {
        id: autoFinish
        interval: 3000
        onTriggered: page.finish()
    }

    // if the web view never answers runJavaScript, continue without document.cookie
    Timer {
        id: fallback
        interval: 4000
        onTriggered: Backend.webviewLogin("", "runJavaScript gave no answer; page " + page.pageInfo())
    }

    BusyBar {
        bottomOffset: Theme.itemSizeLarge + Theme.paddingLarge
        running: Backend.busy
        text: Backend.busyText
    }

    StatusBanner { id: banner }
}
