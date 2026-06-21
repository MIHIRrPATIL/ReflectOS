import { Gesture } from "../Gesture";
import { HandInfo } from "../HandTracker";
import { distance } from "../primitives";

const HISTORY_REQUIRED = 3;

// ==========================================
// SWIPES
// ==========================================
abstract class SwipeGesture extends Gesture {
    protected minVelocityBase = 0.04;
    protected requiredStreak = 2;
    protected cooldown = 800;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const hand = hands[0];
        const handHistory = history[hand.id] || [];

        if (handHistory.length < HISTORY_REQUIRED) return false;

        const curr = hand.wristCoords;
        const prev = handHistory[handHistory.length - HISTORY_REQUIRED].wristCoords;

        const vec = { x: curr.x - prev.x, y: curr.y - prev.y };
        const minVelocity = this.minVelocityBase * (hand.scale / 0.1);

        return this.checkDirection(vec, minVelocity);
    }

    abstract checkDirection(vec: { x: number; y: number }, minV: number): boolean;
}

export class SwipeLeft extends SwipeGesture {
    name = "SWIPE_LEFT";
    checkDirection(vec: { x: number; y: number }, minV: number): boolean {
        // Camera is mirrored: physical left = positive x in coordinates
        return vec.x > minV && Math.abs(vec.y) < Math.abs(vec.x);
    }
}

export class SwipeRight extends SwipeGesture {
    name = "SWIPE_RIGHT";
    checkDirection(vec: { x: number; y: number }, minV: number): boolean {
        // Camera is mirrored: physical right = negative x in coordinates
        return vec.x < -minV && Math.abs(vec.y) < Math.abs(vec.x);
    }
}

export class SwipeUp extends SwipeGesture {
    name = "SWIPE_UP";
    checkDirection(vec: { x: number; y: number }, minV: number): boolean {
        return vec.y < -minV && Math.abs(vec.x) < Math.abs(vec.y);
    }
}

export class SwipeDown extends SwipeGesture {
    name = "SWIPE_DOWN";
    checkDirection(vec: { x: number; y: number }, minV: number): boolean {
        return vec.y > minV && Math.abs(vec.x) < Math.abs(vec.y);
    }
}

// ==========================================
// TAPS
// ==========================================

export class AirTap extends Gesture {
    name = "AIR_TAP";
    protected cooldown = 250; // Very fast to allow rapid double taps or "Hold to Select"
    protected requiredStreak = 2;
    private baseThreshold = 0.03; // More strict to prevent phantom pinches

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const hand = hands[0];

        // Strict Check: Index and Thumb must be "extended" to some degree, 
        // but for AirTap Tip-to-Tip is the primary check.
        // HOWEVER, to avoid THUMB_UP, we MUST ensure Middle, Ring, Pinky are curled.
        if (hand.fingersExtended[2] || hand.fingersExtended[3] || hand.fingersExtended[4]) return false;
        
        // Index should be roughly extended (or at least not tightly curled)
        // MediaPipe fingersExtended is usually reliable for this.
        if (!hand.fingersExtended[1]) return false;

        const thumbTip = hand.landmarks[4];
        const indexTip = hand.landmarks[8];
        const dist = distance(thumbTip, indexTip);

        const threshold = this.baseThreshold * (hand.scale / 0.1);
        return dist < threshold;
    }
}

export class GunTap extends Gesture {
    name = "GUN_TAP";
    protected cooldown = 1000;
    protected requiredStreak = 5; // Require holding the pose briefly

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const hand = hands[0];

        // Debug Log (Throttled slightly or just spam it for now, user is waiting)
        // console.log("GunTap Check", hand.fingersExtended);

        // 1. Check Pose: Two-Finger Gun
        // Index (1) and Middle (2) extended
        // Ring (3) and Pinky (4) curled (not extended)
        if (!hand.fingersExtended[1] || !hand.fingersExtended[2]) {
            // console.log("GunTap Fail: Index/Middle not extended");
            return false;
        }
        if (hand.fingersExtended[3] || hand.fingersExtended[4]) {
            // console.log("GunTap Fail: Ring/Pinky extended");
            return false;
        }

