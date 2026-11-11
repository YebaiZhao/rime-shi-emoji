-- MIT. Match Chinese candidate text; no shell, network, or model calls.
local M = {}
local function new(data, guard_root, guard_index)
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
  if not guard_root and not guard_index then
    guard_root = {}
    for _, word in ipairs(data.word_guards or {}) do
      local node = guard_root
      for i = 1, #word do
        local byte = word:sub(i, i)
        node[byte] = node[byte] or {}
        node = node[byte]
      end
      node.terminal = true
    end
  end
  return {root = root, data = data, guard_root = guard_root, guard_index = guard_index}
end

function M.new(data)
  return new(data)
end

local function tiered(data, entries, shared)
  local rules = {}
  local guards = {}
  local guard_index = shared and shared.guard_index or data.guard_index
  if not shared and not guard_index then
    for _, word in ipairs(data.word_guards or {}) do guards[#guards + 1] = word end
  end
  for phrase, relations in pairs(entries) do
    rules[#rules + 1] = {id = phrase, phrases = {phrase}, relations = relations}
    if not shared and not guard_index then
      local sentence = false
      for _, relation in ipairs(relations) do sentence = sentence or relation[3] == true end
      if not sentence then guards[#guards + 1] = phrase end
    end
  end
  return new({rules = rules, word_guards = guards,
              boundaries = data.boundaries, negators = data.negators}, shared and shared.guard_root, guard_index)
end

function M.tiered(data, entries)
  return tiered(data, entries)
end

function M.tiered_extension(index, entries)
  return tiered(index.data, entries, index)
end

local function tier_rule(rule, tier, exact, eligible, start, finish)
  if not rule.relations then return rule end
  local found = {id = rule.id, emoji = {}}
  for _, entry in ipairs(rule.relations) do
    local target, level, scope, sequence = table.unpack(entry)
    if level <= tier and (exact or scope and eligible(scope, start, finish)) then
      if not found.level then
        found.level = level
        found.legacy_negation = scope == true and not exact
        if sequence then found.suffix = target end
      end
      found.emoji[#found.emoji + 1] = target
    end
  end
  if found.level then return found end
end

local function packed_step(index, node, label)
  local first, last = string.unpack("<I3I3", index.offsets, node * 3 + 1)
  local low, high = first & 0x7fffff, (last & 0x7fffff) - 1
  while low <= high do
    local mid = (low + high) // 2
    local edge = string.unpack("<I5", index.edges, mid * 5 + 1)
    local code = edge & 0x1fffff
    if code == label then return edge >> 21 end
    if code < label then low = mid + 1 else high = mid - 1 end
  end
end

local function guard_spans(index, text)
  local guards, start = {}, 1
  local packed = index.guard_index
  while start <= #text do
    if packed then
      local node = 0
      local finish = start
      while finish <= #text do
        node = packed_step(packed, node, utf8.codepoint(text, finish))
        if not node then break end
        finish = utf8.offset(text, 2, finish) or (#text + 1)
        if packed.offsets:byte(node * 3 + 3) >= 128 then
          guards[#guards + 1] = {start, finish}
        end
      end
    else
      local node, finish = index.guard_root, start
      while finish <= #text and node[text:sub(finish, finish)] do
        node = node[text:sub(finish, finish)]
        finish = finish + 1
        if node.terminal then guards[#guards + 1] = {start, finish} end
      end
    end
    start = utf8.offset(text, 2, start) or (#text + 1)
  end
  return guards
end

function M.search(index, text, limit, tier)
  local result, scores, position, groups = {}, {}, 1, {}
  local text_length = utf8.len(text)
  local guards = guard_spans(index, text)
  local function protected(a, b)
    for _, span in ipairs(guards) do
      if span[1] <= a and b <= span[2] and (span[1] ~= a or b ~= span[2]) then return true end
    end
    return false
  end
  local asserted_spans
  local function eligible(scope, start, finish)
    if protected(start, finish) then return false end
    if scope == true then return true end
    if not asserted_spans then
      local boundary = require("shi_emoji.word_boundary")
      asserted_spans = boundary.asserted_spans(text, index.data.negators)
    end
    return asserted_spans(start, finish)
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
      local exact = position == 1 and finish == #text + 1
      local found = node.rule and tier_rule(node.rule, tier, exact, eligible, position, finish)
      if found and (not found.min_context_len
          or text_length >= found.min_context_len)
          and (found.level or not protected(position, finish))
          and (not found.exact_only or exact) then
        local phrase = text:sub(position, finish - 1)
        local group_negated = negated and (not found.level or found.legacy_negation)
        groups[#groups + 1] = {start = position, finish = finish, phrase = phrase,
          intent = found.id, emoji = found.emoji, suffix = found.suffix, negated = group_negated,
          level = found.level}
        for rank, emoji in ipairs(found.emoji) do
          local score = utf8.len(phrase) * 100 + 21 - rank + (found.priority or 0)
          if not scores[emoji] or score > scores[emoji].score
              or (score == scores[emoji].score and scores[emoji].negated and not group_negated) then
            scores[emoji] = {emoji = emoji, score = score, phrase = phrase, intent = found.id,
                            suffix = found.suffix, negated = group_negated}
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
