// Score-distribution family (_dist_*) split from ai_scorer.cpp.
// One helper per action archetype (recovery/protect/hazard/screen/paralysis/setup/
// tailwind/trick_room/terrain/poison/will_o_wisp/status_special/damage). Called by
// cpp_dist_action in ai_scorer.cpp. Shared constants/predicates live in
// ai_scorer_internal.h.
#include "ai_scorer.h"
#include "ai_scorer_internal.h"
#include "ai_shared.h"
#include "ai_damage.h"
#include "damage.h"          // cpp_effective_stat, cpp_expected_damage
#include "type_chart_lookup.h"

#include "../generated/ai_move_sets.h"

#include <algorithm>
#include <cstdint>
#include <utility>
#include <vector>

using namespace ai_scorer;

namespace ai_scorer {

// ---------------------------------------------------------------------------
// _dist_recovery
// ---------------------------------------------------------------------------
ScoreDistC dist_recovery(const BattleState& state, int ai_idx, double heal_pct) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    double hp_pct = (double)ai_mon.hp / ai_mon.max_hp;
    if (hp_pct >= 1.0) return {{-20, 1.0}};
    if (hp_pct >= 0.85) return {{-6, 1.0}};
    auto [p_true, p_false] = should_recover(state, ai_idx, heal_pct);
    ScoreDistC out;
    if (p_true > 0) out.push_back({7, p_true});
    if (p_false > 0) out.push_back({5, p_false});
    if (out.empty()) out.push_back({5, 1.0});
    return out;
}

