"""Filesystem layout for an alethech store.

.alethech/
    identities/<agent_id>.json      # Identity records (public only)
    keys/signing.key                # Private signing key (PEM, 0600)
    keys/recovery.key               # Private recovery key (PEM, 0600)
    commits/<commit_id>.json        # MemoryCommit files
    evidence/<commit_id>.json      # EvidenceCommit files
    artifacts/<hash>               # Raw artifact bytes (named by sha256)
    HEAD                            # Current head commit_id (text file)
"""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from . import crypto
from .objects import Identity, MemoryCommit, EvidenceCommit, Checkpoint


class StoreError(Exception):
    pass


@dataclass
class Store:
    """A alethech store on disk."""

    root: Path

    @classmethod
    def init(cls, root: Path) -> "Store":
        root = Path(root)
        if root.exists() and any(root.iterdir()):
            raise StoreError(f"directory not empty: {root}")
        (root / "identities").mkdir(parents=True, exist_ok=True)
        (root / "keys").mkdir(parents=True, exist_ok=True)
        (root / "commits").mkdir(parents=True, exist_ok=True)
        (root / "evidence").mkdir(parents=True, exist_ok=True)
        (root / "artifacts").mkdir(parents=True, exist_ok=True)
        # HEAD doesn't exist until first commit
        return cls(root=root)

    @classmethod
    def open(cls, root: Path) -> "Store":
        root = Path(root)
        if not (root / "identities").is_dir():
            raise StoreError(f"not an alethech store: {root}")
        return cls(root=root)

    # ---------- identities ----------

    def write_identity(self, identity: Identity) -> None:
        path = self.root / "identities" / f"{identity.agent_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(identity.to_dict(), indent=2), encoding="utf-8")

    def load_identities(self) -> dict[str, Identity]:
        ids = {}
        idir = self.root / "identities"
        if not idir.is_dir():
            return ids
        for path in idir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                ident = Identity.from_dict(data)
                ids[ident.agent_id] = ident
            except Exception as e:
                raise StoreError(f"corrupted identity {path.name}: {e}") from e
        return ids

    # ---------- keys ----------

    def write_signing_key(self, keypair: crypto.KeyPair) -> None:
        path = self.root / "keys" / "signing.key"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write with restrictive perms
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, keypair.private_pem())
        finally:
            os.close(fd)

    def load_signing_key(self) -> crypto.KeyPair:
        path = self.root / "keys" / "signing.key"
        if not path.is_file():
            raise StoreError("signing key not found")
        return crypto.KeyPair.from_private_pem(path.read_bytes())

    def write_recovery_key(self, keypair: crypto.KeyPair) -> None:
        path = self.root / "keys" / "recovery.key"
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, keypair.private_pem())
        finally:
            os.close(fd)

    # ---------- HEAD ----------

    def read_head(self) -> str | None:
        path = self.root / "HEAD"
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8").strip() or None

    def write_head(self, commit_id: str) -> None:
        path = self.root / "HEAD"
        path.write_text(commit_id + "\n", encoding="utf-8")

    # ---------- commits ----------

    def write_commit(self, commit: MemoryCommit) -> None:
        path = self.root / "commits" / f"{commit.commit_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(commit.to_signed_dict(), indent=2),
            encoding="utf-8",
        )

    def load_commits(self) -> dict[str, MemoryCommit]:
        commits = {}
        cdir = self.root / "commits"
        if not cdir.is_dir():
            return commits
        for path in cdir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                commit = MemoryCommit.from_dict(data)
                commits[commit.commit_id] = commit
            except Exception as e:
                raise StoreError(f"corrupted commit {path.name}: {e}") from e
        return commits

    # ---------- evidence ----------

    def write_evidence(self, ev: EvidenceCommit) -> None:
        path = self.root / "evidence" / f"{ev.commit_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(ev.to_signed_dict(), indent=2),
            encoding="utf-8",
        )

    def load_evidence(self) -> dict[str, EvidenceCommit]:
        evs = {}
        edir = self.root / "evidence"
        if not edir.is_dir():
            return evs
        for path in edir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                ev = EvidenceCommit.from_dict(data)
                evs[ev.commit_id] = ev
            except Exception as e:
                raise StoreError(f"corrupted evidence {path.name}: {e}") from e
        return evs

    # ---------- artifacts ----------

    def write_artifact(self, data: bytes) -> str:
        """Write artifact bytes, return its hash identifier."""
        h = "sha256:" + crypto.sha256_hex(data)
        path = self.root / "artifacts" / h
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        return h

    def read_artifact(self, hash_id: str) -> bytes | None:
        path = self.root / "artifacts" / hash_id
        if not path.is_file():
            return None
        return path.read_bytes()

    def list_artifacts(self) -> set[str]:
        adir = self.root / "artifacts"
        if not adir.is_dir():
            return set()
        return {p.name for p in adir.iterdir() if p.is_file()}
