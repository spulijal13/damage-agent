import copy
import os
import tempfile
import unittest

from agent import apply_common_corrections, ensure_default_doubles
from showdown_bridge import run_showdown_calc, explain_showdown_damage


class DamageTests(unittest.TestCase):
    def battle(self, move="Dire Claw", attacker="Sneasler", defender="Primarina"):
        return {"attacker": {"name": attacker}, "defender": {"name": defender},
                "move": move, "field": {}}

    def test_physical_critical_and_screens(self):
        battle = self.battle()
        baseline = run_showdown_calc(battle)["max_damage"]
        self.assertEqual(baseline, 174)
        for screen in ("reflect", "aurora_veil"):
            battle["field"] = {screen: True}
            self.assertLess(run_showdown_calc(battle)["max_damage"], baseline)
        battle["field"] = {"critical": True}
        self.assertGreater(run_showdown_calc(battle)["max_damage"], baseline)

    def test_move_name_normalization(self):
        baseline = run_showdown_calc(self.battle("Drain Punch"))
        for name in ("drainpunch", "DRAIN PUNCH", "drain-punch", "drain_punch"):
            with self.subTest(name=name):
                result = run_showdown_calc(self.battle(name))
                self.assertEqual(result["move"], "Drain Punch")
                self.assertEqual(result["damage"], baseline["damage"])

    def test_unresolved_move_typo_requests_clarification(self):
        with self.assertRaisesRegex(RuntimeError, "Please restate your battle question"):
            run_showdown_calc(self.battle("close compbat"))

    def test_light_screen(self):
        battle = self.battle("Moonblast", "Primarina", "Sneasler")
        baseline = run_showdown_calc(battle)["max_damage"]
        battle["field"]["light_screen"] = True
        self.assertLess(run_showdown_calc(battle)["max_damage"], baseline)

    def test_current_hp_changes_damage(self):
        battle = self.battle("Eruption", "Typhlosion", "Blissey")
        baseline = run_showdown_calc(battle)["max_damage"]
        battle["attacker"]["current_hp_percent"] = 50
        battle["defender"]["current_hp_percent"] = 50
        result = run_showdown_calc(battle)
        self.assertLess(result["max_damage"], baseline)
        self.assertEqual(result["defender_current_hp"], result["defender_hp"] // 2)

    def test_independent_of_working_directory(self):
        original = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.chdir(directory)
                self.assertEqual(run_showdown_calc(self.battle())["max_damage"], 174)
        finally:
            os.chdir(original)

    def test_unknown_names_and_unsupported_grounding(self):
        for role in ("attacker", "defender"):
            battle = self.battle()
            battle[role]["name"] = "Not a Pokemon"
            with self.assertRaisesRegex(RuntimeError, "Unknown Pokemon"):
                run_showdown_calc(battle)
        battle = self.battle("Not a Move")
        with self.assertRaisesRegex(RuntimeError, "Unknown move"):
            run_showdown_calc(battle)
        battle = self.battle()
        battle["defender"]["grounded"] = True
        with self.assertRaisesRegex(RuntimeError, "grounded"):
            run_showdown_calc(battle)

    def test_nested_damage_range(self):
        battle = self.battle("Body Slam", "Kangaskhan-Mega", "Blissey")
        battle["attacker"]["ability"] = "Parental Bond"
        result = run_showdown_calc(battle)
        self.assertIsInstance(result["damage"][0], list)
        self.assertEqual(result["min_damage"], sum(min(hit) for hit in result["damage"]))
        self.assertEqual(result["min_damage"], result["range"][0])
        self.assertEqual(result["max_damage"], result["range"][1])
        self.assertIsInstance(result["max_damage"], (int, float))
        self.assertIn("Damage:", explain_showdown_damage(result))

    def test_corrections_preserve_parser_choices(self):
        battle = self.battle("Drain Punch")
        battle["field"] = {"critical": False, "weather": None}
        battle["defender"]["item"] = "Life Orb"
        request = {"mode": "damage", "battle": battle}
        corrected = apply_common_corrections(copy.deepcopy(request),
            "Sneasler Drain Punch vs Primarina holding Life Orb, no crit, not Close Combat")
        self.assertEqual(corrected, request)
        self.assertTrue(ensure_default_doubles(corrected, "damage")["battle"]["field"]["is_double_battle"])
        self.assertFalse(ensure_default_doubles(corrected, "singles")["battle"]["field"]["is_double_battle"])

    def test_missing_battle_clarifies(self):
        result = apply_common_corrections({"mode": "damage"}, "damage")
        self.assertEqual(result["mode"], "clarify")


if __name__ == "__main__":
    unittest.main()
