# Release

## Checklist

- Versions match:
  - `package.json`
  - `package-lock.json`
  - `server.json`
  - `pyproject.toml`
- Run sanity checks:
  - `node -c index.js && node -c setup-wizard.js && node -c scripts/postinstall.js`
  - `python3 -m compileall -q discord_py_self_mcp`
  - `npm pack --dry-run`

## Publish (npm)

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
