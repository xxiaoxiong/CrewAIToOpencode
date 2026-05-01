from __future__ import annotations


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip().strip("/")


def _matches(path: str, rule: str) -> bool:
    normalized_path = _norm(path)
    normalized_rule = rule.replace("\\", "/").strip()
    if not normalized_rule:
        return False

    is_dir_rule = normalized_rule.endswith("/")
    normalized_rule = normalized_rule.strip("/")
    if is_dir_rule:
        return normalized_path == normalized_rule or normalized_path.startswith(f"{normalized_rule}/")
    return normalized_path == normalized_rule


def check_file_policy(
    changed_files: list[str],
    allowed_paths: list[str],
    denied_paths: list[str],
) -> dict:
    violations: list[dict] = []

    for changed in changed_files:
        for denied in denied_paths or []:
            if _matches(changed, denied):
                violations.append({"file": changed, "rule": denied, "type": "denied"})

        if allowed_paths:
            if not any(_matches(changed, allowed) for allowed in allowed_paths):
                violations.append({"file": changed, "rule": allowed_paths, "type": "not_allowed"})

    return {"passed": not violations, "violations": violations}
