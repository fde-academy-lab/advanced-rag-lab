# Newsletter · September 2026 · Issue 1

**Takeaways**

1. The agent *runtime* is becoming the product, not the model: DeepSeek open-sourced a harness
   where the model, tools, skills, sessions and sandbox are all swappable plug-ins. That is the
   seam architecture this repository teaches, applied one level up.
2. Everyone is building the box the agent runs in: Docker's disposable microVMs, Microsoft's
   ThinkingBox for "works once versus works every time". The grading bot here already runs
   learner code with no token in a throwaway job; the industry has caught up with the reason.
3. Cheaper long context does not change the first-stage rule. A million-token window still
   cannot recover a document retrieval never returned.

Every item below names its source and the date the source gave. The sources were read through
search summaries on 2 September 2026; the pages themselves were not reachable from the machine
that wrote this, so **check a number against the source before you quote it in a client room**.

---

### 1. DeepSeek Harness: everything is a plug-in

**What happened.** DeepSeek released *Harness* v0.1 as a developer preview on 13 August 2026,
alongside its V4-Pro model, under the MIT licence. The premise is that practically every part
of the agent runtime can be swapped as a plugin: models, tools, skills, sessions, sandboxes and
interfaces, including entire agent harnesses such as Claude Code or Codex. The repository passed
33,000 GitHub stars within hours, per the coverage. Sources:
[DeepSeek](https://deepseek.com/harness/en/),
[The Register, 14 Aug](https://www.theregister.com/ai-and-ml/2026/08/14/deepseeks-innovative-harness-treats-everything-as-a-plug-in/5288095),
[VentureBeat](https://venturebeat.com/technology/deepseek-harness-launches-as-open-source-rival-to-claude-code-alongside-v4-pro-on-api-with-higher-prices),
[The New Stack](https://thenewstack.io/deepseek-harness-open-source-plugins/).

**Why an FDE cares.** A client who asks "which agent framework" is asking the wrong question if
the runtime lets the model be swapped under a fixed harness. The decision moves to the eval:
which model, on *your* tasks, in *your* sandbox, with *your* tools. That is a measurement job.

**Try today.** The L.A.B. Simulator's grader is a harness with one plug-in slot: `check.py`.
Write a second grader for one unit that reaches the same verdict a different way, then run
`python -m labsim selftest` on both. If the two disagree on any reference case, you have found
the check that was carrying an assumption. Idea 12 on [Ideas To Try](Ideas-To-Try.md).

### 2. Microsoft Agent Lightning v1.0 and ThinkingBox

**What happened.** Microsoft released Agent Lightning v1.0 on 17 August 2026, an open-source
reinforcement-learning framework for agents, and ThinkingBox, an open-source sandbox for
testing whether agents do real work reliably rather than once. Source:
[AI Agent Store, August 2026 roundup](https://aiagentstore.ai/ai-agent-news/2026-august).

**Why an FDE cares.** "Reliably" is the word. A demo that works once is what every client has
already seen; what they are paying for is the number of times out of a hundred.

**Try today.** Run one drill's reference solution through the grader ten times in a row in a
Codespace and confirm the verdict is identical each time. Then do the same for an `answer`
drill with a near-miss value at the tolerance boundary (`RD2`'s tolerance is 0.03). A grader
that flips at the boundary is a grader that ranks noise.

### 3. Docker Sandboxes: disposable microVMs for coding agents

**What happened.** Docker launched *Docker Sandboxes*, disposable, isolated microVM environments
built so coding agents can run unattended with full autonomy. Source:
[AI Agent Store, week of 2 September](https://aiagentstore.ai/ai-agent-news/this-week).

**Why an FDE cares.** The security argument for running a stranger's code with no credentials
in scope is now a product category. The three-job split in
[`lab-simulator-discussions.yml`](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/.github/workflows/lab-simulator-discussions.yml)
(route with no code, grade with no token, respond with no untrusted code) is the same design
in GitHub Actions.

**Try today.** Read that workflow's header comment, then try to write a submission that makes
the *respond* job post something it should not. The sanitiser strips mentions and foreign HTML
comments; find what it does not strip, and open an issue rather than a thread.

### 4. Gemini 3.7 Flash: a million tokens at introductory pricing

**What happened.** Google released Gemini 3.7 Flash, aimed at software development, agent tasks
and document processing, with a context window up to 1 million tokens, 64,000-token maximum
output, and introductory pricing of $0.75 per million input tokens and $3.75 per million
output tokens through the end of 2026, as reported by
[AI Agent Store](https://aiagentstore.ai/ai-agent-news/today).

**Why an FDE cares.** Cheap long context is the strongest argument a client will make for
"just put the whole corpus in the prompt". Client Zero's 2,430 chunks would fit. The reason not
to is not cost; it is that the model reads the middle of a long window worst, and that a
retrieval stage is the only place recall can be measured at all.

**Try today.** Idea 4 on [Ideas To Try](Ideas-To-Try.md): halve and double k in the packer and
watch full-chain recall against evidence recall. Then ask what "put it all in" would do to the
first number, and whether you could ever know.

### 5. Claude Code: keyless sign-in, /web-setup, and /loop everywhere

**What happened.** The September 2026 Claude Code changelog lists sign-in through an Anthropic
Console account without an API key, a `/status` line showing whether GitHub is connected for
Claude Code on the web (with `/web-setup` when it is not), the model and effort each subagent
ran on shown in `/tasks`, and `/loop` self-paced mode available everywhere including Bedrock
and Vertex. Source: [gradually.ai changelog](https://www.gradually.ai/en/changelogs/claude-code/),
[Releasebot](https://releasebot.io/updates/anthropic/claude-code).

**Why an FDE cares.** Cohort operations here run from a browser session of Claude Code on the
web, with the GitHub connection tied to the delivery account rather than to a laptop. The
keyless path removes the last reason to paste a token into a chat, which is the single most
common security mistake in this repository's own history.

**Try today.** Open a Claude Code web session on this repository, ask it to run
`python scripts/run_eval.py --compare`, and have it paste the table with the intervals into a
Show and tell thread. Then check the numbers against the measurement note yourself.

### 6. Claudeforce: a default reasoning model inside a CRM

**What happened.** Salesforce and Anthropic announced *Claudeforce*, embedding Claude as a
default reasoning model across Agentforce, Slack and developer tools, with 37 prebuilt sales
skills and a September open beta, per
[AI Agent Store](https://aiagentstore.ai/ai-agent-news/today).

**Why an FDE cares.** "Prebuilt skills" is the enterprise version of the plug-in argument in
item 1. The FDE's job on such a platform is not to write the skill; it is to build the eval
set the skill is measured against, which nobody ships prebuilt.

**Try today.** Take one seeded use case from
[Design Reviews](https://github.com/fde-academy-lab/advanced-rag-lab/discussions/categories/design-reviews)
and write the ten-question eval set a prebuilt skill would have to pass before you let it near
the client's data. Post it; the argument in the replies is the deliverable.

---

## Three ideas to experiment with this month

- **A harness-swap drill.** An `implement` unit whose starter is a grader interface rather
  than a retrieval function: the learner writes a check, and the reference cases decide whether
  it is honest. Item 1 turned into fifteen minutes.
- **Reliability as a metric.** Add "verdict identical over N runs" to `labsim selftest` output.
  Item 2 as a repository feature; small, and it would have caught the tolerance-boundary case.
- **The long-context bet, measured.** A measurement note that puts the whole corpus in a
  long-context model and reports full-chain recall beside the retrieval pipeline's, with the
  cost per query for each. Item 4 as a cohort project; extension 14 has the seam.

Contributions for Issue 2: a thread in
[Ideas](https://github.com/fde-academy-lab/advanced-rag-lab/discussions/categories/ideas) with
the `newsletter` label, the link, the date, and one thing to try here.
