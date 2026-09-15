"""Presentation names; canonical names remain stable in storage and calculations."""
import re

GENDERED_SPECIES = {'Indeedee', 'Meowstic', 'Basculegion', 'Oinkologne'}


def gendered_name(name):
    if name in GENDERED_SPECIES:
        return name + '-M'
    if re.search(r'-(M|F)(?:-|$)', name):
        return name
    return None


def display_name(name):
    name = gendered_name(name) or name
    for region, adjective in [('Alola', 'Alolan'), ('Galar', 'Galarian'), ('Hisui', 'Hisuian'), ('Paldea', 'Paldean')]:
        if re.search(rf'-{region}(?=-|$)', name):
            name = adjective + ' ' + re.sub(rf'-{region}(?=-|$)', '', name)
            break
    if '-Mega' in name:
        base, suffix = name.split('-Mega', 1)
        name = 'Mega ' + base + suffix.replace('-', ' ')
    return re.sub(r'-(M|F)(?= |$)', r' - \1', name)
