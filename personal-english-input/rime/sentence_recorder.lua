-- Records Chinese text committed through Rime plus printable English typed in
-- Squirrel's internal ASCII mode, then saves one sentence when Return is
-- pressed. The log stays local; control shortcuts are never recorded.

local M = {}

local HOME = os.getenv("HOME") or ""
local DATA_DIR = os.getenv("PERSONAL_ENGLISH_DATA_DIR") or
    (HOME .. "/Library/Application Support/personal-english-lexicon")
local LOG_PATH = DATA_DIR .. "/sentences.tsv"
local BUFFER_PATH = DATA_DIR .. "/current_sentence.tsv"
local CURSOR_PATH = DATA_DIR .. "/current_cursor.txt"
local NOOP = 2
local MAX_IDLE_SECONDS = 1800

local ASCII_KEYS = {
  space = " ", minus = "-", equal = "=", bracketleft = "[",
  bracketright = "]", backslash = "\\", semicolon = ";",
  apostrophe = "'", grave = "`", comma = ",", period = ".", slash = "/",
  exclam = "!", at = "@", numbersign = "#", dollar = "$", percent = "%",
  asciicircum = "^", ampersand = "&", asterisk = "*", parenleft = "(",
  parenright = ")", underscore = "_", plus = "+", braceleft = "{",
  braceright = "}", bar = "|", colon = ":", quotedbl = '"',
  asciitilde = "~", less = "<", greater = ">", question = "?",
}

local SHIFTED_ASCII = {
  ["1"] = "!", ["2"] = "@", ["3"] = "#", ["4"] = "$", ["5"] = "%",
  ["6"] = "^", ["7"] = "&", ["8"] = "*", ["9"] = "(", ["0"] = ")",
  minus = "_", equal = "+", bracketleft = "{", bracketright = "}",
  backslash = "|", semicolon = ":", apostrophe = '"', grave = "~",
  comma = "<", period = ">", slash = "?",
}

local function has_cjk(text)
  return text and text:match("[\228-\233][\128-\191][\128-\191]") ~= nil
end

local function sanitize(text)
  if not text then return "" end
  return text:gsub("[\r\n\t]", " ")
end

local function clean(text)
  return sanitize(text):gsub("%s+", " "):gsub("^%s+", ""):gsub("%s+$", "")
end

local function clear_buffer()
  local file = io.open(BUFFER_PATH, "w")
  if file then file:close() end
  file = io.open(CURSOR_PATH, "w")
  if file then file:close() end
end

local function invalidate(env)
  env.invalid = true
  env.pending_return = false
  clear_buffer()
end

