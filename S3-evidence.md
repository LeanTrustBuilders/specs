# S3: evidence records (`ltb-evidence/0`)

An **evidence record** is one judgement or fact about a declaration, asserted by a person, an agent
or a tool: a review, a problem report, a link to a test, a named result. Records are JSON objects,
stored one per line (JSONL), **append-only**: a record is never edited; a later record supersedes,
answers or resolves it.

Every record is **accountable**: it names the GitHub account it came from, or it is labelled as an
AI agent's, or both. There are no anonymous records.

Records live in **evidence stores** (below): directories in git repositories, filled by an intake
bot from GitHub issues and comments, or by pull requests.

The design behind the review fields is in
[`reviews.md`](https://github.com/LeanTrustBuilders/design/blob/main/AI_initial_docs/reviews.md).
Version 0 is a draft, changed in place while only the pilots use it.

## Common fields

| field | required | meaning |
|---|---|---|
| `schema` | yes | `"ltb-evidence/0"` |
| `kind` | yes | `review`, `comment`, `status`, `test` or `named` |
| `id` | yes | the first 16 hex digits of the SHA-256 of the record's canonical form (below) |
| `subject` | `review`, `test`, `named`; optional for `comment` | the S1 key of the declaration the record is about, plus `kind`: `definition`, `statement`, `instance`, `link` or `text` |
| `by` | yes | who made it (below) |
| `at` | yes | when, RFC 3339 in UTC |
| `origin` | no | where the record came from: `{kind, ref}`, e.g. `{"kind": "issue", "ref": "owner/repo#12"}` |
| `links` | no | `supersedes`, `replies_to`: record ids |
| `migration` | no | for records converted from another tool: `from`, and `hashes_from` when the subject's hashes were taken at another commit than `subject.commit` |
| `signature` | no | reserved for signed records |

**`by`: who made it.**

| field | required | meaning |
|---|---|---|
| `kind` | yes | `person` or `agent` (an AI agent) |
| `identity` | for a person; for an agent that acted through GitHub | `{"kind": "github", "id": "<login>"}`: the account that wrote the issue, comment or pull request the record came from. For an agent, that is the account it acted through: its operator's, or its own bot account |
| `agent` | for an agent | `{tool, model, session}`: what produced it, e.g. `{"tool": "Claude Code", "model": "claude-opus-5-5"}`; `tool` is required |
| `involvement` | no | `author` (of the declaration), `contributor` (to the library), `outsider`, or `unknown` (the default) |

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

A later review by the same identity (and, for an agent, the same tool and model) on the same
declaration can name the earlier one in `links.supersedes`: it is that reviewer's current view, and
the earlier one no longer counts.

### `comment`

Discussion: `text` (Markdown), and `links.replies_to`, the record it answers or discusses. `subject`
is that record's subject, when it has one. An answer to a question is a comment on it.

### `status`

The state of an earlier record: `target` (a record id), `state`, and optionally `note` and `commit`
(for `fixed`: the commit that fixed it).

| state | for | meaning |
|---|---|---|
| `fixed` | a problem | the code was changed |
| `intended` | a problem | the behaviour is deliberate (and should be documented, ideally with an example) |
| `invalid` | a problem | there was no problem |
| `answered` | a question | it has an answer |
| `reopened` | a problem or question | open again |
| `withdrawn` | any review | its author takes it back |

The latest status of a target, by `at`, is its state. A problem or question with none is **open**;
an `accept` with none stands.

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
| `unavailable` | no node is named `k.name`, and `k.module` is one of the dataset's `library.unavailable` modules (S2): it did not build at the dataset's commit, so the record cannot be checked |
| `renamed` | no node is named `k.name`, and exactly one node (of the subject's kind, if several) has meaning hash `k.hashes.meaning` |
| `orphaned` | otherwise |

A record **applies** to the current code when it is `current` or `renamed`.

## Threads (informative)

The records about a declaration read as threads: each review, with the comments replying to it and
the statuses about it, in time order. A review is **in force** when it applies to the current code
(above), is not withdrawn, and is not superseded. An `accept` and a `problem` in force on the same
declaration are a **disagreement**, which a view shows rather than resolves.

## Evidence stores

An **evidence store** is a directory `evidence/` in a git repository: the repository of the library
the records are about, or another one.

* `evidence/store.json` describes it: `spec` (`"ltb-evidence-store/0"`); `library`: `repo`
  (`owner/name`) and `root` (the library's root module); `datasets`: where the S2 datasets of the
  library's commits are, as `repo`, a release `tag` template (`"dataset-{commit12}"`, where
  `{commit12}` is the first 12 characters of the commit) and the `asset` (`dataset.tar.gz`);
  optionally `claims` (declaration names) and `maintainers` (GitHub logins that may set statuses,
  besides the repository's collaborators).
* **Records** are the lines of every `*.jsonl` file under `evidence/`. The store is the set of them,
  by `id`: the same record may appear twice; two different records with one `id` are an error.
* **Append-only**: between two commits of the store, every record of the earlier one is still
  there, unchanged. Corrections are new records.

**Writing to a store.** Every record says who made it, and a store only takes a record from that
identity:

* **intake from issues**: a bot turns an issue opened with one of the store's issue forms (a
  review, a problem, a question) into a record, and each later comment on that issue into a
  `comment` or, for a command such as `/fixed`, a `status`. The identity is the GitHub account that
  wrote the issue or comment. An agent says so in the form, or with a line
  `<!-- agent: tool=…; model=…; session=… -->` in a comment. `origin` records the issue or comment.
* **pull requests**: records added by a pull request must have the pull request's author as their
  identity.

Who may set which status is the store's policy. The reference intake lets the author of a record
withdraw it; the author of a problem or question, and the store's maintainers, set the other
states.

[evidence-store](https://github.com/LeanTrustBuilders/evidence-store) implements intake, the checks
and the setup of a store in a repository.

## Coverage (informative)

A claim is **covered**, under a reader's policy, when every project node in its `meaning` closure
(the claim included) has an `accept` review in force that the policy counts, and none has an open
problem. A policy says whose reviews count: agents or not, authors or not, reviews with caveats
or not, reviews stale underneath or not, and whether upstream nodes must be reviewed too.
evidence-core implements this; the policy is the reader's choice, not part of the records.
