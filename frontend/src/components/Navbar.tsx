"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 z-40 w-full bg-gradient-to-b from-black/90 to-transparent">
      <div className="flex items-center justify-between px-8 md:px-16 py-4">
        {/* Logo */}
        <Link href="/" className="text-2xl font-bold text-red-600 tracking-wide">
          STREAMMIND
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-6 text-sm">
          <Link
            href="/"
            className={`transition-colors ${
              pathname === "/"
                ? "text-white font-semibold"
                : "text-gray-300 hover:text-white"
            }`}
          >
            Home
          </Link>
          <Link
            href="/history"
            className={`transition-colors ${
              pathname === "/history"
                ? "text-white font-semibold"
                : "text-gray-300 hover:text-white"
            }`}
          >
            My List
          </Link>
        </div>
      </div>
    </nav>
  );
}