        // 2. Check Action: Thumb Tap on Index Joint
        // Backend Logic: Thumb tip (4) touches Index PIP (6) or MCP (5)
        const thumbTip = hand.landmarks[4];
        const indexPip = hand.landmarks[6];
        const indexMcp = hand.landmarks[5];

        const distPip = distance(thumbTip, indexPip);
        const distMcp = distance(thumbTip, indexMcp);

        // Allow tapping either joint
        const minDist = Math.min(distPip, distMcp);

        // Backend used 0.06 base * scale.
        const threshold = 0.06 * (hand.scale / 0.1);

        console.log(`GunTap Debug: Dist: ${minDist.toFixed(3)}, Thr: ${threshold.toFixed(3)} (PIP: ${distPip.toFixed(3)}, MCP: ${distMcp.toFixed(3)})`);

        // If thumb is touching index knuckle, trigger
        return minDist < threshold;
    }
}

// ==========================================
// PINCH & DRAG (PINCH_HOLD)
// ==========================================

export class PinchHold extends Gesture {
    name = "PINCH_HOLD";
    protected cooldown = 0;

    private isDragging = false;
    private holdFrames = 0;

    // Override check() to manage state manually
    check(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) {
            // Lost hands during drag -> Release
            if (this.isDragging) {
                this.isDragging = false;
                this.holdFrames = 0;
                this.name = "PINCH_END:0,0";
                return true;
            }
            this.holdFrames = 0;
            return false;
        }

        const hand = hands[0];
        const thumbTip = hand.landmarks[4];
        const indexTip = hand.landmarks[8];
        const dist = distance(thumbTip, indexTip);

        const threshold = 0.03 * (hand.scale / 0.1);
        const isPinching = dist < threshold;

        if (isPinching) {
            this.holdFrames++;

            // "if an air tap is detected for let say more than 15 streak then it should be considered a pinch"
            if (this.holdFrames >= 15) {
                const x = thumbTip.x.toFixed(3);
                const y = thumbTip.y.toFixed(3);

                if (!this.isDragging) {
                    // Start Drag detected (Streak exceeded 10)
                    this.isDragging = true;
                    this.name = `PINCH_START:${x},${y}`;
                    return true;
                } else {
                    // Continue Drag
                    this.name = `PINCH_MOVE:${x},${y}`;
                    return true;
                }
            } else {
                // Should "never detect a pinch in one streak" implies we don't emit anything yet
                return false;
            }
        } else {
            // Released
            if (this.isDragging) {
                this.isDragging = false;
                this.holdFrames = 0;
                const x = thumbTip.x.toFixed(3);
                const y = thumbTip.y.toFixed(3);
                this.name = `PINCH_END:${x},${y}`;
                return true;
            }
            this.holdFrames = 0;
            return false; // Not pinching, not dragging
        }
    }

    // Unused because we override check()
    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean { return false; }
}

// ==========================================
// COMPLEX
// ==========================================

export class VolumeDial extends Gesture {
    name = "VOLUME_DIAL";
    protected cooldown = 0;
    protected requiredStreak = 3; // Increased for stability

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const hand = hands[0];

        const thumbTip = hand.landmarks[4];
        const indexTip = hand.landmarks[8];
        const dist = distance(thumbTip, indexTip);
        const pinchThreshold = 0.045 * (hand.scale / 0.1); // Slightly more relaxed

        // 1. Must be pinching
        if (dist > pinchThreshold) return false;

        // 2. Calculate Angle relative to Up (0 deg)
        const wrist = hand.landmarks[0];
        const indexMcp = hand.landmarks[5];

        const vec = { x: indexMcp.x - wrist.x, y: indexMcp.y - wrist.y };
        const rad = Math.atan2(vec.y, vec.x);

        let deg = (rad * 180 / Math.PI) + 90;

