-- Annotates Rime candidates using only the user's local personal lexicon.
-- Missing entries stay unannotated. No fallback, helper, database, or network
-- request is used on the typing path.

local M = {}

local USER_DIR = rime_api.get_user_data_dir()
local LEXICON_PATH = USER_DIR .. "/personal_translate.tsv"
local IMPORTED_PATH = USER_DIR .. "/imported_translate.tsv"
local MAX_CANDIDATE_LENGTH = 20
local MAX_TRANSLATIONS = 2
local SEPARATOR = " / "

local cache = {}
local cache_revision = nil
local imported_cache = {}
local imported_revision = nil

local function read_revision(path)
  local file = io.open(path, "r")
  if not file then return nil end
  local first = file:read("*l") or ""
  file:close()
  return first:match("^#rev=(%d+)$")
end

local function load_file(path)
  local next_cache = {}
  local file = io.open(path, "r")
  if file then
    for line in file:lines() do
      if not line:match("^#") then
        local zh, en = line:match("^(.-)\t(.+)$")
        if zh and en and en ~= "" then next_cache[zh] = en end
      end
    end
    file:close()
  end
  return next_cache
end

local function reload_if_needed()
  local revision = read_revision(LEXICON_PATH)
  if revision ~= cache_revision then
    cache = load_file(LEXICON_PATH)
    cache_revision = revision
  end
  local imported = read_revision(IMPORTED_PATH)
  if imported ~= imported_revision then
    imported_cache = load_file(IMPORTED_PATH)
    imported_revision = imported
  end
end

local function is_cjk(text)
  if not text or text == "" then return false end
  local length = utf8.len(text)
  if not length or length == 0 or length > MAX_CANDIDATE_LENGTH then return false end
  for _, codepoint in utf8.codes(text) do
    if not ((codepoint >= 0x3400 and codepoint <= 0x9FFF) or
        (codepoint >= 0xF900 and codepoint <= 0xFAFF)) then
      return false
    end
  end
  return true
end

local function render(value)
  if not value or value == "" then return nil end
  local parts = {}
  for item in value:gmatch("[^|]+") do
    parts[#parts + 1] = item:match("^%s*(.-)%s*$")
    if #parts >= MAX_TRANSLATIONS then break end
  end
  if #parts == 0 then return nil end
  return table.concat(parts, SEPARATOR)
end

function M.init(env)
  reload_if_needed()
end

function M.func(input, env)
  reload_if_needed()
  for candidate in input:iter() do
    local handled = false
    if is_cjk(candidate.text) and candidate.type ~= "raw" then
      local english = render(cache[candidate.text] or imported_cache[candidate.text])
      if english then
        if candidate.type == "simplified" or candidate.type == "shadow" then
          local replacement = Candidate(
            "simplified", candidate.start, candidate._end,
            candidate.text, "  " .. english
          )
          replacement.quality = candidate.quality
          handled = true
          yield(replacement)
        else
          pcall(function()
            candidate.comment = (candidate.comment or "") .. "  " .. english
          end)
        end
      end
    end
    if not handled then yield(candidate) end
  end
end

return M
