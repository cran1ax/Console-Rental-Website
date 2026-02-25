/**
 * Corner Console — Stripe Checkout Integration (Frontend Example)
 * ================================================================
 *
 * This file shows how to call the backend's Checkout Session endpoint
 * and redirect the user to the Stripe-hosted payment page.
 *
 * Prerequisites
 * -------------
 * 1.  User is authenticated (JWT token available).
 * 2.  A rental has been created (you have the rental UUID).
 *
 * Usage (vanilla JS)
 * ------------------
 *   <button id="pay-btn" data-rental-id="<UUID>">Pay Now</button>
 *   <script src="/static/js/stripe_checkout_example.js"></script>
 */

const API_BASE = "/api/v1/payments";

// ─── Helper: get JWT from cookie or localStorage ────────────────
function getAuthToken() {
  // Adapt this to however your app stores the JWT.
  return localStorage.getItem("access_token") || "";
}

// ─── Create Checkout Session & redirect ─────────────────────────
async function startCheckout(rentalId, paymentType = "rental") {
  const btn = document.getElementById("pay-btn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Redirecting…";
  }

  try {
    const response = await fetch(`${API_BASE}/checkout-session/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAuthToken()}`,
      },
      body: JSON.stringify({
        rental_id: rentalId,
        payment_type: paymentType,
        // Optional overrides:
        // success_url: "https://yoursite.com/thankyou?session_id={CHECKOUT_SESSION_ID}",
        // cancel_url:  "https://yoursite.com/cart",
      }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Payment session creation failed.");
    }

    const data = await response.json();

    // ── Redirect to Stripe Checkout hosted page ─────────────
    window.location.href = data.checkout_url;
  } catch (error) {
    console.error("Checkout error:", error);
    alert(error.message || "Something went wrong. Please try again.");

    if (btn) {
      btn.disabled = false;
      btn.textContent = "Pay Now";
    }
  }
}

// ─── Wire up button click ───────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const payBtn = document.getElementById("pay-btn");
  if (payBtn) {
    payBtn.addEventListener("click", () => {
      const rentalId = payBtn.dataset.rentalId;
      const paymentType = payBtn.dataset.paymentType || "rental";
      if (!rentalId) {
        alert("Missing rental ID.");
        return;
      }
      startCheckout(rentalId, paymentType);
    });
  }
});

// ─── Success-page helper (optional) ────────────────────────────
// On your /payments/success page, you can read the session_id from
// the query string and show a confirmation message:
//
//   const params = new URLSearchParams(window.location.search);
//   const sessionId = params.get("session_id");
//   if (sessionId) {
//     document.getElementById("session-ref").textContent = sessionId;
//   }

/*
 * ─── React / Next.js example ────────────────────────────────────
 *
 * import { useRouter } from 'next/router';
 *
 * export function PayButton({ rentalId, paymentType = 'rental' }) {
 *   const router = useRouter();
 *   const [loading, setLoading] = useState(false);
 *
 *   const handlePay = async () => {
 *     setLoading(true);
 *     try {
 *       const res = await fetch('/api/v1/payments/checkout-session/', {
 *         method: 'POST',
 *         headers: {
 *           'Content-Type': 'application/json',
 *           Authorization: `Bearer ${getToken()}`,
 *         },
 *         body: JSON.stringify({ rental_id: rentalId, payment_type: paymentType }),
 *       });
 *       const data = await res.json();
 *       if (!res.ok) throw new Error(data.detail);
 *
 *       // Redirect to Stripe
 *       window.location.href = data.checkout_url;
 *     } catch (err) {
 *       alert(err.message);
 *       setLoading(false);
 *     }
 *   };
 *
 *   return (
 *     <button onClick={handlePay} disabled={loading}>
 *       {loading ? 'Redirecting…' : 'Pay Now'}
 *     </button>
 *   );
 * }
 */
