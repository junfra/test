# Oracle-Plus

Oracle-Plus is a Python 3.12+ `uv`-managed CLI that wraps the Node.js `@steipete/oracle` tool through subprocess execution.

## Entry Point

```bash
cd /home/user01/project/oracle
uv sync
uv run oracle-plus --help
```

The installed CLI is `oracle-plus`.

## Runtime Contract

- Local browser ports: `9473-9479`
- Lock files: `~/.cache/oracle-plus/ports/*.lock`
- Run-state files: `~/.cache/oracle-plus/runs/<slug>.meta`
- Browser automation remains in Node `@steipete/oracle`

## Notes

- Source-bearing docs and helper scripts point at the Python CLI, not a shell wrapper.
- The repo-local `skills/oracle-browser/SKILL.md` mirrors the same contract.
