"use client";

function Pulse({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-white/5 ${className}`} />;
}

export function HeroSkeleton() {
  return (
    <div className="relative h-[65vh] min-h-[460px] w-full bg-[#0c0c0c]">
      <div className="absolute inset-0 bg-gradient-to-t from-[#0c0c0c] via-[#0c0c0c]/50 to-[#141414]" />
      <div className="relative flex h-full flex-col justify-end px-8 pb-20 md:px-16 gap-3">
        <Pulse className="h-10 w-80 max-w-full" />
        <div className="flex gap-2">
          <Pulse className="h-6 w-16 rounded-full" />
          <Pulse className="h-6 w-12" />
          <Pulse className="h-6 w-32" />
        </div>
        <Pulse className="h-16 w-full max-w-lg" />
        <div className="flex gap-3 mt-2">
          <Pulse className="h-10 w-28 rounded-lg" />
          <Pulse className="h-10 w-32 rounded-lg" />
        </div>
      </div>
    </div>
  );
}

export function MovieCardSkeleton() {
  return (
    <div className="flex-shrink-0 w-[120px] sm:w-[140px] md:w-[180px] lg:w-[200px]">
      <Pulse className="aspect-[2/3] w-full rounded-lg" />
      <Pulse className="mt-1.5 h-3 w-3/4" />
    </div>
  );
}

export function LaneSkeleton() {
  return (
    <div className="mb-8 animate-fadeIn">
      <div className="px-8 md:px-16 mb-3">
        <Pulse className="h-6 w-40" />
      </div>
      <div className="flex gap-3 px-8 md:px-16 overflow-hidden">
        {Array.from({ length: 8 }).map((_, i) => (
          <MovieCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}

export function SearchBarSkeleton() {
  return (
    <div className="px-8 md:px-16 py-6">
      <Pulse className="h-12 w-full max-w-2xl rounded-lg" />
    </div>
  );
}
