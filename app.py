import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

import gradio as gr
import requests
from dotenv import dotenv_values, load_dotenv, set_key

load_dotenv()

API_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3
UI_DEFAULTS_PATH = Path("ui_defaults.json")
ENV_PATH = Path(".env")
TERMINAL_STATUSES = {"succeeded", "failed", "timeout", "canceled", "cancelled"}
DEFAULT_SETTINGS = {
    "API_BASE_URL": "http://localhost:3000",
    "branch_base": "main",
    "modelCTO": "gpt-4.1-mini",
    "modelCoder": "gpt-4.1",
    "budgetUsd": 2.5,
    "maxRequests": 120,
    "maxMinutes": 45,
}
REQUEST_SESSION = requests.Session()


def load_ui_defaults() -> Dict[str, Any]:
    if UI_DEFAULTS_PATH.exists():
        try:
            return json.loads(UI_DEFAULTS_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def persist_ui_defaults(values: Dict[str, Any]) -> None:
    """Persist non-secret UI defaults to a small JSON file."""
    safe_values = {
        "GITHUB_OWNER": values.get("GITHUB_OWNER", ""),
        "GITHUB_REPO": values.get("GITHUB_REPO", ""),
        "branch_base": values.get("branch_base", DEFAULT_SETTINGS["branch_base"]),
        "modelCTO": values.get("modelCTO", DEFAULT_SETTINGS["modelCTO"]),
        "modelCoder": values.get("modelCoder", DEFAULT_SETTINGS["modelCoder"]),
        "budgetUsd": values.get("budgetUsd", DEFAULT_SETTINGS["budgetUsd"]),
        "maxRequests": values.get("maxRequests", DEFAULT_SETTINGS["maxRequests"]),
        "maxMinutes": values.get("maxMinutes", DEFAULT_SETTINGS["maxMinutes"]),
    }
    UI_DEFAULTS_PATH.write_text(json.dumps(safe_values, indent=2, ensure_ascii=False))


def load_initial_values() -> Dict[str, Any]:
    """Combine baked defaults, stored UI values, and .env entries."""
    env_values = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    ui_values = load_ui_defaults()
    merged: Dict[str, Any] = {}
    merged.update(DEFAULT_SETTINGS)
    merged.update(ui_values)
    merged.update(env_values)
    for key in ("budgetUsd", "maxRequests", "maxMinutes"):
        try:
            value = merged.get(key)
            if value is not None:
                merged[key] = float(value) if key == "budgetUsd" else int(value)
        except (TypeError, ValueError):
            merged[key] = DEFAULT_SETTINGS[key]
    return merged


def ensure_env_file() -> None:
    """Create an empty .env file if it does not exist."""
    if not ENV_PATH.exists():
        ENV_PATH.touch()


def save_env_file(values: Dict[str, Optional[str]]) -> Tuple[bool, str]:
    """Idempotently update .env keys without logging their values."""
    ensure_env_file()
    existing = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    updated_keys: List[str] = []
    for key, value in values.items():
        if value is None:
            value = ""
        value = str(value)
        previous = existing.get(key)
        if previous != value:
            updated_keys.append(key)
            existing[key] = value
        set_key(str(ENV_PATH), key, value, quote_mode="never")
    if updated_keys:
        return True, f"Updated .env keys: {', '.join(updated_keys)}"
    return True, "No changes required for .env"


def request_with_backoff(method: str, url: str, *, retries: int = MAX_RETRIES, **kwargs: Any) -> requests.Response:
    """Perform an HTTP request with exponential backoff on 429 or transport errors."""
    for attempt in range(1, retries + 1):
        try:
            response = REQUEST_SESSION.request(method, url, timeout=API_TIMEOUT_SECONDS, **kwargs)
        except requests.RequestException as exc:
            if attempt >= retries:
                raise exc
            time.sleep(2**attempt)
            continue
        if response.status_code != 429:
            return response
        time.sleep(2**attempt)
    return response


def timestamp_from_event(event: Dict[str, Any]) -> Optional[str]:
    for key in ("timestamp", "ts", "time", "created_at"):
        if key in event and event[key]:
            return str(event[key])
    return None


def event_to_line(event: Any) -> str:
    if isinstance(event, str):
        return event
    if isinstance(event, dict):
        for candidate in ("message", "detail", "status", "text", "description", "summary"):
            if event.get(candidate):
                return str(event[candidate])
        return json.dumps(event, ensure_ascii=False)
    return str(event)


def format_log_line(message: str, event_ts: Optional[str] = None) -> str:
    if event_ts:
        return f"[{event_ts}] {message}"
    return f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] {message}"


