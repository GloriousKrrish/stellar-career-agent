// Mock auth — localStorage flag. Real auth comes later.
const KEY = "aria.auth";

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
}
