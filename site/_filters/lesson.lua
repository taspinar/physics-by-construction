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
-- not take a number, so the exercises keep theirs. A div with the class hint
-- inside an exercise becomes a closed <details> element titled "Hint k of n
-- for exercise N", in the order written, before the solution. The lesson
-- source check keeps hints before the solution and free of computed numbers.
--
-- A self-check may hold choices (see "Choices of a self-check" below).
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

local function details(class, el, summary)
  local blocks = pandoc.List({
    pandoc.RawBlock("html", '<details class="' .. class .. '">'),
    pandoc.RawBlock("html", "<summary>" .. summary .. "</summary>"),
  })
  blocks:extend(el.content)
  blocks:insert(pandoc.RawBlock("html", "</details>"))
  return blocks
end

local function solution(el, summary)
  return details("solution", el, summary)
end

local function count_hints(el)
  local total = 0
  el:walk({
    Div = function(inner)
      if inner.classes:includes("hint") then
        total = total + 1
      end
    end,
  })
  return total
end

-- The controls of a self-check are declared as an enhancement of the page
-- (an element with an id and the attribute data-enhancement), so that what the
-- script of the site adds is not required content and what the page has
-- without it stands in the element. With choices, the element holds the list
-- of choices, which the script turns into radio buttons. Without, it holds a
-- sentence, before the solution, and the script puts the button there.
local function self_check_controls(content)
  local attr = pandoc.Attr("self-check-controls", {}, { { "data-enhancement", "" } })
  for index, block in ipairs(content) do
    if block.t == "Div" and block.classes:includes("choices") then
      content[index] = pandoc.Div({ block }, attr)
      return content
    end
  end
  local sentence = pandoc.read(
    "With scripts, you can record in this browser that you answered this question.",
    "markdown"
  ).blocks[1]
  local controls = pandoc.Div({ sentence }, attr)
  for index, block in ipairs(content) do
    if block.t == "Div" and block.classes:includes("solution") then
      content:insert(index, controls)
      return content
    end
  end
  content:insert(controls)
  return content
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
        if self_check then
          el.content = self_check_controls(el.content)
        end
        local hints = count_hints(el)
        local hint_number = 0
        el = el:walk({
          Div = function(inner)
            if inner.classes:includes("solution") then
              return solution(inner, "Solution to " .. name)
            elseif inner.classes:includes("hint") then
              hint_number = hint_number + 1
              return details("hint", inner, "Hint " .. hint_number .. " of " .. hints .. " for " .. name)
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

-- Choices of a self-check: a div with the class choices holds two or more
-- divs with the class choice, one of them with correct="true", each with a
-- div with the class feedback. It becomes an ordered list that reads on its
-- own: the question, the options, and what each option means. The script of
-- the site (learner/progress.js) turns it into radio buttons with immediate
-- feedback; without the script the closed solution of the self-check is the
-- way to the answer. The build fails on a malformed list.
local function choices(el)
  if not el.classes:includes("choices") then
    return nil
  end
  local items = pandoc.List()
  for _, block in ipairs(el.content) do
    if block.t == "Div" and block.classes:includes("choice") then
      items:insert(block)
    end
  end
  if #items < 2 or #items ~= #el.content then
    error("choices holds " .. #items .. " choice divs among " .. #el.content .. " blocks; it needs two or more and nothing else")
  end
  local correct = 0
  local blocks = pandoc.List({ pandoc.RawBlock("html", '<ol class="choices">') })
  for _, item in ipairs(items) do
    local right = item.attributes["correct"] == "true"
    if right then
      correct = correct + 1
    end
    local has_feedback = false
    item.content:walk({
      Div = function(inner)
        if inner.classes:includes("feedback") then
          has_feedback = true
        end
      end,
    })
    if not has_feedback then
      error("a choice has no feedback div")
    end
    blocks:insert(pandoc.RawBlock("html", '<li class="choice" data-correct="' .. tostring(right) .. '">'))
    blocks:extend(item.content)
    blocks:insert(pandoc.RawBlock("html", "</li>"))
  end
  if correct ~= 1 then
    error("choices has " .. correct .. " correct choices; it needs exactly one")
  end
  blocks:insert(pandoc.RawBlock("html", "</ol>"))
  return blocks
end

local function div(el)
  if el.classes:includes("claim") then
    return claim_div(el)
  elseif el.classes:includes("choices") then
    return choices(el)
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
