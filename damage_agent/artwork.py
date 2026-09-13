"""Match supplied Sugimori artwork by Pokédex number and canonical form name."""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

ART_ROOT = Path(__file__).resolve().parents[1] / 'Sugimori_Art'


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
    candidates = [name, aliases.get(name, name)]
    if name.startswith('Ogerpon-'):
        candidates.append(name + ' Mask')
    for candidate in candidates:
        path = artwork_index().get((pokemon['num'], normalized(candidate)))
        if path:
            return path
    # Names can differ between the Pokédex and the artwork collection. Prefer
    # the main species illustration (shallower directory), never another number.
    same_number = [path for (number, _), path in artwork_index().items()
                   if number == pokemon['num']]
    return min(same_number, key=lambda path: (
        'Alternate Versions' in path.parts,
        len(path.relative_to(ART_ROOT).parts), len(path.stem), str(path),
    ), default=None)
