# task-4dDA thread — arXiv link in JaleesBench results browser header

- 2026-09-05: Urgent one-line task. Added `Paper (arXiv)` link (https://arxiv.org/abs/2608.07508,
  target=_blank rel=noopener noreferrer) to `.app-header` in apps/jaleesbrowser/src/App.tsx, between
  the title and the theme toggle, so it shows on every view. One small `.paper-link` CSS rule using
  the existing `--accent` variable. No other changes.
- Note: IntroPanel already renders a dataset-driven paper link inside the collapsible intro; left as-is
  (task said this one link only, no refactors).
- Verified in worktree after `npm ci`: 82/82 vitest tests pass, `tsc` clean, `vite build` clean.
- PR opened; architect messaged for review. Deploy is GitHub Pages on merge to main.
