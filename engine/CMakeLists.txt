cmake_minimum_required(VERSION 3.15)
project(nuzlocke_engine_cpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Release throughput tuning (single-machine build; not distributed):
#  - IPO/LTO: cross-TU inlining of the many small hot leaf functions.
#  - -march=native: emit ISA for THIS CPU only. Binary is not portable — do not
#    ship the resulting .so to a different microarchitecture.
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()
include(CheckIPOSupported)
check_ipo_supported(RESULT _ipo_ok OUTPUT _ipo_msg)
if(_ipo_ok)
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE ON)
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELWITHDEBINFO ON)
endif()
include(CheckCXXCompilerFlag)
check_cxx_compiler_flag("-march=native" _march_native_ok)
if(_march_native_ok)
    add_compile_options($<$<NOT:$<CONFIG:Debug>>:-march=native>)
    add_compile_options($<$<NOT:$<CONFIG:Debug>>:-mtune=native>)
endif()

# Parity: disable FMA multiply-add contraction. GCC default -ffp-contract=fast fuses
# a*b+c into one FMA that rounds ONCE; CPython never fuses (rounds twice), causing
# 1-ULP divergences (e.g. cpp_calc_exp_gain off-by-one). -ffp-contract=off restores
# unfused double semantics matching Python. Applied to ALL configs. Monotonic toward
# parity — can only remove divergences, never introduce them. Also on link line for LTO.
check_cxx_compiler_flag("-ffp-contract=off" _ffp_contract_off_ok)
if(_ffp_contract_off_ok)
    add_compile_options(-ffp-contract=off)
    add_link_options(-ffp-contract=off)
endif()

