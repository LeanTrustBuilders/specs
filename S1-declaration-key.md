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
| `hasher` | object | how the hashes were computed: `meaning` (the rule, `ltb-meaning/1`), `local` (`ltb-local/2`), and in a dataset `content` (`ltb-content/1`). Each name is its version |
| `hashes.meaning` | 16 hex digits | the rule's **meaning** hash (below) |
| `hashes.local` | 16 hex digits | the rule's **local** hash (below) |
| `hashes.content` | 16 hex digits | in a dataset: the rule's **content** hash (below), proofs included |

In a dataset, `commit`, `toolchain` and `hasher` are recorded once, in `meta.json`. An evidence
record (S3) leaves the content hash out: it decides nothing about the record.

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
* name gone, exactly one declaration with the same meaning hash (or, when several have it, exactly
  one of the same aspect, S3): the record follows it (**renamed**).

Hashes are comparable only when computed by the same hasher: the same `hasher.meaning` and the same
`hasher.local`. A consumer must treat keys from different hashers as incomparable, and a producer
changing either must change its name: a change to the rule, or to how it is computed, that moves any
hash is a new name.

The content hash does not decide a record's status. It tells, between two datasets, a declaration
whose meaning is unchanged but a proof in its closure changed from one where nothing changed. Two
content hashes are comparable only when their `hasher.content` names agree; a change to what the
content walk hashes is a new content hasher name.

Because the hashes follow the `meaning` graph, a record that is stale underneath has something in
its `meaning` closure whose meaning changed, and the closure's members whose local hash changed are
the declarations to blame.

How the statuses fared on a real library, and why this rule replaced semantic_hash's hashes
(version 0), is measured in the design notes (`meaning-hash.md` §8, and `dependency-testing.md` §9).

## Known limits

* The local hash sees elaboration details: a declaration whose text is unchanged, but whose use of
  a constant now elaborates with different implicit or instance arguments (because that constant's
  signature changed), is **stale** rather than **stale underneath** (up to a third of the stale
  declarations, measured on Tau Ceti). For the same reason, the rewritten dependencies a
  **stale underneath** status names include such declarations besides the one really rewritten
  (`MeasureTheory.Lp` besides `MeasureTheory.eLpNorm`, which gained an instance argument). A candidate fix is a fourth hash,
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
