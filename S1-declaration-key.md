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

It changes when the declaration itself is rewritten, and not when something it uses changes.

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

## Known limits

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
