"""Verifiable objects: Identity, MemoryCommit, EvidenceCommit, Checkpoint.

Each object knows how to:
- canonicalize itself (excluding commit_id and signature)
- compute its commit_id (= sha256 of canonical bytes without commit_id)
- re-canonicalize with commit_id (excluding signature)
- be signed by a private key
- be verified by a public key
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import crypto
from .canonical import canonical_json_bytes


# ---------- helpers ----------

def utc_now_iso() -> str:
    """ISO 8601 UTC timestamp with milliseconds."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def sha256_commit_id(canonical_bytes: bytes) -> str:
    """commit_id = 'sha256:' + hex(sha256(canonical_bytes))"""
    return "sha256:" + crypto.sha256_hex(canonical_bytes)


# ---------- Identity ----------

@dataclass
class Identity:
    """Agent identity record. Public only — private keys live in .alethech/keys/."""

    agent_id: str  # did:alethech:...
    public_key: dict  # JWK {kty, crv, x}
    key_id: str = "key-001"
    created_at: str = field(default_factory=utc_now_iso)
    recovery_root: str = ""  # base64url of recovery public key, optional

    def to_dict(self) -> dict:
        return {
            "type": "Identity",
            "version": 1,
            "agent_id": self.agent_id,
            "public_key": self.public_key,
            "key_id": self.key_id,
            "created_at": self.created_at,
            "recovery_root": self.recovery_root,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Identity":
        if d.get("type") != "Identity":
            raise ValueError(f"not an Identity record: type={d.get('type')}")
        return cls(
            agent_id=d["agent_id"],
            public_key=d["public_key"],
            key_id=d.get("key_id", "key-001"),
            created_at=d["created_at"],
            recovery_root=d.get("recovery_root", ""),
        )

    def verify_self(self) -> bool:
        """Verify that agent_id derives from public_key (corrección 1 de GPT)."""
        derived = crypto.derive_agent_id(self.public_key)
        return derived == self.agent_id


# ---------- base signed object ----------

@dataclass
class SignedObject:
    """Base for objects that have a commit_id and a signature.

    Subclasses define the schema. They MUST override:
    - object_type() -> str
    - to_signable_dict() -> dict (the object minus commit_id and signature)
    - to_signed_dict() -> dict (full object including commit_id and signature)
    """

    commit_id: str = ""
    signature: str = ""

    @staticmethod
    def object_type() -> str:
        raise NotImplementedError

    def to_signable_dict(self) -> dict:
        """Return the object WITHOUT commit_id and WITHOUT signature."""
        raise NotImplementedError

    def to_signed_dict(self) -> dict:
        """Return the full object, INCLUDING commit_id and signature."""
        raise NotImplementedError

    # --- commit_id computation ---

    def compute_commit_id(self) -> str:
        """sha256 of canonical bytes (without commit_id and signature)."""
        signable = self.to_signable_dict()
        canonical = canonical_json_bytes(signable)
        return sha256_commit_id(canonical)

    # --- canonical bytes used for signing ---

    def canonical_bytes_for_signing(self) -> bytes:
        """Canonical bytes INCLUDING commit_id, EXCLUDING signature.

        This is what Ed25519 signs.
        """
        # build a dict with commit_id but without signature
        signable = self.to_signable_dict()
        signable["commit_id"] = self.commit_id
        return canonical_json_bytes(signable)

    # --- sign / verify ---

    def sign(self, keypair: crypto.KeyPair) -> None:
        self.commit_id = self.compute_commit_id()
        msg = self.canonical_bytes_for_signing()
        sig = keypair.sign(msg)
        self.signature = "ed25519:" + crypto.b64url(sig)

    def verify(self, public_jwk: dict) -> bool:
        """Verify signature AND that commit_id matches content.

        Steps (6 total, corrección 1):
        1. Reconstruct canonical_bytes_with_commit_id (obj with commit_id, no signature)
        2. Verify Ed25519(public_key, canonical_bytes_with_commit_id, signature)
        3. Reconstruct canonical_bytes (no commit_id, no signature)
        4. Recompute sha256(canonical_bytes)
        5. Compare with declared commit_id
        6. Caller must verify agent_id <-> public_key separately
        """
        if not self.commit_id or not self.signature:
            return False
        if not self.signature.startswith("ed25519:"):
            return False
        sig_b64 = self.signature[len("ed25519:"):]
        try:
            sig_bytes = crypto.b64url_decode(sig_b64)
        except Exception:
            return False

        # 1. canonical with commit_id, no signature
        msg = self.canonical_bytes_for_signing()

        # 2. verify signature
        try:
            pub = crypto.KeyPair.public_from_jwk(public_jwk)
        except Exception:
            return False
        if not crypto.KeyPair.verify(pub, sig_bytes, msg):
            return False

        # 3. canonical without commit_id, no signature
        signable = self.to_signable_dict()
        canonical = canonical_json_bytes(signable)

        # 4. recompute hash
        recomputed = sha256_commit_id(canonical)

        # 5. compare
        return recomputed == self.commit_id


# ---------- MemoryCommit ----------

@dataclass
class MemoryCommit(SignedObject):
    """A signed memory commit, linked to its parents in the DAG."""

    agent_id: str = ""
    key_id: str = "key-001"
    parents: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_now_iso)
    session_id: str = ""
    memory_type: str = "semantic"  # semantic|episodic|procedural
    content: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)

    @staticmethod
    def object_type() -> str:
        return "MemoryCommit"

    def to_signable_dict(self) -> dict:
        return {
            "type": "MemoryCommit",
            "version": 1,
            "agent_id": self.agent_id,
            "key_id": self.key_id,
            "parents": self.parents,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "provenance": self.provenance,
        }

    def to_signed_dict(self) -> dict:
        d = self.to_signable_dict()
        d["commit_id"] = self.commit_id
        d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryCommit":
        if d.get("type") != "MemoryCommit":
            raise ValueError(f"not a MemoryCommit: type={d.get('type')}")
        return cls(
            agent_id=d.get("agent_id", ""),
            key_id=d.get("key_id", "key-001"),
            parents=d.get("parents", []),
            timestamp=d["timestamp"],
            session_id=d.get("session_id", ""),
            memory_type=d.get("memory_type", "semantic"),
            content=d.get("content", {}),
            provenance=d.get("provenance", {}),
            commit_id=d.get("commit_id", ""),
            signature=d.get("signature", ""),
        )


