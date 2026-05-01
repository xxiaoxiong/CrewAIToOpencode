你现在要实现一个 Python 项目，项目名称建议为：

```
CrewAIToOpencode
```

这个项目的目标是：**通过 Python 编排层调用本地 OpenCode 4096 HTTP 服务，让 OpenCode 作为真实代码执行器，完成“接收任务 → 创建 OpenCode session → 发送编程任务 → 获取 diff → 运行测试/质量门禁 → Reviewer 审查 → 失败自动返工 → 最终输出报告”的闭环。**

请严格按本文档实现，不要随意扩展成复杂平台。第一版只做“可用型 POC”，不做 Web UI、不做多用户、不做数据库、不做 GitLab MR、不做复杂队列。

你需要完成：

```
1. Python 项目骨架
2. OpenCode HTTP Client
3. 项目配置读取
4. 质量门禁模块
5. CrewAI Reviewer Agent
6. 主流程编排器
7. 命令行入口
8. 报告输出
9. 可选 FastAPI 接口
10. 可选 git worktree 管理
```

最终验收标准：

```
1. 可以连接已经启动的 OpenCode 4096 服务
2. 可以创建 OpenCode session
3. 可以发送任务给 OpenCode build agent
4. 可以获取 session diff
5. 可以检查 git status / git diff
6. 可以运行配置中的 test_command / lint_command
7. 可以检查禁止修改文件、允许修改范围、危险模式
8. 可以调用 CrewAI Reviewer 审查 diff 和质量门禁结果
9. 失败时最多自动返工 3 轮
10. 成功或失败都必须输出 JSON 报告和 Markdown 报告
```

实现过程中每完成一个模块都要自测。不要等我催。每一步都要能运行。

------

# 二、项目背景

当前用户已经在本地启动了 OpenCode Web / Server，端口是：

```
http://127.0.0.1:4096
```

OpenCode 是实际的编程执行器。它可以：

```
读取项目文件
修改代码
运行命令
创建 session
接收 message
返回 diff
查看文件状态
```

本项目不直接写业务代码，而是作为外部编排层，负责：

```
管理任务
生成高质量任务提示词
调用 OpenCode
运行测试
检查 diff
审查结果
失败返工
输出报告
```

第一版以单机、单项目、单 OpenCode 服务为主。

------

# 三、第一版目标

## 3.1 必须实现的能力

第一版必须支持：

```
固定一个业务项目
固定一个 OpenCode 4096 服务
通过 Python 创建 OpenCode session
通过 Python 发送任务给 OpenCode
通过 Python 获取 session diff
通过 Python 运行测试命令
通过 Python 检查 git status / git diff
通过 Python 检查文件修改策略
通过 CrewAI Reviewer 审查改动
失败自动返工，最多 3 轮
最终生成报告
```

## 3.2 第一版暂不实现

第一版不要实现：

```
Web 前端页面
多用户权限
数据库
任务队列
GitLab MR 自动创建
Docker 沙箱
多 OpenCode 实例池
复杂 MCP 管理
多项目并发
Kubernetes 部署
```

可以预留接口，但不要把第一版做复杂。

------

# 四、整体架构

目标架构如下：

```
用户 / 命令行
  ↓
Python 编排项目
  ↓
读取 projects.yaml
  ↓
连接 OpenCode 4096
  ↓
创建 session
  ↓
生成结构化任务 Prompt
  ↓
POST /session/:id/message
  ↓
OpenCode 执行代码修改
  ↓
GET /session/:id/diff
  ↓
本地质量门禁：
  - git status
  - git diff
  - test_command
  - lint_command
  - 文件策略检查
  - 危险模式检查
  ↓
CrewAI Reviewer 审查
  ↓
是否通过？
  ├── 是：输出最终报告
  └── 否：把失败原因发回 OpenCode 继续修，最多 3 轮
```

核心原则：

```
CrewAI / Python 编排层：负责流程、判断、审查、报告
OpenCode：负责真实代码修改和命令执行
质量门禁：负责确定性验收
Reviewer Agent：负责语义审查
```

------

# 五、推荐目录结构

请实现如下目录结构：

