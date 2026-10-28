local preview = require("shi_emoji.filter")
local settings = require("shi_emoji.settings")
local M = {}

function M.init(env)
  env.zero_key = env.engine.schema.config:get_bool("shi_emoji/zero_key")
  env.settings = settings.load(env.engine.schema.config)
end

function M.func(key, env)
  local context = env.engine.context
  if key:release() or not context:get_option("shi_emoji")
      or context:get_option("ascii_mode") then return 2 end
  local zero = env.zero_key and key.keycode == 0x30
      and not key:alt() and not key:ctrl() and not key:shift() and not key:super()
  local option_return = key.keycode == 0xff0d and key:alt()
      and not key:shift() and not key:super()
  if not zero and not option_return then return 2 end
  local candidate = context:get_selected_candidate()
  if candidate and candidate.type == "shi_emoji" then return 2 end
  if not preview.eligible(candidate, context) then return 2 end
  local adult = option_return and key:ctrl()
  if adult and not env.settings.adult then return 2 end
  local suffix = preview.suffix(candidate.text, env.settings, adult)
  if not suffix then return 2 end
  local output = zero and context:get_option("shi_emoji_emoji_only")
      and suffix or candidate.text .. " " .. suffix
  env.engine:commit_text(output)
  context:clear()
  return 1
end

return M
