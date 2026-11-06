"""The thin local interface of the product (unresolved question 21, settled
in F138; ``docs/products.md``).

One page, rendered on the server by the standard library, with no
JavaScript and no build step: the configuration form, the progress of a
running sweep (the page reloads itself once a second while it runs), the
results with the report's figure, the failures with what to do about them,
a stop button, and links to the exported files. ``App.handle`` maps a
request to a response without a socket, so the page is tested without
starting a server; ``serve`` binds it to the loopback interface of the
learner's own machine and refuses any other address.

Binding to loopback does not stop another web page open in the learner's
browser from sending a form to the interface, or a foreign domain that
resolves to 127.0.0.1 (DNS rebinding) from reading it. So every request
must carry a Host header that names the interface's own loopback address and
port, and every POST must come from the interface's own origin (its Origin,
or without one its Referer) and carry the random token of this process that
the page embeds in its forms. A request that fails any of these is refused
and changes nothing: no other origin can start a run, stop one, or supply
the learner's confirmation of the circuit.
"""

import html
import ipaddress
import secrets
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from pbc.instruments import RECORDED, SIMULATED, Instrument
from pbc.products.physics_lab import workflow
from pbc.products.physics_lab.protocol import Config, Measurement
from pbc.products.physics_lab.report import ALT

