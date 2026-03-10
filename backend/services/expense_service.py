import sqlite3
import os
from datetime import datetime, timedelta

class ExpenseService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "data", "memory.db")

    def _get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)

    # ── Account Operations ────────────────────────────────────────

    def get_balances(self, user_id):
        """Get all account balances."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, name, type, balance FROM accounts WHERE user_id = ? ORDER BY id",
                (user_id,)
            ).fetchall()
            return [{"id": r[0], "name": r[1], "type": r[2], "balance": r[3]} for r in rows]
        finally:
            conn.close()

    def _find_account(self, conn, user_id, name_fragment):
        """Fuzzy-match an account by name fragment."""
        if not name_fragment:
            return None
        fragment = name_fragment.strip().lower()
        rows = conn.execute(
            "SELECT id, name, balance FROM accounts WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        # Try exact match first, then contains
        for r in rows:
            if r[1].lower() == fragment:
                return r
        for r in rows:
            if fragment in r[1].lower() or r[1].lower() in fragment:
                return r
        return None

    def _update_balance(self, conn, account_id, delta):
        """Adjust account balance by delta (positive or negative)."""
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            (delta, account_id)
        )

    # ── Transaction Operations ────────────────────────────────────

    def add_expense(self, user_id, amount, category, description, account_name, date=None):
        """Record an expense and deduct from account."""
        conn = self._get_conn()
        try:
            account = self._find_account(conn, user_id, account_name)
            account_id = account[0] if account else None
            tx_date = date or datetime.now().strftime("%Y-%m-%d")

            conn.execute(
                "INSERT INTO transactions (user_id, type, amount, category, description, account_id, date) VALUES (?,?,?,?,?,?,?)",
                (user_id, "expense", amount, category, description, account_id, tx_date)
            )
            if account_id:
                self._update_balance(conn, account_id, -amount)
            conn.commit()

            acct_name = account[1] if account else "Unknown"
            print(f"[EXPENSE] Added: ₹{amount} ({category}) from {acct_name}")
            return {"type": "expense", "amount": amount, "category": category, "description": description, "account": acct_name, "date": tx_date}
        finally:
            conn.close()

    def add_income(self, user_id, amount, category, description, account_name, date=None):
        """Record income and add to account."""
        conn = self._get_conn()
        try:
            account = self._find_account(conn, user_id, account_name)
            account_id = account[0] if account else None
            tx_date = date or datetime.now().strftime("%Y-%m-%d")

            conn.execute(
                "INSERT INTO transactions (user_id, type, amount, category, description, account_id, date) VALUES (?,?,?,?,?,?,?)",
                (user_id, "income", amount, category or "Other", description, account_id, tx_date)
            )
            if account_id:
                self._update_balance(conn, account_id, amount)
            conn.commit()

            acct_name = account[1] if account else "Unknown"
            print(f"[EXPENSE] Income: ₹{amount} ({category}) to {acct_name}")
            return {"type": "income", "amount": amount, "category": category, "description": description, "account": acct_name, "date": tx_date}
        finally:
            conn.close()

    def transfer(self, user_id, amount, from_account_name, to_account_name, description=None, date=None):
        """Transfer between accounts."""
        conn = self._get_conn()
        try:
            from_acc = self._find_account(conn, user_id, from_account_name)
            to_acc = self._find_account(conn, user_id, to_account_name)
            if not from_acc or not to_acc:
                return None
            tx_date = date or datetime.now().strftime("%Y-%m-%d")

            conn.execute(
                "INSERT INTO transactions (user_id, type, amount, description, account_id, to_account_id, date) VALUES (?,?,?,?,?,?,?)",
                (user_id, "transfer", amount, description or f"Transfer: {from_acc[1]} → {to_acc[1]}", from_acc[0], to_acc[0], tx_date)
            )
            self._update_balance(conn, from_acc[0], -amount)
            self._update_balance(conn, to_acc[0], amount)
            conn.commit()

            print(f"[EXPENSE] Transfer: ₹{amount} from {from_acc[1]} to {to_acc[1]}")
            return {"type": "transfer", "amount": amount, "from": from_acc[1], "to": to_acc[1], "date": tx_date}
        finally:
            conn.close()

    def list_transactions(self, user_id, days=7, account_name=None, category=None, limit=20):
        """List recent transactions with optional filters."""
        conn = self._get_conn()
        try:
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            query = """
                SELECT t.id, t.type, t.amount, t.category, t.description,
                       a1.name as from_account, a2.name as to_account, t.date
                FROM transactions t
                LEFT JOIN accounts a1 ON t.account_id = a1.id
                LEFT JOIN accounts a2 ON t.to_account_id = a2.id
                WHERE t.user_id = ? AND t.date >= ?
            """
            params = [user_id, cutoff]

            if account_name:
                account = self._find_account(conn, user_id, account_name)
                if account:
                    query += " AND (t.account_id = ? OR t.to_account_id = ?)"
                    params.extend([account[0], account[0]])

            if category:
                query += " AND t.category LIKE ?"
                params.append(f"%{category}%")

            query += " ORDER BY t.date DESC, t.id DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [{
                "id": r[0], "type": r[1], "amount": r[2], "category": r[3],
                "description": r[4], "from_account": r[5], "to_account": r[6], "date": r[7]
            } for r in rows]
        finally:
            conn.close()

    def get_summary(self, user_id, period="weekly"):
        """Get spending summary aggregated by category."""
        conn = self._get_conn()
        try:
            days = 7 if period == "weekly" else 1 if period == "daily" else 30
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            # Expenses by category
            rows = conn.execute("""
                SELECT category, SUM(amount) as total, COUNT(*) as count
                FROM transactions
                WHERE user_id = ? AND type = 'expense' AND date >= ?
                GROUP BY category ORDER BY total DESC
            """, (user_id, cutoff)).fetchall()

            expense_total = sum(r[1] for r in rows)
            categories = [{"category": r[0] or "Other", "total": r[1], "count": r[2]} for r in rows]

            # Income total
            income_row = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions
                WHERE user_id = ? AND type = 'income' AND date >= ?
            """, (user_id, cutoff)).fetchone()
            income_total = income_row[0]

            return {
                "period": period,
                "days": days,
                "expense_total": expense_total,
                "income_total": income_total,
                "net": income_total - expense_total,
                "by_category": categories
            }
        finally:
            conn.close()

    def delete_transaction(self, user_id, tx_id):
        """Delete a transaction and reverse the balance change."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT type, amount, account_id, to_account_id FROM transactions WHERE id = ? AND user_id = ?",
                (tx_id, user_id)
            ).fetchone()
            if not row:
                return None

            tx_type, amount, acc_id, to_acc_id = row
            # Reverse balance changes
            if tx_type == "expense" and acc_id:
                self._update_balance(conn, acc_id, amount)
            elif tx_type == "income" and acc_id:
                self._update_balance(conn, acc_id, -amount)
            elif tx_type == "transfer":
                if acc_id:
                    self._update_balance(conn, acc_id, amount)
                if to_acc_id:
                    self._update_balance(conn, to_acc_id, -amount)

            conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
            conn.commit()
            print(f"[EXPENSE] Deleted transaction #{tx_id}")
            return {"id": tx_id, "deleted": True}
        finally:
            conn.close()

    # ── Debt Operations ───────────────────────────────────────────

    def add_debt(self, user_id, person, amount, direction, description=None):
        """Add a debt record. direction: 'owe' (I owe them) or 'owed' (they owe me)."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO debts (user_id, person, amount, direction, description) VALUES (?,?,?,?,?)",
                (user_id, person, amount, direction, description)
            )
            conn.commit()
            label = f"You owe {person}" if direction == "owe" else f"{person} owes you"
            print(f"[EXPENSE] Debt: {label} ₹{amount}")
            return {"person": person, "amount": amount, "direction": direction, "description": description}
        finally:
            conn.close()

    def list_debts(self, user_id, settled=False):
        """List debts, optionally including settled ones."""
        conn = self._get_conn()
        try:
            if settled:
                rows = conn.execute(
                    "SELECT id, person, amount, direction, description, settled, created_at FROM debts WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, person, amount, direction, description, settled, created_at FROM debts WHERE user_id = ? AND settled = 0 ORDER BY created_at DESC",
                    (user_id,)
                ).fetchall()
            return [{
                "id": r[0], "person": r[1], "amount": r[2], "direction": r[3],
                "description": r[4], "settled": bool(r[5]), "created_at": r[6]
            } for r in rows]
        finally:
            conn.close()

    def settle_debt(self, user_id, person):
        """Settle all debts with a person."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "UPDATE debts SET settled = 1 WHERE user_id = ? AND person LIKE ? AND settled = 0",
                (user_id, f"%{person}%")
            )
            conn.commit()
            count = cursor.rowcount
            print(f"[EXPENSE] Settled {count} debt(s) with '{person}'")
            return count
        finally:
            conn.close()

    # ── Category Operations ───────────────────────────────────────

    def get_categories(self, user_id):
        """List all categories."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, name, type FROM categories WHERE user_id = ? ORDER BY type, name",
                (user_id,)
            ).fetchall()
            return [{"id": r[0], "name": r[1], "type": r[2]} for r in rows]
        finally:
            conn.close()

    def add_category(self, user_id, name, cat_type="expense"):
        """Add a custom category."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO categories (user_id, name, type) VALUES (?, ?, ?)",
                (user_id, name, cat_type)
            )
            conn.commit()
            print(f"[EXPENSE] Added category: {name} ({cat_type})")
            return {"name": name, "type": cat_type}
        finally:
            conn.close()

    # ── Global Search ─────────────────────────────────────────────

    def global_search(self, user_id, query, limit=30):
        """Search across transactions and debts by any field."""
        conn = self._get_conn()
        try:
            q = f"%{query}%"
            results = {"transactions": [], "debts": []}

            # Search transactions
            tx_rows = conn.execute("""
                SELECT t.id, t.type, t.amount, t.category, t.description,
                       a1.name as from_account, a2.name as to_account, t.date
                FROM transactions t
                LEFT JOIN accounts a1 ON t.account_id = a1.id
                LEFT JOIN accounts a2 ON t.to_account_id = a2.id
                WHERE t.user_id = ? AND (
                    t.category LIKE ? OR t.description LIKE ? OR
                    a1.name LIKE ? OR a2.name LIKE ? OR
                    t.date LIKE ? OR CAST(t.amount AS TEXT) LIKE ? OR
                    t.type LIKE ?
                )
                ORDER BY t.date DESC, t.id DESC LIMIT ?
            """, (user_id, q, q, q, q, q, q, q, limit)).fetchall()

            results["transactions"] = [{
                "id": r[0], "type": r[1], "amount": r[2], "category": r[3],
                "description": r[4], "from_account": r[5], "to_account": r[6], "date": r[7]
            } for r in tx_rows]

            # Search debts
            debt_rows = conn.execute("""
                SELECT id, person, amount, direction, description, settled, created_at
                FROM debts WHERE user_id = ? AND (
                    person LIKE ? OR description LIKE ? OR
                    CAST(amount AS TEXT) LIKE ?
                )
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, q, q, q, limit)).fetchall()

            results["debts"] = [{
                "id": r[0], "person": r[1], "amount": r[2], "direction": r[3],
                "description": r[4], "settled": bool(r[5]), "created_at": r[6]
            } for r in debt_rows]

            return results
        finally:
            conn.close()

