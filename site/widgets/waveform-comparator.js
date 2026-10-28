// Waveform comparator: a measured series against model profiles, with the
// error metrics of each, for the figure "measured against model" of a lab.
//
// The component does no physics. The page names a file of results computed
// by pbc when the page was built (pbc.data.comparison) in its
// data-ondemand attribute. The file is loaded from the site's own origin
// only after the reader presses the button, never to read the page. The
// measured samples, the model samples, the residuals, and the metrics are
// drawn and listed exactly as the file holds them: the component never
// changes, smooths, or resamples a value. It enhances the static figure in
// the page: after loading it replaces that image and uses the reserved
// controls slot. It uses no storage and does not animate; the static figure
// is the keyframe of every state it can show. Every word it shows about the
// data (the button, the legend, the metrics and their digits, the slider)
// comes from the file, so that one component serves every lab.
// Convention: docs/authoring.md, "Widgets".

const SVG_NS = "http://www.w3.org/2000/svg";
const SCHEMA = "waveform-comparison-2";

// The drawing is 640 x 520 units, as the static figure's proportions allow.
const WIDTH = 640;
const HEIGHT = 520;
const LEFT = 68;
const RIGHT = 624;
const TOP_PANEL = { top: 24, bottom: 300 };
const RESIDUAL_PANEL = { top: 336, bottom: 456 };
const MEASURED_COLOR = "#1a1a1a";
const MODEL_COLOR = "#b34700";
const WINDOW_FILL = "#005a9c";

function svg(tag, attributes = {}, text) {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, value);
  }
  if (text !== undefined) element.textContent = text;
  return element;
}

function html(tag, attributes = {}, ...children) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, value);
  }
  element.append(...children);
  return element;
}

function scale(domainLow, domainHigh, rangeLow, rangeHigh) {
  return (value) =>
    rangeLow + ((value - domainLow) / (domainHigh - domainLow)) * (rangeHigh - rangeLow);
}

// Numbers are written the same way in every browser language: a metric with
// the number of decimals the file gives it.
function metricFormat(decimals) {
  return (v) => v.toFixed(decimals);
}

// The parameter with its unit, as a label: "chirp mass (solar masses)", or
// the name alone when it has no unit.
function withUnit(parameter) {
  return parameter.unit ? `${parameter.name} (${parameter.unit})` : parameter.name;
}

function niceTicks(low, high) {
  const span = high - low;
  const raw = span / 4;
  const power = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= raw);
  const ticks = [];
  for (let t = Math.ceil(low / step) * step; t <= high + 1e-9; t += step) {
    ticks.push(Number(t.toPrecision(6)));
  }
  return ticks;
}

class WaveformComparator {
  constructor(root) {
    this.root = root;
    this.id = root.id;
    this.image = root.querySelector("img");
    this.slot = root.querySelector(".widget-controls");
    if (!this.image || !this.slot) {
      throw new Error("the static figure or controls slot is missing");
    }
    this.url = new URL(root.dataset.ondemand, document.baseURI);
    if (this.url.origin !== window.location.origin) {
      throw new Error("the data is not on the site's own origin");
    }
    this.selected = 0;
    this.loadLabel = root.dataset.loadLabel || "Compare the models";
    this.fallback = Array.from(this.slot.childNodes);
  }

  // Before the reader asks: one button. Nothing is requested.
  offer() {
    this.status = html("p", { role: "status", class: "widget-status" });
    this.button = html(
      "button",
      { type: "button", id: `${this.id}-load`, "data-loads-ondemand": "" },
      this.loadLabel,
    );
    this.button.addEventListener("click", () => this.load());
    this.slot.replaceChildren(
      html("p", {}, this.fallback.map((n) => n.textContent.trim()).join(" ")),
      this.button,
      this.status,
    );
    this.root.classList.add("widget-offered");
  }