        // Map 30->0, 150->100
        if (deg < 10 || deg > 170) return false;

        let percentage = 0;
        if (deg <= 30) percentage = 0;
        else if (deg >= 150) percentage = 100;
        else {
            percentage = Math.round(((deg - 30) / 120) * 100);
        }

        this.name = `VOLUME:${percentage}`;
        return true;
    }
}

export class MenuWheel extends Gesture {
    name = "MENU_WHEEL";
    protected cooldown = 0; // Continuous

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const hand = hands[0];

        // RELAXED: Only Index(1) and Middle(2) need to be open.
        if (!hand.fingersExtended[1] || !hand.fingersExtended[2]) return false;

        const wrist = hand.landmarks[0];
        const middleTip = hand.landmarks[12]; // Using Middle Tip (12) as requested

        // Vector from Wrist(0) to Tip(12)
        const vec = { x: middleTip.x - wrist.x, y: middleTip.y - wrist.y };

        // Atan2: 0=Right, -PI/2=Up, PI=Left, PI/2=Down
        const rad = Math.atan2(vec.y, vec.x);

        // Map to 0-180 Range relative to "Base Line" (Horizontal)
        // We assume the semicircle is the Upper Hemisphere (Right -> UI -> Left)

        // Convert radians to degrees [-180, 180]
        let deg = rad * (180 / Math.PI);

        // Filter: If pointing DOWN (positive deg), ignore (or clamp if noisy)
        if (deg > 30) return false;

        // Normalize to 0-180
        // -0 -> 0, -90 -> 90, -179 -> 179
        let normalized = (deg < 0) ? -deg : 0;
        if (Math.abs(deg) > 170) normalized = 180;

        // REQUESTED RANGE: 30 to 180 (150 deg span)
        if (normalized < 30 || normalized > 180) return false;

        // Map 30->0, 180->100% (5 sections)
        // Span = 150. Section = 150 / 5 = 30 deg per section.

        let val = normalized;
        let section = Math.floor((val - 30) / 30);
        section = Math.max(0, Math.min(4, section));

        this.name = `MENU_WHEEL_${section}`;
        return true;
    }
}

export class ModeSwitch extends Gesture {
    name = "MODE_SWITCH";
    protected cooldown = 2000;
    protected requiredStreak = 3;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const hand = hands[0];

        const hist = history[hand.id] || [];
        if (hist.length < 5) return false;

        const prevHand = hist[hist.length - 5];
        const n1 = hand.palmNormal;
        const n2 = prevHand.palmNormal;

        const dot = n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2];
        const angleRad = Math.acos(Math.max(-1, Math.min(1, dot)));
        const angleDeg = angleRad * (180 / Math.PI);

        return angleDeg > 120;
    }
}

export class FistMove extends Gesture {
    name = "FIST_MOVE";
    protected requiredStreak = 25; // Even higher to prevent any accidental interrupts

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const hand = hands[0];
        return hand.fingersExtended.every(f => !f);
    }
}

export class ThumbUp extends Gesture {
    name = "THUMB_UP";
    protected cooldown = 1000;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const h = hands[0];
        
        // STRICT: Thumb ONLY. Index, Middle, Ring, Pinky MUST be curled.
        if (!h.fingersExtended[0]) return false;
        if (h.fingersExtended[1] || h.fingersExtended[2] || h.fingersExtended[3] || h.fingersExtended[4]) return false;

        const tip = h.landmarks[4];
        const ip = h.landmarks[3];
        const mcp = h.landmarks[2];

        // Additional sanity: Tip must be significantly higher than MCP in Y (for UP)
        return (tip.y < ip.y - 0.05) && (ip.y < mcp.y);
    }
}

export class ThumbDown extends Gesture {
    name = "THUMB_DOWN";
    protected cooldown = 1000;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const h = hands[0];

        // STRICT: Thumb ONLY. Others MUST be curled.
        if (!h.fingersExtended[0]) return false;
        if (h.fingersExtended[1] || h.fingersExtended[2] || h.fingersExtended[3] || h.fingersExtended[4]) return false;

