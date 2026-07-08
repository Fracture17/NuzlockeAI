-- Lua TCP socket server loaded by mGBA at launch. Listens on localhost:8888,
-- accepts commands from a Python client, and dispatches them via mGBA's Lua API.
-- Runs inside mGBA's per-frame callback; all I/O uses hasdata() to avoid blocking.
--
-- Protocol (Python → Lua):
--   Commands end with <|END|>; responses are <|SUCCESS|><|END|> or <|ERROR|>msg<|END|>.
--
-- Protocol (Lua → Python, unsolicited):
--   <|EVENT|>eventname arg1 arg2<|END|>
--   Current events: "toggle_capture", "print_messages"
--
-- NOTE: The emulator object is exposed as the global 'emu', not 'core'.

local DELIMITER = "<|END|>"
local SUCCESS   = "<|SUCCESS|>"
local ERROR_PFX = "<|ERROR|>"
local EVENT_PFX = "<|EVENT|>"

-- ---------------------------------------------------------------------------
-- Pokemon memory reading
-- ---------------------------------------------------------------------------

local PARTY_COUNT_ADDR = 0x2023a95  -- gPlayerPartyCount (u8)
local PARTY_BASE_ADDR  = 0x2023a98  -- gPlayerParty base
local STORAGE_BASE_ADDR = 0x202884c -- gPokemonStorage.boxes (struct base 0x2028848 + 4 for currentBox u8 + padding)
local BOX_MON_SIZE   = 80
local PARTY_MON_SIZE = 100
local BOXES          = 14
local BOX_SLOTS      = 30
local NAME_LEN       = 10
local CHAR_TERMINATOR = 0xFF

-- Ported verbatim from runandbun.lua lines 4043–4060.
local CHARMAP = { [0]=
    " ", "À", "Á", "Â", "Ç", "È", "É", "Ê", "Ë", "Ì", "こ", "Î", "Ï", "Ò", "Ó", "Ô",
    "Œ", "Ù", "Ú", "Û", "Ñ", "ß", "à", "á", "ね", "ç", "è", "é", "ê", "ë", "ì", "ま",
    "î", "ï", "ò", "ó", "ô", "œ", "ù", "ú", "û", "ñ", "º", "ª", "▯", "&", "+", "あ",
    "ぃ", "ぅ", "ぇ", "ぉ", "v", "=", "ょ", "が", "ぎ", "ぐ", "げ", "ご", "ざ", "じ", "ず", "ぜ",
    "ぞ", "だ", "ぢ", "づ", "で", "ど", "ば", "び", "ぶ", "べ", "ぼ", "ぱ", "ぴ", "ぷ", "ぺ", "ぽ",
    "っ", "¿", "¡", "Pk", "Mn", "Po", "Ké", "▯", "▯", "▯", "Í", "%", "(", ")", "セ", "ソ",
    "タ", "チ", "ツ", "テ", "ト", "ナ", "ニ", "ヌ", "â", "ノ", "ハ", "ヒ", "フ", "ヘ", "ホ", "í",
    "ミ", "ム", "メ", "モ", "ヤ", "ユ", "ヨ", "ラ", "リ", "⬆", "⬇", "⬅", "➡", "ヲ", "ン", "ァ",
    "ィ", "ゥ", "ェ", "ォ", "ャ", "ュ", "ョ", "ガ", "ギ", "グ", "ゲ", "ゴ", "ザ", "ジ", "ズ", "ゼ",
    "ゾ", "ダ", "ヂ", "ヅ", "デ", "ド", "バ", "ビ", "ブ", "ベ", "ボ", "パ", "ピ", "プ", "ペ", "ポ",
    "ッ", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "!", "?", ".", "-", "・",
    "…", "“", "”", "‘", "’", "♂", "♀", "$", ",", "×", "/", "A", "B", "C", "D", "E",
    "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U",
    "V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k",
    "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "▶",
    ":", "Ä", "Ö", "Ü", "ä", "ö", "ü", "⬆", "⬇", "⬅", "▯", "▯", "▯", "▯", "▯", ""
}

