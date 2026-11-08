"""Aplica los scripts SQL de sql/ (no destructivos e idempotentes) sobre DATABASE_URL."""
from pathlib import Path

from app.db.session import engine

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def main() -> None:
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        for path in sorted(SQL_DIR.glob("*.sql")):
            print(f"Aplicando {path.name} ...")
            cur.execute(path.read_text(encoding="utf-8"))
        raw.commit()
        print("Listo.")
    finally:
        raw.close()


if __name__ == "__main__":
    main()
