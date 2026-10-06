"""Serve a built site locally under the path it has in production.

GitHub Pages serves the site from a sub-path of the host
(``/physics-by-construction/``). Serving it the same way in tests means a link
that only works at the root of a host fails here too.
"""

import threading
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import yaml


def configured_site_url(site_source: Path) -> str:
    """Return the public address of the site: ``website.site-url``."""
    config = yaml.safe_load((site_source / "_quarto.yml").read_text())
    url = config["website"]["site-url"]
    return url if url.endswith("/") else url + "/"


def configured_repository_url(site_source: Path) -> str:
    """Return the address of the repository: ``website.repo-url``."""
    config = yaml.safe_load((site_source / "_quarto.yml").read_text())
    return config["website"]["repo-url"].rstrip("/")


def configured_base_path(site_source: Path) -> str:
    """Return the path of the public address, with a trailing slash."""
    return urlsplit(configured_site_url(site_source)).path


class _Handler(SimpleHTTPRequestHandler):
    base_path = "/"

    def send_head(self):  # type: ignore[no-untyped-def]
        if not urlsplit(self.path).path.startswith(self.base_path):
            # Outside the site: answer as the real host would.
            self.send_error(HTTPStatus.NOT_FOUND, "Outside the site")
            return None
        return super().send_head()

    def translate_path(self, path: str) -> str:
        request_path = urlsplit(path).path
        return super().translate_path("/" + request_path[len(self.base_path) :])

    def log_message(self, format: str, *args: object) -> None:
        pass


class SiteServer:
    """Context manager that serves ``directory`` at ``base_path``."""

    def __init__(self, directory: Path, base_path: str = "/") -> None:
        if not (base_path.startswith("/") and base_path.endswith("/")):
            raise ValueError(f"base path must start and end with '/': {base_path}")
        handler = type("Handler", (_Handler,), {"base_path": base_path})
        self._httpd = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(handler, directory=str(directory))
        )
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self.base_path = base_path

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self._httpd.server_address[1]}"

    @property
    def url(self) -> str:
        """URL of the site root, with a trailing slash."""
        return self.origin + self.base_path

    def __enter__(self) -> SiteServer:
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join()