// ---------------------------------------------------------------------------
// _dist_protect
// ---------------------------------------------------------------------------
ScoreDistC dist_protect(const BattleState& state, int ai_idx) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    int base = 6;
    if (has_protect_debuff(ai_mon)) base -= 2;
    if (has_protect_debuff(pl_mon)) base += 1;
    if (ai_mon.turns_in_battle == 0 && state.format != FMT_DOUBLES) base -= 1;
    return {{base, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_hazard
// ---------------------------------------------------------------------------
ScoreDistC dist_hazard(const BattleState& state, int ai_idx, int32_t move_id) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const SideState& opp_side = side_at(state, 1 - ai_idx);
    bool first_turn = ai_mon.turns_in_battle == 0;

    if (move_id == MV_STEALTH_ROCK) {
        if (side_has_condition(opp_side, SC_STEALTH_ROCK)) return {{-20, 1.0}};
        return first_turn ? ScoreDistC{{8, 0.25}, {9, 0.75}} : ScoreDistC{{6, 0.25}, {7, 0.75}};
    }
    if (move_id == MV_SPIKES) {
        int existing = count_side_conditions(opp_side, {SC_SPIKES_1, SC_SPIKES_2, SC_SPIKES_3});
        if (existing >= 3) return {{-20, 1.0}};
        int adj = (existing > 0) ? -1 : 0;
        return first_turn ? ScoreDistC{{8+adj, 0.25}, {9+adj, 0.75}} : ScoreDistC{{6+adj, 0.25}, {7+adj, 0.75}};
    }
    if (move_id == MV_TOXIC_SPIKES) {
        int existing = count_side_conditions(opp_side, {SC_TOXIC_SPIKES_1, SC_TOXIC_SPIKES_2});
        if (existing >= 2) return {{-20, 1.0}};
        int adj = (existing > 0) ? -1 : 0;
        return first_turn ? ScoreDistC{{8+adj, 0.25}, {9+adj, 0.75}} : ScoreDistC{{6+adj, 0.25}, {7+adj, 0.75}};
    }
    if (move_id == MV_STICKY_WEB) {
        if (side_has_condition(opp_side, SC_STICKY_WEB)) return {{-20, 1.0}};
        return first_turn ? ScoreDistC{{9, 0.25}, {12, 0.75}} : ScoreDistC{{6, 0.25}, {9, 0.75}};
    }
    return {{6, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_screen
// ---------------------------------------------------------------------------
ScoreDistC dist_screen(const BattleState& state, int ai_idx, int32_t move_id) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    bool is_lscreen = (move_id == MV_LIGHT_SCREEN);
    const SideState& ai_side = side_at(state, ai_idx);
    if (is_lscreen && side_has_condition(ai_side, SC_LIGHT_SCREEN)) return {{-40, 1.0}};
    if (!is_lscreen && side_has_condition(ai_side, SC_REFLECT)) return {{-40, 1.0}};

    int base = 6;
    for (int slot = 0; slot < 4; ++slot) {
        int32_t mid = move_id_at(pl_mon, slot);
        if (mid == MV_NONE) continue;
        const MoveData* md = ai_move_data_get(mid);
        if (!md) continue;
        bool relevant = (is_lscreen && (int32_t)md->category == CAT_SPECIAL)
                     || (!is_lscreen && (int32_t)md->category == CAT_PHYSICAL);
        if (relevant) {
            int clay_bonus = (ai_mon.item == ITM_LIGHT_CLAY) ? 1 : 0;
            return {{base + clay_bonus + 1, 0.5}, {base + clay_bonus, 0.5}};
        }
    }
    return {{base, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_paralysis
// ---------------------------------------------------------------------------
ScoreDistC dist_paralysis(const BattleState& state, int ai_idx, int32_t move_id) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    const MoveData& md = ai_move_data_or_throw(move_id);

    // Electric-type: blocked by Ground, Electric type, or Limber
    if ((int32_t)md.move_type == TYPE_ELECTRIC) {
        for (int32_t t : pl_mon.types) {
            if (t == TYPE_GROUND || t == TYPE_ELECTRIC) return {{-40, 1.0}};
        }
        if (pl_mon.ability == AB_LIMBER) return {{-40, 1.0}};
    }
    if (pl_mon.ability == AB_LIMBER) return {{-40, 1.0}};
    if (pl_mon.status != STATUS_NONE) return {{-20, 1.0}};

    // cpp_effective_stat for raw speed (stat index 5)
    int32_t pl_spe = cpp_effective_stat(pl_mon, 5);
    int32_t ai_spe = cpp_effective_stat(ai_mon, 5);
    int32_t para_spe = std::max(1, pl_spe / 4);
    bool speed_flip = (pl_spe > ai_spe && para_spe < ai_spe);
    int base = speed_flip ? 8 : 7;
    return {{base - 1, 0.5}, {base, 0.5}};
}

// ---------------------------------------------------------------------------
// _dist_setup (SetupKind: OFFENSIVE=0, DEFENSIVE=1, SPEED=2)
// ---------------------------------------------------------------------------
ScoreDistC dist_setup(const BattleState& state, int ai_idx, SetupKind kind) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);

    if (kind == SetupKind::SPEED) {
        return cpp_ai_faster(state, ai_idx) ? ScoreDistC{{-20, 1.0}} : ScoreDistC{{7, 1.0}};
    }

    // Threatened → never setup
    if (player_can_ko_ai(state, ai_idx)) {
        bool sash = (ai_mon.item == ITM_FOCUS_SASH && ai_mon.hp == ai_mon.max_hp);
        bool sturdy = (ai_mon.ability == AB_STURDY && ai_mon.hp == ai_mon.max_hp);
        if (!sash && !sturdy) return {{-20, 1.0}};
    }

    bool slower_2hko = (!cpp_ai_faster(state, ai_idx) && player_can_nhko_ai(state, ai_idx, 2));
    bool incap = is_incapacitated(pl_mon);

    if (kind == SetupKind::OFFENSIVE) {
        int base = 6;
        if (incap) base += 3;
        if (slower_2hko) base -= 5;
        return {{base, 1.0}};
    }

    // DEFENSIVE
    int base = 6;
    if (slower_2hko) base -= 5;
    if (incap) return {{base + 2, 0.95}, {base, 0.05}};
    return {{base, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_tailwind
// ---------------------------------------------------------------------------
ScoreDistC dist_tailwind(const BattleState& state, int ai_idx) {
    const SideState& ai_side = side_at(state, ai_idx);
    if (side_has_condition(ai_side, SC_TAILWIND)) return {{-40, 1.0}};
    const SideState& pl_side = side_at(state, 1 - ai_idx);
    bool useful = false;
    for (int ai_i : ai_side.active_indices) {
        if (ai_side.team[ai_i].fainted) continue;
        int32_t ai_spe = cpp_effective_stat(ai_side.team[ai_i], 5);
        for (int pl_i : pl_side.active_indices) {
            if (pl_side.team[pl_i].fainted) continue;
            int32_t pl_spe = cpp_effective_stat(pl_side.team[pl_i], 5);
            if (ai_spe < pl_spe) { useful = true; break; }
        }
        if (useful) break;
    }
    return useful ? ScoreDistC{{9, 1.0}} : ScoreDistC{{5, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_trick_room
// ---------------------------------------------------------------------------
ScoreDistC dist_trick_room(const BattleState& state, int ai_idx) {
    if (has_pseudo_weather(state, PW_TRICK_ROOM)) return {{-20, 1.0}};
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    int32_t ai_spe = cpp_effective_stat(ai_mon, 5);
    int32_t pl_spe = cpp_effective_stat(pl_mon, 5);
    return (ai_spe < pl_spe) ? ScoreDistC{{10, 1.0}} : ScoreDistC{{5, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_terrain
// ---------------------------------------------------------------------------
ScoreDistC dist_terrain(const BattleState& state, int ai_idx) {
    if (state.terrain != 0) return {{-40, 1.0}};
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    return (ai_mon.item == ITM_TERRAIN_EXTENDER) ? ScoreDistC{{9, 1.0}} : ScoreDistC{{8, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_poison_move
// ---------------------------------------------------------------------------
ScoreDistC dist_poison_move(const BattleState& state, int ai_idx, int32_t move_id) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    // Toxic blocked on Poison/Steel unless Corrosion
    if (move_id == 92 /*TOXIC*/) {  // Move.TOXIC = 92
        bool blocked = false;
        for (int32_t t : pl_mon.types)
            if (t == TYPE_POISON || t == TYPE_STEEL) { blocked = true; break; }
        if (blocked && ai_mon.ability != AB_CORROSION) return {{-40, 1.0}};
    }
    if (pl_mon.status != STATUS_NONE) return {{-20, 1.0}};
    return {{6, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_will_o_wisp
// ---------------------------------------------------------------------------
ScoreDistC dist_will_o_wisp(const BattleState& state, int ai_idx) {
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);
    for (int32_t t : pl_mon.types)
        if (t == TYPE_FIRE) return {{-20, 1.0}};
    if (pl_mon.status != STATUS_NONE) return {{-20, 1.0}};
    return {{7, 0.37}, {6, 0.63}};
}

// ---------------------------------------------------------------------------
// _dist_status_special
// ---------------------------------------------------------------------------
ScoreDistC dist_status_special(const BattleState& state, int ai_idx, int32_t move_id,
                               const PokemonState& ai_mon, const PokemonState& pl_mon,
                               bool ai_fst) {
    // Role Play: -20 in singles
    if (move_id == MV_ROLE_PLAY) {
        if (state.format != FMT_DOUBLES) return {{-20, 1.0}};
        const SideState& ai_side = side_at(state, ai_idx);
        for (size_t pi = 1; pi < ai_side.active_indices.size(); ++pi) {
            int slot = ai_side.active_indices[pi];
            const PokemonState& partner = ai_side.team[slot];
            if (!partner.fainted
                && ai_set_contains(ROLE_PLAY_VALUABLE_ABILITIES, N_ROLE_PLAY_VALUABLE_ABILITIES, partner.ability)
                && partner.ability != ai_mon.ability)
                return {{9, 1.0}};
        }
        return {{-20, 1.0}};
    }

    // Imprison
    if (move_id == MV_IMPRISON) {
        const SideState& pl_side = side_at(state, 1 - ai_idx);
        if (!pl_side.imprisoned_moves.empty()) return {{-20, 1.0}};
        // Check if AI and player share a move
        for (int slot = 0; slot < 4; ++slot) {
            int32_t ai_mid = move_id_at(ai_mon, slot);
            if (ai_mid == MV_NONE) continue;
            for (int pslot = 0; pslot < 4; ++pslot) {
                int32_t pl_mid = move_id_at(pl_mon, pslot);
                if (pl_mid == MV_NONE) continue;
                if (ai_mid == pl_mid) return {{9, 1.0}};
            }
        }
        return {{-20, 1.0}};
    }

    // Sleep Talk
    if (move_id == MV_SLEEP_TALK) {
        return (ai_mon.status == STATUS_SLEEP) ? ScoreDistC{{6, 1.0}} : ScoreDistC{{-40, 1.0}};
    }

    // Leech Seed
    if (move_id == MV_LEECH_SEED) {
        for (int32_t t : pl_mon.types)
            if (t == TYPE_GRASS) return {{-20, 1.0}};
        if (pl_mon.volatiles & VOL_LEECH_SEEDED) return {{-20, 1.0}};
        return {{6, 1.0}};
    }

    // Final Gambit
    if (move_id == MV_FINAL_GAMBIT) {
        if (ai_fst && ai_mon.hp > pl_mon.hp) return {{8, 1.0}};
        if (ai_fst && player_can_ko_ai(state, ai_idx)) return {{7, 1.0}};
        return {{6, 1.0}};
    }

    // Sleep moves (Yawn, Hypnosis, Sing, Grass Whistle, Dark Void): identical scoring.
    if (move_id == MV_YAWN || move_id == MV_HYPNOSIS || move_id == MV_SING
        || move_id == MV_GRASS_WHISTLE || move_id == MV_DARK_VOID) {
        if (pl_mon.status != STATUS_NONE) return {{-20, 1.0}};
        if (state.terrain == TE_ELECTRIC || state.terrain == TE_MISTY) return {{-20, 1.0}};
        if (pl_mon.ability == AB_INSOMNIA || pl_mon.ability == AB_VITAL_SPIRIT
            || pl_mon.ability == AB_SWEET_VEIL) return {{-20, 1.0}};
        return {{6, 1.0}};
    }

    // Scary Face
    if (move_id == MV_SCARY_FACE) {
        return ai_fst ? ScoreDistC{{-20, 1.0}} : ScoreDistC{{6, 1.0}};
    }

    // Helping Hand / Follow Me: 0 in singles (+6 default - 6 singles penalty)
    if (move_id == MV_HELPING_HAND || move_id == MV_FOLLOW_ME) {
        return (state.format != FMT_DOUBLES) ? ScoreDistC{{0, 1.0}} : ScoreDistC{{6, 1.0}};
    }

    // Weather moves: -40 if target weather already active
    if (ai_set_contains(WEATHER_MOVE_IDS, N_WEATHER_MOVES, move_id)) {
        // Find the target weather for this move
        for (int i = 0; i < N_WEATHER_MOVES; ++i) {
            if (WEATHER_MOVE_IDS[i] == move_id) {
                if (state.weather == WEATHER_MOVE_WEATHERS[i]) return {{-40, 1.0}};
                return {{6, 1.0}};
            }
        }
    }

    // Taunt
    if (move_id == MV_TAUNT) {
        if (pl_mon.volatiles & VOL_TAUNT_ACTIVE) return {{-40, 1.0}};
        bool tr_active = has_pseudo_weather(state, PW_TRICK_ROOM);
        bool has_tr = false;
        for (int slot = 0; slot < 4; ++slot)
            if (move_id_at(pl_mon, slot) == MV_TRICK_ROOM) { has_tr = true; break; }
        if (has_tr && !tr_active) return {{9, 1.0}};
        bool has_defog = false;
        for (int slot = 0; slot < 4; ++slot)
            if (move_id_at(pl_mon, slot) == MV_DEFOG) { has_defog = true; break; }
        const SideState& ai_side = side_at(state, ai_idx);
        bool has_aurora_veil = side_has_condition(ai_side, SC_AURORA_VEIL);
        if (has_defog && has_aurora_veil && ai_fst) return {{9, 1.0}};
        return {{5, 1.0}};
    }

    // Baton Pass
    if (move_id == MV_BATON_PASS) {
        bool has_sub = (ai_mon.volatiles & VOL_SUBSTITUTE) != 0;
        bool has_boost = false;
        for (int i = 0; i < 7; ++i)
            if (mon_stage(ai_mon, i) > 0) { has_boost = true; break; }
        if (has_sub || has_boost) return {{14, 1.0}};
        int ai_living = 0;
        for (const auto& m : side_at(state, ai_idx).team) if (!m.fainted) ++ai_living;
        if (ai_living == 1) return {{-20, 1.0}};
        return {{0, 1.0}};
    }

    // Memento
    if (move_id == MV_MEMENTO) {
        int ai_living = 0;
        for (const auto& m : side_at(state, ai_idx).team) if (!m.fainted) ++ai_living;
        if (ai_living == 1) return {{-40, 1.0}};
        double hp_pct = (double)ai_mon.hp / ai_mon.max_hp;
        if (hp_pct < 0.10) return {{16, 1.0}};
        if (hp_pct < 0.33) return {{14, 0.70}, {6, 0.30}};
        if (hp_pct < 0.66) return {{13, 0.50}, {6, 0.50}};
        return {{13, 0.05}, {6, 0.95}};
    }

    // Encore
    if (move_id == MV_ENCORE) {
        if (pl_mon.volatiles & VOL_ENCORE_ACTIVE) return {{-40, 1.0}};
        if (pl_mon.last_used_slot == -1) return {{-40, 1.0}};
        if (!ai_fst) return {{5, 0.5}, {6, 0.5}};
        return {{6, 1.0}};
    }

    // Counter / Mirror Coat
    if (move_id == MV_COUNTER || move_id == MV_MIRROR_COAT) {
        bool is_counter = (move_id == MV_COUNTER);
        if (is_counter) {
            for (int32_t t : pl_mon.types)
                if (t == TYPE_GHOST) return {{-20, 1.0}};
        } else {
            for (int32_t t : pl_mon.types)
                if (t == TYPE_DARK) return {{-20, 1.0}};
        }
        int32_t relevant_cat = is_counter ? CAT_PHYSICAL : CAT_SPECIAL;
        if (!player_has_split(pl_mon, relevant_cat)) return {{-20, 1.0}};
        if (player_can_ko_ai(state, ai_idx)
            && ai_mon.item != ITM_FOCUS_SASH
            && !(ai_mon.ability == AB_STURDY && ai_mon.hp == ai_mon.max_hp))
            return {{-20, 1.0}};

        int32_t other_cat = is_counter ? CAT_SPECIAL : CAT_PHYSICAL;
        bool player_only_split = !player_has_split(pl_mon, other_cat);

        // Check if player has any STATUS moves with PP>0
        bool pl_has_status = false;
        for (int slot = 0; slot < 4; ++slot) {
            int32_t mid = move_id_at(pl_mon, slot);
            if (mid == MV_NONE) continue;
            if (move_pp_at(pl_mon, slot) == 0) continue;
            const MoveData* md = ai_move_data_get(mid);
            if (md && (int32_t)md->category == CAT_STATUS) { pl_has_status = true; break; }
        }

        int base = 6;
        if (player_only_split) {
            if (player_can_ko_ai(state, ai_idx)) {
                base = 8;
            } else {
                // Complex expansion: [(8,0.80),(6,0.20)] then ai_fst and pl_has_status expansions
                ScoreDistC dist = {{8, 0.80}, {6, 0.20}};
                if (ai_fst) {
                    ScoreDistC nd;
                    for (auto [s, p] : dist) { nd.push_back({s, p * 0.75}); nd.push_back({s-1, p * 0.25}); }
                    dist = nd;
                }
                if (pl_has_status) {
                    ScoreDistC nd;
                    for (auto [s, p] : dist) { nd.push_back({s, p * 0.75}); nd.push_back({s-1, p * 0.25}); }
                    dist = nd;
                }
                return dist;
            }
        }
        ScoreDistC dist = {{base, 1.0}};
        if (ai_fst) {
            ScoreDistC nd;
            for (auto [s, p] : dist) { nd.push_back({s, p * 0.75}); nd.push_back({s-1, p * 0.25}); }
            dist = nd;
        }
        if (pl_has_status) {
            ScoreDistC nd;
            for (auto [s, p] : dist) { nd.push_back({s, p * 0.75}); nd.push_back({s-1, p * 0.25}); }
            dist = nd;
        }
        return dist;
    }

    // Magnet Rise
    if (move_id == MV_MAGNET_RISE) {
        if (has_timed_volatile(ai_mon, VE_MAGNET_RISE)) return {{-40, 1.0}};
        if (ai_fst) {
            for (int slot = 0; slot < 4; ++slot) {
                int32_t mid = move_id_at(pl_mon, slot);
                if (mid == MV_NONE) continue;
                if (move_pp_at(pl_mon, slot) == 0) continue;
                const MoveData* md = ai_move_data_get(mid);
                if (md && (int32_t)md->move_type == TYPE_GROUND && md->base_power > 0)
                    return {{8, 1.0}};
            }
        }
        return {{5, 1.0}};
    }

    return {{6, 1.0}};
}

// ---------------------------------------------------------------------------
// _dist_damage
// ---------------------------------------------------------------------------
ScoreDistC dist_damage(const BattleState& state, int ai_idx, int32_t move_id,
                       const MoveData& md, double p_highest, bool kills, bool ai_fst) {
    const PokemonState& ai_mon = active_mon(state, ai_idx);
    const PokemonState& pl_mon = active_mon(state, 1 - ai_idx);

    // Rollout: always +7
    if (move_id == MV_ROLLOUT) return {{7, 1.0}};

    // Relic Song: Meloetta form-dependent
    if (move_id == MV_RELIC_SONG) {
        return (ai_mon.species == SP_MELOETTA_PIROUETTE)
            ? ScoreDistC{{-20, 1.0}} : ScoreDistC{{10, 1.0}};
    }

    // Meteor Beam: Power Herb conditional
    if (move_id == MV_METEOR_BEAM) {
        return (ai_mon.item == ITM_POWER_HERB) ? ScoreDistC{{9, 1.0}} : ScoreDistC{{-20, 1.0}};
    }

    // Contrary: treat Overheat/Leaf Storm/Superpower as setup when not HD and not killing
    if (ai_mon.ability == AB_CONTRARY && !kills && p_highest <= 0.0
        && (move_id == MV_OVERHEAT || move_id == MV_LEAF_STORM || move_id == MV_SUPERPOWER)) {
        return is_incapacitated(pl_mon) ? ScoreDistC{{9, 1.0}} : ScoreDistC{{6, 1.0}};
    }

    // Fake Out
    bool fake_out_first_turn = false;
    if (move_id == MV_FAKE_OUT) {
        if (pl_mon.ability == AB_SHIELD_DUST || pl_mon.ability == AB_INNER_FOCUS)
            return {{-40, 1.0}};
        if (ai_mon.turns_in_battle != 0) return {{-40, 1.0}};
        // Type immunity check
        bool fo_immune = false;
        for (int32_t t : pl_mon.types) {
            float eff = cpp_type_effectiveness((int32_t)md.move_type, t);
            if (eff == 0.0f && pl_mon.item != ITM_RING_TARGET) { fo_immune = true; break; }
        }
        if (fo_immune) return {{-40, 1.0}};
        fake_out_first_turn = true;
    }

    // First Impression: -50 after first turn
    if (move_id == MV_FIRST_IMPRESSION && ai_mon.turns_in_battle > 0) return {{-50, 1.0}};

    // Fell Stinger: forced score when killing and Atk not maxed
    if (move_id == MV_FELL_STINGER && kills && ai_mon.stage0 < 6) {
        return ai_fst ? ScoreDistC{{21, 0.8}, {23, 0.2}} : ScoreDistC{{15, 0.8}, {17, 0.2}};
    }

    // Psychic Terrain blocks priority
    if (state.terrain == TE_PSYCHIC && md.priority > 0) return {{-40, 1.0}};

    // Fixed-damage moves: -40 if type-immune
    if (is_fixed_damage_rank_move(move_id)) {
        if (is_type_immune(md, pl_mon)) return {{-40, 1.0}};
    }

    // Explosion / Self-Destruct / Misty Explosion
    if (move_id == MV_EXPLOSION || move_id == MV_SELF_DESTRUCT || move_id == MV_MISTY_EXPLOSION) {
        if (is_type_immune(md, pl_mon)) return {{-40, 1.0}};
        int ai_living = 0, pl_living = 0;
        for (const auto& m : side_at(state, ai_idx).team) if (!m.fainted) ++ai_living;
        for (const auto& m : side_at(state, 1 - ai_idx).team) if (!m.fainted) ++pl_living;
        if (ai_living == 1 && pl_living >= 2) return {{-40, 1.0}};
        if (!kills) {
            double ai_hp_pct = (double)ai_mon.hp / ai_mon.max_hp;
            ScoreDistC base_dist;
            if (ai_hp_pct < 0.10)      base_dist = {{10, 1.0}};
            else if (ai_hp_pct < 0.33) base_dist = {{8, 0.70}, {0, 0.30}};
            else if (ai_hp_pct < 0.66) base_dist = {{7, 0.50}, {0, 0.50}};
            else                       base_dist = {{7, 0.05}, {0, 0.95}};
            if (ai_living == 1 && pl_living == 1) {
                for (auto& [s, p] : base_dist) s -= 1;
            }
            return base_dist;
        }
        // Kill case falls through
    }

    // Base kill/HD distribution
    ScoreDistC base_dist;
    if (kills) {
        int kb = ai_fst ? 6 : 3;
        int moxie_bonus = ai_set_contains(MOXIE_ABILITIES, N_MOXIE_ABILITIES, ai_mon.ability) ? 1 : 0;
        base_dist = {{6 + kb + moxie_bonus, 0.8}, {8 + kb + moxie_bonus, 0.2}};
    } else if (p_highest <= 0.0) {
        base_dist = {{0, 1.0}};
    } else if (p_highest >= 1.0) {
        base_dist = {{6, 0.8}, {8, 0.2}};
    } else {
        base_dist = {{6, 0.8 * p_highest}, {8, 0.2 * p_highest}, {0, 1.0 - p_highest}};
    }

    // Acid Spray: +6 bonus
    if (move_id == MV_ACID_SPRAY) {
        for (auto& [s, p] : base_dist) s += 6;
    }

    // Fake Out first-turn: +9 bonus
    if (fake_out_first_turn) {
        for (auto& [s, p] : base_dist) s += 9;
    }

    // Priority bonus (+11): AI slower, player can KO AI, move is priority
    bool is_priority_move = (md.priority > 0)
        || (move_id == MV_GRASSY_GLIDE && state.terrain == TE_GRASSY);
    if (player_can_ko_ai(state, ai_idx) && !ai_fst && is_priority_move) {
        for (auto& [s, p] : base_dist) s += 11;
    }

    // Future Sight: compute independently
    if (move_id == MV_FUTURE_SIGHT) {
        int32_t fs_dmg = cpp_expected_damage(ai_mon, move_id, pl_mon, state, MAX_LUCK_C,
                                             -1, false, -1);
        if (fs_dmg >= pl_mon.hp) {
            int kb = ai_fst ? 6 : 3;
            int moxie_bonus = ai_set_contains(MOXIE_ABILITIES, N_MOXIE_ABILITIES, ai_mon.ability) ? 1 : 0;
            return {{6 + kb + moxie_bonus, 0.8}, {8 + kb + moxie_bonus, 0.2}};
        }
        int score = (ai_fst && player_can_ko_ai(state, ai_idx)) ? 8 : 6;
        return {{score, 1.0}};
    }

    // Trapping moves: always +6/+8, own kill check
    if (is_trapping(move_id)) {
        int32_t tm_dmg = cpp_expected_damage(ai_mon, move_id, pl_mon, state, MAX_LUCK_C,
                                             -1, false, -1);
        if (tm_dmg >= pl_mon.hp) {
            int kb = ai_fst ? 6 : 3;
            int moxie_bonus = ai_set_contains(MOXIE_ABILITIES, N_MOXIE_ABILITIES, ai_mon.ability) ? 1 : 0;
            return {{6 + kb + moxie_bonus, 0.8}, {8 + kb + moxie_bonus, 0.2}};
        }
        return {{6, 0.8}, {8, 0.2}};
    }

    // Sucker Punch last-turn penalty
    if (move_id == MV_SUCKER_PUNCH && ai_mon.sucker_punch_last_turn) {
        ScoreDistC nd;
        for (auto [s, p] : base_dist) { nd.push_back({s - 20, p * 0.5}); nd.push_back({s, p * 0.5}); }
        base_dist = nd;
    }

    // Pursuit
    if (move_id == MV_PURSUIT && !kills) {
        double pl_hp_pct = (double)pl_mon.hp / pl_mon.max_hp;
        if (pl_hp_pct <= 0.20) {
            for (auto& [s, p] : base_dist) s += 10;
        } else if (pl_hp_pct <= 0.40) {
            ScoreDistC nd;
            for (auto [s, p] : base_dist) { nd.push_back({s + 8, p * 0.5}); nd.push_back({s, p * 0.5}); }
            base_dist = nd;
        }
        if (ai_fst) for (auto& [s, p] : base_dist) s += 3;
    } else if (move_id == MV_PURSUIT && kills) {
        for (auto& [s, p] : base_dist) s += 10;
        if (ai_fst) for (auto& [s, p] : base_dist) s += 3;
    }

    // Speed-reduction moves: +6 or +5 when not HD and not killing
    if (ai_set_contains(SPEED_REDUCTION_MOVES, N_SPEED_REDUCTION_MOVES, move_id) && !kills) {
        bool all_zero = true;
        for (auto [s, p] : base_dist) if (s != 0) { all_zero = false; break; }
        if (all_zero) {
            bool blocked = ai_set_contains(STAT_REDUCTION_ABILITIES, N_STAT_REDUCTION_ABILITIES,
                                           pl_mon.ability);
            return (!blocked && !ai_fst) ? ScoreDistC{{6, 1.0}} : ScoreDistC{{5, 1.0}};
        }
    }

    // Stat-reduction damaging moves: +6 or +5 when not HD and not killing
    if (ai_set_contains(STAT_REDUCTION_DAMAGE_MOVES, N_STAT_REDUCTION_DAMAGE_MOVES, move_id) && !kills) {
        bool all_zero = true;
        for (auto [s, p] : base_dist) if (s != 0) { all_zero = false; break; }
        if (all_zero) {
            bool physical_move = (move_id == MV_TROP_KICK || move_id == MV_BREAKING_SWIPE);
            int32_t relevant_split = physical_move ? CAT_PHYSICAL : CAT_SPECIAL;
            bool has_split = player_has_split(pl_mon, relevant_split);
            bool blocked = ai_set_contains(STAT_REDUCTION_ABILITIES, N_STAT_REDUCTION_ABILITIES,
                                           pl_mon.ability);
            return (!blocked && has_split) ? ScoreDistC{{6, 1.0}} : ScoreDistC{{5, 1.0}};
        }
    }

    // Flame Charge: +6 when AI slower, 0 when AI faster
    if (move_id == MV_FLAME_CHARGE && !kills) {
        bool all_zero = true;
        for (auto [s, p] : base_dist) if (s != 0) { all_zero = false; break; }
        if (all_zero) {
            return ai_fst ? ScoreDistC{{0, 1.0}} : ScoreDistC{{6, 1.0}};
        }
    }

    // Smack Down / Thousand Arrows: +6 grounding bonus if player is groundable
    if (move_id == MV_SMACK_DOWN || move_id == MV_THOUSAND_ARROWS) {
        bool already_grounded = has_timed_volatile(pl_mon, VE_GROUNDED);
        bool groundable = false;
        for (int32_t t : pl_mon.types) if (t == TYPE_FLYING) { groundable = true; break; }
        if (!groundable && pl_mon.ability == 26 /* LEVITATE */) groundable = true; // Levitate=26
        if (groundable && !already_grounded) {
            for (auto& [s, p] : base_dist) s += 6;
        }
    }

    // High-crit SE bonus: +1 at 50% rate
    if (ai_set_contains(HIGH_CRIT_MOVES, N_HIGH_CRIT_MOVES, move_id)
        && is_move_super_effective(move_id, pl_mon)) {
        ScoreDistC nd;
        for (auto [s, p] : base_dist) {
            nd.push_back({s, p * 0.5});
            nd.push_back({s + 1, p * 0.5});
        }
        base_dist = nd;
    }

    return base_dist;
}

} // namespace ai_scorer
