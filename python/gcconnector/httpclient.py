"""Tiny `requests`-like HTTP client on top of the standard library.

Only what the connector needs: Session with cookies and default headers,
get/post/request with params, form data, json body, gzip, redirects.
Keeps the app free of third-party Python packages (nothing to bundle on Sailfish OS).
"""
import gzip
import json as _json
import socket
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import Cookie, CookieJar
from typing import Any, Dict, List, Optional


class RequestException(Exception):
    """Network level failure (DNS, connection, timeout, ...)."""


class Response:
    def __init__(self, status_code: int, content: bytes, headers: Dict[str, str], url: str):
        self.status_code = status_code
        self.content = content
        self.headers = headers
        self.url = url

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    @property
    def encoding(self) -> str:
        ctype = self.headers.get("content-type", "")
        if "charset=" in ctype:
            return ctype.split("charset=", 1)[1].split(";")[0].strip().strip('"') or "utf-8"
        return "utf-8"

    @property
    def text(self) -> str:
        try:
            return self.content.decode(self.encoding, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return _json.loads(self.text)

    def raise_for_status(self) -> None:
        if not self.ok:
            raise RequestException("HTTP %d for %s" % (self.status_code, self.url))


class _Cookies:
    def __init__(self, jar: CookieJar):
        self.jar = jar

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        for c in self.jar:
            if c.name == name:
                return c.value
        return default

    def set(self, name: str, value: str, domain: str = "", path: str = "/", secure: bool = False) -> None:
        self.jar.set_cookie(Cookie(
            0, name, value, None, False, domain, bool(domain), domain.startswith("."), path, True,
            secure, None, True, None, None, {}))

    def clear(self) -> None:
        self.jar.clear()


class _NoRedirectOnError(urllib.request.HTTPRedirectHandler):
    """Default behaviour (follow redirects, POST -> GET), kept explicit for clarity."""


class Session:
    def __init__(self):
        self.headers: Dict[str, str] = {"Accept-Encoding": "gzip"}
        self._jar = CookieJar()
        self.cookies = _Cookies(self._jar)
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar), _NoRedirectOnError())

    def request(self, method: str, url: str, params=None, data=None, json=None,
                headers: Optional[Dict[str, str]] = None, timeout: float = 30) -> Response:
        if params:
            query = urllib.parse.urlencode(params)
            url += ("&" if "?" in url else "?") + query
        body: Optional[bytes] = None
        hdr = dict(self.headers)
        if json is not None:
            body = _json.dumps(json).encode("utf-8")
            hdr["Content-Type"] = "application/json"
        elif data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            hdr["Content-Type"] = "application/x-www-form-urlencoded"
        elif method.upper() in ("POST", "PUT", "PATCH"):
            body = b""
        hdr.update(headers or {})
        req = urllib.request.Request(url, data=body, headers=hdr, method=method.upper())
        try:
            try:
                resp = self._opener.open(req, timeout=timeout)
            except urllib.error.HTTPError as e:   # 4xx / 5xx still carry a body
                resp = e
            raw = resp.read()
            rh = {k.lower(): v for k, v in resp.headers.items()}
            if rh.get("content-encoding", "").lower() == "gzip":
                raw = gzip.decompress(raw)
            return Response(getattr(resp, "status", None) or resp.getcode(), raw, rh, resp.geturl())
        except (urllib.error.URLError, socket.timeout, OSError, EOFError) as e:
            raise RequestException(str(e))

    def get(self, url: str, params=None, headers=None, timeout: float = 30) -> Response:
        return self.request("GET", url, params=params, headers=headers, timeout=timeout)

    def post(self, url: str, data=None, json=None, params=None, headers=None, timeout: float = 30) -> Response:
        return self.request("POST", url, params=params, data=data, json=json, headers=headers, timeout=timeout)
