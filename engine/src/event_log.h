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
// canonical string mapping lives in the Python shim. Only the source/volatile tag
// strings the CONSUMED events actually distinguish are enumerated (DAMAGE source,
// HEAL source, VOLATILE_APPLY "confused"); the rest use MOVE/ABILITY/RESIDUAL/ITEM
// broad buckets since the reconciler never reads them.
enum class SourceTag : int32_t { NONE = 0, MOVE, BERRY, CHEEK_POUCH, ABILITY, ITEM, RESIDUAL, RECOIL };
enum class VolatileTag : int32_t { NONE = 0, CONFUSED, TAUNT, ENCORE, LEECH_SEEDED };
enum class CauseTag : int32_t { NONE = 0 };

// One recorded LogEvent. All named int fields default to RICH_UNSET; tag fields
// default to NONE. Only the fields relevant to a given event are populated.
// For the five E1a "silent" events: event, turn, species (user/pokemon/target;
// for STAT_COPY = copier), side, and aux0 = move id (or, for STAT_COPY, the
// copied-from source species).
// E1b consumed-event field usage:
//   MOVE_USE: species=user, move, side.
//   CRIT / CANT_* : species=target/pokemon.
//   HIT_SELF_CONFUSION: species=pokemon, amount=damage, side.
//   MOVE_MISS: species=user.
//   STATUS_APPLY: species=target, status, side (source_tag).
//   STAT_BOOST: species=target, stat, stages, side (source_tag).
//   VOLATILE_APPLY: species=target, side, volatile_tag (source_tag).
//   HITCOUNT: species=user, side.
//   DAMAGE: species=target, amount, hp_after, attacker_side, attacker_slot,
//           defender_side, source_tag.
//   HEAL: species=target, amount, hp_after, side, source_tag.
//   EXP_GAIN: species=pokemon, amount.
//   LEVEL_UP: species=pokemon, new_level.
//   FAINT: species=pokemon, side (cause_tag).
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
    int32_t move = RICH_UNSET;       // MOVE_USE
    int32_t stat = RICH_UNSET;       // STAT_BOOST stat index
    int32_t hp_after = RICH_UNSET;   // DAMAGE / HEAL fidelity
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

// LogEvent integer constants for the ~18 CONSUMED events (E1b).
static constexpr int RICH_EV_CANT_SLEEP = 5;
static constexpr int RICH_EV_CANT_FROZEN = 8;
static constexpr int RICH_EV_CANT_PARALYSIS = 10;
static constexpr int RICH_EV_CANT_FLINCH = 11;
static constexpr int RICH_EV_HIT_SELF_CONFUSION = 13;
static constexpr int RICH_EV_CANT_INFATUATION = 14;
static constexpr int RICH_EV_MOVE_USE = 27;
static constexpr int RICH_EV_MOVE_MISS = 33;
static constexpr int RICH_EV_DAMAGE = 45;
static constexpr int RICH_EV_CRIT = 46;
static constexpr int RICH_EV_HITCOUNT = 48;
static constexpr int RICH_EV_HEAL = 51;
static constexpr int RICH_EV_STAT_BOOST = 53;
static constexpr int RICH_EV_STATUS_APPLY = 61;
static constexpr int RICH_EV_VOLATILE_APPLY = 64;
static constexpr int RICH_EV_FAINT = 123;
static constexpr int RICH_EV_EXP_GAIN = 132;
static constexpr int RICH_EV_LEVEL_UP = 133;

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

// ---------------------------------------------------------------------------
// E1b consumed-event emit helpers. Same nullptr fast-path + fail-loud species/side
// guards as E1a. Each is called at exactly one observation point in the mechanic
// code (or one per chokepoint where a chokepoint funnels many callers).
// ---------------------------------------------------------------------------

inline void rich_log_move_use(int turn, int32_t species, int32_t move, int32_t side) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_move_use: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_MOVE_USE;
    e.species = species; e.move = move; e.side = side;
    sink->entries.push_back(e);
}

// species-only presence events: CRIT / CANT_FLINCH / CANT_PARALYSIS / CANT_FROZEN /
// CANT_INFATUATION / MOVE_MISS. The event id disambiguates the kwarg name in the shim.
inline void rich_log_presence(int turn, int event, int32_t species) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_presence: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = event; e.species = species;
    sink->entries.push_back(e);
}

