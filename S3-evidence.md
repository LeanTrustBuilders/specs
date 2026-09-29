# S3: evidence records (`ltb-evidence/2`)

An **evidence record** is one judgement or fact about a declaration, asserted by a person, an agent
or a tool: a review, a problem report, a link to a test, a proposed test (a challenge), a named
result. Records are JSON objects, stored one per line (JSONL), **append-only**: a record is never
edited; a later record supersedes, answers or resolves it.

Every record is **accountable**: it names the GitHub account it came from, or it is labelled as an
AI agent's, or both. There are no anonymous records.

Records live in **evidence stores** (below): directories in git repositories, filled by an intake
bot from GitHub issues and comments, or by pull requests.

The design behind the review fields is in
[`reviews.md`](https://github.com/LeanTrustBuilders/design/blob/main/AI_initial_docs/reviews.md).

## Compatibility

Records are never rewritten, so what a record says must stay readable as the spec grows:

* **Readers ignore** fields they do not know, and records of a kind they do not know. A reader that
  meets a value it does not know ignores a verdict or a state, and shows an axis of a rubric it does
  not know by its name.
* **Within a version**, fields are only added, and the values an enumeration allows only grow. No
  field changes meaning.
* **Rubrics are versioned**: within a version of a rubric (below), axes are only added, and none
  changes meaning. Any other change is a new version of the rubric.
* **A new version** is for a change that is not additive. Its readers need not read earlier
  versions: a store moving to it is rewritten once, its records converted and their ids, and the
  links between them, recomputed.

## Common fields

| field | required | meaning |
|---|---|---|
| `schema` | yes | `"ltb-evidence/2"` |
| `kind` | yes | `review`, `comment`, `status`, `test`, `challenge` or `named` |
| `id` | yes | the first 16 hex digits of the SHA-256 of the record's canonical form (below) |
| `subject` | `review`, `test`, `challenge`, `named`; optional for `comment` | the S1 key of the declaration the record is about (`name`, `module`, `package`, `commit`, `toolchain`, `hasher`, `hashes.meaning`, `hashes.local`), and `aspect`: what of it the record is about, `definition` (what it is), `statement` (what it states) or `instance` |
| `text` | per kind | the record's words, in Markdown: a review's reasons, a comment, a status's note, what a test checks, a challenge's property, what a named result is |
| `by` | yes | who made it (below) |
| `at` | yes | when, RFC 3339 in UTC |
| `origin` | no | where the record came from: `{kind, ref}`, e.g. `{"kind": "issue", "ref": "owner/repo#12"}` |
| `rubric` | when the record names an axis | the rubric that `category`, `checked`, `caveats` and `modes` name axes of (Rubrics, below), e.g. `"ltb-rubric/1"` |
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

**Canonical form.** The record without `id` and `signature`, in the JSON Canonicalization Scheme
(RFC 8785). Records hold no numbers other than integers and their keys are ASCII, so this is: keys
sorted, no whitespace, strings escaped as JSON requires and non-ASCII characters written as
themselves. `id` and signatures are computed over its UTF-8 bytes.

## Kinds

### `review`

| field | required | meaning |
|---|---|---|
| `verdict` | yes | `accept`, `problem` or `question` |
| `category` | for problems | what is wrong: an axis, or `other` |
| `text` | for problems, and for agents | why |
| `reference` | encouraged | what the subject was compared with: `{text, url}` |
| `checked` | encouraged | axis → `checked`, `unchecked` or `na` |
| `caveats` | no | `[{category, note}]`, `category` as above |
| `fix` | no | for problems: a suggested fix (Markdown, often Lean) |

A later review by the same identity (and, for an agent, the same tool and model) on the same
declaration can name the earlier one in `links.supersedes`: it is that reviewer's current view, and
the earlier one no longer counts.

### `comment`

Discussion: `text` (required), and `links.replies_to` (required), the record it answers or discusses.
`subject` is that record's subject, when it has one. An answer to a question is a comment on it.

### `status`

The state of an earlier record: `target` (a record id) and `state` (both required), and optionally
`text`, `commit` (for `fixed`: the commit that fixed it) and `test` (for `met`: the S1 key, or at
least the `name`, of the declaration that meets the challenge).

| state | for | meaning |
|---|---|---|
| `fixed` | a problem | the code was changed |
| `intended` | a problem | the behaviour is deliberate (and should be documented, ideally with an example) |
| `invalid` | a problem | there was no problem |
| `answered` | a question | it has an answer |
| `met` | a challenge | the library has a declaration that proves the property (`test`) |
| `failed` | a challenge | the subject does not have the property: that is a problem with it |
| `declined` | a challenge | it will not be written: not a useful test, or out of scope |
| `reopened` | a problem, question or challenge | open again |
| `withdrawn` | any record but a comment or status | its author takes it back |

The latest status of a target (by `at`, and between records with the same `at`, by `id`) is its
state. A problem, question or challenge with none is **open**; any other record with none stands.

### `test`

A declaration of the library that tests the subject: a lemma that pins it down (a value, a
degenerate case, agreement with another notion). `test` (required): its S1 key, or at least its
`name`; `text`: what it checks (required of an agent).

A test is a fact the kernel keeps checking: a view shows it as **passing** while a declaration of that
name (or, when `test` has a meaning hash, of that meaning) is in the dataset without `sorry` in its
axioms, and as **missing** or **with sorry** otherwise. It does not go stale as a review does.

### `challenge`

A **proposed test**: a property the subject should have, which anyone can then try to prove in the
library (or refute). It is how people and agents who read a definition, without writing the library,
say what would convince them it is right.

| field | required | meaning |
|---|---|---|
| `text` | yes | what the subject should satisfy, and why it is a good test |
| `statement` | no | the property as a Lean statement |
| `catches` | no | what a failure would reveal |
| `modes` | no | the axes on which it would catch a failure |

A challenge is open until a status says it was `met` (with the declaration that meets it, which the
views then check as a test), `failed` (which is a problem with the subject, reported as its own
review), `declined` or `withdrawn`.

### `named`

`name` (required), `what` (`result` or `definition`), `text` (a sentence), `reference` (where the
naming comes from: `{text, url}`): the subject is a named result or notable definition, one to read
first in a library whose other declarations are mostly API and steps of proofs. It can be withdrawn
by its author.

## Rubrics

A **rubric** is a list of **axes**: the ways a declaration can fail to mean what it should, which a
review says it checked and a problem says is wrong. An axis is named with lowercase ASCII letters,
digits and hyphens, starting with a letter. `other` is not an axis of any rubric: as a `category`, it
says that what is wrong is on none of them.

A rubric's name carries its version, as the hashers of S1 do. This spec suggests one, below; a store
may ask for another (its `store.json`, below), and a record says which one it used in `rubric`.

### `ltb-rubric/1`

| axis | a review that checked it says | a problem on it |
|---|---|---|
| `object` | it is the intended notion, or states the intended result, and not a different one | a different object |
| `convention` | it follows the source's conventions: normalization, indexing, signs, and the instances it picks up | a different convention |
| `edge-cases` | it decides degenerate and boundary inputs as the source does | different edge cases |
| `junk` | no default value outside the intended domain changes what it means | a junk value |
| `vacuous` | it is neither vacuous nor trivial | vacuous or trivial |
| `choice` | it makes no arbitrary choice where the intended object is canonical | an arbitrary choice |
| `generality` | it is as general as the source | less general than the source |
| `naming` | its name and docstring do not mislead | a misleading name or docstring |

These are the failure modes of
[`trusting-definitions.md`](https://github.com/LeanTrustBuilders/design/blob/main/AI_initial_docs/trusting-definitions.md)
§2 but two. What a declaration rests on is not an axis: the declarations underneath are nodes with
reviews of their own, and coverage asks for all of them. Drift is not an axis: a review that the
code has changed under is `stale` or `stale-underneath` (below).

## Status of a record

Against a dataset of the current code, a record whose subject has key `k` is:

| status | condition |
|---|---|
| `incomparable` | `k.hasher.meaning` or `k.hasher.local` differs from the dataset's (S1) |
| `unknown` | `k` has no meaning hash |
| `current` | a node named `k.name` has meaning hash `k.hashes.meaning` |
| `stale-underneath` | the node named `k.name` has another meaning hash but local hash `k.hashes.local` |
| `stale` | the node named `k.name` has another local hash |
| `unavailable` | no node is named `k.name`, and `k.module` is one of the dataset's `library.unavailable` modules (S2): it did not build at the dataset's commit, so the record cannot be checked |
| `renamed` | no node is named `k.name`, and exactly one node has meaning hash `k.hashes.meaning` (when several do, exactly one of the subject's `aspect`: `instance` for an instance, `statement` for a proof, `definition` for anything else) |
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
  optionally `claims` (declaration names: the claims, for a library that does not name its own, and
  otherwise ignored), `maintainers` (GitHub logins that may set statuses, besides the
  repository's collaborators) and `rubric`, the rubric its forms ask for when it is not
  `ltb-rubric/1`: `{name, axes}`, each axis `{name, check, problem}`, where `check` is what a review
  that checked it says and `problem` names a problem on it.
* **Records** are the lines of every `*.jsonl` file under `evidence/`.
  The store is the set of them, by `id`: the same record may appear twice; two different records with
  one `id` are an error.
* **Append-only**: between two commits of the store, every record of the earlier one is still
  there, unchanged. Corrections are new records. (The one exception is the rewrite that moves a
  store to a new version of this spec.)

**Writing to a store.** Every record says who made it, and a store only takes a record from that
identity:

* **intake from issues**: a bot turns an issue opened with one of the store's issue forms (a
  review, a problem, a question, a challenge, a test, a named result) into a record, and each later
  comment on that issue into a `comment` or, for a command such as `/fixed`, a `status`. Closing or
  reopening the issue by hand is a status too (closing a problem as completed says `fixed`, as not
  planned `invalid`; a challenge, `met` or `declined`). Lines such as `Reviewed-by: <declaration> —
  <note>` in a comment on the store's **bulk issue** are records of their own, one per line. The
  identity is the GitHub account that wrote the issue, comment or closed it. An agent says so in the
  form, or with a line `<!-- agent: tool=…; model=…; session=… -->` in a comment. `origin` records
  the issue, comment, line or event.
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