```
ai-dev-team-poc/
├── README.md
├── IMPLEMENTATION.md
├── requirements.txt
├── .env.example
├── config/
│   └── projects.yaml
├── reports/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── cli.py
│   ├── settings.py
│   │
│   ├── config_loader.py
│   │
│   ├── opencode/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── errors.py
│   │
│   ├── quality/
│   │   ├── __init__.py
│   │   ├── command_runner.py
│   │   ├── git_checker.py
│   │   ├── file_policy.py
│   │   ├── pattern_checker.py
│   │   └── quality_gate.py
│   │
│   ├── reviewer/
│   │   ├── __init__.py
│   │   └── crew_reviewer.py
│   │
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── prompt_builder.py
│   │   ├── flow_runner.py
│   │   └── report_writer.py
│   │
│   ├── workspace/
│   │   ├── __init__.py
│   │   └── worktree_manager.py
│   │
│   └── api/
│       ├── __init__.py
│       └── app.py
└── tests/
    ├── test_file_policy.py
    ├── test_pattern_checker.py
    └── test_prompt_builder.py
```

其中：

```
src/cli.py：命令行入口
src/api/app.py：可选 FastAPI 入口
src/opencode/client.py：OpenCode HTTP API 封装
src/quality/*：质量门禁
src/reviewer/crew_reviewer.py：CrewAI 审查 Agent
src/orchestration/flow_runner.py：主流程
src/orchestration/report_writer.py：报告输出
```

------

# 六、依赖要求

创建 `requirements.txt`：

```
crewai
fastapi
uvicorn
requests
pydantic
pyyaml
python-dotenv
rich
```

如果 CrewAI 安装存在版本兼容问题，允许先把 Reviewer Agent 做成普通 LLM HTTP 调用占位，但代码结构必须保留 `crew_reviewer.py`，后续可以替换。

------

# 七、配置文件设计

创建 `config/projects.yaml`：

```
projects:
  demo-project:
    name: demo-project

    # 业务项目路径。第一版要求 OpenCode 4096 就是在这个目录启动的。
    repo_path: "D:/projects/demo-project"

    # OpenCode 服务地址
    opencode_base_url: "http://127.0.0.1:4096"
    opencode_username: "opencode"
    opencode_password: "123456"

    # OpenCode agent
    opencode_agent: "build"

    # 可选：如果 OpenCode API 需要指定模型，可使用这两个字段
    opencode_provider_id: ""
    opencode_model_id: ""

    # 测试命令。根据项目类型配置
    test_command: "npm test"

    # 可为空
    lint_command: ""

    # 允许修改的路径。为空代表不限制，但第一版建议必须配置
    allowed_write_paths:
      - "src/"
      - "tests/"
      - "README.md"

    # 禁止修改的路径
    denied_paths:
      - ".env"
      - ".env.local"
      - "docker-compose.prod.yml"
      - "package-lock.json"
      - "pnpm-lock.yaml"
      - "yarn.lock"

    # 最大返工轮次
    max_iterations: 3

    # 是否启用 Reviewer Agent
    reviewer_enabled: true

    # 是否启用 lint
    lint_enabled: false

    # 是否启用测试
    test_enabled: true

    # 是否启用 git worktree。第一版默认 false，后续可开启
    worktree_enabled: false
```

`.env.example`：

```
# CrewAI / Local LLM
LLM_MODEL=openai/qwen3.5-27b-fp8
LLM_BASE_URL=http://127.0.0.1:8000/v1
LLM_API_KEY=EMPTY
LLM_TEMPERATURE=0.1

# Default project
DEFAULT_PROJECT_ID=demo-project
```

------

# 八、核心模块设计

## 8.1 OpenCode HTTP Client

文件：

```
src/opencode/client.py
```

必须封装这些方法：

```
class OpenCodeClient:
    def health(self) -> dict: ...
    def current_path(self) -> dict: ...
    def vcs(self) -> dict: ...
    def agents(self) -> dict: ...
    def create_session(self, title: str) -> dict: ...
    def send_message(self, session_id: str, text: str, agent: str = "build") -> dict: ...
    def list_messages(self, session_id: str, limit: int = 20) -> dict: ...
    def get_diff(self, session_id: str) -> dict: ...
    def file_status(self) -> dict: ...
    def abort(self, session_id: str) -> dict: ...
```

实现要求：

```
1. 使用 requests
2. 支持 HTTP Basic Auth
3. 每个请求必须设置 timeout
4. 请求失败要抛出清晰异常
5. 返回值保持 dict
6. send_message 支持 agent 参数
7. 可选支持 providerID/modelID
```

`send_message` 请求体基础格式：

