"use client";

import React, { useState, useEffect } from 'react';
import { useSocket } from '../context/SocketContext';
import { motion, AnimatePresence } from 'framer-motion';

interface YouTubeVideo {
    title: string;
    video_id: string;
    link: string;
    thumbnail: string;
    channel: string;
    length?: string;
}

export default function YouTubePlayer() {
    const { socket } = useSocket();
    const [videos, setVideos] = useState<YouTubeVideo[]>([]);
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        if (!socket) return;

        const handleMessage = (msg: any) => {
            if (msg.type !== "RESPONSE") return;
            
            const payload = msg.payload;
            if (payload.tool_outputs?.youtube?.results) {
                const results = payload.tool_outputs.youtube.results;
                setVideos(results);
                setIsOpen(true);

                // Auto-open the first result in a new tab
                if (results.length > 0) {
                    window.open(`https://www.youtube.com/watch?v=${results[0].video_id}`, '_blank');
                }
            }
        };

        socket.on("message", handleMessage);
        return () => { socket.off("message", handleMessage); };
    }, [socket]);

    // Close on Escape
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') setIsOpen(false);
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, []);

    if (!isOpen || videos.length === 0) return null;

    const handleVideoClick = (videoId: string) => {
        window.open(`https://www.youtube.com/watch?v=${videoId}`, '_blank');
    };

    return (
        <AnimatePresence>
            <motion.div
                className="fixed inset-0 z-50 flex items-center justify-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
            >
                {/* Backdrop */}
                <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setIsOpen(false)} />

                {/* Panel */}
                <motion.div
                    className="relative w-[85vw] max-w-[800px] max-h-[80vh] flex flex-col z-10"
                    initial={{ y: 40, scale: 0.97 }}
                    animate={{ y: 0, scale: 1 }}
                    exit={{ y: 40, scale: 0.97 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                >
                    <div className="hud-frame p-0 overflow-hidden flex flex-col max-h-[80vh]">
                        <div className="hud-frame-inner flex flex-col h-full">
                            {/* ── Header ──────────────────────────── */}
                            <div className="px-4 pt-4 pb-3 border-b border-white/10 shrink-0">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="w-[6px] h-[6px] rounded-full bg-red-500" />
                                        <span className="text-[11px] tracking-[0.2em] uppercase text-white/60">
                                            Video Results
                                        </span>
                                        <span className="text-[9px] text-white/25 ml-2">
                                            {videos.length} FOUND
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => setIsOpen(false)}
                                        className="text-[10px] text-white/30 hover:text-white/70 transition-colors tracking-[0.15em] uppercase"
                                    >
                                        ✕ CLOSE
                                    </button>
                                </div>
                            </div>

                            {/* ── Video List ──────────────────────── */}
                            <div
                                className="flex-1 overflow-y-auto px-4 py-3 min-h-0"
                                style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.1) transparent' }}
                            >
                                <div className="flex flex-col gap-2">
                                    {videos.map((video, i) => (
                                        <motion.button
                                            key={video.video_id || `vid-${i}`}
                                            initial={{ opacity: 0, x: -15 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: i * 0.04 }}
                                            onClick={() => handleVideoClick(video.video_id)}
                                            className="group relative flex gap-3 p-3 bg-white/2 hover:bg-white/6 transition-all text-left border border-white/5 hover:border-white/10"
                                        >
                                            {/* L-Brackets for each card */}
                                            <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white/20 group-hover:border-white/50 transition-colors" />
                                            <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white/20 group-hover:border-white/50 transition-colors" />

                                            {/* Thumbnail */}
                                            <div className="relative w-[160px] h-[90px] shrink-0 overflow-hidden bg-white/5 border border-white/10">
                                                <img
                                                    src={video.thumbnail}
                                                    alt={video.title}
                                                    className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity"
                                                />
                                                {/* Duration badge */}
                                                {video.length && (
                                                    <span
                                                        className="absolute bottom-1 right-1 text-[9px] bg-black/90 text-white/80 px-1.5 py-0.5 font-mono border border-white/10"
                                                    >
                                                        {video.length}
                                                    </span>
                                                )}
                                                {/* Play overlay */}
                                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                                                    <span className="text-white/90 text-[14px] font-mono">▶ [PLAY]</span>
                                                </div>
                                            </div>

                                            {/* Info */}
                                            <div className="flex flex-col justify-start pt-1 flex-1 min-w-0 font-mono">
                                                <span className="text-[12px] text-white/80 group-hover:text-white line-clamp-2 leading-tight transition-colors">
                                                    {video.title}
                                                </span>
                                                <div className="flex items-center gap-2 mt-2">
                                                    <span className="text-[9px] text-white/40 uppercase tracking-widest border-r border-white/10 pr-2">
                                                        {video.channel}
                                                    </span>
                                                    <span className="text-[8px] text-white/20 uppercase tracking-[0.2em]">
                                                        Verified Result
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Open icon */}
                                            <div className="flex items-center px-1 opacity-20 group-hover:opacity-100 transition-opacity">
                                                <span className="text-[10px] text-white font-mono">↗</span>
                                            </div>
                                        </motion.button>
                                    ))}
                                </div>
                            </div>

                            {/* ── Footer hint ────────────────────── */}
                            <div className="px-4 py-2 border-t border-white/5 shrink-0">
                                <span className="text-[8px] text-white/15 tracking-widest uppercase">
                                    Click to open in browser · ESC to close
                                </span>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
