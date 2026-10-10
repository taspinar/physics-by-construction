"""scripts/check-links.sh reports a dead link and a missing anchor (ADR 009).

The script runs against a local fixture server, so the test needs no network.
It is also absent from the required checks: a check that contacts other sites
cannot be a verification check.
"""

import http.server
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from support.paths import REPO_ROOT
from support.verify_conf import checks

SCRIPT = REPO_ROOT / "scripts" / "check-links.sh"

PAGE = b'<html><body><h2 id="energy">Energy</h2><a name="old"></a></body></html>'


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/large.html":
            # An anchor placed past any fixed read limit of the checker.
            body = b"<p>" + b"x" * 6_000_000 + b'</p><h2 id="late">Late</h2>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/page.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PAGE)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def server() -> Iterator[str]:
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    thread.join()


def run(tmp_path: Path, register: str) -> subprocess.CompletedProcess[str]:
    file = tmp_path / "references.yaml"
    file.write_text(register)
    return subprocess.run(
        [str(SCRIPT), "--register", str(file), "--timeout", "5"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_links_that_resolve_pass(tmp_path: Path, server: str):
    result = run(
        tmp_path,
        f"- key: fine\n  url: {server}/page.html#energy\n  last_checked: 2026-01-01\n"
        f"- key: plain\n  url: {server}/page.html\n"
        f"- key: named\n  url: {server}/page.html\n  anchor: old\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All 3 links resolve" in result.stdout
    assert "set last_checked to" in result.stdout


def test_dead_link_and_missing_anchor_are_reported(tmp_path: Path, server: str):
    result = run(
        tmp_path,
        f"- key: fine\n  url: {server}/page.html#energy\n"
        f"- key: gone\n  url: {server}/gone.html\n  last_checked: 2026-01-01\n"
        f"- key: moved\n  url: {server}/page.html#momentum\n",
    )
    assert result.returncode == 1
    lines = result.stdout.splitlines()
    assert any(
        line.startswith("BROKEN") and "gone" in line and "HTTP 404" in line
        for line in lines
    )
    assert any(
        line.startswith("BROKEN") and "moved" in line and "#momentum" in line
        for line in lines
    )
    assert any(line.startswith("OK") and "fine" in line for line in lines)
    assert "2 of 3 links no longer resolve" in result.stdout


def test_an_anchor_late_in_a_large_page_is_found(tmp_path: Path, server: str):
    result = run(tmp_path, f"- key: late\n  url: {server}/large.html#late\n")
    assert result.returncode == 0, result.stdout + result.stderr


def test_unreachable_host_is_reported(tmp_path: Path):
    result = run(tmp_path, "- key: nowhere\n  url: http://127.0.0.1:9/x.html\n")
    assert result.returncode == 1
    assert "BROKEN   nowhere" in result.stdout


def test_a_missing_register_has_nothing_to_check(tmp_path: Path):
    result = subprocess.run(
        [str(SCRIPT), "--register", str(tmp_path / "none.yaml")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "no link to check" in result.stdout


def test_the_link_check_is_not_a_required_check():
    assert not any("check-links" in cmd for cmd in checks().values())
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "check-links" not in ci
