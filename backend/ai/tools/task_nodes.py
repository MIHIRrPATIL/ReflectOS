from ai.core.state import ReflectState
from ai.core.config import OPENROUTER_API_KEY_2, OPENROUTER_MODEL, OPENROUTER_URL
from ai.core.local_llm import LocalLLM
from utils.ai_helpers import extract_json
from services.task_service import TaskService
import json
import datetime
import requests



def task_node(state: ReflectState):
    """
    Manages TODO tasks (ADD_TASK, READ_TASKS) with persistent SQLite storage.
    Uses LLM to parse natural language into structured task operations.
    """
    user_input = state.get("user_input", "")
    user_id = state.get("user_id", "local_user")
    print(f"[TASKS] Processing: {user_input}")

    task_service = TaskService.get_instance()

    # 1. Parse the request using LLM
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S (%A)")

    system_prompt = (
        "You are an assistant that parses TODO/task management requests. "
        f"The current date and time is: {now_str} (timezone: Asia/Kolkata, IST). "
        "Use this to resolve relative deadlines like 'tomorrow', 'next Monday', 'by Friday', etc.\n\n"
        "Determine the action and extract parameters. Output ONLY valid JSON.\n\n"
        "Actions:\n"
        "- ADD: {\"action\": \"ADD\", \"title\": \"task description\", \"deadline\": \"YYYY-MM-DDTHH:MM:SS\" or null}\n"
        "- LIST: {\"action\": \"LIST\", \"show_done\": false}\n"
        "- DONE: {\"action\": \"DONE\", \"title\": \"task to mark done (partial match ok)\"}\n"
        "- DONE_ALL: {\"action\": \"DONE_ALL\"} — Use when user wants to mark ALL pending tasks as done\n"
        "- DELETE: {\"action\": \"DELETE\", \"title\": \"task to delete (partial match ok)\"}\n"
        "- UPDATE: {\"action\": \"UPDATE\", \"title\": \"existing task (partial match)\", \"new_title\": \"updated text\" or null, \"new_deadline\": \"YYYY-MM-DDTHH:MM:SS\" or null}\n\n"
        "Examples:\n"
        "- 'add buy groceries by tomorrow 5pm' → {\"action\": \"ADD\", \"title\": \"Buy groceries\", \"deadline\": \"2026-03-02T17:00:00\"}\n"
        "- 'show my tasks' → {\"action\": \"LIST\", \"show_done\": false}\n"
        "- 'mark groceries as done' → {\"action\": \"DONE\", \"title\": \"groceries\"}\n"
        "- 'mark all tasks as done' → {\"action\": \"DONE_ALL\"}\n"
        "- 'delete the groceries task' → {\"action\": \"DELETE\", \"title\": \"groceries\"}\n"
        "- 'show all tasks including completed' → {\"action\": \"LIST\", \"show_done\": true}\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    parsed_action = None
    if OPENROUTER_API_KEY_2:
        try:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY_2}", "Content-Type": "application/json"}
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0}
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"]
                parsed_action = extract_json(raw_content)
        except Exception as e:
            print(f"[ERROR] Tasks OpenRouter failed: {e}")

    if not parsed_action:
        print("[TASKS] Using Local Fallback for parsing...")
        raw_content = LocalLLM.get_instance().generate(messages)
        try:
            parsed_action = extract_json(raw_content)
        except Exception:
            parsed_action = None

    # Fallback: use keyword detection if LLM parsing fails completely
    if not isinstance(parsed_action, dict):
        lower = user_input.lower()
        if any(kw in lower for kw in ["add", "create", "new task", "remind me"]):
            # Extract the task title from user input
            title = user_input
            for prefix in ["add task", "add a task", "create task", "create a task", "add", "create", "remind me to", "new task"]:
                if lower.startswith(prefix):
                    title = user_input[len(prefix):].strip()
                    break
            parsed_action = {"action": "ADD", "title": title or "New Task"}
        elif any(kw in lower for kw in ["done", "complete", "finished", "mark"]):
            parsed_action = {"action": "DONE", "title": lower.replace("mark", "").replace("as done", "").replace("completed", "").replace("finished", "").strip()}
        elif any(kw in lower for kw in ["delete", "remove"]):
            parsed_action = {"action": "DELETE", "title": lower.replace("delete", "").replace("remove", "").replace("task", "").strip()}
        else:
            parsed_action = {"action": "LIST", "show_done": "all" in lower or "done" in lower}

    print(f"[TASKS] Parsed Action: {parsed_action}")

    # 2. Execute Action
    tool_output = {"status": "success", "action": parsed_action.get("action")}

    action = parsed_action.get("action", "LIST").upper()

    if action == "ADD":
        title = parsed_action.get("title", "New Task")
        deadline = parsed_action.get("deadline")
        result = task_service.add_task(user_id, title, deadline)
        tool_output["task"] = result
        deadline_str = f" (deadline: {deadline})" if deadline else ""
        tool_output["message"] = f"Added task: '{title}'{deadline_str}"

    elif action == "LIST":
        show_done = parsed_action.get("show_done", False)
        tasks = task_service.list_tasks(user_id, show_done=show_done)
        tool_output["tasks"] = tasks
        if tasks:
            task_lines = []
            for i, t in enumerate(tasks, 1):
                status = "✅" if t["done"] else "⬜"
                dl = f" (due: {t['deadline']})" if t.get("deadline") else ""
                task_lines.append(f"{i}. {status} {t['title']}{dl}")
            tool_output["message"] = f"You have {len(tasks)} tasks:\n" + "\n".join(task_lines)
        else:
            tool_output["message"] = "You have no pending tasks. Your list is clean!"

    elif action == "DONE":
        title_fragment = parsed_action.get("title", "")
        # If title is empty or generic ("all", "pending tasks", etc.), treat as DONE_ALL
        generic_titles = {"", "all", "all tasks", "pending tasks", "all pending tasks", "everything", "pending"}
        if title_fragment.lower().strip() in generic_titles:
            action = "DONE_ALL"
        else:
            result = task_service.mark_done(user_id, title_fragment=title_fragment)
            if result:
                tool_output["task"] = result
                tool_output["message"] = f"Marked '{result['title']}' as done! ✅"
            else:
                tool_output["status"] = "error"
                tool_output["message"] = f"Could not find a task matching '{title_fragment}'."

    if action == "DONE_ALL":
        count = task_service.mark_all_done(user_id)
        tool_output["action"] = "DONE_ALL"
        tool_output["message"] = f"Marked all {count} pending task(s) as done! ✅" if count > 0 else "No pending tasks to mark as done."

    elif action == "DELETE":
        title_fragment = parsed_action.get("title", "")
        result = task_service.delete_task(user_id, title_fragment=title_fragment)
        if result:
            tool_output["task"] = result
            tool_output["message"] = f"Deleted task: '{result['title']}'."
        else:
            tool_output["status"] = "error"
            tool_output["message"] = f"Could not find a task matching '{title_fragment}'."

    elif action == "UPDATE":
        title_fragment = parsed_action.get("title", "")
        new_title = parsed_action.get("new_title")
        new_deadline = parsed_action.get("new_deadline")
        result = task_service.update_task(user_id, title_fragment=title_fragment, new_title=new_title, new_deadline=new_deadline)
        if result:
            tool_output["task"] = result
            tool_output["message"] = f"Updated task: '{result['title']}'."
        else:
            tool_output["status"] = "error"
            tool_output["message"] = f"Could not find a task matching '{title_fragment}'."

    else:
        tool_output["status"] = "error"
        tool_output["message"] = f"Unknown task action: {action}"

    # Update State
    state["tool_outputs"]["tasks"] = tool_output
    state["current_node"] = "task_node"
    state["execution_path"] = state.get("execution_path", []) + ["task_node"]

    return state
