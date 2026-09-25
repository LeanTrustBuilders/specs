# S1: the declaration key (version 0)

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
| `hasher` | object | how the hashes were computed: `name` (`semantic_hash`), `revision` (a commit of semantic_hash), `local` (the local hash function, `ltb-local-v1`) |
| `hashes.meaning` | 16 hex digits | semantic_hash's **proof-irrelevant** hash |
| `hashes.content` | 16 hex digits | semantic_hash's **proof-relevant** hash |
| `hashes.local` | 16 hex digits | the **local** hash (below) |

In a dataset, `commit`, `toolchain` and `hasher` are recorded once, in `meta.json`.

## The three hashes

All three are invariant under renaming binders and universe parameters, and under metadata.

**meaning** is *deep*: a referenced constant contributes its own hash, not its name. It therefore
changes when anything the declaration's statement or data rests on changes meaning, transitively,
upstream packages included. Proofs do not contribute: a theorem hashes by its proposition, and a
proof lifted out of a definition into a `_proof_n` theorem contributes its proposition. The meaning
hash does not depend on the declaration's own name, so it identifies a declaration across renames.

**content** is deep too, and also changes when a proof changes.

**local** (`ltb-local-v1`) covers the declaration's *own* statement and data, with every referenced
constant contributing a hash of its *name* instead of its content:

| declaration | hashed |
|---|---|
| theorem, axiom, opaque constant | its type |
| definition | its type and its value |
| inductive type, structure, class | its type, its number of parameters, and each constructor's type |

It changes when the declaration itself is rewritten, and not when something it uses changes. It
hashes the elaborated declaration, not its text, so it also changes when unchanged text elaborates
differently: when a `variable` in scope changes (the statement really changed, though its source
range reads the same), or when a constant it uses changes its implicit or instance arguments (see
*Known limits*).

## How keys are compared

A record keyed at one commit is compared with a dataset of another (see S3, *Status*):

* same name, same meaning hash: the record still applies (**current**);
* same name, same local hash, different meaning hash: the declaration is written the same, but
  something it rests on changed (**stale underneath**);
* same name, different local hash: the declaration itself changed (**stale**);
* name gone, exactly one declaration with the same meaning hash (and kind): the record follows it
  (**renamed**).

Hashes are comparable only when computed by the same hasher: the same semantic_hash revision and the
same local hash function. A consumer must treat keys from different hashers as incomparable, and a
producer changing either must change its identifier.

## Measured on Tau Ceti

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

## Known limits

* The local hash sees elaboration details: a declaration whose text is unchanged, but whose use of
  a constant now elaborates with different implicit or instance arguments (because that constant's
  signature changed), is **stale** rather than **stale underneath** (up to 135 of 394 stale
  declarations in the measurement above). A candidate fix for version 1 is a fourth hash, of the statement with
  implicit and instance arguments erased: a change of the local hash alone would then read as
  stale underneath.

* Hashes are 64-bit. A change goes unnoticed only if the new hash equals the old one, with
  probability 2⁻⁶⁴. The chance that any two of 10⁵ declarations share a meaning hash by accident,
  which would make a rename ambiguous, is about 3·10⁻¹⁰.
* The meaning hash inherits semantic_hash's proof irrelevance, which is structural: a proof written
  *inline* in a definition's value (not lifted into a `_proof_n` theorem) is hashed as a term. This
  can report a change that does not matter, never miss one.
* Hashes depend on what was visible when they were computed. The extractor imports every module at
  full visibility (including `.olean.private`), so definition bodies that a module does not export
  still contribute. A tool hashing at lower visibility would get different hashes for the same code,
  and its keys would not be comparable with the extractor's.
