from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import gradio as gr
import requests
from dotenv import dotenv_values, set_key

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
UI_DEFAULTS_PATH = ROOT_DIR / "webui" / "ui_defaults.json"
API_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 2
TERMINAL_STATUSES = {"completed", "succeeded", "failed", "timeout", "cancelled", "canceled"}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "API_BASE_URL": "http://localhost:3000",
    "GITHUB_OWNER": "",
    "GITHUB_REPO": "",
    "branch_base": "main",
    "modelCTO": "gpt-4.1-mini",
    "modelCoder": "gpt-4.1",
    "budgetUsd": 2.5,
    "maxRequests": 120,
    "maxMinutes": 45,
    "task": "Beschreibe hier deine gewünschte Änderung",
}

REQUEST_SESSION = requests.Session()


def _coerce_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def load_ui_defaults() -> Dict[str, Any]:
    if UI_DEFAULTS_PATH.exists():
        try:
            return json.loads(UI_DEFAULTS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def persist_ui_defaults(values: Dict[str, Any]) -> None:
    safe_values = {
        "API_BASE_URL": values.get("API_BASE_URL", DEFAULT_SETTINGS["API_BASE_URL"]),
        "GITHUB_OWNER": values.get("GITHUB_OWNER", ""),
        "GITHUB_REPO": values.get("GITHUB_REPO", ""),
        "branch_base": values.get("branch_base", DEFAULT_SETTINGS["branch_base"]),
        "modelCTO": values.get("modelCTO", DEFAULT_SETTINGS["modelCTO"]),
        "modelCoder": values.get("modelCoder", DEFAULT_SETTINGS["modelCoder"]),
        "budgetUsd": values.get("budgetUsd", DEFAULT_SETTINGS["budgetUsd"]),
        "maxRequests": values.get("maxRequests", DEFAULT_SETTINGS["maxRequests"]),
        "maxMinutes": values.get("maxMinutes", DEFAULT_SETTINGS["maxMinutes"]),
        "task": values.get("task", DEFAULT_SETTINGS["task"]),
    }
    UI_DEFAULTS_PATH.write_text(json.dumps(safe_values, indent=2, ensure_ascii=False), encoding="utf-8")


def load_initial_values() -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    values.update(DEFAULT_SETTINGS)
    values.update(load_ui_defaults())
    env_values = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    values.update({k: v for k, v in env_values.items() if v is not None})

    for numeric_key in ("budgetUsd", "maxRequests", "maxMinutes"):
        raw_value = values.get(numeric_key)
        if raw_value is None or raw_value == "":
            values[numeric_key] = DEFAULT_SETTINGS[numeric_key]
            continue
        try:
            if numeric_key == "budgetUsd":
                values[numeric_key] = float(raw_value)
            else:
                values[numeric_key] = int(raw_value)
        except (TypeError, ValueError):
            values[numeric_key] = DEFAULT_SETTINGS[numeric_key]

    api_base = str(values.get("API_BASE_URL") or DEFAULT_SETTINGS["API_BASE_URL"]).strip()
    values["API_BASE_URL"] = api_base or DEFAULT_SETTINGS["API_BASE_URL"]
    return values


def ensure_env_file() -> None:
    if not ENV_PATH.exists():
        ENV_PATH.touch()


def save_env(values: Dict[str, Optional[str]]) -> str:
    ensure_env_file()
    changed_keys: List[str] = []
    existing = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    for key, value in values.items():
        safe_value = "" if value is None else str(value)
        previous = existing.get(key)
        if previous != safe_value:
            changed_keys.append(key)
        set_key(str(ENV_PATH), key, safe_value, quote_mode="never")
    if changed_keys:
        return "Aktualisierte .env Schlüssel: " + ", ".join(changed_keys)
    return "Keine Änderungen an .env erforderlich"


def normalize_base_url(url: str) -> str:
    cleaned = (url or "").strip()
    if not cleaned:
        cleaned = DEFAULT_SETTINGS["API_BASE_URL"]
    return cleaned.rstrip("/")


def format_status(job: Dict[str, Any]) -> str:
    status = job.get("status", "unbekannt")
    progress = job.get("progress")
    cost = job.get("cost_usd")
    last_action = job.get("last_action") or ""
    parts = [f"**Status:** {status}"]
    if progress is not None:
        parts.append(f"Fortschritt: {progress:.0%}" if isinstance(progress, float) else f"Fortschritt: {progress}")
    if isinstance(cost, (int, float)):
        parts.append(f"Kosten USD: {cost:.2f}")
    if last_action:
        parts.append(f"Letzte Aktion: {last_action}")
    pr_md = format_pr_links(job.get("pr_links") or job.get("pr_urls") or [])
    return " | ".join(parts) + (f"\n\n{pr_md}" if pr_md else "")


def format_pr_links(links: Any) -> str:
    if not isinstance(links, list):
        return ""
    safe_links = [str(link) for link in links if link]
    if not safe_links:
        return ""
    items = [f"[PR {idx + 1}]({link})" for idx, link in enumerate(safe_links)]
    return "PR Links: " + " · ".join(items)


def append_tail_line(state: Dict[str, Any], message: str) -> None:
    lines: List[str] = state.setdefault("lines", [])
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"[{timestamp}] {message}")
    # Limit tail to latest 200 lines to keep UI light
    if len(lines) > 200:
        del lines[:-200]