  async load() {
    this.button.disabled = true;
    this.status.textContent = "Loading the data from this site.";
    try {
      const response = await fetch(this.url, { credentials: "omit" });
      if (!response.ok) throw new Error(`status ${response.status}`);
      this.data = await response.json();
      if (this.data.schema !== SCHEMA) throw new Error("unknown data version");
    } catch (error) {
      console.error("waveform comparator data not loaded:", error);
      this.status.textContent =
        `The data could not be loaded. ${this.root.dataset.loadFailed || "The figure above stays as it is."}`;
      this.button.disabled = false;
      return;
    }
    this.build();
  }

  build() {
    const { data } = this;
    this.metrics = data.metrics.map(([key, label, decimals]) => [key, label, metricFormat(decimals)]);
    this.details = data.details ?? [];
    this.hasBest = data.best_parameter !== null && data.best_parameter !== undefined;
    this.best = Math.max(
      0,
      data.models.findIndex((m) => m.parameter === data.best_parameter),
    );
    this.selected = this.hasBest ? this.best : 0;
    const t = data.time;
    this.t0 = t[0];
    this.t1 = t[t.length - 1];
    const spread = (values) => values.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
    this.topRange = 1.05 * Math.max(spread(data.measured), ...data.models.map((m) => spread(m.values)));
    this.residualRange = 1.05 * Math.max(...data.models.map((m) => spread(m.residual)));

    this.drawing = svg("svg", {
      viewBox: `0 0 ${WIDTH} ${HEIGHT}`,
      role: "img",
      "aria-label": data.labels.description,
      "aria-describedby": `${this.id}-readout`,
      class: `widget-drawing ${this.image.getAttribute("class") ?? ""}`.trim(),
    });
    // The drawing takes the box of the image it replaces, so nothing moves.
    const width = Number(this.image.getAttribute("width"));
    const height = Number(this.image.getAttribute("height"));
    if (width > 0 && height > 0) {
      this.drawing.setAttribute("width", String(width));
      this.drawing.setAttribute("height", String(height));
      this.drawing.style.aspectRatio = `${width} / ${height}`;
    }
    this.plot = svg("g");
    this.drawing.append(this.plot);

    this.slot.replaceChildren(this.buildControls());
    this.image.replaceWith(this.drawing);
    this.root.classList.remove("widget-offered");
    this.root.classList.add("widget-active");
    this.render();
    this.slider.focus();
  }

  buildControls() {
    const { data } = this;
    const sliderId = `${this.id}-parameter`;
    this.slider = html("input", {
      type: "range",
      id: sliderId,
      min: "0",
      max: String(data.models.length - 1),
      step: "1",
      value: String(this.selected),
    });
    this.slider.addEventListener("input", () => {
      this.selected = Number(this.slider.value);
      this.render();
    });
    this.parameterLabel = html("output", { for: sliderId, "data-quantity": "parameter" });
    const sliderRow = html(
      "div",
      { class: "widget-slider" },
      html("label", { for: sliderId }, `${data.labels.slider} ${withUnit(data.parameter)}: `, this.parameterLabel),
      this.slider,
    );

    this.readout = html("dl", { id: `${this.id}-readout`, class: "widget-readout", "aria-live": "polite" });
    this.values = {};
    const rows = [
      ...(this.hasBest ? [["best", "Is this the best fit of the page?"]] : []),
      ...this.details,
      ...this.metrics.map(([key, label]) => [key, label]),
    ];
    for (const [key, label] of rows) {
      const output = html("output", { "data-quantity": key });
      this.values[key] = output;
      this.readout.append(html("dt", {}, label), html("dd", {}, output));
    }

    this.exportButton = html("button", { type: "button", id: `${this.id}-export` }, "Show the displayed values as text");
    this.exportButton.addEventListener("click", () => this.toggleExport());
    this.exportText = html("textarea", {
      id: `${this.id}-text`,
      readonly: "",
      rows: "6",
      "aria-label": "The displayed values as tab-separated text",
      hidden: "",
    });
    this.download = html("a", { id: `${this.id}-download`, hidden: "" }, "Download as a text file");
    return html(
      "div",
      { class: "widget-panel", id: `${this.id}-panel` },
      sliderRow,
      this.readout,
      html("div", { class: "widget-export" }, this.exportButton, this.download, this.exportText),
    );
  }

