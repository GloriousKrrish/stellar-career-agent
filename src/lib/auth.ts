// Mock auth — localStorage flags. Real auth comes later.
const KEY = "aria.auth";
const ONBOARD_KEY = "aria.onboarded";

export function isAuthed(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(KEY) === "1";
}

export function signIn() {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, "1");
}

export function signOut() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
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
