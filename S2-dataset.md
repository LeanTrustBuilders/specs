# S2: the dataset (`ltb-dataset/1`)

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
modules.jsonl               the project's modules (optional)
edges/<notion>.bin          one file per notion of dependency
facets/<name>.jsonl         one file per facet
```

## `meta.json`

| field | meaning |
|---|---|
| `spec` | `"ltb-dataset/1"` |
| `producer` | `{name, version}` of the tool, and optionally `parts`: how many parts the work was split into, for a tool that splits it (see below) |
| `library` | `root` (module prefix), `package`, `repo` (`owner/name`), `commit`, `dirty` (uncommitted changes when extracted), `modules` (count of the modules extracted), `unavailable` (the library's modules that were not extracted because they do not build at `commit`, with every module importing them; sorted, possibly empty) |
| `toolchain` | the project's `lean-toolchain` |
| `lean` | the Lean the producer ran on: `version`, `githash` |
| `hasher` | see S1: `name` and `meaning` (the rule, `ltb-meaning/1`), `local` (`ltb-local/2`), `content` (`{name: "semantic_hash", revision, variant: "proof-relevant"}`), and `legacy`, the hasher of the version-0 hashes each node also carries (`{name: "semantic_hash", revision, meaning: "proof-irrelevant", local: "ltb-local-v1"}`) |
| `counts` | `nodes`, `project`, `upstream` |
| `edges` | one entry per edge file: `name` (the notion), `file`, `format` (`i32le-pairs`), `count`, `description` |
| `facets` | one entry per facet file: `name`, `file`, `schema` (`<facet>/<version>`), `count`, `description` |
| `modules` | optional: `file` (`modules.jsonl`), `count` |
| `packages` | optional: one entry per package the library imports, itself included: `name` (as in S1: the Lake package, `lean4` for the toolchain), `modules` (how many of its modules are imported), `requires` (the packages its imported modules import from, sorted) |
| `upstreamClosure` | optional, present when the dataset follows dependencies past the project (see below): `follow` (the notion followed: `statement`, `meaning` or `term`) and `display` (which constants count as declarations: `declared`, the rule's) |

A dataset carries no timestamp, so that extracting the same commit twice gives identical files.

A tool that splits the work into parts (each importing part of the library) should produce the same
dataset however it splits it. trust-extract does, with one exception it records: Lean generates
some auxiliary lemmas on demand, several modules can hold their own copy, and the copy a part sees
depends on what it imports. The content hashes and term edges that rest on such a lemma can then
depend on the split, which is why `producer.parts` is recorded. Meaning and local hashes, statement,
meaning and source edges, and facets do not depend on it.

## `modules.jsonl`

One line per extracted project module, sorted by name: `name`, `path` (the source file, relative to
the project root), `imports` (the modules it imports, in order, without repetition), `doc` (its module
docstrings, verbatim, in order).

## `decls.jsonl`

One JSON object per line, one line per **node**, in id order:

| field | meaning |
|---|---|
| `id` | the node's index, from 0. Ids are local to one dataset: join datasets by `name` |
| `name`, `module`, `package` | as in S1 |
| `scope` | `project` (declared in the project) or `upstream` |
| `kind` | `theorem`, `definition`, `instance`, `class`, `structure`, `inductive`, `axiom`, `opaque` |
| `isProp` | whether the declaration is a proof (its type is a proposition) |
| `hashes` | `meaning`, `local`, `content`: see S1; and `legacy`: `meaning`, `local`, the node's hashes under version 0 of S1, for keys of that version |

**Nodes** are the project's own declarations (written by a person, private ones included; not the
constructors, recursors, projections, matchers and other helpers the compiler generates) and the
upstream declarations their statements and meanings rest on; with an upstream closure, also every
upstream declaration it reaches. Which constants are declarations is the rule's (S1). **Order:** project
nodes by module name, then by position in the module; then upstream nodes by name.

## Edge files

Little-endian 32-bit integer pairs `(source id, target id)`, one file per notion of dependency. In the
four notions below only project nodes have outgoing edges; upstream nodes are where a closure
leaves the project.

| notion | edges from a declaration to |
|---|---|
| `statement` | the declarations its type mentions, proofs erased |
| `meaning` | what it means under the rule of S1: the declarations its content mentions (its statement for a proof; its statement and value for a definition; its type and constructors for an inductive type), proofs erased everywhere. The closure over these edges is what coverage is computed over, and what the meaning hash covers |
| `term` | its type and whole value, proofs included, restricted to targets that are nodes |
| `source` | what its source relies on that its elaborated term does not mention: the coercion instances behind its `↑`, and for a notation, the constants it expands to. What a standalone file must bring along; not meaning |

Helpers are looked through, in every notion: an edge to a helper is replaced by edges to the
declarations it uses, upstream helpers included, so that every target is a declaration. A
constructor or recursor stands for its inductive type.

### Past the project

A dataset can also follow dependencies into the libraries underneath (`meta.upstreamClosure`).
Starting from the upstream targets of the project's `statement` and `meaning` edges (and, when the
closure follows `term`, of the `term` edges of the project's declarations that are not proofs), it
follows, from each upstream declaration reached, the notion named by `follow`: from a proof, its
statement only; from anything else, `statement`, `meaning` or `term` as named. Every declaration
reached is a node, and its edges are in three more files:

| notion | edges |
|---|---|
| `upstream-statement` | `statement`, from the upstream nodes the closure reached |
| `upstream-meaning` | `meaning`, from the same |
| `upstream-term` | `term`, from those of them that are not proofs: an upstream proof term is not walked |

Past the project, helpers are looked through wherever they come from, and there are no `source`
edges (they serve a project's source). The project notions, the hashes
and the facets of project nodes are the same with or without a closure, except that `term`, which
keeps targets that are nodes, keeps the ones the closure added. A reader that wants the whole graph
takes the union of a notion and its `upstream-` companion; a reader that does not know the
`upstream-` notions sees the project's graph, with more upstream nodes.

## Facets

Everything else about declarations is a **facet**: one JSONL file per facet, one line per
declaration it applies to, keyed by `decl` (a name), in node order.

Readers **ignore facets they do not know**, and a reader that needs a facet checks its `schema`.
A facet can be added to an existing dataset later, by another tool, provided it describes the same
commit; that tool adds its entry to `meta.json`.

### Registry

| facet | schema | row fields |
|---|---|---|
| `docstring` | `docstring/1` | `text`. Project nodes, and upstream nodes unless the producer leaves them out |
| `signature` | `signature/1` | `text`: the node's signature as Lean prints it (`name (x : α) … : β`), for every node; optionally `refs`, as in `statement` (the declaration's own name left out) |
| `source` | `source/1` | `path` (relative to the project root), `start` and `end` as `[line, column]` (lines from 1, columns in UTF-16 code units from 0), `keyword` (as written: `theorem`, `lemma`, `def`, `abbrev`, `instance`, `structure`, `class`, `class inductive`, …) |
| `axioms` | `axioms/1` | `axioms` (names, sorted), `sorry` (whether `sorryAx` is among them) |
| `statement` | `statement/1` | the statement taken apart: `binders`, each with `name` (empty for one the source cannot name, such as an anonymous instance), `type`, `role` (`type`, `variable`, `hypothesis` or `instance`) and `explicit`; `conclusion` (what the type states under the binders); for a definition that is not a proof, `value` (its body, the binders in place); for a structure or class, `fields` (`name`, `type`); for another inductive type, `constructors` (`name`, `type`). Project nodes, and with an upstream closure the upstream nodes it reached that are not proofs. All text is Lean's pretty-printing from inside the declaration's namespace; `⋯` marks what a bounded printer cut. Optionally, each text `t` comes with `tRefs` (`typeRefs`, `conclusionRefs`, `valueRefs`): `[start, stop, constant]` for each identifier, operator or notation in it that stands for a constant, positions in Unicode code points, innermost spans only; each binder names the `head` constant of its type, and `conclusionHead` that of the conclusion |
| `examples` | `examples/1` | `examples`: the `example`s of the library whose statement names the declaration, each `{path, line, end, statement, sorry}` (`sorry`: whether its text uses `sorry`). They are not in the compiled library; an analyzer reading the sources adds the facet (the extractor's `scripts/examples.py`). Project nodes |
| `check.kernel.<notion>` | `check.kernel/1` | the kernel check of the dataset's closures along `<notion>` (`meaning` or `term`), by `trust-extract check`: `kernel` is `ok`, `missing` (with `missing`: the constants Lean's kernel needed to check the declaration that its closure lacks), `error` (with `error`, the kernel's message) or `skipped`; `unlisted`: what the declaration mentions, through helpers, that its closure lacks. Project nodes |
| `annotation.<attr>` | `annotation/2` | `entries`: for each application of the attribute `<attr>` to the declaration, in order, the JSON it recorded in the TrustAnnotations extension (`annotation/1` had one `payload`, which lost repeated applications) |

Annotations defined in [TrustAnnotations](https://github.com/LeanTrustBuilders/annotations):

| attribute | payload |
|---|---|
| `claim` | `{}` or `{"reference": "…"}` |
| `example_of`, `nonexample_of` | `{"target": "<definition name>"}` |
| `specifies` | `{"target": "<definition name>", "comment": "…"}`: the theorem is part of the specification of the definition; repeatable |
| `characterization` | `{"role": "property" \| "existence" \| "uniqueness", "property": "<predicate>", "target": "<definition>", "relation": "…", "relationHead": "<constant>", "comment": "…"}`: the declaration's part in the characterization of `target` by `property`; `relation` is the uniqueness theorem's conclusion as written |

New facets are added to this registry by pull request, so that two tools do not give one name two
meanings.

## Versioning

Adding a facet or an edge notion does not change `spec`. Changing the meaning of an existing field,
facet schema or notion does.

`ltb-dataset/1` (September 2026) changed from `ltb-dataset/0`:
* the meaning and local hashes are the rule's (S1 version 1), and each node carries its version-0
  hashes as `hashes.legacy`; `hasher` says which is which;
* `statement` and `meaning` follow the rule: proofs erased everywhere (version 0 skipped only the
  proofs in a definition's own value, and read those of the helpers it looked through), and a
  constructor, recursor or projection stands for its type;
* private declarations are nodes; version 0 looked through them;
* notation and coercion dependencies moved from `meaning` (and `statement`, `term`) to a notion of
  their own, `source`;
* `term` looks through upstream helpers, so that its targets are declarations too.

A reader of version 0 can read version 1 by ignoring `hashes.legacy`, `hasher.content` and
`hasher.legacy`; a record keyed under version 0 is resolved as S1 says.