```
{
  "agent": "build",
  "parts": [
    {
      "type": "text",
      "text": "任务内容"
    }
  ]
}
```

如果配置了模型，则使用：

```
{
  "agent": "build",
  "model": {
    "providerID": "vllm",
    "modelID": "qwen3.5-27b-fp8"
  },
  "parts": [
    {
      "type": "text",
      "text": "任务内容"
    }
  ]
}
```

------

## 8.2 命令执行模块

文件：

```
src/quality/command_runner.py
```

必须实现：

```
def run_cmd(cmd: str, cwd: str, timeout: int = 600) -> dict:
    ...
```

返回格式：

```
{
  "enabled": true,
  "passed": true,
  "cmd": "npm test",
  "stdout": "...",
  "stderr": "...",
  "returncode": 0
}
```

要求：

```
1. cmd 为空时返回 enabled=false, passed=true
2. stdout/stderr 最多保留最后 8000～12000 字符
3. timeout 要可配置
4. 不要让命令异常导致整个程序崩溃，应该返回失败结果
```

------

## 8.3 Git 检查模块

文件：

```
src/quality/git_checker.py
```

必须实现：

```
def get_git_status(cwd: str) -> str: ...
def get_git_diff(cwd: str) -> str: ...
def get_git_diff_stat(cwd: str) -> str: ...
def extract_changed_files(status_text: str) -> list[str]: ...
```

要求：

```
1. 使用 git status --short
2. 使用 git diff
3. 支持 Windows 路径转换为 /
4. 能识别 rename 情况
5. git 命令失败时返回清晰错误
```

------

## 8.4 文件策略模块

文件：

```
src/quality/file_policy.py
```

必须实现：

```
def check_file_policy(
    changed_files: list[str],
    allowed_paths: list[str],
    denied_paths: list[str]
) -> dict:
    ...
```

返回：

```
{
  "passed": true,
  "violations": []
}
```

判断规则：

```
1. 命中 denied_paths 必须失败
2. 如果 allowed_paths 非空，所有 changed_files 必须在 allowed_paths 范围内
3. 支持文件精确匹配
4. 支持目录前缀匹配
5. 路径统一转成 /
```

示例：

```
allowed_write_paths:
  - src/
  - tests/
  - README.md

changed_files:
  - src/auth/login.ts         通过
  - tests/auth/login.test.ts  通过
  - README.md                 通过
  - package.json              不通过
```

------

## 8.5 危险模式检查模块

文件：

```
src/quality/pattern_checker.py
```

检查 `git diff` 中是否出现危险模式。

必须检查：

```
TODO
FIXME
HACK
hack
临时绕过
先这样
skip test
it.skip
describe.skip
@Disabled
console.log(
debugger
password=
api_key=
secret=
```

实现：

```
def scan_bad_patterns(diff_text: str) -> dict:
    ...
```

返回：

```
{
  "passed": false,
  "hits": ["TODO", "it.skip"]
}
```

注意：第一版可以简单字符串匹配，后续再升级正则。

------

## 8.6 质量门禁模块

文件：

```
src/quality/quality_gate.py
```

必须实现：

```
def run_quality_gate(project_config: dict) -> dict:
    ...
```

内部执行：

```
1. git status --short
2. git diff
3. git diff --stat
4. 提取 changed_files
5. 执行 test_command
6. 执行 lint_command
7. 文件策略检查
8. 危险模式检查
9. 生成 passed
```

通过条件：

```
1. changed_files 不为空
2. test_enabled=true 时 test_command 必须通过
3. lint_enabled=true 时 lint_command 必须通过
4. 文件策略必须通过
5. 危险模式检查必须通过
```

返回格式：

```
{
  "passed": true,
  "changed_files": [],
  "git_status": "",
  "git_diff_stat": "",
  "diff": "",
  "test": {},
  "lint": {},
  "file_policy": {},
  "bad_patterns": {}
}
```

------

## 8.7 Prompt Builder

文件：

```
src/orchestration/prompt_builder.py
```

必须实现：

```
def build_initial_prompt(task_text: str, project_config: dict) -> str: ...
def build_retry_prompt(
    task_text: str,
    quality_result: dict,
    review_result: dict,
    iteration: int
) -> str: ...
```

### 初始 Prompt 要包含

```
任务目标
执行约束
允许修改路径
禁止修改路径
测试命令
禁止行为
输出要求
```

初始 Prompt 模板：

