import { Gesture } from "../Gesture";
import { HandInfo } from "../HandTracker";
import { distance, distance2D } from "../primitives";

export class SpreadZoom extends Gesture {
    name = "SPREAD_ZOOM";
    protected cooldown = 1000;
    protected requiredStreak = 3;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length < 2) return false;

        const h1 = hands[0];
        const h2 = hands[1];
        const currDist = distance2D(h1.landmarks[0], h2.landmarks[0]);

        const hist1 = history[h1.id] || [];
        const hist2 = history[h2.id] || [];

        if (hist1.length < 5 || hist2.length < 5) return false;

        const prevH1 = hist1[hist1.length - 5];
        const prevH2 = hist2[hist2.length - 5];

        const prevDist = distance2D(prevH1.landmarks[0], prevH2.landmarks[0]);

        return Math.abs(currDist - prevDist) > 0.1;
    }
}

export class WristCross extends Gesture {
    name = "WRIST_CROSS";
    protected cooldown = 2000;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length < 2) return false;

        // Sort by X to find actual Left vs Right spatial position
        // Usually we track by ID, but for Cross we want physical intersection.

        const h1 = hands[0];
        const h2 = hands[1];

        const dist = distance2D(h1.landmarks[0], h2.landmarks[0]);
        if (dist > 0.15) return false; // Must be close

        // Check Logic: 
        // To strictly detect a cross, the hands must be roughly opposite their natural side?
        // Or simpler: Both wrists are close AND forearms are angled in.

        // Strict Cross: Wrist points must be close.
        // AND Middle Finger MCPs must be further apart than Wrists? No, that's V shape.

        // Let's use Palm Normals or Vectors?
        // Simple heuristic for now: Vertical Offset is small (Same height)
        if (Math.abs(h1.landmarks[0].y - h2.landmarks[0].y) > 0.1) return false;

        // Ensure they are NOT facing away?
        return true;
    }
}

export class AirMeasure extends Gesture {
    name = "AIR_MEASURE";
    protected cooldown = 1000;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length < 2) return false;

        const isPinching = (h: HandInfo) => distance(h.landmarks[4], h.landmarks[8]) < 0.05;

        return isPinching(hands[0]) && isPinching(hands[1]);
    }
}

export class DualSwipe extends Gesture {
    name = "DUAL_SWIPE";
    protected cooldown = 1000;
    protected requiredStreak = 3;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length < 2) return false;

        const h1 = hands[0];
        const h2 = hands[1];

        const h1Hist = history[h1.id];
        const h2Hist = history[h2.id];

        if (!h1Hist || h1Hist.length < 5 || !h2Hist || h2Hist.length < 5) return false;

        const h1Prev = h1Hist[h1Hist.length - 5];
        const h2Prev = h2Hist[h2Hist.length - 5];

        const v1 = h1.landmarks[0].x - h1Prev.landmarks[0].x;
        const v2 = h2.landmarks[0].x - h2Prev.landmarks[0].x;

        // Both moving same direction horizontally and fast enough
        // Increased threshold to 0.06 to reduce sensitivity
        return (v1 * v2) > 0 && Math.abs(v1) > 0.06;
    }
}

export class CurtainOpen extends Gesture {
    name = "CURTAIN_OPEN";
    protected cooldown = 2000;
    protected requiredStreak = 3; // Reduced streak for quicker entry

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length < 2) return false;

        const h1 = hands[0];
        const h2 = hands[1];

        // 1. MUST BE FISTS (Relaxed: Fingers 1-4 curled, Thumb ignored)
        // Many people keep thumb out when making a fist
        const isFist = (h: HandInfo) => h.fingersExtended.slice(1).every(f => !f);
        if (!isFist(h1) || !isFist(h2)) return false;

        const h1Hist = history[h1.id];
        const h2Hist = history[h2.id];

        if (!h1Hist || h1Hist.length < 10 || !h2Hist || h2Hist.length < 10) return false;

        const h1Prev = h1Hist[h1Hist.length - 10];
        const h2Prev = h2Hist[h2Hist.length - 10];

        // Logic: Knuckles were close, Wrists are now far
        const prevKnuckleDist = distance2D(h1Prev.landmarks[5], h2Prev.landmarks[5]);
        const currWristDist = distance2D(h1.landmarks[0], h2.landmarks[0]);
        const prevWristDist = distance2D(h1Prev.landmarks[0], h2Prev.landmarks[0]);

        // Relaxed "Moving Apart" threshold to 0.15 (was 0.2)
        // Relaxed "Start Close" threshold to 0.2 (was 0.15)
        return (currWristDist - prevWristDist) > 0.15 && prevKnuckleDist < 0.2;
    }
}

export class AirFrame extends Gesture {
    name = "AIR_FRAME";
    protected cooldown = 1000;

    detect(hands: HandInfo[], history: Record<number, HandInfo[]>): boolean {
        if (hands.length < 2) return false;

        const isLShape = (h: HandInfo) => {
            if (!h.fingersExtended[0] || !h.fingersExtended[1]) return false;
            if (h.fingersExtended[2] || h.fingersExtended[3] || h.fingersExtended[4]) return false;
            return true;
        };

        return isLShape(hands[0]) && isLShape(hands[1]);
    }
}