  model() {
    return this.data.models[this.selected];
  }

  // The text of everything shown for the selected model, as the file holds it.
  exportString() {
    const { data } = this;
    const m = this.model();
    const lines = [
      `# ${data.labels.title}`,
      `# ${withUnit(data.parameter)}: ${m.parameter}`,
      ...this.details.map(([key, , exported]) => `# ${exported}: ${m[key]}`),
      ...this.metrics.map(([key, label]) => `# ${label}: ${m.metrics[key]}`),
      `# ${data.labels.window} (s): ${data.window[0]} to ${data.window[1]}`,
      ...(data.labels.notes ?? []).map((note) => `# ${note}`),
      ["time (s)", "measured", "model", "residual"].join("\t"),
    ];
    data.time.forEach((time, i) => {
      lines.push([time, data.measured[i], m.values[i], m.residual[i]].join("\t"));
    });
    return lines.join("\n");
  }

  toggleExport() {
    const shown = this.exportText.hidden;
    this.exportText.hidden = !shown;
    this.download.hidden = !shown;
    this.exportButton.textContent = shown ? "Hide the values as text" : "Show the displayed values as text";
    if (shown) this.refreshExport();
  }

  refreshExport() {
    const text = this.exportString();
    this.exportText.value = text;
    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
    this.objectUrl = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    this.download.setAttribute("href", this.objectUrl);
    const name = String(this.model().parameter).toLowerCase().replace(/[^a-z0-9.]+/g, "-");
    this.download.setAttribute("download", `${this.id}-${name}.txt`);
  }

  render() {
    const { data } = this;
    const m = this.model();
    this.parameterLabel.textContent = String(m.parameter);
    this.slider.setAttribute("aria-valuetext", `${m.parameter} ${data.parameter.unit}`.trim());
    if (this.hasBest) this.values.best.textContent = this.selected === this.best ? "yes" : "no";
    for (const [key] of this.details) {
      this.values[key].textContent = String(m[key]);
    }
    for (const [key, , format] of this.metrics) {
      this.values[key].textContent = format(m.metrics[key]);
    }
    this.root.dataset.parameter = String(m.parameter);
    if (!this.exportText.hidden) this.refreshExport();
    this.draw();
  }

  line(xScale, yScale, values, attributes) {
    const points = this.data.time.map((t, i) => `${xScale(t).toFixed(1)},${yScale(values[i]).toFixed(1)}`);
    return svg("polyline", { fill: "none", points: points.join(" "), ...attributes });
  }

