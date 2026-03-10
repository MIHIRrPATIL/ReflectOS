"use client";

import React, { useState, useEffect, useRef } from "react";
import GestureCamera from "./GestureCamera";
import Webcam from "react-webcam";
import { GestureSocket } from "../lib/gesture-engine/GestureSocket";
import { motion, AnimatePresence } from "framer-motion";
import ExpensePanel from "./ExpensePanel";

export default function GestureFeedback() {
  const [lastGesture, setLastGesture] = useState<string | null>(null);
  const [webcam, setWebcam] = useState<Webcam | null>(null);
  
  // Volume State
  const [volume, setVolume] = useState(0);
  const [showVolume, setShowVolume] = useState(false);
  const volumeTimer = useRef<NodeJS.Timeout | null>(null);

  // Menu State
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(2); 
  const [confirmedItem, setConfirmedItem] = useState<number | null>(null);

  const menuItems = ["VISION", "OCR", "HOME", "SPOTIFY", "FINANCE"];
  
  // Finance panel state
  const [financePanelOpen, setFinancePanelOpen] = useState(false);
  
  // AI Feedback State
  const [aiResults, setAiResults] = useState<any>(null);
  const [showCaptureFlash, setShowCaptureFlash] = useState(false);
  const aiResultTimer = useRef<NodeJS.Timeout | null>(null);

  // Spotify State (persistent from socket responses)
  const [spotifyStatus, setSpotifyStatus] = useState<any>(null);

  // Gesture lock state (locked during mode switch)
  const [gestureLocked, setGestureLocked] = useState(false);

  // Camera expanded state (Spread Zoom)
  const [cameraExpanded, setCameraExpanded] = useState(false);

  // Cursor Mode State
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 }); // Pixels
  const smoothedPos = useRef({ x: 0.5, y: 0.5 }); // Normalized [0,1]
  const [cursorVisible, setCursorVisible] = useState(false);
  const [isHoveringClickable, setIsHoveringClickable] = useState(false);
  const [lastClickTime, setLastClickTime] = useState(0);
  const cursorTimer = useRef<NodeJS.Timeout | null>(null);

  const ALPHA = 0.25; // EMA Smoothing factor (lower = smoother/slower, higher = snappier)

  const checkClickable = (x: number, y: number) => {
    try {
        const elem = document.elementFromPoint(x, y);
        if (!elem) return false;
        const style = window.getComputedStyle(elem);
        return (
            elem.tagName === 'BUTTON' || 
            elem.tagName === 'A' || 
            style.cursor === 'pointer' ||
            !!elem.closest('button') || 
            !!elem.closest('a')
        );
    } catch (e) {
        return false;
    }
  };

  useEffect(() => {
    const socket = GestureSocket.getInstance().getSocket();
    if (!socket) return;
    
    const handleMessage = (msg: any) => {
        if (msg.type === "VISION_CAPTURE") {
            setShowCaptureFlash(true);
            setTimeout(() => setShowCaptureFlash(false), 800);
            return;
        }

        if (msg.type !== "RESPONSE") return;
        
        const data = msg.payload;
        if (data.tool_outputs) {
            setAiResults(data.tool_outputs);
            if (aiResultTimer.current) clearTimeout(aiResultTimer.current);
            aiResultTimer.current = setTimeout(() => setAiResults(null), 10000);

            // Persist Spotify status
            if (data.tool_outputs.spotify_status) {
                setSpotifyStatus(data.tool_outputs.spotify_status);
            }
            if (data.tool_outputs.spotify_playback?.success) {
                // Refetch status via REST (avoids re-entering AI pipeline)
                setTimeout(async () => {
                    try {
                        const res = await fetch('http://localhost:5000/api/spotify/status');
                        const ct = res.headers.get('content-type') || '';
                        if (res.ok && ct.includes('application/json')) {
                            const data = await res.json();
                            if (data.is_playing || data.track) setSpotifyStatus(data);
                        }
                    } catch (e) { /* ignore */ }
                }, 2000);
            }
        }
    };
    
    socket.on('message', handleMessage);
    return () => { socket.off('message', handleMessage); };
  }, []);

  // Poll Spotify status via REST (passive, no AI pipeline)
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('http://localhost:5000/api/spotify/status');
        const ct = res.headers.get('content-type') || '';
        if (res.ok && ct.includes('application/json')) {
          const data = await res.json();
          if (data.is_playing || data.track) {
            setSpotifyStatus(data);
          }
        }
      } catch (e) {
        // Backend not ready
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleGesture = (gesture: string) => {
    // MODE SWITCH: Toggle gesture lock
    if (gesture === "MODE_SWITCH") {
        setGestureLocked(prev => !prev);
        setLastGesture(gestureLocked ? "MODE: UNLOCKED" : "MODE: LOCKED");
        setTimeout(() => setLastGesture(null), 1500);
        return; // Don't process further
    }

    // If gestures are locked, only allow unlock via MODE_SWITCH (handled above)
    if (gestureLocked) return;

    // Skip debug toast for high-frequency cursor/volume events to prevent infinite loops
    if (!gesture.startsWith("CURSOR_") && !gesture.startsWith("VOLUME:")) {
        setLastGesture(gesture);
        setTimeout(() => setLastGesture(null), 1500);
    }

    // FIST / CLOSE = INTERRUPT ALL
    if (gesture === "GESTURE_CLOSE" || gesture === "FIST_MOVE") {
        GestureSocket.getInstance().sendInterrupt();
        setMenuOpen(false);
        setConfirmedItem(null);
        setAiResults(null);
        setShowVolume(false);
        setCameraExpanded(false);
        return;
    }

  // SPREAD ZOOM = Toggle camera fullscreen
    if (gesture === "SPREAD_ZOOM") {
        setCameraExpanded(prev => !prev);
        return;
    }

    // CURSOR HANDLER
    if (gesture.startsWith("CURSOR_MOVE:")) {
        const [xRaw, yRaw] = gesture.split(":")[1].split(",");
        let targetX = 1 - parseFloat(xRaw); // Invert X for mirrored camera
        let targetY = parseFloat(yRaw);

        // Scaling for full-screen reach
        const scale = 1.5;
        targetX = 0.5 + (targetX - 0.5) * scale;
        targetY = 0.5 + (targetY - 0.5) * scale;

        // Clamp to [0, 1]
        targetX = Math.max(0, Math.min(1, targetX));
        targetY = Math.max(0, Math.min(1, targetY));

        // APPLY EMA SMOOTHING
        smoothedPos.current = {
            x: smoothedPos.current.x + ALPHA * (targetX - smoothedPos.current.x),
            y: smoothedPos.current.y + ALPHA * (targetY - smoothedPos.current.y)
        };

        const screenX = smoothedPos.current.x * window.innerWidth;
        const screenY = smoothedPos.current.y * window.innerHeight;

        setCursorPos({ x: screenX, y: screenY });
        
        // Update clickable hover state (Throttled if needed, but here fine)
        setIsHoveringClickable(checkClickable(screenX, screenY));

        setCursorVisible(true);
        if (cursorTimer.current) clearTimeout(cursorTimer.current);
        cursorTimer.current = setTimeout(() => {
            setCursorVisible(false);
            setIsHoveringClickable(false);
        }, 5000);
        return;
    }

    if (gesture.startsWith("CURSOR_CLICK:")) {
        // Use the current SMOOTHED coordinates instead of raw ones from the event
        // This ensures the click happens exactly where the user sees the cursor
        const screenX = smoothedPos.current.x * window.innerWidth;
        const screenY = smoothedPos.current.y * window.innerHeight;
        
        // Visual feedback for click
        setLastClickTime(Date.now());
        
        // Native Click Simulation
        let targetElem = document.elementFromPoint(screenX, screenY) as HTMLElement | null;
        
        if (targetElem) {
            // 1. Find the closest interactive ancestor if the target itself isn't one
            const interactive = targetElem.closest('button, a, [role="button"], input, select, textarea') as HTMLElement | null;
            if (interactive) targetElem = interactive;

            console.log("[CURSOR] Clicking element:", targetElem);
            
            // 2. Dispatch a sequence of events for maximum compatibility
            const eventTypes = ["pointerdown", "mousedown", "pointerup", "mouseup", "click"];
            
            eventTypes.forEach(evtType => {
                const isClick = evtType === "click";
                const EventClass = evtType.startsWith("pointer") ? PointerEvent : MouseEvent;
                
                const evt = new EventClass(evtType, {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: screenX,
                    clientY: screenY,
                    button: 0,
                    buttons: isClick ? 0 : 1,
                    pointerId: 1, // For PointerEvents
                    isPrimary: true
                });
                targetElem?.dispatchEvent(evt);
            });

            // 3. Fallback: Force focus if it's an input-like element
            if (["INPUT", "TEXTAREA", "SELECT"].includes(targetElem.tagName)) {
                targetElem.focus();
            }
        }
        return;
    }

    // SWIPE LEFT = Previous song (direct REST, bypasses AI pipeline)
    if (gesture === "SWIPE_LEFT") {
        fetch('http://localhost:5000/api/spotify/previous', { method: 'POST' })
            .then(() => setTimeout(async () => {
                try {
                    const res = await fetch('http://localhost:5000/api/spotify/status');
                    if (res.ok) { const d = await res.json(); if (d.track) setSpotifyStatus(d); }
                } catch (e) { /* ignore */ }
            }, 500))
            .catch(e => console.error('[SPOTIFY] Previous error:', e));
        return;
    }

    // SWIPE RIGHT = Next song (direct REST, bypasses AI pipeline)
    if (gesture === "SWIPE_RIGHT") {
        fetch('http://localhost:5000/api/spotify/next', { method: 'POST' })
            .then(() => setTimeout(async () => {
                try {
                    const res = await fetch('http://localhost:5000/api/spotify/status');
                    if (res.ok) { const d = await res.json(); if (d.track) setSpotifyStatus(d); }
                } catch (e) { /* ignore */ }
            }, 500))
            .catch(e => console.error('[SPOTIFY] Next error:', e));
        return;
    }

    // VOLUME HANDLER
    if (gesture.startsWith("VOLUME:")) {
        const val = parseInt(gesture.split(":")[1]);
        setVolume(val);
        setShowVolume(true);
        if (volumeTimer.current) clearTimeout(volumeTimer.current);
        volumeTimer.current = setTimeout(() => setShowVolume(false), 2000);
    }

    // MENU HANDLER
    if (gesture === "GESTURE_CLOSE" || gesture === "MENU_CLOSE") {
        setMenuOpen(false);
        setConfirmedItem(null);
    }
    if (gesture === "MENU_OPEN") {
        setMenuOpen(true);
        setConfirmedItem(null);
    }
    if (gesture.startsWith("MENU_WHEEL_")) {
        if (menuOpen) {
            const idx = parseInt(gesture.split("_").pop() || "2");
            setSelectedItem(idx);
        }
    }
    if (gesture === "MENU_SELECT") {
        if (menuOpen && confirmedItem === null) {
            setAiResults(null);
            const item = menuItems[selectedItem];
            setConfirmedItem(selectedItem);
            
            let screenshot = null;
            if ((item === "VISION" || item === "OCR") && webcam) {
                screenshot = webcam.getScreenshot();
            }

            // Route actions properly locally if needed, or send to backend
            if (item === "FINANCE") {
                setFinancePanelOpen(true);
            } else if (item === "SPOTIFY") {
                GestureSocket.getInstance().sendVoiceCommand("play some music", {});
            } else {
                GestureSocket.getInstance().sendMenuAction(item, {
                    image: screenshot
                });
            }

            setTimeout(() => {
                setMenuOpen(false);
                setConfirmedItem(null);
            }, 600);
        }
    }
  };

  // Spotify playback control via direct REST (bypasses AI pipeline)
  const spotifyControl = async (action: string) => {
    const actionMap: Record<string, string> = {
      'previous song': '/api/spotify/previous',
      'pause music': '/api/spotify/pause',
      'next song': '/api/spotify/next',
    };
    const endpoint = actionMap[action];
    if (endpoint) {
      try {
        await fetch(`http://localhost:5000${endpoint}`, { method: 'POST' });
        // Refresh status after action
        setTimeout(async () => {
          try {
            const res = await fetch('http://localhost:5000/api/spotify/status');
            if (res.ok) { const d = await res.json(); if (d.track) setSpotifyStatus(d); }
          } catch (e) { /* ignore */ }
        }, 500);
      } catch (e) {
        console.error('[SPOTIFY] Control error:', e);
      }
    } else {
      // Fallback to AI pipeline for complex commands like "play some music"
      GestureSocket.getInstance().sendVoiceCommand(action, {});
    }
  };

  return (
    <>
      {/* Camera - animated expand/collapse */}
      <motion.div
        layout
        transition={{ type: 'spring', stiffness: 200, damping: 28, mass: 0.8 }}
        className={cameraExpanded
          ? 'fixed inset-4 z-30 rounded-lg overflow-hidden'
          : ''
        }
      >
        <GestureCamera
          onGesture={handleGesture}
          onReady={(inst) => setWebcam(inst)}
          expanded={cameraExpanded}
        />
      </motion.div>
      
      {/* ── DEBUG TOAST (HUD styled) ──────────────────────────── */}
      <AnimatePresence>
        {lastGesture && (
          <motion.div
            className="fixed top-6 left-1/2 -translate-x-1/2 z-50"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <div className="hud-frame px-4 py-2">
              <div className="hud-frame-inner flex items-center gap-2">
                <span className="hud-dot hud-dot--success" />
                <span className="text-[12px] tracking-[0.15em] uppercase">
                  {lastGesture}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── VOLUME DIAL (HUD styled) ──────────────────────────── */}
      <AnimatePresence>
        {showVolume && (
          <motion.div
            className="fixed top-1/2 right-8 -translate-y-1/2 pointer-events-none z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="relative w-48 h-48 flex items-center justify-center">
              <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
                {/* Background circle - dashed */}
                <circle
                  cx="50" cy="50" r="42"
                  fill="none"
                  stroke="var(--hud-line-dim)"
                  strokeWidth="1"
                  strokeDasharray="2 4"
                />
                {/* Volume arc - solid */}
                <circle
                  cx="50" cy="50" r="42"
                  fill="none"
                  stroke="var(--hud-fg)"
                  strokeWidth="1"
                  strokeDasharray="264"
                  strokeDashoffset={264 - (264 * volume) / 100}
                  strokeLinecap="butt"
                  className="transition-[stroke-dashoffset] duration-100 ease-linear"
                />
                {/* Tick marks every 10% */}
                {Array.from({ length: 10 }).map((_, i) => {
                  const angle = (i / 10) * 360;
                  const rad = (angle - 90) * (Math.PI / 180);
                  const x1 = 50 + 38 * Math.cos(rad);
                  const y1 = 50 + 38 * Math.sin(rad);
                  const x2 = 50 + 35 * Math.cos(rad);
                  const y2 = 50 + 35 * Math.sin(rad);
                  return (
                    <line
                      key={i}
                      x1={x1} y1={y1} x2={x2} y2={y2}
                      stroke="var(--hud-line-dim)"
                      strokeWidth="1"
                    />
                  );
                })}
              </svg>
              <div className="text-center">
                <div className="text-4xl font-light tracking-wider">{volume}</div>
                <div className="hud-label text-[9px] mt-1">VOLUME</div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── CAPTURE FLASH ─────────────────────────────────────── */}
      <AnimatePresence>
        {showCaptureFlash && (
          <motion.div
            className="fixed inset-0 flex items-center justify-center pointer-events-none z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="hud-frame px-6 py-3">
              <div className="hud-frame-inner flex items-center gap-3">
                <span className="hud-dot" />
                <span className="hud-title text-[11px]">CAPTURED</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── AI RESULTS OVERLAY (HUD styled) ───────────────────── */}
      <AnimatePresence>
        {aiResults && (
          <motion.div
            className="fixed top-20 left-1/2 -translate-x-1/2 z-40 max-w-xl w-full px-4"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <div className="hud-frame p-4">
              <div className="hud-frame-inner">
                {aiResults?.object_detection && (
                  <div>
                    <span className="hud-label">SCENE ANALYSIS</span>
                    {aiResults.object_detection.description && (
                      <p className="text-[15px] text-white/85 mt-2 leading-relaxed">
                        {aiResults.object_detection.description}
                      </p>
                    )}
                    {aiResults.object_detection.objects?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {aiResults.object_detection.objects.map((obj: any, i: number) => (
                          <span key={i} className="text-[12px] text-white/70 border border-white/15 px-2 py-0.5">
                            {obj.label} {Math.round(obj.confidence * 100)}%
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {aiResults?.ocr && (
                  <div className={aiResults.object_detection ? "mt-3 pt-3 border-t border-white/10" : ""}>
                    <span className="hud-label">TEXT SCAN</span>
                    <p className="text-[15px] text-white/85 mt-1 border-l border-white/25 pl-3">
                      {aiResults.ocr.cleaned_text || aiResults.ocr.raw_text || aiResults.ocr.text}
                    </p>
                  </div>
                )}
                {aiResults?.outfit_analysis && (
                  <div className={aiResults.object_detection || aiResults.ocr ? "mt-3 pt-3 border-t border-white/10" : ""}>
                    <span className="hud-label">STYLE SCAN</span>
                    <p className="text-[15px] text-white/85 mt-1">{aiResults.outfit_analysis.suggestions}</p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── SPOTIFY NOW PLAYING (bottom-left, ALWAYS visible) ──── */}
      <div className="fixed bottom-6 left-6 z-30">
        <div className="hud-frame p-3 w-[260px]">
          <div className="hud-frame-inner">
            <span className="hud-label block mb-2">
              <span
                className={`inline-block w-[5px] h-[5px] rounded-full mr-1 ${
                  spotifyStatus?.is_playing ? 'bg-green-500' : 'bg-white/20'
                }`}
              />
              {spotifyStatus?.is_playing ? 'NOW PLAYING' : 'SPOTIFY'}
            </span>

            {spotifyStatus?.is_playing ? (
              <>
                <div className="flex items-center gap-3">
                  {spotifyStatus.image && (
                    <img
                      src={spotifyStatus.image}
                      alt="Album"
                      className="w-10 h-10 object-cover"
                      style={{ border: '1px solid var(--hud-line-dim)' }}
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-[14px] text-white/90 truncate font-medium">
                      {spotifyStatus.track}
                    </div>
                    <div className="text-[11px] text-white/50 truncate">
                      {spotifyStatus.artist}
                    </div>
                  </div>
                </div>

                {spotifyStatus.duration_ms > 0 && (
                  <div className="mt-2 h-px bg-white/10 w-full">
                    <div
                      className="h-full bg-white/50"
                      style={{
                        width: `${(spotifyStatus.progress_ms / spotifyStatus.duration_ms) * 100}%`,
                      }}
                    />
                  </div>
                )}

                <div className="flex items-center justify-center gap-4 mt-2">
                  <button
                    onClick={() => spotifyControl('previous song')}
                    className="text-[10px] text-white/30 hover:text-white/80 transition-colors cursor-pointer tracking-widest"
                  >
                    ◁◁
                  </button>
                  <button
                    onClick={() => spotifyControl('pause music')}
                    className="w-6 h-6 border border-white/30 hover:border-white/80 flex items-center justify-center transition-colors cursor-pointer"
                  >
                    <span className="text-[8px]">▮▮</span>
                  </button>
                  <button
                    onClick={() => spotifyControl('next song')}
                    className="text-[10px] text-white/30 hover:text-white/80 transition-colors cursor-pointer tracking-widest"
                  >
                    ▷▷
                  </button>
                </div>

                <div className="mt-1.5 text-[7px] text-white/20 text-center tracking-[0.2em] uppercase">
                  {spotifyStatus.device || 'DEVICE'}
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center py-3 gap-2">
                <svg width="24" height="24" viewBox="0 0 18 18" fill="none" opacity="0.3">
                  <circle cx="9" cy="9" r="7" stroke="white" strokeWidth="1" />
                  <path d="M5 7C7 6 11 6 13 7" stroke="white" strokeWidth="1" />
                  <path d="M6 10C7.5 9 10.5 9 12 10" stroke="white" strokeWidth="1" />
                  <path d="M7 13C8 12.5 10 12.5 11 13" stroke="white" strokeWidth="1" />
                </svg>
                <span className="text-[9px] text-white/20 tracking-[0.15em] uppercase">
                  NO ACTIVE PLAYBACK
                </span>
                <button
                  onClick={() => spotifyControl('play some music')}
                  className="hud-btn text-[8px] px-3 py-1 mt-1"
                >
                  PLAY
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── MENU ARC (HUD styled) ─────────────────────────────── */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            className="fixed bottom-0 left-0 right-0 h-1/2 flex items-end justify-center pb-16 pointer-events-none z-50"
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            {/* Arc line decoration */}
            <svg
              className="absolute bottom-0 left-1/2 -translate-x-1/2"
              width="700" height="350"
              style={{ overflow: 'visible' }}
            >
              <motion.path
                d="M 50,350 Q 350,0 650,350"
                fill="none"
                stroke="var(--hud-line-dim)"
                strokeWidth="1"
                strokeDasharray="4 6"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.5 }}
              />
            </svg>

            <div className="relative w-[600px] h-[280px]">
              {menuItems.map((item, index) => {
                const angle = 30 + (index * 30); 
                const rad = (180 - angle) * (Math.PI / 180);
                const radius = 200;
                const x = Math.cos(rad) * radius + 300 - 45; 
                const y = 280 - (Math.sin(rad) * radius) - 35;

                const isSelected = selectedItem === index;
                const isConfirmed = confirmedItem === index;

                return (
                  <motion.div
                    key={item}
                    className="absolute w-[90px] h-[70px] flex flex-col items-center justify-center pointer-events-auto cursor-pointer"
                    style={{ left: x, top: y }}
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ 
                      opacity: 1, 
                      scale: isSelected ? 1.15 : 1 
                    }}
                    transition={{ delay: index * 0.05, duration: 0.2 }}
                    onClick={() => {
                      setSelectedItem(index);
                      setConfirmedItem(index);
                      const itemName = menuItems[index];
                      let screenshot = null;
                      if ((itemName === "VISION" || itemName === "OCR") && webcam) {
                        screenshot = webcam.getScreenshot();
                      }

                      // Route actions properly
                      if (itemName === "SPOTIFY") {
                        GestureSocket.getInstance().sendVoiceCommand("play some music", {});
                      } else if (itemName === "FINANCE") {
                        setFinancePanelOpen(true);
                      } else {
                        GestureSocket.getInstance().sendMenuAction(itemName, { image: screenshot });
                      }

                      setTimeout(() => { setMenuOpen(false); setConfirmedItem(null); }, 600);
                    }}
                  >
                    {/* L-bracket frame */}
                    <div className={`
                      hud-frame w-full h-full flex flex-col items-center justify-center transition-all duration-200
                      ${isSelected ? 'bg-white/8' : ''}
                      ${isConfirmed ? 'bg-white/20' : ''}
                    `}>
                      <div className="hud-frame-inner w-full h-full flex flex-col items-center justify-center">
                        <MenuIcon name={item} active={isSelected} />
                        <span className={`text-[8px] font-medium mt-1 tracking-[0.2em] uppercase ${
                          isSelected ? 'text-white' : 'text-white/40'
                        }`}>
                          {item}
                        </span>
                        {isSelected && (
                          <motion.div
                            className="absolute -bottom-1 left-1/2 -translate-x-1/2"
                            initial={{ width: 0 }}
                            animate={{ width: 20 }}
                          >
                            <div className="h-[1px] bg-white w-full" />
                          </motion.div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── FINANCE PANEL OVERLAY ──────────────────────────────── */}
      <AnimatePresence>
        {financePanelOpen && (
          <ExpensePanel onClose={() => setFinancePanelOpen(false)} />
        )}
      </AnimatePresence>

      {/* ── GESTURE CURSOR RETICLE (HUD styled) ──────────────────── */}
      <AnimatePresence>
        {cursorVisible && (
          <motion.div
            key="cursor-reticle"
            className="fixed pointer-events-none z-100"
            animate={{ 
              x: cursorPos.x - 20, 
              y: cursorPos.y - 20,
              scale: isHoveringClickable ? 1.2 : 1
            }}
            transition={{ type: 'spring', stiffness: 400, damping: 35, mass: 0.5 }}
          >
            <div className="relative w-10 h-10">
              {/* Pulse animation for click */}
              <AnimatePresence mode="popLayout">
                <motion.div
                  key={lastClickTime}
                  className="absolute inset-0 bg-white/40 rounded-full"
                  initial={{ scale: 0, opacity: 0.8 }}
                  animate={{ scale: 3, opacity: 0 }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                />
              </AnimatePresence>

              {/* Outer Circle - Glows if hovering something clickable */}
              <motion.div 
                className={`absolute inset-0 border border-white/20 rounded-full transition-shadow duration-300 ${
                  isHoveringClickable ? 'shadow-[0_0_15px_rgba(255,255,255,0.6)] border-white/40' : ''
                }`}
                animate={{ rotate: 360 }}
                transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
              />
              
              {/* Inner Circle (dim) */}
              <div className="absolute inset-2 border border-white/10 rounded-full border-dashed" />
              
              {/* Center Dot - Stronger glow if clickable */}
              <div className={`absolute inset-[18px] rounded-full transition-all duration-300 ${
                  isHoveringClickable 
                    ? 'bg-white shadow-[0_0_12px_rgba(255,255,255,0.8)]' 
                    : 'bg-white/60 shadow-[0_0_8px_rgba(255,255,255,0.4)]'
              }`} />
              
              {/* Crosshair Lines */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-2 bg-white/40" />
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-px h-2 bg-white/40" />
              <div className="absolute top-1/2 left-0 -translate-y-1/2 h-px w-2 bg-white/40" />
              <div className="absolute top-1/2 right-0 -translate-y-1/2 h-px w-2 bg-white/40" />
              
              {/* L-Brackets Corners (Micro) */}
              <div className="absolute top-0 left-0 w-1.5 h-1.5 border-t border-l border-white/60" />
              <div className="absolute top-0 right-0 w-1.5 h-1.5 border-t border-r border-white/60" />
              <div className="absolute bottom-0 left-0 w-1.5 h-1.5 border-b border-l border-white/60" />
              <div className="absolute bottom-0 right-0 w-1.5 h-1.5 border-b border-r border-white/60" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

// ── Menu Icons (SVG line art) ───────────────────────────────────
function MenuIcon({ name, active }: { name: string; active: boolean }) {
  const stroke = active ? "var(--hud-fg)" : "var(--hud-fg-dim)";
  const size = 18;

  switch (name) {
    case "VISION":
      return (
        <svg width={size} height={size} viewBox="0 0 18 18" fill="none">
          <circle cx="9" cy="9" r="3" stroke={stroke} strokeWidth="1" />
          <path d="M1 9C1 9 4 3 9 3C14 3 17 9 17 9C17 9 14 15 9 15C4 15 1 9 1 9Z" stroke={stroke} strokeWidth="1" />
        </svg>
      );
    case "OCR":
      return (
        <svg width={size} height={size} viewBox="0 0 18 18" fill="none">
          <rect x="2" y="3" width="14" height="12" stroke={stroke} strokeWidth="1" />
          <line x1="5" y1="7" x2="13" y2="7" stroke={stroke} strokeWidth="1" />
          <line x1="5" y1="10" x2="11" y2="10" stroke={stroke} strokeWidth="1" />
          <line x1="5" y1="13" x2="9" y2="13" stroke={stroke} strokeWidth="1" />
        </svg>
      );
    case "HOME":
      return (
        <svg width={size} height={size} viewBox="0 0 18 18" fill="none">
          <path d="M2 9L9 2L16 9" stroke={stroke} strokeWidth="1" />
          <path d="M4 8V16H14V8" stroke={stroke} strokeWidth="1" />
          <rect x="7" y="11" width="4" height="5" stroke={stroke} strokeWidth="1" />
        </svg>
      );
    case "SPOTIFY":
      return (
        <svg width={size} height={size} viewBox="0 0 18 18" fill="none">
          <circle cx="9" cy="9" r="7" stroke={stroke} strokeWidth="1" />
          <path d="M5 7C7 6 11 6 13 7" stroke={stroke} strokeWidth="1" />
          <path d="M6 10C7.5 9 10.5 9 12 10" stroke={stroke} strokeWidth="1" />
          <path d="M7 13C8 12.5 10 12.5 11 13" stroke={stroke} strokeWidth="1" />
        </svg>
      );
    case "FINANCE":
      return (
        <svg width={size} height={size} viewBox="0 0 18 18" fill="none">
          <rect x="2" y="2" width="14" height="14" rx="1" stroke={stroke} strokeWidth="1" />
          <text x="9" y="13" textAnchor="middle" fill={stroke} fontSize="10" fontFamily="monospace">₹</text>
        </svg>
      );
    default:
      return null;
  }
}
