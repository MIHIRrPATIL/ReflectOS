'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ── Types ───────────────────────────────────────────────────────
interface Task {
  id: number;
  title: string;
  deadline: string | null;
  done: boolean;
  created_at: string;
}

const API_BASE = 'http://localhost:5000/api/tasks';

// ── Draw-in SVG Line Animation ──────────────────────────────────
const lineVariants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: { duration: 0.6, ease: 'easeInOut' },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.3, ease: 'easeOut' },
  },
  exit: {
    opacity: 0,
    x: 20,
    transition: { duration: 0.2 },
  },
};

// ── Deadline Flag Tag ───────────────────────────────────────────
function DeadlineFlag({ deadline }: { deadline: string }) {
  const date = new Date(deadline);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  let label: string;
  if (diffHours < 0) {
    label = 'OVERDUE';
  } else if (diffHours < 24) {
    label = `${Math.ceil(diffHours)}H`;
  } else {
    const days = Math.ceil(diffHours / 24);
    label = `${days}D`;
  }

  const isUrgent = diffHours < 0 || diffHours < 6;

  return (
    <div className="flex items-center gap-1 ml-2">
      {/* 45° leader line */}
      <svg width="10" height="10" className="shrink-0">
        <motion.line
          x1="0" y1="10" x2="10" y2="0"
          stroke="rgba(255,255,255,0.3)"
          strokeWidth="1"
          variants={lineVariants}
          initial="hidden"
          animate="visible"
        />
      </svg>
      {/* Flag tag */}
      <span
        className="px-1.5 py-0.5 text-[8px] font-semibold tracking-[0.15em] uppercase"
        style={{
          border: `1px solid ${isUrgent ? 'var(--hud-warning)' : 'var(--hud-line-dim)'}`,
          color: isUrgent ? 'var(--hud-warning)' : 'var(--hud-fg-dim)',
        }}
      >
        {label}
      </span>
    </div>
  );
}

