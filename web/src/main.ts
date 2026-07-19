/**
 * Shared bootstrap loaded by every page: hamburger menu, global scenario
 * search, theme toggle, header shadow, and scroll-reveal. Page-specific
 * entries run their own main() after.
 */

import { $, $$ } from "./lib/dom";
import "./styles/main.css";

const THEME_KEY = "f1sc-theme";

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

/* ── Theme ──────────────────────────────────────────────────────────── */

function effectiveTheme(): "light" | "dark" {
  const forced = document.documentElement.dataset.theme;
  if (forced === "light" || forced === "dark") return forced;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function bindThemeToggle(): void {
  const btn = $<HTMLButtonElement>("[data-theme-toggle]");
  if (!btn) return;

  const sync = () => {
    const dark = effectiveTheme() === "dark";
    document.documentElement.dataset.themeEffective = dark ? "dark" : "light";
    const label = dark ? "Switch to light theme" : "Switch to dark theme";
    btn.setAttribute("aria-label", label);
    btn.title = label;
  };
  sync();

  btn.addEventListener("click", () => {
    const next = effectiveTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      /* storage unavailable (private mode) — theme still applies for the page */
    }
    sync();
    window.dispatchEvent(new CustomEvent("f1sc:themechange"));
  });

  // Follow live OS changes while no explicit choice is stored.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (document.documentElement.dataset.theme) return;
    sync();
    window.dispatchEvent(new CustomEvent("f1sc:themechange"));
  });
}

/* ── Header shadow once the page scrolls ────────────────────────────── */

function bindHeaderState(): void {
  const header = $<HTMLElement>(".site-header");
  if (!header) return;
  const update = () => {
    header.dataset.scrolled = String(window.scrollY > 8);
  };
  update();
  window.addEventListener("scroll", update, { passive: true });
}

/* ── Scroll reveal ──────────────────────────────────────────────────── */
/* Sections rise in as they enter the viewport; card grids stagger their
 * children. Fully inert without JS or with reduced motion — content is
 * only hidden after [data-reveal-ready] is stamped on <html>. */

function bindReveal(): void {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (!("IntersectionObserver" in window)) return;

  const targets: HTMLElement[] = [];
  const staggered = new Set<Element>();

  const stagger = (group: HTMLElement) => {
    let i = 0;
    for (const child of Array.from(group.children)) {
      const el = child as HTMLElement;
      el.classList.add("reveal");
      el.style.setProperty("--reveal-i", String(Math.min(i++, 10)));
      targets.push(el);
    }
    staggered.add(group);
  };

  for (const grid of $$<HTMLElement>("main .grid")) {
    if (grid.children.length > 1 && grid.querySelector(":scope > .card")) stagger(grid);
  }
  for (const stack of $$<HTMLElement>("main ol.stack, main ul.stack")) {
    if (stack.children.length > 1 && stack.querySelector(":scope > .card")) stagger(stack);
  }
  for (const section of $$<HTMLElement>("main .section")) {
    if ([...staggered].some((g) => section.contains(g))) continue;
    section.classList.add("reveal");
    targets.push(section);
  }
  if (targets.length === 0) return;

  document.documentElement.dataset.revealReady = "true";

  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        (entry.target as HTMLElement).classList.add("is-in");
        io.unobserve(entry.target);
      }
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
  );

  // Anything already on screen reveals instantly (same frame — no flicker);
  // everything below the fold animates on scroll.
  const fold = window.innerHeight * 0.95;
  for (const el of targets) {
    if (el.getBoundingClientRect().top < fold) el.classList.add("is-in");
    else io.observe(el);
  }
}

bindHamburger();
bindGlobalSearch();
bindNavGroups();
markCurrentNav();
bindThemeToggle();
bindHeaderState();
bindReveal();
