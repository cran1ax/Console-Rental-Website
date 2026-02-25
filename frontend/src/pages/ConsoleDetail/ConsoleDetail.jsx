import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { FiCheckCircle, FiXCircle } from "react-icons/fi";
import { SiPlaystation } from "react-icons/si";
import { rentalsAPI } from "../../api";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import StarRating from "../../components/ui/StarRating";
import "./ConsoleDetail.css";

export default function ConsoleDetail() {
  const { slug } = useParams();
  const [console_, setConsole] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  /* ── Availability check state ──────────────────────────────── */
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [availability, setAvailability] = useState(null);
  const [checkingAvail, setCheckingAvail] = useState(false);

  useEffect(() => {
    async function fetchConsole() {
      try {
        const [detailRes, statsRes, reviewsRes] = await Promise.all([
          rentalsAPI.getConsole(slug),
          rentalsAPI.getConsoleReviewStats(slug),
          rentalsAPI.getConsoleReviews(slug, { page_size: 5 }),
        ]);
        setConsole(detailRes.data);
        setStats(statsRes.data);
        setReviews(reviewsRes.data.results || reviewsRes.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchConsole();
  }, [slug]);

  const handleCheckAvailability = async () => {
    if (!startDate || !endDate) return;
    setCheckingAvail(true);
    try {
      const { data } = await rentalsAPI.checkConsoleAvailability(slug, startDate, endDate);
      setAvailability(data);
    } catch {
      setAvailability(null);
    } finally {
      setCheckingAvail(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (!console_) return <p className="empty">Console not found.</p>;

  return (
    <div className="console-detail">
      {/* ── Header Row ───────────────────────────────────────── */}
      <div className="detail-grid">
        {/* Image */}
        <div className="detail__image">
          {console_.images?.length > 0 ? (
            <img
              src={console_.images[0].image}
              alt={console_.name}
            />
          ) : console_.image ? (
            <img src={console_.image} alt={console_.name} />
          ) : (
            <div className="detail__image-placeholder">
              <SiPlaystation />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="detail__info">
          <span className="detail__type">{console_.console_type_display}</span>
          <h1>{console_.name}</h1>

          {stats && (
            <div className="detail__rating">
              <StarRating value={stats.average_rating || 0} />
              <span className="detail__review-count">
                ({stats.total_reviews} review{stats.total_reviews !== 1 && "s"})
              </span>
            </div>
          )}

          <p className="detail__desc">{console_.description}</p>

          {/* Pricing */}
          <div className="pricing-grid">
            <div className="pricing-card">
              <span className="pricing-card__label">Daily</span>
              <span className="pricing-card__value">₹{console_.daily_price}</span>
            </div>
            <div className="pricing-card">
              <span className="pricing-card__label">Weekly</span>
              <span className="pricing-card__value">₹{console_.weekly_price}</span>
            </div>
            <div className="pricing-card">
              <span className="pricing-card__label">Monthly</span>
              <span className="pricing-card__value">₹{console_.monthly_price}</span>
            </div>
            <div className="pricing-card pricing-card--muted">
              <span className="pricing-card__label">Deposit</span>
              <span className="pricing-card__value">₹{console_.security_deposit}</span>
            </div>
          </div>

          <p className="detail__stock">
            <strong>Condition:</strong> {console_.condition_display}
            &nbsp;&bull;&nbsp;
            <strong>Available:</strong> {console_.available_quantity}/{console_.stock_quantity}
          </p>

          {/* Availability Check */}
          <div className="avail-check">
            <h3>Check Availability</h3>
            <div className="avail-check__row">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <span>to</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
              <button
                className="btn btn--primary"
                onClick={handleCheckAvailability}
                disabled={checkingAvail || !startDate || !endDate}
              >
                {checkingAvail ? "Checking…" : "Check"}
              </button>
            </div>

            {availability && (
              <div className={`avail-result ${availability.is_available ? "avail-result--ok" : "avail-result--no"}`}>
                {availability.is_available ? (
                  <><FiCheckCircle /> Available for selected dates!</>
                ) : (
                  <><FiXCircle /> {availability.reason}</>
                )}
              </div>
            )}
          </div>

          {/* Book CTA */}
          <Link
            to={`/book?console=${console_.id}`}
            className="btn btn--primary btn--lg detail__cta"
          >
            Rent This Console
          </Link>
        </div>
      </div>

      {/* ── Reviews ──────────────────────────────────────────── */}
      <section className="section">
        <h2>Customer Reviews</h2>
        {reviews.length === 0 ? (
          <p className="empty">No reviews yet.</p>
        ) : (
          <div className="reviews-list">
            {reviews.map((r) => (
              <div key={r.id} className="review-card">
                <div className="review-card__header">
                  <StarRating value={r.rating} size={14} />
                  <span className="review-card__author">{r.user_name}</span>
                  <span className="review-card__date">
                    {new Date(r.created_at).toLocaleDateString()}
                  </span>
                </div>
                {r.title && <h4 className="review-card__title">{r.title}</h4>}
                <p className="review-card__comment">{r.comment}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
