# Design System — Master File

> **LOGIC:** When building a specific page, first check
> `design-system/course-folder-management-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file. Otherwise follow
> the rules below.

---

**Project:** Course Folder Management System (UIIT, PMAS Arid Agriculture University)
**Direction:** Accessible & Ethical / education — calm, professional academic, not flashy
**Generated with:** `ui-ux-pro-max` skill (font pairing + UX rules), palette tuned to the
brief (Forest green + warm stone) and verified for WCAG AA contrast.

---

## 1. Brand intent

A focal-person/faculty tool for assembling and certifying course folders. It must
read as trustworthy, institutional, and quiet — the evidence (documents,
checklists, certificates) is the hero, not the chrome. The forest green nods to the
university's agricultural roots; warm stone neutrals keep long admin sessions calm.
One restrained accent (muted gold) marks issuance/seals only.

## 2. Color palette (WCAG AA verified)

All foreground/background text pairs below meet AA (≥4.5:1 normal text); ratios noted.

| Role | Hex | CSS Variable | Notes |
|------|-----|--------------|-------|
| Primary | `#166534` | `--color-primary` | Forest green. White text = 7.13:1 |
| Primary (hover/strong) | `#14532D` | `--color-primary-strong` | White text = 9.11:1 |
| On Primary | `#FFFFFF` | `--color-on-primary` | |
| Accent | `#9A6B00` | `--color-accent` | Muted gold; seals/issuance. White = 4.69:1 |
| On Accent | `#FFFFFF` | `--color-on-accent` | |
| Background | `#F7F6F2` | `--color-background` | Warm stone 50 |
| Foreground | `#1C1917` | `--color-foreground` | Stone 900. On bg = 16.2:1 |
| Card | `#FFFFFF` | `--color-card` | |
| Muted | `#EFEDE6` | `--color-muted` | Subtle fills, table headers |
| Muted Foreground | `#57534E` | `--color-muted-foreground` | Secondary text. On bg = 7.05:1 |
| Border | `#E0DDD3` | `--color-border` | Hairline borders (non-text) |
| Success | `#166534` | `--color-success` | Reuses primary green |
| Warning | `#B45309` | `--color-warning` | "In review" / pending states |
| Destructive | `#B91C1C` | `--color-destructive` | Missing/return. White = 6.47:1 |
| Ring (focus) | `#166534` | `--color-ring` | Visible keyboard focus |

**Status semantics:** Certified → green; In review → warning amber; Pending/Missing
→ stone/destructive. Never convey status by color alone — always pair with a label.

## 3. Typography (Academic / Research pairing)

Chosen for accessibility: **Atkinson Hyperlegible** is designed for maximum
legibility; **Crimson Pro** gives scholarly headings.

- **Display / headings:** Crimson Pro (600/700)
- **Body / UI:** Atkinson Hyperlegible (400/700)
- **Base size:** 16px, line-height 1.5; never below 12px.

```css
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Crimson+Pro:wght@400;500;600;700&display=swap');
```

```js
// tailwind.config.js
fontFamily: {
  display: ['"Crimson Pro"', 'Georgia', 'serif'],
  sans: ['"Atkinson Hyperlegible"', 'system-ui', 'sans-serif'],
}
```

Type scale: page title 1.5–1.875rem (display), section 1.125–1.25rem, body 0.875–1rem,
meta 0.75rem.

## 4. Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Tight gaps |
| `--space-sm` | 8px | Icon gaps, inline |
| `--space-md` | 16px | Standard padding |
| `--space-lg` | 24px | Card / section padding |
| `--space-xl` | 32px | Large gaps |
| `--space-2xl` | 48px | Section margins |

Radius: `--radius` 8px (controls, inputs), 12px (cards), full (pills/badges).

## 5. Shadows

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(28,25,23,0.05)` | Subtle lift (cards) |
| `--shadow-md` | `0 4px 6px rgba(28,25,23,0.08)` | Hover, dropdowns |
| `--shadow-lg` | `0 10px 15px rgba(28,25,23,0.10)` | Modals/popovers |

## 6. Component specs (Tailwind utility recipes)

- **Primary button:** `bg-primary text-on-primary hover:bg-primary-strong rounded-md
  px-4 py-2 font-medium transition-colors cursor-pointer focus-visible:outline-none
  focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`
- **Secondary button:** `border border-border bg-card text-foreground hover:bg-muted …`
  (same radius/focus ring).
- **Accent / issue button:** `bg-accent text-on-accent` (used only for certificate issuance).
- **Card:** `rounded-xl border border-border bg-card p-6 shadow-sm`.
- **Input/select:** `rounded-md border border-border px-3 py-2 text-sm focus:border-primary
  focus-visible:ring-2 focus-visible:ring-ring`.
- **Badge:** pill, `px-2 py-0.5 text-xs font-medium`; certified=green, review=amber,
  pending=stone, missing=red — each with a text label.

## 7. Interaction & accessibility (non-negotiable)

- Visible focus on every interactive element (`focus-visible:ring-2 ring-ring ring-offset-2`).
- `cursor-pointer` on all clickable elements.
- Transitions 150–300ms; honor `prefers-reduced-motion` (disable transforms/animation).
- Contrast ≥ 4.5:1 for text (verified above); status never by color alone.
- Hit targets ≥ 44px where practical; labels on all form fields; logical heading order.
- SVG icons only (no emoji as icons).

## 8. Responsive breakpoints

Design mobile-first; verify at **375 / 768 / 1024 / 1440**. No horizontal scroll;
tables scroll within their container on small screens.

## 9. Anti-patterns (do NOT use)

- ❌ Emoji as icons · ❌ Missing `cursor-pointer` · ❌ Invisible focus states
- ❌ Text contrast < 4.5:1 · ❌ Status by color alone · ❌ Layout-shifting hovers
- ❌ Flashy/ornate decoration — this is a calm academic tool.

## 10. Pre-delivery checklist

- [ ] Tokens used (no stray raw hex in templates)
- [ ] `cursor-pointer` + visible focus on all interactive elements
- [ ] Contrast ≥ 4.5:1; status has a text label
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive at 375 / 768 / 1024 / 1440; no horizontal scroll
- [ ] Headings sequential; form fields labelled; SVG (not emoji) icons
