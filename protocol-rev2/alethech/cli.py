"""alethech CLI — six commands. No more, no less.

    alethech init
    alethech commit
    alethech evidence
    alethech verify
    alethech export
    alethech import
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import click

from . import crypto
from .objects import Identity, MemoryCommit, EvidenceCommit, Checkpoint
from .store import Store, StoreError
from .verify import verify_store


# ---------- helpers ----------

def _store_path(ctx: click.Context) -> Path:
    """Get the alethech store path from the click context."""
    return Path(ctx.obj["store"])


def _load_content(path: str) -> dict:
    """Load a JSON object from a file path."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise click.ClickException(f"content is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise click.ClickException(f"content must be a JSON object, got {type(data).__name__}")
    return data


def _hash_file(path: str) -> str:
    """Compute sha256:hex of file contents."""
    data = Path(path).read_bytes()
    return "sha256:" + crypto.sha256_hex(data)


# ---------- CLI group ----------

@click.group()
@click.option(
    "--store",
    default=".alethech",
    envvar="ALETHECH_STORE",
    help="Path to the alethech store directory (default: .alethech/)",
)
@click.pass_context
def cli(ctx: click.Context, store: str) -> None:
    """alethech — verifiable agent continuity protocol."""
    ctx.ensure_object(dict)
    ctx.obj["store"] = store


# ---------- 1. init ----------

@cli.command()
@click.option("--recovery-key-file", type=click.Path(exists=True), help="Existing recovery private key (PEM)")
def init(recovery_key_file: str | None) -> None:
    """Initialize a new alethech store with identity + genesis commit."""
    store_path = Path(click.get_current_context().obj["store"])

    # Refuse if directory exists and is non-empty
    if store_path.exists() and any(store_path.iterdir()):
        raise click.ClickException(f"directory not empty: {store_path}")

    # Generate signing keypair
    signing = crypto.KeyPair.generate()

    # Recovery keypair: load or generate
    if recovery_key_file:
        recovery_pem = Path(recovery_key_file).read_bytes()
        recovery = crypto.KeyPair.from_private_pem(recovery_pem)
    else:
        recovery = crypto.KeyPair.generate()

    # Derive agent_id from public key (corrección 1 de GPT)
    public_jwk = signing.public_jwk()
    agent_id = crypto.derive_agent_id(public_jwk)

    # Build Identity record
    recovery_pub_bytes = recovery.public.public_bytes(
        encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.Raw,
        format=__import__("cryptography").hazmat.primitives.serialization.PublicFormat.Raw,
    )
    identity = Identity(
        agent_id=agent_id,
        public_key=public_jwk,
        key_id="key-001",
        recovery_root="ed25519:" + crypto.b64url(recovery_pub_bytes),
    )

    # Initialize store dirs
    store = Store.init(store_path)
    store.write_identity(identity)
    store.write_signing_key(signing)
    store.write_recovery_key(recovery)

    # Genesis commit: parents=[], content={"type": "genesis"}
    genesis = MemoryCommit(
        agent_id=agent_id,
        key_id="key-001",
        parents=[],
        session_id=str(uuid.uuid4()),
        memory_type="semantic",
        content={"type": "genesis"},
        provenance={
            "source": "agent_observation",
            "source_id": None,
            "evidence_refs": [],
            "confidence": 1.0,
        },
    )
    genesis.sign(signing)
    store.write_commit(genesis)
    store.write_head(genesis.commit_id)

    click.echo(f"agent_id: {agent_id}")
    click.echo(f"public_key: ed25519:{public_jwk['x']}")
    click.echo(f"key_id: {identity.key_id}")
    click.echo(f"genesis_commit: {genesis.commit_id}")


# ---------- 2. commit ----------

@cli.command()
@click.option("--content", required=True, type=click.Path(exists=True), help="JSON file with commit content")
@click.option("--type", "memory_type", default="semantic",
              type=click.Choice(["semantic", "episodic", "procedural"]))