// CANT_SLEEP carries an optional turns count (aux0); consumer reads presence only.
inline void rich_log_cant_sleep(int turn, int32_t species, int32_t turns) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_cant_sleep: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_CANT_SLEEP; e.species = species; e.aux0 = turns;
    sink->entries.push_back(e);
}

inline void rich_log_hit_self_confusion(int turn, int32_t species, int32_t damage, int32_t side) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_hit_self_confusion: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_HIT_SELF_CONFUSION;
    e.species = species; e.amount = damage; e.side = side;
    sink->entries.push_back(e);
}

inline void rich_log_status_apply(int turn, int32_t species, int32_t status, int32_t side,
                                  SourceTag source) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_status_apply: species must be non-negative");
    if (side < 0) throw std::runtime_error("rich_log_status_apply: side must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_STATUS_APPLY;
    e.species = species; e.status = status; e.side = side;
    e.source_tag = static_cast<int32_t>(source);
    sink->entries.push_back(e);
}

inline void rich_log_stat_boost(int turn, int32_t species, int32_t stat, int32_t stages,
                                int32_t side, SourceTag source) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_stat_boost: species must be non-negative");
    if (side < 0) throw std::runtime_error("rich_log_stat_boost: side must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_STAT_BOOST;
    e.species = species; e.stat = stat; e.stages = stages; e.side = side;
    e.source_tag = static_cast<int32_t>(source);
    sink->entries.push_back(e);
}

inline void rich_log_volatile_apply(int turn, int32_t species, VolatileTag vol, int32_t side,
                                    SourceTag source) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_volatile_apply: species must be non-negative");
    if (side < 0) throw std::runtime_error("rich_log_volatile_apply: side must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_VOLATILE_APPLY;
    e.species = species; e.side = side;
    e.volatile_tag = static_cast<int32_t>(vol);
    e.source_tag = static_cast<int32_t>(source);
    sink->entries.push_back(e);
}

inline void rich_log_hitcount(int turn, int32_t species, int32_t side) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_hitcount: species must be non-negative");
    if (side < 0) throw std::runtime_error("rich_log_hitcount: side must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_HITCOUNT; e.species = species; e.side = side;
    sink->entries.push_back(e);
}

inline void rich_log_damage(int turn, int32_t species, int32_t amount, int32_t hp_after,
                            int32_t attacker_side, int32_t attacker_slot, int32_t defender_side,
                            SourceTag source) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_damage: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_DAMAGE;
    e.species = species; e.amount = amount; e.hp_after = hp_after;
    e.attacker_side = attacker_side; e.attacker_slot = attacker_slot;
    e.defender_side = defender_side;
    e.source_tag = static_cast<int32_t>(source);
    sink->entries.push_back(e);
}

inline void rich_log_heal(int turn, int32_t species, int32_t amount, int32_t hp_after,
                          int32_t side, SourceTag source) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_heal: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_HEAL;
    e.species = species; e.amount = amount; e.hp_after = hp_after; e.side = side;
    e.source_tag = static_cast<int32_t>(source);
    sink->entries.push_back(e);
}

inline void rich_log_faint(int turn, int32_t species, int32_t side) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_faint: species must be non-negative");
    if (side < 0) throw std::runtime_error("rich_log_faint: side must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_FAINT; e.species = species; e.side = side;
    sink->entries.push_back(e);
}

inline void rich_log_exp_gain(int turn, int32_t species, int32_t amount) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_exp_gain: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_EXP_GAIN; e.species = species; e.amount = amount;
    sink->entries.push_back(e);
}

inline void rich_log_level_up(int turn, int32_t species, int32_t new_level) {
    RichEventLog* sink = g_rich_event_log();
    if (!sink) return;
    if (species < 0) throw std::runtime_error("rich_log_level_up: species must be non-negative");
    RichEventEntry e{};
    e.turn = turn; e.event = RICH_EV_LEVEL_UP; e.species = species; e.new_level = new_level;
    sink->entries.push_back(e);
}

#endif // NUZLOCKE_EVENT_LOG_H
