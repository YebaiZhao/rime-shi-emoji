-- Select distinct concepts, not several alternatives for the same concept.
local M = {}
function M.suffix(groups, transform)
  table.sort(groups, function(a, b)
    local al, bl = a.finish - a.start, b.finish - b.start
    if al == bl then return a.start < b.start end
    return al > bl
  end)
  local selected, intents, emojis = {}, {}, {}
  for _, group in ipairs(groups) do
    local overlap = false
    for _, other in ipairs(selected) do
      if group.start < other.finish and other.start < group.finish then overlap = true; break end
    end
    local primary = group.suffix or group.emoji[1]
    if not overlap and not intents[group.intent] and not emojis[primary] then
      selected[#selected + 1] = group
      intents[group.intent], emojis[primary] = true, true
      if #selected == 3 then break end
    end
  end
  table.sort(selected, function(a, b) return a.start < b.start end)
  local parts = {}
  transform = transform or function(emoji) return emoji end
  for _, group in ipairs(selected) do
    if group.negated then parts[#parts + 1] = transform("🙅", group.phrase) end
    parts[#parts + 1] = transform(group.suffix or group.emoji[1], group.phrase)
    if #selected == 1 and not group.negated and not group.suffix and group.emoji[2] then
      local second = transform(group.emoji[2], group.phrase)
      if second ~= parts[#parts] then parts[#parts + 1] = second end
    end
  end
  return table.concat(parts, " ")
end
return M
