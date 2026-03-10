'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const API = 'http://localhost:5000/api/expenses';

interface Account {
  id: number;
  name: string;
  type: string;
  balance: number;
}

export default function AccountBalances() {
  const [accounts, setAccounts] = useState<Account[]>([]);

  useEffect(() => {
    const fetchBalances = async () => {
      try {
        const res = await fetch(`${API}/balances`);
        if (res.ok) {
          const data = await res.json();
          setAccounts(data.accounts || []);
        }
      } catch (e) { /* backend may be down */ }
    };
    fetchBalances();
    const id = setInterval(fetchBalances, 30000);
    return () => clearInterval(id);
  }, []);

  const total = accounts.reduce((s, a) => s + a.balance, 0);

  const fmt = (n: number) =>
    n.toLocaleString('en-IN', { maximumFractionDigits: 0 });

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.4, duration: 0.5 }}
    >
      <div className="hud-frame p-3 w-[220px]">
        <div className="hud-frame-inner">
          <span className="hud-label block mb-2 text-[8px]">ACCOUNTS</span>
          <div className="flex flex-col gap-1.5">
            {accounts.map((a) => (
              <div key={a.id} className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-[5px] h-[5px] rounded-full ${
                      a.balance >= 0 ? 'bg-emerald-500' : 'bg-red-500'
                    }`}
                  />
                  <span className="text-[10px] text-white/50 uppercase tracking-widest">
                    {a.name}
                  </span>
                </div>
                <span
                  className="text-[11px] tabular-nums tracking-wider"
                  style={{
                    fontFamily: 'var(--font-mono, monospace)',
                    color: a.balance >= 0 ? 'rgba(255,255,255,0.6)' : 'rgba(239,68,68,0.8)',
                  }}
                >
                  ₹{fmt(a.balance)}
                </span>
              </div>
            ))}
          </div>

          {accounts.length > 0 && (
            <>
              <div className="border-t border-white/10 mt-2 pt-1.5 flex items-center justify-between">
                <span className="text-[9px] text-white/30 uppercase tracking-[0.15em]">
                  Total
                </span>
                <span
                  className="text-[12px] tabular-nums tracking-wider text-white/70"
                  style={{ fontFamily: 'var(--font-mono, monospace)' }}
                >
                  ₹{fmt(total)}
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}
