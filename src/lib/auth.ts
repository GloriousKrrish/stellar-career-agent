const KEY = "aria.auth";
const ONBOARD_KEY = "aria.onboarded";
const TOKEN_KEY = "aria.token";
const USER_KEY = "aria.user";

export function isAuthed(): boolean {
  if (typeof window === "undefined") return false;
  return !!window.localStorage.getItem(TOKEN_KEY);
}

export function signIn(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(KEY, "1");
}

export function signOut() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  window.localStorage.removeItem(ONBOARD_KEY);
}

export function hasOnboarded(): boolean {
  if (typeof window === "undefined") return true;
  return window.localStorage.getItem(ONBOARD_KEY) === "1";
}

export function completeOnboarding() {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ONBOARD_KEY, "1");
}

export function resetOnboarding() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ONBOARD_KEY);
}

export function getCurrentUser() {
  if (typeof window === "undefined") return null;
  const userStr = window.localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

