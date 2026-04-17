/**
 * Shared bootstrap loaded by every page: hamburger, season switcher, global
 * championship-ID search. Page-specific entries run their own main() after.
 */

import { $, $$ } from "./lib/dom";
import "./styles/main.css";

function bindHamburger(): void {
  const btn = $<HTMLButtonElement>("[data-hamburger]");
  const nav = $<HTMLElement>("[data-site-nav]");
  if (!btn || !nav) return;
  btn.addEventListener("click", () => {
    const open = nav.dataset.open === "true";
    nav.dataset.open = String(!open);
    btn.setAttribute("aria-expanded", String(!open));
  });
}

function bindSeasonSwitcher(): void {
  const select = $<HTMLSelectElement>("[data-season-switcher]");
  if (!select) return;
  select.addEventListener("change", () => {
    const url = new URL(window.location.href);
    url.searchParams.set("season", select.value);
    window.location.assign(url.toString());
  });
}

function bindGlobalSearch(): void {
  const form = $<HTMLFormElement>("[data-global-search]");
  if (!form) return;
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const input = form.querySelector<HTMLInputElement>('input[name="championship_id"]');
    const id = input?.value.trim();
    if (id) window.location.assign(`/championship/${encodeURIComponent(id)}`);
  });
}

function markCurrentNav(): void {
  const path = window.location.pathname;
  for (const link of $$<HTMLAnchorElement>(".site-nav a")) {
    if (link.getAttribute("href") === path) link.setAttribute("aria-current", "page");
  }
}

bindHamburger();
bindSeasonSwitcher();
bindGlobalSearch();
markCurrentNav();
