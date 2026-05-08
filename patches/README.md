# Patches — code changes that live outside HQ but back up here

This directory holds `.patch` files representing code changes made in
**other repositories** that aren't pushed to a user-controlled remote.
The patches are a belt-and-braces backup so the work survives a Mac wipe
or a project-directory loss without depending on the upstream repo.

## When to add a patch here

- You modified an external open-source repo (e.g., upstream Paperclip)
- You didn't fork → can't push the branch
- The change matters enough that "lose it and we redo it" isn't acceptable

## How to apply

```bash
cd <target-repo>
git checkout master            # or whichever base the patch was generated against
git apply ~/claude-hq/patches/<file>.patch
# or for cleaner history:
git am ~/claude-hq/patches/<file>.patch
```

## How to refresh

If the branch the patch was generated from has new commits, regenerate:

```bash
cd <target-repo> && git diff <base>..<branch> > ~/claude-hq/patches/<name>-$(git rev-parse --short HEAD).patch
```

The SHA suffix in the filename tells future-you which version this snapshot represents.

## Current patches

| File | What it is | Generated from |
|---|---|---|
| `paperclip-multi-model-routing-8028acf.patch` | HQ Commander multi-model routing translated into Paperclip — `routeModel()` function, doctrine table, hard floor, env overrides, and the 2026-05-08 safety patches (non-Anthropic passthrough + current_tier_floor). | Paperclip branch `feat/multi-model-routing` at commit `8028acf`, against upstream `paperclipai/paperclip` master `d2cbe2c` |
