// C++ port of end-of-turn residuals (src/engine/residuals.py, C1.5).
// Reproduces _apply_residuals state mutations bit-for-bit; Python log() calls omitted.
// Unported branches (Moody, EXP flush on residual KO) throw "unported: ...".
// random_mode=true with rng=nullptr throws loudly (misconfiguration).
#pragma once
#ifndef NUZLOCKE_RESIDUALS_H
#define NUZLOCKE_RESIDUALS_H

#include "state.h"
#include "effects.h"
#include "native_rng.h"   // NativeRng
#include <vector>

// Per-side deterministic luck (residuals read proc_threshold; berry/damage fields reuse EffectsLuck).
struct ResidualLuck {
    EffectsLuck side0;
    EffectsLuck side1;
};

// Context mirror for tib gating + EXP-flush stub gating.
struct ResidualCtx {
    bool ctx_present = false;        // false => behave as ctx is None (count all for tib)
    bool turn_start_active_null = true;            // true => tib counts every active slot
    std::vector<std::pair<int,int>> turn_start_active;  // (side_idx, team_idx) initiators
    bool has_exp_participants = false;             // gates exp flush
    // Per-active-slot participant team indices (ctx.exp_participants); mutated (cleared) on award.
    std::vector<std::vector<int32_t>> exp_participants;
    bool has_oracle = false;           // Moody/Starf use oracle; throws if it would fire
    bool random_mode = false;          // true = resolvers draw from rng
    NativeRng* rng   = nullptr;        // non-null iff random_mode=true
};

// _apply_residuals: full field-wide band pass + Wish/Future Sight, with per-slot EE/Wimp Out.
// Mutates state in place; appends Emergency-Exit pending switches.
void cpp_apply_residuals(BattleState& state, const ResidualLuck& luck,
                         const ResidualCtx& ctx,
                         std::vector<PendingSwitch>& pending_switches);

// Emergency Exit / Wimp Out crossing check for one battler at active_idx on side si.
// hp_before is the HP captured before residual damage. Exposed for native tests.
void emergency_exit_check(BattleState& s, int si, int active_idx, int hp_before,
                          std::vector<PendingSwitch>& pending);

#endif // NUZLOCKE_RESIDUALS_H
