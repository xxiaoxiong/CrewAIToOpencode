from __future__ import annotations

import json


def _list_lines(values: list[str] | None) -> str:
    if not values:
        return "- 不限制"
    return "\n".join(f"- {value}" for value in values)


def build_initial_prompt(task_text: str, project_config: dict) -> str:
    allowed_write_paths = _list_lines(project_config.get("allowed_write_paths", []))
    denied_paths = _list_lines(project_config.get("denied_paths", []))
    test_command = project_config.get("test_command", "")

    return f"""你是 OpenCode 编程执行 Agent。请在当前项目中完成以下任务。

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
6. 不允许通过 mock、硬编码、跳过测试、注释掉逻辑来伪造成成功。
7. 修改完成后，请运行项目测试命令：
{test_command or "未配置测试命令"}
8. 如果测试失败，请根据失败日志继续修复。
9. 最终说明修改了哪些文件、为什么修改、测试结果如何。

【禁止行为】
- 不要修改 `.env`、密钥、生产部署配置或锁文件。
- 不要引入 TODO、FIXME、HACK、debugger、console.log 或敏感字段。
- 不要把失败说成成功。

【输出要求】
请在执行结束时简要说明变更文件、测试命令和结果。

请开始执行。"""


def build_retry_prompt(
    task_text: str,
    quality_result: dict,
    review_result: dict,
    iteration: int,
) -> str:
    test = quality_result.get("test", {})
    lint = quality_result.get("lint", {})
    file_policy = quality_result.get("file_policy", {})
    bad_patterns = quality_result.get("bad_patterns", {})
    blocking = review_result.get("blocking_issues", [])

    failure_summary = {
        "quality_passed": quality_result.get("passed"),
        "changed_files": quality_result.get("changed_files", []),
        "test_passed": test.get("passed"),
        "lint_passed": lint.get("passed"),
        "file_policy": file_policy,
        "bad_patterns": bad_patterns,
        "review_passed": review_result.get("passed"),
        "review_blocking_issues": blocking,
        "review_retry_instruction": review_result.get("retry_instruction", ""),
    }

    return f"""你是 OpenCode 编程执行 Agent。上一轮没有通过验收，请只修复失败点。

【原始任务】
{task_text}

【当前返工轮次】
第 {iteration} 轮

【质量门禁失败原因】
{json.dumps(failure_summary, ensure_ascii=False, indent=2)}

【测试日志】
命令：{test.get("cmd", "")}
stdout:
{test.get("stdout", "")[-4000:]}
stderr:
{test.get("stderr", "")[-4000:]}

【lint 日志】
命令：{lint.get("cmd", "")}
stdout:
{lint.get("stdout", "")[-4000:]}
stderr:
{lint.get("stderr", "")[-4000:]}

【Reviewer 阻塞问题】
{json.dumps(blocking, ensure_ascii=False, indent=2)}

【返工要求】
1. 只修复上述失败点，不要扩展新功能。
2. 不要修改允许范围之外的文件。
3. 不要跳过、删除或弱化测试。
4. 修复后重新运行测试命令，并说明结果。

请继续在同一个 session 中修复。"""
