-- An executed cell without a label gets a random identifier on every build,
-- which would make two builds of the same sources differ. Nothing refers to
-- that identifier, so it is removed. A cell with a label keeps the
-- identifier derived from its label.

function Div(el)
  if el.classes:includes("cell") and el.identifier:match("^%x%x%x%x%x%x%x%x$") then
    el.identifier = ""
    return el
  end
end
