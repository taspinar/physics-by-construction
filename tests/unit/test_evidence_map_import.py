"""The tests of the evidence map read the claims when they run, not when
pytest imports them: every run that collects tests/e2e imports the module,
also the runs that select other tests, and reading the claims starts a pandoc
for each block of every lesson."""

import importlib.util

from support.paths import REPO_ROOT

from pbc.authoring import evidence

MODULE = REPO_ROOT / "tests" / "e2e" / "test_evidence_map.py"


def test_importing_the_evidence_map_tests_reads_no_claim(monkeypatch):
    def read_all(*args, **kwargs):
        raise AssertionError("the claims were read while the module was imported")

    monkeypatch.setattr(evidence, "read_all", read_all)
    spec = importlib.util.spec_from_file_location("evidence_map_probe", MODULE)
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert hasattr(module, "CLAIMS")