def format_metrics(job: Dict[str, Any]) -> str:
    status = job.get("status", "unknown")
    runtime = job.get("runtime_s") or job.get("runtime") or 0
    costs = job.get("costs", {}) or {}
    usd = costs.get("usd")
    tokens = costs.get("tokens")
    requests_count = costs.get("requests") or job.get("requests")
    tokens_text = ""
    if isinstance(tokens, dict):
        parts = []
        if tokens.get("input") is not None:
            parts.append(f"in {tokens['input']}")
        if tokens.get("output") is not None:
            parts.append(f"out {tokens['output']}")
        if tokens.get("total") is not None:
            parts.append(f"total {tokens['total']}")
        if parts:
            tokens_text = " · Tokens " + ", ".join(parts)
    elif tokens is not None:
        tokens_text = f" · Tokens {tokens}"
    usd_text = f" · USD {usd:.2f}" if isinstance(usd, (int, float)) else ""
    requests_text = f" · Requests {requests_count}" if requests_count is not None else ""
    last_action = job.get("last_action") or job.get("current_step") or job.get("description")
    last_action_text = f"\nLast action: {last_action}" if last_action else ""
    pr_lines = format_pr_links(job)
    metrics = f"**Status:** {status} · Runtime {runtime}s{usd_text}{tokens_text}{requests_text}{last_action_text}"
    if pr_lines:
        metrics += f"\n\n{pr_lines}"
    return metrics


def format_pr_links(job: Dict[str, Any]) -> str:
    raw_links: Iterable[Any] = []
    if job.get("pr_urls"):
        raw_links = job["pr_urls"]
    elif job.get("pull_requests"):
        raw_links = job["pull_requests"]
    elif job.get("prs"):
        raw_links = job["prs"]
    elif job.get("pr_url"):
        raw_links = [job["pr_url"]]
    links = [str(item) for item in raw_links if item]
    if not links:
        return ""
    parts = []
    for index, link in enumerate(links):
        if index == len(links) - 1:
            parts.append(f"**[PR {index + 1}]({link})**")
        else:
            parts.append(f"[PR {index + 1}]({link})")
    return "PR Links: " + " · ".join(parts)


def extract_tail_updates(job: Dict[str, Any], tracker: Dict[str, Any]) -> List[str]:
    """Collect only new event/step lines for the live tail view."""
    lines: List[str] = []
    events = job.get("events")
    if isinstance(events, list):
        start = tracker.get("events", 0)
        for event in events[start:]:
            ts = timestamp_from_event(event) if isinstance(event, dict) else None
            lines.append(format_log_line(event_to_line(event), ts))
        tracker["events"] = len(events)
    steps = job.get("steps")
    if isinstance(steps, list):
        start = tracker.get("steps", 0)
        for step in steps[start:]:
            ts = timestamp_from_event(step) if isinstance(step, dict) else None
            lines.append(format_log_line(event_to_line(step), ts))
        tracker["steps"] = len(steps)
    status = job.get("status", "unknown")
    if not lines and tracker.get("status") != status:
        lines.append(format_log_line(f"Status: {status}"))
        tracker["status"] = status
    return lines


def health_check(api_base_url: str) -> Tuple[str, str]:
    """Call the backend health endpoint and format UI feedback."""
    url = api_base_url.rstrip("/") + "/health"
    try:
        response = request_with_backoff("GET", url)
        response.raise_for_status()
    except requests.RequestException as exc:
        message = (
            f"<span style='color:red'>Health check failed:</span> {exc}. "
            "Ensure the backend is running (try scripts/run.ps1)."
        )
        return message, ""
    payload = response.json()
    message = "<span style='color:green'>Health check succeeded.</span>"
    return message, f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"


def on_save_env(
    api_base_url: str,
    openai_api_key: str,
    github_token: str,
    github_owner: str,
    github_repo: str,
    branch_base: str,
    model_cto: str,
    model_coder: str,
    budget_usd: float,
    max_requests: int,
    max_minutes: int,
) -> str:
    env_values = {
        "API_BASE_URL": api_base_url.strip(),
        "OPENAI_API_KEY": openai_api_key.strip(),
        "GITHUB_TOKEN": github_token.strip(),
        "GITHUB_OWNER": github_owner.strip(),
        "GITHUB_REPO": github_repo.strip(),
    }
    try:
        budget_value = float(budget_usd)
    except (TypeError, ValueError):
        budget_value = float(DEFAULT_SETTINGS["budgetUsd"])
    try:
        max_requests_value = int(max_requests)
    except (TypeError, ValueError):
        max_requests_value = int(DEFAULT_SETTINGS["maxRequests"])
    try:
        max_minutes_value = int(max_minutes)
    except (TypeError, ValueError):
        max_minutes_value = int(DEFAULT_SETTINGS["maxMinutes"])
    success, message = save_env_file(env_values)
    persist_ui_defaults(
        {
            "GITHUB_OWNER": github_owner.strip(),
            "GITHUB_REPO": github_repo.strip(),
            "branch_base": branch_base.strip(),
            "modelCTO": model_cto.strip(),
            "modelCoder": model_coder.strip(),
            "budgetUsd": budget_value,
            "maxRequests": max_requests_value,
            "maxMinutes": max_minutes_value,
        }
    )
    return message if success else "Failed to update .env"


