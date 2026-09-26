#!/usr/bin/env python3
"""Checks the conformance vectors: dataset structure (stdlib only), records against the schema's
required fields, and evidence-core's statuses against expected-status.json. Also checks that the
records of vectors/v0, keyed by the hashes of ltb-dataset/0, still get their statuses against the
datasets of ltb-dataset/1, through the legacy hashes those carry."""
import json
import struct
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
V = root / "vectors"
errors = []

for ds, spec in (("fixture-a", "ltb-dataset/1"), ("fixture-b", "ltb-dataset/1"),
                 ("fixture-b-partial", "ltb-dataset/1"), ("v0/fixture-a", "ltb-dataset/0"),
                 ("v0/fixture-b", "ltb-dataset/0"), ("v0/fixture-b-partial", "ltb-dataset/0")):
    meta = json.loads((V / ds / "meta.json").read_text())
    if meta.get("spec") != spec:
        errors.append(f"{ds}: spec")
    decls = [json.loads(l) for l in (V / ds / "decls.jsonl").read_text().splitlines()]
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
        for k in range(e["count"]):
            s, t = struct.unpack_from("<ii", data, 8 * k)
            if decls[s]["scope"] != "project":
                errors.append(f"{ds}: edge from upstream node {decls[s]['name']}")
                break
    names = {d["name"] for d in decls}
    for f in meta["facets"]:
        for line in (V / ds / f["file"]).read_text().splitlines():
            if json.loads(line)["decl"] not in names:
                errors.append(f"{ds}: facet {f['name']} row for a non-node")
                break

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

    # Records keyed by the hashes of ltb-dataset/0, against datasets of ltb-dataset/1: re-keyed
    # through version A (which carries both), they get the statuses they had; without version A,
    # compared with the legacy hashes, the same statuses without the rewritten dependencies.
    old_records = rec.load(V / "v0" / "records.jsonl")
    for ds, file in (("fixture-b", "expected-status.json"), ("fixture-b-partial", "expected-status-partial.json")):
        now = Dataset.load(V / ds)
        expected = json.loads((V / "v0" / file).read_text())
        for r in old_records:
            if r["kind"] == "status":
                continue
            want = expected[r["id"]]
            for old, changed in ((A, want["changed"]), (None, [])):
                s = classify(r["subject"], now, old=old)
                got = {"subject": r["subject"]["name"], "status": s.state,
                       "now": s.decl.name if s.decl else None, "changed": s.changed}
                if got != dict(want, changed=changed):
                    errors.append(f"{ds}, v0 record {r['id']} ({'through A' if old else 'legacy'}): "
                                  f"expected {dict(want, changed=changed)}, got {got}")

for e in errors:
    print(f"FAIL: {e}")
print("ok" if not errors else f"{len(errors)} failures")
sys.exit(1 if errors else 0)