-- Maps personality % 24 → {pos_of_G, pos_of_A, pos_of_E, pos_of_M} (1-indexed).
-- Ported verbatim from runandbun.lua lines 4166–4191.
-- Each entry says: substructure G is at memory position pSel[1], A at pSel[2], etc.
local SUBSTRUCT_ORDER = {
    [ 0] = {0, 1, 2, 3},
    [ 1] = {0, 1, 3, 2},
    [ 2] = {0, 2, 1, 3},
    [ 3] = {0, 3, 1, 2},
    [ 4] = {0, 2, 3, 1},
    [ 5] = {0, 3, 2, 1},
    [ 6] = {1, 0, 2, 3},
    [ 7] = {1, 0, 3, 2},
    [ 8] = {2, 0, 1, 3},
    [ 9] = {3, 0, 1, 2},
    [10] = {2, 0, 3, 1},
    [11] = {3, 0, 2, 1},
    [12] = {1, 2, 0, 3},
    [13] = {1, 3, 0, 2},
    [14] = {2, 1, 0, 3},
    [15] = {3, 1, 0, 2},
    [16] = {2, 3, 0, 1},
    [17] = {3, 2, 0, 1},
    [18] = {1, 2, 3, 0},
    [19] = {1, 3, 2, 0},
    [20] = {2, 1, 3, 0},
    [21] = {3, 1, 2, 0},
    [22] = {2, 3, 1, 0},
    [23] = {3, 2, 1, 0},
}

local function decode_name(address, length)
    local result = ""
    for i = 0, length - 1 do
        local byte = emu:read8(address + i)
        if byte == CHAR_TERMINATOR then break end
        local ch = CHARMAP[byte]
        if ch then result = result .. ch end
    end
    return result
end

-- Read and decrypt 3 u32s for the substructure at memory position pos (0-indexed).
-- key = personality XOR otId
local function read_substruct(base, pos, key)
    local offset = base + 32 + pos * 12
    return {
        emu:read32(offset +  0) ~ key,
        emu:read32(offset +  4) ~ key,
        emu:read32(offset +  8) ~ key,
    }
end

