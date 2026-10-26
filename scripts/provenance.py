"""Record source and calculation files that produced a reporting build."""
import hashlib


def build_inputs(root,files):
    paths=[root/'docs/source_manifest.json',root/'docs/verification.json']
    paths.extend(root/name for name in files)
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
