import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import toast from "react-hot-toast";
import { useAuth } from "../../context/AuthContext";
import "./Auth.css";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back!");
      navigate(from, { replace: true });
    } catch (err) {
      const msg =
        err.response?.data?.non_field_errors?.[0] ||
        err.response?.data?.detail ||
        "Invalid credentials.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth__card">
        <h1>Log In</h1>
        <p className="auth__subtitle">Welcome back to Corner Console</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn--primary btn--lg auth__submit"
            disabled={loading}
          >
            {loading ? "Logging in…" : "Log In"}
          </button>
        </form>

        <p className="auth__footer">
          Don&apos;t have an account?{" "}
          <Link to="/register">Sign up</Link>
        </p>
      </div>
    </div>
  );
}