# ---------- EvidenceCommit ----------

@dataclass
class EvidenceCommit(SignedObject):
    """A signed evidence record. Atomic event, not part of the DAG."""

    agent_id: str = ""
    key_id: str = "key-001"
    timestamp: str = field(default_factory=utc_now_iso)
    event_type: str = "tool_execution"
    tool: str = ""
    tool_version: str = ""
    input_hash: str = ""
    output_hash: str = ""
    artifacts: list[dict] = field(default_factory=list)
    result: str = "success"

    @staticmethod
    def object_type() -> str:
        return "EvidenceCommit"

    def to_signable_dict(self) -> dict:
        return {
            "type": "EvidenceCommit",
            "version": 1,
            "agent_id": self.agent_id,
            "key_id": self.key_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "artifacts": self.artifacts,
            "result": self.result,
        }

    def to_signed_dict(self) -> dict:
        d = self.to_signable_dict()
        d["commit_id"] = self.commit_id
        d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "EvidenceCommit":
        if d.get("type") != "EvidenceCommit":
            raise ValueError(f"not an EvidenceCommit: type={d.get('type')}")
        return cls(
            agent_id=d.get("agent_id", ""),
            key_id=d.get("key_id", "key-001"),
            timestamp=d["timestamp"],
            event_type=d.get("event_type", "tool_execution"),
            tool=d.get("tool", ""),
            tool_version=d.get("tool_version", ""),
            input_hash=d.get("input_hash", ""),
            output_hash=d.get("output_hash", ""),
            artifacts=d.get("artifacts", []),
            result=d.get("result", "success"),
            commit_id=d.get("commit_id", ""),
            signature=d.get("signature", ""),
        )


# ---------- Checkpoint ----------

@dataclass
class Checkpoint(SignedObject):
    """A checkpoint signed by an agent. Preserved externally to detect rollback.

    Without an external checkpoint, `verify` can only prove integrity —
    it cannot prove continuity (i.e. that the presented history is the
    most recent one). With a checkpoint, it can also prove that the
    presented history continues from that checkpoint.
    """

    agent_id: str = ""
    head_commit_id: str = ""
    commit_count: int = 0
    evidence_count: int = 0
    created_at: str = field(default_factory=utc_now_iso)

    @staticmethod
    def object_type() -> str:
        return "Checkpoint"

    def to_signable_dict(self) -> dict:
        return {
            "type": "Checkpoint",
            "version": 1,
            "agent_id": self.agent_id,
            "head_commit_id": self.head_commit_id,
            "commit_count": self.commit_count,
            "evidence_count": self.evidence_count,
            "created_at": self.created_at,
        }

    def to_signed_dict(self) -> dict:
        d = self.to_signable_dict()
        d["checkpoint_id"] = self.commit_id  # field name in protocol is checkpoint_id
        d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Checkpoint":
        if d.get("type") != "Checkpoint":
            raise ValueError(f"not a Checkpoint: type={d.get('type')}")
        return cls(
            agent_id=d.get("agent_id", ""),
            head_commit_id=d.get("head_commit_id", ""),
            commit_count=d.get("commit_count", 0),
            evidence_count=d.get("evidence_count", 0),
            created_at=d["created_at"],
            commit_id=d.get("checkpoint_id", d.get("commit_id", "")),
            signature=d.get("signature", ""),
        )
