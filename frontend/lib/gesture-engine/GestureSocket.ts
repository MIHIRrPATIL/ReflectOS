import { io, Socket } from "socket.io-client";

// Singleton to manage socket connection
export class GestureSocket {
    private static instance: GestureSocket;
    private socket: Socket | null = null;
    private isConnected = false;

    private constructor() {
        // Initialize connection
        // Assuming Backend is at localhost:5000 based on previous steps
        this.socket = io("http://localhost:5000", {
            transports: ["websocket"], // Enforce websocket to avoid polling issues
            autoConnect: true
        });

        this.socket.on("connect", () => {
            console.log("[SOCKET] Connected to Backend");
            this.isConnected = true;
        });

        this.socket.on("disconnect", () => {
            console.log("[SOCKET] Disconnected");
            this.isConnected = false;
        });

        this.socket.on("connect_error", (err) => {
            console.error("[SOCKET] Connection Error:", err);
        });
    }

    public static getInstance(): GestureSocket {
        if (!GestureSocket.instance) {
            GestureSocket.instance = new GestureSocket();
        }
        return GestureSocket.instance;
    }

    public sendGesture(gestureName: string, data: any = {}) {
        this.emitMessage("GESTURE", {
            gesture: gestureName,
            ...data
        });
    }

    public sendInterrupt() {
        console.log("[INTERRUPT] Sending Signal");
        this.emitMessage("INTERRUPT", {});
    }

    public sendMenuAction(action: string, data: any = {}) {
        console.log("[TOOL] Sending Menu Action:", action);
        this.emitMessage("TOOL_CALL", {
            action: action,
            ...data
        });
    }

    public sendVoiceCommand(command: string, data: any = {}) {
        console.log("[VOICE] Sending Command:", command);
        this.emitMessage("VOICE_COMMAND", {
            command: command,
            ...data
        });
    }

    private emitMessage(type: string, payload: any) {
        if (this.socket && this.socket.connected) {
            const message = {
                uuid: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 11),
                type: type,
                payload: payload
            };
            this.socket.emit("message", message);
            return message.uuid;
        }
        console.warn(`[SOCKET] Message DROPPED (not connected): type=${type}`, payload);
        return null;
    }

    public getSocket(): Socket | null {
        return this.socket;
    }
}