def cancel_job(
    api_base_url: str,
    job_state: Optional[Dict[str, Any]],
    current_log: str,
) -> Tuple[str, str, Dict[str, Any], str]:
    if not job_state or not job_state.get("job_id"):
        return current_log, gr.update(), job_state or {}, "No active job to cancel."
    job_id = job_state["job_id"]
    url = api_base_url.rstrip("/") + f"/jobs/{job_id}/cancel"
    try:
        response = request_with_backoff("POST", url)
        response.raise_for_status()
    except requests.RequestException as exc:
        return current_log, gr.update(), job_state, f"Cancel failed: {exc}"
    updated_log = current_log + ("\n" if current_log else "") + format_log_line(f"Cancel requested for job {job_id}")
    job_state = {"job_id": job_id, "active": False}
    return updated_log, gr.update(), job_state, "Cancel request sent."


def run_job(
    api_base_url: str,
    github_owner: str,
    github_repo: str,
    branch_base: str,
    model_cto: str,
    model_coder: str,
    budget_usd: float,
    max_requests: int,
    max_minutes: int,
    dry_run: bool,
    task_text: str,
) -> Generator[Tuple[str, str, Dict[str, Any], str], None, None]:
    """Start a task and stream incremental job updates back to Gradio."""
    try:
        budget_value = float(budget_usd)
    except (TypeError, ValueError):
        budget_value = float(DEFAULT_SETTINGS["budgetUsd"])
    try:
        max_requests_value = int(max_requests)
    except (TypeError, ValueError):
        max_requests_value = int(DEFAULT_SETTINGS["maxRequests"])
    try:
        max_minutes_value = int(max_minutes)
    except (TypeError, ValueError):
        max_minutes_value = int(DEFAULT_SETTINGS["maxMinutes"])
    persist_ui_defaults(
        {
            "GITHUB_OWNER": github_owner.strip(),
            "GITHUB_REPO": github_repo.strip(),
            "branch_base": branch_base.strip(),
            "modelCTO": model_cto.strip(),
            "modelCoder": model_coder.strip(),
            "budgetUsd": budget_value,
            "maxRequests": max_requests_value,
            "maxMinutes": max_minutes_value,
        }
    )
    payload = {
        "githubOwner": github_owner.strip(),
        "githubRepo": github_repo.strip(),
        "branch_base": branch_base.strip(),
        "modelCTO": model_cto.strip(),
        "modelCoder": model_coder.strip(),
        "budgetUsd": budget_value,
        "maxRequests": max_requests_value,
        "maxMinutes": max_minutes_value,
        "dry_run": bool(dry_run),
        "task": task_text.strip(),
    }
    start_url = api_base_url.rstrip("/") + "/tasks"
    try:
        response = request_with_backoff("POST", start_url, json=payload)
        response.raise_for_status()
    except requests.RequestException as exc:
        error_line = format_log_line(f"Failed to start job: {exc}")
        yield error_line, gr.update(), {}, f"Run failed: {exc}"
        return
    data = response.json()
    job_id = data.get("job_id") or data.get("id")
    if not job_id:
        error_line = format_log_line("Backend response missing job_id")
        yield error_line, gr.update(), {}, "Run failed: missing job_id"
        return
    log_lines = [format_log_line(f"Job {job_id} started.")]
    tracker: Dict[str, Any] = {"events": 0, "steps": 0, "status": None}
    metrics_text = "Awaiting first update..."
    state = {"job_id": job_id, "active": True}
    yield "\n".join(log_lines), metrics_text, state, f"Job {job_id} launched."
    poll_url = api_base_url.rstrip("/") + f"/jobs/{job_id}"
    while True:
        time.sleep(2)
        try:
            poll_response = request_with_backoff("GET", poll_url)
            poll_response.raise_for_status()
        except requests.RequestException as exc:
            log_lines.append(format_log_line(f"Polling error: {exc}"))
            yield "\n".join(log_lines), gr.update(), state, f"Polling failed: {exc}"
            time.sleep(2)
            continue
        job_payload = poll_response.json()
        new_lines = extract_tail_updates(job_payload, tracker)
        log_lines.extend(new_lines)
        metrics_text = format_metrics(job_payload)
        status = job_payload.get("status", "unknown")
        state = {"job_id": job_id, "active": status not in TERMINAL_STATUSES}
        yield "\n".join(log_lines), metrics_text, state, f"Status: {status}"
        if status in TERMINAL_STATUSES:
            break


