import { useState, useEffect, useRef } from 'react';
import { PorcupineWorker } from '@picovoice/porcupine-web';
import { WebVoiceProcessor } from '@picovoice/web-voice-processor';

const ACCESS_KEY = process.env.NEXT_PUBLIC_PICOVOICE_ACCESS_KEY;
const KEYWORD = {
    publicPath: '/WakeUpWord/alfred_en_wasm_v4_0_0.ppn',
    label: 'Alfred',
    sensitivity: 0.98,
};
const MODEL = {
    publicPath: '/WakeUpWord/porcupine_params.pv',
};

export const useWakeWord = () => {
    const [isWakeWordDetected, setIsWakeWordDetected] = useState(false);
    const [isLoaded, setIsLoaded] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const porcupineRef = useRef<PorcupineWorker | null>(null);

    useEffect(() => {
        if (!ACCESS_KEY) {
            setError("Missing Picovoice Access Key");
            return;
        }

        const initPorcupine = async () => {
            try {
                const keywordDetectionCallback = (detection: any) => {
                    if (detection.label === 'Alfred') {
                        setIsWakeWordDetected(true);
                        setTimeout(() => setIsWakeWordDetected(false), 1000);
                    }
                };

                const processErrorCallback = (err: any) => {
                    console.error("Porcupine error:", err);
                    setError(err.toString());
                };

                porcupineRef.current = await PorcupineWorker.create(
                    ACCESS_KEY,
                    KEYWORD,
                    keywordDetectionCallback,
                    MODEL
                );

                await WebVoiceProcessor.subscribe(porcupineRef.current);

                setIsLoaded(true);
            } catch (err: any) {
                console.error("Porcupine initialization failed:", err);
                setError(err.message || 'Failed to initialize wake word detection');
            }
        };

        initPorcupine();

        return () => {
            if (porcupineRef.current) {
                porcupineRef.current.terminate();
                WebVoiceProcessor.unsubscribe(porcupineRef.current);
            }
        };
    }, []);

    return { isWakeWordDetected, isLoaded, error };
};
