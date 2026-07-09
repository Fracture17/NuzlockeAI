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
target_link_libraries(nuzlocke_native_tests PRIVATE nuzlocke_core Catch2::Catch2WithMain)

add_test(NAME native_tests COMMAND nuzlocke_native_tests)
