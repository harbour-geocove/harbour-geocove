# NOTICE:
#
# Application name defined in TARGET has a corresponding QML filename.
# If name defined in TARGET is changed, the following needs to be done
# to match new name:
#   - corresponding QML filename must be changed
#   - desktop icon filename must be changed
#   - desktop filename must be changed
#   - icon definition filename in desktop file must be changed
#   - translation filenames have to be changed

# The name of your application
TARGET = harbour-geocove

CONFIG += sailfishapp_qml

DISTFILES += \
    qml/harbour-geocove.qml \
    qml/cover/CoverPage.qml \
    qml/components/qmldir \
    qml/components/*.qml \
    qml/components/Util.js \
    qml/pages/*.qml \
    qml/maps/*.qml \
    rpm/harbour-geocove.changes.in \
    rpm/harbour-geocove.changes.run.in \
    rpm/harbour-geocove.spec \
    translations/*.ts \
    harbour-geocove.desktop
 
# Python backend, installed next to the QML (qml/components/Backend.qml adds ../../python)
python.files = python/gcconnector
python.path = /usr/share/$${TARGET}/python
INSTALLS += python

SAILFISHAPP_ICONS = 86x86 108x108 128x128 172x172

# to disable building translations every time, comment out the
# following CONFIG line
CONFIG += sailfishapp_i18n

# German translation is enabled as an example. If you aren't
# planning to localize your app, remember to comment out the
# following TRANSLATIONS line. And also do not forget to
# modify the localized app name in the the .desktop file.
#TRANSLATIONS += translations/harbour-geocove-cs.ts
