from slimconfig import build_output

from contract import TaskOutput
from verifier.checks import encoded, safe_path
from verifier.operation import verify_input


def solve(v):
    rows = []
    for start in range(v.window_start, v.window_end - v.length + 1, v.step):
        end = start + v.length
        if all(r.start == r.end or end <= r.start or start >= r.end for r in v.blocked):
            rows.append({"start": start, "end": end})
    return rows, len(rows)


def operate(value, workspace):
    verdict = verify_input(value)
    if not verdict["valid"]:
        raise ValueError(verdict["message"])
    path = safe_path(workspace, value.destination)
    if path is None:
        raise ValueError("destination crosses a symlink or leaves the workspace")
    rows, total = solve(value)
    output = build_output({"path": value.destination, "records": rows, "total": total}, TaskOutput)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(encoded(rows, total))
    return output
