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


def _get_default_branch(repo: Repo) -> str:
    """Auto-detect the default branch of a repository."""
    try:
        # Try to get the default branch from remote HEAD
        remote_refs = repo.remotes.origin.refs
        for ref in remote_refs:
            if ref.name == "origin/HEAD":
                # Extract branch name from origin/HEAD -> origin/main
                default = ref.reference.name.replace("origin/", "")
                logger.info("detected_default_branch", branch=default)
                return default
    except Exception as exc:
        logger.warning("default_branch_detection_failed", error=str(exc))

    # Fallback: check which of main/master exists
    try:
        repo.git.rev_parse("--verify", "origin/main")
        return "main"
    except GitCommandError:
        pass

    try:
        repo.git.rev_parse("--verify", "origin/master")
        return "master"
    except GitCommandError:
        pass

    # Last resort: return main as default
    return "main"


def clone_or_update_repo(owner: str, repo_name: str, branch: str, *, force: bool = False) -> tuple[Path, str]:
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = REPOS_DIR / f"{owner}-{repo_name}"

    # Clean branch name: remove "origin " or "origin/" prefix if present
    cleaned_branch = branch.strip()
    if cleaned_branch.startswith("origin "):
        cleaned_branch = cleaned_branch.replace("origin ", "", 1).strip()
    elif cleaned_branch.startswith("origin/"):
        cleaned_branch = cleaned_branch.replace("origin/", "", 1).strip()

    logger.info("clone_or_update_repo", owner=owner, repo=repo_name, branch=cleaned_branch)

    if target_path.exists() and force:
        logger.info("removing_repo", path=str(target_path))
        shutil.rmtree(target_path)

    # Get GitHub token for authenticated operations
    settings = get_settings()
    token = settings.github_token

    if target_path.exists():
        repo = Repo(target_path)
        # Update remote URL with token for authenticated fetch
        if token:
            auth_url = f"https://{token}@github.com/{owner}/{repo_name}.git"
            repo.remotes.origin.set_url(auth_url)
        repo.remotes.origin.fetch()
    else:
        # Clone with token in URL for authentication
        if token:
            url = f"https://{token}@github.com/{owner}/{repo_name}.git"
        else:
            url = f"https://github.com/{owner}/{repo_name}.git"
        repo = Repo.clone_from(url, target_path)

    # Try to checkout the requested branch
    branch_variants = [
        cleaned_branch,
        f"origin/{cleaned_branch}",
    ]

    checked_out = False
    actual_branch = cleaned_branch
    for variant in branch_variants:
        try:
            repo.git.checkout(variant)
            if variant.startswith("origin/"):
                # If we checked out a remote branch, create a local tracking branch
                local_name = variant.replace("origin/", "")
                try:
                    repo.git.checkout("-b", local_name)
                    logger.info("created_local_branch", branch=local_name, tracking=variant)
                except GitCommandError:
                    # Branch already exists locally
                    pass
                actual_branch = local_name
            else:
                actual_branch = variant
            checked_out = True
            logger.info("checked_out_branch", branch=variant)
            break
        except GitCommandError:
            continue

    # If requested branch doesn't exist, use default branch
    if not checked_out:
        default_branch = _get_default_branch(repo)
        logger.warning("branch_not_found_using_default", requested=cleaned_branch, default=default_branch)
        try:
            repo.git.checkout(default_branch)
            actual_branch = default_branch
        except GitCommandError:
            # Try with origin/ prefix
            repo.git.checkout(f"origin/{default_branch}")
            repo.git.checkout("-b", default_branch)
            actual_branch = default_branch

    return target_path, actual_branch


def create_branch(repo: Repo, branch: str, base: str) -> None:
    logger.info("create_branch", branch=branch, base=base)
    if branch in repo.heads:
        repo.git.checkout(branch)
    else:
        # Ensure base branch exists locally
        try:
            repo.git.checkout(base)
        except GitCommandError:
            # Base might not exist locally, try to get it from remote
            logger.warning("base_branch_not_local", base=base)
            try:
                repo.git.checkout(f"origin/{base}")
                repo.git.checkout('-b', base)
            except GitCommandError:
                # Last resort: use current HEAD
                logger.warning("base_branch_not_found_using_current", base=base)
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

    # Ensure remote URL has token for authenticated push
    settings = get_settings()
    token = settings.github_token
    if token:
        # Extract owner/repo from current remote URL
        current_url = repo.remotes.origin.url
        if "github.com" in current_url:
            # Parse out owner/repo from URL
            if current_url.startswith("https://"):
                # Extract path after github.com/
                parts = current_url.replace("https://", "").split("@")[-1].split("github.com/")
                if len(parts) > 1:
                    repo_path = parts[1].replace(".git", "")
                    auth_url = f"https://{token}@github.com/{repo_path}.git"
                    repo.remotes.origin.set_url(auth_url)
                    logger.info("updated_remote_url_for_push")

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
