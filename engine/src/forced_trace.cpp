// forced_trace_from_json implementation.
#include "forced_trace.h"

ForcedTrace forced_trace_from_json(const nlohmann::json& j) {
    ForcedTrace ft;

    // Parse rng entries.
    if (j.contains("rng") && !j["rng"].is_null()) {
        for (const auto& entry : j["rng"]) {
            int turn       = entry.at("turn").get<int>();
            int event      = entry.at("event").get<int>();
            int occurrence = entry.at("occurrence").get<int>();

            // Validate ranges before computing key (key() throws on bad values).
            uint64_t k = ForcedTrace::key(turn, event, occurrence);
            if (ft.rng.count(k))
                throw std::runtime_error(
                    "forced_trace_mismatch: duplicate rng entry turn="
                    + std::to_string(turn) + " event=" + std::to_string(event)
                    + " occ=" + std::to_string(occurrence));

            const auto& outcome = entry.at("outcome");
            ForcedOutcome fo;
            if (outcome.is_boolean()) {
                fo.kind = 2;
                fo.b    = outcome.get<bool>();
                fo.i    = 0;
                fo.d    = 0.0;
            } else if (outcome.is_number_integer()) {
                fo.kind = 0;
                fo.i    = outcome.get<int64_t>();
                fo.b    = false;
                fo.d    = 0.0;
            } else {
                fo.kind = 1;
                fo.d    = outcome.get<double>();
                fo.i    = 0;
                fo.b    = false;
            }
            ft.rng[k] = fo;
        }
    }

    // Parse answer entries.
    if (j.contains("answers") && !j["answers"].is_null()) {
        for (const auto& entry : j["answers"]) {
            ForcedAnswer fa;
            fa.turn  = entry.at("turn").get<int>();
            fa.event = entry.at("event").get<int>();
            fa.side  = entry.value("side", -1);
            fa.i0    = entry.value("i0", -1);
            fa.i1    = entry.value("i1", -1);

            if (entry.contains("actions_p0") && !entry["actions_p0"].is_null())
                fa.actions_p0 = entry["actions_p0"];
            else
                fa.actions_p0 = nullptr;

            if (entry.contains("actions_p1") && !entry["actions_p1"].is_null())
                fa.actions_p1 = entry["actions_p1"];
            else
                fa.actions_p1 = nullptr;

            ft.answers.push_back(std::move(fa));
        }
    }

    return ft;
}
