# Working in this repo

Several Claude sessions often work here at once. To keep out of each other's way:

- Start every task in your own git worktree, never in the main checkout:
  `git worktree add ../davidvanvliet-<task> -b <task> main`, then work from there.
- Never push the worktree's branch: Vercel deploys a preview for every pushed branch.
  When the work is done, `git fetch`, `git rebase origin/main`, then `git push origin HEAD:main`.
  If the push is rejected (another session pushed first), fetch, rebase and push again. Remove
  your worktree only after a push that succeeded: chained after a failed push, the cleanup
  deletes the unpushed commit with the branch.
- Commit only your own files. Run `git diff --cached --name-only` before committing.
- Never commit `frontend/AGENTS.md` or `frontend/CLAUDE.md` (written by `next dev`).
- The dev server on localhost:3000 runs from the main checkout and stays there: never move it or
  start another. Its model dashboard (`/models?dashboard`) reads every worktree, so your builds
  show up there as soon as you build in your own worktree.
- Nobody works in the main checkout. After pushing to main, fast-forward it
  (`git -C <main checkout> merge --ff-only origin/main`) so :3000 shows what is live.
- The Blender harness (`frontend/scripts/blender`) works from any worktree; see the
  model-probe skill.
