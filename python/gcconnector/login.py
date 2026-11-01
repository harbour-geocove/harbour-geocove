"""Login and logged-in requests, ported from c:geo's GCLogin.java.

Uses the stdlib-only gcconnector.httpclient (no third-party packages). Android specifics (WebView manual login,
Settings storage, avatar, home location setting) were left out; instead
`set_auth_cookie()` lets the UI inject a `gspkauth` cookie obtained elsewhere,
which is the way around captcha problems.
"""
import html
import json
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import httpclient as requests

from . import constants as C
from .models import StatusCode
from .textutils import get_match, matches, replace_whitespace

LOGIN_URI = "https://www.geocaching.com/account/signin?returnUrl=%2Faccount%2Fsettings%2Fhomelocation"
SERVER_PARAMS_URI = "https://www.geocaching.com/play/serverparameters/params"
TOKEN_URI = "https://www.geocaching.com/account/oauth/token"
WEBSITE_URL = "https://www.geocaching.com"
API_PROXY_URL = WEBSITE_URL + "/api/proxy"
REQUEST_VERIFICATION_TOKEN = "__RequestVerificationToken"

USER_AGENT = "Mozilla/5.0 (Linux; Sailfish) AppleWebKit/537.36 (KHTML, like Gecko) Mobile Safari/537.36"
TIMEOUT = 30
JSON_ACCEPT = "application/json, text/plain, */*"


class _StatusError(Exception):
    def __init__(self, status: StatusCode):
        super().__init__(status.value)
        self.status = status


# --- page helpers (GCParser.getUsername / getCachesCount live here to avoid a cycle)

def get_username(page: str) -> Optional[str]:
    username = get_match(page, C.PATTERN_LOGIN_NAME1, trim=False, default=None)
    if username and username.strip():
        if "\\" in username:
            try:
                username = json.loads('"%s"' % username)
            except ValueError:
                pass
        return username
    username = get_match(page, C.PATTERN_LOGIN_NAME2, trim=False, default=None)
    if username and username.strip():
        return username
    return None


def get_caches_count(page: Optional[str]) -> int:
    value = get_match(page, C.PATTERN_FINDCOUNT, True, 1, "")
    try:
        return int(value) if value else -1
    except ValueError:
        return -1


# --- custom date (format depends on the account's setting, e.g. "dd/MMM/yyyy")

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_gc_custom_date(text: str, fmt: str = C.DEFAULT_GC_DATE) -> datetime:
    """Parse a date using a Java SimpleDateFormat pattern (locale independent).

    Supports yyyy, yy, MMMM, MMM, MM, M, dd, d and literal separators.
    Raises ValueError when the text does not match.
    """
    tokens = re.findall(r"y+|M+|d+|[^yMd]+", fmt)
    rx, order = "", []
    for t in tokens:
        if t[0] == "y":
            rx += r"(\d{4})" if len(t) >= 3 else r"(\d{2})"
            order.append("y")
        elif t[0] == "M":
            if len(t) >= 3:
                rx += r"([A-Za-z]+)\.?"
                order.append("mname")
            else:
                rx += r"(\d{1,2})"
                order.append("m")
        elif t[0] == "d":
            rx += r"(\d{1,2})"
            order.append("d")
        else:
            rx += re.escape(t)
    m = re.fullmatch(rx, text.strip())
    if not m:
        raise ValueError("date %r does not match %r" % (text, fmt))
    y = mo = d = None
    for kind, val in zip(order, m.groups()):
        if kind == "y":
            y = int(val) + (2000 if len(val) == 2 else 0)
        elif kind == "m":
            mo = int(val)
        elif kind == "mname":
            mo = _MONTHS.get(val[:3].lower())
            if mo is None:
                raise ValueError("unknown month %r" % val)
        elif kind == "d":
            d = int(val)
    return datetime(y, mo, d, tzinfo=timezone.utc)


