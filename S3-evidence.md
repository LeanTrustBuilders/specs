# S3: evidence records (`ltb-evidence/0`)

An **evidence record** is one judgement or fact about a declaration, asserted by a person, an agent
or a tool: a review, a problem report, a link to a test, a named result. Records are JSON objects,
stored one per line (JSONL), **append-only**: a record is never edited; a later record supersedes,
answers or resolves it.

The design behind the review fields is in
[`reviews.md`](https://github.com/LeanTrustBuilders/design/blob/main/AI_initial_docs/reviews.md).

## Common fields

| field | required | meaning |
|---|---|---|
| `schema` | yes | `"ltb-evidence/0"` |
| `kind` | yes | `review`, `status`, `test` or `named` |
| `id` | yes | the first 16 hex digits of the SHA-256 of the record's canonical form (below) |
| `subject` | all kinds but `status` | the S1 key of the declaration the record is about, plus `kind`: `definition`, `statement`, `instance`, `link` or `text` |
| `by` | yes | `kind` (`person` or `agent`); `identity` (`{kind: none}`, `{kind: github, id}`, or `{kind: key, fingerprint}`); `agent` (required for an agent: tool, model, session); `involvement` (`author`, `contributor`, `outsider`, `unknown`) |
| `at` | yes | when, RFC 3339 in UTC |
| `origin` | no | where the record came from: `{kind, ref}`, e.g. `{"kind": "issue", "ref": "owner/repo#12"}` |
| `links` | no | `supersedes`, `replies_to`: record ids |
| `migration` | no | for records converted from another tool: `from`, and `hashes_from` when the subject's hashes were taken at another commit than `subject.commit` |
| `signature` | no | an armored OpenPGP signature over the canonical bytes, by `by.identity` |

**Canonical form.** The JSON encoding of the record without `id` and `signature`, with keys sorted,
no whitespace, and non-ASCII characters written as themselves. `id` and signatures are computed over
its UTF-8 bytes.

## Kinds

### `review`

| field | required | meaning |
|---|---|---|
| `verdict` | yes | `accept`, `problem` or `question` |
| `problem.category` | for problems | `F1` different object, `F2` convention, `F3` edge cases, `F4` junk value, `F5` vacuous, `F6` choice, `F7` wrong thing underneath, `F8` drift, `F9` generality, `naming`, `other` |
| `rationale` | for problems, and for agents | why |
| `reference` | encouraged | what the subject was compared with: `{text, url}` |
| `checked` | encouraged | failure mode → `checked`, `unchecked` or `na` |
| `caveats` | no | `[{category, note}]` |

The failure modes are those of
[`trusting-definitions.md`](https://github.com/LeanTrustBuilders/design/blob/main/AI_initial_docs/trusting-definitions.md) §2.

### `status`

The state of an earlier record, usually a problem: `target` (a record id) and `state`: `fixed`,
`intended` (the behaviour is deliberate), `invalid`, `reopened`, or `withdrawn` (the author takes
the record back). The latest status of a target, by `at`, is its state; a problem with none is
**open**.

### `test`

`test`: the S1 key (or at least the `name`) of a declaration that tests the subject, and `checks`:
what it checks.

### `named`

`name`, `what` (`result` or `definition`), `about`, `source`: the subject is a named result or
notable definition.

## Status of a record

Against a dataset of the current code, a record whose subject has key `k` is:

| status | condition |
|---|---|
| `incomparable` | `k.hasher` names a different hasher revision than the dataset |
| `unknown` | `k` has no meaning hash |
| `current` | a node named `k.name` has meaning hash `k.hashes.meaning` |
| `stale-underneath` | the node named `k.name` has another meaning hash but local hash `k.hashes.local` |
| `stale` | the node named `k.name` has another local hash |
| `renamed` | no node is named `k.name`, and exactly one node (of the subject's kind, if several) has meaning hash `k.hashes.meaning` |
| `orphaned` | otherwise |

A record **applies** to the current code when it is `current` or `renamed`.

## Coverage (informative)

A claim is **covered**, under a reader's policy, when every project node in its `meaning` closure
(the claim included) has an `accept` review that applies and that the policy counts, and none has an
open problem. A policy says whose reviews count: agents or not, authors or not, reviews with caveats
or not, reviews stale underneath or not, and whether upstream nodes must be reviewed too.
evidence-core implements this; the policy is the reader's choice, not part of the records.