```
你是 OpenCode 编程执行 Agent。请在当前项目中完成以下任务。

【任务目标】
{task_text}

【执行约束】
1. 先阅读相关代码，再制定简短修改计划。
2. 只做最小必要修改，不要大范围重构。
3. 只允许修改这些范围：
{allowed_write_paths}
4. 禁止修改这些文件或目录：
{denied_paths}
5. 不允许删除测试来让测试通过。
6. 不允许通过 mock、硬编码、跳过测试、注释掉逻辑来伪造成功。
7. 修改完成后，请运行项目测试命令：
{test_command}
8. 如果测试失败，请根据失败日志继续修复。
9. 最终说明修改了哪些文件、为什么修改、测试结果如何。

请开始执行。
```

### 返工 Prompt 要包含

```
原始任务
当前返工轮次
质量门禁失败原因
测试日志
lint 日志
Reviewer 阻塞问题
明确要求只修复失败点
```

------

## 8.8 Reviewer Agent

文件：

```
src/reviewer/crew_reviewer.py
```

必须实现：

```
def review_change(task_text: str, quality_result: dict) -> dict:
    ...
```

使用 CrewAI 的 Agent + Task + Crew。

Reviewer 职责：

```
审查 git diff
判断是否解决原始任务
判断是否过度修改
判断是否有明显 bug
判断是否有安全风险
判断是否应该返工
输出返工指令
```

返回格式必须尽量结构化：

```
{
  "passed": true,
  "score": 90,
  "blocking_issues": [],
  "non_blocking_issues": [],
  "retry_instruction": "",
  "raw": "原始模型输出"
}
```

第一版允许模型输出不完全 JSON。实现时要做容错：

```
1. 优先 json.loads
2. 如果解析失败，保留 raw
3. 如果 raw 中明显包含 passed true，则 passed=true
4. 否则 passed=false
```

Reviewer 的 Prompt 必须要求：

```
只输出 JSON，不要 Markdown
```

但代码要能处理模型不听话的情况。

------

## 8.9 主流程编排器

文件：

```
src/orchestration/flow_runner.py
```

必须实现：

```
def run_dev_task(
    project_id: str,
    task_text: str,
    max_iterations: int | None = None
) -> dict:
    ...
```

主流程：

```
1. 读取项目配置
2. 初始化 OpenCodeClient
3. 调 health()
4. 调 current_path()
5. 调 vcs()
6. 创建 session
7. for i in 1..max_iterations:
      a. 构造 initial_prompt 或 retry_prompt
      b. 发送给 OpenCode
      c. 获取 OpenCode diff
      d. 执行 quality_gate
      e. 执行 reviewer
      f. 如果 quality_gate passed 且 reviewer passed，结束成功
      g. 否则进入下一轮
8. 超过最大轮次仍失败，输出失败报告
9. 写入 reports/
10. 返回结果
```

最终返回：

```
{
  "project_id": "demo-project",
  "task": "...",
  "session_id": "...",
  "passed": true,
  "iterations_used": 2,
  "max_iterations": 3,
  "quality": {},
  "review": {},
  "report_json": "reports/xxx.json",
  "report_md": "reports/xxx.md"
}
```

------

## 8.10 报告输出模块

文件：

```
src/orchestration/report_writer.py
```

必须实现：

```
def write_json_report(report: dict) -> str: ...
def write_markdown_report(report: dict) -> str: ...
```

报告文件命名：

```
reports/report-YYYYMMDD-HHMMSS.json
reports/report-YYYYMMDD-HHMMSS.md
```

Markdown 报告必须包含：

```
任务名称
项目 ID
OpenCode session ID
是否成功
使用轮次
修改文件
测试结果
lint 结果
文件策略结果
危险模式结果
Reviewer 审查结果
失败原因
下一步建议
```

------

## 8.11 CLI 入口

文件：

```
src/cli.py
```

要求支持：

```
python -m src.cli --project demo-project --task "请在 README.md 中新增 AI POC 说明"
```

也支持从文件读取任务：

```
python -m src.cli --project demo-project --task-file task.txt
```

参数：

```
--project        项目 ID
--task           任务文本
--task-file      任务文件
--max-iterations 最大返工轮次
```

必须打印：

```
OpenCode health
当前项目路径
session_id
每轮执行状态
质量门禁结果
Reviewer 结果
最终报告路径
```

------

## 8.12 可选 FastAPI 入口

