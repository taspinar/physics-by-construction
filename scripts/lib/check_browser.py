"""Check that the browser build pinned through uv.lock is installed and starts.

Used by scripts/lib/prerequisites.sh. The exit status tells the two failures
apart, because they have different fixes:

    0  the browser started and rendered a page
    3  the browser build is not installed
    4  the browser build is installed but cannot start
"""

import sys

from playwright.sync_api import Error, sync_playwright

NOT_INSTALLED = 3
CANNOT_START = 4


def _reason(error: Error) -> str:
    """Return the first line of a Playwright error, indented like a fix hint."""
    return "         " + str(error).strip().splitlines()[0]


def main() -> int:
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Error as error:
            print(_reason(error), file=sys.stderr)
            if "Executable doesn't exist" in str(error):
                return NOT_INSTALLED
            return CANNOT_START
        try:
            page = browser.new_page()
            page.set_content("<p>ready</p>")
            if page.inner_text("p") != "ready":
                print("         The browser did not render a page.", file=sys.stderr)
                return CANNOT_START
        except Error as error:
            print(_reason(error), file=sys.stderr)
            return CANNOT_START
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
