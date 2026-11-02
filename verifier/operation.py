from dataclasses import asdict

from .checks import destination_problem, encoded, result, safe_path


def input_problem(v):
    problem = destination_problem(v.destination)
    if problem:
        return problem
    if not 0 <= v.window_start <= v.window_end <= 1440:
        return "window must be ordered and inside one day"
    if not 1 <= v.length <= 1440 or not 1 <= v.step <= 1440 or len(v.blocked) > 100:
        return "invalid meeting length, grid step, or interval count"
    if any(not 0 <= r.start <= r.end <= 1440 for r in v.blocked):
        return "blocked intervals must be ordered and inside one day"
    return None


def verify_input(value):
    problem = input_problem(value)
    return result(not problem, problem or "input is valid")


def expected(v):
    occupied = set()
    for r in v.blocked:
        occupied.update(range(r.start, r.end))
    rows = []
    for start in range(v.window_start, v.window_end + 1):
        end = start + v.length
        if (
            (start - v.window_start) % v.step == 0
            and end <= v.window_end
            and not occupied.intersection(range(start, end))
        ):
            rows.append({"start": start, "end": end})
    return rows, len(rows)


def verify_output(input_value, output_value, workspace):
    problem = input_problem(input_value)
    if problem:
        return result(False, problem)
    rows, total = expected(input_value)
    actual = [asdict(r) for r in output_value.records]
    if actual != rows or output_value.total != total:
        return result(False, "returned rows or total do not match the task rules")
    if output_value.path != input_value.destination:
        return result(False, "returned path does not match destination")
    path = safe_path(workspace, input_value.destination)
    if path is None or not path.is_file():
        return result(False, "artifact is missing, is a symlink, or escapes the workspace")
    try:
        content = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        return result(False, "artifact cannot be read as UTF-8")
    if content != encoded(rows, total):
        return result(False, "artifact is not the exact canonical JSON result")
    return result(True, "verified rows, total, destination, and artifact bytes", rows=len(rows), total=total)


def verify_task(arguments, output, reference, workspace):
    return verify_output(arguments, output, workspace)