# nuzlocke_core: static library with all engine source files (excludes lookup.cpp,
# which was also excluded in the old single-target build).
add_library(nuzlocke_core STATIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/codec.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/stats.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/lookup_species.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/lookup_move.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/lookup_item.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/damage.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/type_chart_lookup.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/effects.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/effects_entry.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/post_hit.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/residuals.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/species_types_lookup.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/species_exp_lookup.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/species_weight_lookup.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/exp.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/core_leaf.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/move_exec_helpers.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/move_exec_premove.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/move_exec_guards.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/move_exec_damage.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/move_exec.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/turn.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/state_eq.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/orchestrate.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/forced_trace.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ai_policy.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ai_damage.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ai_scorer.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ai_scorer_dist.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ai_analytic.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/game_driver.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver_turn.cpp
)
# Required: static lib links into a pybind11 shared module, so all objects need PIC.
set_target_properties(nuzlocke_core PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(nuzlocke_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/generated
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party
)

# Locate pybind11 from the venv; caller must set pybind11_DIR.
find_package(pybind11 REQUIRED)

# pybind11 module: only the binding glue; all engine logic comes from nuzlocke_core.
pybind11_add_module(nuzlocke_engine_cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/bindings/module.cpp
)
target_link_libraries(nuzlocke_engine_cpp PRIVATE nuzlocke_core)

# nuzlocke_solver: solver algorithms (one-way dependency on nuzlocke_core; core must
# never depend on solver). Same compile flags as core are inherited via add_compile_options
# at the top of this file.
add_library(nuzlocke_solver STATIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/engine_queries.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/move_scope.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/bucket/concede.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/state_codec.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/question.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/transition_oracle.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/action_space.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/matchup_gen.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/audit/audit_core.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/audit/audit_analytic_core.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/bsolver.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/analytic/analytic.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/bucket/breakpoints.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/bucket/ai_breakpoints.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/bucket/bucket.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/bucket/expand.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/bucket/win_solver.cpp
)
set_target_properties(nuzlocke_solver PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_link_libraries(nuzlocke_solver PUBLIC nuzlocke_core)
# Solver headers are under src/solver/; consumers include them as "solver/foo.h".
target_include_directories(nuzlocke_solver PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# audit_oracle: standalone completeness + probability audit harness for the transition oracle.
# EXCLUDE_FROM_ALL: never built by default; build on demand:
#   cmake --build engine/build --target audit_oracle
add_executable(audit_oracle EXCLUDE_FROM_ALL
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/audit/audit_oracle.cpp)
target_link_libraries(audit_oracle PRIVATE nuzlocke_solver nuzlocke_core)
target_compile_definitions(audit_oracle PRIVATE
    NUZLOCKE_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")

# bcheck: cross-check bsolver-exact vs naive reference walker on generator matchups.
# EXCLUDE_FROM_ALL: never built by default; build on demand:
#   cmake --build engine/build --target bcheck
add_executable(bcheck EXCLUDE_FROM_ALL
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/audit/bcheck.cpp)
target_link_libraries(bcheck PRIVATE nuzlocke_solver nuzlocke_core)
target_compile_definitions(bcheck PRIVATE
    NUZLOCKE_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")

# ccheck: pessimal/coarse-vs-exact theorem audit.
# EXCLUDE_FROM_ALL: never built by default; build on demand:
#   cmake --build engine/build --target ccheck
add_executable(ccheck EXCLUDE_FROM_ALL
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/audit/ccheck.cpp)
target_link_libraries(ccheck PRIVATE nuzlocke_solver nuzlocke_core)
target_compile_definitions(ccheck PRIVATE
    NUZLOCKE_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")

# audit_analytic: tiered analytic-certifier audit (analytic → pessimal → exact verification).
# EXCLUDE_FROM_ALL: never built by default; build on demand:
#   cmake --build engine/build --target audit_analytic
add_executable(audit_analytic EXCLUDE_FROM_ALL
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/audit/audit_analytic.cpp)
target_link_libraries(audit_analytic PRIVATE nuzlocke_solver nuzlocke_core)
target_compile_definitions(audit_analytic PRIVATE
    NUZLOCKE_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")

# analytic_trace: single-matchup analytic trace printer and oracle-child inspector.
# EXCLUDE_FROM_ALL: never built by default; build on demand:
#   cmake --build engine/build --target analytic_trace
add_executable(analytic_trace EXCLUDE_FROM_ALL
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/audit/analytic_trace.cpp)
target_link_libraries(analytic_trace PRIVATE nuzlocke_solver nuzlocke_core)
target_compile_definitions(analytic_trace PRIVATE
    NUZLOCKE_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")

# solver_trace: single-case debug trace tool for diagnosing oracle failures.
# EXCLUDE_FROM_ALL: build on demand:
#   cmake --build engine/build --target solver_trace
add_executable(solver_trace EXCLUDE_FROM_ALL
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/audit/solver_trace.cpp)
target_link_libraries(solver_trace PRIVATE nuzlocke_solver nuzlocke_core)
target_compile_definitions(solver_trace PRIVATE
    NUZLOCKE_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")

# verify_policy_sampling: one-time tool to verify AI policy sampling == analytic distribution.
# EXCLUDE_FROM_ALL: not a regular build target.
add_executable(verify_policy_sampling EXCLUDE_FROM_ALL
    ${CMAKE_CURRENT_SOURCE_DIR}/src/solver/audit/verify_policy_sampling.cpp)
target_link_libraries(verify_policy_sampling PRIVATE nuzlocke_solver nuzlocke_core)
target_compile_definitions(verify_policy_sampling PRIVATE
    NUZLOCKE_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")

# Native C++ tests via Catch2 v3 (fetched at configure time).
include(FetchContent)
FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2
    GIT_TAG        v3.7.1
)
FetchContent_MakeAvailable(Catch2)

enable_testing()
include(CTest)

file(GLOB NATIVE_TEST_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/tests/*.cpp)
add_executable(nuzlocke_native_tests ${NATIVE_TEST_SOURCES})
target_link_libraries(nuzlocke_native_tests PRIVATE nuzlocke_solver nuzlocke_core Catch2::Catch2WithMain)
# NUZLOCKE_REPO_ROOT: absolute path to repo root, used by matchup_gen tests to locate data files.
target_compile_definitions(nuzlocke_native_tests PRIVATE
    NUZLOCKE_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/.."
)

add_test(NAME native_tests COMMAND nuzlocke_native_tests)

# D5 seam benchmark: standalone throughput harness for the solver hot path and the
# JSON bridge overhead. Deliberately EXCLUDE_FROM_ALL and NOT an add_test() — it must
# never slow the default build or the correctness ctest run. Build on demand:
#   cmake --build build --target nuzlocke_bench_seam
add_executable(nuzlocke_bench_seam EXCLUDE_FROM_ALL
    ${CMAKE_CURRENT_SOURCE_DIR}/bench/bench_solver_seam.cpp)
target_link_libraries(nuzlocke_bench_seam PRIVATE nuzlocke_core)

# bench_oracle: per-(state,action) wall-time and leaf-throughput benchmark for the
# transition oracle. EXCLUDE_FROM_ALL: never built by default; build on demand:
#   cmake --build engine/build --target bench_oracle
add_executable(bench_oracle EXCLUDE_FROM_ALL
    ${CMAKE_CURRENT_SOURCE_DIR}/bench/bench_oracle.cpp)
target_link_libraries(bench_oracle PRIVATE nuzlocke_solver nuzlocke_core)
target_compile_definitions(bench_oracle PRIVATE
    NUZLOCKE_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")
