local M = {}
local skins = {default=true, light=true, medium_light=true, medium=true,
  medium_dark=true, dark=true}
local genders = {neutral=true, female=true, male=true}

function M.load(config)
  local skin = config:get_string('shi_emoji/skin') or 'default'
  local gender = config:get_string('shi_emoji/gender') or 'neutral'
  assert(skins[skin], 'Invalid shi_emoji/skin: ' .. skin)
  assert(genders[gender], 'Invalid shi_emoji/gender: ' .. gender)
  return {skin=skin, gender=gender, adult=config:get_bool('shi_emoji/adult') or false}
end

return M
