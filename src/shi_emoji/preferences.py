"""Compile only valid pinned Unicode gender/skin variants and optional addon."""
import json
from pathlib import Path
from .coverage import normalize
from .export import lua_value, runtime_source


def variant_data(rows):
    valid = {normalize(r["emoji"]): r["emoji"] for r in rows}
    bases = {normalize(r["emoji"]): r["emoji"] for r in rows if not r["skin_variant"]}
    tones = {}
    for row in rows:
        chars = list(row["emoji"])
        modifiers = [c for c in chars if 0x1F3FB <= ord(c) <= 0x1F3FF]
        if len(modifiers) == 1:
            base = normalize(''.join(c for c in chars if c not in modifiers))
            tones.setdefault(base, {})[str(ord(modifiers[0]) - 0x1F3FA)] = row["emoji"]
    output = {}
    for key, emoji in bases.items():
        stem = key.replace('\u200d♀', '').replace('\u200d♂', '')
        special = next((triple for triple in [('🧒','👧','👦'),('🧓','👵','👴')] if key in triple), None)
        if special:
            family = dict(zip(('neutral','female','male'), special))
        elif stem.startswith(('👨','👩','🧑')):
            stem = '🧑' + stem[1:]
            family = {'neutral': stem, 'female': '👩'+stem[1:], 'male': '👨'+stem[1:]}
        else:
            family = {'neutral': stem, 'female': stem+'\u200d♀', 'male': stem+'\u200d♂'}
        family = {gender: valid[value] for gender,value in family.items() if value in valid}
        if len(family) < 2:
            family = {'neutral': emoji}
        entry = {}
        for gender, base in family.items():
            entry[gender] = {'0': base, **tones.get(normalize(base), {})}
        if len(family) > 1 or any(len(v)>1 for v in entry.values()):
            output[key] = entry
    return output


def main():
    root = Path(__file__).resolve().parents[2]
    rows = json.loads((root/'data/emoji_inventory.json').read_text())
    variants = variant_data(rows)
    (root/'rime/lua/shi_emoji/variant_data.lua').write_text('-- Unicode-3.0; generated from pinned Emoji 16.0 inventory\nreturn '+lua_value(variants)+'\n')
    adult = json.loads((root/'data/adult_phrases.json').read_text())
    from .match import Matcher
    Matcher(adult)
    (root/'rime/lua/shi_emoji/adult.lua').write_text(runtime_source(adult))
    print(f'Compiled {len(variants)} variant entries; bundled extension separate from main dictionary')


if __name__ == '__main__':
    main()
