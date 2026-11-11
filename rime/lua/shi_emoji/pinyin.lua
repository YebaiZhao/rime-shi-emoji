-- Optional exact full-pinyin Chinese names. Never emits Emoji candidates.
local entries = require('shi_emoji.pinyin_data')
local M = {}

function M.func(input, segment, env)
  local context = env.engine.context
  if not context:get_option('shi_emoji') or context:get_option('ascii_mode') then return end
  if segment.start ~= 0 or segment._end ~= #context.input or input ~= context.input then return end
  if not segment:has_tag('abc') then return end
  local names = entries[(input:gsub("'", ''))]
  if not names then return end
  for _, name in ipairs(names) do
    local candidate = Candidate('shi_emoji_name', 0, #input, name, '')
    candidate.quality = 1
    yield(candidate)
  end
end

return M
