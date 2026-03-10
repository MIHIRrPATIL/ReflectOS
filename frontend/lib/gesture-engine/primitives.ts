import { HandLandmarkerResult } from "@mediapipe/tasks-vision";

export type Landmark = { x: number; y: number; z: number };

export function distance(p1: Landmark, p2: Landmark): number {
    return Math.sqrt(
        Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2) + Math.pow(p1.z - p2.z, 2)
    );
}

export function distance2D(p1: Landmark, p2: Landmark): number {
    return Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2));
}

export function mean(values: number[]): number {
    if (values.length === 0) return 0;
    return values.reduce((a, b) => a + b, 0) / values.length;
}

export type Vector3 = [number, number, number];

export function subtract(v1: Vector3, v2: Vector3): Vector3 {
    return [v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]];
}

export function crossProduct(a: Vector3, b: Vector3): Vector3 {
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ];
}

export function normalize(v: Vector3): Vector3 {
    const len = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    if (len < 1e-6) return [0, 0, 0];
    return [v[0] / len, v[1] / len, v[2] / len];
}

export function dot(v1: Vector3, v2: Vector3): number {
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2];
}
