from ai.core.state import ReflectState
from ai.core.config import OPENROUTER_API_KEY_2, OPENROUTER_MODEL, OPENROUTER_URL
from ai.core.local_llm import LocalLLM
from utils.ai_helpers import extract_json
from services.expense_service import ExpenseService
import json
import datetime
import requests

def expense_node(state: ReflectState):
    """
    Manages expenses, income, transfers, debts, and financial summaries.
    Uses LLM to parse natural language into structured finance operations.
    """
    user_input = state.get("user_input", "")
    user_id = state.get("user_id", "local_user")
    print(f"[EXPENSE] Processing: {user_input}")

    service = ExpenseService.get_instance()

    # 1. Parse the request using LLM
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S (%A)")

    # Get current balances for context
    balances = service.get_balances(user_id)
    balance_ctx = ", ".join([f"{b['name']}: ₹{b['balance']:.0f}" for b in balances])

    # Get categories for context
    categories = service.get_categories(user_id)
    expense_cats = [c["name"] for c in categories if c["type"] == "expense"]
    income_cats = [c["name"] for c in categories if c["type"] == "income"]

    system_prompt = (
        "You are a personal finance assistant that parses expense/income requests. "
        f"Current date/time: {now_str} (IST). "
        f"Available accounts: Union Bank, SBI, Saraswat, Cash. Current balances: {balance_ctx}. "
        f"Expense categories: {', '.join(expense_cats)}. "
        f"Income categories: {', '.join(income_cats)}. "
        "Output ONLY valid JSON.\n\n"
        "Actions:\n"
        '- ADD_EXPENSE: {"action": "ADD_EXPENSE", "amount": 500, "category": "Food", "description": "lunch", "account": "Union Bank", "date": "YYYY-MM-DD" or null}\n'
        '- ADD_INCOME: {"action": "ADD_INCOME", "amount": 50000, "category": "Salary", "description": "monthly salary", "account": "SBI", "date": null}\n'
        '- TRANSFER: {"action": "TRANSFER", "amount": 2000, "from_account": "Union Bank", "to_account": "Saraswat", "description": "savings"}\n'
        '- BALANCE: {"action": "BALANCE"}\n'
        '- LIST: {"action": "LIST", "days": 7, "account": null, "category": null}\n'
        '- SUMMARY: {"action": "SUMMARY", "period": "weekly"} (weekly/daily/monthly)\n'
        '- ADD_DEBT: {"action": "ADD_DEBT", "person": "Rahul", "amount": 500, "direction": "owed", "description": "dinner"}\n'
        '  direction: "owe" = I owe them, "owed" = they owe me\n'
        '- LIST_DEBTS: {"action": "LIST_DEBTS"}\n'
        '- SETTLE_DEBT: {"action": "SETTLE_DEBT", "person": "Rahul"}\n'
        '- ADD_CATEGORY: {"action": "ADD_CATEGORY", "name": "Subscriptions", "type": "expense"}\n'
        '- DELETE_TX: {"action": "DELETE_TX", "id": 5}\n\n'
        "Examples:\n"
        '- "I spent 200 on food from Union Bank" → {"action": "ADD_EXPENSE", "amount": 200, "category": "Food", "description": "food", "account": "Union Bank"}\n'
        '- "Got 50k salary in SBI" → {"action": "ADD_INCOME", "amount": 50000, "category": "Salary", "description": "salary", "account": "SBI"}\n'
        '- "Transfer 5000 from Union Bank to savings" → {"action": "TRANSFER", "amount": 5000, "from_account": "Union Bank", "to_account": "Saraswat"}\n'
        '- "Rahul owes me 1500 for dinner" → {"action": "ADD_DEBT", "person": "Rahul", "amount": 1500, "direction": "owed", "description": "dinner"}\n'
        '- "How much did I spend this week?" → {"action": "SUMMARY", "period": "weekly"}\n'
        '- "Show my balances" → {"action": "BALANCE"}\n'
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    parsed = None
    if OPENROUTER_API_KEY_2:
        try:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY_2}", "Content-Type": "application/json"}
            payload = {"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0}
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"]
                parsed = extract_json(raw)
        except Exception as e:
            print(f"[ERROR] Expense OpenRouter failed: {e}")

    if not parsed:
        print("[EXPENSE] Using Local Fallback...")
        raw = LocalLLM.get_instance().generate(messages)
        try:
            parsed = extract_json(raw)
        except Exception:
            parsed = None

    # Keyword fallback
    if not isinstance(parsed, dict):
        lower = user_input.lower()
        if any(kw in lower for kw in ["balance", "how much do i have"]):
            parsed = {"action": "BALANCE"}
        elif any(kw in lower for kw in ["summary", "how much did i spend", "spending"]):
            period = "daily" if "today" in lower or "daily" in lower else "monthly" if "month" in lower else "weekly"
            parsed = {"action": "SUMMARY", "period": period}
        elif any(kw in lower for kw in ["owe", "debt", "lent", "borrowed"]):
            parsed = {"action": "LIST_DEBTS"}
        else:
            parsed = {"action": "LIST", "days": 7}

    print(f"[EXPENSE] Parsed: {parsed}")

    # 2. Execute
    action = parsed.get("action", "LIST").upper()
    tool_output = {"status": "success", "action": action}

    if action == "ADD_EXPENSE":
        result = service.add_expense(
            user_id,
            amount=parsed.get("amount", 0),
            category=parsed.get("category", "Other"),
            description=parsed.get("description", ""),
            account_name=parsed.get("account", "Cash"),
            date=parsed.get("date")
        )
        tool_output["transaction"] = result
        tool_output["message"] = f"Recorded expense: ₹{result['amount']} ({result['category']}) from {result['account']}"
        if result.get("description"):
            tool_output["message"] += f" — {result['description']}"

    elif action == "ADD_INCOME":
        result = service.add_income(
            user_id,
            amount=parsed.get("amount", 0),
            category=parsed.get("category", "Salary"),
            description=parsed.get("description", ""),
            account_name=parsed.get("account", "Cash"),
            date=parsed.get("date")
        )
        tool_output["transaction"] = result
        tool_output["message"] = f"Recorded income: ₹{result['amount']} ({result['category']}) to {result['account']}"

    elif action == "TRANSFER":
        result = service.transfer(
            user_id,
            amount=parsed.get("amount", 0),
            from_account_name=parsed.get("from_account", ""),
            to_account_name=parsed.get("to_account", ""),
            description=parsed.get("description")
        )
        if result:
            tool_output["transaction"] = result
            tool_output["message"] = f"Transferred ₹{result['amount']} from {result['from']} to {result['to']}"
        else:
            tool_output["status"] = "error"
            tool_output["message"] = "Could not find one or both accounts for the transfer."

    elif action == "BALANCE":
        accts = service.get_balances(user_id)
        tool_output["accounts"] = accts
        lines = [f"  • {a['name']}: ₹{a['balance']:,.0f}" for a in accts]
        total = sum(a["balance"] for a in accts)
        tool_output["message"] = "Account Balances:\n" + "\n".join(lines) + f"\n  Total: ₹{total:,.0f}"

    elif action == "LIST":
        txns = service.list_transactions(
            user_id,
            days=parsed.get("days", 7),
            account_name=parsed.get("account"),
            category=parsed.get("category")
        )
        tool_output["transactions"] = txns
        if txns:
            lines = []
            for t in txns:
                if t["type"] == "transfer":
                    lines.append(f"  • {t['date']}: ↔ ₹{t['amount']:,.0f} ({t['from_account']} → {t['to_account']})")
                elif t["type"] == "expense":
                    lines.append(f"  • {t['date']}: -₹{t['amount']:,.0f} [{t['category']}] {t['description'] or ''} ({t['from_account'] or ''})")
                else:
                    lines.append(f"  • {t['date']}: +₹{t['amount']:,.0f} [{t['category']}] {t['description'] or ''} ({t['from_account'] or ''})")
            tool_output["message"] = f"Last {parsed.get('days', 7)} days ({len(txns)} transactions):\n" + "\n".join(lines)
        else:
            tool_output["message"] = "No transactions found for this period."

    elif action == "SUMMARY":
        summary = service.get_summary(user_id, period=parsed.get("period", "weekly"))
        tool_output["summary"] = summary
        lines = [f"  • {c['category']}: ₹{c['total']:,.0f} ({c['count']} txns)" for c in summary["by_category"]]
        tool_output["message"] = (
            f"{summary['period'].title()} Summary ({summary['days']} days):\n"
            f"  Income: ₹{summary['income_total']:,.0f}\n"
            f"  Expenses: ₹{summary['expense_total']:,.0f}\n"
            f"  Net: ₹{summary['net']:,.0f}\n"
            + ("Breakdown:\n" + "\n".join(lines) if lines else "No expenses recorded.")
        )

    elif action == "ADD_DEBT":
        result = service.add_debt(
            user_id,
            person=parsed.get("person", "Someone"),
            amount=parsed.get("amount", 0),
            direction=parsed.get("direction", "owed"),
            description=parsed.get("description")
        )
        tool_output["debt"] = result
        if result["direction"] == "owed":
            tool_output["message"] = f"{result['person']} owes you ₹{result['amount']:,.0f}"
        else:
            tool_output["message"] = f"You owe {result['person']} ₹{result['amount']:,.0f}"
        if result.get("description"):
            tool_output["message"] += f" for {result['description']}"

    elif action == "LIST_DEBTS":
        debts = service.list_debts(user_id, settled=parsed.get("show_settled", False))
        tool_output["debts"] = debts
        if debts:
            owed_to_me = [d for d in debts if d["direction"] == "owed"]
            i_owe = [d for d in debts if d["direction"] == "owe"]
            lines = []
            if owed_to_me:
                lines.append("People who owe you:")
                for d in owed_to_me:
                    desc = f" ({d['description']})" if d.get("description") else ""
                    lines.append(f"  • {d['person']}: ₹{d['amount']:,.0f}{desc}")
            if i_owe:
                lines.append("You owe:")
                for d in i_owe:
                    desc = f" ({d['description']})" if d.get("description") else ""
                    lines.append(f"  • {d['person']}: ₹{d['amount']:,.0f}{desc}")
            tool_output["message"] = "\n".join(lines)
        else:
            tool_output["message"] = "No outstanding debts!"

    elif action == "SETTLE_DEBT":
        count = service.settle_debt(user_id, person=parsed.get("person", ""))
        tool_output["message"] = f"Settled {count} debt(s) with {parsed.get('person', 'them')}." if count > 0 else f"No unsettled debts found with '{parsed.get('person', '')}'."

    elif action == "ADD_CATEGORY":
        result = service.add_category(user_id, name=parsed.get("name", ""), cat_type=parsed.get("type", "expense"))
        tool_output["category"] = result
        tool_output["message"] = f"Added category: {result['name']} ({result['type']})"

    elif action == "DELETE_TX":
        result = service.delete_transaction(user_id, tx_id=parsed.get("id", 0))
        if result:
            tool_output["message"] = f"Deleted transaction #{result['id']}."
        else:
            tool_output["status"] = "error"
            tool_output["message"] = "Transaction not found."

    else:
        tool_output["status"] = "error"
        tool_output["message"] = f"Unknown expense action: {action}"

    # Update state
    if "tool_outputs" not in state or state["tool_outputs"] is None:
        state["tool_outputs"] = {}
    state["tool_outputs"]["expenses"] = tool_output
    state["current_node"] = "expense_node"
    state["execution_path"] = state.get("execution_path", []) + ["expense_node"]

    return state
