import api from "./client";

export const rentalsAPI = {
  /* ── Consoles ─────────────────────────────────────────────── */
  listConsoles: (params = {}) =>
    api.get("/rentals/consoles/", { params }),

  getConsole: (slug) =>
    api.get(`/rentals/consoles/${slug}/`),

  getConsoleReviews: (slug, params = {}) =>
    api.get(`/rentals/consoles/${slug}/reviews/`, { params }),

  getConsoleReviewStats: (slug) =>
    api.get(`/rentals/consoles/${slug}/review-stats/`),

  checkConsoleAvailability: (slug, startDate, endDate) =>
    api.get(`/rentals/consoles/${slug}/check-availability/`, {
      params: { start_date: startDate, end_date: endDate },
    }),

  /* ── Games ────────────────────────────────────────────────── */
  listGames: (params = {}) =>
    api.get("/rentals/games/", { params }),

  getGame: (slug) =>
    api.get(`/rentals/games/${slug}/`),

  /* ── Accessories ──────────────────────────────────────────── */
  listAccessories: (params = {}) =>
    api.get("/rentals/accessories/", { params }),

  getAccessory: (slug) =>
    api.get(`/rentals/accessories/${slug}/`),

  /* ── Bookings ─────────────────────────────────────────────── */
  createRental: (data) =>
    api.post("/rentals/bookings/", data),

  listRentals: (params = {}) =>
    api.get("/rentals/bookings/", { params }),

  getRental: (id) =>
    api.get(`/rentals/bookings/${id}/`),

  returnRental: (id) =>
    api.post(`/rentals/bookings/${id}/return_rental/`),

  cancelRental: (id) =>
    api.post(`/rentals/bookings/${id}/cancel/`),

  getLateFee: (id) =>
    api.get(`/rentals/bookings/${id}/late_fee/`),

  /* ── Reviews ──────────────────────────────────────────────── */
  createReview: (data) =>
    api.post("/rentals/reviews/", data),

  listMyReviews: (params = {}) =>
    api.get("/rentals/reviews/", { params }),

  getReviewableRentals: () =>
    api.get("/rentals/reviews/reviewable/"),

  /* ── Availability ─────────────────────────────────────────── */
  checkBulkAvailability: (data) =>
    api.post("/rentals/availability/check/", data),
};
