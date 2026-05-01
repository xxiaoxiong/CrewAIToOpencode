# Implementation Notes

This POC keeps the orchestration layer small and explicit.

## Flow

1. `src.cli` reads task input.
2. `src.config_loader` loads `config/projects.yaml`.
3. `src.opencode.client.OpenCodeClient` checks OpenCode, creates a session, sends the prompt, and fetches diff data.
4. `src.quality.quality_gate` gathers git status/diff, runs configured test/lint commands, checks file policy, and scans dangerous patterns.
5. `src.reviewer.crew_reviewer` reviews the result with CrewAI when available and falls back to deterministic checks when it is not.
6. `src.orchestration.flow_runner` retries failed work up to `max_iterations`.
7. `src.orchestration.report_writer` writes JSON and Markdown reports under `reports/`.

## POC Boundaries

- No database.
- No queue.
- No multi-user model.
- No automatic GitLab or GitHub merge request creation.
- Worktree support is present as a small helper but disabled by default.
- FastAPI runs tasks synchronously.

## Main Command

```bash
python -m src.cli --project demo-project --task "请在 README.md 中新增一段 AI 自动开发 POC 说明，只允许修改 README.md"
```

OpenCode must already be running at the configured `opencode_base_url`.
