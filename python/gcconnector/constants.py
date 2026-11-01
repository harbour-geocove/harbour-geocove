"""Patterns and constants, translated from c:geo's GCConstants.java.

Java string literals were copied verbatim (the escape rules are the same in
Python normal strings). Only Java-specific regex syntax was changed:
  * `[0-9A-Z&&[^ILOSU]]` (class intersection)  -> `[0-9A-HJKMNPQRTV-Z]`
  * `(?>...)` (atomic group, Python < 3.11)     -> `(?:...)`
  * Pattern.quote(x)                            -> re.escape(x)
"""
import re

D = re.DOTALL
I = re.IGNORECASE
M = re.MULTILINE

# Letters allowed in GC codes (A-Z without I, L, O, S, U)
_GCCH = "0-9A-HJKMNPQRTV-Z"

GC_URL = "https://www.geocaching.com/"
URL_LIVE_MAP = GC_URL + "map/default.aspx"
DEFAULT_GC_DATE = "MM/dd/yyyy"
GEOCODE_PATTERN = "(?<!\\w)(GC[" + _GCCH + "]{1,5})(?=$|\\W|\\s|_)"

# --- detailed cache page -----------------------------------------------------

PATTERN_HINT = re.compile("<div id=\"div_hint\"[^>]*>(.*?)</div>", D)
PATTERN_DESC = re.compile("<span [^>]*id=\"ctl00_ContentBody_LongDescription\"[^>]*>(.*?)</span>\\s*</div>\\s*<(p|div) id=\"ctl00_ContentBody", D)
PATTERN_SHORTDESC = re.compile("<span [^>]*id=\"ctl00_ContentBody_ShortDescription\"[^>]*>(.*?)</span>\\s*</div>", D)
PATTERN_GEOCODE = re.compile("class=\"CoordInfoCode\">" + GEOCODE_PATTERN + "</span>")
PATTERN_GUID = re.compile(re.escape("&wid=") + "([0-9a-z\\-]+)" + re.escape("&"))
PATTERN_SIZE = re.compile("/icons/container/([a-z_]+)\\.")
PATTERN_LATLON = re.compile("<span id=\"uxLatLon\"[^>]*>(.*?)</span>")
PATTERN_LATLON_ORIG = re.compile("\\{\"isUserDefined\":true[^}]+?\"oldLatLngDisplay\":\"([^\"]+)\"\\}")
PATTERN_LOCATION = re.compile("<title>.*\\) in (.*?) created by .*</title>")
PATTERN_LOCATION_LOGIN = re.compile("homeLocation:\\s*\\{\\\"Latitude\\\":(-?\\d*\\.\\d*),\\\"Longitude\\\":(-?\\d*\\.\\d*)\\}")
PATTERN_PERSONALNOTE = re.compile("<div id=\"srOnlyCacheNote\"[^>]*>(.*?)</div>", D)
PATTERN_NAME = re.compile("<span id=\"ctl00_ContentBody_CacheName\".*?>(.*?)</span>")
PATTERN_DIFFICULTY = re.compile("<span id=\"ctl00_ContentBody_uxLegendScale\"[^>]*>[^<]*<img src=\"[^\"]*/images/stars/stars([0-9_]+)\\.gif\"")
PATTERN_TERRAIN = re.compile("<span id=\"ctl00_ContentBody_Localize[\\d]+\"[^>]*>[^<]*<img src=\"[^\"]*/images/stars/stars([0-9_]+)\\.gif\"")
PATTERN_OWNER_USERID = re.compile("<a href=\"/play/search\\?owner\\[0\\]=(.*?)&a=")
PATTERN_OWNER_GUID = re.compile("\\/p(rofile)?\\/\\?guid=([0-9a-z\\-]+)&")

# LogType ids (c:geo LogType): FOUND_IT=2, DIDNT_FIND_IT=3, ATTENDED=10, WEBCAM_PHOTO_TAKEN=11
# !! verify against LogType.java (foundLogTypes()) !!
FOUND_LOG_TYPE_IDS = ("2", "10", "11")
DNF_LOG_TYPE_ID = "3"
PATTERN_FOUND = re.compile("logtypes/48/(" + "|".join(FOUND_LOG_TYPE_IDS) + ").png\" id=\"ctl00_ContentBody_GeoNav_logTypeImage\"")
PATTERN_DNF = re.compile("logtypes/48/(" + DNF_LOG_TYPE_ID + ").png\" id=\"ctl00_ContentBody_GeoNav_logTypeImage\"")

