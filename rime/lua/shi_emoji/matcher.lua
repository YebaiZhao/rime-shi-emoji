-- MIT. Match Chinese candidate text; no shell, network, or model calls.
local M = {}
function M.new(data)
  local root = {}
  for _, rule in ipairs(data.rules) do
    for _, phrase in ipairs(rule.phrases) do
      local node = root
      for i = 1, #phrase do
        local byte = phrase:sub(i, i)
        node[byte] = node[byte] or {}
        node = node[byte]
      end
      node.rule = rule
    end
  end
  local guard_root = {}
  for _, word in ipairs(data.word_guards or {}) do
    local node = guard_root
    for i = 1, #word do
      local byte = word:sub(i, i)
      node[byte] = node[byte] or {}
      node = node[byte]
    end
    node.terminal = true
  end
  return {root = root, data = data, guard_root = guard_root}
end

function M.search(index, text, limit)
  local result, scores, position, groups = {}, {}, 1, {}
  local text_length = utf8.len(text)
  local guards, start = {}, 1
  while start <= #text do
    local node, finish = index.guard_root, start
    while finish <= #text and node[text:sub(finish, finish)] do
      node = node[text:sub(finish, finish)]
      finish = finish + 1
      if node.terminal then guards[#guards + 1] = {start, finish} end
    end
    start = utf8.offset(text, 2, start) or (#text + 1)
  end
  local function protected(a, b)
    for _, span in ipairs(guards) do
      if span[1] <= a and b <= span[2] and (span[1] ~= a or b ~= span[2]) then return true end
    end
    return false
  end
  while position <= #text do
    local left, boundary = text:sub(1, position - 1), 1
    for _, mark in ipairs(index.data.boundaries) do
      local start = 1
      while true do
        local a, b = left:find(mark, start, true)
        if not a then break end
        boundary = math.max(boundary, b + 1)
        start = b + 1
      end
    end
    left = left:sub(boundary)
    local length = utf8.len(left)
    if length > 4 then left = left:sub(utf8.offset(left, length - 3)) end
    local negated = false
    for _, word in ipairs(index.data.negators) do
      if left:find(word, 1, true) then negated = true; break end
    end
    local node, finish = index.root, position
    while finish <= #text and node[text:sub(finish, finish)] do
      node = node[text:sub(finish, finish)]
      finish = finish + 1
      if node.rule and (not node.rule.min_context_len
          or text_length >= node.rule.min_context_len)
          and not protected(position, finish)
          and (not node.rule.exact_only or (position == 1 and finish == #text + 1)) then
        local found, phrase = node.rule, text:sub(position, finish - 1)
        groups[#groups + 1] = {start = position, finish = finish, phrase = phrase,
          intent = found.id, emoji = found.emoji, suffix = found.suffix, negated = negated}
        for rank, emoji in ipairs(found.emoji) do
          local score = utf8.len(phrase) * 100 + 21 - rank + (found.priority or 0)
          if not scores[emoji] or score > scores[emoji].score
              or (score == scores[emoji].score and scores[emoji].negated and not negated) then
            scores[emoji] = {emoji = emoji, score = score, phrase = phrase, intent = found.id,
                            suffix = found.suffix, negated = negated}
          end
        end
      end
    end
    -- Scan every character boundary so a long phrase cannot hide an overlapping one.
    position = utf8.offset(text, 2, position) or (#text + 1)
  end
  for _, row in pairs(scores) do result[#result + 1] = row end
  table.sort(result, function(a, b)
    if a.score == b.score then return a.emoji < b.emoji end
    return a.score > b.score
  end)
  while #result > (limit or 6) do table.remove(result) end
  return result, groups
end
return M
