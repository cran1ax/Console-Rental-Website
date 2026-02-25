import { Link, useNavigate } from "react-router-dom";
import { FiLogOut, FiUser, FiMenu, FiX } from "react-icons/fi";
import { SiPlaystation } from "react-icons/si";
import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import "./Navbar.css";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <nav className="navbar">
      <div className="navbar__inner">
        {/* Logo */}
        <Link to="/" className="navbar__brand">
          <SiPlaystation className="navbar__icon" />
          <span>Corner Console</span>
        </Link>

        {/* Hamburger */}
        <button
          className="navbar__toggle"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {menuOpen ? <FiX /> : <FiMenu />}
        </button>

        {/* Links */}
        <div className={`navbar__links ${menuOpen ? "navbar__links--open" : ""}`}>
          <Link to="/" onClick={() => setMenuOpen(false)}>
            Home
          </Link>
          <Link to="/consoles" onClick={() => setMenuOpen(false)}>
            Consoles
          </Link>
          <Link to="/games" onClick={() => setMenuOpen(false)}>
            Games
          </Link>

          {user ? (
            <>
              <Link to="/dashboard" onClick={() => setMenuOpen(false)}>
                <FiUser /> Dashboard
              </Link>
              <button className="navbar__btn navbar__btn--ghost" onClick={handleLogout}>
                <FiLogOut /> Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="navbar__btn navbar__btn--ghost" onClick={() => setMenuOpen(false)}>
                Log In
              </Link>
              <Link to="/register" className="navbar__btn navbar__btn--primary" onClick={() => setMenuOpen(false)}>
                Sign Up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
