"""
Generate a test Arrow file with sample TMDB movie data and random embeddings.
No API key needed - uses hardcoded popular movie data for testing.
"""

import json
import os

import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc

SAMPLE_MOVIES = [
    {"id": 550, "title": "Fight Club", "overview": "An insomniac office worker and a devil-may-care soap maker form an underground fight club that evolves into much more.", "poster_path": "/pB8BM7pdSp6B6Ih7QI4S2t0POoT.jpg", "backdrop_path": "/hZkgoQYus5dXo3H8T7Uef6DNknx.jpg", "vote_average": 8.4, "vote_count": 28000, "release_date": "1999-10-15", "genres": ["Drama", "Thriller"], "popularity": 75.0},
    {"id": 680, "title": "Pulp Fiction", "overview": "A burger-loving hit man, his philosophical partner, a drug-addled gangster's moll and a washed-up boxer converge in this sprawling, comedic crime caper.", "poster_path": "/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg", "backdrop_path": "/suaEOtk1N1sgg2MTM7oZd2cfVp3.jpg", "vote_average": 8.5, "vote_count": 27000, "release_date": "1994-09-10", "genres": ["Thriller", "Crime"], "popularity": 80.0},
    {"id": 238, "title": "The Godfather", "overview": "Spanning the years 1945 to 1955, a chronicle of the fictional Italian-American Corleone crime family.", "poster_path": "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg", "backdrop_path": "/tmU7GeKVybMWFButWEGl2M4GeiP.jpg", "vote_average": 8.7, "vote_count": 19000, "release_date": "1972-03-14", "genres": ["Drama", "Crime"], "popularity": 95.0},
    {"id": 278, "title": "The Shawshank Redemption", "overview": "Imprisoned in the 1940s for the double murder of his wife and her lover, upstanding banker Andy Dufresne begins a new life at the Shawshank prison.", "poster_path": "/9cjIGRQL0TUrEWsn1misN0XBZEY.jpg", "backdrop_path": "/kXfqcdQKsToO0OUXHcrrNCHDBzO.jpg", "vote_average": 8.7, "vote_count": 26000, "release_date": "1994-09-23", "genres": ["Drama", "Crime"], "popularity": 90.0},
    {"id": 155, "title": "The Dark Knight", "overview": "Batman raises the stakes in his war on crime. With the help of Lt. Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations that plague the streets.", "poster_path": "/qJ2tW6WMUDux911BTUOt0Pax6Mz.jpg", "backdrop_path": "/nMKdUUepR0i5zn0y1T4CsSB5ez.jpg", "vote_average": 8.5, "vote_count": 31000, "release_date": "2008-07-16", "genres": ["Drama", "Action", "Crime", "Thriller"], "popularity": 85.0},
    {"id": 13, "title": "Forrest Gump", "overview": "A man with a low IQ has accomplished great things in his life and been present during significant historic events—in each case, far exceeding what anyone imagined he could do.", "poster_path": "/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg", "backdrop_path": "/3h1JZGDhZ8nzxdgvkxha0qBqi05.jpg", "vote_average": 8.5, "vote_count": 26000, "release_date": "1994-06-23", "genres": ["Comedy", "Drama", "Romance"], "popularity": 70.0},
    {"id": 120, "title": "The Lord of the Rings: The Fellowship of the Ring", "overview": "Young hobbit Frodo Baggins, after inheriting a mysterious ring from his uncle Bilbo, must leave his home in order to keep it from falling into the hands of its evil creator.", "poster_path": "/6oom5QYQ2yQTMJIbnvbkBL9cHo6.jpg", "backdrop_path": "/pIUvQ9Ed35wlWhY2oU6OmwEgzz8.jpg", "vote_average": 8.4, "vote_count": 23000, "release_date": "2001-12-18", "genres": ["Adventure", "Fantasy", "Action"], "popularity": 88.0},
    {"id": 603, "title": "The Matrix", "overview": "Set in the 22nd century, The Matrix tells the story of a computer hacker who joins a group of underground insurgents fighting the vast and powerful computers who now rule the earth.", "poster_path": "/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg", "backdrop_path": "/fNG7i7RqMErkcqhohV2a6cV1Ehy.jpg", "vote_average": 8.2, "vote_count": 25000, "release_date": "1999-03-30", "genres": ["Action", "Science Fiction"], "popularity": 82.0},
    {"id": 157336, "title": "Interstellar", "overview": "The adventures of a group of explorers who make use of a newly discovered wormhole to surpass the limitations on human space travel and conquer the vast distances involved in an interstellar voyage.", "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", "backdrop_path": "/xJHokMbljvjADYdit5fK1DVfjko.jpg", "vote_average": 8.4, "vote_count": 34000, "release_date": "2014-11-05", "genres": ["Adventure", "Drama", "Science Fiction"], "popularity": 92.0},
    {"id": 11, "title": "Star Wars", "overview": "Princess Leia is captured and held hostage by the evil Imperial forces in their effort to take over the galactic Empire. Venturesome Luke Skywalker and dashing captain Han Solo team together with the loveable robot duo R2-D2 and C-3PO to rescue the beautiful princess and restore peace and justice in the Empire.", "poster_path": "/6FfCtAuVAW8XJjZ7eWeLibRLWTw.jpg", "backdrop_path": "/zqkmTXzjkAgXmEWLRsY4UpTWCeo.jpg", "vote_average": 8.2, "vote_count": 19000, "release_date": "1977-05-25", "genres": ["Adventure", "Action", "Science Fiction"], "popularity": 78.0},
    {"id": 496243, "title": "Parasite", "overview": "All unemployed, Ki-taek's family takes peculiar interest in the wealthy and glamorous Parks for their livelihood until they get entangled in an unexpected incident.", "poster_path": "/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg", "backdrop_path": "/TU9NIjwzjoKPwQHoHshkFcQUCG.jpg", "vote_average": 8.5, "vote_count": 17000, "release_date": "2019-05-30", "genres": ["Comedy", "Thriller", "Drama"], "popularity": 72.0},
    {"id": 569094, "title": "Spider-Man: Across the Spider-Verse", "overview": "After reuniting with Gwen Stacy, Brooklyn's full-time, friendly neighborhood Spider-Man is catapulted across the Multiverse.", "poster_path": "/8Vt6mWEReuy58HR0T7Z0fGjSjHI.jpg", "backdrop_path": "/4HodYYKEIsGOdinkGi2Ucz6X9i0.jpg", "vote_average": 8.4, "vote_count": 6000, "release_date": "2023-05-31", "genres": ["Animation", "Action", "Adventure", "Science Fiction"], "popularity": 96.0},
    {"id": 27205, "title": "Inception", "overview": "Cobb, a skilled thief who commits corporate espionage by infiltrating the subconscious of his targets is offered a chance to regain his old life as payment for a task considered to be impossible: inception.", "poster_path": "/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg", "backdrop_path": "/s3TBrRGB1iav7gFOCNx3H31MoES.jpg", "vote_average": 8.4, "vote_count": 35000, "release_date": "2010-07-15", "genres": ["Action", "Science Fiction", "Adventure"], "popularity": 91.0},
    {"id": 389, "title": "12 Angry Men", "overview": "The defense and the prosecution have rested and the jury is filing into the jury room to decide if a young Spanish-American is guilty or innocent of murdering his father.", "poster_path": "/ow3wq89wM8qd5X7hWKxiRfsFf9C.jpg", "backdrop_path": "/qqHQsStV6exghCM7zbObuYBiYxw.jpg", "vote_average": 8.5, "vote_count": 8000, "release_date": "1957-04-10", "genres": ["Drama"], "popularity": 40.0},
    {"id": 346, "title": "Seven Samurai", "overview": "A samurai answers a village's request for protection after he discovers that bandits will return to steal their crops.", "poster_path": "/8OKmBV5BUFzmozIC3pCWb5FPzds.jpg", "backdrop_path": "/sJNNMCe6C3znEOqgJvGZCiobCpB.jpg", "vote_average": 8.5, "vote_count": 3500, "release_date": "1954-04-26", "genres": ["Action", "Drama"], "popularity": 35.0},
    {"id": 424, "title": "Schindler's List", "overview": "The true story of how businessman Oskar Schindler saved over a thousand Jewish lives from the Nazis while they worked as slaves in his factory during World War II.", "poster_path": "/sF1U4EUQS8YHUYjNl3pMGNIQyr0.jpg", "backdrop_path": "/loRmRzQXZC0MYczglDYMRWJG9sf.jpg", "vote_average": 8.6, "vote_count": 15000, "release_date": "1993-11-30", "genres": ["Drama", "History", "War"], "popularity": 60.0},
    {"id": 429, "title": "The Good, the Bad and the Ugly", "overview": "While the Civil War rages, three men – aass bounty hunter, a ruthless hitman, and a Mexican bandit – comb the American Southwest in search of a strongbox containing $200,000 in stolen gold.", "poster_path": "/bX2xnavhMYjWDoZp1VM6VnU1xwe.jpg", "backdrop_path": "/gCEg2niOg82R0eNFIeLhAz3cLDm.jpg", "vote_average": 8.5, "vote_count": 8000, "release_date": "1966-12-23", "genres": ["Western"], "popularity": 45.0},
    {"id": 372058, "title": "Your Name", "overview": "High schoolers Mitsuha and Taki are complete strangers living separate lives. But one night, they suddenly switch places.", "poster_path": "/q719jXXEhOQ7msUEdYpqan9N9J9.jpg", "backdrop_path": "/dIWwZW7dJJtqC6CgWzYkNVKIUm2.jpg", "vote_average": 8.5, "vote_count": 10000, "release_date": "2016-08-26", "genres": ["Animation", "Romance", "Drama"], "popularity": 65.0},
    {"id": 129, "title": "Spirited Away", "overview": "A young girl, Chihiro, becomes trapped in a strange new world of spirits. When her parents undergo a mysterious transformation, she must call upon the courage she never knew she had to free her family.", "poster_path": "/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg", "backdrop_path": "/6oaL4DP75yABrd5EL2E2PQFRDLP.jpg", "vote_average": 8.5, "vote_count": 15000, "release_date": "2001-07-20", "genres": ["Animation", "Family", "Fantasy"], "popularity": 73.0},
    {"id": 19404, "title": "Dilwale Dulhania Le Jayenge", "overview": "Raj is a rich, carefree, happy-go-lucky second generation NRI. Simran is the daughter of Chaudhary Baldev Singh, who in spite of living abroad is very strict about Indian values.", "poster_path": "/2CAL2433ZeIihfX1Hb2139CX0pW.jpg", "backdrop_path": "/gMJngTNfaqCSCqGD4y8lVMZXKDe.jpg", "vote_average": 8.6, "vote_count": 4300, "release_date": "1995-10-20", "genres": ["Comedy", "Drama", "Romance"], "popularity": 30.0},
    {"id": 497, "title": "The Green Mile", "overview": "A supernatural tale set on death row in a Southern prison, where gentle giant John Coffey possesses the mysterious power to heal people's ailments.", "poster_path": "/velWPhVMQeQKcxggNEU8YmIo52R.jpg", "backdrop_path": "/l6hQWH9eDksNJNiXWYRkWqikOdu.jpg", "vote_average": 8.5, "vote_count": 16500, "release_date": "1999-12-10", "genres": ["Fantasy", "Drama", "Crime"], "popularity": 63.0},
    {"id": 122, "title": "The Lord of the Rings: The Return of the King", "overview": "Aragorn is revealed as the heir to the ancient kings as he, Gandalf and the other members of the broken fellowship struggle to save Gondor from Sauron's forces.", "poster_path": "/rCzpDGLbOoPwLjy3OAm5NUPOTrC.jpg", "backdrop_path": "/lXhgCODAbBXL5buk9yEmTpOoOgR.jpg", "vote_average": 8.5, "vote_count": 23000, "release_date": "2003-12-17", "genres": ["Adventure", "Fantasy", "Action"], "popularity": 86.0},
    {"id": 769, "title": "GoodFellas", "overview": "The true story of Henry Hill, a half-Irish, half-Sicilian Brooklyn kid who is adopted by neighbourhood gangsters at an early age and grows up to be a major mobster.", "poster_path": "/aKuFiU82s5ISJDx4ALNQHJ06igt.jpg", "backdrop_path": "/sw7mordbZxgITU877yTpZCud90M.jpg", "vote_average": 8.5, "vote_count": 12000, "release_date": "1990-09-12", "genres": ["Drama", "Crime"], "popularity": 55.0},
    {"id": 539, "title": "Psycho", "overview": "When larcenous real estate clerk Marion Crane goes on the lam with a wad of cash and checks into a remote motel, she encounters the mysterious owner Aunt boy Norman Bates.", "poster_path": "/yz4QVqPx3h1hD1DfqqQkCq3rmxW.jpg", "backdrop_path": "/qxlcS4qYIlgOysArBF2yFIOVbYO.jpg", "vote_average": 8.4, "vote_count": 7500, "release_date": "1960-06-16", "genres": ["Horror", "Thriller"], "popularity": 38.0},
    {"id": 244786, "title": "Whiplash", "overview": "Under the direction of a ruthless instructor, a talented young drummer begins to pursue perfection at any cost, even his humanity.", "poster_path": "/7fn624j5lj3xTme2SgiLCeuedos.jpg", "backdrop_path": "/fRGxZuo7jJUWQsVzOn60FtHnjJ7.jpg", "vote_average": 8.4, "vote_count": 14500, "release_date": "2014-10-10", "genres": ["Drama", "Music"], "popularity": 67.0},
    {"id": 637, "title": "Life Is Beautiful", "overview": "A touching story of an Italian book seller of Jewish ancestry who lives in his own little fairy tale. His creative and happy life takes a dramatic turn when Nazis start rounding up Jewish families.", "poster_path": "/74hLDKjD5aGYOotO6esUVaeISa2.jpg", "backdrop_path": "/gavyCu1UaTaTNPsVaGXT6pe5u24.jpg", "vote_average": 8.5, "vote_count": 12500, "release_date": "1997-12-20", "genres": ["Comedy", "Drama", "Romance", "War"], "popularity": 50.0},
    {"id": 438631, "title": "Dune", "overview": "Paul Atreides, a brilliant and gifted young man born into a great destiny beyond his understanding, must travel to the most dangerous planet in the universe to ensure the future of his family and his people.", "poster_path": "/d5NXSklXo0qyIYkgV94XAgMIckC.jpg", "backdrop_path": "/jYEW5xZkZk2WTrdbMGAPFuBqbDc.jpg", "vote_average": 7.8, "vote_count": 10500, "release_date": "2021-09-15", "genres": ["Science Fiction", "Adventure"], "popularity": 88.0},
    {"id": 693134, "title": "Dune: Part Two", "overview": "Follow the mythic journey of Paul Atreides as he unites with Chani and the Fremen while on a path of revenge against the conspirators who destroyed his family.", "poster_path": "/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg", "backdrop_path": "/xOMo8BRK7PfcJv9JCnx7s5hj0PX.jpg", "vote_average": 8.2, "vote_count": 5500, "release_date": "2024-02-27", "genres": ["Science Fiction", "Adventure", "Drama"], "popularity": 94.0},
    {"id": 346698, "title": "Barbie", "overview": "Barbie and Ken are having the time of their lives in the colorful and seemingly perfect world of Barbie Land. However, when they get a chance to go to the real world, they soon discover the joys and perils of living among humans.", "poster_path": "/iuFNMS8U5cb6xfzi51Dbkovj7vM.jpg", "backdrop_path": "/nHf61UzkfFno5X1ofIhugCPus2R.jpg", "vote_average": 7.0, "vote_count": 8000, "release_date": "2023-07-19", "genres": ["Comedy", "Adventure", "Fantasy"], "popularity": 70.0},
    {"id": 872585, "title": "Oppenheimer", "overview": "The story of J. Robert Oppenheimer's role in the development of the atomic bomb during World War II.", "poster_path": "/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg", "backdrop_path": "/fm6KqXpk3M2HVveHwCrBSSBaO0V.jpg", "vote_average": 8.1, "vote_count": 9000, "release_date": "2023-07-19", "genres": ["Drama", "History", "Thriller"], "popularity": 89.0},
    {"id": 299536, "title": "Avengers: Infinity War", "overview": "As the Avengers and their allies have continued to protect the world from threats too large for any one hero to handle, a new danger has emerged from the cosmic shadows: Thanos.", "poster_path": "/7WsyChQLEftFiDhRhCg16NOKrVu.jpg", "backdrop_path": "/lmZFxXgJE3vgrciwuDib0N8CfQo.jpg", "vote_average": 8.3, "vote_count": 28000, "release_date": "2018-04-25", "genres": ["Adventure", "Action", "Science Fiction"], "popularity": 87.0},
]