PATTERN_OWNER_DISPLAYNAME = re.compile("<div id=\"ctl00_ContentBody_mcd1\">[^<]+<a href=\"[^\"]+\">([^<]+)</a>")
PATTERN_TYPE = re.compile("<use xlink:href=\"/app/ui-icons/sprites/cache-types.svg#icon-([0-9a-f]+)")
PATTERN_HIDDEN = re.compile("ctl00_ContentBody_mcd2[^:]+:\\s*([^<]+?)<")
PATTERN_HIDDENEVENT = re.compile(":\\s*([0-9-/]+)\\s*<div id=\"calLinks\">", D)
PATTERN_EVENTTIMES = re.compile("<div id=\"mcd3\">\\s*[^<]*?\\s+([APM ]*)([0-9]+)[\\.:]([0-9]+)([APM ]*)\\s*</div>\\s*<div id=\"mcd4\">\\s*[^<]*?\\s+([APM ]*)([0-9]+)[\\.:]([0-9]+)([APM ]*)\\s*</div>")
PATTERN_IS_FAVORITE = re.compile("<div id=\"pnlFavoriteCache\">")
PATTERN_FAVORITECOUNT = re.compile("<span class=\"favorite-value\">\\D*([0-9]+?)\\D*</span>")
PATTERN_COUNTLOGS = re.compile("<span id=\"ctl00_ContentBody_lblFindCounts\"><ul(.+?)</ul></span>")
PATTERN_WATCHLIST_COUNT = re.compile("data-watchcount=\"(\\d+)\"")
PATTERN_GALLERY_COUNT = re.compile("<a href=\"/seek/gallery.aspx\\?guid=[^(]+?\\((\\d+)\\)</a>")
PATTERN_TB_CURRENT_GEOCACHE_JSON = re.compile("\"currentGeocache\":\\{([^}]+)\\}")
PATTERN_COUNTLOG = re.compile("logtypes/([0-9]+)\\.[^>]+>\\s*([0-9,.]+)")
PATTERN_PREMIUMMEMBERS = re.compile("<p class=\"Warning NoBottomSpacing\"")
PATTERN_ATTRIBUTES = re.compile("(<img src=\"/images/attributes.*?)</p")
PATTERN_ATTRIBUTESINSIDE = re.compile("<img src=\"([^\"]+)\" alt=\"([^\"]+?)\"")

IMAGE_FORMATS = "jpg|jpeg|png|gif|bmp|JPG|JPEG|PNG|GIF|BMP"
IMAGE_URL = "<a href=[\"'](https?://img(?:cdn)?\\.geocaching\\.com[^.]+\\.(?:" + IMAGE_FORMATS + "))[\"'][^>]+>(?:[^>]*</strong>[^>]+>)?"
PATTERN_SPOILER_IMAGE = re.compile(IMAGE_URL + "([^<]*)</a>" + ".*?(?:description\"[^>]*>([^<]+)</span>)?</li>", D)
PATTERN_GALLERY_IMAGE = re.compile("<span(?: [^>+]+)>([^>]+)</span>\\s*?" + IMAGE_URL + ".*?<span>([^<]*)</span>", D)
PATTERN_INVENTORY = re.compile("ctl00_ContentBody_uxTravelBugList_uxInventoryLabel\">.*?WidgetBody(.*?)<div")
PATTERN_INVENTORYINSIDE = re.compile("[^<]*<li>[^<]*<a href=\"[a-z0-9\\-\\_\\.\\?\\/\\:\\@]*\\/(?:track|hide)\\/details\\.aspx\\?(guid|TB)=([0-9a-zA-Z\\-]+)[^\"]*\"[^>]*>[^<]*<img src=\"[^\"]+\"[^>]*>[^<]*<span>([^<]+)<\\/span>[^<]*<\\/a>[^<]*<\\/li>")
PATTERN_WATCHLIST = re.compile("data-cacheonwatchlist=\"True\"")
PATTERN_RELATED_WEB_PAGE = re.compile("ctl00_ContentBody_uxCacheUrl.*? href=\"(.*?)\">")
PATTERN_BACKGROUND_IMAGE = re.compile("<body background=\"(.+?)\"")
PATTERN_GC_CHECKER = "ctl00_ContentBody_lblSolutionChecker"  # plain string, used with `in`