// ── Main TodoPanel ──────────────────────────────────────────────
export default function TodoPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [newDeadline, setNewDeadline] = useState('');
  const [loading, setLoading] = useState(true);

  // Fetch tasks
  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/?show_done=true`);
      const contentType = res.headers.get('content-type') || '';
      if (!res.ok || !contentType.includes('application/json')) {
        console.warn('[TODO] Backend not ready or returned non-JSON');
        return;
      }
      const data = await res.json();
      setTasks(data.tasks || []);
    } catch (e) {
      // Backend not running yet — silently ignore
      console.warn('[TODO] Backend unavailable:', (e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
    // Poll every 10s for voice-added tasks
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  // Add task
  const handleAdd = async () => {
    const title = newTitle.trim();
    if (!title) return;

    try {
      await fetch(API_BASE + '/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          deadline: newDeadline || null,
        }),
      });
      setNewTitle('');
      setNewDeadline('');
      fetchTasks();
    } catch (e) {
      console.error('[TODO] Add error:', e);
    }
  };

  // Mark done
  const handleDone = async (id: number) => {
    try {
      await fetch(`${API_BASE}/${id}/done`, { method: 'PUT' });
      fetchTasks();
    } catch (e) {
      console.error('[TODO] Done error:', e);
    }
  };

  // Delete
  const handleDelete = async (id: number) => {
    try {
      await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
      fetchTasks();
    } catch (e) {
      console.error('[TODO] Delete error:', e);
    }
  };

  const pendingTasks = tasks.filter((t) => !t.done);
  const doneTasks = tasks.filter((t) => t.done);

  return (
    <div className="hud-frame relative w-[320px]">
      <div className="hud-frame-inner">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="hud-dot" />
            <span className="hud-title">TASKS</span>
          </div>
          <span className="hud-label">
            {pendingTasks.length} PENDING
          </span>
        </div>

        {/* Timeline */}
        <div className="relative ml-3">
          {/* Vertical timeline line */}
          <svg
            className="absolute left-0 top-0 h-full"
            width="2"
            style={{ overflow: 'visible' }}
          >
            <motion.line
              x1="1" y1="0" x2="1" y2="100%"
              stroke="var(--hud-line-dim)"
              strokeWidth="1"
              variants={lineVariants}
              initial="hidden"
              animate="visible"
            />
          </svg>

          {/* Task Items */}
          <div className="pl-5 space-y-1 max-h-[280px] overflow-y-auto">
            <AnimatePresence mode="popLayout">
              {loading ? (
                <motion.div
                  key="loading"
                  className="hud-label py-4"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.5 }}
                >
                  LOADING...
                </motion.div>
              ) : (
                <>
                  {pendingTasks.map((task) => (
                    <motion.div
                      key={task.id}
                      className="group relative flex items-center py-1.5"
                      variants={itemVariants}
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                      layout
                    >
                      {/* Horizontal stub */}
                      <svg
                        className="absolute -left-5"
                        width="16"
                        height="2"
                        style={{ top: '50%', transform: 'translateY(-50%)' }}
                      >
                        <motion.line
                          x1="0" y1="1" x2="16" y2="1"
                          stroke="var(--hud-line)"
                          strokeWidth="1"
                          variants={lineVariants}
                          initial="hidden"
                          animate="visible"
                        />
                      </svg>

                      {/* Hollow block (pending) — click to complete */}
                      <button
                        onClick={() => handleDone(task.id)}
                        className="shrink-0 w-3 h-3 border border-white/60 hover:bg-white/20 transition-colors cursor-pointer mr-3"
                        title="Mark as done"
                      />

                      {/* Title */}
                      <span className="text-[11px] text-white/80 flex-1 truncate">
                        {task.title}
                      </span>

                      {/* Deadline flag */}
                      {task.deadline && <DeadlineFlag deadline={task.deadline} />}

                      {/* Delete × */}
                      <button
                        onClick={() => handleDelete(task.id)}
                        className="ml-2 text-[10px] text-white/20 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                        title="Delete"
                      >
                        ×
                      </button>
                    </motion.div>
                  ))}

                  {/* Done section */}
                  {doneTasks.length > 0 && (
                    <>
                      <hr className="hud-divider my-2" />
                      <span className="hud-label text-[8px]">COMPLETED</span>
                      {doneTasks.map((task) => (
                        <motion.div
                          key={task.id}
                          className="group relative flex items-center py-1"
                          variants={itemVariants}
                          initial="hidden"
                          animate="visible"
                          exit="exit"
                          layout
                        >
                          {/* Horizontal stub */}
                          <svg
                            className="absolute -left-5"
                            width="16"
                            height="2"
                            style={{ top: '50%', transform: 'translateY(-50%)' }}
                          >
                            <line
                              x1="0" y1="1" x2="16" y2="1"
                              stroke="var(--hud-line-dim)"
                              strokeWidth="1"
                            />
                          </svg>

                          {/* Solid block (done) */}
                          <div className="shrink-0 w-3 h-3 bg-white/60 mr-3" />

                          {/* Strikethrough title */}
                          <span className="text-[11px] text-white/25 line-through flex-1 truncate">
                            {task.title}
                          </span>

                          {/* Delete × */}
                          <button
                            onClick={() => handleDelete(task.id)}
                            className="ml-2 text-[10px] text-white/20 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                            title="Delete"
                          >
                            ×
                          </button>
                        </motion.div>
                      ))}
                    </>
                  )}

                  {/* Empty state */}
                  {pendingTasks.length === 0 && doneTasks.length === 0 && (
                    <div className="hud-label py-6 text-center">
                      NO TASKS — ADD ONE BELOW
                    </div>
                  )}
                </>
              )}
            </AnimatePresence>
          </div>
        </div>

        <hr className="hud-divider mt-3 mb-2" />

        {/* Add Task Input */}
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <input
              type="text"
              className="hud-input"
              placeholder="+ ADD TASK..."
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            />
          </div>
          <input
            type="datetime-local"
            className="hud-input text-[9px] w-[130px]"
            value={newDeadline}
            onChange={(e) => setNewDeadline(e.target.value)}
            style={{ colorScheme: 'dark' }}
          />
          <button
            className="hud-btn text-[9px] px-3 py-1"
            onClick={handleAdd}
          >
            ADD
          </button>
        </div>
      </div>
    </div>
  );
}
