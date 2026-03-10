import type { Metadata } from "next";
import "./globals.css";
import GestureFeedback from "@/components/GestureFeedback";
import YouTubePlayer from "@/components/YouTubePlayer";
import { SocketProvider } from "@/context/SocketContext";

export const metadata: Metadata = {
  title: "ReflectOS",
  description: "Personal Operating System — HUD Interface",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <SocketProvider>
          {/* Dot grid background layer */}
          <div className="hud-grid" />
          <GestureFeedback />
          <YouTubePlayer />
          {children}
        </SocketProvider>
      </body>
    </html>
  );
}
