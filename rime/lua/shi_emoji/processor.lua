local preview = require("shi_emoji.filter")
local M = {}

function M.func(key, env)
  local context = env.engine.context
  if key:release() or not context:get_option("shi_emoji")
      or context:get_option("ascii_mode") then return 2 end
  if key.keycode ~= 0xff0d or not key:alt() or key:shift() or key:super() then
    return 2
  end
  local candidate = context:get_selected_candidate()
  if candidate and candidate.type == "shi_emoji" then return 2 end
  if not preview.eligible(candidate, context) then return 2 end
  local adult = key:ctrl()
  if adult and not context:get_option("shi_emoji_adult") then return 2 end
  local suffix = preview.suffix(candidate.text, context, adult)
  if not suffix then return 2 end
  env.engine:commit_text(candidate.text .. " " .. suffix)
  context:clear()
  return 1
end

return M