local function utf8_characters(text)
  local characters = {}
  for character in text:gmatch("[\0-\127\194-\244][\128-\191]*") do
    characters[#characters + 1] = character
  end
  return characters
end

local function write_buffer(text, cursor)
  text = sanitize(text)
  local characters = utf8_characters(text)
  cursor = math.max(0, math.min(cursor or #characters, #characters))

  local file = io.open(BUFFER_PATH, "w")
  if not file then return end
  if text ~= "" then file:write(tostring(os.time()), "\t", text, "\n") end
  file:close()

  file = io.open(CURSOR_PATH, "w")
  if not file then return end
  file:write(tostring(cursor), "\n")
  file:close()
end

local function read_buffer()
  local parts = {}
  local last_time = nil
  local file = io.open(BUFFER_PATH, "r")
  if not file then return parts, last_time end
  for line in file:lines() do
    local timestamp, text = line:match("^(%d+)\t(.*)$")
    if timestamp and text and text ~= "" then
      last_time = tonumber(timestamp)
      parts[#parts + 1] = text
    end
  end
  file:close()
  return parts, last_time
end

local function read_state()
  local parts, last_time = read_buffer()
  local text = sanitize(table.concat(parts))
  local characters = utf8_characters(text)
  local cursor = #characters
  local file = io.open(CURSOR_PATH, "r")
  if file then
    cursor = tonumber(file:read("*l")) or cursor
    file:close()
  end
  cursor = math.max(0, math.min(cursor, #characters))
  return text, cursor, last_time
end

local function append_fragment(env, text)
  text = sanitize(text)
  if text == "" then return end
  if env.invalid then return end
  local now = os.time()
  local sentence, cursor, last_time = read_state()
  if last_time and now - last_time > MAX_IDLE_SECONDS then
    sentence, cursor = "", 0
  end

  local existing = utf8_characters(sentence)
  local inserted = utf8_characters(text)
  local result = {}
  for i = 1, cursor do result[#result + 1] = existing[i] end
  for _, character in ipairs(inserted) do result[#result + 1] = character end
  for i = cursor + 1, #existing do result[#result + 1] = existing[i] end
  write_buffer(table.concat(result), cursor + #inserted)
end

local function ascii_character(repr)
  if repr:find("Control+", 1, true) or repr:find("Alt+", 1, true) or
      repr:find("Super+", 1, true) then
    return nil
  end

  local shifted = false
  local base = repr
  if base:sub(1, 6) == "Shift+" then
    shifted = true
    base = base:sub(7)
  end

  if #base == 1 and base:match("^[A-Za-z]$") then
    return shifted and base:upper() or base
  end
  if #base == 1 and base:match("^%d$") then
    return shifted and SHIFTED_ASCII[base] or base
  end
  if shifted and SHIFTED_ASCII[base] then return SHIFTED_ASCII[base] end
  return ASCII_KEYS[base]
end

local function remove_last_character(env)
  local sentence, cursor = read_state()
  local characters = utf8_characters(sentence)
  if cursor == 0 then
    invalidate(env)
    return
  end
  table.remove(characters, cursor)
  write_buffer(table.concat(characters), cursor - 1)
end

local function delete_next_character(env)
  local sentence, cursor = read_state()
  local characters = utf8_characters(sentence)
  if cursor >= #characters then
    invalidate(env)
    return
  end
  table.remove(characters, cursor + 1)
  write_buffer(table.concat(characters), cursor)
end

local function move_cursor(env, repr)
  local sentence, cursor = read_state()
  local length = #utf8_characters(sentence)
  if length == 0 then
    invalidate(env)
    return
  end
  if repr == "Left" then cursor = math.max(0, cursor - 1) end
  if repr == "Right" then cursor = math.min(length, cursor + 1) end
  write_buffer(sentence, cursor)
end

local function reset(env)
  env.pending_return = false
  env.invalid = false
  clear_buffer()
end

local function save_sentence(env)
  local sentence = clean(read_state())
  local invalid = env.invalid
  reset(env)
  if invalid then return end
  if sentence == "" or not has_cjk(sentence) then return end
  if #sentence > 1200 then return end

  local file = io.open(LOG_PATH, "a")
  if not file then return end
  file:write(tostring(os.time()), "\t", sentence, "\n")
  file:close()
end

function M.init(env)
  env.pending_return = false
  env.invalid = false
  env.commit_connection = env.engine.context.commit_notifier:connect(function(ctx)
    local committed = ctx:get_commit_text()
    append_fragment(env, committed)
    if env.pending_return then save_sentence(env) end
  end)
end

function M.fini(env)
  if env.commit_connection then env.commit_connection:disconnect() end
  env.pending_return = false
  env.invalid = false
end

function M.func(key, env)
  local repr = key:repr()
  local ctx = env.engine.context

  if repr == "Return" or repr == "KP_Enter" then
    if ctx:is_composing() then
      -- The downstream editor commits after this processor. Flush from the
      -- commit callback so the final committed text is included.
      env.pending_return = true
    else
      save_sentence(env)
    end
    return NOOP
  end

  if not ctx:is_composing() and repr == "BackSpace" then
    remove_last_character(env)
    return NOOP
  end

  if not ctx:is_composing() and (
      repr == "Left" or repr == "Right") then
    move_cursor(env, repr)
    return NOOP
  end

  if not ctx:is_composing() and repr == "Delete" then
    delete_next_character(env)
    return NOOP
  end

  -- Printable characters bypass Rime's commit notifier in ASCII mode.
  -- Capture them while keeping Chinese-mode letters for the normal composer.
  if not ctx:is_composing() then
    if ctx:get_option("ascii_mode") then
      local character = ascii_character(repr)
      if character then append_fragment(env, character) end
    else
      if repr:match("^%d$") then append_fragment(env, repr) end
      if repr == "space" then append_fragment(env, " ") end
    end
  end

  -- These keys can leave the current line or create a selection. Their exact
  -- behavior depends on the host app, so skip this sentence instead of
  -- recording guessed text.
  if not ctx:is_composing() and (
      repr == "Up" or repr == "Down" or
      repr == "Home" or repr == "End" or
      repr == "Page_Up" or repr == "Page_Down" or
      repr:find("Left", 1, true) or repr:find("Right", 1, true)) then
    invalidate(env)
  end

  return NOOP
end

return M
