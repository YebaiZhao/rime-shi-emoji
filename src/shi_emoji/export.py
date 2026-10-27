"""Export reviewed intent phrases as a Lua data module, without model dependencies."""
import argparse
import json
from pathlib import Path
from .match import Matcher
from .datafiles import merged_data


def lua_value(value):
    if isinstance(value, str):
        # JSON's \u escapes are not Lua escapes. Keep Unicode literal, escape
        # only ASCII controls and string delimiters with Lua-compatible syntax.
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t') + '"'
    if isinstance(value, list):
        return "{" + ",".join(lua_value(item) for item in value) + "}"
    if isinstance(value, dict):
        return "{" + ",".join("[" + lua_value(key) + "]=" + lua_value(item) for key, item in value.items()) + "}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    raise TypeError(type(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phrases", type=Path, default=Path("data/phrases.json"))
    parser.add_argument("--output", type=Path, default=Path("rime/lua/shi_emoji/data.lua"))
    parser.add_argument("--curated-only", action="store_true")
    args = parser.parse_args()
    data = merged_data(args.phrases, include_generated=not args.curated_only)
    Matcher(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(runtime_source(data), encoding="utf-8")
    print(f"Exported {len(data['rules'])} intent rules to {args.output}")


def runtime_source(data):
    license_note = ("MIT; includes Unicode-3.0, jieba MIT, and OpenCC Apache-2.0 derived data; "
                    "see THIRD_PARTY_NOTICES.md") if "attribution" in data else "MIT"
    runtime = {key: value for key, value in data.items()
               if key in {"version", "negators", "boundaries", "word_guards", "attribution"}}
    runtime["rules"] = [{key: value for key, value in rule.items()
                         if key in {"id", "phrases", "emoji", "priority", "suffix", "exact_only", "min_context_len"}}
                        for rule in data["rules"]]
    return "-- Generated from reviewed phrase data; " + license_note + "\nreturn " + lua_value(runtime) + "\n"


if __name__ == "__main__":
    main()
