"""CLI helper to initialize a fresh Cloud MySQL database with OS-DBX schema."""

from pathlib import Path
import sys

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services.schema_bootstrap import init_schema_if_needed


def main() -> None:
    result = init_schema_if_needed()
    print(
        f"Schema bootstrap complete: base_schema={result['applied_base_schema']}, "
        f"migration_003={result['applied_migration_003']}"
    )


if __name__ == "__main__":
    main()
