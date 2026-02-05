"use client";
/**
 * Shared API Client
 *
 * Centralized axios instance.
 * All API modules should import this client instead of creating their own.
 */
import axios from "axios";

export const apiClient = axios.create({
  baseURL: `${process.env.NEXT_PUBLIC_API_BASE_URL}`,
});

export default apiClient;