# --- user info -----------------------------------------------------------------

PATTERN_LOGIN_NAME1 = re.compile(",\"referenceCode\":\"[^\"]+\",\"id\":[0-9]+,\"username\":\\s*\"(([^\\\\\\\"]*(\\\\[a-z\\\"])*)*)\\\",")
PATTERN_FINDCOUNT = re.compile("\"findCount\":\\s*([0-9]+)[,\\s]")
PATTERN_LOGIN_NAME2 = re.compile("window(?:\\.|\\[')(?:headerSettings|chromeSettings)(?:'\\])?\\s*=\\s*\\{[\\S\\s]*\"username\":\\s*\"([^\"]*)\",?[\\S\\s]*\\}")
PATTERN_CACHES_FOUND = re.compile("window(?:\\.|\\[')(?:headerSettings|chromeSettings)(?:'\\])?\\s*=\\s*\\{[\\S\\s]*\"findCount\":\\s*([0-9]*)[\\S\\s]*\\}")

# --- trackables ----------------------------------------------------------------

PATTERN_TRACKABLE_GUID = re.compile("<a id=\"ctl00_ContentBody_lnkPrint\" aria-labelledby=\"[^\"]*\" href=\".*sheet\\.aspx\\?guid=([a-z0-9\\-]+)\"[^>]*>[^<]*</a>")
PATTERN_TRACKABLE_GEOCODE = re.compile(re.escape("CoordInfoCode\">") + "(TB[" + _GCCH + "]+)<")

ERROR_TB_DOES_NOT_EXIST = "does not exist in the system"
ERROR_TB_ELEMENT_EXCEPTION = "ElementNotFound Exception"
ERROR_TB_ARITHMETIC_OVERFLOW = "operation resulted in an overflow"
ERROR_TB_NOT_ACTIVATED = "hasn't been activated"

