import { useState, useEffect, useRef, useCallback } from 'react';

export const useSpeechToText = () => {
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [interimTranscript, setInterimTranscript] = useState('');
    const recognitionRef = useRef<any>(null);
    const isListeningRef = useRef(false);
    const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // How long to wait after the user stops speaking before auto-stopping (ms)
    const SILENCE_TIMEOUT = 3000;

    useEffect(() => {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.continuous = true;        // Keep listening until stopped
            recognitionRef.current.interimResults = true;
            recognitionRef.current.lang = 'en-US';

            recognitionRef.current.onstart = () => {
                setIsListening(true);
                isListeningRef.current = true;
            };

            recognitionRef.current.onend = () => {
                setIsListening(false);
                isListeningRef.current = false;
                clearSilenceTimer();
            };

            recognitionRef.current.onresult = (event: any) => {
                let final = '';
                let interim = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        final += event.results[i][0].transcript;
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }

                if (final) {
                    setTranscript(prev => (prev + ' ' + final).trim());
                }
                setInterimTranscript(interim);

                // Reset silence timer every time we get speech input
                resetSilenceTimer();
            };

            recognitionRef.current.onerror = (event: any) => {
                console.error("Speech recognition error", event.error);
                setIsListening(false);
                isListeningRef.current = false;
                clearSilenceTimer();
            };
        }
    }, []);

    const clearSilenceTimer = () => {
        if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
        }
    };

    const resetSilenceTimer = () => {
        clearSilenceTimer();
        silenceTimerRef.current = setTimeout(() => {
            // Auto-stop after silence
            if (recognitionRef.current && isListeningRef.current) {
                recognitionRef.current.stop();
            }
        }, SILENCE_TIMEOUT);
    };

    const startListening = useCallback(() => {
        if (recognitionRef.current && !isListeningRef.current) {
            try {
                setTranscript('');
                setInterimTranscript('');
                recognitionRef.current.start();
                // Start the silence timer (in case user doesn't say anything)
                resetSilenceTimer();
            } catch (e) {
                console.error("Failed to start recognition", e);
            }
        }
    }, []);

    const stopListening = useCallback(() => {
        clearSilenceTimer();
        if (recognitionRef.current && isListeningRef.current) {
            recognitionRef.current.stop();
        }
    }, []);

    return { isListening, transcript, interimTranscript, startListening, stopListening };
};
