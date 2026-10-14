## Git management
- **Commit for each individual feature.**
- Use `lore-commits` for non-trivial commits.
- Use `lore-query` to inspect decision context and `lore-setup` to configure Lore rules.

## Tool bootstrap

At session start, verify that the current agent can call or invoke each tool below. Do not reinstall
components that already work.

- **CodeGraph MCP** — repo: [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph).
  Install if missing: `npm install -g @colbymchenry/codegraph && codegraph install -y`.
  Then verify that `codegraph_explore` is callable before code exploration or edits. If `.codegraph/`
  is absent, do not run `codegraph init` automatically; ask the user to index the project.
- **Graphify** — repo: [safishamsi/graphify](https://github.com/safishamsi/graphify). Install if
  missing: `python3 -m pip install graphifyy && graphify install`. Both the skill and `graphify` CLI
  are required; run `graphify update .` after installation.
- **Lore** — repo: [tmdgusya/lora](https://github.com/tmdgusya/lora). Install if any of
  `lore-commits`, `lore-query`, or `lore-setup` is missing: `npx skills add tmdgusya/lora -g`.
  Reread each installed `SKILL.md` and use the skills.

## Lore commit context
- Use an imperative summary and meaningful Lore trailers for non-trivial commits. Include `Constraint`, `Directive`, `Tested`, `Not-tested`, `Confidence`, and `Reversibility` only when each carries real context.
- Record the affected `Lab-Vulnerability: Axx` or `Lab-Vulnerability: Sxx` on vulnerability commits. Keep one planned service or server work unit per commit; split larger work rather than making an omnibus commit.
- Never claim a check ran when it did not. Keep credential values, private keys, and unmasked secrets out of commits and Graphify input.

Install or enable missing capabilities before continuing. Verify that they are callable in the
current session; if installation fails, report the missing capability and required user action
instead of silently substituting another tool.

## Knowledge graph workflow

Use **CodeGraph** for code structure and **Graphify** to help the agent understand source code and cross-file relationships.
They are complementary, not interchangeable.

### CodeGraph

- Before exploring symbols, call flows, impact, or code changes, call `codegraph_explore` with the
  relevant question, symbols, or files.
- Trust its source and blast-radius output; use ordinary file tools only for unsupported formats such
  as Markdown, JSON, YAML, and other configuration files.
- Never run `codegraph init` automatically on an unindexed project. If the index is stale, prefer the
  current file content and resolve any post-edit sync warnings.
- For visual call-graph inspection, use `codegraph ui [path]` (default `http://127.0.0.1:4747`;
  add `--read-only` to prevent saved navigation).

### Graphify

- `graphify-out/` is an agent assistance artifact, not a product acceptance deliverable.
- Run `graphify update .` at the repository root for initial architecture discovery and after code or
  documentation changes. Record only command completion and exit status; this is sufficient.
- Unless the user requests them, no graph structure quality checks (including edge counts, direction,
  multiplicity, communities or source fidelity), bespoke export repair, benchmarks, or independent
  Graphify QA/reviewer are required. Graphify output quality is not a product acceptance gate.
- Semantic extraction for docs, papers or images is optional when needed for source understanding;
  documentation changes do not require a separate semantic extraction pass.
- Use `graphify cluster-only .` to regroup an existing graph. Enable `graphify watch .` only for an
  explicitly long-running development session; never mix it with the production scheduler.
- Treat `EXTRACTED`, `INFERRED`, and `AMBIGUOUS` edges differently. Verify inferred or ambiguous
  edges against source locations before stating them as facts.
- Exclude `.env`, Gmail credentials, API keys, and other secrets from Graphify input. Report only the
  count of skipped sensitive files, never their names or contents.
- Check file and word counts before semantic extraction because it can consume tokens. Do not rerun
  semantic extraction for code-only changes when the AST graph is sufficient.
- Do not invent relationships when summarizing Graphify output; mark unsupported conclusions as
  `AMBIGUOUS`.
