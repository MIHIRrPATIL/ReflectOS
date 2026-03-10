import { HandInfo } from "./HandTracker";

export abstract class Gesture {
    abstract name: string;

    // Cooldown & Streak Logic
    protected lastTriggered: number = 0;
    protected cooldown: number = 500; // ms (Default 0.5s)
    protected requiredStreak: number = 4; // Frames (Increased for stability)
    protected currentStreak: number = 0;

    /**
     * Main check function called by Manager.
     * Handles cooldowns and streaks.
     */
    public check(
        hands: HandInfo[],
        history: Record<number, HandInfo[]>
    ): boolean {
        const now = Date.now();

        // 1. Cooldown Check
        if (now - this.lastTriggered < this.cooldown) {
            return false;
        }

        // 2. Detection
        const detected = this.detect(hands, history);

        if (detected) {
            this.currentStreak++;
            console.log(`[${this.name}] Streak: ${this.currentStreak}/${this.requiredStreak}`);

            if (this.currentStreak >= this.requiredStreak) {
                this.lastTriggered = now;
                this.currentStreak = 0;
                return true;
            }
        } else {
            // Reset streak if detection fails
            this.currentStreak = 0;
        }

        return false;
    }

    /**
     * Actual geometric detection logic. Implemented by subclasses.
     */
    protected abstract detect(
        hands: HandInfo[],
        history: Record<number, HandInfo[]>
    ): boolean;
}
