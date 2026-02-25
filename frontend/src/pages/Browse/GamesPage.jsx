import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { SiPlaystation } from "react-icons/si";
import { rentalsAPI } from "../../api";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import "./Browse.css";

const GENRES = [
  { value: "", label: "All Genres" },
  { value: "action", label: "Action" },
  { value: "adventure", label: "Adventure" },
  { value: "rpg", label: "RPG" },
  { value: "sports", label: "Sports" },
  { value: "racing", label: "Racing" },
  { value: "shooter", label: "Shooter" },
  { value: "puzzle", label: "Puzzle" },
  { value: "horror", label: "Horror" },
  { value: "simulation", label: "Simulation" },
  { value: "fighting", label: "Fighting" },
];

const PLATFORMS = [
  { value: "", label: "All Platforms" },
  { value: "ps5", label: "PS5" },
  { value: "ps4", label: "PS4" },
  { value: "ps4_ps5", label: "PS4 & PS5" },
];

export default function GamesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [genre, setGenre] = useState(searchParams.get("genre") || "");
  const [platform, setPlatform] = useState(searchParams.get("platform") || "");

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (genre) params.genre = genre;
    if (platform) params.platform = platform;
    rentalsAPI
      .listGames(params)
      .then(({ data }) => setGames(data.results || data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [genre, platform]);

  const updateParams = (key, value) => {
    const next = { ...Object.fromEntries(searchParams) };
    if (value) next[key] = value;
    else delete next[key];
    setSearchParams(next);
  };

  return (
    <div className="browse">
      <h1>Games</h1>

      {/* Filters */}
      <div className="browse__filters-group">
        <div className="browse__filters">
          {GENRES.map((g) => (
            <button
              key={g.value}
              className={`filter-chip ${genre === g.value ? "filter-chip--active" : ""}`}
              onClick={() => {
                setGenre(g.value);
                updateParams("genre", g.value);
              }}
            >
              {g.label}
            </button>
          ))}
        </div>
        <div className="browse__filters">
          {PLATFORMS.map((p) => (
            <button
              key={p.value}
              className={`filter-chip ${platform === p.value ? "filter-chip--active" : ""}`}
              onClick={() => {
                setPlatform(p.value);
                updateParams("platform", p.value);
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : games.length === 0 ? (
        <p className="empty">No games found.</p>
      ) : (
        <div className="card-grid">
          {games.map((g) => (
            <Link to={`/games/${g.slug}`} key={g.id} className="card">
              <div className="card__img">
                {g.cover_image ? (
                  <img src={g.cover_image} alt={g.title} />
                ) : (
                  <div className="card__img-placeholder">
                    <SiPlaystation />
                  </div>
                )}
              </div>
              <div className="card__body">
                <div className="card__tags">
                  <span className="card__badge">{g.platform_display}</span>
                  <span className="card__badge card__badge--alt">{g.genre_display}</span>
                </div>
                <h3 className="card__title">{g.title}</h3>
                <p className="card__price">
                  ₹{g.daily_price}<span>/day</span>
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
