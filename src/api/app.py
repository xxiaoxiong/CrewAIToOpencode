from __future__ import annotations

from pydantic import BaseModel

from src.orchestration.flow_runner import run_dev_task

try:
    from fastapi import FastAPI
except Exception as exc:  # pragma: no cover
    raise RuntimeError("fastapi is required to run src.api.app") from exc


app = FastAPI(title="CrewAIToOpencode POC")


class RunTaskRequest(BaseModel):
    project_id: str = "demo-project"
    task: str
    max_iterations: int | None = None


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/tasks/run")
def run_task(request: RunTaskRequest) -> dict:
    report = run_dev_task(request.project_id, request.task, request.max_iterations)
    return {
        "passed": report.get("passed", False),
        "report_json": report.get("report_json", ""),
        "report_md": report.get("report_md", ""),
    }
