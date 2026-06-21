import { useState, useEffect, useRef } from 'react';

export const useWakeWord = (isIdle: boolean = true) => {
    const [isWakeWordDetected, setIsWakeWordDetected] = useState(false);
    const [isLoaded, setIsLoaded] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const recognitionRef = useRef<any>(null);
    const activeRef = useRef(false);

    useEffect(() => {
        if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
            setError("Web Speech API not supported in this browser.");
            return;
        }

        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = 'en-US';
        recognitionRef.current = rec;

        rec.onstart = () => {
            console.log("[WAKEWORD] Continuous SpeechRecognition started");
            activeRef.current = true;
        };

        rec.onend = () => {
            activeRef.current = false;
            // Restart if it ended unexpectedly and we are still idle
            if (isIdle) {
                try {
                    rec.start();
                } catch (e) {
                    console.error("[WAKEWORD] Failed to restart", e);
                }
            }
        };

        rec.onresult = (event: any) => {
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                const text = event.results[i][0].transcript.toLowerCase();
                console.log("[WAKEWORD] Heard:", text);
                if (text.includes("alfred")) {
                    console.log("[WAKEWORD] Wake word 'Alfred' DETECTED!");
                    setIsWakeWordDetected(true);
                    
                    // Stop recognition to release microphone for main assistant
                    try {
                        rec.stop();
                    } catch (e) {}

                    // Trigger detection state pulse
                    setTimeout(() => setIsWakeWordDetected(false), 1000);
                    break;
                }
            }
        };

        rec.onerror = (event: any) => {
            console.error("[WAKEWORD] Error:", event.error);
            if (event.error === 'not-allowed') {
                setError("Microphone permission denied.");
            }
        };

        setIsLoaded(true);

        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.onend = null;
                try {
                    recognitionRef.current.stop();
                } catch (e) {}
            }
        };
    }, []);

    // Control speech recognition activation based on isIdle status
    useEffect(() => {
        const rec = recognitionRef.current;
        if (!rec) return;

        if (isIdle) {
            if (!activeRef.current) {
                try {
                    rec.start();
                    console.log("[WAKEWORD] Activated listener");
                } catch (e) {
                    console.error("[WAKEWORD] Failed to start listener", e);
                }
            }
        } else {
            if (activeRef.current) {
                try {
                    rec.stop();
                    console.log("[WAKEWORD] Deactivated listener");
                } catch (e) {
                    console.error("[WAKEWORD] Failed to stop listener", e);
                }
            }
        }
    }, [isIdle]);

    return { isWakeWordDetected, isLoaded, error };
};
