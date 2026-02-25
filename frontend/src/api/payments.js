import api from "./client";

export const paymentsAPI = {
  createCheckoutSession: (rentalId, paymentType) =>
    api.post("/payments/checkout-session/", {
      rental_id: rentalId,
      payment_type: paymentType,
    }),

  listPayments: (params = {}) =>
    api.get("/payments/", { params }),

  getPayment: (id) =>
    api.get(`/payments/${id}/`),
};
