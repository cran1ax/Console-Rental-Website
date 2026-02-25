import { Link } from "react-router-dom";
import { FiXCircle } from "react-icons/fi";

export default function PaymentCancelled() {
  return (
    <div className="auth">
      <div className="auth__card" style={{ textAlign: "center" }}>
        <FiXCircle size={56} color="#dc2626" />
        <h1 style={{ marginTop: "1rem" }}>Payment Cancelled</h1>
        <p style={{ color: "var(--color-text-muted)", margin: "1rem 0 2rem" }}>
          Your payment was cancelled. The rental is still pending — you can pay
          from your dashboard anytime.
        </p>
        <Link to="/dashboard" className="btn btn--primary btn--lg" style={{ width: "100%", justifyContent: "center" }}>
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
