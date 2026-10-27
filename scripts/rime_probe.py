"""Headless Rime C-API probe. Uses a dedicated user-data directory, never your live session.

ABI declarations follow https://github.com/rime/librime/blob/master/src/rime_api.h
Uses the int-Bool rime_get_api entrypoint. Python standard library only.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import time


class Traits(C.Structure):
    _fields_ = [("data_size", C.c_int)] + [(name, C.c_char_p) for name in (
        "shared_data_dir", "user_data_dir", "distribution_name", "distribution_code_name",
        "distribution_version", "app_name")] + [("modules", C.POINTER(C.c_char_p)),
        ("min_log_level", C.c_int), ("log_dir", C.c_char_p),
        ("prebuilt_data_dir", C.c_char_p), ("staging_dir", C.c_char_p)]


class Composition(C.Structure):
    _fields_ = [(key, C.c_int) for key in ("length", "cursor_pos", "sel_start", "sel_end")] + [("preedit", C.c_char_p)]


class Candidate(C.Structure):
    _fields_ = [("text", C.c_char_p), ("comment", C.c_char_p), ("reserved", C.c_void_p)]


class Menu(C.Structure):
    _fields_ = [(key, C.c_int) for key in ("page_size", "page_no", "is_last_page", "highlighted_candidate_index", "num_candidates")] + [("candidates", C.POINTER(Candidate)), ("select_keys", C.c_char_p)]


class Context(C.Structure):
    _fields_ = [("data_size", C.c_int), ("composition", Composition), ("menu", Menu),
                ("commit_text_preview", C.c_char_p), ("select_labels", C.POINTER(C.c_char_p))]


class Commit(C.Structure):
    _fields_ = [("data_size", C.c_int), ("text", C.c_char_p)]


NAMES = """setup set_notification_handler initialize finalize start_maintenance is_maintenance_mode
join_maintenance_thread deployer_initialize prebuild deploy deploy_schema deploy_config_file sync_user_data
create_session find_session destroy_session cleanup_stale_sessions cleanup_all_sessions process_key
commit_composition clear_composition get_commit free_commit get_context free_context get_status free_status
set_option get_option set_property get_property get_schema_list free_schema_list get_current_schema select_schema
schema_open config_open config_close config_get_bool config_get_int config_get_double config_get_string
config_get_cstring config_update_signature config_begin_map config_next config_end simulate_key_sequence""".split()


class Api(C.Structure):
    _fields_ = [("data_size", C.c_int)] + [(name, C.c_void_p) for name in NAMES]


def sized(cls):
    obj = cls()
    obj.data_size = C.sizeof(cls) - C.sizeof(C.c_int)
    return obj


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--library", type=Path, default=Path("/Library/Input Methods/Squirrel.app/Contents/Frameworks/librime.1.dylib"))
    p.add_argument("--plugin", type=Path, default=Path("/Library/Input Methods/Squirrel.app/Contents/Frameworks/rime-plugins/librime-lua.dylib"))
    p.add_argument("--shared", type=Path, default=Path("/Library/Input Methods/Squirrel.app/Contents/SharedSupport"))
    p.add_argument("--user", type=Path, required=True)
    p.add_argument("--schema", default="wanxiang")
    p.add_argument("--keys", required=True, help="Rime key sequence, e.g. {Control+Shift+e}wanshua")
    p.add_argument("--mode", action="store_true")
    p.add_argument("--option-state", choices=["off", "on", "saved"], default="off",
                   help="Initialize plugin state explicitly for independent tests, or restore saved state")
    p.add_argument("--ascii", action="store_true")
    p.add_argument("--menu-toggle", action="store_true", help="Toggle 诗Emoji through the native switcher menu")
    p.add_argument("--menu-select", action="append", default=[], help="Select exact native option label; repeat for several preferences")
    args = p.parse_args()
    lib = C.CDLL(str(args.library), mode=C.RTLD_GLOBAL)
    plugin = C.CDLL(str(args.plugin), mode=C.RTLD_GLOBAL)
    lib.rime_get_api.restype = C.POINTER(Api)
    api = lib.rime_get_api().contents

    def fn(name, result, *types):
        if Api.__dict__[name].offset + C.sizeof(C.c_void_p) > api.data_size + 4:
            raise RuntimeError(f"Rime API is too old for {name}")
        return C.CFUNCTYPE(result, *types)(getattr(api, name))

    traits = sized(Traits)
    traits.shared_data_dir = str(args.shared.resolve()).encode()
    traits.user_data_dir = str(args.user.resolve()).encode()
    traits.app_name = b"rime.shi_emoji_probe"
    traits.min_log_level = 2
    traits.modules = (C.c_char_p * 3)(b"default", b"lua", None)
    fn("setup", None, C.POINTER(Traits))(C.byref(traits))
    fn("initialize", None, C.POINTER(Traits))(C.byref(traits))
    session = fn("create_session", C.c_size_t)()
    try:
        if not fn("select_schema", C.c_int, C.c_size_t, C.c_char_p)(session, args.schema.encode()):
            raise RuntimeError("Schema selection failed")
        fn("set_option", None, C.c_size_t, C.c_char_p, C.c_int)(session, b"ascii_mode", int(args.ascii))
        if args.mode or args.option_state != "saved":
            fn("set_option", None, C.c_size_t, C.c_char_p, C.c_int)(
                session, b"shi_emoji", int(args.mode or args.option_state == "on"))
        selections = ([None] if args.menu_toggle else []) + args.menu_select
        for selection in selections:
            simulate = fn("simulate_key_sequence", C.c_int, C.c_size_t, C.c_char_p)
            simulate(session, b"{Control+grave}")
            while True:
                menu_context = sized(Context)
                fn("get_context", C.c_int, C.c_size_t, C.POINTER(Context))(session, C.byref(menu_context))
                labels = [(menu_context.menu.candidates[i].text or b"").decode()
                          for i in range(menu_context.menu.num_candidates)]
                last_page = bool(menu_context.menu.is_last_page)
                fn("free_context", C.c_int, C.POINTER(Context))(C.byref(menu_context))
                wanted = {selection} if selection else {"诗Emoji关", "诗Emoji开"}
                found = next((i for i, label in enumerate(labels) if label in wanted), None)
                if found is not None:
                    simulate(session, str(found + 1).encode())
                    break
                if last_page:
                    raise RuntimeError(f"Requested switch not present in native menu: {wanted}")
                simulate(session, b"{Page_Down}")
        started = time.perf_counter()
        fn("simulate_key_sequence", C.c_int, C.c_size_t, C.c_char_p)(session, args.keys.encode())
        context = sized(Context)
        fn("get_context", C.c_int, C.c_size_t, C.POINTER(Context))(session, C.byref(context))
        rows = [{"text": context.menu.candidates[i].text.decode(),
                 "comment": (context.menu.candidates[i].comment or b"").decode()}
                for i in range(context.menu.num_candidates)]
        highlighted = context.menu.highlighted_candidate_index
        page_no = context.menu.page_no
        preedit = (context.composition.preedit or b"").decode()
        fn("free_context", C.c_int, C.POINTER(Context))(C.byref(context))
        elapsed = (time.perf_counter() - started) * 1000
        commit = sized(Commit)
        committed = ""
        if fn("get_commit", C.c_int, C.c_size_t, C.POINTER(Commit))(session, C.byref(commit)):
            committed = commit.text.decode()
            fn("free_commit", C.c_int, C.POINTER(Commit))(C.byref(commit))
        mode = fn("get_option", C.c_int, C.c_size_t, C.c_char_p)(session, b"shi_emoji")
        print(json.dumps({"keys": args.keys, "preedit": preedit, "candidates": rows,
                          "highlighted": highlighted, "page_no": page_no,
                          "commit": committed, "mode": bool(mode), "sequence_ms": elapsed}, ensure_ascii=False, indent=2))
    finally:
        fn("destroy_session", C.c_int, C.c_size_t)(session)
        fn("finalize", None)()


if __name__ == "__main__":
    main()