PATTERN_TRACKABLE_NAME = re.compile("<span id=\"ctl00_ContentBody_lbHeading\">(.*?)</span>")
PATTERN_TRACKABLE_OWNER = re.compile("<a id=\"ctl00_ContentBody_BugDetails_BugOwner\"[^>]+href=\"https?://www.geocaching.com/p(rofile)?/\\?guid=(.*?)\">(.*?)</a>")
PATTERN_TRACKABLE_RELEASES = re.compile("<span id=\"ctl00_ContentBody_BugDetails_BugReleaseDate\">([^<]+)<\\/span>[^<]*</dd>")
PATTERN_TRACKABLE_FOUND_LOG = re.compile("<img src=\"/images/logtypes/(.*?).png\" id=\"ctl00_ContentBody_InteractionLogTypeImage\"[^>]*>")
PATTERN_TRACKABLE_DISPOSITION_LOG = re.compile("<a id=\"ctl00_ContentBody_InteractionLogLink\"[^>]*href=\"/track/log.aspx\\?LUID=([a-z0-9\\-]+)\">[^0-9]+(.*?)</a>")
PATTERN_TRACKABLE_ORIGIN = re.compile("<span id=\"ctl00_ContentBody_BugDetails_BugOrigin\">([^<]+)<\\/span>[^<]*</dd>")
PATTERN_TRACKABLE_SPOTTEDCACHE_BY_GEOCODE = re.compile("<a id=\"ctl00_ContentBody_BugDetails_BugLocation\" title=\"[^\"]*\" data-name=\"([^\"]+)\" data-status=\"Cache\" href=\"[^\"]*/geocache/(GC[A-Z0-9]+)\">[^<]+</a>")
PATTERN_TRACKABLE_SPOTTEDCACHE_BY_GUID = re.compile("<a id=\"ctl00_ContentBody_BugDetails_BugLocation\" title=\"[^\"]*\" data-name=\"([^\"]+)\" data-status=\"Cache\" href=\"[^\"]*/seek/cache_details.aspx\\?guid=([a-z0-9\\-]+)\">[^<]+</a>")
PATTERN_TRACKABLE_SPOTTEDUSER = re.compile("<a id=\"ctl00_ContentBody_BugDetails_BugLocation\" data-name=\"([^\"]+)\" data-status=\"User\" href=\"[^\"]*/p(rofile)?/\\?guid=([a-z0-9\\-]+)\">")
PATTERN_TRACKABLE_SPOTTEDUNKNOWN = re.compile("<a id=\"ctl00_ContentBody_BugDetails_BugLocation\" data-status=\"Unknown\">[^<]*</a>")
PATTERN_TRACKABLE_SPOTTEDOWNER = re.compile("<a id=\"ctl00_ContentBody_BugDetails_BugLocation\" data-status=\"Owner\">[^<]*</a>")
PATTERN_TRACKABLE_GOAL = re.compile("<div id=\"TrackableGoal\">[^<]*<p>(.*?)</p>[^<]*</div>", D)
PATTERN_TRACKABLE_DETAILSIMAGE = re.compile("<div id=\"TrackableDetails\">([^<]*<p>([^<]*<img id=\"ctl00_ContentBody_BugDetails_BugImage\" class=\"[^\"]+\" src=\"([^\"]+)\"[^>]*>)?[^<]*</p>)?[^<]*<p[^>]*>(.*)</p>[^<]*</div> <div class=\"Clear\">")
PATTERN_TRACKABLE_ICON = re.compile("<img id=\"ctl00_ContentBody_BugTypeImage\" class=\"TravelBugHeaderIcon\" (?:aria-hidden=\"true\" )?src=\"([^\"]+)\"[^>]*>")
PATTERN_TRACKABLE_TYPE = re.compile("<img id=\"ctl00_ContentBody_BugTypeImage\" class=\"TravelBugHeaderIcon\" (?:aria-hidden=\"true\" )?src=\"[^\"]+\" alt=\"([^\"]+)\"[^>]*>")
PATTERN_TRACKABLE_TYPE_TITLE = re.compile("<title>\\s\\(TB[0-9A-Z]*\\) ([^<]*)<\\/title>")
PATTERN_TRACKABLE_DISTANCE = re.compile("\\(([0-9.,]+)(km|mi)[^\\)]*\\)\\s*<a href=\"map_gm")
PATTERN_TRACKABLE_LOG_OUTER = re.compile("<tr class=\"Data BorderTop \\w*\">[\\S\\s]+?(?=</tr>)[\\S\\s]+?(?=<tr)[\\S\\s]+?(?=</tr)")
PATTERN_TRACKABLE_LOG_INNER = re.compile("/images/logtypes/([^.]+)\\.png[^>]+>&nbsp;([^<]+)</th>[\\S\\s]+?(?=\\?guid=)\\?guid=([^\"]+)\">([^<]+)</a>(?:.+?(?=https://www\\.geocaching\\.com/geocache/)https://www\\.geocaching\\.com/geocache/([^\"]+)\">(<span[^>]+>)?([^<]+))?[\\S\\s]+?(?=/live/log)/live/log/([^\"]+)[\\S\\s]+?(?=TrackLogText)[^\"]+\">([\\S\\s]*?(?=</div>))")
PATTERN_TRACKABLE_LOG_IMAGES = re.compile("<ul class=\"log_images\"><li><a href=\"([^\"]+)\".+?(?= alt) alt=\"([^\"]+)\"")
PATTERN_TRACKABLE_IS_LOCKED = re.compile("<a id=\"ctl00_ContentBody_LogLink\"[^(]*\\(locked\\)</a></td>")

# --- waypoints -------------------------------------------------------------------

