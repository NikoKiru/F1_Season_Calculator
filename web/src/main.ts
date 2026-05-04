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

function bindNavGroups(): void {
  const groups = $$<HTMLElement>("[data-nav-group]");
  if (groups.length === 0) return;

  const closeAll = (except?: HTMLElement) => {
    for (const g of groups) {
      if (g === except) continue;
      g.dataset.open = "false";
      const trigger = g.querySelector<HTMLButtonElement>("[data-nav-trigger]");
      trigger?.setAttribute("aria-expanded", "false");
    }
  };

  const open = (g: HTMLElement, focusFirstItem = false) => {
    closeAll(g);
    g.dataset.open = "true";
    const trigger = g.querySelector<HTMLButtonElement>("[data-nav-trigger]");
    trigger?.setAttribute("aria-expanded", "true");
    if (focusFirstItem) {
      g.querySelector<HTMLAnchorElement>(".nav-group__menu a")?.focus();
    }
  };

  const close = (g: HTMLElement, focusTrigger = false) => {
    g.dataset.open = "false";
    const trigger = g.querySelector<HTMLButtonElement>("[data-nav-trigger]");
    trigger?.setAttribute("aria-expanded", "false");
    if (focusTrigger) trigger?.focus();
  };

  for (const group of groups) {
    const trigger = group.querySelector<HTMLButtonElement>("[data-nav-trigger]");
    if (!trigger) continue;

    trigger.addEventListener("click", (e) => {
      e.preventDefault();
      const isOpen = group.dataset.open === "true";
      if (isOpen) close(group);
      else open(group);
    });

    trigger.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open(group, true);
      } else if (e.key === "Escape") {
        close(group, true);
      }
    });

    group.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close(group, true);
      }
    });
  }

  document.addEventListener("click", (e) => {
    const target = e.target as Node;
    if (!groups.some((g) => g.contains(target))) closeAll();
  });
}

bindHamburger();
bindSeasonSwitcher();
bindGlobalSearch();
bindNavGroups();
markCurrentNav();
