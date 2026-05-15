/** Tiny DOM helpers — nothing worth a library for. */

export function $<T extends HTMLElement = HTMLElement>(selector: string, root: ParentNode = document): T | null {
  return root.querySelector<T>(selector);
}

export function $$<T extends HTMLElement = HTMLElement>(selector: string, root: ParentNode = document): T[] {
  return Array.from(root.querySelectorAll<T>(selector));
}

export function require$<T extends HTMLElement = HTMLElement>(selector: string, root: ParentNode = document): T {
  const el = $<T>(selector, root);
  if (!el) throw new Error(`Required element not found: ${selector}`);
  return el;
}

export function readJsonScript<T>(id: string): T | null {
  const el = document.getElementById(id);
  if (!el || el.tagName !== "SCRIPT") return null;
  try {
    return JSON.parse(el.textContent ?? "null") as T;
  } catch {
    return null;
  }
}
