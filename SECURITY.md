# Security policy

## Reporting a vulnerability

**Do not open a public issue.** Email **the address in SECURITY.md** with:

- What you found and where
- How to reproduce it
- What an attacker could do with it

You will get an acknowledgement within three working days and an assessment within ten.

## Scope

This is a teaching repository that runs offline. The realistic surface is small, and being
precise about it is part of the lesson.

### In scope

| Class | Why it matters here |
|---|---|
| **Credential or key leakage** | Anything in the repo, the notebooks, or CI logs that could expose an AWS or API credential |
| **The ACL model** | A path by which a persona receives evidence outside its groups — including through caches, traces, result counts or latency |
| **Prompt injection through retrieved content** | Retrieved documents are untrusted input. The current prompt contract does **not** treat them as such, and hardening it is a known gap — see [EXTENSION-POINTS.md #17](docs/09-research/extension-points.md) |
| **Dependency vulnerabilities** | Reported by Dependabot; PRs welcome |
| **CI workflow injection** | `pull_request_target` workflows that could be made to run untrusted code |

### Out of scope

- The synthetic corpus contains no real data. Organisations, people and events in it are
  fictional and generated from a fact graph.
- Denial of service against your own machine by setting `n_candidates=10_000_000`.
- The absence of authentication. There is no server.

## Handling credentials

**This repository never reads, stores or logs a credential.**

- AWS credentials come from the standard boto3 chain (environment, `~/.aws/credentials`, SSO,
  instance role). `raglab.bedrock` never accepts a key as an argument.
- `preflight()` is deliberately read-only: it reports what is *configured* and makes no AWS
  calls, so nobody bills an account by hitting Run All.
- `.gitignore` excludes `.env`, `*.pem`, `credentials*` and `.aws/`.
- Do not paste credentials into Discussions or issues. If you do, rotate them first, then
  delete the post — deletion alone is not sufficient.

## A note for students

Two habits worth carrying out of here:

1. **Traces store retrieved text**, so a trace store inherits the compliance boundary of the
   corpus it read — including its retention policy and its jurisdiction. This is the part
   people forget when they add observability.
2. **A shared prompt-prefix cache across tenants is a data-leak class of bug**, not a
   performance issue. Key it per tenant.
