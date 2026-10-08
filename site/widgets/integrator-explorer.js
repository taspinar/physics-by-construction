// Integrator explorer: the interactive form of the figure in the lesson
// "Numerical integrators".
//
// The widget does no physics. The page embeds the runs of all four
// integrators at every offered step count, computed by pbc when the page was
// built (pbc.mechanics.explorer), and the widget draws and reads out the run
// the learner selects. It enhances the static figure that is in the page
// without scripts: it replaces that image and fills the reserved controls
// slot. It makes no request, uses no storage, and does not animate.
// Convention: docs/authoring.md, "Widgets".

const SVG_NS = "http://www.w3.org/2000/svg";

// Four methods that differ by colour, line style and (for the selected one)
// markers, so that colour is never the only difference.
const STYLES = [
  { color: "#b34700", dash: "" },
  { color: "#005a9c", dash: "7 4" },
  { color: "#00734f", dash: "2 4" },
  { color: "#6a3d9a", dash: "9 4 2 4" },
];

// The drawing is 640 x 520 units; the static figure has the same shape.
const WIDTH = 640;
const HEIGHT = 520;
const LEFT = 68;
const RIGHT = 624;
const POSITION_PANEL = { top: 24, bottom: 224 };
const ENERGY_PANEL = { top: 290, bottom: 460 };
const POSITION_RANGE = 1.5; // metres; larger values leave the panel
const DEFAULT_STEPS = 16;

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

// Numbers are written the same way in every browser language.
function formatEnergy(value) {
  return value.toPrecision(4);
}

function formatError(value) {
  return value.toExponential(2);
}

function formatTick(value) {
  const magnitude = Math.abs(value);
  if (magnitude >= 1000 || magnitude < 0.01) return value.toExponential(0);
  return String(Number(value.toPrecision(2)));
}

function scale(domainLow, domainHigh, rangeLow, rangeHigh) {
  return (value) =>
    rangeLow + ((value - domainLow) / (domainHigh - domainLow)) * (rangeHigh - rangeLow);
}

class IntegratorExplorer {
  constructor(root, data) {
    this.root = root;
    this.data = data;
    this.id = root.id;
    this.steps = data.integrators[0].series.map((s) => s.steps_per_period);
    this.selected = 0;
    this.stepIndex = Math.max(0, this.steps.indexOf(DEFAULT_STEPS));
    this.duration = data.n_periods * data.period;
  }

  build() {
    const image = this.root.querySelector("img");
    const controls = this.root.querySelector(".widget-controls");
    if (!image || !controls) throw new Error("the static figure or controls slot is missing");

    this.drawing = svg("svg", {
      viewBox: `0 0 ${WIDTH} ${HEIGHT}`,
      role: "img",
      "aria-label":
        "Position against time and energy against time for four integrators of the harmonic oscillator.",
      "aria-describedby": `${this.id}-readout`,
      class: `widget-drawing ${image.getAttribute("class") ?? ""}`.trim(),
    });
    // The drawing takes the box of the image it replaces, so nothing moves:
    // the width and height the markup reserves, the class that spaces a
    // figure image, and the image's aspect ratio, so that it scales down
    // with the page exactly as the image does. The drawing is fitted
    // inside that box.
    const width = Number(image.getAttribute("width"));
    const height = Number(image.getAttribute("height"));
    if (width > 0 && height > 0) {
      this.drawing.setAttribute("width", String(width));
      this.drawing.setAttribute("height", String(height));
      this.drawing.style.aspectRatio = `${width} / ${height}`;
    }
    this.plot = svg("g");
    this.drawing.append(this.plot);

    controls.replaceChildren(this.buildControls());
    image.replaceWith(this.drawing);
    this.root.classList.add("widget-active");
    this.render();
  }

