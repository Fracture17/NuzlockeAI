// Rich LogEvent-stream logger (mirrors Python liveplay/logger.py LogEvent, 1-133).
// Separate from the analytical RNG logger (logger.h): perf non-critical, used by the
// emulator/state-transition path only. One global toggle pointer (nullptr=off, zero
// work) — NO preprocessor gating. Entries are POD; string kwargs are int-enum tags
// whose canonical strings live in the Python shim (single source of truth).
#pragma once
#ifndef NUZLOCKE_EVENT_LOG_H
#define NUZLOCKE_EVENT_LOG_H

#include <cstdint>
#include <stdexcept>
#include <type_traits>
#include <vector>

// Sentinel for "field unset". Fields default to this; the shim drops them.
static constexpr int32_t RICH_UNSET = INT32_MIN;

// String-valued kwargs are stored as int-enum tags to keep the entry POD. The
// canonical string mapping lives in the Python shim. E1b will grow these.
enum class SourceTag : int32_t { NONE = 0, MOVE, BERRY, CHEEK_POUCH, ABILITY, ITEM, RESIDUAL };
enum class VolatileTag : int32_t { NONE = 0, CONFUSED, TAUNT, ENCORE, LEECH_SEEDED };
enum class CauseTag : int32_t { NONE = 0 };

// One recorded LogEvent. All named int fields default to RICH_UNSET; tag fields
// default to NONE. Only the fields relevant to a given event are populated.
// For the five E1a "silent" events: event, turn, species (user/pokemon/target;
// for STAT_COPY = copier), side, and aux0 = move id (or, for STAT_COPY, the
// copied-from source species).
struct RichEventEntry {
    int32_t turn = 0;
    int32_t event = 0;            // LogEvent integer value (1-133)

    int32_t species = RICH_UNSET;
    int32_t side = RICH_UNSET;
    int32_t amount = RICH_UNSET;
    int32_t stages = RICH_UNSET;
    int32_t attacker_side = RICH_UNSET;
    int32_t attacker_slot = RICH_UNSET;
    int32_t defender_side = RICH_UNSET;
    int32_t status = RICH_UNSET;
    int32_t new_level = RICH_UNSET;
    int32_t aux0 = RICH_UNSET;
    int32_t aux1 = RICH_UNSET;

    int32_t source_tag = static_cast<int32_t>(SourceTag::NONE);
    int32_t volatile_tag = static_cast<int32_t>(VolatileTag::NONE);
    int32_t cause_tag = static_cast<int32_t>(CauseTag::NONE);
};

static_assert(std::is_trivially_copyable<RichEventEntry>::value,
              "RichEventEntry must be trivially copyable (POD)");

// Log sink: a POD entry vector. Off = nullptr; enable/disable via g_rich_event_log.
struct RichEventLog {
    std::vector<RichEventEntry> entries;

    void clear() { entries.clear(); }
    size_t size() const { return entries.size(); }
    const RichEventEntry& at(size_t i) const { return entries.at(i); }
};

// The one runtime toggle. nullptr = logger off; nothing happens on emit.
// Set by whoever owns a sink (Python shim / emulator driver / test harness).
inline RichEventLog*& g_rich_event_log() {
    static RichEventLog* p = nullptr;
    return p;
}

inline void set_rich_event_log(RichEventLog* log) { g_rich_event_log() = log; }
inline RichEventLog* get_rich_event_log() { return g_rich_event_log(); }

// LogEvent integer constants used by E1a (liveplay/logger.py).
static constexpr int RICH_EV_CHARGE_TURN = 38;
static constexpr int RICH_EV_SEMI_INVULNERABLE_ENTER = 39;
static constexpr int RICH_EV_SEMI_INVULNERABLE_EXIT = 40;
static constexpr int RICH_EV_STAT_COPY = 55;
static constexpr int RICH_EV_BATON_PASS_TRANSFER = 92;

// ---------------------------------------------------------------------------
// Emit helpers. Each is a no-op when the logger is off (one comparison). Turn is
// passed from the call site — the mechanic code has the state in scope; never read
// from a global. Invariant guards fail loud (negative species/side where those are
// invariants of the emit site).
// ---------------------------------------------------------------------------

inline void rich_log_charge_turn(int turn, int32_t species, int32_t move) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0)
        throw std::runtime_error("rich_log_charge_turn: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn;
    e.event = RICH_EV_CHARGE_TURN;
    e.species = species;
    e.aux0 = move;
    sink->entries.push_back(e);
}

inline void rich_log_semi_invuln_enter(int turn, int32_t species, int32_t move) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0)
        throw std::runtime_error("rich_log_semi_invuln_enter: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn;
    e.event = RICH_EV_SEMI_INVULNERABLE_ENTER;
    e.species = species;
    e.aux0 = move;
    sink->entries.push_back(e);
}

inline void rich_log_semi_invuln_exit(int turn, int32_t species, int32_t move) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0)
        throw std::runtime_error("rich_log_semi_invuln_exit: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn;
    e.event = RICH_EV_SEMI_INVULNERABLE_EXIT;
    e.species = species;
    e.aux0 = move;
    sink->entries.push_back(e);
}

inline void rich_log_baton_pass_transfer(int turn, int32_t side, int32_t species) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (side < 0)
        throw std::runtime_error("rich_log_baton_pass_transfer: side must be non-negative");
    if (species < 0)
        throw std::runtime_error("rich_log_baton_pass_transfer: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn;
    e.event = RICH_EV_BATON_PASS_TRANSFER;
    e.side = side;
    e.species = species;
    sink->entries.push_back(e);
}

inline void rich_log_stat_copy(int turn, int32_t side, int32_t copier_species,
                               int32_t source_species) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (side < 0)
        throw std::runtime_error("rich_log_stat_copy: side must be non-negative");
    if (copier_species < 0 || source_species < 0)
        throw std::runtime_error("rich_log_stat_copy: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn;
    e.event = RICH_EV_STAT_COPY;
    e.side = side;
    e.species = copier_species;
    e.aux0 = source_species;
    sink->entries.push_back(e);
}

#endif // NUZLOCKE_EVENT_LOG_H
