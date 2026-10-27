local matcher = require("shi_emoji.matcher")
local compose = require("shi_emoji.compose")
local variants = require("shi_emoji.variants")
local settings = require("shi_emoji.settings")
local M = {}
local shared_index
local adult_index

function M.init(env)
  env.index = shared_index
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
      local suffix = M.suffix(source.text, env.settings)
      slot.candidate.text = suffix or source.text
      slot.candidate.comment = suffix and "诗Emoji" or "诗Emoji · 当前词无联想"
      return
    end
    if not M.eligible(candidate, context) then return end
    local normal = M.suffix(candidate.text, env.settings)
    local adult = env.settings.adult and M.suffix(candidate.text, env.settings, true)
    if not normal and not adult then return end
    local preview = ""
    if normal then
      preview = preview .. (env.zero_key and " 〔0 → " .. normal .. "〕"
          or " 〔诗Emoji " .. normal .. "〕")
    end
    if adult then preview = preview .. " 〔重口 " .. adult .. "〕" end
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

function M.suffix(text, settings, adult)
  local index
  if adult then
    adult_index = adult_index or matcher.new(require("shi_emoji.adult"))
    index = adult_index
  else
    shared_index = shared_index or matcher.new(require("shi_emoji.data"))
    index = shared_index
  end
  local rows, groups = matcher.search(index, text, 6)
  if #rows == 0 then return nil end
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
      if M.eligible(rows[i], context) and M.suffix(rows[i].text, env.settings) then
        source = rows[i]
        break
      end
    end
    if source then
      for i = 1, math.min(#rows, env.page_size - 1) do yield(rows[i]) end
      local suffix = M.suffix(rows[1].text, env.settings)
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
