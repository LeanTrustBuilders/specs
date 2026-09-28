# S1: the declaration key (version 2)

A **declaration key** identifies a Lean declaration *as it was at some point*, so that a judgement
about it can later be checked against the declaration as it is now. Every evidence record (S3)
carries the key of its subject; every dataset (S2) carries the key of each of its nodes.

## Fields

| field | type | meaning |
|---|---|---|
| `name` | string | the declaration's full name, e.g. `TauCeti.IdealArithmeticFunction.vonMangoldt` |
| `module` | string | the module declaring it |
| `package` | string | the Lake package of that module (`lean4` for the toolchain) |
| `commit` | string | the commit of the project the key was taken at |
| `toolchain` | string | the Lean toolchain of that commit, e.g. `leanprover/lean4:v4.34.0-rc2` |
| `hasher` | object | how the hashes were computed: `name` (the rule, `ltb-meaning/1`), `local` (`ltb-local/2`), `content` (`ltb-content/1`), `revision` (`null`: each name is its version) |
| `hashes.meaning` | 16 hex digits | the rule's **meaning** hash (below) |
| `hashes.local` | 16 hex digits | the rule's **local** hash (below) |
| `hashes.content` | 16 hex digits | the rule's **content** hash (below): proofs included |

In a dataset, `commit`, `toolchain` and `hasher` are recorded once, in `meta.json`.

## The three hashes

The meaning and local hashes follow a **rule**, `ltb-meaning/1`, which also draws the `meaning`
graph of S2: MeaningGraph's `MeaningGraph.Hash`. The graph and the hashes come from one walk, so they
agree by construction. The rule:

* **Proofs are erased everywhere**, in statements, values and the helpers looked through: an
  argument whose expected type (read off the type of the function applied) is a proposition, and a
  let-bound value whose type is one, is replaced by a marker. A declaration whose type is a
  proposition means its statement.
* **Content.** A definition's content is its type and its erased value; a theorem's, an axiom's
  and an opaque constant's is its type; an inductive type is taken with its mutual block and their
  constructors (the recursors follow from them). A constructor or recursor stands for its block.
* **Declarations** are the constants a person wrote, private ones included; the others are
  helpers, looked through.

**meaning** is a Merkle hash: a hash of the declaration's content in which every reference to a
constant is replaced by that constant's meaning hash. The kernel only lets a constant refer to
earlier constants or its own block, so this is well founded. It is *deep*: it changes when anything
in the declaration's `meaning` closure changes, transitively, upstream packages and Lean core
included, and only then (up to collisions). It does not depend on names: not the declaration's own,
nor those of the constants it refers to, nor binder names, binder kinds, metadata or the names of
universe parameters. So it identifies a declaration across renames, and a proof change anywhere
never changes it.

**local** (`ltb-local/2`) is a hash of the same content with references to other declarations, and
to the helpers they own, by *name*; the helpers the declaration owns (`foo.match_1`, …) and helpers
nobody owns are looked through. It changes when the declaration itself is rewritten, and not when
something it uses changes. It hashes the elaborated declaration, not its text, so it also changes
when unchanged text elaborates differently: when a `variable` in scope changes, or when a constant
it uses changes its implicit or instance arguments (see *Known limits*).

