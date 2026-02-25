import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { FiPackage, FiStar, FiUser } from "react-icons/fi";
import { useAuth } from "../../context/AuthContext";
import { authAPI } from "../../api/auth";
import { rentalsAPI, paymentsAPI } from "../../api";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import StatusBadge from "../../components/ui/StatusBadge";
import StarRating from "../../components/ui/StarRating";
import "./Dashboard.css";

const TABS = [
  { key: "rentals", label: "My Rentals", icon: <FiPackage /> },
  { key: "reviews", label: "My Reviews", icon: <FiStar /> },
  { key: "profile", label: "Profile", icon: <FiUser /> },
];

export default function Dashboard() {
  const { user, refreshUser, logout } = useAuth();
  const [tab, setTab] = useState("rentals");
  const [rentals, setRentals] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  /* ── Profile edit state ────────────────────────────────────── */
  const [profileForm, setProfileForm] = useState({
    full_name: "",
    phone_number: "",
    address: "",
  });

  useEffect(() => {
    if (user) {
      setProfileForm({
        full_name: user.full_name || "",
        phone_number: user.phone_number || "",
        address: user.address || "",
      });
    }
  }, [user]);

  /* ── Fetch data ────────────────────────────────────────────── */
  useEffect(() => {
    async function load() {
      try {
        const [rentalsRes, reviewsRes] = await Promise.all([
          authAPI.myRentals({ ordering: "-created_at" }),
          rentalsAPI.listMyReviews(),
        ]);
        setRentals(rentalsRes.data.results || rentalsRes.data);
        setReviews(reviewsRes.data.results || reviewsRes.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  /* ── Handlers ──────────────────────────────────────────────── */
  const handleCancelRental = async (id) => {
    if (!window.confirm("Cancel this rental?")) return;
    try {
      await rentalsAPI.cancelRental(id);
      toast.success("Rental cancelled.");
      setRentals((prev) =>
        prev.map((r) => (r.id === id ? { ...r, status: "cancelled" } : r)),
      );
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to cancel.");
    }
  };

  const handlePayRental = async (id) => {
    try {
      const { data } = await paymentsAPI.createCheckoutSession(id, "rental");
      if (data.checkout_url) window.location.href = data.checkout_url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Payment failed.");
    }
  };

  const handleProfileSave = async (e) => {
    e.preventDefault();
    try {
      await authAPI.updateMe(profileForm);
      await refreshUser();
      toast.success("Profile updated!");
    } catch (err) {
      toast.error("Failed to update profile.");
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="dashboard">
      {/* ── Greeting ─────────────────────────────────────────── */}
      <div className="dashboard__header">
        <h1>Welcome, {user?.full_name || "Gamer"} 👋</h1>
        <p className="dashboard__email">{user?.email}</p>
      </div>

      {/* ── Tabs ─────────────────────────────────────────────── */}
      <div className="dashboard__tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`dashboard__tab ${tab === t.key ? "dashboard__tab--active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ── Rentals Tab ──────────────────────────────────────── */}
      {tab === "rentals" && (
        <section className="dashboard__section">
          {rentals.length === 0 ? (
            <div className="dashboard__empty">
              <p>No rentals yet.</p>
              <Link to="/consoles" className="btn btn--primary">
                Browse Consoles
              </Link>
            </div>
          ) : (
            <div className="rental-list">
              {rentals.map((r) => (
                <div key={r.id} className="rental-card">
                  <div className="rental-card__top">
                    <span className="rental-card__number">{r.rental_number}</span>
                    <StatusBadge status={r.status} />
                  </div>
                  <p className="rental-card__console">
                    {r.console_name || "Game-only rental"}
                  </p>
                  <div className="rental-card__dates">
                    {r.rental_start_date} → {r.rental_end_date}
                  </div>
                  <div className="rental-card__bottom">
                    <span className="rental-card__price">
                      ₹{r.total_price}
                    </span>
                    <div className="rental-card__actions">
                      {r.payment_status === "unpaid" && r.status !== "cancelled" && (
                        <button
                          className="btn btn--primary btn--sm"
                          onClick={() => handlePayRental(r.id)}
                        >
                          Pay Now
                        </button>
                      )}
                      {r.status === "pending" && (
                        <button
                          className="btn btn--outline btn--sm"
                          onClick={() => handleCancelRental(r.id)}
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Reviews Tab ──────────────────────────────────────── */}
      {tab === "reviews" && (
        <section className="dashboard__section">
          {reviews.length === 0 ? (
            <p className="dashboard__empty">You haven&apos;t written any reviews yet.</p>
          ) : (
            <div className="reviews-list">
              {reviews.map((r) => (
                <div key={r.id} className="review-card">
                  <div className="review-card__header">
                    <StarRating value={r.rating} size={14} />
                    <span className="review-card__date">
                      {new Date(r.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {r.title && <h4 className="review-card__title">{r.title}</h4>}
                  <p className="review-card__comment">{r.comment}</p>
                  <p className="review-card__console-name">
                    {r.console_name || "General review"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Profile Tab ──────────────────────────────────────── */}
      {tab === "profile" && (
        <section className="dashboard__section">
          <form className="profile-form" onSubmit={handleProfileSave}>
            <div className="form-group">
              <label htmlFor="full_name">Full Name</label>
              <input
                id="full_name"
                value={profileForm.full_name}
                onChange={(e) =>
                  setProfileForm((p) => ({ ...p, full_name: e.target.value }))
                }
              />
            </div>
            <div className="form-group">
              <label htmlFor="phone_number">Phone Number</label>
              <input
                id="phone_number"
                value={profileForm.phone_number}
                onChange={(e) =>
                  setProfileForm((p) => ({ ...p, phone_number: e.target.value }))
                }
              />
            </div>
            <div className="form-group">
              <label htmlFor="address">Address</label>
              <textarea
                id="address"
                rows={3}
                value={profileForm.address}
                onChange={(e) =>
                  setProfileForm((p) => ({ ...p, address: e.target.value }))
                }
              />
            </div>
            <button type="submit" className="btn btn--primary">
              Save Changes
            </button>
          </form>
        </section>
      )}
    </div>
  );
}
