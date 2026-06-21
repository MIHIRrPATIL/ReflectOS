import { Gesture } from "./Gesture";
import { HandInfo } from "./HandTracker";
import {
    AirTap, CursorMove, FistMove, GunTap, MenuWheel, ModeSwitch, PinchHold, SwipeDown, SwipeLeft, SwipeRight, SwipeUp, ThumbDown, ThumbUp, VerticalSplit, VolumeDial
} from "./gestures/oneHand";

import {
    AirFrame, AirMeasure, DualSwipe, SpreadZoom, WristCross
} from "./gestures/twoHand";

export class GestureManager {
    private history: Record<number, HandInfo[]> = {};
    private historySize = 60;

    // State Machine
    private inMenuMode = false;
    private isCursorActive = false; // track if left index is pointing
    private menuCooldown = 0;
    private lastVolumeVal = ""; // For throttling

    // Double Tap State
    private lastTapTime = 0;

    // Cursor Grace Period & Persistence
    private lastCursorActiveTime = 0;
    private lastCursorCoords = "0.5,0.5";
    private readonly cursorGracePeriod = 0.5; // 500ms grace for tap-to-click transition

    // Locking & Debouncing
    private lockExpiry = 0;
    private lockingSource: "VOLUME" | "OTHER" | null = null;
    private activeGestureName: string | null = null;
    private activeGestureStreak = 0;
    private readonly STREAK_THRESHOLD = 3;

    // Gestures
    private twoHandGestures: Gesture[];
    private oneHandGestures: Gesture[];
    private swipes: Gesture[];

    // Special References
    private volumeDial = new VolumeDial();
    private menuWheel = new MenuWheel();
    private fistGesture = new FistMove();
    private airTap = new AirTap();
    private cursorMove = new CursorMove();
    private gunTap = new GunTap();
    private verticalSplit = new VerticalSplit();
    private thumbUp = new ThumbUp();
    private thumbDown = new ThumbDown();

    constructor() {
        this.twoHandGestures = [
            new AirMeasure(),
            new SpreadZoom(),
            new DualSwipe(),
            new WristCross(),
            new AirFrame(),
        ];

        this.swipes = [
            new SwipeLeft(), new SwipeRight(), new SwipeUp(), new SwipeDown()
        ];

        // Priotized list for one-hand gestures
        this.oneHandGestures = [
            this.fistGesture,   // 1. Safety / Interrupt
            this.verticalSplit, // 2. Major Layout Action
            this.thumbUp,       // 3. Zen Mode Toggle
            this.thumbDown,     // 4. Downwards Toggle
            new ModeSwitch(),   // 5. Locking
            this.volumeDial,    // 6. Analog Control
            this.gunTap,        // 7. Menu Navigation
            new PinchHold(),    // 8. Complex Cursor Action
            this.airTap         // 9. Default Click / Point
        ];
    }

    // Helper to pipe to socket
    private emit(name: string): string {
        try {
            const { GestureSocket } = require("./GestureSocket");
            GestureSocket.getInstance().sendGesture(name);
        } catch (e) {
            // Ignored error
        }
        return name;
    }

    public update(hands: HandInfo[]): string | null {
        if (hands.length === 0) {
            this.lastVolumeVal = ""; // Reset volume tracking
            this.lockExpiry = 0;     // Release locks
            this.lockingSource = null;
            this.isCursorActive = false;
            this.activeGestureName = null;
            this.activeGestureStreak = 0;

            if (this.inMenuMode) {
                this.inMenuMode = false;
                return this.emit("GESTURE_CLOSE");
            }
            return null;
        }

        // Update History
        for (const hand of hands) {
            if (!this.history[hand.id]) this.history[hand.id] = [];
            const hist = this.history[hand.id];
            hist.push(hand);
            if (hist.length > this.historySize) hist.shift();
        }

        const primaryHand = hands[0];
        const currentTime = Date.now() / 1000;

        // 1. CURSOR MODE (Special handling, high priority for navigation)
        if (this.cursorMove.check([primaryHand], this.history)) {
            this.isCursorActive = true;
            this.lastCursorActiveTime = currentTime;
            this.lastCursorCoords = this.cursorMove.name.split(":")[1];
            this.activeGestureName = "CURSOR";
            
            if (this.airTap.check([primaryHand], this.history)) {
                return this.emit(`CURSOR_CLICK:${this.lastCursorCoords}`);
            }
            return this.emit(this.cursorMove.name);
        } else {
            this.isCursorActive = false;
        }

        // 2. CHECK EXISTING ACTIVE GESTURE (STICKY LOCK)
        // If we are already in a gesture (like THUMB_UP), we prioritize continuing it
        // until it's lost for a few frames. This preventing flickering.
        if (this.activeGestureName && this.activeGestureName !== "IDLE" && this.activeGestureName !== "CURSOR") {
             const activeG = this.oneHandGestures.find(g => g.name === this.activeGestureName) || 
                          this.swipes.find(g => g.name === this.activeGestureName);
             
             if (activeG && activeG.check([primaryHand], this.history)) {
                 this.activeGestureStreak++;
                 // Continue active gesture
                 if (this.activeGestureName.startsWith("VOLUME:")) {
                     const newVal = activeG.name;
                     if (newVal !== this.lastVolumeVal) {
                        this.lastVolumeVal = newVal;
                        return this.emit(newVal);
                     }
                     return null;
                 }
                 // Swipes are one-off, don't repeat them
                 if (this.activeGestureName.startsWith("SWIPE_")) return null;

                 return null; // Already emitted or continuous
             } else {
                 this.activeGestureStreak = 0;
                 this.activeGestureName = null;
             }
        }

        // 3. GLOBAL FIST (Immediate Close / Priority 0)
        if (this.fistGesture.check([primaryHand], this.history)) {
            this.inMenuMode = false;
            this.activeGestureName = "FIST_MOVE";
            return this.emit("GESTURE_CLOSE");
        }

        // 4. TWO-HAND GESTURES
        if (hands.length >= 2) {
            for (const gesture of this.twoHandGestures) {
                if (gesture.check(hands, this.history)) {
                    this.activeGestureName = gesture.name;
                    return this.emit(gesture.name);
                }
            }
            return null;
        }

        // 5. ONE-HAND GESTURES (Strict Priority Chain)
        for (const gesture of this.oneHandGestures) {
            if (gesture.check([primaryHand], this.history)) {
                // LOCK GESTURE
                this.activeGestureName = gesture.name;
                this.activeGestureStreak = 1;

                if (gesture.name.startsWith("VOLUME:")) {
                    this.lastVolumeVal = gesture.name;
                }
                
                // GunTap triggers Menu Open
                if (gesture.name === "GUN_TAP" && !this.inMenuMode) {
                    if (currentTime - this.menuCooldown > 1.0) {
                        this.inMenuMode = true;
                        this.menuCooldown = currentTime;
                        return this.emit("MENU_OPEN");
                    }
                }

                return this.emit(gesture.name);
            }
        }

        // 6. SWIPES (Lowest priority, easily confused with movement)
        for (const swipe of this.swipes) {
            if (swipe.check([primaryHand], this.history)) {
                this.activeGestureName = swipe.name;
                return this.emit(swipe.name);
            }
        }

        return null;
    }
}