**content** (`ltb-content/1`) is the same Merkle hash with nothing erased: a declaration's content
is then everything the kernel checked of it (a theorem's statement and proof, a definition's type and
value, an opaque constant's type and value, an axiom's type, an inductive type's block as above),
and every reference to a constant is replaced by that constant's content hash. It is deep through
proofs: it changes when a proof anywhere in the declaration's closure changes, which the meaning hash
never does, and it leaves names out as the meaning hash does. MeaningGraph's `MeaningGraph.Hash`
computes it, in a second walk that keeps proofs.

## How keys are compared

A record keyed at one commit is compared with a dataset of another (see S3, *Status*):

* same name, same meaning hash: the record still applies (**current**);
* same name, same local hash, different meaning hash: the declaration is written the same, but
  something it rests on changed (**stale underneath**);
* same name, different local hash: the declaration itself changed (**stale**);
* name gone, exactly one declaration with the same meaning hash (and kind): the record follows it
  (**renamed**).

Hashes are comparable only when computed by the same hasher: the same rule and the same local hash
function. A consumer must treat keys from different hashers as incomparable, and a producer
changing either must change its identifier: a change to the rule, or to how it is computed, that
moves any hash is a new rule name.

The content hash does not decide a record's status. It tells, between two datasets, a declaration
whose meaning is unchanged but a proof in its closure changed from one where nothing changed. Two
content hashes are comparable only when their `hasher.content` names agree; a change to what the
content walk hashes is a new content hasher name.

Because the hashes follow the `meaning` graph, a record that is stale underneath has something in
its `meaning` closure whose meaning changed, and the closure's members whose local hash changed are
the declarations to blame.

## Keys of earlier versions

A key of **version 1** has the same meaning and local hashes as version 2 (the rule `ltb-meaning/1`,
`ltb-local/2`), so it is compared as a key of version 2. Its content hash was semantic_hash's
proof-relevant hash, which is not comparable with `ltb-content/1`; nothing compares content hashes
across hashers (S3's statuses do not use them).

A key of **version 0** was made of semantic_hash's hashes (`hasher` `{name: "semantic_hash", revision,
local: "ltb-local-v1"}`). Those hashes did not follow the graph: semantic_hash and the graph erased
different proofs, so between two Tau Ceti datasets 4 declarations were stale underneath with nothing
changed in their closure, and 335 were current although their closure had changed. Datasets no longer
carry those hashes, so such a key is **incomparable** with them.

The measurements below were made with version 0.


## Measured on Tau Ceti (version 0)

Between Tau Ceti d3aec47 and 8befae0 (428 commits in 29 hours, same toolchain and Mathlib; datasets
by trust-extract 0.2), taking each of the 77,758 declarations of d3aec47 as if a review had been
made of it there:

| status at 8befae0 | declarations | share |
|---|---:|---:|
| current | 71,880 | 92.4% |
| current, a proof in its closure changed | 4,112 | 5.3% |
| stale underneath | 1,282 | 1.6% |
| stale | 394 | 0.5% |
| renamed | 21 | |
| orphaned (removed) | 69 | |

4,310 declarations were added. Against the source text at both commits:

* **current**: a handful of declarations whose statement text changed are still current, rightly:
  a name written fully qualified, or an attribute added;
* **stale underneath**: 96% read exactly the same, as they should; most are downstream of a few
  rewritten definitions (three rewritten weight tables are among the causes of 810, 319 and 300
  of them);
* **stale**: 153 read differently. 241 read the same: 106 because a `variable` line of their
  section changed (the statement did change: stale is right, but the change is outside the
  declaration's source range, so a page must show the elaborated statement, not only the source),
  and 135 whose section's variables did not change either. 73 of these are in files that did not
  change at all; in the cases examined, a constant they use changed its signature, so that the same
  text now elaborates with other instance or implicit arguments. For a reviewer, these are closer to
  stale underneath: nothing in the declaration was rewritten.

Across a dependency bump, from 8befae0 to c59177e (16 commits, among them the move from Lean
v4.34.0-rc2 to v4.34.0 and a Mathlib bump of 249 commits), of 81,999 declarations: 24,874 current,
35,369 current with a proof in their closure changed, 21,493 (26%) stale underneath, 237 stale.
Only 74 of the 15,945 upstream declarations Tau Ceti rests on were rewritten, and 28 removed; 17,076
of the stale-underneath declarations have only such upstream causes. The largest causes include
real refactors of definitions (`Bialgebra`'s `toBialgHom` now built from `AlgHom.ofClass`), and
changes of signature: `MeasureTheory.eLpNorm` gained an instance argument `[TopologicalSpace ε]`, so
`MeasureTheory.Lp`, whose source did not change, now elaborates with that argument, and its local
hash changed with it (826 declarations rest on it).

## Known limits


* The local hash sees elaboration details: a declaration whose text is unchanged, but whose use of
  a constant now elaborates with different implicit or instance arguments (because that constant's
  signature changed), is **stale** rather than **stale underneath** (up to 135 of 394 stale
  declarations in the measurement above). For the same reason, the rewritten dependencies a
  **stale underneath** status names include such declarations besides the one really rewritten
  (`MeasureTheory.Lp` besides `MeasureTheory.eLpNorm` above). A candidate fix is a fourth hash,
  of the statement with implicit and instance arguments erased: a change of the local hash alone
  would then read as stale underneath.

* The content hash can depend on how an extraction was split (S2): a proof that rests on an
  auxiliary lemma Lean generated separately in several modules (`congr_simp`, equation lemmas) is
  hashed with whichever copy the environment holds. On Tau Ceti at 8befae0, 287 content hashes out
  of 97,944 differed between 4 and 8 parts (measured with semantic_hash's content hash, which saw the
  same copies). The meaning and local hashes, which key records, did not.
* Hashes are 64-bit. A change goes unnoticed only if the new hash equals the old one, with
  probability 2⁻⁶⁴. The chance that any two of 10⁵ declarations share a meaning hash by accident,
  which would make a rename ambiguous, is about 3·10⁻¹⁰.
* The meaning hash erases a proof by position: an argument whose expected type is a proposition. A
  definition whose value is a *choice* made with a proof (`Classical.choose h`) means "a choice of an
  object with that property", whatever the proof: which choice principle it rests on is for the
  axioms facet and a choice report, not for the meaning hash. On LeanMachineLearning, across a
  Mathlib bump that changed only proofs (fields of `Prop`-valued instances), version 0 reported 67
  declarations stale underneath and version 1 none.
* Hashes depend on what was visible when they were computed. The extractor imports every module at
  full visibility (including `.olean.private`), so definition bodies that a module does not export
  still contribute. A tool hashing at lower visibility would get different hashes for the same code,
  and its keys would not be comparable with the extractor's.
