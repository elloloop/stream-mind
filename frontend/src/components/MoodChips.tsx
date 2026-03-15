"use client";

const MOODS = [
  { label: "Feel Good", query: "uplifting feel-good movies that leave you smiling" },
  { label: "Mind-Bending", query: "mind-bending psychological movies with plot twists" },
  { label: "Edge of Seat", query: "intense suspenseful thrillers that keep you on the edge of your seat" },
  { label: "Date Night", query: "romantic movies perfect for date night" },
  { label: "Nostalgic", query: "nostalgic classic movies from the 80s and 90s" },
  { label: "Epic Adventure", query: "epic adventure movies with grand scale and world-building" },
  { label: "Dark & Gritty", query: "dark gritty crime dramas with morally complex characters" },
  { label: "Laugh Out Loud", query: "hilarious comedy movies that make you laugh out loud" },
];

interface MoodChipsProps {
  onSelect: (query: string) => void;
  activeQuery?: string;
  disabled?: boolean;
}

export default function MoodChips({ onSelect, activeQuery, disabled }: MoodChipsProps) {
  return (
    <div className="flex gap-2 overflow-x-auto scrollbar-hide snap-lane momentum-scroll py-1 px-8 md:px-16">
      {MOODS.map((mood) => {
        const isActive = activeQuery === mood.query;
        return (
          <button
            key={mood.label}
            onClick={() => onSelect(mood.query)}
            disabled={disabled}
            className={`flex-shrink-0 rounded-full px-4 py-2 text-sm font-medium transition-all select-none min-h-[36px] ${
              isActive
                ? "bg-yellow-400/10 border border-yellow-400/50 text-yellow-400"
                : "bg-white/5 border border-white/10 text-gray-300 hover:border-yellow-400/30 hover:text-white"
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            {mood.label}
          </button>
        );
      })}
    </div>
  );
}
