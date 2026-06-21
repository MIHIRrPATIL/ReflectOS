"use client";

import { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useHUD } from "@/context/HUDContext";
import VoiceAssistant from "@/components/VoiceAssistant";
import TodoPanel from "@/components/TodoPanel";
import AccountBalances from "@/components/AccountBalances";

function useDigitalClock() {
  const [mounted, setMounted] = useState(false);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    setMounted(true);
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  if (!mounted) return { day: '--', date: '--', time: '--:--:--' };

  const day = now.toLocaleDateString('en-US', { weekday: 'long' }).toUpperCase();
  const date = now.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();
  const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

  return { day, date, time };
}

export default function Home() {
  const { day, date, time } = useDigitalClock();
  const hud = useHUD();
  const zenMode = hud?.zenMode ?? false;
  console.log("[HOME] HUD State:", { zenMode, hudExists: !!hud });

  return (
    <main className="relative w-screen h-screen overflow-hidden">
      {/* ── Top-Left: System Label ────────────────────────────── */}
      <div className="fixed top-6 left-6 z-10">
        <div className="hud-label text-[8px] mb-1">SYS.01</div>
        <div className="hud-title text-[14px] tracking-[0.3em]">REFLECTOS</div>
        <div className="mt-2 flex items-center gap-2">
          <span className="hud-dot hud-dot--success" />
          <span className="hud-label">ONLINE</span>
        </div>
      </div>

      {/* ── Top-Right: TODO Panel ────────────────────────────── */}
      <AnimatePresence>
        {!zenMode && (
          <motion.div 
            className="fixed top-6 right-6 z-10 fade-in"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
          >
            <TodoPanel />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Center: Voice Agent (large, prominent) ───────────── */}
      <div className="fixed inset-0 flex items-center justify-center z-20 pointer-events-none">
        <div className="pointer-events-auto">
          <VoiceAssistant />
        </div>
      </div>

      {/* ── Center Background: Decorative Reticle ────────────── */}
      <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-0">
        <svg width="200" height="200" opacity="0.04">
          {/* Crosshair lines */}
          <line x1="100" y1="0" x2="100" y2="80" stroke="white" strokeWidth="1" />
          <line x1="100" y1="120" x2="100" y2="200" stroke="white" strokeWidth="1" />
          <line x1="0" y1="100" x2="80" y2="100" stroke="white" strokeWidth="1" />
          <line x1="120" y1="100" x2="200" y2="100" stroke="white" strokeWidth="1" />
          {/* Inner circle */}
          <circle cx="100" cy="100" r="25" fill="none" stroke="white" strokeWidth="1" />
          {/* Outer dashed circle  */}
          <circle cx="100" cy="100" r="60" fill="none" stroke="white" strokeWidth="1" strokeDasharray="4 4" />
          {/* Corner brackets */}
          <path d="M30,30 L30,45 M30,30 L45,30" stroke="white" strokeWidth="1" />
          <path d="M170,30 L170,45 M170,30 L155,30" stroke="white" strokeWidth="1" />
          <path d="M30,170 L30,155 M30,170 L45,170" stroke="white" strokeWidth="1" />
          <path d="M170,170 L170,155 M170,170 L155,170" stroke="white" strokeWidth="1" />
        </svg>
      </div>

      {/* ── Bottom-Center: Digital Clock ──────────────────────── */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-10">
        <div className="flex flex-col items-center gap-0.5">
          <div className="text-[36px] font-light tracking-[0.15em] text-white/70 tabular-nums" style={{ fontFamily: 'var(--font-mono, monospace)' }}>
            {time}
          </div>
          <div className="flex items-center gap-3">
            <span className="hud-label text-[8px]">{day}</span>
            <span className="w-[3px] h-[3px] rounded-full bg-white/20" />
            <span className="hud-label text-[8px]">{date}</span>
          </div>
        </div>
      </div>

      {/* ── Left-Middle: Account Balances ────────────────────────── */}
      <AnimatePresence>
        {!zenMode && (
          <motion.div 
            className="fixed left-6 top-1/2 -translate-y-1/2 z-10 fade-in"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            <AccountBalances />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Bottom-Right: System Stats ────────────────────────── */}
      <AnimatePresence>
        {!zenMode && (
          <motion.div 
            className="fixed bottom-6 right-6 z-10"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
          >
            <div className="flex items-center gap-4">
              <div className="text-right">
                <span className="hud-label text-[7px] block">MODULES</span>
                <span className="text-[11px] text-white/40">5 ACTIVE</span>
              </div>
              <div className="text-right">
                <span className="hud-label text-[7px] block">STATUS</span>
                <span className="text-[11px] text-white/40">NOMINAL</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