文件：

```
src/api/app.py
```

第一版可实现简单 API：

```
GET  /health
POST /tasks/run
```

`POST /tasks/run` 请求：

```
{
  "project_id": "demo-project",
  "task": "请修复登录模块空指针问题",
  "max_iterations": 3
}
```

返回：

```
{
  "passed": true,
  "report_json": "...",
  "report_md": "..."
}
```

注意：第一版可以同步执行，不需要后台队列。

------

# 九、git worktree 支持

第一版可以默认关闭，但代码要预留。

文件：

```
src/workspace/worktree_manager.py
```

实现：

```
def create_worktree(repo_path: str, worktree_base: str, branch_name: str) -> str:
    ...

def remove_worktree(worktree_path: str) -> None:
    ...
```

后续模式：

```
原始项目：
D:/projects/demo-project

AI 工作区：
D:/ai-worktrees/demo-project/task-20260501-001
```

命令：

```
git worktree add D:/ai-worktrees/demo-project/task-20260501-001 -b ai/task-20260501-001
```

第一版可以不自动启动新的 OpenCode 端口。
 但文档和代码结构要为后续支持多 OpenCode 实例预留。

------

# 十、安全限制

必须遵守：

```
1. 不允许自动执行 rm -rf、del /s、格式化磁盘等危险命令
2. 不允许自动修改 .env、密钥、生产部署配置
3. 不允许删除测试来让测试通过
4. 不允许跳过测试来伪造成功
5. 不允许大范围重构，除非用户任务明确要求
6. 不允许把失败报告写成成功
7. 质量门禁失败时必须标记 passed=false
8. 最多返工 max_iterations 轮，不能无限循环
```

------

# 十一、开发任务拆解

请按以下任务顺序实现。

## Task 1：创建项目骨架

完成：

```
requirements.txt
.env.example
README.md
config/projects.yaml
src/ 目录结构
reports/ 目录
logs/ 目录
```

验收：

```
python -m src.cli --help
```

能正常显示帮助。

------

## Task 2：实现配置读取

文件：

```
src/config_loader.py
```

实现：

```
def load_projects_config(path: str = "config/projects.yaml") -> dict: ...
def get_project_config(project_id: str) -> dict: ...
```

验收：

```
python -c "from src.config_loader import get_project_config; print(get_project_config('demo-project'))"
```

------

## Task 3：实现 OpenCode Client

文件：

```
src/opencode/client.py
```

验收：

```
python -m src.cli --project demo-project --check-opencode
```

输出：

```
health ok
path ok
vcs ok
agents ok
```

如果 `--check-opencode` 参数实现成本高，也可以单独写一个临时测试命令。

------

## Task 4：实现质量门禁基础模块

文件：

```
src/quality/*
```

必须完成：

```
command_runner
git_checker
file_policy
pattern_checker
quality_gate
```

验收：

```
pytest tests/
```

至少测试：

```
allowed_paths 判断
denied_paths 判断
bad_patterns 判断
extract_changed_files 判断
```

------

## Task 5：实现 Prompt Builder

文件：

```
src/orchestration/prompt_builder.py
```

验收：

```
python -c "from src.orchestration.prompt_builder import build_initial_prompt; print(build_initial_prompt('测试任务', {'allowed_write_paths':['README.md'], 'denied_paths':['.env'], 'test_command':'npm test'}))"
```

输出必须包含：

```
任务目标
允许修改
禁止修改
测试命令
不要删除测试
```

------

## Task 6：实现 Reviewer Agent

文件：

```
src/reviewer/crew_reviewer.py
```

验收：

```
传入一个假的 quality_result，能够返回 dict
即使模型输出不是合法 JSON，也不能导致程序崩溃
```

------

## Task 7：实现主流程 flow_runner

文件：

```
src/orchestration/flow_runner.py
```

验收任务：

```
让 OpenCode 修改 README.md
然后获取 diff
然后运行质量门禁
然后输出报告
```

------

## Task 8：实现 CLI

文件：

```
src/cli.py
```

验收命令：

```
python -m src.cli --project demo-project --task "请在 README.md 中新增一段 AI 自动开发 POC 说明，只允许修改 README.md"
```

预期：

```
创建 session 成功
OpenCode 执行成功
检测到 README.md 修改
质量门禁执行完成
生成 reports/report-xxx.json
生成 reports/report-xxx.md
```

------

