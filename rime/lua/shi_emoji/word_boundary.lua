-- Verify both ends of an embedded clue against the surrounding candidate text.
local M = {}
local buckets = setmetatable({}, {__mode = "v"})
local empty = {}

local function lexicon(data, prefix)
  local bucket = buckets[prefix]
  if bucket then return bucket end
  local payload = data.prefixes[prefix]
  if not payload then return empty end
  bucket = {}
  local total = math.log(data.total)
  for suffix, frequency in payload:gmatch("([^ \n]*) (%d+)\n") do
    bucket[suffix] = total - math.log(tonumber(frequency))
  end
  buckets[prefix] = bucket
  return bucket
end

local function han(code)
  return (code >= 0x3400 and code <= 0x9fff)
      or (code >= 0x20000 and code <= 0x323af)
end

local function identifier(code)
  return code and (
      code >= 48 and code <= 57 or code >= 65 and code <= 90 or code >= 97 and code <= 122
      or code >= 0xff10 and code <= 0xff19 or code >= 0xff21 and code <= 0xff3a
      or code >= 0xff41 and code <= 0xff5a or code == 95 or code == 0xff3f)
end

local function separator(code)
  return not code or not (han(code) or identifier(code))
end

local function token_boundaries(text)
  local data = require("shi_emoji.boundary_data")
  local offsets, codes = {}, {}
  for offset, code in utf8.codes(text) do
    offsets[#offsets + 1], codes[#codes + 1] = offset, code
  end
  local last = #codes + 1
  offsets[last] = #text + 1

  local edges, forward, backward = {}, {[1] = 0}, {[last] = 0}
  local log_total = math.log(data.total)
  for start = 1, last - 1 do
    local options = {}
    local code = codes[start]
    if han(code) then
      local suffix_start = offsets[start + 1]
      local words = lexicon(data, text:sub(offsets[start], suffix_start - 1))
      for finish = start + 1, math.min(last, start + data.max_length) do
        if not han(codes[finish - 1]) then break end
        local cost = words[text:sub(suffix_start, offsets[finish] - 1)]
        if cost then
          options[#options + 1] = {finish, cost}
        end
      end
      if not options[1] or options[1][1] ~= start + 1 then
        options[#options + 1] = {start + 1, log_total + 1, true}
      end
    else
      options[1] = {start + 1, 0}
    end
    edges[start] = options
    for _, edge in ipairs(options) do
      local finish, cost = edge[1], forward[start] + edge[2]
      forward[finish] = math.min(forward[finish] or math.huge, cost)
    end
  end
  for start = last - 1, 1, -1 do
    local best = math.huge
    for _, edge in ipairs(edges[start]) do
      best = math.min(best, edge[2] + backward[edge[1]])
    end
    backward[start] = best
  end

  -- An edge on a nearly as likely segmentation can invalidate a boundary.
  -- Unknown Han characters supply no lexical evidence.
  local uncertain = {}
  local max_cost = forward[last] + math.log(2)
  for start, options in ipairs(edges) do
    for _, edge in ipairs(options) do
      local finish, cost, unknown = table.unpack(edge)
      if forward[start] + cost + backward[finish] <= max_cost then
        for i = start + 1, finish - 1 do uncertain[i] = true end
        if unknown then uncertain[start], uncertain[finish] = true, true end
      end
    end
  end
  local verified = {}
  for i, offset in ipairs(offsets) do
    local left, right = codes[i - 1], codes[i]
    verified[offset] = (not uncertain[i] or separator(left) or separator(right))
        and not (identifier(left) and identifier(right))
  end
  return verified
end


local open_quotes = {["“"]="”", ["‘"]="’", ["「"]="」", ["『"]="』",
                     ["《"]="》", ["〈"]="〉", ['"']='"', ["'"]="'"}
local reporting = {"说", "說", "提到", "表示", "声称", "聲稱", "据说", "據說",
                   "听说", "聽說", "转述", "轉述", "引用", "写道", "寫道"}
local sentence_marks = {"。", "！", "？", "；", ".", "!", "?", ";", "\n",
                        "但是", "不过", "不過", "可是", "而是", "然后", "然後"}
local clause_marks = {"，", "、", ","}
local negative_scope = {"没有", "沒有", "不是", "从未", "從未", "未", "未曾", "并非", "並非",
                        "别", "別", "否认", "否認", "从没", "從沒", "不会", "不會", "不能",
                        "不敢", "不曾", "不必", "不许", "不許", "无需", "無需", "无法", "無法"}

local function starts_at(text, offset, words, boundaries)
  for _, word in ipairs(words) do
    if (not boundaries or boundaries[offset + #word])
        and text:sub(offset, offset + #word - 1) == word then return #word end
  end
end

function M.asserted_spans(text, negators)
  local boundaries = token_boundaries(text)
  local quotes, asserted = {}, {}
  local negated, reported, reset_at = false, false, 0
  for offset in utf8.codes(text) do
    local char = text:sub(offset, (utf8.offset(text, 2, offset) or #text + 1) - 1)
    if char == quotes[#quotes] then
      quotes[#quotes] = nil
    elseif open_quotes[char] then
      quotes[#quotes + 1] = open_quotes[char]
    end
    if #quotes == 0 and offset >= reset_at then
      local length = starts_at(text, offset, sentence_marks, boundaries)
      if length then
        reset_at, negated, reported = offset + length, false, false
      elseif starts_at(text, offset, clause_marks) then
        negated = false
      else
        asserted[offset] = not negated and not reported and boundaries[offset]
        if boundaries[offset] then
          negated = negated or starts_at(text, offset, negators, boundaries)
              or starts_at(text, offset, negative_scope, boundaries)
          reported = reported or starts_at(text, offset, reporting, boundaries)
        end
      end
    end
  end
  return function(start, finish)
    return asserted[start] and boundaries[finish]
  end
end

return M