WPT_SECTION_START = "id=\"ctl00_ContentBody_Waypoints\""
PATTERN_WPTYPE = re.compile("\\/WptTypes\\/sm\\/(.+)\\.jpg", I)
PATTERN_WPPREFIXORLOOKUPORLATLON = re.compile(">([^<]*<[^>]+>)?([^<]+)(<[^>]+>[^<]*)?<\\/td>")
PATTERN_WPNAME = re.compile(">[^<]*<a[^>]+>([^<]*)<\\/a>")
PATTERN_WPNOTE = re.compile("colspan=\"6\">(.*)" + re.escape("</td>"), D)

# --- misc -------------------------------------------------------------------------

PATTERN_LINEBREAK = re.compile("<(br|p)[^>]*>")
PATTERN_TYPE4 = re.compile("\"logTypes\":\\[([^]]+)]")
PATTERN_TOTAL_TRACKABLES = re.compile("\"totalTrackables\":\"?([\\d]+)\"?")
PATTERN_LOGPAGE_TRACKABLES = re.compile("\"trackables\":\\[(.+?\\})\\],[\"_sentry|\\},\"__N_SSP]")
PATTERN_MAINTENANCE = re.compile("<span id=\"ctl00_ContentBody_LogBookPanel1_lbConfirm\"[^>]*>([^<]*<font[^>]*>)?([^<]+)(</font>[^<]*)?</span>", I)
PATTERN_VIEWSTATEFIELDCOUNT = re.compile("id=\"__VIEWSTATEFIELDCOUNT\"[^(value)]+value=\"(\\d+)\"[^>]+>", I | M)
PATTERN_VIEWSTATES = re.compile("id=\"__VIEWSTATE(\\d*)\"[^(value)]+value=\"([^\"]+)\"[^>]+>", I | M)
PATTERN_USERTOKEN = re.compile("userToken\\s*=\\s*'([^']+)'")
PATTERN_REQUESTVERIFICATIONTOKEN = re.compile("__RequestVerificationToken\" type=\"hidden\" value=\"([^\"]+)\"")
PATTERN_PQ_LAST_GEN = re.compile("([^(]*)(\\(([\\d]+)?)?")
PATTERN_USERSESSION = re.compile("UserSession\\('([^']+)'")
PATTERN_SESSIONTOKEN = re.compile("\"?sessionToken\"?:['\"]([^'\"]+)")

STRING_PREMIUMONLY = "class=\"illustration lock-icon\""
PATTERN_PREMIUMONLY_CACHETYPE = re.compile("/app/ui-icons/sprites/cache-types\\.svg#icon-([^\"\\-]+)-?([^\"]+)?")
PATTERN_PREMIUMONLY_CACHENAME = re.compile("<h1 class=\"heading-3\">(.+)</h1>")
PATTERN_PREMIUMONLY_GEOCODE = re.compile("<li class=\"li__gccode\">([^<]+)")
PATTERN_PREMIUMONLY_DIFFICULTY = re.compile("<span id=\"ctl00_ContentBody_lblDifficulty\"(?:.|\\s)*?<span>([0-5](?:[\\.,]5)?)</span>")
PATTERN_PREMIUMONLY_TERRAIN = re.compile("<span id=\"ctl00_ContentBody_lblTerrain\"(?:.|\\s)*?<span>([0-5](?:[\\.,]5)?)</span>")
PATTERN_PREMIUMONLY_SIZE = re.compile("<span id=\"ctl00_ContentBody_lblSize\"(?:.|\\s)*?<span>([^<]+)</span>")

STRING_UNPUBLISHED_OTHER = "you cannot view this cache listing until it has been published"
STRING_UNPUBLISHED_FROM_SEARCH = "class=\"UnpublishedCacheSearchWidget"
STRING_UNKNOWN_ERROR = "An Error Has Occurred"
STRING_STATUS_DISABLED = "<div id=\"ctl00_ContentBody_uxDisabledMessageBody\""
STRING_STATUS_ARCHIVED = "<div id=\"ctl00_ContentBody_archivedMessage\""
STRING_STATUS_LOCKED = "<div id=\"ctl00_ContentBody_lockedMessage\""
STRING_CACHEDETAILS = "id=\"cacheDetails\""
STRING_404_FILE_NOT_FOUND = "<title>404 - File Not Found</title>"

URL_MESSAGECENTER = "https://www.geocaching.com/account/messagecenter"
NUMBER_OF_LOGS = 35
