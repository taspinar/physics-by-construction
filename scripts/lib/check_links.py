"""Report every link of the reference register that no longer resolves.

Run through scripts/check-links.sh. Reads site/references.yaml (ADR 009),
opens every URL with a timeout, and checks that the page answers and, when
the entry names an anchor, that the page has it. Prints a report and changes
nothing; the maintainer updates the last-checked dates it names.

Exit status: 0 when every link resolves, 1 when one does not, 2 for a
register that cannot be read.
"""

import argparse
import codecs
import datetime
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag

import yaml

USER_AGENT = "physics-by-construction-link-check (maintenance, on demand)"
CHUNK_BYTES = 65_536


class Anchors(HTMLParser):
    """The ids and names a page offers as link targets."""

    def __init__(self) -> None:
        super().__init__()
        self.found: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in ("id", "name") and value:
                self.found.add(value)


def entries(register: Path) -> list[dict]:
    data = yaml.safe_load(register.read_text())
    if isinstance(data, dict):
        data = data.get("references", data.get("entries", []))
    if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
        raise ValueError("expected a list of entries, or a mapping with 'references'")
    return data


def has_anchor(response, anchor: str) -> bool:
    """Stream the whole response through the parser; stop once the anchor shows."""
    wanted = {anchor, unquote(anchor)}
    charset = response.headers.get_content_charset() or "utf-8"
    try:
        decoder = codecs.getincrementaldecoder(charset)(errors="replace")
    except LookupError:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    parser = Anchors()
    while chunk := response.read(CHUNK_BYTES):
        parser.feed(decoder.decode(chunk))
        if wanted & parser.found:
            return True
    parser.feed(decoder.decode(b"", final=True))
    parser.close()
    return bool(wanted & parser.found)


def check(url: str, anchor: str | None, timeout: float) -> str | None:
    """None when the link resolves, else the reason it does not."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if anchor and not has_anchor(response, anchor):
                return f"missing anchor: #{anchor}"
    except urllib.error.HTTPError as error:
        return f"dead: HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return f"dead: {getattr(error, 'reason', error)}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--register", type=Path, default=Path("site/references.yaml"))
    parser.add_argument("--timeout", type=float, default=15.0)
    arguments = parser.parse_args()

    if not arguments.register.exists():
        print(f"No register at {arguments.register}: no link to check.")
        return 0
    try:
        found = entries(arguments.register)
    except (yaml.YAMLError, ValueError) as error:
        print(f"Cannot read {arguments.register}: {error}", file=sys.stderr)
        return 2

    today = datetime.date.today().isoformat()
    problems = 0
    print(f"Link check of {arguments.register} on {today}")
    for position, entry in enumerate(found, start=1):
        key = str(entry.get("key", f"entry {position}"))
        url = entry.get("url")
        if not url:
            print(f"BROKEN   {key}: the entry has no url")
            problems += 1
            continue
        page, fragment = urldefrag(str(url))
        anchor = str(entry.get("anchor") or fragment) or None
        reason = check(page, anchor, arguments.timeout)
        was = f"last checked {entry.get('last_checked', 'never')}"
        if reason:
            problems += 1
            print(f"BROKEN   {key}: {reason} ({url}); {was}")
        else:
            print(f"OK       {key}: set last_checked to {today} ({was})")
    print()
    if problems:
        print(
            f"{problems} of {len(found)} links no longer resolve. Re-research"
            " each one; do not replace it by a title match (docs/authoring.md)."
        )
        return 1
    print(f"All {len(found)} links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
