local matcher = require("shi_emoji.matcher")
local compose = require("shi_emoji.compose")
local variants = require("shi_emoji.variants")
local settings = require("shi_emoji.settings")
local entry_data = require("shi_emoji.entry_data")
local M = {}
local adult_index
local tier_index

function M.current_suffix(text, env)
  return M.suffix(text, env.settings, settings.tier(env.engine.context))
end

function M.init(env)
  env.settings = settings.load(env.engine.schema.config)
  env.candidate_slot = env.engine.schema.config:get_bool("shi_emoji/candidate_slot")
  env.zero_key = env.engine.schema.config:get_bool("shi_emoji/zero_key")
  env.page_size = env.engine.schema.config:get_int("menu/page_size") or 6
  env.preview_update = env.engine.context.update_notifier:connect(function(context)
    if env.preview_target then
      env.preview_target.comment = env.preview_original_comment
      env.preview_target = nil
      env.preview_original_comment = nil
    end
    if env.preview_segment then
      local segment = env.preview_segment
      local prompt = segment.prompt or ""
      local suffix = env.preview_prompt
      if prompt:sub(-#suffix) == suffix then
        segment.prompt = prompt:sub(1, #prompt - #suffix)
      end
      env.preview_segment = nil
      env.preview_prompt = nil
    end
    if not context:get_option("shi_emoji") or context:get_option("ascii_mode") then return end
    local candidate = context:get_selected_candidate()
    if env.candidate_slot then
      if not candidate then return end
      local segment = context.composition:back()
      if not segment then return end
      local page = math.floor(segment.selected_index / env.page_size) + 1
      segment.menu:get_candidate_at(page * env.page_size - 1)
      local slot = env.slots and env.slots[page]
      if not slot then return end
      if candidate ~= slot.candidate then slot.source = candidate end
      local source = slot.source
      if not M.eligible(source, context) then return end
      local suffix = M.current_suffix(source.text, env)
      slot.candidate.text = suffix or source.text
      slot.candidate.comment = suffix and "诗Emoji" or "诗Emoji · 当前词无联想"
      return
    end
    if not M.eligible(candidate, context) then return end
    local suffix = M.current_suffix(candidate.text, env)
    if not suffix then return end
    local preview = (env.zero_key and " 〔0→" or " 〔诗Emoji ") .. suffix .. "〕"
    local original = candidate.comment or ""
    candidate.comment = original .. preview
    if candidate.comment == original .. preview then
      env.preview_target = candidate
      env.preview_original_comment = original
      return
    end
    local genuine = candidate:get_genuine()
    local genuine_comment = genuine.comment or ""
    genuine.comment = genuine_comment .. preview
    if candidate.comment == original .. preview then
      env.preview_target = genuine
      env.preview_original_comment = genuine_comment
      return
    end
    genuine.comment = genuine_comment
    local segment = context.composition:back()
    segment.prompt = (segment.prompt or "") .. preview
    env.preview_segment = segment
    env.preview_prompt = preview
  end)
end

function M.fini(env)
  env.preview_update:disconnect()
end

function M.eligible(candidate, context)
  return candidate and candidate.start == 0 and candidate._end == #context.input
      and candidate.text:find("[\228-\233]") ~= nil
end

function M.suffix(text, settings, tier)
  tier = tier or 2
  tier_index = tier_index or matcher.tiered(require("shi_emoji.match_metadata"), require("shi_emoji.tier_data"))
  local index = tier_index
  local _, groups = matcher.search(index, text, 6, tier)
  -- Entry repair is an exact-candidate lookup. It must not add trie words or
  -- guards: those would change the existing behavior inside sentences.
  local entry = entry_data[text]
  if entry and tier >= entry.min_tier then
    local targets, level = {}, nil
    for _, relation in ipairs(entry.targets) do
      if relation[2] <= tier then
        targets[#targets + 1] = relation[1]
        level = level or relation[2]
      end
    end
    groups = {{start=1, finish=#text+1, phrase=text, intent=text,
               emoji=targets, level=level}}
  end
  if tier == 3 and settings.adult then
    if not adult_index then
      local adult = require("shi_emoji.adult")
      adult_index = matcher.with_guard({rules = adult.rules,
                                       boundaries = adult.boundaries, negators = adult.negators}, index)
    end
    local _, extra = matcher.search(adult_index, text, 6)
    local function whole(group)
      return group.start == 1 and group.finish == #text + 1
    end
    local ordinary_whole = false
    for _, group in ipairs(groups) do ordinary_whole = ordinary_whole or whole(group) end
    for _, group in ipairs(extra) do
      group.level = 3
      if whole(group) then
        if not ordinary_whole then
          groups = {group}
          break
        end
      else
        groups[#groups + 1] = group
      end
    end
  end
  if #groups == 0 then return nil end
  return compose.suffix(groups, function(emoji, phrase)
    return variants.apply(emoji, phrase, settings)
  end)
end

function M.func(translation, env)
  local context = env.engine.context
  if not env.candidate_slot or not context:get_option("shi_emoji")
      or context:get_option("ascii_mode") then
    for candidate in translation:iter() do yield(candidate) end
    return
  end
  env.slots = {}
  local rows = {}
  local page = 1
  local function emit_page()
    local source
    for i = 1, math.min(#rows, env.page_size - 1) do
      if M.eligible(rows[i], context) and M.current_suffix(rows[i].text, env) then
        source = rows[i]
        break
      end
    end
    if source then
      for i = 1, math.min(#rows, env.page_size - 1) do yield(rows[i]) end
      local suffix = M.current_suffix(rows[1].text, env)
      local text = suffix or rows[1].text
      local slot = Candidate("shi_emoji", 0, #context.input, text,
          suffix and "诗Emoji" or "诗Emoji · 当前词无联想")
      env.slots[page] = {candidate = slot, source = rows[1]}
      yield(slot)
      rows = rows[env.page_size] and {rows[env.page_size]} or {}
    else
      for _, candidate in ipairs(rows) do yield(candidate) end
      rows = {}
    end
    page = page + 1
  end
  for candidate in translation:iter() do
    rows[#rows + 1] = candidate
    if #rows == env.page_size then emit_page() end
  end
  if #rows > 0 then emit_page() end
end

return M
