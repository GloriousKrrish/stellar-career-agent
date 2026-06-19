// Real auth management via localStorage tokens.
const AUTH_KEY = "aria.auth";
const ONBOARD_KEY = "aria.onboarded";
const TOKEN_KEY = "aria.token";

export function isAuthed(): boolean {
  if (typeof window === "undefined") return false;
  const token = window.localStorage.getItem(TOKEN_KEY);
  const auth = window.localStorage.getItem(AUTH_KEY);
  return !!token && auth === "1";
}

export function signIn(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(AUTH_KEY, "1");
  window.dispatchEvent(new Event("auth-change"));
}

export function signOut() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(AUTH_KEY);
  window.localStorage.removeItem(ONBOARD_KEY);
  window.localStorage.removeItem("aria.run_id");
  window.dispatchEvent(new Event("auth-change"));
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