@click.option("--evidence", "evidence_ids", multiple=True, help="EvidenceCommit IDs to reference")
@click.option("--session", "session_id", default="", help="Session ID (default: random)")
def commit(content: str, memory_type: str, evidence_ids: tuple[str, ...], session_id: str) -> None:
    """Create a signed MemoryCommit linked to the current HEAD."""
    ctx = click.get_current_context()
    store_path = Path(ctx.obj["store"])
    store = Store.open(store_path)

    # Load identity + signing key
    try:
        signing = store.load_signing_key()
    except StoreError as e:
        raise click.ClickException(str(e))

    identities = store.load_identities()
    if not identities:
        raise click.ClickException("no identities in store — run `alethech init` first")
    # Use the first identity (rev 2 supports only one agent per store)
    identity = next(iter(identities.values()))

    # Verify agent_id matches public key
    if not identity.verify_self():
        raise click.ClickException("identity_mismatch: agent_id does not derive from public_key in store")

    # Load current HEAD
    head = store.read_head()
    if head is None:
        raise click.ClickException("HEAD missing — store may be corrupted; run `alethech verify`")
    commits = store.load_commits()
    if head not in commits:
        raise click.ClickException(f"HEAD points to nonexistent commit {head} — run `alethech verify`")

    # Verify evidence IDs exist
    if evidence_ids:
        evidence = store.load_evidence()
        for eid in evidence_ids:
            if eid not in evidence:
                raise click.ClickException(f"evidence_id not found: {eid}")

    # Build commit
    content_obj = _load_content(content)
    if not session_id:
        session_id = str(uuid.uuid4())

    mc = MemoryCommit(
        agent_id=identity.agent_id,
        key_id=identity.key_id,
        parents=[head],
        session_id=session_id,
        memory_type=memory_type,
        content=content_obj,
        provenance={
            "source": "agent_observation",
            "source_id": str(uuid.uuid4()),
            "evidence_refs": list(evidence_ids),
            "confidence": 1.0,
        },
    )
    mc.sign(signing)
    store.write_commit(mc)
    store.write_head(mc.commit_id)

    click.echo(f"commit: {mc.commit_id}")
    click.echo(f"parent: {head}")
    click.echo(f"agent: {mc.agent_id}")
    click.echo(f"timestamp: {mc.timestamp}")


# ---------- 3. evidence ----------

@cli.command()
@click.option("--tool", required=True, help="Tool name (e.g. filesystem.read)")
@click.option("--input", "input_file", required=True, type=click.Path(exists=True), help="Input file")
@click.option("--output", "output_file", required=True, type=click.Path(exists=True), help="Output file")
@click.option("--result", default="success", type=click.Choice(["success", "failure", "timeout"]))
@click.option("--artifacts", "artifact_files", multiple=True, type=click.Path(exists=True), help="Additional artifact files")
@click.option("--tool-version", default="", help="Tool version")
def evidence(tool: str, input_file: str, output_file: str, result: str,
             artifact_files: tuple[str, ...], tool_version: str) -> None:
    """Create a signed EvidenceCommit for a tool execution event."""
    ctx = click.get_current_context()
    store_path = Path(ctx.obj["store"])
    store = Store.open(store_path)

    try:
        signing = store.load_signing_key()
    except StoreError as e:
        raise click.ClickException(str(e))

    identities = store.load_identities()
    if not identities:
        raise click.ClickException("no identities in store — run `alethech init` first")
    identity = next(iter(identities.values()))

    input_hash = _hash_file(input_file)
    output_hash = _hash_file(output_file)

    artifacts_meta = []
    for af in artifact_files:
        data = Path(af).read_bytes()
        if len(data) > 100 * 1024 * 1024:
            raise click.ClickException(f"artifact too large (>100MB): {af}")
        h = store.write_artifact(data)
        artifacts_meta.append({
            "name": Path(af).name,
            "hash": h,
            "size": len(data),
        })

    ev = EvidenceCommit(
        agent_id=identity.agent_id,
        key_id=identity.key_id,
        event_type="tool_execution",
        tool=tool,
        tool_version=tool_version,
        input_hash=input_hash,
        output_hash=output_hash,
        artifacts=artifacts_meta,
        result=result,
    )
    ev.sign(signing)
    store.write_evidence(ev)

    click.echo(f"evidence: {ev.commit_id}")
    click.echo(f"tool: {ev.tool}")
    click.echo(f"input_hash: {ev.input_hash}")
    click.echo(f"output_hash: {ev.output_hash}")
    click.echo(f"artifacts: {len(artifacts_meta)}")


# ---------- 4. verify ----------

