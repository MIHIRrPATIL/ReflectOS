'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API = 'http://localhost:5000/api/expenses';

// ── Types ───────────────────────────────────────────────────────
interface Transaction {
  id: number;
  type: 'income' | 'expense' | 'transfer';
  amount: number;
  category: string | null;
  description: string | null;
  from_account: string | null;
  to_account: string | null;
  date: string;
}

interface Debt {
  id: number;
  person: string;
  amount: number;
  direction: 'owe' | 'owed';
  description: string | null;
  settled: boolean;
  created_at: string;
}

interface Summary {
  period: string;
  days: number;
  expense_total: number;
  income_total: number;
  net: number;
  by_category: { category: string; total: number; count: number }[];
}

interface Category {
  id: number;
  name: string;
  type: 'income' | 'expense';
}

type Tab = 'transactions' | 'debts' | 'summary' | 'categories';

// ── Helpers ─────────────────────────────────────────────────────
const fmt = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 0 });

const TYPE_COLORS: Record<string, string> = {
  income: '#22c55e',
  expense: '#ef4444',
  transfer: '#eab308',
};

const TYPE_ICONS: Record<string, string> = {
  income: '↑',
  expense: '↓',
  transfer: '↔',
};

// ── Component ───────────────────────────────────────────────────
export default function ExpensePanel({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<Tab>('transactions');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{ transactions: Transaction[]; debts: Debt[] } | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  // Tab data
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [debts, setDebts] = useState<Debt[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);

  // Filters
  const [filterAccount, setFilterAccount] = useState('ALL');
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [filterDays, setFilterDays] = useState(7);
  const [summaryPeriod, setSummaryPeriod] = useState('weekly');

  // ── Data Fetching ──────────────────────────────────────────────
  const fetchTransactions = useCallback(async () => {
    try {
      let url = `${API}/recent?days=${filterDays}&limit=50`;
      if (filterAccount !== 'ALL') url += `&account=${encodeURIComponent(filterAccount)}`;
      if (filterCategory !== 'ALL') url += `&category=${encodeURIComponent(filterCategory)}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setTransactions(data.transactions || []);
      }
    } catch (e) { /* ignore */ }
  }, [filterDays, filterAccount, filterCategory]);

  const fetchDebts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/debts`);
      if (res.ok) {
        const data = await res.json();
        setDebts(data.debts || []);
      }
    } catch (e) { /* ignore */ }
  }, []);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${API}/summary?period=${summaryPeriod}`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch (e) { /* ignore */ }
  }, [summaryPeriod]);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API}/categories`);
      if (res.ok) {
        const data = await res.json();
        setCategories(data.categories || []);
      }
    } catch (e) { /* ignore */ }
  }, []);

  // Fetch on tab/filter change
  useEffect(() => {
    if (tab === 'transactions') fetchTransactions();
    else if (tab === 'debts') fetchDebts();
    else if (tab === 'summary') fetchSummary();
    else if (tab === 'categories') fetchCategories();
  }, [tab, fetchTransactions, fetchDebts, fetchSummary, fetchCategories]);

  // ── Global Search ──────────────────────────────────────────────
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      setIsSearching(false);
      return;
    }
    setIsSearching(true);
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/search?q=${encodeURIComponent(searchQuery)}`);
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data);
        }
      } catch (e) { /* ignore */ }
      setIsSearching(false);
    }, 300); // debounce
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // ── Keyboard close ─────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const tabs: { key: Tab; label: string }[] = [
    { key: 'transactions', label: 'TRANSACTIONS' },
    { key: 'debts', label: 'DEBTS' },
    { key: 'summary', label: 'SUMMARY' },
    { key: 'categories', label: 'CATEGORIES' },
  ];

  const accountOptions = ['ALL', 'Union Bank', 'SBI', 'Saraswat', 'Cash'];
  const categoryOptions = ['ALL', ...categories.filter(c => c.type === 'expense').map(c => c.name)];
  const dayOptions = [
    { label: '7D', value: 7 },
    { label: '30D', value: 30 },
    { label: '90D', value: 90 },
    { label: 'ALL', value: 3650 },
  ];

  // ── Render ─────────────────────────────────────────────────────
  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <motion.div
        className="relative w-[90vw] max-w-[700px] max-h-[85vh] flex flex-col z-10"
        initial={{ y: 40, scale: 0.97 }}
        animate={{ y: 0, scale: 1 }}
        exit={{ y: 40, scale: 0.97 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        <div className="hud-frame p-0 overflow-hidden flex flex-col max-h-[85vh]">
          <div className="hud-frame-inner flex flex-col h-full">
            {/* ── Header ──────────────────────────────────────── */}
            <div className="px-4 pt-4 pb-2 border-b border-white/10 shrink-0">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="w-[6px] h-[6px] rounded-full bg-emerald-500" />
                  <span className="text-[11px] tracking-[0.2em] uppercase text-white/60">
                    Finance Terminal
                  </span>
                </div>
                <button
                  onClick={onClose}
                  className="text-[10px] text-white/30 hover:text-white/70 transition-colors tracking-[0.15em] uppercase"
                >
                  ✕ CLOSE
                </button>
              </div>

              {/* Search Bar */}
              <div className="relative mb-3">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="SEARCH TRANSACTIONS, DEBTS, AMOUNTS, CATEGORIES..."
                  className="w-full bg-white/5 border border-white/10 text-[11px] text-white/70 px-3 py-2 tracking-widest uppercase placeholder:text-white/20 focus:outline-none focus:border-white/25 transition-colors"
                  style={{ fontFamily: 'var(--font-mono, monospace)' }}
                />
                {isSearching && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-white/30 animate-pulse">
                    ●●●
                  </span>
                )}
              </div>

              {/* Tabs */}
              {!searchQuery && (
                <div className="flex gap-1">
                  {tabs.map((t) => (
                    <button
                      key={t.key}
                      onClick={() => setTab(t.key)}
                      className={`text-[9px] tracking-[0.15em] px-3 py-1.5 transition-all uppercase ${
                        tab === t.key
                          ? 'text-white/90 border-b border-white/50'
                          : 'text-white/30 hover:text-white/60'
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* ── Content ─────────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto px-4 py-3 min-h-0" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.1) transparent' }}>
              {/* Search Results */}
              {searchQuery && searchResults ? (
                <SearchResultsView results={searchResults} />
              ) : searchQuery ? (
                <div className="text-center text-white/20 text-[10px] tracking-widest py-8">SEARCHING...</div>
              ) : (
                <>
                  {/* Transactions Tab */}
                  {tab === 'transactions' && (
                    <>
                      {/* Filters */}
                      <div className="flex items-center gap-2 mb-3 flex-wrap">
                        <FilterSelect label="ACCOUNT" value={filterAccount} options={accountOptions} onChange={setFilterAccount} />
                        <FilterSelect label="CATEGORY" value={filterCategory} options={categoryOptions} onChange={setFilterCategory} />
                        <div className="flex items-center gap-1 ml-auto">
                          {dayOptions.map((d) => (
                            <button
                              key={d.value}
                              onClick={() => setFilterDays(d.value)}
                              className={`text-[8px] px-2 py-1 tracking-wider transition-all ${
                                filterDays === d.value
                                  ? 'text-white/80 border border-white/30'
                                  : 'text-white/25 hover:text-white/50'
                              }`}
                            >
                              {d.label}
                            </button>
                          ))}
                        </div>
                      </div>
                      <TransactionList transactions={transactions} />
                    </>
                  )}

                  {/* Debts Tab */}
                  {tab === 'debts' && <DebtsList debts={debts} />}

                  {/* Summary Tab */}
                  {tab === 'summary' && (
                    <>
                      <div className="flex items-center gap-1 mb-3">
                        {['daily', 'weekly', 'monthly'].map((p) => (
                          <button
                            key={p}
                            onClick={() => setSummaryPeriod(p)}
                            className={`text-[8px] px-2 py-1 tracking-wider uppercase transition-all ${
                              summaryPeriod === p
                                ? 'text-white/80 border border-white/30'
                                : 'text-white/25 hover:text-white/50'
                            }`}
                          >
                            {p}
                          </button>
                        ))}
                      </div>
                      {summary && <SummaryView summary={summary} />}
                    </>
                  )}

                  {/* Categories Tab */}
                  {tab === 'categories' && <CategoriesView categories={categories} />}
                </>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// SUB‑COMPONENTS
// ═══════════════════════════════════════════════════════════════════

function FilterSelect({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      <span className="text-[7px] text-white/20 tracking-widest">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-white/5 border border-white/10 text-[9px] text-white/60 px-2 py-1 tracking-wider uppercase appearance-none cursor-pointer focus:outline-none"
        style={{ fontFamily: 'var(--font-mono, monospace)' }}
      >
        {options.map((o) => (
          <option key={o} value={o} className="bg-black text-white">{o}</option>
        ))}
      </select>
    </div>
  );
}

function TransactionList({ transactions }: { transactions: Transaction[] }) {
  if (transactions.length === 0) {
    return (
      <div className="text-center text-white/15 text-[10px] tracking-widest py-10 uppercase">
        No transactions found
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5">
      {transactions.map((tx, i) => (
        <motion.div
          key={tx.id}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.02 }}
          className="flex items-center gap-2 py-1.5 border-b border-white/5 last:border-0"
        >
          {/* Date */}
          <span className="text-[9px] text-white/25 w-[60px] shrink-0 tabular-nums"
            style={{ fontFamily: 'var(--font-mono, monospace)' }}>
            {tx.date.slice(5)}
          </span>

          {/* Type icon */}
          <span
            className="text-[12px] w-[18px] text-center shrink-0"
            style={{ color: TYPE_COLORS[tx.type] }}
          >
            {TYPE_ICONS[tx.type]}
          </span>

          {/* Amount */}
          <span
            className="text-[11px] w-[70px] text-right shrink-0 tabular-nums tracking-wider"
            style={{ fontFamily: 'var(--font-mono, monospace)', color: TYPE_COLORS[tx.type] }}
          >
            ₹{fmt(tx.amount)}
          </span>

          {/* Category */}
          {tx.category && (
            <span className="text-[8px] text-white/40 border border-white/10 px-1.5 py-0.5 shrink-0 uppercase tracking-wider">
              {tx.category}
            </span>
          )}

          {/* Description + Account */}
          <span className="text-[9px] text-white/35 truncate flex-1">
            {tx.type === 'transfer'
              ? `${tx.from_account} → ${tx.to_account}`
              : tx.description || ''}
          </span>

          {tx.type !== 'transfer' && tx.from_account && (
            <span className="text-[8px] text-white/20 shrink-0">
              {tx.from_account}
            </span>
          )}
        </motion.div>
      ))}
    </div>
  );
}

function DebtsList({ debts }: { debts: Debt[] }) {
  const owedToMe = debts.filter((d) => d.direction === 'owed');
  const iOwe = debts.filter((d) => d.direction === 'owe');

  if (debts.length === 0) {
    return (
      <div className="text-center text-white/15 text-[10px] tracking-widest py-10 uppercase">
        No outstanding debts
      </div>
    );
  }

  const renderDebt = (d: Debt, i: number) => (
    <motion.div
      key={d.id}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.03 }}
      className="flex items-center gap-2 py-1.5 border-b border-white/5 last:border-0"
    >
      <span
        className="text-[11px] w-[80px] text-right shrink-0 tabular-nums tracking-wider"
        style={{
          fontFamily: 'var(--font-mono, monospace)',
          color: d.direction === 'owed' ? '#22c55e' : '#ef4444',
        }}
      >
        ₹{fmt(d.amount)}
      </span>
      <span className="text-[10px] text-white/60 shrink-0">{d.person}</span>
      {d.description && (
        <span className="text-[9px] text-white/25 truncate flex-1">— {d.description}</span>
      )}
    </motion.div>
  );

  return (
    <div className="flex flex-col gap-4">
      {owedToMe.length > 0 && (
        <div>
          <span className="text-[8px] tracking-[0.2em] uppercase" style={{ color: '#22c55e99' }}>
            They owe you
          </span>
          <div className="mt-1">{owedToMe.map(renderDebt)}</div>
          <div className="mt-1 text-right text-[10px] tabular-nums" style={{ fontFamily: 'var(--font-mono, monospace)', color: '#22c55eaa' }}>
            Total: ₹{fmt(owedToMe.reduce((s, d) => s + d.amount, 0))}
          </div>
        </div>
      )}
      {iOwe.length > 0 && (
        <div>
          <span className="text-[8px] tracking-[0.2em] uppercase" style={{ color: '#ef444499' }}>
            You owe
          </span>
          <div className="mt-1">{iOwe.map(renderDebt)}</div>
          <div className="mt-1 text-right text-[10px] tabular-nums" style={{ fontFamily: 'var(--font-mono, monospace)', color: '#ef4444aa' }}>
            Total: ₹{fmt(iOwe.reduce((s, d) => s + d.amount, 0))}
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryView({ summary }: { summary: Summary }) {
  const maxCat = Math.max(...summary.by_category.map((c) => c.total), 1);

  return (
    <div className="space-y-4">
      {/* Totals */}
      <div className="grid grid-cols-3 gap-3">
        <div className="text-center">
          <div className="text-[8px] text-white/25 tracking-widest uppercase mb-1">Income</div>
          <div className="text-[14px] tabular-nums" style={{ fontFamily: 'var(--font-mono, monospace)', color: '#22c55e' }}>
            ₹{fmt(summary.income_total)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-[8px] text-white/25 tracking-widest uppercase mb-1">Expenses</div>
          <div className="text-[14px] tabular-nums" style={{ fontFamily: 'var(--font-mono, monospace)', color: '#ef4444' }}>
            ₹{fmt(summary.expense_total)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-[8px] text-white/25 tracking-widest uppercase mb-1">Net</div>
          <div
            className="text-[14px] tabular-nums"
            style={{
              fontFamily: 'var(--font-mono, monospace)',
              color: summary.net >= 0 ? '#22c55e' : '#ef4444',
            }}
          >
            {summary.net >= 0 ? '+' : ''}₹{fmt(summary.net)}
          </div>
        </div>
      </div>

      {/* Category Breakdown */}
      {summary.by_category.length > 0 && (
        <div>
          <div className="text-[8px] text-white/20 tracking-[0.2em] uppercase mb-2">
            Spending Breakdown
          </div>
          <div className="flex flex-col gap-2">
            {summary.by_category.map((c, i) => (
              <motion.div
                key={c.category}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[9px] text-white/50 uppercase tracking-wider">
                    {c.category}
                  </span>
                  <span className="text-[10px] text-white/40 tabular-nums" style={{ fontFamily: 'var(--font-mono, monospace)' }}>
                    ₹{fmt(c.total)} ({c.count})
                  </span>
                </div>
                <div className="h-[3px] bg-white/5 w-full">
                  <motion.div
                    className="h-full"
                    style={{ backgroundColor: '#ef4444' }}
                    initial={{ width: 0 }}
                    animate={{ width: `${(c.total / maxCat) * 100}%` }}
                    transition={{ delay: i * 0.04 + 0.1, duration: 0.4 }}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {summary.by_category.length === 0 && (
        <div className="text-center text-white/15 text-[10px] tracking-widest py-6 uppercase">
          No expenses recorded for this period
        </div>
      )}
    </div>
  );
}

function CategoriesView({ categories }: { categories: Category[] }) {
  const expenseCats = categories.filter((c) => c.type === 'expense');
  const incomeCats = categories.filter((c) => c.type === 'income');

  const renderGroup = (title: string, cats: Category[], color: string) => (
    <div>
      <span className="text-[8px] tracking-[0.2em] uppercase" style={{ color }}>
        {title}
      </span>
      <div className="flex flex-wrap gap-1.5 mt-2">
        {cats.map((c) => (
          <span
            key={c.id}
            className="text-[9px] text-white/50 border border-white/10 px-2 py-1 uppercase tracking-wider"
          >
            {c.name}
          </span>
        ))}
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      {renderGroup('Expense Categories', expenseCats, '#ef444480')}
      {renderGroup('Income Categories', incomeCats, '#22c55e80')}
    </div>
  );
}

function SearchResultsView({ results }: { results: { transactions: Transaction[]; debts: Debt[] } }) {
  const total = results.transactions.length + results.debts.length;

  if (total === 0) {
    return (
      <div className="text-center text-white/15 text-[10px] tracking-widest py-10 uppercase">
        No results found
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-[8px] text-white/25 tracking-widest">
        {total} RESULT{total !== 1 ? 'S' : ''} FOUND
      </div>

      {results.transactions.length > 0 && (
        <div>
          <span className="text-[8px] text-white/30 tracking-[0.2em] uppercase mb-1 block">
            Transactions ({results.transactions.length})
          </span>
          <TransactionList transactions={results.transactions} />
        </div>
      )}

      {results.debts.length > 0 && (
        <div>
          <span className="text-[8px] text-white/30 tracking-[0.2em] uppercase mb-1 block">
            Debts ({results.debts.length})
          </span>
          <DebtsList debts={results.debts} />
        </div>
      )}
    </div>
  );
}
