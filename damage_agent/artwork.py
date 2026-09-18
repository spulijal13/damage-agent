"""Match supplied Sugimori artwork by Pokédex number and canonical form name."""
from damage_agent.pokemon_catalog import gendered_name

import re
import unicodedata
from functools import lru_cache
from difflib import SequenceMatcher
from pathlib import Path

ART_ROOT = Path(__file__).resolve().parents[1] / 'images' / 'pokemon_art'


def normalized(name):
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    name = name.replace('gigantamax', 'gmax')
    return re.sub(r'[^a-z0-9]', '', name)


@lru_cache(maxsize=1)
def artwork_index():
    result = {}
    # Prefer the main collection over alternate illustrations of the same form.
    for path in sorted(ART_ROOT.rglob('*.png'), key=lambda p: ('Alternate Versions' in p.parts, str(p))):
        match = re.match(r'^(\d+)\s+(.+)$', path.stem)
        if match:
            result.setdefault((int(match[1]), normalized(match[2])), path)
    return result


def artwork_path(pokemon):
    name = pokemon['name']
    # These forms deliberately share an illustration.
    if name in ('Meowstic-M-Mega', 'Meowstic-F-Mega'):
        name = 'Meowstic-M-Mega'
    elif name in ('Magearna-Mega', 'Magearna-Original-Mega'):
        name = 'Magearna-Mega'
    elif name == 'Magearna-Original':
        name = 'Magearna'
    elif name == 'Tatsugiri' or name.startswith('Tatsugiri-'):
        name = 'Tatsugiri-Mega' if name.endswith('-Mega') else 'Tatsugiri'
    aliases = {
        'Cherrim': 'Cherrim Overcast', 'Cherrim-Sunshine': 'Cherrim Sunny',
        'Deerling': 'Deerling Spring', 'Sawsbuck': 'Sawsbuck Spring',
        'Basculin-Blue-Striped': 'Basculin Blue', 'Basculin-White-Striped': 'Basculin White',
        'Zygarde-10%': 'Zygarde 10Percent', 'Toxtricity': 'Toxtricity Amped',
        'Eiscue': 'Eiscue Ice', 'Calyrex-Ice': 'Calyrex Ice Rider',
        'Calyrex-Shadow': 'Calyrex Shadow Rider', 'Oinkologne-F': 'Oinkologne Female',
        'Pikachu-Starter': 'Pikachu Partner', 'Eevee-Starter': 'Eevee Partner',
        'Nidoran-F': 'Nidoran', 'Nidoran-M': 'Nidoran',
        'Basculegion-F': 'Basculegion Female',
        'Indeedee-F': 'Indeedee Female', 'Meowstic-F': 'Meowstic Female',
        'Urshifu-Gmax': 'Urshifu Gigantamax Single Strike',
        'Urshifu-Rapid-Strike-Gmax': 'Urshifu Gigantamax Rapid Strike',
    }
    gender_name = gendered_name(name)
    if gender_name:
        candidates = [gender_name, re.sub(r'-M(?=-|$)', ' Male', re.sub(r'-F(?=-|$)', ' Female', gender_name))]
        # Nidoran's numbered artwork omits the gender suffix; its numbers differ.
        if name.startswith('Nidoran-'):
            candidates.append('Nidoran')
    else:
        candidates = [name, aliases.get(name, name)]
    if name.startswith('Ogerpon-'):
        candidates.append(name + ' Mask')
    for candidate in candidates:
        path = artwork_index().get((pokemon['num'], normalized(candidate)))
        if path:
            return path
    # Prefer the closest form name, never artwork from another Pokédex number.
    # Main-collection and base-species preferences only break similarity ties.
    same_number = [(art_name, path) for (number, art_name), path in artwork_index().items()
                   if number == pokemon['num']]
    if not same_number:
        return None
    normalized_candidates = [normalized(candidate) for candidate in candidates]
    def rank(entry):
        art_name, path = entry
        return (
            -max(SequenceMatcher(None, candidate, art_name).ratio() for candidate in normalized_candidates),
            'Alternate Versions' in path.parts,
            len(path.relative_to(ART_ROOT).parts), len(path.stem), str(path),
        )
    return min(same_number, key=rank)[1]