def tail_text(state: Dict[str, Any]) -> str:
    lines: List[str] = state.get("lines", [])
    return "\n".join(lines)


def health_check(api_base_url: str) -> str:
    base_url = normalize_base_url(api_base_url)
    try:
        response = REQUEST_SESSION.get(f"{base_url}/health", timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        filtered = {k: payload.get(k) for k in ("ok", "db", "redis", "version")}
        return "Health OK: " + json.dumps(filtered, ensure_ascii=False)
    except requests.HTTPError as exc:
        try:
            detail = exc.response.json()
        except Exception:
            detail = exc.response.text if exc.response else str(exc)
        return f"Health Check fehlgeschlagen ({exc.response.status_code if exc.response else 'n/a'}): {detail}"
    except requests.RequestException as exc:
        return f"Health Check fehlgeschlagen: {exc}"


def run_task(
    api_base_url: str,
    task_text: str,
    owner: str,
    repo: str,
    branch: str,
    model_cto: str,
    model_coder: str,
    budget_usd: float,
    max_requests: int,
    max_minutes: int,
    state: Dict[str, Any],
) -> tuple[str, str, Dict[str, Any]]:
    base_url = normalize_base_url(api_base_url)
    budget_val = _coerce_float(budget_usd, DEFAULT_SETTINGS["budgetUsd"])
    max_requests_val = _coerce_int(max_requests, int(DEFAULT_SETTINGS["maxRequests"]))
    max_minutes_val = _coerce_int(max_minutes, int(DEFAULT_SETTINGS["maxMinutes"]))
    persist_ui_defaults(
        {
            "API_BASE_URL": base_url,
            "GITHUB_OWNER": owner,
            "GITHUB_REPO": repo,
            "branch_base": branch,
            "modelCTO": model_cto,
            "modelCoder": model_coder,
            "budgetUsd": budget_val,
            "maxRequests": max_requests_val,
            "maxMinutes": max_minutes_val,
            "task": task_text,
        }
    )

    payload = {
        "task": task_text,
        "repo_owner": owner,
        "repo_name": repo,
        "branch_base": branch,
        "budgetUsd": budget_val,
        "maxRequests": max_requests_val,
        "maxMinutes": max_minutes_val,
        "modelCTO": model_cto or None,
        "modelCoder": model_coder or None,
    }

    try:
        response = REQUEST_SESSION.post(
            f"{base_url}/tasks",
            json=payload,
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        append_tail_line(state, f"Fehler beim Starten des Jobs: {exc}")
        state.update({"job_id": None, "done": True})
        return f"Job konnte nicht gestartet werden: {exc}", tail_text(state), state

    job_id = response.json().get("job_id")
    state.update(
        {
            "job_id": job_id,
            "base_url": base_url,
            "done": False,
            "last_status": None,
            "last_action": None,
            "cancel_requested": False,
        }
    )
    append_tail_line(state, f"Job {job_id} wurde gestartet.")
    return f"Job gestartet (ID: {job_id}).", tail_text(state), state


def cancel_job(state: Dict[str, Any]) -> tuple[str, str, Dict[str, Any]]:
    job_id = state.get("job_id")
    base_url = state.get("base_url")
    if not job_id or not base_url:
        return "Kein laufender Job zum Abbrechen.", tail_text(state), state

    try:
        response = REQUEST_SESSION.post(
            f"{base_url}/jobs/{job_id}/cancel",
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        append_tail_line(state, f"Cancel Request gesendet (Job {job_id}).")
        state["cancel_requested"] = True
        return "Cancel Request gesendet.", tail_text(state), state
    except requests.RequestException as exc:
        append_tail_line(state, f"Cancel fehlgeschlagen: {exc}")
        return f"Cancel fehlgeschlagen: {exc}", tail_text(state), state


def poll_job(state: Dict[str, Any]) -> tuple[Any, Any, Dict[str, Any]]:
    job_id = state.get("job_id")
    base_url = state.get("base_url")
    if not job_id or not base_url or state.get("done"):
        return gr.update(), gr.update(), state

    try:
        response = REQUEST_SESSION.get(
            f"{base_url}/jobs/{job_id}", timeout=API_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        job = response.json()
    except requests.RequestException as exc:
        append_tail_line(state, f"Polling-Fehler: {exc}")
        state["done"] = True
        return gr.update(value="Polling-Fehler"), tail_text(state), state

    last_status = state.get("last_status")
    last_action = state.get("last_action")
    status = job.get("status")
    action = job.get("last_action")

    if status and status != last_status:
        append_tail_line(state, f"Status → {status}")
        state["last_status"] = status
    if action and action != last_action:
        append_tail_line(state, f"Aktion → {action}")
        state["last_action"] = action

    if status and status.lower() in TERMINAL_STATUSES:
        state["done"] = True
        append_tail_line(state, f"Job abgeschlossen mit Status {status}.")

    status_md = format_status(job)
    return gr.update(value=status_md), gr.update(value=tail_text(state)), state


def save_env_action(
    openai_key: str,
    github_token: str,
    owner: str,
    repo: str,
    branch: str,
    model_cto: str,
    model_coder: str,
    budget_usd: float,
    max_requests: int,
    max_minutes: int,
    api_base_url: str,
    state: Dict[str, Any],
) -> tuple[str, str, Dict[str, Any]]:
    budget_val = _coerce_float(budget_usd, DEFAULT_SETTINGS["budgetUsd"])
    max_requests_val = _coerce_int(max_requests, int(DEFAULT_SETTINGS["maxRequests"]))
    max_minutes_val = _coerce_int(max_minutes, int(DEFAULT_SETTINGS["maxMinutes"]))
    persist_ui_defaults(
        {
            "API_BASE_URL": normalize_base_url(api_base_url),
            "GITHUB_OWNER": owner,
            "GITHUB_REPO": repo,
            "branch_base": branch,
            "modelCTO": model_cto,
            "modelCoder": model_coder,
            "budgetUsd": budget_val,
            "maxRequests": max_requests_val,
            "maxMinutes": max_minutes_val,
            "task": state.get("last_task", DEFAULT_SETTINGS["task"]),
        }
    )

    message = save_env(
        {
            "OPENAI_API_KEY": openai_key,
            "GITHUB_TOKEN": github_token,
            "GITHUB_OWNER": owner,
            "GITHUB_REPO": repo,
            "MODEL_CTO": model_cto,
            "MODEL_CODER": model_coder,
            "BUDGET_USD_MAX": budget_val,
            "MAX_REQUESTS": max_requests_val,
            "MAX_WALLCLOCK_MINUTES": max_minutes_val,
        }
    )
    append_tail_line(state, "Speichere .env (Werte werden nicht geloggt).")
    return message, tail_text(state), state


def update_task_state(task_text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    state["last_task"] = task_text
    return state


def launch_ui() -> None:
    initial = load_initial_values()

    with gr.Blocks(title="Auto Dev Orchestrator UI") as demo:
        gr.Markdown("## Auto Dev Orchestrator – Control Center")
        state = gr.State({"lines": []})

        with gr.Row():
            api_base_input = gr.Textbox(
                label="API Base URL",
                value=initial["API_BASE_URL"],
                placeholder="http://localhost:3000",
            )

        with gr.Accordion("Secrets", open=False):
            openai_input = gr.Textbox(label="OPENAI_API_KEY", value=initial.get("OPENAI_API_KEY", ""), type="password")
            github_token_input = gr.Textbox(label="GITHUB_TOKEN", value=initial.get("GITHUB_TOKEN", ""), type="password")

        with gr.Accordion("Settings", open=True):
            with gr.Row():
                owner_input = gr.Textbox(label="GitHub Owner", value=initial.get("GITHUB_OWNER", ""))
                repo_input = gr.Textbox(label="GitHub Repo", value=initial.get("GITHUB_REPO", ""))
                branch_input = gr.Textbox(label="Branch", value=initial.get("branch_base", "main"))
            with gr.Row():
                model_cto_input = gr.Textbox(label="CTO Modell", value=initial.get("modelCTO", ""))
                model_coder_input = gr.Textbox(label="Coder Modell", value=initial.get("modelCoder", ""))
            with gr.Row():
                budget_input = gr.Number(label="Budget (USD)", value=initial.get("budgetUsd", 2.5), precision=2)
                max_requests_input = gr.Number(label="Max Requests", value=initial.get("maxRequests", 120), precision=0)
                max_minutes_input = gr.Number(label="Max Minuten", value=initial.get("maxMinutes", 45), precision=0)

        task_input = gr.Textbox(
            label="Task Beschreibung",
            value=initial.get("task", DEFAULT_SETTINGS["task"]),
            lines=8,
            placeholder="Beschreibe die gewünschte Änderung",
        )

        with gr.Row():
            save_button = gr.Button("Save .env")
            health_button = gr.Button("Health")
            run_button = gr.Button("Run", variant="primary")
            cancel_button = gr.Button("Cancel", variant="stop")

        status_markdown = gr.Markdown("Status wird hier angezeigt.")
        log_output = gr.Textbox(label="Job Tail", value="", lines=12, interactive=False)

        timer = gr.Timer(POLL_INTERVAL_SECONDS)
        timer.tick(fn=poll_job, inputs=state, outputs=[status_markdown, log_output, state])

        save_button.click(
            save_env_action,
            inputs=[
                openai_input,
                github_token_input,
                owner_input,
                repo_input,
                branch_input,
                model_cto_input,
                model_coder_input,
                budget_input,
                max_requests_input,
                max_minutes_input,
                api_base_input,
                state,
            ],
            outputs=[status_markdown, log_output, state],
        )

        health_button.click(
            lambda api_url, st: (health_check(api_url), tail_text(st), st),
            inputs=[api_base_input, state],
            outputs=[status_markdown, log_output, state],
        )

        run_button.click(
            run_task,
            inputs=[
                api_base_input,
                task_input,
                owner_input,
                repo_input,
                branch_input,
                model_cto_input,
                model_coder_input,
                budget_input,
                max_requests_input,
                max_minutes_input,
                state,
            ],
            outputs=[status_markdown, log_output, state],
        )

        cancel_button.click(
            cancel_job,
            inputs=[state],
            outputs=[status_markdown, log_output, state],
        )

        task_input.change(update_task_state, inputs=[task_input, state], outputs=state)

    demo.queue().launch()


if __name__ == "__main__":
    launch_ui()
