# Working in this repo

Several Claude sessions often work here at once. To keep out of each other's way:

- Start every task in your own git worktree, never in the main checkout:
  `git worktree add ../davidvanvliet-<task> -b <task> main`, then work from there.
- Never push the worktree's branch: Vercel deploys a preview for every pushed branch.
  When the work is done, `git fetch`, `git rebase origin/main`, then `git push origin HEAD:main`.
- Commit only your own files. Run `git diff --cached --name-only` before committing.
- Never commit `frontend/AGENTS.md` or `frontend/CLAUDE.md` (written by `next dev`).
- The dev server on localhost:3000 runs from the main checkout. Serve a worktree there only
  when David asks.
- The Blender harness (`frontend/scripts/blender`) works from any worktree; see the
  model-probe skill.
