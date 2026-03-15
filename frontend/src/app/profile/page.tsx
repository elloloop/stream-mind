"use client";

import { useState, useEffect } from "react";
import { getDeviceId, getSyncCode } from "@/lib/identity";
import { getWatchedIds, getLikedMovieIds, getWatchlistIds, getDismissedIds } from "@/lib/storage";
import { ToastProvider, useToast } from "@/components/Toast";
import Navbar from "@/components/Navbar";
import BottomNav from "@/components/BottomNav";

function ProfileContent() {
  const [deviceId, setDeviceId] = useState("");
  const [syncCode, setSyncCode] = useState("");
  const [stats, setStats] = useState({ watched: 0, liked: 0, watchlist: 0, dismissed: 0 });
  const { toast } = useToast();

  useEffect(() => {
    setDeviceId(getDeviceId());
    setSyncCode(getSyncCode());
    setStats({
      watched: getWatchedIds().length,
      liked: getLikedMovieIds().length,
      watchlist: getWatchlistIds().length,
      dismissed: getDismissedIds().length,
    });
  }, []);

  const handleCopySyncCode = async () => {
    try {
      await navigator.clipboard.writeText(syncCode);
      toast("Sync code copied!", "success");
    } catch {
      toast("Couldn't copy", "error");
    }
  };

  return (
    <main className="min-h-screen bg-[#0c0c0c]">
      <Navbar />

      <div className="px-6 md:px-16 pt-6 md:pt-24 pb-8 max-w-xl">
        <h1 className="text-2xl md:text-3xl font-bold text-white mb-8">Profile</h1>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 mb-8">
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4">
            <p className="text-2xl font-bold text-white">{stats.watched}</p>
            <p className="text-xs text-gray-500 mt-1">Watched</p>
          </div>
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4">
            <p className="text-2xl font-bold text-white">{stats.liked}</p>
            <p className="text-xs text-gray-500 mt-1">Liked</p>
          </div>
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4">
            <p className="text-2xl font-bold text-white">{stats.watchlist}</p>
            <p className="text-xs text-gray-500 mt-1">Watchlist</p>
          </div>
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4">
            <p className="text-2xl font-bold text-white">{stats.dismissed}</p>
            <p className="text-xs text-gray-500 mt-1">Dismissed</p>
          </div>
        </div>

        {/* Sync Code */}
        <div className="rounded-xl bg-white/[0.03] border border-white/5 p-5 mb-6">
          <h2 className="text-sm font-semibold text-white mb-1">Sync Code</h2>
          <p className="text-xs text-gray-500 mb-4">Use this code to transfer your data to another device</p>

          <div className="flex items-center gap-3">
            <div className="flex-1 bg-black/30 rounded-lg px-4 py-3 font-mono text-lg tracking-[0.3em] text-yellow-400 text-center select-all">
              {syncCode}
            </div>
            <button
              onClick={handleCopySyncCode}
              className="rounded-lg bg-white/5 border border-white/10 p-3 text-gray-400 hover:text-white hover:bg-white/10 transition-colors min-h-[44px]"
              title="Copy sync code"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
              </svg>
            </button>
          </div>
        </div>

        {/* Device ID */}
        <div className="rounded-xl bg-white/[0.03] border border-white/5 p-5">
          <h2 className="text-sm font-semibold text-white mb-1">Device ID</h2>
          <p className="text-xs text-gray-500 mb-3">Your anonymous profile identifier</p>
          <p className="font-mono text-xs text-gray-600 break-all">{deviceId}</p>
        </div>

        <p className="mt-6 text-xs text-gray-600 text-center">
          All your data is stored locally on this device. No account required.
        </p>
      </div>

      <div className="h-24 md:h-20" />
      <BottomNav />
    </main>
  );
}

export default function ProfilePage() {
  return (
    <ToastProvider>
      <ProfileContent />
    </ToastProvider>
  );
}
