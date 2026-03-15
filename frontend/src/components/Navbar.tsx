"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 z-40 w-full bg-gradient-to-b from-black/95 to-transparent backdrop-blur-sm safe-top hidden md:block">
      <div className="flex items-center justify-between px-8 md:px-16 py-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-yellow-400 flex items-center justify-center">
            <svg className="h-4 w-4 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <span className="text-xl font-bold tracking-tight text-white">
            stream<span className="text-yellow-400">mind</span>
          </span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-6 text-sm">
          <Link
            href="/"
            className={`transition-colors ${
              pathname === "/"
                ? "text-yellow-400 font-semibold"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Discover
          </Link>
          <Link
            href="/watchlist"
            className={`transition-colors ${
              pathname === "/watchlist"
                ? "text-yellow-400 font-semibold"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Watchlist
          </Link>
          <Link
            href="/history"
            className={`transition-colors ${
              pathname === "/history"
                ? "text-yellow-400 font-semibold"
                : "text-gray-400 hover:text-white"
            }`}
          >
            History
          </Link>
          <Link
            href="/profile"
            className={`transition-colors ${
              pathname === "/profile"
                ? "text-yellow-400 font-semibold"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Profile
          </Link>
        </div>
      </div>
    </nav>
  );
}
