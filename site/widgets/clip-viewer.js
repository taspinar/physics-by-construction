// Clip viewer: the frames of generated clips, one at a time, for a lesson
// that reads a measurement from a clip (the compass needle of "Measurement
// quality and multimodal observations").
//
// The component does no physics and never plays a clip. The page names a
// file of frames the build generated from a simulation (pbc.electromagnetism
// .needle) in its data-ondemand attribute. The file is loaded from the site's
// own origin only after the reader presses the button, never to read the
// page. Each frame is shown as the file holds it, with its time; the reader
// moves between frames with a slider or two buttons, and chooses the clip
// with radio buttons, so nothing moves by itself and the preference for
// reduced motion holds by construction. The frame takes the box of the static
// figure it replaces, so the page does not move. It uses no storage. The
// words it shows about the clips come from the file.
// Convention: docs/authoring.md, "Widgets" and "On-demand data".

const SCHEMA = "clip-frames-1";

function html(tag, attributes = {}, ...children) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, value);
  }
  element.append(...children);
  return element;
}

// Times are written the same way in every browser language.
function seconds(t) {
  return t.toFixed(3);
}

class ClipViewer {
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
    this.loadLabel = root.dataset.loadLabel || "Load the clips";
    this.fallback = Array.from(this.slot.childNodes);
    this.clip = 0;
    this.index = 0;
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
    this.status.textContent = "Loading the clips from this site.";
    try {
      const response = await fetch(this.url, { credentials: "omit" });
      if (!response.ok) throw new Error(`status ${response.status}`);
      this.data = await response.json();
      if (this.data.schema !== SCHEMA) throw new Error("unknown data version");
      if (!Array.isArray(this.data.clips) || this.data.clips.length === 0) {
        throw new Error("the file holds no clip");
      }
    } catch (error) {
      console.error("clip viewer data not loaded:", error);
      this.status.textContent =
        `The clips could not be loaded. ${this.root.dataset.loadFailed || "The figure above stays as it is."}`;
      this.button.disabled = false;
      return;
    }
    this.build();
  }

  build() {
    // The frame takes the box of the image it replaces, so nothing moves.
    this.frame = html("img", {
      class: `widget-drawing ${this.image.getAttribute("class") ?? ""}`.trim(),
      "aria-describedby": `${this.id}-readout`,
      "data-frame": "",
    });
    const width = Number(this.image.getAttribute("width"));
    const height = Number(this.image.getAttribute("height"));
    if (width > 0 && height > 0) {
      this.frame.setAttribute("width", String(width));
      this.frame.setAttribute("height", String(height));
      this.frame.style.aspectRatio = `${width} / ${height}`;
    }
    this.frame.style.objectFit = "contain";
    this.slot.replaceChildren(this.buildControls());
    this.image.replaceWith(this.frame);
    this.root.classList.remove("widget-offered");
    this.root.classList.add("widget-active");
    this.render();
    this.slider.focus();
  }

  buildControls() {
    const { data } = this;
    const choices = html("div", { class: "widget-choices" });
    data.clips.forEach((clip, i) => {
      const input = html("input", {
        type: "radio",
        name: `${this.id}-clip`,
        id: `${this.id}-clip-${clip.id}`,
        value: String(i),
      });
      input.checked = i === this.clip;
      input.addEventListener("change", () => {
        if (!input.checked) return;
        this.clip = i;
        this.index = 0;
        this.render();
      });
      choices.append(html("label", { for: input.id }, input, clip.title));
    });
    const fieldset = html("fieldset", {}, html("legend", {}, "Clip"), choices);

    const sliderId = `${this.id}-frame`;
    this.slider = html("input", { type: "range", id: sliderId, min: "0", step: "1", value: "0" });
    this.slider.addEventListener("input", () => {
      this.index = Number(this.slider.value);
      this.render();
    });
    const sliderRow = html(
      "div",
      { class: "widget-slider" },
      html("label", { for: sliderId }, "Frame"),
      this.slider,
    );

    this.previous = html("button", { type: "button", id: `${this.id}-previous` }, "Previous frame");
    this.next = html("button", { type: "button", id: `${this.id}-next` }, "Next frame");
    this.previous.addEventListener("click", () => this.step(-1));
    this.next.addEventListener("click", () => this.step(1));
    const steps = html("div", { class: "widget-export" }, this.previous, this.next);

    this.readout = html("dl", { id: `${this.id}-readout`, class: "widget-readout", "aria-live": "polite" });
    this.values = {};
    for (const [quantity, label] of [
      ["clip", "Clip"],
      ["frame", "Frame"],
      ["time", "Time of the frame (s)"],
      ["frame-rate", "Frame rate (frames/s)"],
    ]) {
      this.values[quantity] = html("output", { "data-quantity": quantity });
      this.readout.append(html("dt", {}, label), html("dd", {}, this.values[quantity]));
    }
    const note = html("p", {}, data.label);
    return html("div", { class: "widget-panel" }, fieldset, sliderRow, steps, this.readout, note);
  }

  step(by) {
    const frames = this.data.clips[this.clip].frames;
    this.index = Math.min(frames.length - 1, Math.max(0, this.index + by));
    this.render();
  }

  render() {
    const clip = this.data.clips[this.clip];
    const frame = clip.frames[this.index];
    const count = clip.frames.length;
    const position = `frame ${this.index + 1} of ${count}`;
    this.frame.src = frame.src;
    this.frame.alt = `${clip.alt} ${clip.title}, ${position}, at ${seconds(frame.t)} s.`;
    this.slider.max = String(count - 1);
    this.slider.value = String(this.index);
    this.slider.setAttribute("aria-valuetext", `${position}, ${seconds(frame.t)} s`);
    this.previous.disabled = this.index === 0;
    this.next.disabled = this.index === count - 1;
    this.values.clip.textContent = clip.title;
    this.values.frame.textContent = `${this.index + 1} of ${count}`;
    this.values.time.textContent = seconds(frame.t);
    this.values["frame-rate"].textContent = String(clip.frame_rate);
  }
}

function start(root) {
  try {
    new ClipViewer(root).offer();
  } catch (error) {
    // The static figure and text stay; the page is complete without the widget.
    console.error("clip viewer not started:", error);
  }
}

for (const root of document.querySelectorAll('[data-widget="clip-viewer"]')) {
  start(root);
}
