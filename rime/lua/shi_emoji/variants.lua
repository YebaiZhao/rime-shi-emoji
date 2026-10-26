local data = require('shi_emoji.variant_data')
local M = {}
local skin_names = {'light','medium_light','medium','medium_dark','dark'}
local function norm(s) return (s:gsub('️','')) end
function M.apply(emoji, phrase, context)
  local entry = data[norm(emoji)]
  if not entry then return emoji end
  local gender = 'neutral'
  -- Explicit wording wins over defaults. Existing gender stays untouched.
  local explicit = false
  for _, word in ipairs({'女','男','妈妈','爸爸','母亲','父亲','姐姐','哥哥','妹妹','弟弟','老公','老婆','女士','先生','妻','夫'}) do
    if phrase:find(word,1,true) then explicit = true; break end
  end
  if explicit then
    local tone = '0'
    for i,name in ipairs(skin_names) do if context:get_option('shi_emoji_skin_'..name) then tone=tostring(i); break end end
    for _, family in pairs(entry) do
      if norm(family['0']) == norm(emoji) then return family[tone] or emoji end
    end
    return emoji
  end
  for _, name in ipairs({'female','male'}) do
    if context:get_option('shi_emoji_gender_'..name) then gender=name; break end
  end
  local family = entry[gender] or entry.neutral
  if not family then return emoji end
  local tone = '0'
  for i,name in ipairs(skin_names) do if context:get_option('shi_emoji_skin_'..name) then tone=tostring(i); break end end
  return family[tone] or family['0']
end
return M
