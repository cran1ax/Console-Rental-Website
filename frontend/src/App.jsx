import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./context/AuthContext";
import Navbar from "./components/layout/Navbar";
import Footer from "./components/layout/Footer";
import ProtectedRoute from "./components/ui/ProtectedRoute";

/* ── Pages ───────────────────────────────────────────────────── */
import Home from "./pages/Home/Home";
import ConsolesPage from "./pages/Browse/ConsolesPage";
import GamesPage from "./pages/Browse/GamesPage";
import ConsoleDetail from "./pages/ConsoleDetail/ConsoleDetail";
import Booking from "./pages/Booking/Booking";
import Login from "./pages/Auth/Login";
import Register from "./pages/Auth/Register";
import Dashboard from "./pages/Dashboard/Dashboard";
import PaymentSuccess from "./pages/Payment/PaymentSuccess";
import PaymentCancelled from "./pages/Payment/PaymentCancelled";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
        <div className="app">
          <Navbar />
          <main className="container">
            <Routes>
              {/* Public */}
              <Route path="/" element={<Home />} />
              <Route path="/consoles" element={<ConsolesPage />} />
              <Route path="/consoles/:slug" element={<ConsoleDetail />} />
              <Route path="/games" element={<GamesPage />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* Payment callbacks */}
              <Route path="/payment/success" element={<PaymentSuccess />} />
              <Route path="/payment/cancelled" element={<PaymentCancelled />} />

              {/* Protected */}
              <Route
                path="/book"
                element={
                  <ProtectedRoute>
                    <Booking />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />

              {/* 404 */}
              <Route
                path="*"
                element={
                  <div style={{ textAlign: "center", padding: "4rem" }}>
                    <h1>404</h1>
                    <p>Page not found.</p>
                  </div>
                }
              />
            </Routes>
          </main>
          <Footer />
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}
