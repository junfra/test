# Port Selection

Oracle-Plus browser mode auto-selects from `9473-9479`, starting at `9473`.

## Rules

- Probe ports in order.
- Skip unreachable ports.
- Skip ports reserved by a local `flock` lock.
- If a reachable port returns `busy`, release the lock and try the next port.
- Preserve lock files under `~/.cache/oracle-plus/ports/*.lock`.

## Run State

Browser runs record state in `~/.cache/oracle-plus/runs/<slug>.meta`.

## Compatibility

`output/oracle-plus.sh`, if it exists, is compatibility surface only and is not the documented entry point.