-- Serialize a box-mon (plus optional party extras) into the 50-field wire format.
local function serialize_mon(box_idx, slot_idx, base_addr, is_party)
    local personality = emu:read32(base_addr + 0)
    local ot_id       = emu:read32(base_addr + 4)
    local nickname    = decode_name(base_addr + 8,  NAME_LEN)
    local flags_byte  = emu:read8 (base_addr + 19)
    local is_bad_egg  = flags_byte & 1
    local has_species = (flags_byte >> 1) & 1
    local is_egg      = (flags_byte >> 2) & 1
    local ot_name     = decode_name(base_addr + 20, NAME_LEN)

    -- XOR key for substructure decryption.
    local key = personality ~ ot_id
    local order = SUBSTRUCT_ORDER[personality % 24]
    -- ss_g/a/e/m: {u32[0], u32[1], u32[2]} after decryption.
    local ss_g = read_substruct(base_addr, order[1], key)
    local ss_a = read_substruct(base_addr, order[2], key)
    local ss_e = read_substruct(base_addr, order[3], key)
    local ss_m = read_substruct(base_addr, order[4], key)

    local species    = ss_g[1] & 0xFFFF
    local held_item  = (ss_g[1] >> 16) & 0xFFFF
    local experience = ss_g[2]
    local pp_bonuses = ss_g[3] & 0xFF
    local friendship = (ss_g[3] >> 8) & 0xFF
    local nature     = personality % 25  -- Gen 3: personality % 25 gives nature (0–24)

    local move0 = ss_a[1] & 0xFFFF
    local move1 = (ss_a[1] >> 16) & 0xFFFF
    local move2 = ss_a[2] & 0xFFFF
    local move3 = (ss_a[2] >> 16) & 0xFFFF
    local pp0   = ss_a[3] & 0xFF
    local pp1   = (ss_a[3] >> 8) & 0xFF
    local pp2   = (ss_a[3] >> 16) & 0xFF
    local pp3   = (ss_a[3] >> 24) & 0xFF

    local hp_ev  = ss_e[1] & 0xFF
    local atk_ev = (ss_e[1] >> 8) & 0xFF
    local def_ev = (ss_e[1] >> 16) & 0xFF
    local spe_ev = (ss_e[1] >> 24) & 0xFF
    local spa_ev = ss_e[2] & 0xFF
    local spd_ev = (ss_e[2] >> 8) & 0xFF

    local m1      = ss_m[1]
    local pokerus      = m1 & 0xFF
    local met_location = (m1 >> 8) & 0xFF
    local met_flags    = m1 >> 16
    local met_level    = met_flags & 0x7F
    local met_game     = (met_flags >> 7) & 0xF
    local pokeball     = (met_flags >> 11) & 0xF
    local m2      = ss_m[2]
    local hp_iv   = (m2 >> 1) & 0x1F
    local atk_iv  = (m2 >> 6) & 0x1F
    local def_iv  = (m2 >> 11) & 0x1F
    local spe_iv  = (m2 >> 16) & 0x1F
    local spa_iv  = (m2 >> 21) & 0x1F
    local spd_iv  = (m2 >> 26) & 0x1F
    local alt_ability = (ss_m[3] >> 29) & 0x3

    -- Fields 0–40 (always present).
    local fields = {
        tostring(box_idx),
        tostring(slot_idx),
        tostring(species),
        nickname,
        ot_name,
        tostring(ot_id),
        tostring(personality),
        tostring(is_egg),
        tostring(is_bad_egg),
        tostring(has_species),
        tostring(held_item),
        tostring(experience),
        tostring(friendship),
        tostring(pp_bonuses),
        tostring(move0),
        tostring(move1),
        tostring(move2),
        tostring(move3),
        tostring(pp0),
        tostring(pp1),
        tostring(pp2),
        tostring(pp3),
        tostring(hp_ev),
        tostring(atk_ev),
        tostring(def_ev),
        tostring(spe_ev),
        tostring(spa_ev),
        tostring(spd_ev),
        tostring(hp_iv),
        tostring(atk_iv),
        tostring(def_iv),
        tostring(spe_iv),
        tostring(spa_iv),
        tostring(spd_iv),
        tostring(nature),
        tostring(alt_ability),
        tostring(pokerus),
        tostring(pokeball),
        tostring(met_location),
        tostring(met_level),
        tostring(met_game),
    }

    -- Fields 41–49: party-only (level through spDefense); empty for box mons.
    if is_party then
        local level      = emu:read8 (base_addr + 84)
        local current_hp = emu:read16(base_addr + 86)
        local max_hp     = emu:read16(base_addr + 88)
        local status     = emu:read32(base_addr + 80)
        local attack     = emu:read16(base_addr + 90)
        local defense    = emu:read16(base_addr + 92)
        local speed      = emu:read16(base_addr + 94)
        local sp_attack  = emu:read16(base_addr + 96)
        local sp_defense = emu:read16(base_addr + 98)
        fields[42] = tostring(level)
        fields[43] = tostring(current_hp)
        fields[44] = tostring(max_hp)
        fields[45] = tostring(status)
        fields[46] = tostring(attack)
        fields[47] = tostring(defense)
        fields[48] = tostring(speed)
        fields[49] = tostring(sp_attack)
        fields[50] = tostring(sp_defense)
    else
        for i = 42, 50 do fields[i] = "" end
    end

    return table.concat(fields, "|")
end