def build_interface() -> gr.Blocks:
    initial = load_initial_values()
    with gr.Blocks(title="Auto Dev Orchestrator UI", theme=gr.themes.Default()) as demo:
        status_banner = gr.Markdown("", elem_id="status-banner")
        with gr.Row():
            api_base_input = gr.Textbox(
                label="API Base URL",
                value=initial.get("API_BASE_URL", DEFAULT_SETTINGS["API_BASE_URL"]),
                placeholder="http://localhost:3000",
            )
        with gr.Accordion("Secrets", open=False):
            openai_key_input = gr.Textbox(
                label="OPENAI_API_KEY",
                value=initial.get("OPENAI_API_KEY", ""),
                type="password",
                placeholder="sk-...",
            )
            github_token_input = gr.Textbox(
                label="GITHUB_TOKEN",
                value=initial.get("GITHUB_TOKEN", ""),
                type="password",
                placeholder="ghp_...",
            )
        with gr.Accordion("Settings", open=True):
            with gr.Row():
                owner_input = gr.Textbox(
                    label="GITHUB_OWNER",
                    value=initial.get("GITHUB_OWNER", ""),
                    placeholder="my-org",
                )
                repo_input = gr.Textbox(
                    label="GITHUB_REPO",
                    value=initial.get("GITHUB_REPO", ""),
                    placeholder="my-repo",
                )
            branch_input = gr.Textbox(
                label="branch_base",
                value=initial.get("branch_base", DEFAULT_SETTINGS["branch_base"]),
                placeholder="main",
            )
            with gr.Row():
                model_cto_input = gr.Textbox(
                    label="modelCTO",
                    value=initial.get("modelCTO", DEFAULT_SETTINGS["modelCTO"]),
                    placeholder="gpt-4.1-mini",
                )
                model_coder_input = gr.Textbox(
                    label="modelCoder",
                    value=initial.get("modelCoder", DEFAULT_SETTINGS["modelCoder"]),
                    placeholder="gpt-4.1",
                )
            with gr.Row():
                budget_input = gr.Number(
                    label="budgetUsd",
                    value=initial.get("budgetUsd", DEFAULT_SETTINGS["budgetUsd"]),
                    precision=2,
                )
                max_requests_input = gr.Number(
                    label="maxRequests",
                    value=initial.get("maxRequests", DEFAULT_SETTINGS["maxRequests"]),
                    precision=0,
                )
                max_minutes_input = gr.Number(
                    label="maxMinutes",
                    value=initial.get("maxMinutes", DEFAULT_SETTINGS["maxMinutes"]),
                    precision=0,
                )
            dry_run_checkbox = gr.Checkbox(label="DRY_RUN", value=False)
        task_input = gr.Textbox(
            label="Task",
            placeholder="Beschreibe deine Aufgabe...",
            lines=8,
        )
        with gr.Row():
            save_button = gr.Button("Save .env")
            health_button = gr.Button("Health")
            run_button = gr.Button("Run", variant="primary")
            cancel_button = gr.Button("Cancel", variant="stop")
        health_output = gr.Markdown(label="Health")
        metrics_output = gr.Markdown("Status · Runtime 0s", label="Job Metrics")
        log_output = gr.Textbox(
            label="Tail",
            value="",
            lines=18,
            interactive=False,
        )
        job_state = gr.State({})

        save_button.click(
            on_save_env,
            inputs=[
                api_base_input,
                openai_key_input,
                github_token_input,
                owner_input,
                repo_input,
                branch_input,
                model_cto_input,
                model_coder_input,
                budget_input,
                max_requests_input,
                max_minutes_input,
            ],
            outputs=status_banner,
        )

        health_button.click(
            lambda api_base: health_check(api_base),
            inputs=[api_base_input],
            outputs=[status_banner, health_output],
        )

        run_button.click(
            run_job,
            inputs=[
                api_base_input,
                owner_input,
                repo_input,
                branch_input,
                model_cto_input,
                model_coder_input,
                budget_input,
                max_requests_input,
                max_minutes_input,
                dry_run_checkbox,
                task_input,
            ],
            outputs=[log_output, metrics_output, job_state, status_banner],
        )

        cancel_button.click(
            cancel_job,
            inputs=[api_base_input, job_state, log_output],
            outputs=[log_output, metrics_output, job_state, status_banner],
        )

    return demo


if __name__ == "__main__":
    app = build_interface()
    app.launch(server_name="0.0.0.0", server_port=7860)
