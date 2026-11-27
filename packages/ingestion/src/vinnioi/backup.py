"""Backup locali verificati. Nessun client cloud o credenziale incorporata."""

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import duckdb

from vinnioi.datasets import QUERIES


class Storage(Protocol):
    def put(self, key: str, content: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key):
        parts = Path(key).parts
        if not parts or Path(key).is_absolute() or any(p in {".", ".."} for p in parts):
            raise ValueError("Chiave storage non sicura")
        path = self.root / key
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("Link fuori dallo storage")
        return path

    def put(self, key: str, content: bytes):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Oggetti immutabili: un backup non sovrascrive mai un altro.
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


def backup(database: Path, snapshot: Path, storage: Storage) -> str:
    if not database.is_file() or Path(str(database) + ".wal").exists():
        raise ValueError("Database chiuso e checkpoint completato obbligatori")
    identifier = str(uuid4())
    files = {}
    # Il lock read-only impedisce scritture concorrenti; un writer aperto viene rifiutato.
    with duckdb.connect(str(database), read_only=True) as connection:
        version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
        manifest = json.loads((snapshot / "manifest.json").read_text())
        for table, expected in manifest["datasets"].items():
            if not re.fullmatch(r"[a-z_]+", table):
                raise ValueError("Nome dataset non valido")
            if table not in QUERIES:
                raise ValueError("Dataset non qualificato nel manifest")
            query = QUERIES[table]
            parquet = str(snapshot / f"{table}.parquet")
            for left, right, parameters in [
                (query, "SELECT * FROM read_parquet(?)", [parquet]),
                ("SELECT * FROM read_parquet(?)", query, [parquet]),
            ]:
                difference = connection.execute(
                    f"SELECT count(*) FROM (({left}) EXCEPT ALL ({right}))", parameters
                ).fetchone()[0]
                if difference:
                    raise ValueError("Snapshot non corrispondente ai contenuti del database")

            actual = connection.execute(
                "SELECT count(*) FROM read_parquet(?)", [str(snapshot / f"{table}.parquet")]
            ).fetchone()[0]
            if actual != expected:
                raise ValueError("Conteggio snapshot incoerente")
        if (
            manifest["datasets"].get("interventions")
            != connection.execute("SELECT count(*) FROM interventions").fetchone()[0]
        ):
            raise ValueError("Snapshot non corrispondente al database")
        sources = [("history.duckdb", database)]
        sources += [
            ("snapshot/" + path.name, path) for path in snapshot.iterdir() if path.is_file()
        ]
        for name, path in sources:
            if path.is_symlink():
                raise ValueError("Link simbolico non consentito nel backup")
            content = path.read_bytes()
            storage.put(f"{identifier}/{name}", content)
            files[name] = {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
    storage.put(
        f"{identifier}/manifest.json",
        json.dumps(
            {"backup_version": 1, "database_schema_version": version, "files": files},
            sort_keys=True,
        ).encode(),
    )
    return identifier


def restore(identifier: str, destination: Path, storage: Storage) -> None:
    if not re.fullmatch(r"[a-f0-9-]{36}", identifier):
        raise ValueError("Identificativo backup non valido")
    if destination.exists():
        raise FileExistsError("Il ripristino non sovrascrive destinazioni esistenti")
    manifest = json.loads(storage.get(f"{identifier}/manifest.json"))
    if manifest.get("backup_version") != 1 or "history.duckdb" not in manifest["files"]:
        raise ValueError("Manifest backup non valido")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".restore-", dir=destination.parent))
    try:
        for name, metadata in manifest["files"].items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Percorso non sicuro nel manifest")
            content = storage.get(f"{identifier}/{name}")
            if (
                len(content) != metadata["size"]
                or hashlib.sha256(content).hexdigest() != metadata["sha256"]
            ):
                raise ValueError("Integrità backup non verificata")
            path = temporary / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        with duckdb.connect(str(temporary / "history.duckdb"), read_only=True) as connection:
            if (
                connection.execute("SELECT version FROM schema_version").fetchone()[0]
                != manifest["database_schema_version"]
            ):
                raise ValueError("Versione database incoerente")
        temporary.rename(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
