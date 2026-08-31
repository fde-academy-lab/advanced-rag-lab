# 01 · Architecture

| File | Level | What it answers |
|---|---|---|
| [overview.md](overview.md) | HLD | The four planes, the module map, the query path, the index lifecycle |
| [lld/](lld/) | LLD | One document per module: contracts, invariants, complexity, failure modes |
| [data-model.md](data-model.md) | LLD | Every table, index and id scheme, and why chunk ids are content-addressed |
| [seams.md](seams.md) | Design | The ten places a new technique plugs in without touching the harness |
| [adr/](adr/) | Decisions | Eight architecture decision records, in Nygard format |

Read `overview.md` first. The LLDs assume you have seen the four planes and will not
re-explain them.
