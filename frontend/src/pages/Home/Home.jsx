import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { SiPlaystation } from "react-icons/si";
import { FiArrowRight } from "react-icons/fi";
import { rentalsAPI } from "../../api";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import "./Home.css";

export default function Home() {
  const [consoles, setConsoles] = useState([]);
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [consolesRes, gamesRes] = await Promise.all([
          rentalsAPI.listConsoles({ page_size: 6 }),
          rentalsAPI.listGames({ page_size: 6 }),
        ]);
        setConsoles(consolesRes.data.results || consolesRes.data);
        setGames(gamesRes.data.results || gamesRes.data);
      } catch (err) {
        console.error("Failed to fetch home data:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="home">
      {/* ── Hero ──────────────────────────────────────────────── */}
      <section className="hero">
        <div className="hero__content">
          <h1 className="hero__title">
            Rent. Play. <span className="hero__highlight">Return.</span>
          </h1>
          <p className="hero__subtitle">
            Premium PlayStation consoles and the latest games — delivered to your
            door or pick up from our store. No commitment, just gaming.
          </p>
          <div className="hero__actions">
            <Link to="/consoles" className="btn btn--primary btn--lg">
              Browse Consoles <FiArrowRight />
            </Link>
            <Link to="/games" className="btn btn--outline btn--lg">
              Browse Games
            </Link>
          </div>
        </div>
        <div className="hero__graphic">
          <SiPlaystation />
        </div>
      </section>

      {/* ── Console Grid ─────────────────────────────────────── */}
      <section className="section">
        <div className="section__header">
          <h2>Featured Consoles</h2>
          <Link to="/consoles" className="section__link">
            View All <FiArrowRight />
          </Link>
        </div>
        <div className="card-grid">
          {consoles.map((c) => (
            <Link to={`/consoles/${c.slug}`} key={c.id} className="card">
              <div className="card__img">
                {c.primary_image?.image ? (
                  <img src={c.primary_image.image} alt={c.name} />
                ) : (
                  <div className="card__img-placeholder">
                    <SiPlaystation />
                  </div>
                )}
              </div>
              <div className="card__body">
                <span className="card__badge">{c.console_type_display}</span>
                <h3 className="card__title">{c.name}</h3>
                <p className="card__price">
                  ₹{c.daily_price}<span>/day</span>
                </p>
                {!c.is_in_stock && <span className="card__oos">Out of Stock</span>}
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── Game Grid ────────────────────────────────────────── */}
      <section className="section">
        <div className="section__header">
          <h2>Popular Games</h2>
          <Link to="/games" className="section__link">
            View All <FiArrowRight />
          </Link>
        </div>
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
      </section>
    </div>
  );
}
