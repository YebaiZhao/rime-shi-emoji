local data = require('shi_emoji.variant_data')
local M = {}
local tones = {default='0', light='1', medium_light='2', medium='3',
  medium_dark='4', dark='5'}
local function norm(s) return (s:gsub('️','')) end
function M.apply(emoji, phrase, settings)
  local entry = data[norm(emoji)]
  if not entry then return emoji end
  local gender = settings.gender
  local tone = tones[settings.skin]
  -- Explicit wording wins over defaults. Existing gender stays untouched.
  local explicit = false
  for _, word in ipairs({'女','男','妈妈','爸爸','母亲','父亲','姐姐','哥哥','妹妹','弟弟','老公','老婆','女士','先生','妻','夫'}) do
    if phrase:find(word,1,true) then explicit = true; break end
  end
  if explicit then
    for _, family in pairs(entry) do
      if norm(family['0']) == norm(emoji) then return family[tone] or emoji end
    end
    return emoji
  end
  local family = entry[gender] or entry.neutral
  if not family then return emoji end
  return family[tone] or family['0']
end
return M