@cli.command()
@click.option("--strict", is_flag=True, help="Fail on warnings")
@click.option("--emit-checkpoint", "emit_checkpoint", type=click.Path(),
              help="Generate a signed checkpoint file at this path")
@click.option("--checkpoint", "checkpoint_file", type=click.Path(exists=True),
              help="External checkpoint file to verify continuity against")
def verify(strict: bool, emit_checkpoint: str | None, checkpoint_file: str | None) -> None:
    """Verify the whole store. Standalone — no network, no LLM."""
    ctx = click.get_current_context()
    store_path = Path(ctx.obj["store"])
    store = Store.open(store_path)

    # Load optional external checkpoint
    cp = None
    if checkpoint_file:
        cp_data = json.loads(Path(checkpoint_file).read_text(encoding="utf-8"))
        cp = Checkpoint.from_dict(cp_data)

    report = verify_store(store, checkpoint=cp)

    # Emit checkpoint if requested (only if verify passes)
    if emit_checkpoint and report.ok:
        signing = store.load_signing_key()
        identities = store.load_identities()
        if identities:
            identity = next(iter(identities.values()))
            commits = store.load_commits()
            evidence = store.load_evidence()
            head = store.read_head() or ""
            new_cp = Checkpoint(
                agent_id=identity.agent_id,
                head_commit_id=head,
                commit_count=len(commits),
                evidence_count=len(evidence),
            )
            new_cp.sign(signing)
            cp_dict = new_cp.to_signed_dict()
            # Rename "commit_id" field to "checkpoint_id" for clarity on disk
            # (already done in Checkpoint.to_signed_dict)
            Path(emit_checkpoint).write_text(
                json.dumps(cp_dict, indent=2),
                encoding="utf-8",
            )
            click.echo(f"checkpoint written: {emit_checkpoint}")
            click.echo(f"  checkpoint_id: {new_cp.commit_id}")
            click.echo(f"  head: {new_cp.head_commit_id}")

    click.echo(report.summary())
    if strict and report.warnings:
        sys.exit(1)
    sys.exit(0 if report.ok else 1)


# ---------- 5. export ----------

@cli.command()
@click.option("--output", required=True, type=click.Path(), help="Output directory (or .tar file)")
@click.option("--include-artifacts/--no-artifacts", default=True, help="Include artifact bytes (default: yes)")
@click.option("--emit-checkpoint/--no-emit-checkpoint", default=False, help="Emit external checkpoint file")
def export(output: str, include_artifacts: bool, emit_checkpoint: bool) -> None:
    """Export the store to a portable package."""
    ctx = click.get_current_context()
    store_path = Path(ctx.obj["store"])
    store = Store.open(store_path)

    # First verify
    report = verify_store(store)
    if not report.ok:
        click.echo("verify failed — refusing to export corrupted store", err=True)
        click.echo(report.summary(), err=True)
        sys.exit(1)

    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "identities").mkdir(exist_ok=True)
    (out / "commits").mkdir(exist_ok=True)
    (out / "evidence").mkdir(exist_ok=True)
    (out / "artifacts").mkdir(exist_ok=True)

    # Copy identities
    identities = store.load_identities()
    for ident in identities.values():
        (out / "identities" / f"{ident.agent_id}.json").write_text(
            json.dumps(ident.to_dict(), indent=2), encoding="utf-8"
        )

    # Copy commits
    commits = store.load_commits()
    for commit in commits.values():
        (out / "commits" / f"{commit.commit_id}.json").write_text(
            json.dumps(commit.to_signed_dict(), indent=2), encoding="utf-8"
        )

    # Copy evidence
    evidence = store.load_evidence()
    for ev in evidence.values():
        (out / "evidence" / f"{ev.commit_id}.json").write_text(
            json.dumps(ev.to_signed_dict(), indent=2), encoding="utf-8"
        )

    # Copy artifacts
    artifact_count = 0
    total_bytes = 0
    if include_artifacts:
        for h in store.list_artifacts():
            data = store.read_artifact(h)
            if data is not None:
                (out / "artifacts" / h).write_bytes(data)
                artifact_count += 1
                total_bytes += len(data)

    # Manifest
    signing = store.load_signing_key()
    identities = store.load_identities()
    identity = next(iter(identities.values()))
    head = store.read_head() or ""

    manifest = {
        "type": "MemexExport",
        "version": 1,
        "exported_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "exported_by": identity.agent_id,
        "commit_count": len(commits),
        "evidence_count": len(evidence),
        "artifact_count": artifact_count,
        "total_bytes": total_bytes,
        "head_commit_id": head,
    }
    # Compute manifest hash (without manifest_hash field)
    from .canonical import canonical_json_bytes
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_hash = "sha256:" + crypto.sha256_hex(manifest_bytes)
    manifest["manifest_hash"] = manifest_hash

    # Sign manifest
    msg = canonical_json_bytes(manifest)
    sig = signing.sign(msg)
    manifest["signature"] = "ed25519:" + crypto.b64url(sig)

    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    click.echo(f"exported to: {out}")
    click.echo(f"commits: {len(commits)}")
    click.echo(f"evidence: {len(evidence)}")
    click.echo(f"artifacts: {artifact_count} ({total_bytes} bytes)")
    click.echo(f"manifest_hash: {manifest_hash}")

    # Optional checkpoint
    if emit_checkpoint:
        cp = Checkpoint(
            agent_id=identity.agent_id,
            head_commit_id=head,
            commit_count=len(commits),
            evidence_count=len(evidence),
        )
        cp.sign(signing)
        cp_path = str(out) + ".checkpoint.json"
        Path(cp_path).write_text(
            json.dumps(cp.to_signed_dict(), indent=2), encoding="utf-8"
        )
        click.echo(f"checkpoint: {cp_path}")


