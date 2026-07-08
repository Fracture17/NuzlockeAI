# Tests for the C++ data codegen pipeline (C0.3).
# Verifies determinism, staleness detection, coverage, and spot-value correctness.
import importlib
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

# Ensure repo root is importable (pytest adds it, but be explicit for clarity)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT_PATH = os.path.join(_REPO_ROOT, "SCRIPTS", "gen_cpp_data.py")
_CPP_GENERATED = os.path.join(_REPO_ROOT, "engine", "generated")


def _import_codegen():
    """Import gen_cpp_data as a module so tests call real source code."""
    spec = importlib.util.spec_from_file_location("gen_cpp_data", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def codegen():
    return _import_codegen()


# ---------------------------------------------------------------------------
# Determinism: two runs into separate temp dirs must be byte-identical
# ---------------------------------------------------------------------------

def test_determinism(codegen):
    with tempfile.TemporaryDirectory() as dir_a, tempfile.TemporaryDirectory() as dir_b:
        codegen.generate(dir_a)
        codegen.generate(dir_b)

        files_a = sorted(os.listdir(dir_a))
        files_b = sorted(os.listdir(dir_b))
        assert files_a == files_b, "File lists differ between runs"
        assert len(files_a) > 0, "No files were generated"

        for filename in files_a:
            path_a = os.path.join(dir_a, filename)
            path_b = os.path.join(dir_b, filename)
            content_a = open(path_a, "rb").read()
            content_b = open(path_b, "rb").read()
            assert content_a == content_b, f"File {filename} differs between runs"


# ---------------------------------------------------------------------------
# Staleness pass: regenerate into cpp/generated/, then --check should exit 0
# ---------------------------------------------------------------------------

def test_staleness_check_passes_when_current(codegen):
    # First regenerate the committed headers so they're fresh
    codegen.generate(_CPP_GENERATED)

    result = subprocess.run(
        [sys.executable, _SCRIPT_PATH, "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"--check returned non-zero on fresh headers.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Staleness fail: mutate one header in a temp dir, --check must exit non-zero
# ---------------------------------------------------------------------------

def test_staleness_check_fails_on_drift():
    with tempfile.TemporaryDirectory() as drift_dir:
        # Copy committed headers to temp dir
        for fname in os.listdir(_CPP_GENERATED):
            shutil.copy(os.path.join(_CPP_GENERATED, fname), os.path.join(drift_dir, fname))

        # Mutate one header
        files = [f for f in os.listdir(drift_dir) if f.endswith(".h")]
        assert files, "No .h files found to mutate"
        mutated_file = files[0]
        path = os.path.join(drift_dir, mutated_file)
        original = open(path).read()
        with open(path, "w") as f:
            f.write(original + "\n// DELIBERATELY MUTATED\n")

        result = subprocess.run(
            [sys.executable, _SCRIPT_PATH, "--check", "--check-dir", drift_dir],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            "--check should have exited non-zero for drifted headers but didn't"
        )
        # The output should name the drifting file
        combined = result.stdout + result.stderr
        assert mutated_file in combined, (
            f"--check output should name '{mutated_file}' as drifting, got:\n{combined}"
        )


# ---------------------------------------------------------------------------
# Coverage: every SPECIES_DATA / MOVE_DATA / ITEM_DATA entry appears in headers
# ---------------------------------------------------------------------------

def test_species_coverage(codegen):
    from liveplay.data.species import SPECIES_DATA
    with tempfile.TemporaryDirectory() as out_dir:
        codegen.generate(out_dir)
        content = open(os.path.join(out_dir, "species_data.h")).read()

    # Each species key's integer value must appear in the header
    missing = []
    for species in SPECIES_DATA:
        # Check the enum value appears — emitted as the array index or struct field
        if str(species.value) not in content:
            missing.append(species)
    assert not missing, f"{len(missing)} species values missing from species_data.h: {missing[:5]}"

    # Count match: the number of data entries should equal len(SPECIES_DATA)
    assert content.count("// entry") == len(SPECIES_DATA) or _count_entries(content) == len(SPECIES_DATA), (
        f"Expected {len(SPECIES_DATA)} entries in species_data.h"
    )


def test_move_coverage(codegen):
    from liveplay.data.moves import MOVE_DATA
    with tempfile.TemporaryDirectory() as out_dir:
        codegen.generate(out_dir)
        content = open(os.path.join(out_dir, "move_data.h")).read()

    missing = []
    for move in MOVE_DATA:
        if str(move.value) not in content:
            missing.append(move)
    assert not missing, f"{len(missing)} move values missing from move_data.h: {missing[:5]}"

    assert _count_entries(content) == len(MOVE_DATA), (
        f"Expected {len(MOVE_DATA)} entries in move_data.h"
    )


def test_item_coverage(codegen):
    from liveplay.data.items import ITEM_DATA
    with tempfile.TemporaryDirectory() as out_dir:
        codegen.generate(out_dir)
        content = open(os.path.join(out_dir, "item_data.h")).read()

    missing = []
    for item in ITEM_DATA:
        if str(item.value) not in content:
            missing.append(item)
    assert not missing, f"{len(missing)} item values missing from item_data.h: {missing[:5]}"

    assert _count_entries(content) == len(ITEM_DATA), (
        f"Expected {len(ITEM_DATA)} entries in item_data.h"
    )


def _count_entries(content: str) -> int:
    """Count '// entry NAME' markers placed by codegen to mark each table row.

    Matches '// entry ' followed by an uppercase letter to avoid matching
    prose comments that happen to contain the word 'entry'."""
    import re
    return len(re.findall(r"// entry [A-Z]", content))


# ---------------------------------------------------------------------------
# Spot-value: known entries must match Python source values
# ---------------------------------------------------------------------------

def test_spot_value_species(codegen):
    from liveplay.data.species import SPECIES_DATA, Species
    with tempfile.TemporaryDirectory() as out_dir:
        codegen.generate(out_dir)
        content = open(os.path.join(out_dir, "species_data.h")).read()

    # Bulbasaur: base_hp=45, base_atk=49, base_def=49, types=(GRASS=4, POISON=7)
    bulba = SPECIES_DATA[Species.BULBASAUR]
    assert str(bulba.base_hp) in content
    assert str(bulba.base_atk) in content

    # Check Pikachu base speed (90) appears
    pika = SPECIES_DATA[Species.PIKACHU]
    assert str(pika.base_spe) in content


def test_spot_value_moves(codegen):
    from liveplay.data.moves import MOVE_DATA, Move
    with tempfile.TemporaryDirectory() as out_dir:
        codegen.generate(out_dir)
        content = open(os.path.join(out_dir, "move_data.h")).read()

    # Flamethrower: base_power=90, accuracy=100, type=FIRE(1), category=SPECIAL(1)
    ft = MOVE_DATA[Move.FLAMETHROWER]
    assert str(ft.base_power) in content
    assert str(ft.accuracy) in content

    # Tackle: base_power=40
    tackle = MOVE_DATA[Move.TACKLE]
    assert str(tackle.base_power) in content


def test_spot_value_natures(codegen):
    from liveplay.data.natures import NATURE_DATA, Nature, Stat
    with tempfile.TemporaryDirectory() as out_dir:
        codegen.generate(out_dir)
        content = open(os.path.join(out_dir, "nature_data.h")).read()

    # ADAMANT boosts ATK(1), lowers SPA(3)
    adamant = NATURE_DATA[Nature.ADAMANT]
    assert str(adamant.boosted.value) in content
    assert str(adamant.lowered.value) in content


# ---------------------------------------------------------------------------
# C1.1: Full inline stat-change arrays in move_data.h
# ---------------------------------------------------------------------------

def _parse_move_table_entry(content: str, move_name: str) -> str:
    """Extract the single line '// entry MOVE_NAME' struct literal from move_data.h."""
    for line in content.splitlines():
        if line.strip().endswith(f"// entry {move_name}"):
            return line.strip()
    raise AssertionError(f"No entry found for move {move_name}")


def _parse_secondary_stat_arrays(entry_line: str, is_secondary2: bool = False) -> tuple:
    """
    Extract (num_stat_changes, [(stat_idx, delta, self_flag), ...]) from an entry line.

    The entry line has two SecondaryEffect literals. Each SecondaryEffect ends with
    num_stat_changes, has_status, has_volatile, and now carries inline stat_changes arrays.
    We parse by splitting on the SecondaryEffect struct fields rather than full C parse.
    This is a targeted regex extraction keyed on the array field names.
    """
    import re
    # Find all SecondaryEffect sub-structs: look for 'sec_stat_changes = {...}' patterns
    # The generated struct has named fields via comments; we rely on positional parsing.
    # Secondary arrays are emitted as: { stat_idx, delta, self_flag } repeated.
    # We look for the sec_stat_changes array block: "{ {x,y,z}, {x,y,z}, ... }"
    # Strategy: find both SecondaryEffect blocks by locating the outer struct boundaries.
    # Each SecondaryEffect is bounded by braces. We extract them in order.
    sec_blocks = _extract_secondary_blocks(entry_line)
    if is_secondary2:
        block = sec_blocks[1]
    else:
        block = sec_blocks[0]
    return _parse_sec_block(block)


def _extract_secondary_blocks(entry_line: str) -> list:
    """Return the two SecondaryEffect struct literal strings from an entry line."""
    # The MoveData struct has: ... secondary, secondary2, move_id
    # Each SecondaryEffect is a brace-balanced sub-literal.
    # We walk the line finding top-level brace groups (depth 1 within the outer struct).
    # The outer struct itself is at depth 0; secondary structs are inner groups.
    depth = 0
    blocks = []
    current = []
    recording = False
    # Skip outer struct: find depth=1 brace groups that are the SecondaryEffect fields
    # The MoveData struct starts with { and contains nested structs for secondary/secondary2.
    # We collect all depth-1 groups (inner structs):
    i = 0
    while i < len(entry_line):
        c = entry_line[i]
        if c == '{':
            depth += 1
            if depth == 2:
                recording = True
                current = ['{']
            elif depth > 2 and recording:
                current.append(c)
        elif c == '}':
            if depth == 2 and recording:
                current.append('}')
                blocks.append(''.join(current))
                recording = False
                current = []
            elif depth > 2 and recording:
                current.append(c)
            depth -= 1
        else:
            if recording:
                current.append(c)
        i += 1
    # blocks now contains ALL depth-2 brace groups from the entry line.
    # We want only the SecondaryEffect ones (they contain stat_changes arrays).
    # The SecondaryEffect blocks are the ones that contain nested { } for the stat array.
    # Actually, with the new format, SecondaryEffect itself contains an array of structs,
    # making it depth-2 from MoveData, but the array elements are depth-3.
    # Filter: SecondaryEffect blocks will be large; non-secondary fields are scalars.
    # The secondary and secondary2 fields are the two largest brace groups.
    # Sort by length and take last two... but order matters. Instead, count nested braces.
    # Any block with nested { } is a SecondaryEffect (it contains the stat_changes array).
    sec_blocks = [b for b in blocks if '{' in b[1:]]  # has nested braces (not just opening)
    if len(sec_blocks) < 2:
        # Fallback: take the two longest blocks
        sec_blocks = sorted(blocks, key=len, reverse=True)[:2]
    return sec_blocks[:2]


def _parse_sec_block(block: str) -> tuple:
    """
    Parse a SecondaryEffect struct literal. Returns (num_stat_changes, pairs).

    Expected format (new):
        { chance, status, flinch,
          num_stat_changes, has_status, has_volatile,
          { {s0,d0,f0}, {s1,d1,f1}, ... },   <- stat_changes array
        }
    We extract num_stat_changes and the array entries.
    """
    import re
    # Extract the inner stat-changes array: find the innermost {...} that contains sub-{} entries
    # The block looks like: { ..., N, bool, bool, { {a,b,c}, ... } }
    # Find the last top-level brace group in block (the stat_changes array)
    inner = _find_last_nested_array(block)
    # Parse individual entries from inner: { stat_idx, delta, self_flag }
    pairs = re.findall(r'\{\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\}', inner)
    pairs = [(int(s), int(d), int(f)) for s, d, f in pairs]
    # Extract num_stat_changes: scalars before the inner array within the block
    pre_array = block[:block.index(inner)]
    scalars = re.findall(r'-?\d+|true|false', pre_array)
    # Struct field order: chance, status, flinch, volatile_confused, has_status, has_volatile, num_stat_changes
    # = 7 scalars before the stat_changes array.
    int_scalars = []
    for s in scalars:
        if s == 'true':
            int_scalars.append(1)
        elif s == 'false':
            int_scalars.append(0)
        else:
            int_scalars.append(int(s))
    # num_stat_changes is at index 6 (0-based) in the scalar sequence
    num_stat_changes = int_scalars[6] if len(int_scalars) >= 7 else 0
    return num_stat_changes, pairs


def _find_last_nested_array(block: str) -> str:
    """Return the last depth-1 (relative to block) brace-balanced sub-group in block.

    Scans block content (inside the outer { }) and returns the last brace group at depth 1
    within the content, which is the stat_changes inline array."""
    # Skip the outer braces: find content between first { and last }
    content_start = block.index('{') + 1
    content_end = block.rindex('}')
    content = block[content_start:content_end]

    # Walk from right within content to find the last depth-1 group
    depth = 0
    end = -1
    for i in range(len(content) - 1, -1, -1):
        if content[i] == '}':
            if depth == 0:
                end = i
            depth += 1
        elif content[i] == '{':
            depth -= 1
            if depth == 0 and end != -1:
                return content[i:end + 1]
    return '{}'


def _parse_self_stat_array(entry_line: str) -> tuple:
    """
    Extract (num_self_stat_changes, [(stat_idx, delta), ...]) from an entry line.

    self_stat_changes is a field on MoveData (not SecondaryEffect). In the new format it is
    emitted as: num_self_stat_changes, { {s0,d0}, {s1,d1}, ... }
    We locate it by finding the MoveData-level array (depth-1 from outer struct) that contains
    only 2-element entries.
    """
    import re
    # Find all depth-1 brace groups (direct children of MoveData outer struct)
    depth = 0
    blocks = []
    current = []
    recording = False
    for c in entry_line:
        if c == '{':
            depth += 1
            if depth == 2:
                recording = True
                current = ['{']
            elif depth > 2 and recording:
                current.append(c)
        elif c == '}':
            if depth == 2 and recording:
                current.append('}')
                blocks.append(''.join(current))
                recording = False
                current = []
            elif depth > 2 and recording:
                current.append(c)
            depth -= 1
        else:
            if recording:
                current.append(c)
    # The self_stat_changes array is a depth-2 block that has 2-element sub-entries
    # SecondaryEffect blocks have 3-element sub-entries; self array has 2-element
    self_blocks = []
    for b in blocks:
        # Look for { {a,b}, ... } pattern (2-element entries)
        two_el = re.findall(r'\{\s*-?\d+\s*,\s*-?\d+\s*\}', b)
        three_el = re.findall(r'\{\s*-?\d+\s*,\s*-?\d+\s*,\s*-?\d+\s*\}', b)
        if two_el and not three_el:
            self_blocks.append((b, two_el))
    if not self_blocks:
        return 0, []
    # Take the last one (self_stat_changes is after secondary fields in MoveData)
    block, entries = self_blocks[-1]
    pairs = [(int(s.strip('{ }').split(',')[0]), int(s.strip('{ }').split(',')[1])) for s in entries]
    # Extract count: find the integer immediately before this block in entry_line
    block_start = entry_line.rfind(block)
    pre = entry_line[:block_start]
    nums = re.findall(r'-?\d+', pre)
    count = int(nums[-1]) if nums else len(pairs)
    return count, pairs


class TestFullStatChangeArrays:
    """C1.1: Verify full inline stat-change arrays are emitted correctly."""

    @pytest.fixture(autouse=True)
    def _gen(self, codegen, tmp_path):
        codegen.generate(str(tmp_path))
        self.content = open(os.path.join(str(tmp_path), "move_data.h")).read()

    def test_ancient_power_secondary_stat_changes(self):
        """Ancient Power secondary must emit all 5 (stat_idx, delta, self_flag) entries."""
        from liveplay.data.moves import MOVE_DATA, Move
        expected = MOVE_DATA[Move.ANCIENT_POWER].secondary.stat_changes
        assert len(expected) == 5, "Test pre-condition: Ancient Power has 5 stat changes"

        entry = _parse_move_table_entry(self.content, "ANCIENT_POWER")
        num_changes, pairs = _parse_secondary_stat_arrays(entry)

        assert num_changes == 5, f"Expected num_stat_changes=5, got {num_changes}"
        assert len(pairs) >= 5, f"Expected at least 5 emitted pairs, got {len(pairs)}"
        for i, (stat_idx, delta, self_flag) in enumerate(expected):
            emitted_idx, emitted_delta, emitted_self = pairs[i]
            assert emitted_idx == stat_idx, f"pair[{i}] stat_idx: expected {stat_idx}, got {emitted_idx}"
            assert emitted_delta == delta, f"pair[{i}] delta: expected {delta}, got {emitted_delta}"
            assert emitted_self == (1 if self_flag else 0), f"pair[{i}] self: expected {self_flag}, got {emitted_self}"

    def test_v_create_self_stat_changes(self):
        """V-Create must emit all 3 self_stat_changes pairs."""
        from liveplay.data.moves import MOVE_DATA, Move
        expected = MOVE_DATA[Move.V_CREATE].self_stat_changes
        assert len(expected) == 3, "Test pre-condition: V-Create has 3 self_stat_changes"

        entry = _parse_move_table_entry(self.content, "V_CREATE")
        count, pairs = _parse_self_stat_array(entry)

        assert count == 3, f"Expected num_self_stat_changes=3, got {count}"
        for i, (stat_idx, delta) in enumerate(expected):
            assert pairs[i][0] == stat_idx, f"pair[{i}] stat_idx: expected {stat_idx}, got {pairs[i][0]}"
            assert pairs[i][1] == delta, f"pair[{i}] delta: expected {delta}, got {pairs[i][1]}"

    def test_superpower_self_stat_changes(self):
        """Superpower must emit 2 self_stat_changes pairs."""
        from liveplay.data.moves import MOVE_DATA, Move
        expected = MOVE_DATA[Move.SUPERPOWER].self_stat_changes
        assert len(expected) == 2, "Test pre-condition: Superpower has 2 self_stat_changes"

        entry = _parse_move_table_entry(self.content, "SUPERPOWER")
        count, pairs = _parse_self_stat_array(entry)

        assert count == 2, f"Expected num_self_stat_changes=2, got {count}"
        for i, (stat_idx, delta) in enumerate(expected):
            assert pairs[i][0] == stat_idx, f"pair[{i}] stat_idx: expected {stat_idx}, got {pairs[i][0]}"
            assert pairs[i][1] == delta, f"pair[{i}] delta: expected {delta}, got {pairs[i][1]}"

    def test_single_secondary_stat_change_unused_slots_zeroed(self):
        """A single-entry secondary (Psychic) must emit count=1 with remaining slots zeroed."""
        from liveplay.data.moves import MOVE_DATA, Move
        expected = MOVE_DATA[Move.PSYCHIC].secondary.stat_changes
        assert len(expected) == 1, "Test pre-condition: Psychic has 1 secondary stat change"

        entry = _parse_move_table_entry(self.content, "PSYCHIC")
        num_changes, pairs = _parse_secondary_stat_arrays(entry)

        assert num_changes == 1, f"Expected num_stat_changes=1, got {num_changes}"
        # The first pair must match
        stat_idx, delta, self_flag = expected[0]
        assert pairs[0][0] == stat_idx
        assert pairs[0][1] == delta
        # Remaining slots (indices 1-4) must be zero-padded
        for i in range(1, 5):
            assert pairs[i] == (0, 0, 0), f"Unused slot {i} not zeroed: {pairs[i]}"

    def test_max_constants_in_header(self):
        """Generated header must define MAX_SECONDARY_STAT_CHANGES and MAX_SELF_STAT_CHANGES."""
        assert "MAX_SECONDARY_STAT_CHANGES" in self.content
        assert "MAX_SELF_STAT_CHANGES" in self.content

    def test_max_constants_values(self):
        """MAX constants must have the correct values (5 and 3)."""
        import re
        m = re.search(r'MAX_SECONDARY_STAT_CHANGES\s*=\s*(\d+)', self.content)
        assert m, "MAX_SECONDARY_STAT_CHANGES not found"
        assert int(m.group(1)) == 5

        m = re.search(r'MAX_SELF_STAT_CHANGES\s*=\s*(\d+)', self.content)
        assert m, "MAX_SELF_STAT_CHANGES not found"
        assert int(m.group(1)) == 3