  buildControls() {
    const name = `${this.id}-integrator`;
    const legend = html("legend", {}, "Integrator (drawn emphasised)");
    const choices = html("div", { class: "widget-choices" });
    this.data.integrators.forEach((integrator, index) => {
      const input = html("input", { type: "radio", name, id: `${name}-${index}`, value: String(index) });
      input.checked = index === this.selected;
      input.addEventListener("change", () => {
        this.selected = index;
        this.render();
      });
      const sample = svg("svg", { viewBox: "0 0 28 8", width: "28", height: "8", "aria-hidden": "true", focusable: "false" });
      sample.append(
        svg("line", {
          x1: "1", y1: "4", x2: "27", y2: "4",
          stroke: STYLES[index].color,
          "stroke-width": "2.5",
          "stroke-dasharray": STYLES[index].dash,
        }),
      );
      choices.append(
        html("label", { for: input.id }, input, sample, html("span", {}, integrator.name)),
      );
    });

    const sliderId = `${this.id}-steps`;
    this.slider = html("input", {
      type: "range",
      id: sliderId,
      min: "0",
      max: String(this.steps.length - 1),
      step: "1",
      value: String(this.stepIndex),
    });
    this.slider.addEventListener("input", () => {
      this.stepIndex = Number(this.slider.value);
      this.render();
    });
    this.stepsLabel = html("output", { for: sliderId, "data-quantity": "steps-per-period" });
    const sliderRow = html(
      "div",
      { class: "widget-slider" },
      html("label", { for: sliderId }, "Steps per period: ", this.stepsLabel),
      this.slider,
    );

    this.readout = html("dl", { id: `${this.id}-readout`, class: "widget-readout", "aria-live": "polite" });
    this.values = {};
    const rows = [
      ["omega-dt", "Step times angular frequency, ω Δt", ""],
      ["energy-ratio", `Energy after ${this.data.n_periods} periods, relative to the start`, ""],
      ["max-error", "Largest position error", " m"],
      ["calls", "Evaluations of the acceleration", ""],
    ];
    for (const [key, label, unit] of rows) {
      const output = html("output", { "data-quantity": key });
      this.values[key] = output;
      this.readout.append(html("dt", {}, label), html("dd", {}, output, unit));
    }
    return html(
      "div",
      { class: "widget-panel" },
      html("fieldset", {}, legend, choices),
      sliderRow,
      this.readout,
    );
  }

  series(integratorIndex) {
    return this.data.integrators[integratorIndex].series[this.stepIndex];
  }

  render() {
    const n = this.steps[this.stepIndex];
    const chosen = this.series(this.selected);
    this.stepsLabel.textContent = String(n);
    this.slider.setAttribute("aria-valuetext", `${n} steps per period`);
    this.values["omega-dt"].textContent = ((this.data.omega * this.data.period) / n).toPrecision(3);
    this.values["energy-ratio"].textContent = formatEnergy(chosen.final_energy);
    this.values["max-error"].textContent = formatError(chosen.max_error);
    this.values.calls.textContent = String(chosen.calls);
    this.root.dataset.integrator = this.data.integrators[this.selected].name;
    this.root.dataset.stepsPerPeriod = String(n);
    this.draw(n);
  }

  draw(n) {
    const clipId = `${this.id}-clip`;
    const xScale = scale(0, this.duration, LEFT, RIGHT);
    const yPosition = scale(POSITION_RANGE, -POSITION_RANGE, POSITION_PANEL.top, POSITION_PANEL.bottom);

    // The energy axis is logarithmic and covers all four runs.
    const logs = this.data.integrators.flatMap((_, index) => this.series(index).e.map(Math.log10));
    let low = Math.min(0, ...logs);
    let high = Math.max(0, ...logs);
    const pad = Math.max(0.02, 0.08 * (high - low));
    low -= pad;
    high += pad;
    const yEnergy = scale(high, low, ENERGY_PANEL.top, ENERGY_PANEL.bottom);

    const layer = svg("g");
    layer.append(
      svg("clipPath", { id: clipId }, undefined),
    );
    layer.firstChild.append(
      svg("rect", { x: LEFT, y: POSITION_PANEL.top, width: RIGHT - LEFT, height: POSITION_PANEL.bottom - POSITION_PANEL.top }),
    );

    this.axes(layer, xScale, yPosition, yEnergy, low, high);

    // Position: the exact motion, then each integrator.
    const exact = this.data.exact;
    layer.append(
      svg("polyline", {
        points: exact.t.map((t, i) => `${xScale(t).toFixed(1)},${yPosition(exact.x[i]).toFixed(1)}`).join(" "),
        fill: "none", stroke: "#444", "stroke-width": "1", "clip-path": `url(#${clipId})`,
      }),
    );
    const dt = this.data.period / n;
    this.data.integrators.forEach((_, index) => {
      const run = this.series(index);
      const emphasised = index === this.selected;
      const style = STYLES[index];
      const common = {
        fill: "none",
        stroke: style.color,
        "stroke-dasharray": style.dash,
        "stroke-width": emphasised ? "2.6" : "1.2",
        "stroke-opacity": emphasised ? "1" : "0.6",
      };
      layer.append(
        svg("polyline", { ...common, "clip-path": `url(#${clipId})`, points: run.x.map((x, i) => `${xScale(i * dt).toFixed(1)},${yPosition(x).toFixed(1)}`).join(" ") }),
        svg("polyline", { ...common, points: run.e.map((e, i) => `${xScale(i * dt).toFixed(1)},${yEnergy(Math.log10(e)).toFixed(1)}`).join(" ") }),
      );
      if (emphasised && n <= 24) {
        run.x.forEach((x, i) => {
          if (Math.abs(x) <= POSITION_RANGE) {
            layer.append(svg("circle", { cx: xScale(i * dt).toFixed(1), cy: yPosition(x).toFixed(1), r: "3", fill: style.color }));
          }
        });
      }
    });

    this.plot.replaceWith(layer);
    this.plot = layer;
  }

