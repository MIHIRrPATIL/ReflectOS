"use client";
import React, { createContext, useContext, useState } from 'react';

interface HUDContextType {
    zenMode: boolean;
    setZenMode: (val: boolean) => void;
    toggleZenMode: () => void;
}

const HUDContext = createContext<HUDContextType>({
    zenMode: false,
    setZenMode: () => {},
    toggleZenMode: () => {}
});

export const HUDProvider = ({ children }: { children: React.ReactNode }) => {
    const [zenMode, setZenMode] = useState(false);
    const toggleZenMode = () => setZenMode(prev => !prev);

    return (
        <HUDContext.Provider value={{ zenMode, setZenMode, toggleZenMode }}>
            {children}
        </HUDContext.Provider>
    );
};

export const useHUD = () => useContext(HUDContext);
