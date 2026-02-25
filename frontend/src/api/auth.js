import api from "./client";

export const authAPI = {
  login: (email, password) =>
    api.post("/auth/login/", { email, password }),

  register: (data) =>
    api.post("/auth/registration/", data),

  logout: (refresh) =>
    api.post("/auth/logout/", { refresh }),

  refreshToken: (refresh) =>
    api.post("/auth/token/refresh/", { refresh }),

  getMe: () =>
    api.get("/auth/me/"),

  updateMe: (data) =>
    api.patch("/auth/me/", data),

  getProfile: () =>
    api.get("/auth/me/profile/"),

  updateProfile: (data) =>
    api.patch("/auth/me/profile/", data),

  changePassword: (oldPassword, newPassword) =>
    api.post("/auth/me/change-password/", {
      old_password: oldPassword,
      new_password: newPassword,
    }),

  myRentals: (params = {}) =>
    api.get("/auth/me/rentals/", { params }),

  deleteAccount: () =>
    api.delete("/auth/me/delete/"),
};
