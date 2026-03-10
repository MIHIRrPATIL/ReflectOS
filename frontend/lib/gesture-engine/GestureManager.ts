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

    // Locking
    private lockExpiry = 0;
    private lockingSource: "VOLUME" | "OTHER" | null = null;

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

        this.oneHandGestures = [
            this.verticalSplit,
            this.cursorMove,
            this.volumeDial,
            ...this.swipes,
            new ModeSwitch(),
            new PinchHold(),
            this.fistGesture,
            new ThumbUp(),
            new ThumbDown(),
            this.airTap
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

        // 1. CURSOR MODE (High Priority)
        if (this.cursorMove.check([primaryHand], this.history)) {
            this.isCursorActive = true;
            this.lastCursorActiveTime = currentTime;
            this.lastCursorCoords = this.cursorMove.name.split(":")[1];

            // While Cursor is moving, check for Air Tap (Click)
            if (this.airTap.check([primaryHand], this.history)) {
                return this.emit(`CURSOR_CLICK:${this.lastCursorCoords}`);
            }

            return this.emit(this.cursorMove.name);
        } else {
            this.isCursorActive = false;

            // GRACE PERIOD: Allow Air Tap to trigger click even if pointing pose is lost briefly
            if (currentTime - this.lastCursorActiveTime < this.cursorGracePeriod) {
                if (this.airTap.check([primaryHand], this.history)) {
                    return this.emit(`CURSOR_CLICK:${this.lastCursorCoords}`);
                }
            }
        }

        // 0. CHECK GLOBAL LOCK
        if (currentTime < this.lockExpiry) {
            // Check Fist to Break Lock/Close
            if (this.fistGesture.check([primaryHand], this.history)) {
                this.lockExpiry = 0;
                this.inMenuMode = false;
                return this.emit("GESTURE_CLOSE");
            }

            if (this.lockingSource === "VOLUME") {
                if (this.volumeDial.check([primaryHand], this.history)) {
                    this.lockExpiry = currentTime + 3.0;
                    return this.emit(this.volumeDial.name);
                }
            }
            return null; // Blocked
        }

        // 0.5 GLOBAL FIST (Immediate Close)
        if (this.fistGesture.check([primaryHand], this.history)) {
            this.inMenuMode = false;
            return this.emit("GESTURE_CLOSE");
        }

        // 1. MENU MODE
        if (this.inMenuMode) {
            // 1. Double Tap Detection
            if (this.airTap.check([primaryHand], this.history)) {
                if (currentTime - this.lastTapTime < 1.2) { // 1.2s window
                    this.inMenuMode = false; // Close Menu
                    return this.emit("MENU_SELECT");
                } else {
                    this.lastTapTime = currentTime;
                    return this.emit("MENU_TAP");
                }
            }

            // 2. Wheel Navigation
            if (this.menuWheel.check([primaryHand], this.history)) {
                return this.emit(this.menuWheel.name);
            }

            return null;
        }
        else {
            // 2. DEFAULT MODE

            // Priority 1: Two-Hand Gestures
            if (hands.length >= 2) {
                for (const gesture of this.twoHandGestures) {
                    if (gesture.check(hands, this.history)) {
                        if (["WRIST_CROSS", "DUAL_SWIPE", "AIR_FRAME", "CURTAIN_OPEN"].includes(gesture.name)) {
                            this.lockExpiry = currentTime + 3.0;
                            this.lockingSource = "OTHER";
                        }
                        return this.emit(gesture.name);
                    }
                }

                if (this.fistGesture.check([primaryHand], this.history)) {
                    this.inMenuMode = false;
                    return this.emit("GESTURE_CLOSE");
                }

                return null;
            }

            // Priority 2: Volume Dial
            if (this.volumeDial.check([primaryHand], this.history)) {
                this.lockExpiry = currentTime + 3.0;
                this.lockingSource = "VOLUME";
                const newVal = this.volumeDial.name;
                if (newVal !== this.lastVolumeVal) {
                    this.lastVolumeVal = newVal;
                    return this.emit(newVal);
                }
                return newVal;
            }

            // Priority 3: Swipes
            for (const swipe of this.swipes) {
                if (swipe.check([primaryHand], this.history)) {
                    return this.emit(swipe.name);
                }
            }

            // Priority 4: Menu Trigger
            if (this.gunTap.check([primaryHand], this.history)) {
                if (currentTime - this.menuCooldown > 1.0) {
                    this.inMenuMode = true;
                    this.menuCooldown = currentTime;
                    return this.emit("MENU_OPEN");
                }
            }

            // Priority 5: Others
            for (const gesture of this.oneHandGestures) {
                if (gesture instanceof SwipeLeft || gesture instanceof VolumeDial || gesture instanceof GunTap || gesture instanceof SwipeRight || gesture instanceof SwipeUp || gesture instanceof SwipeDown || gesture instanceof VerticalSplit || gesture instanceof CursorMove) continue;

                if (gesture.check([primaryHand], this.history)) {
                    return this.emit(gesture.name);
                }
            }
        }

        return null;
    }
}
