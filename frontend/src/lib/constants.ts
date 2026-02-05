/**
 * Application-wide constants for auth-free deployment.
 * All user-related operations use this anonymous user to maintain
 * data consistency across frontend and backend.
 */

/**
 * Anonymous user identity for auth-free mode.
 * MUST match backend settings.default_username ("miko") for data isolation.
 */
export const ANONYMOUS_USER = {
  name: "miko",
  email: "",
} as const;

export type AnonymousUser = typeof ANONYMOUS_USER;
