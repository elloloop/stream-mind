import type { Metadata } from "next";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface PageProps {
  params: Promise<{ id: string }>;
}

async function fetchMovie(id: string) {
  try {
    const res = await fetch(`${API_BASE}/api/movie/${id}`, { next: { revalidate: 3600 } });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const movie = await fetchMovie(id);

  if (!movie) {
    return { title: "Movie not found — StreamMind" };
  }

  const year = movie.release_date?.slice(0, 4);
  const title = `${movie.title}${year ? ` (${year})` : ""} — StreamMind`;
  const description = movie.overview?.slice(0, 200) || "Discover this movie on StreamMind";
  const posterUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : undefined;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      images: posterUrl ? [{ url: posterUrl, width: 500, height: 750 }] : [],
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: posterUrl ? [posterUrl] : [],
    },
  };
}

export default async function MoviePage({ params }: PageProps) {
  const { id } = await params;
  // Client-side redirect to home with movie modal
  return (
    <main className="min-h-screen bg-[#0c0c0c] flex items-center justify-center">
      <div className="text-center p-8">
        <p className="text-gray-400 mb-4">Loading movie details...</p>
        <script
          dangerouslySetInnerHTML={{
            __html: `window.location.href = '/?movie=${id}';`,
          }}
        />
      </div>
    </main>
  );
}
