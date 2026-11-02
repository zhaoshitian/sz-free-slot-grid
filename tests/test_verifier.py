import copy

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import TaskInput, TaskOutput
from plugin.operation import operate

SAMPLE = {
    "window_start": 540,
    "window_end": 660,
    "length": 30,
    "step": 15,
    "blocked": [{"start": 570, "end": 600}, {"start": 590, "end": 615}, {"start": 630, "end": 630}],
}
EXPECTED_ROWS = [{"start": 540, "end": 570}, {"start": 615, "end": 645}, {"start": 630, "end": 660}]
EXPECTED_TOTAL = 3
EMPTY = {"window_start": 0, "window_end": 0, "length": 1, "step": 1, "blocked": []}
INVALID = {"step": 0}
TOOL = "find_slots"
TASK = "find-slots"


def given(data):
    return build_output({"destination": "results/out.json", **data}, TaskInput)


def valid_input(data):
    return verifier.verify_input(TOOL, given(data))["valid"]


def execute(data, workspace):
    value = given(data)
    assert verifier.verify_input(TOOL, value)["valid"]
    output = build_output(plain_output(operate(value, workspace)), TaskOutput)
    assert verifier.verify_output(TOOL, value, output, str(workspace))["valid"]
    verdict = verifier.verify_task(TASK, value, output, None, str(workspace))
    assert verdict["valid"] and verdict["score"] == 1.0
    assert verdict == verifier.verify_task(TASK, value, output, None, str(workspace))
    return output


def test_known_answer(tmp_path):
    out = execute(SAMPLE, tmp_path)
    assert plain_output(out)["records"] == EXPECTED_ROWS
    assert out.total == EXPECTED_TOTAL


def test_empty_boundary(tmp_path):
    out = execute(EMPTY, tmp_path)
    assert out.records == [] and out.total == 0


def test_wrong_total_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.total += 1
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_omitted_row_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.records.pop()
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_duplicate_row_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.records.append(out.records[0])
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_order_is_canonical(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.records.reverse()
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_missing_file_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    (tmp_path / out.path).unlink()
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


@pytest.mark.parametrize(
    "text", ["{", "null", "{}", '{"records":[],"total":NaN}', '{"records":[],"total":0,"total":1}']
)
def test_malformed_or_incorrect_file_rejected(tmp_path, text):
    out = execute(SAMPLE, tmp_path)
    (tmp_path / out.path).write_text(text)
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_invalid_utf8_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    (tmp_path / out.path).write_bytes(b"\xff")
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_claimed_path_mismatch_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.path = "different.json"
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


@pytest.mark.parametrize(
    "destination", ["../escape.json", "/absolute.json", "result.txt", "", "a/../b.json", "./x.json", "a\\b.json"]
)
def test_destination_rejected(destination):
    assert not valid_input({**SAMPLE, "destination": destination})


def test_invalid_input_and_tool_failure(tmp_path):
    data = {**SAMPLE, **INVALID}
    assert not valid_input(data)
    with pytest.raises(ValueError):
        operate(given(data), tmp_path)


def test_schema_rejects_missing_or_malformed():
    with pytest.raises((ValueError, TypeError)):
        build_output({}, TaskInput)
    with pytest.raises((ValueError, TypeError)):
        build_output({"path": "out.json", "records": "wrong", "total": "wrong"}, TaskOutput)
    with pytest.raises((ValueError, TypeError)):
        build_output({"path": "out.json", "records": [], "total": 0, "extra": 1}, TaskOutput)


def test_existing_file_is_never_overwritten(tmp_path):
    out = execute(SAMPLE, tmp_path)
    content = (tmp_path / out.path).read_bytes()
    with pytest.raises(FileExistsError):
        operate(given(SAMPLE), tmp_path)
    assert (tmp_path / out.path).read_bytes() == content


def test_symlink_file_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    path = tmp_path / out.path
    target = tmp_path / "target.json"
    path.rename(target)
    path.symlink_to(target)
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_symlink_directory_rejected(tmp_path):
    (tmp_path / "actual").mkdir()
    (tmp_path / "results").symlink_to(tmp_path / "actual", target_is_directory=True)
    with pytest.raises(ValueError):
        operate(given(SAMPLE), tmp_path)


def test_input_permutation_does_not_change_result(tmp_path):
    data = copy.deepcopy(SAMPLE)
    for value in data.values():
        if isinstance(value, list):
            value.reverse()
    assert plain_output(execute(data, tmp_path))["records"] == EXPECTED_ROWS


def test_edited_row_even_with_matching_file_is_rejected(tmp_path):
    import json

    out = execute(SAMPLE, tmp_path)
    data = plain_output(out)
    row = data["records"][0]
    key = next(k for k, v in row.items() if type(v) is int)
    row[key] += 1
    forged = build_output(data, TaskOutput)
    artifact = {"records": data["records"], "total": data["total"]}
    (tmp_path / out.path).write_text(json.dumps(artifact, sort_keys=True, separators=(",", ":")) + "\n")
    assert not verifier.verify_task(TASK, given(SAMPLE), forged, None, str(tmp_path))["valid"]


def test_touching_endpoints_are_free(tmp_path):
    data = {"window_start": 0, "window_end": 30, "length": 10, "step": 10, "blocked": [{"start": 10, "end": 20}]}
    assert plain_output(execute(data, tmp_path))["records"] == [{"start": 0, "end": 10}, {"start": 20, "end": 30}]


def test_full_day_blocked(tmp_path):
    assert execute({**SAMPLE, "blocked": [{"start": 0, "end": 1440}]}, tmp_path).total == 0


def test_zero_width_block_is_empty(tmp_path):
    data = {"window_start": 0, "window_end": 10, "length": 10, "step": 1, "blocked": [{"start": 5, "end": 5}]}
    assert execute(data, tmp_path).total == 1


def test_length_exceeds_window(tmp_path):
    assert execute({**SAMPLE, "length": 121}, tmp_path).records == []


def test_crlf_is_not_canonical_bytes(tmp_path):
    out = execute(SAMPLE, tmp_path)
    artifact = tmp_path / out.path
    artifact.write_bytes(artifact.read_bytes().replace(b"\n", b"\r\n"))
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]
