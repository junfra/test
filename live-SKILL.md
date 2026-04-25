# Oracle Browser Skill

Use the Python CLI:

```bash
ORACLE_CLI="/home/user01/project/oracle/.venv/bin/oracle-plus"
```

## Standard Flow

```bash
"$ORACLE_CLI" --engine browser --browser-model-strategy current --wait --slug "example" --write-output /tmp/oracle_final_capture.md -p "Prompt"
```

## Contract

- Auto-select ports `9473-9479`.
- Keep `~/.cache/oracle-plus/ports/*.lock`.
- Keep `~/.cache/oracle-plus/runs/<slug>.meta`.
- Keep Node `@steipete/oracle` as the browser automation layer.
- Control commands bypass browser auto-selection.