## Task 9：实现失败返工

制造一个测试失败场景，验证：

```
第一轮失败
生成 retry prompt
第二轮继续发给同一个 session
最多 3 轮停止
```

验收：

```
程序不能无限循环
最终报告必须说明每轮失败原因
```

------

## Task 10：实现 FastAPI 可选入口

文件：

```
src/api/app.py
```

启动：

```
uvicorn src.api.app:app --host 127.0.0.1 --port 7001
```

测试：

```
curl -X POST http://127.0.0.1:7001/tasks/run \
  -H "Content-Type: application/json" \
  -d '{"project_id":"demo-project","task":"请在 README.md 中新增 AI POC 说明","max_iterations":3}'
```

------

# 十二、README.md 内容要求

README 必须说明：

```
1. 项目用途
2. 前置条件
3. 如何启动 OpenCode 4096
4. 如何配置 projects.yaml
5. 如何运行 CLI
6. 如何查看报告
7. 常见问题
```

其中必须包含 OpenCode 启动示例：

Windows PowerShell：

```
cd D:\projects\demo-project

$env:OPENCODE_SERVER_USERNAME="opencode"
$env:OPENCODE_SERVER_PASSWORD="123456"

opencode web --hostname 127.0.0.1 --port 4096
```

Linux：

```
cd /data1/MyWorkSpace/projects/demo-project

export OPENCODE_SERVER_USERNAME=opencode
export OPENCODE_SERVER_PASSWORD=123456

opencode web --hostname 127.0.0.1 --port 4096
```

------

# 十三、最终验收清单

完成后必须逐项自检：

```
[ ] pip install -r requirements.txt 成功
[ ] python -m src.cli --help 成功
[ ] 能读取 config/projects.yaml
[ ] 能连接 OpenCode /global/health
[ ] 能获取 OpenCode /path
[ ] 能获取 OpenCode /vcs
[ ] 能创建 OpenCode session
[ ] 能发送 message 给 build agent
[ ] 能获取 session diff
[ ] 能运行 git status / git diff
[ ] 能运行 test_command
[ ] 能运行 lint_command
[ ] 能检查 allowed_write_paths
[ ] 能检查 denied_paths
[ ] 能检查危险模式
[ ] 能调用 Reviewer Agent
[ ] 能失败返工
[ ] 能最多 3 轮停止
[ ] 能输出 JSON 报告
[ ] 能输出 Markdown 报告
[ ] README 写清楚使用方式
```

------

# 十四、第一版成功案例

运行命令：

```
python -m src.cli --project demo-project --task "请在 README.md 中新增一段 AI 自动开发 POC 说明，只允许修改 README.md"
```

成功后报告应类似：

```
{
  "project_id": "demo-project",
  "task": "请在 README.md 中新增一段 AI 自动开发 POC 说明，只允许修改 README.md",
  "session_id": "ses_xxx",
  "passed": true,
  "iterations_used": 1,
  "changed_files": [
    "README.md"
  ],
  "quality": {
    "passed": true,
    "test": {
      "passed": true
    },
    "file_policy": {
      "passed": true
    },
    "bad_patterns": {
      "passed": true
    }
  },
  "review": {
    "passed": true
  }
}
```

------

# 十五、第二个验收案例：真实 Bug

运行：

```
python -m src.cli --project demo-project --task "请修复登录模块在 user 为 null 时抛异常的问题，要求补充测试，并确保测试通过"
```

期望：

```
1. OpenCode 定位登录模块
2. 修改代码
3. 补充或修改测试
4. 运行测试
5. 测试失败则返工
6. 最多 3 轮
7. 最终报告说明是否成功
```

------

# 十六、实现注意事项

请特别注意：

```
1. 不要把所有代码写在 main.py
2. 每个模块职责清晰
3. 所有外部调用都要有 timeout
4. 所有失败都要写入最终报告
5. 不要因为 Reviewer JSON 解析失败就中断流程
6. 不要因为测试失败就程序崩溃
7. 失败是一种正常结果，要输出报告
8. 不要无限重试
9. 不要默认任务成功
10. 不要覆盖用户项目文件，所有修改都由 OpenCode 完成
```

------

# 十七、交付物

最终需要交付：

```
完整 Python 项目
README.md
requirements.txt
config/projects.yaml 示例
.env.example
CLI 可运行
可选 FastAPI 可运行
tests 单元测试
reports 示例报告
```

