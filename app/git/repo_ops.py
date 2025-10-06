from __future__ import annotations

import shutil
from pathlib import Path

from git import GitCommandError, Repo
from github import GithubException

from app.core.config import get_settings
from app.core.logging import get_logger

from .github_client import get_github_client

logger = get_logger(__name__)

REPOS_DIR = Path("./data/repos")


def clone_or_update_repo(owner: str, repo_name: str, branch: str, *, force: bool = False) -> Path:
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = REPOS_DIR / f"{owner}-{repo_name}"
    if target_path.exists() and force:
        logger.info("removing_repo", path=str(target_path))
        shutil.rmtree(target_path)
    if target_path.exists():
        repo = Repo(target_path)
        repo.remotes.origin.fetch()
    else:
        url = f"https://github.com/{owner}/{repo_name}.git"
        repo = Repo.clone_from(url, target_path)

    stashed = False
    if repo.is_dirty(untracked_files=True):
        logger.info("stashing_changes_before_checkout", path=str(target_path))
        repo.git.stash("save", "autodev-stash-before-checkout")
        stashed = True

    remote = repo.remotes.origin
    remote.fetch()

    remote_refs = {
        getattr(ref, "remote_head", None): ref
        for ref in remote.refs
        if getattr(ref, "remote_head", None)
    }

    default_branch = None
    try:
        remote_info = repo.git.remote("show", "origin")
        for line in remote_info.splitlines():
            line = line.strip()
            if line.startswith("HEAD branch:"):
                default_branch = line.split(":", 1)[1].strip()
                if default_branch == "(unknown)":
                    default_branch = None
                break
    except GitCommandError:
        default_branch = None

    candidate_branches = []
    if branch:
        candidate_branches.append(branch)
    for fallback in ("main", "master"):
        if fallback not in candidate_branches:
            candidate_branches.append(fallback)
    if default_branch and default_branch not in candidate_branches:
        candidate_branches.append(default_branch)

    resolved_branch = None
    for candidate in candidate_branches:
        if candidate in remote_refs:
            resolved_branch = candidate
            break
        if candidate in repo.heads:
            resolved_branch = candidate
            break

    if resolved_branch is None:
        available = sorted(remote_refs.keys())
        logger.error(
            "branch_not_found",
            branch=branch,
            available_branches=available,
        )
        raise ValueError(f"Unable to find a suitable branch to checkout from candidates: {candidate_branches}")

    try:
        if resolved_branch in repo.heads:
            repo.git.checkout(resolved_branch)
        elif resolved_branch in remote_refs:
            repo.git.checkout("-B", resolved_branch, remote_refs[resolved_branch].name)
        else:
            repo.git.checkout(resolved_branch)
        if resolved_branch in remote_refs:
            repo.git.pull("--ff-only", "origin", resolved_branch)
    except GitCommandError as exc:
        raise ValueError(f"Unable to checkout branch '{resolved_branch}'") from exc

    logger.info(
        "checked_out_branch",
        requested_branch=branch,
        resolved_branch=resolved_branch,
        path=str(target_path),
    )
    if stashed:
        logger.info("stash_created", message="autodev-stash-before-checkout", path=str(target_path))
    return target_path


def create_branch(repo: Repo, branch: str, base: str) -> None:
    logger.info("create_branch", branch=branch, base=base)
    if branch in repo.heads:
        repo.git.checkout(branch)
    else:
        repo.git.checkout(base)
        repo.git.checkout('-b', branch)


def commit_all(repo: Repo, message: str) -> str:
    repo.git.add(A=True)
    if not repo.is_dirty():
        logger.info("nothing_to_commit")
        return ""
    commit = repo.index.commit(message)
    logger.info("commit_created", commit=str(commit.hexsha))
    return str(commit.hexsha)


def push_branch(repo: Repo, branch: str) -> None:
    logger.info("push_branch", branch=branch)
    repo.remotes.origin.push(refspec=f"HEAD:{branch}")


def open_pull_request(job_id: str, title: str, body: str, head: str, base: str) -> str:
    settings = get_settings()
    github = get_github_client()
    repository = github.get_repo(f"{settings.github_owner}/{settings.github_repo}")
    try:
        pr = repository.create_pull(title=title, body=body, head=head, base=base)
        logger.info("pr_opened", pr_url=pr.html_url)
        return pr.html_url
    except GithubException as exc:
        logger.error("pr_failed", error=str(exc))
        raise


def merge_strategy() -> str:
    settings = get_settings()
    return settings.merge_conflict_behavior
