import { Landmark, distance, Vector3, subtract, crossProduct, normalize, distance2D } from "./primitives";

export interface HandInfo {
    id: number;
    landmarks: Landmark[]; // 0..20
    handedness: "Left" | "Right";
    palmNormal: Vector3;
    fingersExtended: boolean[]; // [thumb, index, middle, ring, pinky]
    wristCoords: { x: number; y: number };
    scale: number; // Distance from wrist to middle finger MCP
}

export class HandTracker {
    private nextHandId = 0;
    private prevHands: { id: number; coords: { x: number; y: number } }[] = [];

    constructor() { }

    public process(
        landmarksList: Landmark[][],
        handednessList: { categoryName: string }[]
    ): HandInfo[] {
        const handsInfo: HandInfo[] = [];

        // 1. Collect coordinates for ID tracking
        const currentHandsCoords = landmarksList.map((lm) => ({ x: lm[0].x, y: lm[0].y }));
        const ids = this.assignIds(currentHandsCoords);

        // 2. Build HandInfo objects
        for (let i = 0; i < landmarksList.length; i++) {
            const lm = landmarksList[i];

            // Safety check for handedness
            let category = "Right";
            if (handednessList[i] && handednessList[i].categoryName) {
                category = handednessList[i].categoryName;
            }
            const handedness = (category === "Left" ? "Left" : "Right") as "Left" | "Right";

            const palmNormal = this.computePalmNormal(lm);
            const fingers = this.getFingerStates(lm, handedness);
            const scale = distance(lm[0], lm[9]); // Wrist to Middle MCP

            handsInfo.push({
                id: ids[i],
                landmarks: lm,
                handedness,
                palmNormal,
                fingersExtended: fingers,
                wristCoords: { x: lm[0].x, y: lm[0].y },
                scale
            });
        }

        return handsInfo;
    }

    private computePalmNormal(lm: Landmark[]): Vector3 {
        const wrist = [lm[0].x, lm[0].y, lm[0].z] as Vector3;
        const indexMcp = [lm[5].x, lm[5].y, lm[5].z] as Vector3;
        const pinkyMcp = [lm[17].x, lm[17].y, lm[17].z] as Vector3;

        const v1 = subtract(indexMcp, wrist);
        const v2 = subtract(pinkyMcp, wrist);
        const normal = normalize(crossProduct(v1, v2));

        return normal;
    }

    private getFingerStates(lm: Landmark[], handedness: "Left" | "Right"): boolean[] {
        // 0: Thumb, 1: Index, 2: Middle, 3: Ring, 4: Pinky
        const tips = [8, 12, 16, 20];
        const pips = [6, 10, 14, 18];

        const fingers: boolean[] = [];

        // Check if TIP is HIGHER (smaller Y) than PIP
        for (let i = 0; i < 4; i++) {
            fingers.push(lm[tips[i]].y < lm[pips[i]].y);
        }

        const thumbTipX = lm[4].x;
        const thumbIpX = lm[3].x;

        let thumbExtended = false;
        if (handedness === "Left") {
            thumbExtended = thumbTipX > thumbIpX;
        } else {
            thumbExtended = thumbTipX < thumbIpX;
        }

        return [thumbExtended, ...fingers];
    }

    private assignIds(currentCoords: { x: number; y: number }[]): number[] {
        const assignedIds: number[] = [];
        const usedPrevIndices = new Set<number>();

        for (const curr of currentCoords) {
            let minDist = Infinity;
            let bestMatchIdx = -1;

            for (let i = 0; i < this.prevHands.length; i++) {
                if (usedPrevIndices.has(i)) continue;

                const prev = this.prevHands[i];
                const d = distance2D({ x: curr.x, y: curr.y, z: 0 }, { x: prev.coords.x, y: prev.coords.y, z: 0 });

                if (d < minDist) {
                    minDist = d;
                    bestMatchIdx = i;
                }
            }

            if (bestMatchIdx !== -1 && minDist < 0.2) {
                assignedIds.push(this.prevHands[bestMatchIdx].id);
                usedPrevIndices.add(bestMatchIdx);
            } else {
                assignedIds.push(this.nextHandId++);
            }
        }

        this.prevHands = currentCoords.map((c, i) => ({ id: assignedIds[i], coords: c }));

        return assignedIds;
    }
}
