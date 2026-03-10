import sqlite3
import os
from datetime import datetime

class TaskService:
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

    def add_task(self, user_id, title, deadline=None):
        """Add a new task. Returns the created task dict."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO tasks (user_id, title, deadline) VALUES (?, ?, ?)",
                (user_id, title, deadline)
            )
            conn.commit()
            task_id = cursor.lastrowid
            print(f"[TASKS] Added task #{task_id}: '{title}' (deadline: {deadline})")
            return {"id": task_id, "title": title, "deadline": deadline, "done": False}
        finally:
            conn.close()

    def list_tasks(self, user_id, show_done=False):
        """List tasks for a user. By default only pending tasks."""
        conn = self._get_conn()
        try:
            if show_done:
                rows = conn.execute(
                    "SELECT id, title, deadline, done, created_at FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, title, deadline, done, created_at FROM tasks WHERE user_id = ? AND done = 0 ORDER BY created_at DESC",
                    (user_id,)
                ).fetchall()
            
            tasks = []
            for row in rows:
                tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "deadline": row[2],
                    "done": bool(row[3]),
                    "created_at": row[4]
                })
            # (suppressed — this fires on every poll)
            return tasks
        finally:
            conn.close()

    def mark_done(self, user_id, task_id=None, title_fragment=None):
        """Mark a task as done by ID or by fuzzy title match."""
        conn = self._get_conn()
        try:
            task = self._find_task(conn, user_id, task_id, title_fragment)
            if not task:
                return None
            
            conn.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task[0],))
            conn.commit()
            print(f"[TASKS] Marked task #{task[0]} ('{task[1]}') as done")
            return {"id": task[0], "title": task[1], "done": True}
        finally:
            conn.close()

    def mark_all_done(self, user_id):
        """Mark all pending tasks as done for a user. Returns count of tasks marked."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "UPDATE tasks SET done = 1 WHERE user_id = ? AND done = 0",
                (user_id,)
            )
            conn.commit()
            count = cursor.rowcount
            print(f"[TASKS] Marked ALL {count} pending tasks as done for user {user_id}")
            return count
        finally:
            conn.close()

    def delete_task(self, user_id, task_id=None, title_fragment=None):
        """Delete a task by ID or by fuzzy title match."""
        conn = self._get_conn()
        try:
            task = self._find_task(conn, user_id, task_id, title_fragment)
            if not task:
                return None
            
            conn.execute("DELETE FROM tasks WHERE id = ?", (task[0],))
            conn.commit()
            print(f"[TASKS] Deleted task #{task[0]} ('{task[1]}')")
            return {"id": task[0], "title": task[1], "deleted": True}
        finally:
            conn.close()

    def update_task(self, user_id, task_id=None, title_fragment=None, new_title=None, new_deadline=None):
        """Update a task's title or deadline."""
        conn = self._get_conn()
        try:
            task = self._find_task(conn, user_id, task_id, title_fragment)
            if not task:
                return None
            
            updates = []
            params = []
            if new_title:
                updates.append("title = ?")
                params.append(new_title)
            if new_deadline:
                updates.append("deadline = ?")
                params.append(new_deadline)
            
            if not updates:
                return {"id": task[0], "title": task[1], "message": "Nothing to update"}
            
            params.append(task[0])
            conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            
            updated_title = new_title or task[1]
            print(f"[TASKS] Updated task #{task[0]} -> '{updated_title}'")
            return {"id": task[0], "title": updated_title, "deadline": new_deadline or task[2], "updated": True}
        finally:
            conn.close()

    def _find_task(self, conn, user_id, task_id=None, title_fragment=None):
        """Find a task by ID or fuzzy title match. Returns the raw row or None."""
        if task_id:
            row = conn.execute(
                "SELECT id, title, deadline, done FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id)
            ).fetchone()
            return row
        
        if title_fragment:
            # Fuzzy match: find tasks whose title contains the fragment
            rows = conn.execute(
                "SELECT id, title, deadline, done FROM tasks WHERE user_id = ? AND title LIKE ?",
                (user_id, f"%{title_fragment}%")
            ).fetchall()
            if rows:
                return rows[0]  # Return best (first) match
        
        return None
