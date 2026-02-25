import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { loadStripe } from "@stripe/stripe-js";
import { rentalsAPI, paymentsAPI } from "../../api";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import "./Booking.css";

const stripePromise = loadStripe(
  import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || "",
);

const RENTAL_TYPES = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

const DELIVERY_OPTIONS = [
  { value: "pickup", label: "Store Pickup" },
  { value: "home_delivery", label: "Home Delivery" },
];

export default function Booking() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const consoleId = searchParams.get("console");
  const [console_, setConsole] = useState(null);
  const [loading, setLoading] = useState(!!consoleId);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    rental_type: "daily",
    rental_start_date: "",
    rental_end_date: "",
    delivery_option: "pickup",
    delivery_address: "",
    delivery_notes: "",
  });

  /* ── Fetch console info ────────────────────────────────────── */
  useEffect(() => {
    if (!consoleId) return;
    rentalsAPI
      .listConsoles()
      .then(({ data }) => {
        const items = data.results || data;
        const found = items.find((c) => c.id === consoleId);
        setConsole(found || null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [consoleId]);

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  /* ── Compute estimated price ───────────────────────────────── */
  const estimatedPrice = (() => {
    if (!console_ || !form.rental_start_date || !form.rental_end_date) return null;
    const start = new Date(form.rental_start_date);
    const end = new Date(form.rental_end_date);
    const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
    if (days <= 0) return null;
    const rate =
      form.rental_type === "monthly"
        ? parseFloat(console_.monthly_price || console_.daily_price)
        : form.rental_type === "weekly"
          ? parseFloat(console_.weekly_price || console_.daily_price)
          : parseFloat(console_.daily_price);
    return (rate * days).toFixed(2);
  })();

  /* ── Submit booking → create rental → Stripe checkout ──────── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const payload = {
        console: consoleId || undefined,
        game_ids: [],
        accessory_ids: [],
        ...form,
      };

      const { data: rental } = await rentalsAPI.createRental(payload);
      toast.success(`Booking ${rental.rental_number} created!`);

      /* Redirect to Stripe Checkout */
      const { data: session } = await paymentsAPI.createCheckoutSession(
        rental.id,
        "rental",
      );

      if (session.checkout_url) {
        window.location.href = session.checkout_url;
      } else {
        /* Fallback — go to dashboard if no Stripe URL */
        navigate("/dashboard");
      }
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        JSON.stringify(err.response?.data) ||
        "Booking failed. Please try again.";
      toast.error(detail);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="booking">
      <h1>Book a Rental</h1>

      {console_ && (
        <div className="booking__console-badge">
          <strong>{console_.name}</strong> — ₹{console_.daily_price}/day
        </div>
      )}

      <form className="booking__form" onSubmit={handleSubmit}>
        {/* Rental Type */}
        <div className="form-group">
          <label>Rental Type</label>
          <div className="radio-group">
            {RENTAL_TYPES.map((t) => (
              <label key={t.value} className="radio-pill">
                <input
                  type="radio"
                  name="rental_type"
                  value={t.value}
                  checked={form.rental_type === t.value}
                  onChange={handleChange}
                />
                <span>{t.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Dates */}
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="rental_start_date">Start Date</label>
            <input
              id="rental_start_date"
              type="date"
              name="rental_start_date"
              value={form.rental_start_date}
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="rental_end_date">End Date</label>
            <input
              id="rental_end_date"
              type="date"
              name="rental_end_date"
              value={form.rental_end_date}
              onChange={handleChange}
              required
            />
          </div>
        </div>

        {/* Delivery */}
        <div className="form-group">
          <label>Delivery Option</label>
          <div className="radio-group">
            {DELIVERY_OPTIONS.map((d) => (
              <label key={d.value} className="radio-pill">
                <input
                  type="radio"
                  name="delivery_option"
                  value={d.value}
                  checked={form.delivery_option === d.value}
                  onChange={handleChange}
                />
                <span>{d.label}</span>
              </label>
            ))}
          </div>
        </div>

        {form.delivery_option === "home_delivery" && (
          <>
            <div className="form-group">
              <label htmlFor="delivery_address">Delivery Address</label>
              <textarea
                id="delivery_address"
                name="delivery_address"
                rows={3}
                value={form.delivery_address}
                onChange={handleChange}
                required
                placeholder="Full delivery address…"
              />
            </div>
            <div className="form-group">
              <label htmlFor="delivery_notes">Delivery Notes (optional)</label>
              <input
                id="delivery_notes"
                type="text"
                name="delivery_notes"
                value={form.delivery_notes}
                onChange={handleChange}
                placeholder="Ring the bell, leave at door, etc."
              />
            </div>
          </>
        )}

        {/* Price Summary */}
        {estimatedPrice && (
          <div className="booking__summary">
            <div className="booking__summary-row">
              <span>Estimated Total</span>
              <strong>₹{estimatedPrice}</strong>
            </div>
            {console_ && (
              <div className="booking__summary-row booking__summary-row--muted">
                <span>Security Deposit</span>
                <span>₹{console_.security_deposit}</span>
              </div>
            )}
          </div>
        )}

        <button
          type="submit"
          className="btn btn--primary btn--lg booking__submit"
          disabled={submitting}
        >
          {submitting ? "Processing…" : "Confirm & Pay"}
        </button>
      </form>
    </div>
  );
}