LOOPBACK_NAMES = {"localhost"}
# The loopback names a browser on this machine may put in the Host header.
_LOOPBACK_AUTHORITIES = ("127.0.0.1", "localhost", "[::1]")
EXPORTS = (
    "report.md",
    "raw.csv",
    "points.csv",
    "run.json",
    "evidence.json",
    "frequency-response.svg",
)
_TYPES = {
    ".md": "text/markdown; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}

_MODE_TEXT = {
    SIMULATED: "Simulated experiment on a deterministic model. Not a measurement.",
    RECORDED: "Recorded data replayed from a declared sample. Not a new experiment.",
}


def check_host(host: str) -> str:
    """``host`` if it is a loopback address; otherwise raise ``ValueError``."""
    if host in LOOPBACK_NAMES:
        return host
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError(f"{host!r} is not a loopback address") from None
    if not address.is_loopback:
        raise ValueError(
            f"{host} is not a loopback address; the product listens only on this"
            " machine (127.0.0.1)"
        )
    return host


@dataclass(frozen=True)
class Response:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes


@dataclass
class State:
    status: str = "idle"  # idle, running, finished, failed
    route: str = workflow.BASELINE
    mode: str = SIMULATED
    points: list[Measurement] = field(default_factory=list)
    result: workflow.Result | None = None
    error: str | None = None
    instrument: Instrument | None = None


class App:
    """The interface's state and its request handling."""

    def __init__(
        self,
        out_root: Path,
        config: Config,
        trace: Path = workflow.TRACE,
        threaded: bool = True,
        runner: Callable[..., workflow.Result] = workflow.run,
        host: str = "127.0.0.1",
        port: int = 8765,
    ):
        self.host = check_host(host)
        self.port = port
        address = f"[{host}]" if ":" in host else host
        self.authorities = frozenset(
            f"{name}:{port}" for name in (address, *_LOOPBACK_AUTHORITIES)
        )
        self.origins = frozenset(f"http://{a}" for a in self.authorities)
        # Embedded in the page's forms; a page of another origin cannot read it.
        self.token = secrets.token_urlsafe(32)
        self.out_root = out_root
        self.config = config
        self.trace = trace
        self.threaded = threaded
        self.runner = runner
        self.state = State()
        self._lock = threading.Lock()

    # -- requests --------------------------------------------------------------

    def handle(
        self,
        method: str,
        path: str,
        form: dict[str, str],
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        """The response to one request; ``headers`` maps lower-case header
        names to their values."""
        refusal = self._refusal(method, form, headers or {})
        if refusal is not None:
            return Response(
                403, (("Content-Type", "text/plain; charset=utf-8"),), refusal.encode()
            )
        if method == "GET" and path == "/":
            return self._page()
        if method == "POST" and path == "/run":
            self._start(form)
            return _redirect()
        if method == "POST" and path == "/stop":
            instrument = self.state.instrument
            if self.state.status == "running" and instrument is not None:
                instrument.request_stop("stopped from the interface")
            return _redirect()
        if method == "GET" and path.startswith("/files/"):
            return self._file(path.removeprefix("/files/"))
        return Response(404, (("Content-Type", "text/plain; charset=utf-8"),), b"")

    def _refusal(
        self, method: str, form: dict[str, str], headers: Mapping[str, str]
    ) -> str | None:
        """Why the request is refused, or None when it comes from this
        interface's own page."""
        if headers.get("host") not in self.authorities:
            return "Refused: the Host header does not name this local interface."
        if method != "POST":
            return None
        origin = headers.get("origin")
        if origin is None:
            referer = headers.get("referer", "")
            if not any(referer.startswith(f"{o}/") for o in self.origins):
                return "Refused: the request does not come from this interface's page."
        elif origin not in self.origins:
            return "Refused: the request comes from another origin."
        if not secrets.compare_digest(form.get("token", ""), self.token):
            return "Refused: the form does not carry this interface's token."
        return None

    def _start(self, form: dict[str, str]) -> None:
        with self._lock:
            if self.state.status == "running":
                return
            try:
                config, route, mode = self._parse(form)
            except ValueError as reason:
                self.state = State(status="failed", error=str(reason))
                return
            self.state = State(status="running", route=route, mode=mode)
        if self.threaded:
            threading.Thread(
                target=self._run, args=(config, route, mode), daemon=True
            ).start()
        else:
            self._run(config, route, mode)

    def _parse(self, form: dict[str, str]) -> tuple[Config, str, str]:
        route = form.get("route", workflow.BASELINE)
        mode = form.get("mode", SIMULATED)
        if route not in workflow.ROUTES:
            raise ValueError(f"Choose a route: {', '.join(workflow.ROUTES)}.")
        if mode not in _MODE_TEXT:
            raise ValueError("Choose the simulated or the recorded mode.")

        def number(name: str, kind: type, label: str):
            text = form.get(name, "").strip()
            try:
                return kind(text)
            except ValueError:
                raise ValueError(f"{label} must be a number, got {text!r}.") from None

        changes = {
            "seed": number("seed", int, "The seed"),
            "low_hz": number("low_hz", float, "The lowest frequency"),
            "high_hz": number("high_hz", float, "The highest frequency"),
            "amplitude_v": number("amplitude_v", float, "The amplitude"),
            "circuit_confirmed": form.get("circuit_confirmed") == "yes",
        }
        return replace(self.config, **changes), route, mode

    def _run(self, config: Config, route: str, mode: str) -> None:
        out_dir = self.out_root / f"{route}-{mode}-seed{config.seed}"
        try:
            sample = None
            if mode == RECORDED:
                sample = self.out_root / f"synthetic-sample-seed{config.seed}.json"
                if not sample.exists():
                    workflow.write_synthetic_sample(config, sample)
            result = self.runner(
                config,
                out_dir,
                route=route,
                mode=mode,
                sample=sample,
                trace=self.trace,
                on_point=self.state.points.append,
                on_instrument=self._attach,
            )
        except Exception as error:  # shown on the page, never swallowed
            self.state.status, self.state.error = "failed", f"{error}"
            return
        self.state.result = result
        self.state.status = "finished" if result.status != "failed" else "failed"
        if result.diagnostics and result.status == "failed":
            self.state.error = "; ".join(result.diagnostics)

    def _attach(self, instrument: Instrument) -> None:
        self.state.instrument = instrument

    def _file(self, name: str) -> Response:
        result = self.state.result
        if name not in EXPORTS or result is None:
            return Response(404, (("Content-Type", "text/plain; charset=utf-8"),), b"")
        path = result.out_dir / name
        if not path.is_file():
            return Response(404, (("Content-Type", "text/plain; charset=utf-8"),), b"")
        kind = _TYPES[path.suffix]
        return Response(200, (("Content-Type", kind),), path.read_bytes())

    # -- the page --------------------------------------------------------------

    def _page(self) -> Response:
        body = render(self.state, self.config, self.token).encode("utf-8")
        return Response(200, (("Content-Type", "text/html; charset=utf-8"),), body)


def _redirect() -> Response:
    return Response(303, (("Location", "/"),), b"")


_STYLE = """
:root {
  --paper: #fafbfc; --ink: #18202b; --muted: #4a5563; --rule: #cbd3de;
  --simulated: #00429d; --recorded: #8a5a00; --fault: #93003a; --pass: #006b5c;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink);
  font: 1rem/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
.mode { color: #fff; padding: 1.1rem 1.5rem; }
.mode.simulated { background: var(--simulated); }
.mode.recorded { background: var(--recorded); }
.mode p { margin: 0; max-width: 70ch; font-size: 1.15rem; font-weight: 600; }
.mode h1 { margin: 0 0 .2rem; font-size: 1rem; font-weight: 400; }
main { display: grid; grid-template-columns: minmax(16rem, 22rem) 1fr;
  gap: 2.5rem; padding: 1.5rem; max-width: 72rem; }
@media (max-width: 52rem) { main { grid-template-columns: 1fr; } }
h2 { font-size: 1.15rem; margin: 0 0 .75rem; }
fieldset { border: 0; border-top: 1px solid var(--rule); margin: 0 0 1rem;
  padding: .75rem 0 0; }
legend { font-weight: 600; padding: 0 .4rem 0 0; }
label { display: block; margin: .35rem 0; }
input[type=text] { width: 100%; padding: .35rem .5rem; font: inherit;
  border: 1px solid var(--rule); border-radius: 3px; background: #fff; }
button { font: inherit; padding: .45rem 1rem; border-radius: 3px;
  border: 1px solid var(--ink); background: var(--ink); color: #fff; cursor: pointer; }
button.stop { background: var(--fault); border-color: var(--fault); }
:focus-visible { outline: 3px solid var(--simulated); outline-offset: 2px; }
.status { font-weight: 600; }
.failure { border-left: 4px solid var(--fault); padding: .5rem 1rem; }
.verdict.pass { color: var(--pass); } .verdict.fail { color: var(--fault); }
table { border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: right; padding: .25rem .9rem .25rem 0;
  border-bottom: 1px solid var(--rule); }
th:first-child, td:first-child { text-align: left; }
figure { margin: 1rem 0; max-width: 46rem; } figure svg { width: 100%; height: auto; }
figcaption { color: var(--muted); max-width: 70ch; }
.unverified { color: var(--muted); }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def _token(token: str) -> str:
    return f'<input type="hidden" name="token" value="{_e(token)}">'


def _form(state: State, config: Config, token: str) -> str:
    def option(name, value, label, current):
        checked = " checked" if value == current else ""
        return (
            f'<label><input type="radio" name="{name}" value="{value}"{checked}>'
            f" {_e(label)}</label>"
        )

    def field_(name, label, value):
        return (
            f'<label for="{name}">{_e(label)}</label>'
            f'<input type="text" id="{name}" name="{name}" value="{_e(value)}"'
            ' inputmode="decimal">'
        )

    confirmed = " checked" if config.circuit_confirmed else ""
    return f"""
<form method="post" action="/run">
  {_token(token)}
  <h2>Run the frequency sweep</h2>
  <fieldset><legend>Route</legend>
    {option("route", "baseline", "Scripted baseline, no model", state.route)}
    {option("route", "agent", "Bounded agent, replayed from its trace", state.route)}
  </fieldset>
  <fieldset><legend>Execution mode</legend>
    {option("mode", SIMULATED, "Simulated bench", state.mode)}
    {
        option(
            "mode",
            RECORDED,
            "Recorded sample (synthetic, declared simulated)",
            state.mode,
        )
    }
  </fieldset>
  <fieldset><legend>Sweep</legend>
    {field_("low_hz", "Lowest frequency (Hz)", f"{config.low_hz:g}")}
    {field_("high_hz", "Highest frequency (Hz)", f"{config.high_hz:g}")}
    {field_("amplitude_v", "Amplitude (V, at most 2)", f"{config.amplitude_v:g}")}
    {field_("seed", "Seed of the noise", config.seed)}
  </fieldset>
  <fieldset><legend>Circuit</legend>
    <label><input type="checkbox" name="circuit_confirmed" value="yes"{confirmed}>
      The prepared series RLC circuit is connected. The product never rewires
      it.</label>
  </fieldset>
  <button type="submit">Start the sweep</button>
</form>"""


def _results(state: State, token: str) -> str:
    parts = []
    if state.status == "running":
        count = len(state.points)
        last = state.points[-1].point if count else None
        latest = (
            f" Latest: {last.frequency_hz:.0f} Hz, gain {last.gain:.3f},"
            f" phase {last.phase_deg:.1f} degrees."
            if last
            else ""
        )
        parts.append(
            f'<p class="status">Measuring: {count} points so far.{_e(latest)}</p>'
            f'<form method="post" action="/stop">{_token(token)}<button'
            ' class="stop" type="submit">Stop the instrument</button></form>'
        )
    if state.error:
        parts.append(
            '<div class="failure" role="alert"><p class="status">The run did not'
            f" finish.</p><p>{_e(state.error)}</p><p>Check the configuration"
            " and start the sweep again; a stopped instrument is made anew for"
            " each run.</p></div>"
        )
    result = state.result
    if result is not None:
        parts.append(_finished(result))
    if not parts:
        parts.append(
            "<p>No run yet. Choose a route and a mode, confirm the circuit, and"
            " start the sweep.</p>"
        )
    return "\n".join(parts)


def _finished(result: workflow.Result) -> str:
    check, analysis = result.check, result.analysis
    rows = ""
    verdict = ""
    if check is not None and analysis.f0_hz is not None and analysis.q is not None:
        m = check.metrics
        rows = (
            "<table><thead><tr><th>Quantity</th><th>Measured</th>"
            "<th>Closed form</th><th>Difference</th></tr></thead><tbody>"
            f"<tr><td>f0 (Hz)</td><td>{analysis.f0_hz:.0f}</td>"
            f"<td>{m['reference_f0_hz']:.0f}</td>"
            f"<td>{m['f0_relative_error'] * 100:+.2f} %</td></tr>"
            f"<tr><td>Q</td><td>{analysis.q:.3f}</td><td>{m['reference_q']:.3f}</td>"
            f"<td>{m['q_relative_error'] * 100:+.2f} %</td></tr></tbody></table>"
        )
        klass = "pass" if check.correct else "fail"
        note = check.note[:1].upper() + check.note[1:]
        verdict = f'<p class="verdict {klass}">{_e(note)}.</p>'
    figure_path = result.files.get("figure")
    figure = ""
    if figure_path is not None and figure_path.is_file():
        svg = figure_path.read_text(encoding="utf-8")
        svg = svg[svg.find("<svg") :]
        figure = (
            f'<figure role="img" aria-label="{_e(ALT)}">{svg}<figcaption>Measured'
            " points, recomputed from the raw samples, against the closed form"
            " of the model (dashed). The dotted line marks the estimated"
            " resonance.</figcaption></figure>"
        )
    answer = ""
    if result.candidate_answer is not None:
        answer = (
            '<p class="unverified">The agent said, unverified:'
            f" {_e(result.candidate_answer or '(nothing)')}</p>"
        )
    links = " ".join(
        f'<a href="/files/{name}">{name}</a>'
        for name in EXPORTS
        if (result.out_dir / name).is_file()
    )
    return f"""
<h2>Result of the {_e(result.route)} route</h2>
<p>{_e(len(result.measurements))} points, status {_e(result.status)}.</p>
{rows}{verdict}{answer}{figure}
<p>Exported to {_e(result.out_dir)}: {links}</p>"""


def render(state: State, config: Config, token: str) -> str:
    """The page for ``state``, its forms carrying ``token``."""
    refresh = (
        '<meta http-equiv="refresh" content="1">' if state.status == "running" else ""
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}<title>Autonomous Physics Lab</title><style>{_STYLE}</style></head>
<body>
<header class="mode {_e(state.mode)}"><h1>Autonomous Physics Lab, frequency
response</h1><p>{_e(_MODE_TEXT[state.mode])}</p></header>
<main><section aria-label="Configuration">{_form(state, config, token)}</section>
<section aria-live="polite" aria-label="Progress and results">{_results(state, token)}
</section></main></body></html>
"""


def serve(app: App) -> None:
    """Serve ``app`` on its loopback host and port until interrupted."""
    host, port = check_host(app.host), app.port

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._reply(app.handle("GET", self.path, {}, self._headers()))

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(min(length, 65_536)).decode("utf-8", "replace")
            form = {k: v[0] for k, v in parse_qs(body).items()}
            self._reply(app.handle("POST", self.path, form, self._headers()))

        def _headers(self) -> dict[str, str]:
            return {name.lower(): value for name, value in self.headers.items()}

        def _reply(self, response: Response):
            self.send_response(response.status)
            for name, value in response.headers:
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, format, *args):  # quiet: the page shows progress
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"The Autonomous Physics Lab runs at http://{host}:{port}/ (Ctrl-C stops)")
    try:
        server.serve_forever()
    finally:
        server.server_close()
