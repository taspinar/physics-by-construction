-- Wide display equations and code blocks scroll sideways inside their own box
-- on a narrow screen instead of widening the page. A box that scrolls must be
-- reachable by keyboard (WCAG 2.1, 2.1.1), so each one becomes focusable.

function Math(el)
  if el.mathtype == "DisplayMath" then
    return pandoc.Span({ el }, pandoc.Attr("", { "display-math" }, { tabindex = "0" }))
  end
end

function CodeBlock(el)
  el.attributes["tabindex"] = "0"
  return el
end
