import { useState, useEffect, useRef } from 'react';

export const useWakeWord = (isIdle: boolean = true) => {
    const [isWakeWordDetected, setIsWakeWordDetected] = useState(false);
    const [isLoaded, setIsLoaded] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const recognitionRef = useRef<any>(null);
    const activeRef = useRef(false);
    const shouldTriggerDetectionRef = useRef(false);
    const isIdleRef = useRef(isIdle);

    // Sync isIdle to ref to prevent stale closures in event handlers
    useEffect(() => {
        isIdleRef.current = isIdle;
    }, [isIdle]);

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
            
            // If we stopped the wake-word session due to detecting 'Alfred', 
            // trigger the state now that the microphone is fully released.
            if (shouldTriggerDetectionRef.current) {
                shouldTriggerDetectionRef.current = false;
                console.log("[WAKEWORD] Mic released. Triggering wake word detection.");
                setIsWakeWordDetected(true);
                setTimeout(() => setIsWakeWordDetected(false), 1000);
                return; // Do NOT restart background listening yet
            }

            // Restart if it ended unexpectedly and we are still idle
            if (isIdleRef.current) {
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
                    console.log("[WAKEWORD] Wake word 'Alfred' DETECTED! Stopping wake-word session to release mic...");
                    shouldTriggerDetectionRef.current = true;
                    
                    // Stop recognition to release microphone for main assistant
                    try {
                        rec.stop();
                    } catch (e) {}
                    break;
                }
            }
        };

        rec.onerror = (event: any) => {
            // Ignore 'aborted' errors when we manually stop recognition on detection
            if (event.error === 'aborted') {
                console.log("[WAKEWORD] Session aborted (expected on stop).");
                return;
            }
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
