"""Build a user-only runtime archive; never package model weights or local profiles."""
from pathlib import Path
import hashlib
import json
import zipfile

USER_DOCS = ('adult-addon.md','architecture.md','coverage.md','evaluation.md','first-run.md',
             'experimental-candidate-slot.md','experimental-zero-key.md','mapping-resolution.md','model-review-sample.md','model-supervision.md','naming.md',
             'manual-integration.md','phrase-mode.md','phrase-results.md','preferences.md','release-engineering.md','word-boundaries.md')


def package(root, output):
    root, output = Path(root), Path(output)
    output.parent.mkdir(exist_ok=True)
    files = {root / "INSTALL.md": "INSTALL.md", root / "LICENSE": "LICENSE",
             root / "THIRD_PARTY_NOTICES.md": "THIRD_PARTY_NOTICES.md"}
    for name in ('README.md','README.en.md','CONTRIBUTING.md','CHANGELOG.md','release.json'):
        files[root/name] = name
    for name in USER_DOCS:
        files[root/'docs'/name] = 'docs/'+name
    for name in ("compose.lua", "data.lua", "filter.lua", "matcher.lua", "processor.lua", "settings.lua", "variants.lua", "variant_data.lua", "adult.lua"):
        path = root / "rime/lua/shi_emoji" / name
        files[path] = "lua/shi_emoji/" + path.name
    for name in ("Unicode-3.0.txt", "jieba-MIT.txt"):
        path = root / "licenses" / name
        files[path] = "licenses/" + path.name
    for name in ("shi_emoji_phrase.custom.yaml.example", "shi_emoji.default.custom.yaml.example"):
        files[root / "rime" / name] = name
    payloads = {name: path.read_bytes() for path, name in files.items()}
    return write_archive(payloads, output)


def write_archive(payloads, output):
    manifest = {name: hashlib.sha256(content).hexdigest() for name, content in sorted(payloads.items())}
    payloads["MANIFEST.sha256.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(payloads.items()):
            entry = zipfile.ZipInfo("rime-shi-emoji/" + name, date_time=(2020, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return manifest


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "dist/rime-shi-emoji-runtime.zip"
    package(root, output)
    print(f"Built {output} ({output.stat().st_size} bytes)")
    version = json.loads((root/'release.json').read_text())['version']
    versioned = root/'dist'/f'rime-shi-emoji-{version}.zip'
    versioned.write_bytes(output.read_bytes())
    checksum = root/'dist/SHA256SUMS'
    checksum.write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')
    print(f'Prepared {versioned.name} and SHA256SUMS (not published)')


if __name__ == "__main__":
    main()