  draw() {
    const { data } = this;
    const m = this.model();
    const xScale = scale(this.t0, this.t1, LEFT, RIGHT);
    const yTop = scale(this.topRange, -this.topRange, TOP_PANEL.top, TOP_PANEL.bottom);
    const yResidual = scale(this.residualRange, -this.residualRange, RESIDUAL_PANEL.top, RESIDUAL_PANEL.bottom);
    const layer = svg("g");
    const text = { fill: "#222", "font-size": "14", "font-family": "sans-serif" };
    const frame = { stroke: "#222", "stroke-width": "1", fill: "none" };

    // The part of the series the models were fitted to.
    const [w0, w1] = data.window;
    for (const box of [TOP_PANEL, RESIDUAL_PANEL]) {
      layer.append(
        svg("rect", {
          x: xScale(Math.max(w0, this.t0)), y: box.top,
          width: xScale(Math.min(w1, this.t1)) - xScale(Math.max(w0, this.t0)),
          height: box.bottom - box.top, fill: WINDOW_FILL, "fill-opacity": "0.1",
        }),
        svg("rect", { ...frame, x: LEFT, y: box.top, width: RIGHT - LEFT, height: box.bottom - box.top }),
      );
    }
    layer.append(
      svg("text", { ...text, x: 16, y: (TOP_PANEL.top + TOP_PANEL.bottom) / 2, "text-anchor": "middle", transform: `rotate(-90 16 ${(TOP_PANEL.top + TOP_PANEL.bottom) / 2})` }, `${data.quantity} (${data.unit})`),
      svg("text", { ...text, x: 16, y: (RESIDUAL_PANEL.top + RESIDUAL_PANEL.bottom) / 2, "text-anchor": "middle", transform: `rotate(-90 16 ${(RESIDUAL_PANEL.top + RESIDUAL_PANEL.bottom) / 2})` }, "residual"),
    );
    for (const value of niceTicks(this.t0, this.t1)) {
      const x = xScale(value);
      layer.append(
        svg("line", { ...frame, x1: x, x2: x, y1: RESIDUAL_PANEL.bottom, y2: RESIDUAL_PANEL.bottom + 5 }),
        svg("text", { ...text, x, y: RESIDUAL_PANEL.bottom + 22, "text-anchor": "middle" }, String(value)),
      );
    }
    layer.append(
      svg("text", { ...text, x: (LEFT + RIGHT) / 2, y: RESIDUAL_PANEL.bottom + 46, "text-anchor": "middle" }, `time (${data.time_unit})`),
    );
    for (const [box, range, y] of [[TOP_PANEL, this.topRange, yTop], [RESIDUAL_PANEL, this.residualRange, yResidual]]) {
      for (const value of niceTicks(-range, range)) {
        layer.append(
          svg("line", { ...frame, x1: LEFT - 5, x2: LEFT, y1: y(value), y2: y(value) }),
          svg("text", { ...text, x: LEFT - 9, y: y(value) + 5, "text-anchor": "end" }, String(value)),
        );
      }
    }

    // The measurement is solid and the model dashed, so that colour is never
    // the only difference. Each polyline holds every sample of the file.
    layer.append(
      this.line(xScale, yTop, data.measured, { stroke: MEASURED_COLOR, "stroke-width": "1.2", "data-series": "measured" }),
      this.line(xScale, yTop, m.values, { stroke: MODEL_COLOR, "stroke-width": "2.2", "stroke-dasharray": "7 4", "data-series": "model" }),
      this.line(xScale, yResidual, m.residual, { stroke: MEASURED_COLOR, "stroke-width": "1", "data-series": "residual" }),
    );
    layer.append(
      svg("line", { x1: LEFT, x2: RIGHT, y1: yResidual(0), y2: yResidual(0), stroke: "#444", "stroke-width": "1", "stroke-dasharray": "1 3" }),
    );
    // Legend inside the upper panel.
    layer.append(
      svg("line", { x1: LEFT + 12, x2: LEFT + 44, y1: TOP_PANEL.top + 14, y2: TOP_PANEL.top + 14, stroke: MEASURED_COLOR, "stroke-width": "1.5" }),
      svg("text", { ...text, x: LEFT + 50, y: TOP_PANEL.top + 19 }, data.labels.measured),
      svg("line", { x1: LEFT + 12, x2: LEFT + 44, y1: TOP_PANEL.top + 36, y2: TOP_PANEL.top + 36, stroke: MODEL_COLOR, "stroke-width": "2.2", "stroke-dasharray": "7 4" }),
      svg("text", { ...text, x: LEFT + 50, y: TOP_PANEL.top + 41 }, `${data.labels.model}${m.parameter}`),
    );
    this.plot.replaceWith(layer);
    this.plot = layer;
  }
}

function start(root) {
  try {
    new WaveformComparator(root).offer();
  } catch (error) {
    // The static figure and text stay; the page is complete without the widget.
    console.error("waveform comparator not started:", error);
  }
}

for (const root of document.querySelectorAll('[data-widget="waveform-comparator"]')) {
  start(root);
}
