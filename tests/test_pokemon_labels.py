import unittest
from damage_agent.pokemon_labels import display_name
from damage_agent.artwork import artwork_path


class PokemonLabelsTests(unittest.TestCase):
    def test_display_names(self):
        for source, expected in [('Charizard-Mega-X','Mega Charizard X'), ('Venusaur-Mega','Mega Venusaur'),
                                 ('Indeedee','Indeedee - M'), ('Indeedee-F','Indeedee - F'),
                                 ('Meowstic-M-Mega','Mega Meowstic - M'), ('Oinkologne','Oinkologne - M')]:
            self.assertEqual(display_name(source),expected)

    def test_regional_names(self):
        for source, expected in [('Raichu-Alola','Alolan Raichu'), ('Slowbro-Galar','Galarian Slowbro'),
                                 ('Zoroark-Hisui','Hisuian Zoroark'), ('Tauros-Paldea-Blaze','Paldean Tauros-Blaze')]:
            self.assertEqual(display_name(source), expected)

    def test_gender_artwork_prefers_specific_image(self):
        for name, number in [('Indeedee',876),('Meowstic',678),('Basculegion',902),('Oinkologne',916)]:
            for suffix, label in [('', 'Male'),('-F','Female')]:
                path = artwork_path({'name':name+suffix,'num':number})
                self.assertEqual(path.name,f'{number:04d} {name} {label}.png')
