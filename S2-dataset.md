# S2: the dataset (`ltb-dataset/0`)

A **dataset** is everything a tool needs to know about a compiled Lean project, as files, so that
tools downstream of it need no Lean. It is written by
[`trust-extract`](https://github.com/LeanTrustBuilders/extractor) and read by
[evidence-core](https://github.com/LeanTrustBuilders/evidence-core) and views.

A dataset is a **deterministic function of the code and of the producing tool's version**. Anything
asserted by a person or an agent is an S3 evidence record, not part of a dataset.

## Layout

```
meta.json
decls.jsonl
edges/<notion>.bin          one file per notion of dependency
facets/<name>.jsonl         one file per facet
```

## `meta.json`

| field | meaning |
|---|---|
| `spec` | `"ltb-dataset/0"` |
| `producer` | `{name, version}` of the tool, and optionally `parts`: how many parts the work was split into, for a tool that splits it (see below) |
| `library` | `root` (module prefix), `package`, `repo` (`owner/name`), `commit`, `dirty` (uncommitted changes when extracted), `modules` (count of the modules extracted), `unavailable` (the library's modules that were not extracted because they do not build at `commit`, with every module importing them; sorted, possibly empty) |
| `toolchain` | the project's `lean-toolchain` |
| `lean` | the Lean the producer ran on: `version`, `githash` |
| `hasher` | `name`, `revision`, `meaning`, `content`, `local`: see S1 |
| `counts` | `nodes`, `project`, `upstream` |
| `edges` | one entry per edge file: `name` (the notion), `file`, `format` (`i32le-pairs`), `count`, `description` |
| `facets` | one entry per facet file: `name`, `file`, `schema` (`<facet>/<version>`), `count`, `description` |

A dataset carries no timestamp, so that extracting the same commit twice gives identical files.

A tool that splits the work into parts (each importing part of the library) should produce the same
dataset however it splits it. trust-extract does, with one exception it records: Lean generates
some auxiliary lemmas on demand, several modules can hold their own copy, and the copy a part sees
depends on what it imports. The content hashes and term edges that rest on such a lemma can then
depend on the split, which is why `producer.parts` is recorded. Meaning and local hashes, statement
and meaning edges, and facets do not depend on it.

## `decls.jsonl`

One JSON object per line, one line per **node**, in id order:

| field | meaning |
|---|---|
| `id` | the node's index, from 0. Ids are local to one dataset: join datasets by `name` |
| `name`, `module`, `package` | as in S1 |
| `scope` | `project` (declared in the project) or `upstream` |
| `kind` | `theorem`, `definition`, `instance`, `class`, `structure`, `inductive`, `axiom`, `opaque` |
| `isProp` | whether the declaration is a proof (its type is a proposition) |
| `hashes` | `meaning`, `content`, `local`: see S1 |

**Nodes** are the project's own declarations (written by a person; not the constructors, recursors,
projections and helpers the compiler generates) and the upstream constants that their statements and
data mention. **Order:** project nodes by module name, then by position in the module; then upstream
nodes by name.

## Edge files

Little-endian 32-bit integer pairs `(source id, target id)`, one file per notion of dependency. Only
project nodes have outgoing edges; upstream nodes are where a closure leaves the project.

| notion | edges from a declaration to |
|---|---|
| `statement` | the constants its type mentions |
| `meaning` | what it means: its statement for a proof; its statement and the data of its value, proofs skipped, for a definition. The closure over these edges is what coverage is computed over |
| `term` | its type and whole value, proofs included, restricted to targets that are nodes |

Compiler-generated helpers are looked through: an edge to a helper is replaced by edges to what it
uses. Notation and coercion instances a declaration's source relies on count as dependencies.

## Facets

Everything else about declarations is a **facet**: one JSONL file per facet, one line per
declaration it applies to, keyed by `decl` (a name), in node order.

Readers **ignore facets they do not know**, and a reader that needs a facet checks its `schema`.
A facet can be added to an existing dataset later, by another tool, provided it describes the same
commit; that tool adds its entry to `meta.json`.

### Registry (version 0)

| facet | schema | row fields |
|---|---|---|
| `docstring` | `docstring/1` | `text` |
| `source` | `source/1` | `path` (relative to the project root), `start` and `end` as `[line, column]` (lines from 1, columns in UTF-16 code units from 0), `keyword` (as written: `theorem`, `lemma`, `def`, `abbrev`, `instance`, `structure`, `class`, `class inductive`, …) |
| `axioms` | `axioms/1` | `axioms` (names, sorted), `sorry` (whether `sorryAx` is among them) |
| `annotation.<attr>` | `annotation/1` | `payload`: the JSON recorded by the attribute `<attr>` in the TrustAnnotations extension |

Annotations defined in [TrustAnnotations](https://github.com/LeanTrustBuilders/annotations) v0:

| attribute | payload |
|---|---|
| `claim` | `{}` or `{"reference": "…"}` |
| `example_of`, `nonexample_of` | `{"target": "<definition name>"}` |

New facets are added to this registry by pull request, so that two tools do not give one name two
meanings.

## Versioning

Adding a facet or an edge notion does not change `spec`. Changing the meaning of an existing field,
facet schema or notion does.
