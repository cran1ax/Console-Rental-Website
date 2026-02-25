import { Link } from "react-router-dom";
import { FiCheckCircle } from "react-icons/fi";

export default function PaymentSuccess() {
  return (
    <div className="auth">
      <div className="auth__card" style={{ textAlign: "center" }}>
        <FiCheckCircle size={56} color="var(--color-success)" />
        <h1 style={{ marginTop: "1rem" }}>Payment Successful!</h1>
        <p style={{ color: "var(--color-text-muted)", margin: "1rem 0 2rem" }}>
          Your rental has been confirmed. You can track it from your dashboard.
        </p>
        <Link to="/dashboard" className="btn btn--primary btn--lg" style={{ width: "100%", justifyContent: "center" }}>
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
