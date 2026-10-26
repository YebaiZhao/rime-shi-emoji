"""Prepare a disposable fixture using read-only compiled Wanxiang assets.

Requires PyYAML; no userdb is copied. Does not deploy to the active Rime profile.
"""
import argparse
from pathlib import Path
import yaml


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True, help="Existing compiled Rime user directory")
    p.add_argument("--output", type=Path, required=True, help="NEW isolated probe directory")
    p.add_argument("--schema", default="wanxiang", help="Compiled Chinese schema to adapt")
    p.add_argument("--runtime", type=Path, help="Extracted runtime lua/shi_emoji directory; defaults to source checkout")
    p.add_argument("--candidate-slot", action="store_true", help="Enable experimental dynamic candidate slot")
    args = p.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = output / "build"
    build.mkdir()
    for path in (source / "build").iterdir():
        if path.name not in {args.schema + ".schema.yaml", "default.yaml"} and path.is_file():
            (build / path.name).symlink_to(path.resolve())
    default = yaml.safe_load((source / "build/default.yaml").read_text())
    default["switcher"]["fold_options"] = False  # Deterministic option-menu tests.
    saved = default["switcher"].setdefault("save_options", [])
    root = Path(__file__).resolve().parents[1]
    options = yaml.safe_load((root/'rime/shi_emoji.default.custom.yaml.example').read_text())['patch']['switcher/save_options/+']
    for option in options:
        if option not in saved: saved.append(option)
    (build / "default.yaml").write_text(yaml.safe_dump(default, allow_unicode=True))
    schema = yaml.safe_load((source / "build" / (args.schema + ".schema.yaml")).read_text())
    # Probe fixtures may originate from either side of the namespace migration.
    for name in ("semantic_emoji", "shi_emoji"):
        schema["engine"]["processors"] = [item for item in schema["engine"]["processors"]
                                             if item != "lua_processor@*" + name + ".processor"]
        schema["engine"]["filters"] = [item for item in schema["engine"]["filters"]
                                         if item != "lua_filter@*" + name + ".filter"]
        schema["switches"] = [item for item in schema["switches"]
                              if not item.get("name",'').startswith(name)
                              and not any(o.startswith(name) for o in item.get('options',[]))]
        schema.pop(name, None)
    schema["engine"]["processors"].insert(0, "lua_processor@*shi_emoji.processor")
    schema["engine"]["filters"].append("lua_filter@*shi_emoji.filter")
    schema["switches"].extend(yaml.safe_load((root/'rime/shi_emoji_phrase.custom.yaml.example').read_text())['patch']['switches/+'])
    if args.candidate_slot:
        schema["menu"]["page_size"] = 7
        schema["shi_emoji"] = {"candidate_slot": True}
    schema["translator"]["enable_user_dict"] = False
    (build / (args.schema + ".schema.yaml")).write_text(yaml.safe_dump(schema, allow_unicode=True))
    lua = output / "lua"
    lua.mkdir()
    for path in (source / "lua").iterdir():
        if path.name != "shi_emoji":
            (lua / path.name).symlink_to(path.resolve())
    runtime = args.runtime.resolve() if args.runtime else Path(__file__).resolve().parents[1] / "rime/lua/shi_emoji"
    (lua / "shi_emoji").symlink_to(runtime)
    (output / "opencc").symlink_to((source / "opencc").resolve())
    if (source / "dicts").exists():
        (output / "dicts").symlink_to((source / "dicts").resolve())
    for path in source.iterdir():
        if path.name.endswith(".gram"):
            (output / path.name).symlink_to(path.resolve())
    (output / ".shi-emoji-probe").write_text("Disposable probe; never use as an active Rime profile.\n")
    print(output)


if __name__ == "__main__":
    main()
