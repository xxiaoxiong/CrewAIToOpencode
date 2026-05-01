# CrewAIToOpencode

CrewAIToOpencode is a personal local CrewAI + OpenCode multi-role programming orchestrator. It is meant for a single developer on one machine: you start OpenCode inside the target project, then this project calls the local OpenCode HTTP API to coordinate exploration, planning, implementation, validation, focused repair, and reporting.

It is not an enterprise platform. It does not provide Docker orchestration, databases, queues, multi-user workflows, or multiple managed OpenCode services.

## Core Value

This project is more than a thin OpenCode wrapper. The orchestration layer adds a controlled context flow:

- Generate a Task Contract from the user task.
- Convert every OpenCode stage response into a small Stage Artifact.
- Keep prompts short and task-focused.
- Validate work against the Task Contract, not a vague impression of success.
- Feed only failed criteria and blocking issues into repair prompts.
- Write reusable JSON and Markdown reports.

The main data flow is:

```text
user task
-> Task Contract
-> Stage Artifact
-> short prompt
-> Quality Gate
-> Contract Validator
-> focused Repair
-> concise report
```

OpenCode raw responses are not passed to later stages. Fields such as `tokens`, `cache`, `sessionID`, `messageID`, `parts`, `raw_response`, `info`, `snapshot`, and `metadata` are stripped before data can enter prompts, retry history, or reports.

## Start OpenCode

Open a terminal in the target project you want OpenCode to edit:

```bash
cd /path/to/target-project
opencode web --hostname 127.0.0.1 --port 4096
```

If your OpenCode server uses basic auth, set matching credentials before starting it and mirror them in `config/projects.yaml`.

## Run CrewAIToOpencode

Return to this repository:

```bash
python -m src.cli --project demo-project --doctor
python -m src.cli --project demo-project --capabilities
python -m src.cli --project demo-project --mode standard --task-file tasks/frontend-demo.txt
```

You can also pass a task directly:

```bash
python -m src.cli --project demo-project --mode quick --task "Update README.md with a short project overview."
```

## Configuration

Edit `config/projects.yaml`.

Important fields:

- `opencode_base_url`: local OpenCode HTTP API, normally `http://127.0.0.1:4096`.
- `opencode_username` / `opencode_password`: optional basic auth.
- `repo_path`: the repository inspected by local quality gates.
- `denied_paths`: safety floor for paths OpenCode must not edit, such as `.git/`, `node_modules/`, `.env`, `.env.local`, `dist/`, and `build/`.
- `test_command` and `lint_command`: commands used by the quality gate.
- `opencode_timeouts`: per-stage API timeouts. The default is at least 600 seconds.
- `prompt_limits`: prompt size limits. Defaults are `build_max_chars: 6000`, `retry_max_chars: 4000`, `plan_max_chars: 5000`, and `section_max_chars: 1800`.
- `crewai.enabled`: enables the CrewAI LLM stages for architect, tester, reviewer, and reporter.
- `crewai.llm.model`: default model is `claude-sonnet-4.6-thinking`.
- `crewai.llm.base_url`: default Claude-compatible endpoint is configured in `config/projects.yaml`.

`allowed_write_paths` may remain in old config files for compatibility, but it is no longer used as a blocking rule. Use `denied_paths` for safety boundaries.

The default `demo-project` is suitable for creating a small frontend project from scratch.

## LLM Setup

CrewAI LLM stages read credentials from `.env` or environment variables. Keep the API key out of `config/projects.yaml`.

```bash
LLM_MODEL=claude-sonnet-4.6-thinking
LLM_BASE_URL=https://yunyi.rdzhvip.com/claude
LLM_API_KEY=your-key
LLM_TEMPERATURE=0
```

Supported key aliases are `LLM_API_KEY`, `CLAUDE_API_KEY`, and `ANTHROPIC_API_KEY`.

## Modes

- `quick`: skips explore, architect, and OpenCode plan. It still builds, validates, reviews, and reports.
- `standard`: default daily mode. It runs explore and architect, but does not enable OpenCode plan.
- `deep`: enables the extra OpenCode plan stage for harder tasks.
- `full`: kept as a compatibility alias for deep-style behavior.

## Stage Artifacts

Stages exchange only Task Contract plus Stage Artifact data:

- `ExploreArtifact`: repository summary, project type, relevant files, risks, suggested scope.
- `PlanArtifact`: concise implementation steps, acceptance notes, risks.
- `BuildArtifact`: build or repair summary and changed-file hints.
- `ValidationArtifact`: per-criterion results, missing files, blocking issues, retry instruction.
- `ReviewArtifact`: reviewer pass/fail, score, blocking and non-blocking issues.

These artifacts may include a short `raw_text_truncated` text snippet for debugging context, but they never include the original OpenCode response object.

## Validation and Repair

The validator checks the Task Contract directly. For example, if the contract requires `package.json` or `src/App.jsx`, those files must appear in `changed_files`. A frontend project creation task fails if the result only changes `README.md`.

Retry prompts contain only:

- failed acceptance items,
- quality gate summary,
- validator and reviewer blocking issues,
- a focused repair instruction,
- prompt character count in retry history.

Retry history does not store the full prompt or any raw OpenCode response.

## Reports

Every run writes:

- `reports/report-YYYYMMDD-HHMMSS.json`
- `reports/report-YYYYMMDD-HHMMSS.md`

Reports include the Task Contract, stage artifacts, quality gate output, validator results, reviewer results, retry summaries, and final status. They do not store full prompts or OpenCode transport metadata.

## Troubleshooting

If OpenCode health checks fail, confirm the server is running on `127.0.0.1:4096` and credentials match `config/projects.yaml`.

If OpenCode returns HTML, the client reports: `OpenCode returned HTML, likely hit the web frontend route instead of API route.` This usually means the request reached the web frontend instead of an API route.

If quality gates fail because no changed files are detected, check that `repo_path` points to the same target project where OpenCode is running.