        const start = h.landmarks[2]; // MCP
        const end = h.landmarks[4];   // TIP

        const vec = { x: end.x - start.x, y: end.y - start.y };
        const len = Math.sqrt(vec.x * vec.x + vec.y * vec.y);
        if (len === 0) return false;
        const norm = { x: vec.x / len, y: vec.y / len };

        return norm.y > 0.85; // Strict down
    }
}

export class VerticalSplit extends Gesture {
    name = "CURTAIN_OPEN"; // Mapped to existing backend name
    protected cooldown = 1000;

    // State
    private state: "IDLE" | "CUTTING" = "IDLE";
    private startY = 0;
    private startTime = 0;

    check(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) {
            this.state = "IDLE";
            return false;
        }

        const hand = hands[0];
        const currentTime = Date.now();

        // Helper: Check V-Shape (Index+Middle Extended, Ring+Pinky Curled)
        const isVShape = () => {
            // Thumb optional? User said "Index + Middle".
            return hand.fingersExtended[1] && hand.fingersExtended[2]
                && !hand.fingersExtended[3] && !hand.fingersExtended[4];
        };

        // Helper: Check Closed (Index+Middle Tips close)
        const isClosed = () => {
            const dist = distance(hand.landmarks[8], hand.landmarks[12]);
            return dist < 0.05; // Touching
        };

        if (this.state === "IDLE") {
            if (isVShape()) {
                this.state = "CUTTING";
                this.startY = hand.wristCoords.y;
                this.startTime = currentTime;
            }
            return false;
        }

        if (this.state === "CUTTING") {
            // Timeout (1.5s to complete cut)
            if (currentTime - this.startTime > 1500) {
                this.state = "IDLE";
                return false;
            }

            // Check if user aborted (opened hand fully or weird shape)
            if (!isVShape() && !isClosed()) {
                // If they are transitioning to closed, we allow it. 
                // But if they opened ring/pinky, abort.
                if (hand.fingersExtended[3] || hand.fingersExtended[4]) {
                    this.state = "IDLE";
                    return false;
                }
            }

            // Check for Completion (Closed Fingers)
            if (isClosed()) {
                // Check Distance Moved
                const currentY = hand.wristCoords.y;
                const deltaY = currentY - this.startY; // Positive is Down

                // Requirement: "Move V downwards"
                if (deltaY > 0.1) { // Moved down by 10%
                    this.state = "IDLE";
                    // Success!
                    return true;
                } else {
                    // Closed too early or didn't move
                    this.state = "IDLE";
                    return false;
                }
            }
            // Still Moving
            return false;
        }
        return false;
    }

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean { return false; }

    public isProcessing(): boolean {
        return this.state === "CUTTING";
    }
}

// ==========================================
// CURSOR MODE
// ==========================================

export class CursorMove extends Gesture {
    name = "CURSOR_MOVE";
    protected cooldown = 0; // Continuous tracking
    protected requiredStreak = 2;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length === 0) return false;
        const hand = hands[0];

        // 1. MUST BE LEFT HAND (User explicitly asked for left index finger)
        if (hand.handedness !== "Left") return false;

        // 2. CHECK POSE: Index finger pointing UP
        // Index (1) extended. Middle, Ring, Pinky (2, 3, 4) NOT extended.
        // Thumb (0) can be anything to allow Air Tap/Pinch.
        const f = hand.fingersExtended;
        if (!f[1] || f[2] || f[3] || f[4]) return false;

        // 3. CHECK DIRECTION: Index Tip must be higher than MCP
        const tip = hand.landmarks[8];
        const mcp = hand.landmarks[5];
        if (tip.y > mcp.y - 0.05) return false; // Y increases downwards

        // 4. EMIT COORDINATES
        // x, y are normalized [0, 1]
        this.name = `CURSOR_MOVE:${tip.x.toFixed(4)},${tip.y.toFixed(4)}`;
        return true;
    }
}