-- ---------------------------------------------------------------------------
-- End Pokemon memory reading
-- ---------------------------------------------------------------------------

-- C.GBA_KEY_* constants are nil in some mGBA builds; use GBA KEYINPUT bit positions directly.
local KEY_MAP = {
  a      = 0,
  b      = 1,
  select = 2,
  start  = 3,
  right  = 4,
  left   = 5,
  up     = 6,
  down   = 7,
  r      = 8,
  l      = 9,
}

-- Resolve a case-insensitive key name to a GBA key constant, or nil + error msg.
local function resolve_key(name)
  local const = KEY_MAP[name:lower()]
  if not const then
    return nil, ERROR_PFX .. "unknown key: " .. name .. DELIMITER
  end
  return const, nil
end

-- Dispatch a single parsed command; return the full response string.
local function handle_command(line)
  local cmd, args = line:match("^(%S+)%s*(.*)")
  if not cmd then
    return ERROR_PFX .. "empty command" .. DELIMITER
  end
  cmd = cmd:lower()

  if cmd == "screenshot" then
    local path = args:match("^%s*(.-)%s*$")
    emu:screenshot(path)
    return SUCCESS .. DELIMITER

  elseif cmd == "addkey" then
    local key, err = resolve_key(args:match("^%s*(%S+)"))
    if err then return err end
    emu:addKey(key)
    return SUCCESS .. DELIMITER

  elseif cmd == "clearkey" then
    local key, err = resolve_key(args:match("^%s*(%S+)"))
    if err then return err end
    emu:clearKey(key)
    return SUCCESS .. DELIMITER

  elseif cmd == "tap" then
    local key, err = resolve_key(args:match("^%s*(%S+)"))
    if err then return err end
    emu:addKey(key)
    emu:runFrame()
    emu:clearKey(key)
    return SUCCESS .. DELIMITER

  elseif cmd == "runframes" then
    local n = tonumber(args:match("^%s*(%S+)"))
    if not n or n < 0 then
      return ERROR_PFX .. "runFrames requires a non-negative integer" .. DELIMITER
    end
    for _ = 1, math.floor(n) do
      emu:runFrame()
    end
    return SUCCESS .. DELIMITER

  elseif cmd == "readparty" then
    local count = emu:read8(PARTY_COUNT_ADDR)
    local lines = {}
    for i = 0, count - 1 do
      local addr = PARTY_BASE_ADDR + i * PARTY_MON_SIZE
      lines[#lines + 1] = serialize_mon(-1, i, addr, true)
    end
    return SUCCESS .. table.concat(lines, "\n") .. DELIMITER

  elseif cmd == "readbox" then
    local b, s = args:match("^(%d+)%s+(%d+)")
    if not b then
      return ERROR_PFX .. "readbox requires two integers: B S" .. DELIMITER
    end
    b, s = tonumber(b), tonumber(s)
    if b < 0 or b >= BOXES or s < 0 or s >= BOX_SLOTS then
      return ERROR_PFX .. "readbox out of range" .. DELIMITER
    end
    local addr = STORAGE_BASE_ADDR + (b * BOX_SLOTS + s) * BOX_MON_SIZE
    local flags = emu:read8(addr + 19)
    local has_species = (flags >> 1) & 1
    if has_species == 0 then
      return SUCCESS .. DELIMITER
    end
    return SUCCESS .. serialize_mon(b, s, addr, false) .. DELIMITER

  elseif cmd == "readallboxes" then
    local lines = {}
    for b = 0, BOXES - 1 do
      for s = 0, BOX_SLOTS - 1 do
        local addr = STORAGE_BASE_ADDR + (b * BOX_SLOTS + s) * BOX_MON_SIZE
        local flags = emu:read8(addr + 19)
        local has_species = (flags >> 1) & 1
        if has_species == 1 then
          lines[#lines + 1] = serialize_mon(b, s, addr, false)
        end
      end
    end
    return SUCCESS .. table.concat(lines, "\n") .. DELIMITER

  elseif cmd == "loadstate" then
    local path = args:match("^%s*(.-)%s*$")
    if not path or path == "" then
      return ERROR_PFX .. "loadstate requires a file path" .. DELIMITER
    end
    local ok = emu:loadStateFile(path)
    if not ok then
      return ERROR_PFX .. "loadStateFile failed for: " .. path .. DELIMITER
    end
    return SUCCESS .. DELIMITER

  elseif cmd == "savestate" then
    local path = args:match("^%s*(.-)%s*$")
    if not path or path == "" then
      return ERROR_PFX .. "savestate requires a file path" .. DELIMITER
    end
    local ok = emu:saveStateFile(path)
    if not ok then
      return ERROR_PFX .. "saveStateFile failed for: " .. path .. DELIMITER
    end
    return SUCCESS .. DELIMITER

  else
    return ERROR_PFX .. "unknown command: " .. cmd .. DELIMITER
  end
end

-- Server and per-connection state.
-- Pass nil as address to bind all interfaces (required by mGBA's socket API).
local server, err = socket.bind(nil, 8888)
if not server then
  console:error("[mGBASocketServer] ERROR: failed to bind port 8888: " .. tostring(err))
  return
end
local ok, err2 = server:listen(1)
if not ok then
  console:error("[mGBASocketServer] ERROR: listen failed: " .. tostring(err2))
  return
end

local client = nil
local buffer = ""

-- Reset connection state; called on any terminal socket error.
local function reset_connection()
  if client then
    pcall(function() client:close() end)
  end
  client = nil
  buffer = ""
end

-- Host-key callbacks: L toggles periodic capture, O initializes battle state
-- (and saves a snapshot to CurrentBattle.pkl), M saves emulator state,
-- P saves a training-data snapshot to TrainingData/.
callbacks:add("key", function(event)
  if not client then return end
  if event.key == 0x4c and event.state == C.INPUT_STATE.DOWN then
    pcall(function()
      client:send(EVENT_PFX .. "toggle_capture" .. DELIMITER)
    end)
  elseif event.key == 0x4f and event.state == C.INPUT_STATE.DOWN then
    pcall(function()
      client:send(EVENT_PFX .. "init_battle" .. DELIMITER)
    end)
  elseif event.key == 0x4d and event.state == C.INPUT_STATE.DOWN then
    pcall(function()
      client:send(EVENT_PFX .. "save_state" .. DELIMITER)
    end)
  elseif event.key == 0x50 and event.state == C.INPUT_STATE.DOWN then
    pcall(function()
      client:send(EVENT_PFX .. "save_training_data" .. DELIMITER)
    end)
  end
end)

-- Per-frame callback: accept, read, dispatch, respond — all non-blocking.
callbacks:add("frame", function()
  local ok, err_msg = pcall(function()

    -- Accept a new client if we have none and one is waiting.
    if not client then
      if server:hasdata() then
        local c = server:accept()
        if c then
          client = c
          buffer = ""
        end
      end
      return
    end

    -- Read available bytes into the buffer.
    if client:hasdata() then
      local data, recv_err = client:receive(4096)
      if not data then
        -- Client disconnected or error.
        reset_connection()
        return
      end
      buffer = buffer .. data
    end

    -- Drain all complete messages from the buffer.
    while true do
      local msg_end = buffer:find(DELIMITER, 1, true)
      if not msg_end then break end

      local message = buffer:sub(1, msg_end - 1)
      buffer = buffer:sub(msg_end + #DELIMITER)

      local response = handle_command(message)
      client:send(response)
    end

  end)

  -- If pcall caught a Lua error, log it and reset so next frame is clean.
  if not ok then
    console:error("[mGBASocketServer] frame error: " .. tostring(err_msg))
    reset_connection()
  end
end)

console:log("[mGBASocketServer] listening on port 8888")
