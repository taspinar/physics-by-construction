-- The lesson constructs of docs/authoring.md that need markup of their own.
--
-- "Not verified" marker: material inside a div or span with the class
-- not-verified did not come through a verified display form (ADR 002). It
-- gets a label in the page itself, so the label is visible without styles or
-- scripts and is read by assistive technology.
--
-- Exercises: a div with the class exercise is numbered in page order. A div
-- with the class solution becomes a closed <details> element, which opens
-- without a script (ADR 001).

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
        count = count + 1
        local number = count
        if el.identifier == "" then
          el.identifier = "exercise-" .. number
        end
        local title = pandoc.Strong({ pandoc.Str("Exercise " .. number .. ".") })
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
              return solution(inner, "Solution to exercise " .. number)
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

return {
  { Pandoc = exercises },
  { Div = not_verified_div, Span = not_verified_span },
}
