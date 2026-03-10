"use client";

import React, { useEffect, useRef, useState } from "react";
import Webcam from "react-webcam";
import { motion, AnimatePresence } from "framer-motion";
import { FilesetResolver, HandLandmarker } from "@mediapipe/tasks-vision";
import { HandTracker } from "../lib/gesture-engine/HandTracker";
import { GestureManager } from "../lib/gesture-engine/GestureManager";

interface GestureCameraProps {
  onGesture?: (gesture: string) => void;
  onReady?: (webcam: Webcam) => void;
  expanded?: boolean;
}

export default function GestureCamera({ onGesture, onReady, expanded = false }: GestureCameraProps) {
  const webcamRef = useRef<Webcam>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [delegate, setDelegate] = useState<"GPU" | "CPU">("GPU");

  // Engine Refs
  const handTracker = useRef(new HandTracker());
  const gestureManager = useRef(new GestureManager());
  const handLandmarkerRef = useRef<HandLandmarker | null>(null);

  useEffect(() => {
    async function loadModel(currentDelegate: "GPU" | "CPU" = "GPU") {
      try {
        setError(null);
        console.log(`[AI] Attempting to load HandLandmarker with ${currentDelegate} delegate...`);
        
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
        );
        
        const handLandmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`,
            delegate: currentDelegate,
          },
          runningMode: "VIDEO",
          numHands: 2,
          minHandDetectionConfidence: 0.7,
          minTrackingConfidence: 0.7,
        });

        handLandmarkerRef.current = handLandmarker;
        setLoaded(true);
        setDelegate(currentDelegate);
        console.log(`[AI] MediaPipe HandLandmarker Loaded successfully using ${currentDelegate}`);
      } catch (err) {
        console.error(`[AI] Failed to load HandLandmarker with ${currentDelegate}:`, err);
        
        if (currentDelegate === "GPU") {
          console.warn("[AI] Falling back to CPU delegate...");
          loadModel("CPU");
        } else {
          setError("Failed to initialize AI tracking. Please check your camera settings.");
        }
      }
    }

    loadModel();
  }, []);

  useEffect(() => {
    if (loaded && webcamRef.current && onReady) {
        onReady(webcamRef.current);
        (window as any).reflectWebcam = webcamRef.current;
    }
  }, [loaded, onReady]);

  useEffect(() => {
    let animationFrameId: number;

    const detect = async () => {
      if (
        webcamRef.current &&
        webcamRef.current.video &&
        webcamRef.current.video.readyState === 4 &&
        webcamRef.current.video.videoWidth > 0 &&
        webcamRef.current.video.videoHeight > 0 &&
        handLandmarkerRef.current
      ) {
        const video = webcamRef.current.video;
        const nowInMs = Date.now();

        // 1. MediaPipe Detection
        const result = handLandmarkerRef.current.detectForVideo(video, nowInMs);

        if (result.landmarks && result.landmarks.length > 0) {
            // 2. Convert to HandInfo structure
            // Fix: Map MediaPipe handedness to simple format
            const simpleHandedness = result.handedness.map(catList => ({
                categoryName: catList[0]?.categoryName || "Right"
            }));
            
            const hands = handTracker.current.process(result.landmarks, simpleHandedness);
            
            // 3. Check Gestures
            const gesture = gestureManager.current.update(hands);
            
            if (gesture) {
                console.log("FE Gesture:", gesture);
                if (onGesture) onGesture(gesture);
            }
        } else {
             // Reset manager if needed (hands lost)
             gestureManager.current.update([]);
        }
      }
      animationFrameId = requestAnimationFrame(detect);
    };

    if (loaded) {
      detect();
    }

    return () => cancelAnimationFrame(animationFrameId);
  }, [loaded, onGesture]);

  if (expanded) {
    return (
      <motion.div
        className="w-full h-full relative"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Webcam
          ref={webcamRef}
          className="w-full h-full object-cover opacity-60"
          mirrored={true}
          screenshotFormat="image/jpeg"
          screenshotQuality={1}
          videoConstraints={{
              width: 1280,
              height: 720,
              facingMode: "user"
          }}
          style={{ border: '1px solid var(--hud-line-dim)' }}
        />
        {/* Animated corner brackets */}
        <motion.div
          initial={{ scale: 1.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.15, duration: 0.4, ease: 'easeOut' }}
        >
          <div className="absolute top-2 left-2 w-8 h-8 border-t-2 border-l-2 border-white/40" />
          <div className="absolute top-2 right-2 w-8 h-8 border-t-2 border-r-2 border-white/40" />
          <div className="absolute bottom-2 left-2 w-8 h-8 border-b-2 border-l-2 border-white/40" />
          <div className="absolute bottom-2 right-2 w-8 h-8 border-b-2 border-r-2 border-white/40" />
        </motion.div>
        {/* Scan line animation */}
        <motion.div
          className="absolute left-0 right-0 h-px bg-linear-to-r from-transparent via-white/30 to-transparent"
          initial={{ top: '0%' }}
          animate={{ top: '100%' }}
          transition={{ duration: 2, ease: 'linear', repeat: Infinity }}
        />
        {/* Label */}
        <motion.div
          className="absolute top-5 left-10"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
        >
          <span className="text-[9px] tracking-[0.2em] uppercase" style={{ color: 'var(--hud-fg-dim)' }}>
            CAM.01 — EXPANDED
          </span>
        </motion.div>
        <motion.div
          className="absolute bottom-5 right-10 flex items-center gap-1"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
        >
          <span className="w-[4px] h-[4px] rounded-full bg-green-500 animate-pulse" />
          <span className="text-[8px] tracking-[0.15em] uppercase" style={{ color: 'var(--hud-fg-dim)' }}>
            {loaded ? delegate : 'INIT'} • FIST TO CLOSE
          </span>
        </motion.div>
      </motion.div>
    );
  }

  return (
    <div className="fixed bottom-16 right-6 z-40 group">
      {/* L-bracket corners */}
      <div className="hud-frame p-0.5 w-44 h-32">
        <div className="hud-frame-inner relative w-full h-full overflow-hidden">
          <Webcam
            ref={webcamRef}
            className="w-full h-full object-cover opacity-40 group-hover:opacity-80 transition-opacity duration-300"
            mirrored={true}
            screenshotFormat="image/jpeg"
            screenshotQuality={1}
            videoConstraints={{
                width: 1280,
                height: 720,
                facingMode: "user"
            }}
            style={{ border: '1px solid var(--hud-line-dim)' }}
          />
          {/* Camera label */}
          <div className="absolute top-1 left-2">
            <span className="text-[7px] tracking-[0.2em] uppercase" style={{ color: 'var(--hud-fg-dim)' }}>
              CAM.01
            </span>
          </div>
          {/* Status indicator */}
          <div className="absolute bottom-1 right-2 flex items-center gap-1">
            <span className="w-[4px] h-[4px] rounded-full bg-green-500 animate-pulse" />
            <span className="text-[6px] tracking-[0.15em] uppercase" style={{ color: 'var(--hud-fg-dim)' }}>
              {loaded ? delegate : 'INIT'}
            </span>
          </div>
          {!loaded && !error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ background: 'rgba(0,0,0,0.8)' }}>
              <div className="text-[9px] tracking-[0.15em] uppercase" style={{ color: 'var(--hud-fg-dim)' }}>LOADING AI...</div>
              <div className="text-[7px] mt-1" style={{ color: 'var(--hud-fg-muted)' }}>HW: {delegate}</div>
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center p-2 text-center" style={{ background: 'rgba(0,0,0,0.8)' }}>
              <span className="text-[8px]" style={{ color: 'var(--hud-error)' }}>{error}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
