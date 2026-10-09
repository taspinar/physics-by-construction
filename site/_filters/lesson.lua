-- The lesson constructs of docs/authoring.md that need markup of their own.
--
-- "Not verified" marker: material inside a div or span with the class
-- not-verified did not come through a verified display form (ADR 002). It
-- gets a label in the page itself, so the label is visible without styles or
-- scripts and is read by assistive technology.
--
-- Exercises: a div with the class exercise is numbered in page order. A div
-- with the class solution becomes a closed <details> element, which opens
-- without a script (ADR 001). A div with the classes exercise and self-check
-- is the self-check of a format 2 lesson: it is titled "Self-check." and does
-- not take a number, so the exercises keep theirs.
--
-- Format 2 (docs/authoring.md): a span or div with the class claim and a
-- type attribute gets a visible label naming the type; a cell with a
-- fig-status option gets a status label that opens the caption; a div
-- with the class go-deeper and a ref attribute is rendered from the entry of
-- that key in site/references.yaml. Every label is plain text in the page.

local NOT_VERIFIED = "not-verified"
local LABEL = "not-verified-label"

local function not_verified_div(el)
  if not el.classes:includes(NOT_VERIFIED) then
    return nil
  end
  local label = pandoc.Para({
    pandoc.Strong({ pandoc.Str("Not verified.") }),
    pandoc.Space(),
    pandoc.Str("The build of this site did not run or check the material in this box."),
  })
  el.content:insert(1, pandoc.Div({ label }, pandoc.Attr("", { LABEL })))
  el.attributes["role"] = "note"
  return el
end

local function not_verified_span(el)
  if not el.classes:includes(NOT_VERIFIED) then
    return nil
  end
  el.content:insert(pandoc.Space())
  el.content:insert(pandoc.Span({ pandoc.Str("(not verified)") }, pandoc.Attr("", { LABEL })))
  return el
end

local function solution(el, summary)
  local blocks = pandoc.List({
    pandoc.RawBlock("html", '<details class="solution">'),
    pandoc.RawBlock("html", "<summary>" .. summary .. "</summary>"),
  })
  blocks:extend(el.content)
  blocks:insert(pandoc.RawBlock("html", "</details>"))
  return blocks
end

local function exercises(doc)
  local count = 0
  return doc:walk({
    traverse = "topdown",
    Div = function(el)
      if el.classes:includes("exercise") then
        local self_check = el.classes:includes("self-check")
        local number = "self-check"
        local name = "the self-check"
        local label = "Self-check."
        if not self_check then
          count = count + 1
          number = count
          name = "exercise " .. number
          label = "Exercise " .. number .. "."
        end
        if el.identifier == "" then
          el.identifier = self_check and "self-check" or ("exercise-" .. number)
        end
        local title = pandoc.Strong({ pandoc.Str(label) })
        local first = el.content[1]
        if first and (first.t == "Para" or first.t == "Plain") then
          first.content:insert(1, pandoc.Space())
          first.content:insert(1, title)
        else
          el.content:insert(1, pandoc.Para({ title }))
        end
        el = el:walk({
          Div = function(inner)
            if inner.classes:includes("solution") then
              return solution(inner, "Solution to " .. name)
            end
          end,
        })
        return el
      elseif el.classes:includes("solution") then
        -- Outside an exercise there is no number to name; the lesson source
        -- check reports this case.
        return solution(el, "Solution")
      end
    end,
  })
end

local CLAIM_TYPES = {
  ["observational"] = "Observational",
  ["experimentally-supported"] = "Experimentally supported",
  ["numerically-verified"] = "Numerically verified",
  ["formal-theorem"] = "Formal theorem",
}

-- A claim is written with a type attribute. The label is a span with the
-- class claim and a data-type attribute (site.css colours it); its words
-- name the type, so the label reads without styles. An element written
-- with data-type and no type is a finished label and is left alone.
local function claim_label(el)
  local kind = el.attributes["type"]
  if kind == nil then
    return nil
  end
  local name = CLAIM_TYPES[kind]
  if name == nil then
    error("claim with unknown type '" .. tostring(kind) .. "'")
  end
  local scope = el.attributes["scope"]
  local text = name
  if scope ~= nil and scope ~= "" then
    text = text .. " (" .. scope .. ")"
  end
  el.attributes["data-evidence"] = el.attributes["evidence"]
  el.attributes["type"] = nil
  el.attributes["scope"] = nil
  el.attributes["evidence"] = nil
  el.classes = pandoc.List({ "claim-statement" })
  local label = pandoc.Span({ pandoc.Str(text) }, pandoc.Attr("", { "claim" }, { { "data-type", kind } }))
  return label
