"""
actions/git_sentinel.py — DevOps Commander & Git Forge Sentinel for Ultron AI.
Autonomous version control and repository intelligence:
  - Real-time Git status, branch tracking, and ahead/behind telemetry.
  - Diff summarization across working tree and staging area.
  - Autonomous AI-crafted Conventional Commits (feat, fix, refactor) with auto-stage.
  - Safe branch switching, creating, stashing, pulling, and pushing.
  - Interactive commit log inspection.
Auto-discovered by core/action_loader.py.
"""
from __future__ import annotations

import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Optional

_OS = platform.system()
_WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if _OS == "Windows" else {}
_BASE_DIR = Path(__file__).resolve().parent.parent


def _run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Execute git CLI command safely and return (returncode, stdout, stderr)."""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            **_WIN_HIDE
        )
        return res.returncode, (res.stdout or "").strip(), (res.stderr or "").strip()
    except Exception as e:
        return -1, "", str(e)


def _resolve_repo(path_str: str | None) -> Path:
    """Resolve target repository directory or fall back to base project."""
    if path_str:
        candidate = Path(path_str).expanduser().resolve()
        if candidate.exists() and candidate.is_dir():
            return candidate
    return _BASE_DIR.resolve()


def _is_git_repo(repo_dir: Path) -> bool:
    """Check if target directory is inside a Git repository."""
    code, out, _ = _run_git(["rev-parse", "--is-inside-work-tree"], repo_dir)
    return code == 0 and out.lower() == "true"


def git_status(repo_dir: Path) -> str:
    """Retrieve detailed Git status and branch telemetry."""
    if not _is_git_repo(repo_dir):
        return f"Directory '{repo_dir.name}' is not a Git repository."

    code, out, err = _run_git(["status", "--porcelain=v1", "-b"], repo_dir)
    if code != 0:
        return f"Git status failed: {err}"

    lines = out.splitlines()
    if not lines:
        return f"Repository '{repo_dir.name}' is clean. Working tree matches HEAD."

    header = lines[0]  # ## branch...origin/branch [ahead 1]
    branch_match = re.search(r"^##\s+([^\s\.]+)", header)
    current_branch = branch_match.group(1) if branch_match else "HEAD (detached)"

    ahead_match = re.search(r"\[ahead\s+(\d+)\]", header)
    behind_match = re.search(r"\[behind\s+(\d+)\]", header)
    sync_status = []
    if ahead_match:
        sync_status.append(f"{ahead_match.group(1)} ahead")
    if behind_match:
        sync_status.append(f"{behind_match.group(1)} behind")
    sync_text = f" ({', '.join(sync_status)})" if sync_status else " (Up to date)"

    staged = []
    modified = []
    untracked = []

    for line in lines[1:]:
        if len(line) < 3:
            continue
        idx_stat = line[0]
        work_stat = line[1]
        file_path = line[3:].strip()

        if idx_stat in ("M", "A", "D", "R", "C"):
            staged.append(file_path)
        if work_stat in ("M", "D"):
            modified.append(file_path)
        if idx_stat == "?" and work_stat == "?":
            untracked.append(file_path)

    report = [
        f"🐙 GIT SENTINEL — {repo_dir.name}",
        f"• Branch:    {current_branch}{sync_text}",
        f"• Staged:    {len(staged)} files",
        f"• Modified:  {len(modified)} files",
        f"• Untracked: {len(untracked)} files",
        "─" * 45,
    ]

    if staged:
        report.append("Staged for commit:")
        for f in staged[:5]:
            report.append(f"  + {f}")
        if len(staged) > 5:
            report.append(f"  ... (+{len(staged)-5} more)")

    if modified:
        report.append("Changes not staged:")
        for f in modified[:5]:
            report.append(f"  • {f}")
        if len(modified) > 5:
            report.append(f"  ... (+{len(modified)-5} more)")

    if untracked:
        report.append("Untracked files:")
        for f in untracked[:5]:
            report.append(f"  ? {f}")
        if len(untracked) > 5:
            report.append(f"  ... (+{len(untracked)-5} more)")

    if not (staged or modified or untracked):
        report.append("Working tree clean. Nothing to commit.")

    return "\n".join(report)


def git_diff_summary(repo_dir: Path) -> str:
    """Returns stat summary of working tree changes."""
    if not _is_git_repo(repo_dir):
        return f"Directory '{repo_dir.name}' is not a Git repository."

    code, out, _ = _run_git(["diff", "--stat"], repo_dir)
    code_c, out_c, _ = _run_git(["diff", "--cached", "--stat"], repo_dir)

    lines = [f"📊 DIFF TELEMETRY — {repo_dir.name}", "─" * 45]
    if out:
        lines.append("Unstaged Changes:")
        lines.append(out)
    if out_c:
        lines.append("\nStaged Changes:")
        lines.append(out_c)
    if not out and not out_c:
        lines.append("No active diffs detected in working tree or index.")
    return "\n".join(lines)


def _generate_commit_message(repo_dir: Path) -> str:
    """Heuristically formulate conventional commit message from changed files."""
    code, out, _ = _run_git(["status", "--porcelain=v1"], repo_dir)
    if not out:
        return "chore: update repository files"

    files = [l[3:].strip() for l in out.splitlines() if len(l) > 3]
    if not files:
        return "chore: workstation maintenance updates"

    # Inspect file types / areas
    first = files[0].lower()
    if any(f.endswith(".py") for f in files):
        if "action" in first or any("action" in f.lower() for f in files):
            action_names = [Path(f).stem for f in files if "action" in f.lower()][:2]
            return f"feat(actions): enhance {', '.join(action_names)} capabilities"
        if "core" in first:
            return "refactor(core): optimize core architecture and pipelines"
        return f"feat: implement updates in {Path(files[0]).stem}"
    elif any(f.endswith((".md", ".txt")) for f in files):
        return "docs: update system documentation and specifications"
    elif any(f.endswith((".json", ".yaml", ".yml", ".toml")) for f in files):
        return "chore(config): adjust configuration and profile settings"
    return f"feat: update {len(files)} modules in {Path(files[0]).name}"


def git_commit(repo_dir: Path, message: str | None = None, push: bool = False) -> str:
    """Stages all changes, creates a commit, and optionally pushes."""
    if not _is_git_repo(repo_dir):
        return f"Directory '{repo_dir.name}' is not a Git repository."

    # Stage all changes
    code_add, _, err_add = _run_git(["add", "-A"], repo_dir)
    if code_add != 0:
        return f"Git add failed: {err_add}"

    # Generate commit message if empty
    commit_msg = (message or "").strip()
    if not commit_msg:
        commit_msg = _generate_commit_message(repo_dir)

    # Commit
    code_c, out_c, err_c = _run_git(["commit", "-m", commit_msg], repo_dir)
    if code_c != 0:
        if "nothing to commit" in (out_c + err_c):
            return "Working tree is clean. Nothing to commit."
        return f"Git commit failed: {err_c or out_c}"

    # Extract commit hash
    match = re.search(r"\[([^\s\]]+)\s+([0-9a-fA-F]+)\]", out_c)
    hash_str = match.group(2) if match else "HEAD"

    lines = [
        "✅ GIT COMMIT EXECUTED",
        f"• Repository: {repo_dir.name}",
        f"• Commit:     {hash_str}",
        f"• Directive:  \"{commit_msg}\"",
    ]

    if push:
        code_p, out_p, err_p = _run_git(["push"], repo_dir)
        if code_p == 0:
            lines.append("• Remote:     Pushed to origin successfully.")
        else:
            lines.append(f"• Remote:     Push error: {err_p or out_p}")

    return "\n".join(lines)


def git_push_pull(repo_dir: Path, action: str = "push") -> str:
    """Execute git push or pull."""
    if not _is_git_repo(repo_dir):
        return f"Directory '{repo_dir.name}' is not a Git repository."

    code, out, err = _run_git([action], repo_dir)
    if code == 0:
        return f"Git {action} completed successfully for '{repo_dir.name}':\n{out or 'Up to date.'}"
    return f"Git {action} failed: {err or out}"


def git_log_history(repo_dir: Path, count: int = 5) -> str:
    """View recent commit timeline."""
    if not _is_git_repo(repo_dir):
        return f"Directory '{repo_dir.name}' is not a Git repository."

    code, out, err = _run_git(["log", f"-n{count}", "--pretty=format:%h | %cr | %s (%an)"], repo_dir)
    if code != 0:
        return f"Git log failed: {err}"

    lines = [f"📜 RECENT COMMIT TIMELINE — {repo_dir.name}", "─" * 45]
    for l in out.splitlines():
        lines.append(f"• {l}")
    return "\n".join(lines)


def git_branch(repo_dir: Path, branch_name: str | None = None, create: bool = False) -> str:
    """List branches or switch/create branch."""
    if not _is_git_repo(repo_dir):
        return f"Directory '{repo_dir.name}' is not a Git repository."

    if not branch_name:
        code, out, _ = _run_git(["branch", "-a"], repo_dir)
        return f"Branches in '{repo_dir.name}':\n{out}"

    args = ["checkout", "-b", branch_name] if create else ["checkout", branch_name]
    code, out, err = _run_git(args, repo_dir)
    if code == 0:
        return f"Switched to branch '{branch_name}' in {repo_dir.name}."
    return f"Branch operation failed: {err or out}"


def git_sentinel(parameters: dict, player=None, **kwargs) -> str:
    """Main handler for git_sentinel tool."""
    action = (parameters.get("action") or "status").lower().strip()
    repo_path = _resolve_repo(parameters.get("repo_path"))
    message = parameters.get("message")
    branch = parameters.get("branch")

    if player:
        try:
            player.write_log(f"[GitSentinel] {action} in {repo_path.name}")
        except Exception:
            pass

    try:
        if action in ("status", "check", "inspect"):
            return git_status(repo_path)

        elif action in ("diff", "changes", "summary"):
            return git_diff_summary(repo_path)

        elif action in ("commit", "auto_commit", "save"):
            push_after = bool(parameters.get("push", False))
            return git_commit(repo_path, message=message, push=push_after)

        elif action in ("push",):
            return git_push_pull(repo_path, action="push")

        elif action in ("pull", "sync"):
            return git_push_pull(repo_path, action="pull")

        elif action in ("log", "history", "timeline"):
            count = int(parameters.get("count", 5))
            return git_log_history(repo_path, count=count)

        elif action in ("branch", "checkout"):
            create = bool(parameters.get("create", False))
            return git_branch(repo_path, branch_name=branch, create=create)

        elif action in ("stash",):
            sub = "pop" if parameters.get("pop") else "save"
            code, out, err = _run_git(["stash", sub], repo_path)
            return f"Git stash {sub}: {out or err}"

        else:
            return f"Unknown git action '{action}'. Available: status, diff, commit, push, pull, log, branch, stash."
    except Exception as e:
        return f"Git Sentinel error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "git_sentinel",
    "description": (
        "DevOps Commander & Git Forge Sentinel. Inspects repository status, branches, ahead/behind telemetry, "
        "diff summaries, creates AI-formatted conventional commits, pushes, pulls, creates/switches branches, "
        "and inspects commit history. Use whenever user asks about git status, uncommitted changes, "
        "committing code, pushing/pulling repos, or checking git log."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "status (check repo status) | diff (view changes) | commit (stage & commit with AI message) | push (push to origin) | pull (sync remote) | log (view recent commits) | branch (list or switch branch) | stash (stash or pop)"
            },
            "message": {
                "type": "STRING",
                "description": "Optional commit message (leave empty for autonomous conventional commit generation)"
            },
            "repo_path": {
                "type": "STRING",
                "description": "Path to target git repository folder. Defaults to current workspace."
            },
            "branch": {
                "type": "STRING",
                "description": "Branch name for branch/checkout action"
            },
            "push": {
                "type": "BOOLEAN",
                "description": "For action='commit': whether to immediately push to origin after committing. Default: false"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": git_sentinel,
}
