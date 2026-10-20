import { apiClient } from "./client";

/**
 * Logs in a user with email and password via POST /api/auth/login/
 * @param {object} credentials - { email, password }
 * @returns {Promise<{token: string, user: {id: number, email: string, username: string, phone_number: string, role: string}}>}
 */
export async function loginApi({ email, password }) {
  return apiClient("/api/auth/login/", {
    method: "POST",
    body: {
      email: email.trim(),
      password,
    },
  });
}

/**
 * Registers a new user via POST /api/auth/register/
 * @param {object} data - { email, username, password, phone_number }
 * @returns {Promise<{token: string, user: {id: number, email: string, username: string, phone_number: string, role: string}}>}
 */
export async function registerApi({ email, username, password, phone_number }) {
  return apiClient("/api/auth/register/", {
    method: "POST",
    body: {
      email: email.trim(),
      username: username.trim(),
      password,
      phone_number: phone_number ? phone_number.trim() : "",
    },
  });
}
