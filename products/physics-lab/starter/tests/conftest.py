"""While ``fit_ringdown`` in ``my_lab/ringdown.py`` is still the skeleton
(it raises ``NotImplementedError``), the provided tests of
``tests/test_ringdown.py`` are skipped with that reason; as soon as it is
written they run, unchanged. The tests are still collected, so what they
import is checked either way."""

import pytest
from my_lab.ringdown import fit_ringdown

RINGDOWN_TESTS = "test_ringdown.py"
SKIPPED = (
    "YOUR WORK: fit_ringdown in my_lab/ringdown.py is not written yet"
    " (SPECIFICATION.md); these tests run as soon as it is"
)


def ringdown_is_written() -> bool:
    """False only while ``fit_ringdown`` raises ``NotImplementedError``.
    Any other outcome on a flat record, a ``ValueError`` among them, means
    the work is there and the tests decide."""
    try:
        fit_ringdown([float(i) for i in range(16)], [0.0] * 16)
    except NotImplementedError:
        return False
    except Exception:  # the tests judge what it raises
        return True
    return True


def pytest_collection_modifyitems(config, items):
    ours = [item for item in items if item.path.name == RINGDOWN_TESTS]
    if ours and not ringdown_is_written():
        for item in ours:
            item.add_marker(pytest.mark.skip(reason=SKIPPED))