end

local function claim_span(el)
  if not el.classes:includes("claim") then
    return nil
  end
  local label = claim_label(el)
  if label == nil then
    return nil
  end
  el.content:insert(1, pandoc.Space())
  el.content:insert(1, pandoc.Str(":"))
  el.content:insert(1, label)
  return el
end

local function claim_div(el)
  local label = claim_label(el)
  if label == nil then
    return nil
  end
  el.classes = pandoc.List({ "claim" })
  el.attributes["data-type"] = label.attributes["data-type"]
  local first = el.content[1]
  if first and (first.t == "Para" or first.t == "Plain") then
    first.content:insert(1, pandoc.Space())
    first.content:insert(1, pandoc.Str(":"))
    first.content:insert(1, label)
  else
    el.content:insert(1, pandoc.Para({ label, pandoc.Str(":") }))
  end
  return el
end

local FIGURE_STATUSES = {
  measured = true,
  calibrated = true,
  processed = true,
  simulated = true,
  conceptual = true,
}

-- The status opens the caption of the figure as a span with the class
-- figure-status, which site.css colours. The words are the status itself.
local function figure_status(el)
  local status = el.attributes["fig-status"]
  if status == nil then
    return nil
  end
  if not FIGURE_STATUSES[status] then
    error("figure with unknown status '" .. status .. "'")
  end
  el.attributes["fig-status"] = nil
  local label = pandoc.Span({ pandoc.Str(status) }, pandoc.Attr("", { "figure-status" }, { { "data-status", status } }))
  return el:walk({
    Figure = function(figure)
      local caption = figure.caption.long[1]
      if caption ~= nil then
        caption.content:insert(1, pandoc.Space())
        caption.content:insert(1, label)
      end
      return figure
    end,
  })
end

-- The register is YAML. Pandoc has no YAML reader of its own, but it reads a
-- YAML block as metadata, which is all that is needed: the fields used here
-- are plain text. Smart punctuation and raw HTML are switched off so that a
-- title or a URL reaches the page as it was written.
local register = nil

local function load_register()
  if register ~= nil then
    return register
  end
  local root = os.getenv("QUARTO_PROJECT_DIR") or "."
  local file = io.open(root .. "/references.yaml", "r")
  if file == nil then
    error("site/references.yaml not found from " .. root)
  end
  local text = file:read("a")
  file:close()
  local meta = pandoc.read("---\n" .. text .. "\n---\n", "markdown-smart-raw_html-tex_math_dollars").meta
  register = {}
  for _, entry in ipairs(meta.references or {}) do
    local record = {}
    for name, value in pairs(entry) do
      record[name] = pandoc.utils.stringify(value)
    end
    register[record.key] = record
  end
  return register
end

local ROLES = {
  intuition = "intuition",
  derivation = "derivation",
  figure = "figure",
  api = "API documentation",
  paper = "paper",
  advanced = "advanced",
}

local function go_deeper(el)
  local key = el.attributes["ref"]
  if not el.classes:includes("go-deeper") or key == nil then
    return nil
  end
  local entry = load_register()[key or ""]
  if entry == nil then
    error("go-deeper names the key '" .. tostring(key) .. "', which is not in the register")
  end
  local byline = entry.author .. ", " .. entry.section .. "; " .. (ROLES[entry.role] or entry.role) .. "."
  local line = pandoc.Para({
    pandoc.Strong({ pandoc.Str("Go deeper:") }),
    pandoc.Space(),
    pandoc.Link({ pandoc.Str(entry.title) }, entry.url),
    pandoc.Space(),
    pandoc.Str("(" .. byline .. ")"),
  })
  el.content:insert(1, line)
  el.attributes["ref"] = nil
  el.attributes["data-reference"] = key
  return el
end

local function div(el)
  if el.classes:includes("claim") then
    return claim_div(el)
  elseif el.classes:includes("go-deeper") then
    return go_deeper(el)
  elseif el.classes:includes("cell") then
    return figure_status(el)
  end
  return not_verified_div(el)
end

return {
  { Pandoc = exercises },
  { Div = div, Span = function(el) return claim_span(el) or not_verified_span(el) end },
}
