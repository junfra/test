"""Allow running via: python -m oracle_plus [args...]"""

import sys
from oracle_plus.cli import main as _cli_main


def main() -> int:
    return _cli_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
