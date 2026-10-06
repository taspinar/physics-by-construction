# Deployment

The site is static files on GitHub Pages. There is one environment,
`github-pages`, and no staging: the built site of every pull request is
attached to its workflow run for review before merge.

- Public address: <https://taspinar.github.io/physics-by-construction/>
- Configured in one place: `website.site-url` in `site/_quarto.yml`. Pages
  link to each other with relative URLs, so a custom domain later is a change
  of that one value plus the Pages setting.

## How a change is published

```text
pull request -> CI verify job -> merge to main -> CI verify job on main
             -> site artifact -> deploy job -> GitHub Pages
```

1. The `verify` job of `.github/workflows/ci.yml` runs `./scripts/verify.sh`
   and uploads `site/_site/` as the `github-pages` artifact. It runs on every
   pull request and on every push to `main`. The site is also uploaded when a
   check failed after the site was built, so that it can be inspected; the
   job still fails.
2. On a push to `main`, and only when the `verify` job succeeded, the
   `deploy` job publishes exactly that artifact. It builds nothing and checks
   out nothing, so the published bytes are the verified bytes.
3. The workflow is read-only (`contents: read`). Only the deploy job has
   `pages: write` and `id-token: write`, and it authenticates with the
   short-lived token GitHub issues to the run. No secret is stored or
   referenced.

Deployment is automatic for every verified commit on `main`. Nobody deploys by
hand, and nothing deploys from a branch.

## Repository settings

These settings live in GitHub, not in the repository, and only the repository
owner can apply them. Changing any of them needs the owner's explicit
approval.

| Setting | Where | Required value |
|---|---|---|
| Pages source | Settings → Pages → Build and deployment | GitHub Actions |
| Required status check | Settings → Rules → Rulesets → ruleset for `main` | `verify`, together with "Require a pull request before merging", "Block force pushes", and "Restrict deletions" |
| Default workflow permissions | Settings → Actions → General | Read repository contents |
| Dependabot alerts and security updates | Settings → Advanced Security | Enabled |
| Secret scanning and push protection | Settings → Advanced Security | Enabled |

Add the required check only after the `verify` job has run once on a pull
request, so that GitHub knows the check. Enable Pages before the first merge
to `main` that contains the deploy job, or that deployment fails.

## Rollback

See `docs/operations.md`.
