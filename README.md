# CrewAIToOpencode

CrewAIToOpencode is a small Python orchestration POC for driving a local OpenCode HTTP service. It creates an OpenCode session, sends a structured development task, checks the resulting git diff with deterministic quality gates, runs a lightweight reviewer, retries failed work up to a configured limit, and writes JSON plus Markdown reports.

## Prerequisites

- Python 3.10+
- Git
- A target project with OpenCode started on `127.0.0.1:4096`
- Python dependencies from `requirements.txt`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Start OpenCode 4096

Windows PowerShell:

```powershell
cd D:\projects\demo-project

$env:OPENCODE_SERVER_USERNAME="opencode"
$env:OPENCODE_SERVER_PASSWORD="123456"

opencode web --hostname 127.0.0.1 --port 4096
```

Linux:

```bash
cd /data1/MyWorkSpace/projects/demo-project

export OPENCODE_SERVER_USERNAME=opencode
export OPENCODE_SERVER_PASSWORD=123456

opencode web --hostname 127.0.0.1 --port 4096
```

## Configure Projects

Edit `config/projects.yaml`. The default `demo-project` points at the included `demo-project/` target repository for easy POC testing. In real use, set `repo_path` to the project directory where OpenCode is running.

Key fields:

- `opencode_base_url`: OpenCode HTTP service URL.
- `opencode_username` / `opencode_password`: Basic auth credentials.
- `test_command`: command run by the quality gate.
- `lint_command`: optional lint command.
- OpenCode is not restricted by an allowed-path whitelist. It may create or modify project files in the current `repo_path` / OpenCode working directory.
- `denied_paths`: files or directories that must never be modified. The default safety floor protects `.git/`, `node_modules/`, `.env`, `.env.local`, `dist/`, and `build/`.
- `max_iterations`: retry limit.
- `opencode_timeouts`: per-stage message timeout settings for `explore`, `plan`, `build`, `repair`, and `validate`.

## Run CLI

```bash
python -m src.cli --project demo-project --task "请在 README.md 中新增一段 AI 自动开发 POC 说明，只允许修改 README.md"
```

Read the task from a file:

```bash
python -m src.cli --project demo-project --task-file task.txt
```

Create a frontend project in the included demo target:

```bash
python -m src.cli --project demo-project --mode standard --task-file tasks/frontend-demo.txt
```

## Prompt 压缩与上下文控制

The flow does not pass full raw OpenCode message responses into later stages. Explore, Plan, Build, and Validate responses are compacted into small summaries before they are used in prompts or reports.

Prompt limits are configured with `prompt_limits` in `config/projects.yaml`. If a build, retry, or plan prompt exceeds its limit, the flow fails before sending it to OpenCode so the context can be compressed.

Reports store compact stage results plus prompt summaries and character counts. They do not store full huge retry prompts or raw OpenCode response metadata such as tokens, cache, session IDs, message IDs, or parts.

Check OpenCode connectivity:

```bash
python -m src.cli --project demo-project --check-opencode
```

## Reports

Every run writes:

- `reports/report-YYYYMMDD-HHMMSS.json`
- `reports/report-YYYYMMDD-HHMMSS.md`

The reports include the task, project ID, session ID, changed files, quality gate results, reviewer results, failure reasons, and suggested next steps.

## FastAPI

```bash
uvicorn src.api.app:app --host 127.0.0.1 --port 7001
```

Then post a task:

```bash
curl -X POST http://127.0.0.1:7001/tasks/run ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":\"demo-project\",\"task\":\"请在 README.md 中新增 AI POC 说明\",\"max_iterations\":3}"
```

## FAQ

If OpenCode health checks fail, confirm the service is running on port `4096` and the credentials match `projects.yaml`.

If quality gates fail because no changed files are detected, OpenCode likely did not modify the target repository or the configured `repo_path` points to the wrong directory.

If reviewer output is not valid JSON, the POC keeps the raw output and fails safely instead of crashing the flow.
