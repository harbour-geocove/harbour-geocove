"""Get the geocaching.com session cookie out of the embedded web view.

The Sailfish web view (Gecko) keeps its cookies in a Firefox-style `cookies.sqlite`
inside the app's profile directory. After the user logged in (and solved the captcha)
in the web view we read `gspkauth` from there. A cookie visible to JavaScript
(`document.cookie`) is tried first. No cookie *values* are ever put into the reports.

Caveat: Gecko does not write pure session cookies to disk. If the site sets `gspkauth`
without an expiry date this cannot work - the report says so.
"""
import os
import re
import shutil
import sqlite3
import tempfile
from typing import Iterable, List, Optional, Tuple

COOKIE_NAME = "gspkauth"
HOST_SUFFIX = "geocaching.com"


def parse_cookie_header(header: Optional[str], name: str = COOKIE_NAME) -> Optional[str]:
    """Value of `name` in a 'a=b; c=d' string (document.cookie), or None."""
    for part in (header or "").split(";"):
        key, _, value = part.strip().partition("=")
        if key == name and value:
            return value
    return None


def extract_gspkauth(text: Optional[str]) -> Optional[str]:
    """Cookie value from whatever the user pasted: just the value, `gspkauth=VALUE`, a whole
    `Cookie:` header line, or a row copied from browser developer tools (tab separated)."""
    t = (text or "").strip()
    if not t:
        return None
    t = re.sub(r"^\s*cookie\s*:\s*", "", t, flags=re.I)
    for line in t.splitlines():
        cols = [c.strip() for c in line.split("\t")]
        if len(cols) >= 2 and cols[0].lower() == COOKIE_NAME and cols[1]:
            return cols[1].strip("\"'")
    value = parse_cookie_header(t.replace("\n", ";").replace("\r", ""), COOKIE_NAME)
    if value:
        return value.strip("\"'")
    t = t.strip("\"'")
    if re.fullmatch(r"[^\s;,]+", t) and not t.lower().startswith(COOKIE_NAME + "="):
        return t                      # looks like the bare value
    return None


def find_cookie_dbs(roots: Iterable[str], max_depth: int = 6, max_dirs: int = 20000) -> List[str]:
    """All files named cookies.sqlite below the roots, newest first."""
    found, seen_dirs = [], 0
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        base_depth = root.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root):
            seen_dirs += 1
            if seen_dirs > max_dirs or dirpath.count(os.sep) - base_depth >= max_depth:
                dirnames[:] = []
            if "cookies.sqlite" in filenames:
                path = os.path.join(dirpath, "cookies.sqlite")
                if path not in found:
                    found.append(path)
    found.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return found


def read_cookie_from_db(path: str, name: str = COOKIE_NAME) -> Tuple[Optional[str], List[str]]:
    """(value or None, report lines) from one Gecko cookie database.

    The database is copied together with its -wal/-shm files first, because Gecko keeps
    recent changes in the write-ahead log and the original may be locked."""
    report: List[str] = []
    tmp = tempfile.mkdtemp(prefix="gccookies")
    try:
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(path + suffix):
                shutil.copy2(path + suffix, os.path.join(tmp, "cookies.sqlite" + suffix))
        conn = sqlite3.connect(os.path.join(tmp, "cookies.sqlite"))
        try:
            rows = conn.execute(
                "SELECT name, value, host, expiry FROM moz_cookies WHERE host LIKE ?",
                ("%" + HOST_SUFFIX,)).fetchall()
        finally:
            conn.close()
        names = sorted({r[0] for r in rows})
        report.append("%s: %d geocaching.com cookies, names=%s" % (path, len(rows), names))
        for cname, value, host, expiry in rows:
            if cname == name and value:
                return value, report
        if rows and name not in names:
            report.append("  %s not stored (probably a session cookie, which Gecko keeps in memory only)" % name)
    except (sqlite3.Error, OSError) as e:
        report.append("%s: cannot read (%s)" % (path, e))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return None, report


def find_gspkauth(roots: Iterable[str]) -> Tuple[Optional[str], List[str]]:
    dbs = find_cookie_dbs(roots)
    report = ["searched %d root dirs, found %d cookies.sqlite file(s)" % (len(list(roots)), len(dbs))]
    for path in dbs:
        value, lines = read_cookie_from_db(path)
        report += lines
        if value:
            return value, report
    return None, report
