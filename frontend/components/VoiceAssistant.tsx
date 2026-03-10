'use client';

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useWakeWord } from '@/lib/hooks/useWakeWord';
import { useSpeechToText } from '@/lib/hooks/useSpeechToText';
import { GestureSocket } from '@/lib/gesture-engine/GestureSocket';
import { motion, AnimatePresence } from 'framer-motion';

// ── Oscilloscope Waveform ───────────────────────────────────────
function OscilloscopeRing({
  isActive,
  isPlaying,
  isProcessing,
}: {
  isActive: boolean;
  isPlaying: boolean;
  isProcessing: boolean;
}) {
  const size = 100;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 38;
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!isActive && !isPlaying && !isProcessing) return;
    const interval = isProcessing ? 50 : 80;
    const id = setInterval(() => setTick((t) => t + 1), interval);
    return () => clearInterval(id);
  }, [isActive, isPlaying, isProcessing]);

  // Generate jagged waveform path around the circle
  const pathData = useMemo(() => {
    const segments = 48;
    const points: string[] = [];

    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2 - Math.PI / 2;
      let r = radius;

      if (isActive) {
        // High-frequency jagged oscilloscope
        const wave =
          Math.sin(angle * 8 + tick * 0.5) * 4 +
          Math.sin(angle * 13 + tick * 0.8) * 2.5 +
          Math.random() * 1.5;
        r += wave;
      } else if (isPlaying) {
        // Gentle pulse
        const wave = Math.sin(angle * 4 + tick * 0.3) * 2;
        r += wave;
      }

      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      points.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`);
    }
    points.push('Z');
    return points.join(' ');
  }, [tick, isActive, isPlaying]);

  return (
    <svg width={size} height={size} className="shrink-0">
      {/* Base circle (always visible) */}
      <motion.circle
        cx={cx}
        cy={cy}
        r={radius}
        fill="none"
        stroke="rgba(255,255,255,0.1)"
        strokeWidth="1"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.8, ease: 'easeInOut' }}
      />

      {/* Active waveform / playing pulse */}
      {(isActive || isPlaying) && (
        <motion.path
          d={pathData}
          fill="none"
          stroke={isActive ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.4)'}
          strokeWidth="1"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        />
      )}

      {/* Outer dashed decorative ring — rotates when processing */}
      <motion.circle
        cx={cx}
        cy={cy}
        r={radius + 8}
        fill="none"
        stroke={isProcessing ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.08)'}
        strokeWidth="1"
        strokeDasharray="3 5"
        animate={isProcessing ? { rotate: 360 } : {}}
        transition={isProcessing ? { duration: 3, repeat: Infinity, ease: 'linear' } : {}}
        style={{ transformOrigin: `${cx}px ${cy}px` }}
      />

      {/* Processing sweep arc */}
      {isProcessing && (
        <motion.circle
          cx={cx}
          cy={cy}
          r={radius + 3}
          fill="none"
          stroke="rgba(255,255,255,0.4)"
          strokeWidth="1"
          strokeDasharray={`${Math.PI * (radius + 3) * 0.3} ${Math.PI * (radius + 3) * 1.7}`}
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          style={{ transformOrigin: `${cx}px ${cy}px` }}
        />
      )}

      {/* Center dot */}
      <circle
        cx={cx}
        cy={cy}
        r={isActive ? 3 : 2}
        fill={
          isActive
            ? 'rgba(255,255,255,0.9)'
            : isPlaying
              ? 'rgba(255,255,255,0.5)'
              : 'rgba(255,255,255,0.15)'
        }
      />
    </svg>
  );
}

// ── Main VoiceAssistant (HUD Feedback Ring) ─────────────────────
export default function VoiceAssistant() {
  const { isWakeWordDetected, isLoaded, error: wakeWordError } = useWakeWord();
  const {
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening,
  } = useSpeechToText();
  const [displayTranscript, setDisplayTranscript] = useState('');
  const [isVisible, setIsVisible] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ignoreNextResponse = useRef(false);
  const autoDismissTimer = useRef<NodeJS.Timeout | null>(null);

  const playAudio = useCallback(
    (base64Audio: string, onComplete?: () => void) => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }

      const audioFn = new Audio(`data:audio/mp3;base64,${base64Audio}`);
      audioRef.current = audioFn;

      audioFn.onplay = () => setIsPlaying(true);
      audioFn.onended = () => {
        setIsPlaying(false);
        if (onComplete) onComplete();
      };

      audioFn.play().catch((e) => console.error('Audio Playback Error:', e));
    },
    []
  );

  // Listen for backend responses
  useEffect(() => {
    const socket = GestureSocket.getInstance().getSocket();
    if (!socket) return;

    const handleMessage = (msg: any) => {
      if (msg.type !== 'RESPONSE') return;

      const data = msg.payload;
      console.log('[AI] Response Message:', data);

      if (ignoreNextResponse.current && data.response) {
        console.log('[INTERRUPT] Ignoring response due to interruption.');
        ignoreNextResponse.current = false;
        return;
      }

      if (data.response) {
        setIsVisible(true);
        setDisplayTranscript(data.response);

        // Clear any previous dismiss timer
        if (autoDismissTimer.current) clearTimeout(autoDismissTimer.current);

        const scheduleDismiss = () => {
          // Start 10-second countdown AFTER TTS finishes
          if (autoDismissTimer.current) clearTimeout(autoDismissTimer.current);
          autoDismissTimer.current = setTimeout(() => {
            setIsVisible(false);
            setDisplayTranscript('');
          }, 10000);
        };

        const handleCompletion = () => {
          scheduleDismiss();
          if (data.should_listen) {
            console.log('[AI] Auto-listening triggered by backend...');
            startListening();
          }
        };

        if (data.audio) {
          playAudio(data.audio, handleCompletion);
        } else {
          // No audio — dismiss after 10 seconds from now
          scheduleDismiss();
          if (data.should_listen) {
            setTimeout(() => startListening(), 2000);
          }
        }
      }
    };

    socket.on('message', handleMessage);
    return () => {
      socket.off('message', handleMessage);
    };
  }, [playAudio, startListening, isPlaying, isListening]);

  // Wake word trigger
  useEffect(() => {
    if (isWakeWordDetected) {
      console.log('Wake word detected! Starting listening...');
      GestureSocket.getInstance().sendInterrupt();
      ignoreNextResponse.current = true;
      setDisplayTranscript('');
      startListening();
      setIsVisible(true);

      if (audioRef.current) {
        audioRef.current.pause();
        setIsPlaying(false);
      }
    }
  }, [isWakeWordDetected]);

  // Handle transcript + send to backend
  useEffect(() => {
    if (transcript) {
      setDisplayTranscript(transcript);
      ignoreNextResponse.current = false;

      let screenshot = null;
      const webcam = (window as any).reflectWebcam;
      if (webcam) {
        screenshot = webcam.getScreenshot();
      }

      GestureSocket.getInstance().sendVoiceCommand(transcript, {
        image: screenshot,
      });
    }
  }, [transcript]);

  // Live feedback for interim results
  useEffect(() => {
    if (isListening && interimTranscript) {
      setDisplayTranscript(interimTranscript);
      setIsVisible(true);
    }
  }, [isListening, interimTranscript]);

  if (wakeWordError) {
    return (
      <div className="fixed bottom-4 right-4 text-[9px] hud-label" style={{ color: 'var(--hud-error)' }}>
        {wakeWordError}
      </div>
    );
  }

  if (!isLoaded) return null;

  // Always show the ring — it's the center of the OS
  const showRing = true;
  const isIdle = !isVisible && !isListening && !isPlaying;

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Transcript display (above ring) */}
      <AnimatePresence>
        {displayTranscript && (
          <motion.div
            className="max-w-md"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
          >
            <div className="hud-frame px-5 py-3">
              <div className="hud-frame-inner">
                <p className="text-[16px] leading-relaxed text-white/80 max-h-[200px] overflow-y-auto text-center">
                    {displayTranscript}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Oscilloscope ring */}
      <motion.div
        className="relative"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: isIdle ? 0.3 : 1 }}
        transition={{ duration: 0.5 }}
      >
        <OscilloscopeRing isActive={isListening} isPlaying={isPlaying} isProcessing={isVisible && !isListening && !isPlaying} />

        {/* State label */}
        <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <span className="hud-label text-[7px]">
            {isListening ? 'LISTENING' : isPlaying ? 'SPEAKING' : isIdle ? 'ALFRED' : 'PROCESSING'}
          </span>
        </div>
      </motion.div>
    </div>
  );
}