class GCLogin:
    """Holds the HTTP session and the user's date format."""

    def __init__(self, username: str = "", password: str = ""):
        self.username = username
        self.password = password
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": USER_AGENT})
        self.gc_custom_date = C.DEFAULT_GC_DATE
        self.logged_in = False
        self.user_name: Optional[str] = None
        self.caches_found = -1
        self.member_type: Optional[str] = None
        self.last_error: Optional[str] = None
        self._server_params: Optional[dict] = None
        self._auth: Optional[str] = None
        self._auth_expires = 0.0
        self.debug_lines: List[str] = []
        self.api_debug: List[str] = []
        self.last_api_error = ""
        self.token_error = ""

    # -- diagnostics (no passwords, cookie values or page contents are recorded)
    def _debug(self, msg: str) -> None:
        self.debug_lines = (self.debug_lines + [msg])[-40:]

    def debug_report(self) -> str:
        return "\n".join(self.debug_lines)

    def _debug_response(self, stage: str, resp) -> None:
        body = resp.text
        markers = [m for m in ("g-recaptcha", "recaptcha", "hcaptcha", "turnstile", "challenge-platform",
                               "signup-validation-error", "__RequestVerificationToken", "UsernameOrEmail",
                               "Password") if m.lower() in body.lower()]
        title = re.search(r"<title>(.*?)</title>", body, re.S | re.I)
        errors = [re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", e)).strip()[:120]
                  for e in re.findall(r'<[^>]+(?:error|validation)[^>]*>(.*?)</', body, re.S | re.I)][:3]
        names = sorted({c.name for c in self.http._jar})
        self._debug("%s: HTTP %d, %d B, url=%s, title=%r" % (
            stage, resp.status_code, len(resp.content), resp.url.split("?")[0],
            title.group(1).strip()[:80] if title else None))
        self._debug("  markers=%s, errors=%s, cookies=%s" % (markers, [e for e in errors if e], names))

    # -- dates
    def parse_date(self, text: str) -> datetime:
        return parse_gc_custom_date(text, self.gc_custom_date)

    # -- raw requests
    def _body_or_status(self, resp: requests.Response) -> str:
        body = resp.text
        if resp.status_code == 503 and matches(body, C.PATTERN_MAINTENANCE):
            raise _StatusError(StatusCode.MAINTENANCE)
        if not resp.ok:
            raise _StatusError(StatusCode.COMMUNICATION_ERROR)
        return body

    def get_text(self, url: str, params: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Plain GET without login check (Network.getRequest + getResponseData)."""
        try:
            r = self.http.get(url, params=params, timeout=TIMEOUT)
            return r.text if r.ok else None
        except requests.RequestException:
            return None

    # -- login
    def set_auth_cookie(self, gspkauth: str) -> StatusCode:
        """Use a `gspkauth` cookie (e.g. obtained in a browser) instead of the password."""
        self.http.cookies.set("gspkauth", gspkauth, domain=".geocaching.com", path="/")
        self._auth, self._auth_expires = None, 0.0
        return self._check_cookie_login()

    def _check_cookie_login(self) -> StatusCode:
        try:
            page = self._body_or_status(self.http.get(LOGIN_URI, timeout=TIMEOUT))
        except _StatusError as e:
            return e.status
        except requests.RequestException:
            return StatusCode.CONNECTION_FAILED_GC
        if self.get_login_status(page):
            return self._complete_login()
        self._debug("cookie login: the server did not accept the cookie (expired or wrong value)")
        return StatusCode.WRONG_LOGIN_DATA

    @staticmethod
    def _extract_verification_token(page: str) -> Optional[str]:
        for rx in (r'<input[^>]*name="%s"[^>]*value="([^"]*)"' % REQUEST_VERIFICATION_TOKEN,
                   r'<input[^>]*value="([^"]*)"[^>]*name="%s"' % REQUEST_VERIFICATION_TOKEN):
            m = re.search(rx, page)
            if m and m.group(1):
                return m.group(1)
        return None

    def login(self, retry: bool = True) -> StatusCode:
        status = self._login_internal(retry)
        if status != StatusCode.NO_ERROR:
            self.logged_in = False
            self.user_name = None
        return status

    def _login_internal(self, retry: bool) -> StatusCode:
        if not self.username or not self.password:
            self.gc_custom_date = C.DEFAULT_GC_DATE
            self.last_error = "missing login data"
            return StatusCode.NO_LOGIN_INFO_STORED
        self.debug_lines = []
        try:
            resp = self.http.get(LOGIN_URI, timeout=TIMEOUT)
            self._debug_response("login page", resp)
            page = self._body_or_status(resp)
            if not page.strip():
                return StatusCode.CONNECTION_FAILED_GC
            if self.get_login_status(page):
                return self._complete_login()

            token = self._extract_verification_token(page)
            if not token:
                self.last_error = "no verification token on login page"
                return StatusCode.LOGIN_PARSE_ERROR

            resp = self.http.post(LOGIN_URI, data={
                "UsernameOrEmail": self.username,
                "Password": self.password,
                REQUEST_VERIFICATION_TOKEN: token,
            }, timeout=TIMEOUT)
            self._debug_response("login POST", resp)
            data = self._body_or_status(resp)
            if not data.strip():
                return StatusCode.COMMUNICATION_ERROR
            if self.get_login_status(data):
                return self._complete_login()

            if 'class="g-recaptcha" data-sitekey="' in data or '<div class="g-recaptcha" data-sitekey="' in data:
                self.last_error = "captcha required - use set_auth_cookie()"
                self.gc_custom_date = C.DEFAULT_GC_DATE
                return StatusCode.LOGIN_CAPTCHA_ERROR
            if 'id="signup-validation-error"' in data:
                self.last_error = "wrong login data"
                self.gc_custom_date = C.DEFAULT_GC_DATE
                return StatusCode.WRONG_LOGIN_DATA
            if 'content="account/join/success"' in data:
                self.last_error = "account not validated"
                self.gc_custom_date = C.DEFAULT_GC_DATE
                return StatusCode.UNVALIDATED_ACCOUNT

            self.last_error = "unknown login error"
            self._debug("login not recognised: no username found in the answer page")
            if retry:
                self.get_login_status(data)
                return self._login_internal(False)
            self.gc_custom_date = C.DEFAULT_GC_DATE
            return StatusCode.UNKNOWN_ERROR
        except _StatusError as e:
            return e.status
        except requests.RequestException:
            self.last_error = "communication error"
            return StatusCode.CONNECTION_FAILED_GC

    def logout(self) -> None:
        try:
            self.http.post("https://www.geocaching.com/account/logout", timeout=TIMEOUT)
        except requests.RequestException:
            pass
        self._server_params = None
        self._auth = None
        self._auth_expires = 0.0
        self.logged_in = False
        self.user_name = None

    def get_login_status(self, page: Optional[str]) -> bool:
        """True if the page was delivered to a logged-in user (updates state)."""
        if not page or not page.strip():
            return False
        name = get_username(page)
        self.logged_in = bool(name)
        if self.logged_in:
            self.user_name = name
            self.caches_found = get_caches_count(page)
            return True
        return False

    # -- server parameters (user's date format, membership)
    def server_parameters(self) -> Optional[dict]:
        if self._server_params is not None:
            return self._server_params
        try:
            body = self._body_or_status(self.http.get(SERVER_PARAMS_URI, timeout=TIMEOUT))
            js = body[body.index("{"):body.rindex(";")]
            params = json.loads(js)
        except (ValueError, _StatusError, requests.RequestException):
            self.gc_custom_date = C.DEFAULT_GC_DATE
            return None
        info = params.get("user:info") or {}
        if info.get("dateFormat"):
            self.gc_custom_date = info["dateFormat"]
        self.member_type = info.get("userType")
        if not self.member_type:
            return params  # not logged in yet: read again next time
        self._server_params = params
        return params

    def _complete_login(self) -> StatusCode:
        self.server_parameters()
        self.authorization()  # force token retrieval up front (as GCAuthAPI does)
        return StatusCode.NO_ERROR

    # -- OAuth token + api/proxy (port of GCAuthAPI.java)
    @staticmethod
    def _excerpt(resp) -> str:
        """Short plain-text start of an (error) response body, for diagnostics."""
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", resp.text or "")).strip()
        return text[:120]

    def _api_note(self, msg: str) -> None:
        self.last_api_error = msg
        self.api_debug = (self.api_debug + [msg])[-12:]

    def authorization(self, force: bool = False) -> Optional[str]:
        """'<token_type> <access_token>' for api/proxy calls; cached for 80 % of its lifetime."""
        now = time.time()
        if not force and self._auth and now < self._auth_expires:
            return self._auth
        self._auth, self._auth_expires = None, 0.0
        try:
            r = self.http.get(TOKEN_URI, headers={"Accept": JSON_ACCEPT}, timeout=TIMEOUT)
        except requests.RequestException as e:
            self.token_error = "network error: %s" % e
            self._api_note("token: " + self.token_error)
            return None
        try:
            r.raise_for_status()
            data = r.json()
            self._auth = "%s %s" % (data["token_type"], data["access_token"])
            self._auth_expires = now + float(data.get("expires_in", 0)) * 0.8
            self.token_error = ""
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
            self.token_error = "HTTP %d %s: %s" % (r.status_code, r.headers.get("content-type", "?").split(";")[0],
                                                   self._excerpt(r))
            self._api_note("token: " + self.token_error)
        return self._auth

    def api_proxy(self, method: str, uri: str, params=None, json_body=None, headers=None):
        """Call https://www.geocaching.com/api/proxy<uri>; returns parsed JSON, {} for an empty body,
        or None on any error (see last_api_error). `params` may be a dict or a list of tuples.
        On 401/403 a new token is fetched and the call is repeated once."""
        for attempt in (0, 1):
            hdr = {"Accept": JSON_ACCEPT}
            hdr.update(headers or {})
            auth = self.authorization(force=(attempt == 1))
            if auth:
                hdr["Authorization"] = auth
            try:
                r = self.http.request(method, API_PROXY_URL + uri, params=params, json=json_body,
                                      headers=hdr, timeout=TIMEOUT)
            except requests.RequestException as e:
                self._api_note("api %s %s: network error %s" % (method, uri.split("?")[0], e))
                return None
            if r.status_code in (401, 403) and attempt == 0:
                continue                      # the token may have expired: new token, one more try
            if not r.ok:
                note = "api %s %s: HTTP %d %s: %s" % (
                    method, uri.split("?")[0], r.status_code, r.headers.get("content-type", "?").split(";")[0],
                    self._excerpt(r))
                if not auth:
                    note += " [no token: %s]" % self.token_error
                self._api_note(note)
                return None
            try:
                return r.json() if r.content else {}
            except ValueError:
                self._api_note("api %s %s: answer is not JSON (%s)" % (method, uri.split("?")[0], self._excerpt(r)))
                return None
        return None

    # -- logged requests (retry once after re-login)
    @staticmethod
    def _can_remove_whitespace(uri: str) -> bool:
        # the cache details page has user-generated whitespace in the personal note
        return "cache_details" not in uri

    def get_request_logged(self, uri: str, params: Optional[Dict[str, str]] = None,
                           remove_whitespace: Optional[bool] = None) -> Optional[str]:
        rw = self._can_remove_whitespace(uri) if remove_whitespace is None else remove_whitespace

        def fetch():
            r = self.http.get(uri, params=params, timeout=TIMEOUT)
            text = r.text
            return r, (replace_whitespace(text) if rw else text)

        try:
            resp, data = fetch()
            # a page not found will not be found if the user logs in either
            if resp.status_code == 404 or self.get_login_status(data):
                return data
            if self.login() == StatusCode.NO_ERROR:
                return fetch()[1]
            return data  # working as guest
        except requests.RequestException:
            return None

    def post_request_logged(self, uri: str, data: Optional[Dict[str, str]] = None) -> Optional[str]:
        try:
            text = self.http.post(uri, data=data, timeout=TIMEOUT).text
            if self.get_login_status(text):
                return text
            if self.login() == StatusCode.NO_ERROR:
                return self.http.post(uri, data=data, timeout=TIMEOUT).text
            return text
        except requests.RequestException:
            return None


def get_viewstates(page: Optional[str]):
    """Read all ASP.NET viewstates from a page (needed for form posts)."""
    if page is None:
        return None
    count = 1
    m = C.PATTERN_VIEWSTATEFIELDCOUNT.search(page)
    if m:
        try:
            count = int(m.group(1))
        except ValueError:
            pass
    states = [None] * count
    for m in C.PATTERN_VIEWSTATES.finditer(page):
        no = int(m.group(1)) if m.group(1) else 0
        if no < count:
            states[no] = html.unescape(m.group(2))
    return None if (len(states) == 1 and states[0] is None) else states
