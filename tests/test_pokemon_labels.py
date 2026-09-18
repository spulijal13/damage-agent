import unittest
from damage_agent.pokemon_catalog import display_name
from damage_agent.artwork import artwork_path


class PokemonLabelsTests(unittest.TestCase):
    def test_display_names(self):
        for source, expected in [('Charizard-Mega-X','Mega X Charizard'), ('Venusaur-Mega','Mega Venusaur'),
                                 ('Pikachu-Rock-Star', 'Rock Star Pikachu'), ('Pikachu', 'Pikachu'),
                                 ('Indeedee','Indeedee-M'), ('Indeedee-F','Indeedee-F'),
                                 ('Nidoran-M', 'Nidoran-M'), ('Nidoran-F', 'Nidoran-F'),
                                 ('Meowstic-M-Mega','Mega Meowstic-M'), ('Oinkologne','Oinkologne-M')]:
            self.assertEqual(display_name(source),expected)

    def test_regional_names(self):
        for source, expected in [('Raichu-Alola','Alola Raichu'), ('Slowbro-Galar','Galar Slowbro'),
                                 ('Zoroark-Hisui','Hisui Zoroark'), ('Tauros-Paldea-Blaze','Paldea Blaze Tauros')]:
            self.assertEqual(display_name(source), expected)

    def test_gender_artwork_prefers_specific_image(self):
        for name, number in [('Indeedee',876),('Meowstic',678),('Basculegion',902),('Oinkologne',916)]:
            for suffix, label in [('', 'Male'),('-F','Female')]:
                path = artwork_path({'name':name+suffix,'num':number})
                self.assertEqual(path.name,f'{number:04d} {name} {label}.png')
