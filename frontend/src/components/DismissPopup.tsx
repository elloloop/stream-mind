"use client";

import type { DismissReason } from "@/lib/types";

const REASONS: { value: DismissReason["reason"]; label: string; icon: string }[] = [
  { value: "seen", label: "Already seen it", icon: "eye" },
  { value: "not_interested", label: "Not interested", icon: "x" },
  { value: "not_in_mood", label: "Not in the mood", icon: "clock" },
  { value: "bad_suggestion", label: "Bad suggestion", icon: "thumbsdown" },
];

interface DismissPopupProps {
  onSelect: (reason: DismissReason["reason"]) => void;
  onCancel: () => void;
  position?: { x: number; y: number };
}

export default function DismissPopup({ onSelect, onCancel }: DismissPopupProps) {
  return (
    <div className="fixed inset-0 z-[60]" onClick={onCancel}>
      <div
        className="fixed inset-x-0 bottom-0 md:inset-auto md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-72 bg-[#1a1a1a] md:rounded-xl rounded-t-xl border border-white/10 shadow-2xl animate-slideUp md:animate-fadeInScale overflow-hidden safe-bottom"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="drag-handle md:hidden" />
        <div className="px-1 py-2">
          <p className="px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
            Why dismiss?
          </p>
          {REASONS.map((reason) => (
            <button
              key={reason.value}
              onClick={() => onSelect(reason.value)}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-200 hover:bg-white/5 transition-colors rounded-lg min-h-[44px]"
            >
              <span className="w-5 h-5 flex items-center justify-center text-gray-500">
                {reason.icon === "eye" && (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                  </svg>
                )}
                {reason.icon === "x" && (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                  </svg>
                )}
                {reason.icon === "clock" && (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                  </svg>
                )}
                {reason.icon === "thumbsdown" && (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7.498 15.25H4.372c-1.026 0-1.945-.694-2.054-1.715a12.137 12.137 0 0 1-.068-1.285c0-2.848.992-5.464 2.649-7.521C5.287 4.247 5.886 4 6.504 4h4.016a4.5 4.5 0 0 1 1.423.23l3.114 1.04a4.5 4.5 0 0 0 1.423.23h1.294M7.498 15.25c.618 0 .991.724.725 1.282A7.471 7.471 0 0 0 7.5 19.75 2.25 2.25 0 0 0 9.75 22a.75.75 0 0 0 .75-.75v-.633c0-.573.11-1.14.322-1.672.304-.76.93-1.33 1.653-1.715a9.04 9.04 0 0 0 2.86-2.4c.498-.634 1.226-1.08 2.032-1.08h.384" />
                  </svg>
                )}
              </span>
              {reason.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