# ---------- 6. import ----------

@cli.command(name="import")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True), help="Path to import from")
@click.option("--target", "target_path", default=None, help="Target alethech store (default: same as --store)")
@click.option("--trust-unknown-identities", is_flag=True, help="Allow importing commits from unknown identities")
@click.option("--allow-conflicts", is_flag=True, help="Allow HEAD conflicts (will not auto-update HEAD)")
@click.option("--checkpoint", "checkpoint_file", type=click.Path(exists=True), help="External checkpoint to verify continuity")
def import_(input_path: str, target_path: str | None,
            trust_unknown_identities: bool, allow_conflicts: bool,
            checkpoint_file: str | None) -> None:
    """Import a portable package into the target store."""
    ctx = click.get_current_context()
    if target_path is None:
        target_path = ctx.obj["store"]
    target = Path(target_path)

    src = Path(input_path)

    # If src is a directory, expect manifest.json
    if src.is_dir():
        manifest_path = src / "manifest.json"
        if not manifest_path.is_file():
            raise click.ClickException(f"no manifest.json in {src}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        raise click.ClickException(f"input must be a directory: {src}")

    # Step 1: Parse manifest
    if manifest.get("type") != "MemexExport":
        raise click.ClickException(f"not a MemexExport manifest: type={manifest.get('type')}")

    # Step 2: Hash verification
    from .canonical import canonical_json_bytes
    manifest_no_hash = {k: v for k, v in manifest.items() if k not in ("manifest_hash", "signature")}
    recomputed = "sha256:" + crypto.sha256_hex(canonical_json_bytes(manifest_no_hash))
    if recomputed != manifest.get("manifest_hash"):
        raise click.ClickException("manifest_hash mismatch — manifest has been tampered with")

    # Step 3: Signature verification
    sig_str = manifest.get("signature", "")
    if not sig_str.startswith("ed25519:"):
        raise click.ClickException("manifest signature missing or malformed")
    sig_bytes = crypto.b64url_decode(sig_str[len("ed25519:"):])

    # Load exporter identity
    exporter_id = manifest.get("exported_by", "")
    exporter_identity_path = src / "identities" / f"{exporter_id}.json"
    if not exporter_identity_path.is_file():
        raise click.ClickException(f"exporter identity not in package: {exporter_id}")
    exporter_identity = Identity.from_dict(json.loads(exporter_identity_path.read_text(encoding="utf-8")))
    if not exporter_identity.verify_self():
        raise click.ClickException("exporter identity_mismatch: agent_id does not derive from public_key")

    pub = crypto.KeyPair.public_from_jwk(exporter_identity.public_key)
    msg = canonical_json_bytes(manifest_no_hash | {"manifest_hash": manifest["manifest_hash"]})
    if not crypto.KeyPair.verify(pub, sig_bytes, msg):
        raise click.ClickException("manifest signature invalid")

    # 4: Load all identities in package
    pkg_identities: dict[str, Identity] = {}
    for path in (src / "identities").glob("*.json"):
        ident = Identity.from_dict(json.loads(path.read_text(encoding="utf-8")))
        if not ident.verify_self():
            raise click.ClickException(f"identity_mismatch in package: {ident.agent_id}")
        pkg_identities[ident.agent_id] = ident

    # 5: Load commits and evidence from package
    pkg_commits: dict[str, MemoryCommit] = {}
    for path in (src / "commits").glob("*.json"):
        commit = MemoryCommit.from_dict(json.loads(path.read_text(encoding="utf-8")))
        pkg_commits[commit.commit_id] = commit

    pkg_evidence: dict[str, EvidenceCommit] = {}
    for path in (src / "evidence").glob("*.json"):
        ev = EvidenceCommit.from_dict(json.loads(path.read_text(encoding="utf-8")))
        pkg_evidence[ev.commit_id] = ev

    # 5b: Verify each commit's signature
    for cid, commit in pkg_commits.items():
        ident = pkg_identities.get(commit.agent_id)
        if ident is None:
            raise click.ClickException(f"unknown_identity in package: commit {cid} claims {commit.agent_id}")
        if not commit.verify(ident.public_key):
            raise click.ClickException(f"signature_invalid in package: commit {cid}")

    for eid, ev in pkg_evidence.items():
        ident = pkg_identities.get(ev.agent_id)
        if ident is None:
            raise click.ClickException(f"unknown_identity in package: evidence {eid} claims {ev.agent_id}")
        if not ev.verify(ident.public_key):
            raise click.ClickException(f"signature_invalid in package: evidence {eid}")

    # 6: Open or init target store
    if not target.exists() or not any(target.iterdir()):
        store = Store.init(target)
    else:
        store = Store.open(target)

    # 7: Check known identities in target
    target_identities = store.load_identities()
    for agent_id, ident in pkg_identities.items():
        if agent_id in target_identities:
            # Verify it's the same identity
            if target_identities[agent_id].public_key != ident.public_key:
                raise click.ClickException(f"identity_collision: {agent_id} exists with different public_key in target")
            continue
        # New identity
        if not trust_unknown_identities:
            raise click.ClickException(
                f"unknown_identity: {agent_id} not in target store — use --trust-unknown-identities to import"
            )
        # Trust it — write it
        store.write_identity(ident)

    # 8: Copy commits (don't overwrite)
    target_commits = store.load_commits()
    new_commits = 0
    for cid, commit in pkg_commits.items():
        if cid in target_commits:
            continue
        store.write_commit(commit)
        new_commits += 1

    # 9: Copy evidence
    target_evidence = store.load_evidence()
    new_evidence = 0
    for eid, ev in pkg_evidence.items():
        if eid in target_evidence:
            continue
        store.write_evidence(ev)
        new_evidence += 1

    # 10: Copy artifacts
    new_artifacts = 0
    if (src / "artifacts").is_dir():
        for art_path in (src / "artifacts").iterdir():
            if not art_path.is_file():
                continue
            h = art_path.name
            if not store.read_artifact(h):
                store.write_artifact(art_path.read_bytes())
                new_artifacts += 1

    # 11: Optional checkpoint continuity check
    continuity = "not checked"
    if checkpoint_file:
        cp_data = json.loads(Path(checkpoint_file).read_text(encoding="utf-8"))
        cp = Checkpoint.from_dict(cp_data)
        target_commits = store.load_commits()
        target_evidence = store.load_evidence()
        if cp.head_commit_id not in target_commits:
            raise click.ClickException(
                f"rollback_detected: checkpoint head {cp.head_commit_id} not in target after import"
            )
        if cp.commit_count != len(target_commits):
            click.echo(f"warning: checkpoint commit_count {cp.commit_count} != target {len(target_commits)}", err=True)
        continuity = "verified"

    # Don't auto-update HEAD — that's the user's decision
    click.echo(f"imported: {new_commits} commits, {new_evidence} evidence, {new_artifacts} artifacts")
    click.echo(f"identities: {len(pkg_identities)} in package")
    click.echo(f"conflicts: 0")
    click.echo(f"continuity: {continuity}")
    click.echo("HEAD not updated — use `alethech merge` (rev 3+) or manually set HEAD")


if __name__ == "__main__":
    cli()