EMBEDDING_DIM = 1536  # Matches Qwen2 1.5B output dim


def main():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "movies.arrow")

    # Generate deterministic random embeddings (seeded by movie ID)
    # This makes KNN search return somewhat consistent results across runs
    embeddings_list = []
    for movie in SAMPLE_MOVIES:
        rng = np.random.RandomState(movie["id"])
        emb = rng.randn(EMBEDDING_DIM).astype(np.float32)
        # L2 normalize
        emb = emb / np.linalg.norm(emb)
        embeddings_list.append(emb.tolist())

    # Build Arrow table
    embedding_type = pa.list_(pa.float32(), EMBEDDING_DIM)

    table = pa.table(
        {
            "movie_id": pa.array([m["id"] for m in SAMPLE_MOVIES], type=pa.int32()),
            "title": pa.array([m["title"] for m in SAMPLE_MOVIES], type=pa.string()),
            "overview": pa.array([m["overview"] for m in SAMPLE_MOVIES], type=pa.string()),
            "poster_path": pa.array([m["poster_path"] for m in SAMPLE_MOVIES], type=pa.string()),
            "backdrop_path": pa.array([m["backdrop_path"] for m in SAMPLE_MOVIES], type=pa.string()),
            "vote_average": pa.array([m["vote_average"] for m in SAMPLE_MOVIES], type=pa.float64()),
            "vote_count": pa.array([m["vote_count"] for m in SAMPLE_MOVIES], type=pa.int32()),
            "release_date": pa.array([m["release_date"] for m in SAMPLE_MOVIES], type=pa.string()),
            "genres": pa.array([json.dumps(m["genres"]) for m in SAMPLE_MOVIES], type=pa.string()),
            "popularity": pa.array([m["popularity"] for m in SAMPLE_MOVIES], type=pa.float64()),
            "embedding": pa.FixedSizeListArray.from_arrays(
                pa.array(np.array(embeddings_list).flatten(), type=pa.float32()),
                EMBEDDING_DIM,
            ),
        },
        schema=pa.schema([
            ("movie_id", pa.int32()),
            ("title", pa.string()),
            ("overview", pa.string()),
            ("poster_path", pa.string()),
            ("backdrop_path", pa.string()),
            ("vote_average", pa.float64()),
            ("vote_count", pa.int32()),
            ("release_date", pa.string()),
            ("genres", pa.string()),
            ("popularity", pa.float64()),
            ("embedding", embedding_type),
        ]),
    )

    options = ipc.IpcWriteOptions(compression="lz4")
    with ipc.new_file(output_path, table.schema, options=options) as writer:
        writer.write_table(table)

    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"Wrote {len(SAMPLE_MOVIES)} movies to {output_path} ({file_size_kb:.0f} KB)")
    print(f"Embedding dim: {EMBEDDING_DIM}")

    # Also save JSON for reference
    json_path = os.path.join(output_dir, "movies.json")
    with open(json_path, "w") as f:
        json.dump(SAMPLE_MOVIES, f, indent=2)
    print(f"Saved movies JSON to {json_path}")


if __name__ == "__main__":
    main()