  axes(layer, xScale, yPosition, yEnergy, low, high) {
    const text = { fill: "#222", "font-size": "14", "font-family": "sans-serif" };
    const line = { stroke: "#222", "stroke-width": "1", fill: "none" };
    const panels = [
      { box: POSITION_PANEL, label: "position (m)" },
      { box: ENERGY_PANEL, label: "energy / initial energy" },
    ];
    for (const { box, label } of panels) {
      layer.append(svg("rect", { ...line, x: LEFT, y: box.top, width: RIGHT - LEFT, height: box.bottom - box.top }));
      const middle = (box.top + box.bottom) / 2;
      layer.append(svg("text", { ...text, x: 16, y: middle, "text-anchor": "middle", transform: `rotate(-90 16 ${middle})` }, label));
    }
    for (let period = 0; period <= this.data.n_periods; period += 1) {
      const x = xScale(period * this.data.period);
      for (const box of [POSITION_PANEL, ENERGY_PANEL]) {
        layer.append(svg("line", { ...line, x1: x, x2: x, y1: box.bottom, y2: box.bottom + 5 }));
      }
      layer.append(svg("text", { ...text, x, y: ENERGY_PANEL.bottom + 22, "text-anchor": "middle" }, String(period)));
    }
    layer.append(
      svg("text", { ...text, x: (LEFT + RIGHT) / 2, y: ENERGY_PANEL.bottom + 46, "text-anchor": "middle" }, "time (periods)"),
    );
    for (const value of [-1, 0, 1]) {
      const y = yPosition(value);
      layer.append(svg("line", { ...line, x1: LEFT - 5, x2: LEFT, y1: y, y2: y }));
      layer.append(svg("text", { ...text, x: LEFT - 9, y: y + 5, "text-anchor": "end" }, String(value)));
    }
    // Ticks at whole decades when the axis spans two or more; otherwise
    // evenly spaced.
    const exponents = [];
    if (high - low >= 2) {
      for (let e = Math.ceil(low); e <= Math.floor(high); e += 1) exponents.push(e);
    } else {
      for (let tick = 0; tick <= 4; tick += 1) exponents.push(low + ((high - low) * tick) / 4);
    }
    for (const exponent of exponents) {
      const y = yEnergy(exponent);
      layer.append(svg("line", { ...line, x1: LEFT - 5, x2: LEFT, y1: y, y2: y }));
      layer.append(svg("text", { ...text, x: LEFT - 9, y: y + 5, "text-anchor": "end" }, formatTick(10 ** exponent)));
    }
    // The reference level of the energy panel: no change.
    layer.append(
      svg("line", { x1: LEFT, x2: RIGHT, y1: yEnergy(0), y2: yEnergy(0), stroke: "#444", "stroke-width": "1", "stroke-dasharray": "1 3" }),
    );
  }
}

function start(root) {
  const source = document.getElementById(`${root.id}-data`);
  if (!source) return;
  try {
    new IntegratorExplorer(root, JSON.parse(source.textContent)).build();
  } catch (error) {
    // The static figure and text stay; the page is complete without the widget.
    console.error("integrator explorer not started:", error);
  }
}

for (const root of document.querySelectorAll('[data-widget="integrator-explorer"]')) {
  start(root);
}
