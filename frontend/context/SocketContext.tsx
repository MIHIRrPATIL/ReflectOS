"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';
import { Socket } from 'socket.io-client';
import { GestureSocket } from '../lib/gesture-engine/GestureSocket';

interface SocketContextType {
    socket: Socket | null;
    isConnected: boolean;
}

const SocketContext = createContext<SocketContextType>({
    socket: null,
    isConnected: false
});

export const SocketProvider = ({ children }: { children: React.ReactNode }) => {
    const [socket, setSocket] = useState<Socket | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const gestureSocket = GestureSocket.getInstance();
        const s = gestureSocket.getSocket();
        setSocket(s);

        if (s) {
            setIsConnected(s.connected);
            
            s.on('connect', () => setIsConnected(true));
            s.on('disconnect', () => setIsConnected(false));

            return () => {
                s.off('connect');
                s.off('disconnect');
            };
        }
    }, []);

    return (
        <SocketContext.Provider value={{ socket, isConnected }}>
            {children}
        </SocketContext.Provider>
    );
};

export const useSocket = () => useContext(SocketContext);
