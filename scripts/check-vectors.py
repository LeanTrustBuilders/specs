#!/usr/bin/env python3
"""Checks the conformance vectors: dataset structure (stdlib only), the datasets and records against
the JSON Schemas (with `jsonschema`, when installed), the records against evidence-core's
validation, and evidence-core's statuses against expected-status.json."""
import json
import struct
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
V = root / "vectors"
errors = []


def lines(path: Path) -> list[str]:
    """A JSON-lines file's lines: split at "\n" only (`splitlines` also splits inside strings, at
    Unicode line separators)."""
    return [l for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]

for ds, spec in (("fixture-a", "ltb-dataset/2"), ("fixture-b", "ltb-dataset/2"),
                 ("fixture-b-partial", "ltb-dataset/2"), ("fixture-b-closure", "ltb-dataset/2")):
    meta = json.loads((V / ds / "meta.json").read_text())
    if meta.get("spec") != spec:
        errors.append(f"{ds}: spec")
    decls = [json.loads(l) for l in lines(V / ds / "decls.jsonl")]
    if [d["id"] for d in decls] != list(range(len(decls))):
        errors.append(f"{ds}: ids are not 0..n-1 in order")
    if meta["counts"]["nodes"] != len(decls):
        errors.append(f"{ds}: counts.nodes")
    seen_upstream = False
    for d in decls:
        if d["scope"] == "upstream":
            seen_upstream = True
        elif seen_upstream:
            errors.append(f"{ds}: project node {d['name']} after an upstream node")
    for e in meta["edges"]:
        data = (V / ds / e["file"]).read_bytes()
        if len(data) != 8 * e["count"]:
            errors.append(f"{ds}: {e['file']} size")
        for k in range(e["count"] if not e["name"].startswith("upstream-") else 0):
            s, t = struct.unpack_from("<ii", data, 8 * k)
            if decls[s]["scope"] != "project":
                errors.append(f"{ds}: edge from upstream node {decls[s]['name']}")
                break
    if set(meta["hasher"]) != {"meaning", "local", "content"}:
        errors.append(f"{ds}: hasher is not {{meaning, local, content}}")
    # S2: at most one line per declaration; lines about nodes first, in node order, then the others
    # by name
    ids = {d["name"]: d["id"] for d in decls}
    for f in meta["facets"]:
        rows = [json.loads(line)["decl"] for line in lines(V / ds / f["file"])]
        key = [(0, ids[n], "") if n in ids else (1, 0, n) for n in rows]
        if len(set(rows)) != len(rows):
            errors.append(f"{ds}: facet {f['name']} has two lines about one declaration")
        if key != sorted(key):
            errors.append(f"{ds}: facet {f['name']} is not in S2's order")
        if len(rows) != f["count"]:
            errors.append(f"{ds}: facet {f['name']} count")

try:
    import jsonschema
except ImportError:
    print("jsonschema not installed: skipping the schema check")
else:
    schema = lambda name: json.loads((root / "schemas" / name).read_text())
    for ds in ("fixture-a", "fixture-b", "fixture-b-partial", "fixture-b-closure"):
        for e in jsonschema.Draft202012Validator(schema("dataset-meta.schema.json")).iter_errors(
                json.loads((V / ds / "meta.json").read_text())):
            errors.append(f"{ds}/meta.json: {e.message}")
        decl = jsonschema.Draft202012Validator(schema("decl.schema.json"))
        for line in lines(V / ds / "decls.jsonl"):
            for e in decl.iter_errors(json.loads(line)):
                errors.append(f"{ds}/decls.jsonl: {e.message}")
    record = jsonschema.Draft202012Validator(schema("evidence-record.schema.json"))
    for line in lines(V / "records.jsonl"):
        for e in record.iter_errors(json.loads(line)):
            errors.append(f"records.jsonl: {e.message}")

try:
    from evidence_core import Dataset, classify
    from evidence_core import records as rec
except ImportError:
    print("evidence_core not installed: skipping the status check")
else:
    A = Dataset.load(V / "fixture-a")
    records = rec.load(V / "records.jsonl")
    for r in records:
        for e in rec.validate(r):
            errors.append(f"record {r.get('id')}: {e}")
    # Statuses against version B, and against B extracted without `Fixture.Uses` (unavailable).
    for ds, file in (("fixture-b", "expected-status.json"), ("fixture-b-partial", "expected-status-partial.json")):
        now = Dataset.load(V / ds)
        expected = json.loads((V / file).read_text())
        for r in records:
            if r["kind"] == "status":
                continue
            s = classify(r["subject"], now, old=A)
            want = expected[r["id"]]
            got = {"subject": r["subject"]["name"], "status": s.state,
                   "now": s.decl.name if s.decl else None, "changed": s.changed}
            if got != want:
                errors.append(f"{ds}, record {r['id']}: expected {want}, got {got}")

for e in errors:
    print(f"FAIL: {e}")
print("ok" if not errors else f"{len(errors)} failures")
sys.exit(1 if errors else 0)
