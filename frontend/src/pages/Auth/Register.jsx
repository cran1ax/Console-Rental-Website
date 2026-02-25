import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { useAuth } from "../../context/AuthContext";
import "./Auth.css";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    password1: "",
    password2: "",
    full_name: "",
    phone_number: "",
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (form.password1 !== form.password2) {
      toast.error("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await register(form);
      toast.success("Account created! Welcome aboard 🎮");
      navigate("/dashboard");
    } catch (err) {
      const data = err.response?.data;
      const msg =
        data?.email?.[0] ||
        data?.password1?.[0] ||
        data?.non_field_errors?.[0] ||
        data?.detail ||
        "Registration failed.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth__card">
        <h1>Sign Up</h1>
        <p className="auth__subtitle">Create your Corner Console account</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="full_name">Full Name</label>
            <input
              id="full_name"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              placeholder="John Doe"
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email *</label>
            <input
              id="email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              placeholder="you@example.com"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="phone_number">Phone Number</label>
            <input
              id="phone_number"
              name="phone_number"
              type="tel"
              value={form.phone_number}
              onChange={handleChange}
              placeholder="+91 98765 43210"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="password1">Password *</label>
              <input
                id="password1"
                name="password1"
                type="password"
                value={form.password1}
                onChange={handleChange}
                placeholder="Min 8 characters"
                required
                minLength={8}
              />
            </div>
            <div className="form-group">
              <label htmlFor="password2">Confirm Password *</label>
              <input
                id="password2"
                name="password2"
                type="password"
                value={form.password2}
                onChange={handleChange}
                placeholder="Re-type password"
                required
                minLength={8}
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn--primary btn--lg auth__submit"
            disabled={loading}
          >
            {loading ? "Creating account…" : "Sign Up"}
          </button>
        </form>

        <p className="auth__footer">
          Already have an account?{" "}
          <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
