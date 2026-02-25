import { SiPlaystation } from "react-icons/si";
import { Link } from "react-router-dom";
import "./Footer.css";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <div className="footer__brand">
          <SiPlaystation className="footer__icon" />
          <span>Corner Console</span>
        </div>

        <div className="footer__links">
          <Link to="/">Home</Link>
          <Link to="/consoles">Consoles</Link>
          <Link to="/games">Games</Link>
        </div>

        <p className="footer__copy">
          &copy; {new Date().getFullYear()} Corner Console. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
