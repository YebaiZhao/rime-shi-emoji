local M = {}
local skins = {default=true, light=true, medium_light=true, medium=true,
  medium_dark=true, dark=true}
local genders = {neutral=true, female=true, male=true}

function M.load(config)
  local skin = config:get_string('shi_emoji/skin') or 'default'
  local gender = config:get_string('shi_emoji/gender') or 'neutral'
  assert(skins[skin], 'Invalid shi_emoji/skin: ' .. skin)
  assert(genders[gender], 'Invalid shi_emoji/gender: ' .. gender)
  local adult = config:get_bool('shi_emoji/adult')
  if adult == nil then adult = true end
  return {skin=skin, gender=gender, adult=adult, tiered=config:get_bool('shi_emoji/tiered')}
end

function M.tier(preferences, context)
  if not preferences.tiered then return nil end
  if context:get_option('shi_emoji_strict') then return 1 end
  if context:get_option('shi_emoji_divergent') then return 3 end
  return 2
end

return M
