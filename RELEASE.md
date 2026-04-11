# Release

## Automated npm release

- Workflow: `.github/workflows/release.yml`
- Trigger: every push to `master`
- Versioning: `semantic-release` using Conventional Commit messages
- Publish mode: npm trusted publishing with GitHub Actions OIDC
- Publishes to npm and updates these files in the release commit:
  - `CHANGELOG.md`
  - `package.json`
  - `package-lock.json`
  - `server.json`
  - `pyproject.toml`

### Required setup

- In npm package settings for `discord-selfbot-mcp`, add this repo/workflow as a trusted publisher
- Workflow file must stay `.github/workflows/release.yml`
- Branch must stay `master` unless the npm trusted publisher entry is updated too
- No `NPM_TOKEN` secret is required for the automated npm publish path

## Manual Checklist

- Versions match:
  - `package.json`
  - `package-lock.json`
  - `server.json`
  - `pyproject.toml`
- Run sanity checks:
  - `node -c index.js && node -c setup-wizard.js && node -c scripts/postinstall.js`
  - `python3 -m compileall -q discord_py_self_mcp`
  - `npm pack --dry-run`

## Manual Publish (npm)

```bash
npm whoami
npm publish
```

## Publish (python)

If you publish this package to PyPI:

```bash
python3 -m build
python3 -m twine upload dist/*
```

## GitHub

- Create a tag matching the version (e.g. `v1.0.4`)
- Create a GitHub release using `CHANGELOG.md` entries
