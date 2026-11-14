"""GUI gerektirmeyen uçtan uca oyun mantığı doğrulaması."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from mars_core import (BASE_X, BASE_Y, WORLD_W, Config, FlightModel,
                       GameSession, RoverModel, RoverConfig, Vehicle, Mission)
from kamera import create_capture


class RoverDroneTests(unittest.TestCase):
    def test_initial_drone_docked(self):
        game = GameSession()
        self.assertTrue(game.drone.docked)
        self.assertFalse(game.drone.airborne)
        self.assertEqual((game.drone.x, game.drone.y), (game.rover.x, game.rover.y))

    def test_first_takeoff_from_rover(self):
        game = GameSession()
        game.step(.02, climb=1)
        self.assertFalse(game.drone.docked)
        self.assertTrue(game.drone.airborne)
        self.assertGreater(game.drone.altitude, 0)

    def test_rover_moves_and_carries_docked_drone(self):
        game = GameSession()
        game.switch_vehicle()
        first = game.rover.x
        for _ in range(10):
            game.step(.02, x=1)
        self.assertGreater(game.rover.x, first)
        self.assertAlmostEqual(game.rover.x, game.drone.x)
        self.assertAlmostEqual(game.rover.y, game.drone.y)

    def test_rover_and_drone_independent(self):
        game = GameSession()
        game.step(.02, climb=1)
        first = game.drone.x
        game.switch_vehicle()
        for _ in range(20):
            game.step(.02, x=1)
        self.assertAlmostEqual(game.drone.x, first)
        self.assertNotAlmostEqual(game.rover.x, game.drone.x)

    def test_cannot_dock_far_away(self):
        game = GameSession()
        game.step(.02, climb=1)
        game.drone.x += 80
        self.assertIn("35", game.try_dock())
        self.assertFalse(game.drone.docked)

    def test_can_dock_and_offload_drone_packets(self):
        game = GameSession()
        game.step(.02, climb=1)
        rock = game.mission.rocks[0]
        game._make_packet("drone", rock)
        game.drone.altitude = 0.6
        game.drone.vertical_speed = 0
        result = game.try_dock()
        self.assertIn("1 görüntü", result)
        self.assertTrue(game.drone.docked)
        self.assertEqual(len(game.drone_packets), 0)
        self.assertEqual(len(game.rover_model.packets), 1)

    def test_battery_swap_only_while_docked(self):
        game = GameSession()
        old = game.drone.battery_wh
        self.assertIn("Batarya değişti", game.swap_battery())
        self.assertGreater(game.drone.battery_wh, old)
        self.assertEqual(game.rover.swapped_count, 1)
        game.step(.02, climb=1)
        self.assertIn("kenetlenmeli", game.swap_battery())

    def test_battery_swap_coolsafe(self):
        game = GameSession()
        game.rover.bay_temp_c = -38
        self.assertIn("çok soğuk", game.swap_battery())

    def test_rover_survey_requires_proximity(self):
        game = GameSession()
        self.assertIn("66", game.survey_rover())
        rock = game.mission.rocks[0]
        game.rover.x, game.rover.y = rock.x, rock.y
        self.assertIn("araştırma tamamladı", game.survey_rover())
        self.assertTrue(rock.surveyed)
        self.assertEqual(len(game.rover_model.packets), 1)

    def test_rover_rejects_hazard(self):
        model = RoverModel()
        x = model.state.x
        # Komuta edilen ilk hareket noktası tam engelde.
        model.step(.1, 1, 0, [(x + 5.4, model.state.y, 18)], .1)
        self.assertAlmostEqual(model.state.x, x)
        self.assertTrue(model.last_move_blocked)

    def test_solar_produces_energy(self):
        model = RoverModel()
        model.step(.1, 0, 0, [], .1)
        self.assertGreater(model.solar_w, 0)
        model.state.solar_deployed = False
        model.step(.1, 0, 0, [], .2)
        self.assertEqual(model.solar_w, 0)

    def test_battery_remains_bounded(self):
        model = RoverModel()
        capacity = model.config.battery_capacity_wh
        model.state.battery_wh = capacity - 0.001
        for i in range(20):
            model.step(.1, 0, 0, [], i*.1)
        self.assertLessEqual(model.state.battery_wh, capacity)

    def test_heater_changes_load(self):
        model = RoverModel()
        model.state.bay_temp_c = -25
        model.step(.1, 0, 0, [], .1)
        hot_load = model.load_w
        model.state.heater_enabled = False
        model.step(.1, 0, 0, [], .2)
        self.assertGreater(hot_load, model.load_w)

    def test_spare_charger_transfers_energy(self):
        model = RoverModel()
        model.state.spare_batteries_wh = [12]
        model.step(.1, 0, 0, [], .1)
        self.assertGreater(model.state.spare_batteries_wh[0], 12)
        self.assertGreater(model.charge_w, 0)

    def test_drone_packets_cannot_transmit_before_docking(self):
        game = GameSession()
        game.step(.02, climb=1)
        packet = game._make_packet("drone", game.mission.rocks[0])
        game.toggle_uplink()
        for _ in range(80):
            game.step(.1)
        self.assertFalse(packet.transferred_to_rover)
        self.assertFalse(packet.delivered)
        self.assertAlmostEqual(packet.progress_mb, 0)

    def test_rover_packets_can_transmit_to_earth_simulation(self):
        game = GameSession()
        pkt = game._make_packet("gezgin", game.mission.rocks[0])
        game.toggle_uplink()
        for _ in range(90):
            game.step(.1)
        self.assertTrue(pkt.delivered)
        self.assertAlmostEqual(pkt.progress_mb, pkt.size_mb)

    def test_uplink_toggle_halts_progress(self):
        game = GameSession()
        pkt = game._make_packet("gezgin", game.mission.rocks[0])
        game.step(.1)
        self.assertEqual(pkt.progress_mb, 0)
        game.toggle_uplink()
        game.step(.1)
        self.assertGreater(pkt.progress_mb, 0)
        game.toggle_uplink()
        previous = pkt.progress_mb
        game.step(.1)
        self.assertEqual(pkt.progress_mb, previous)

    def test_take_photo_packet(self):
        game = GameSession()
        self.assertIn("görüntüsü", game.take_photo())
        self.assertEqual(game.packets[-1].source, "gezgin")
        self.assertTrue(game.packets[-1].transferred_to_rover)

    def test_full_mission_victory(self):
        game = GameSession()
        for rock in game.mission.rocks:
            rock.scanned = True
            pkt = game._make_packet("drone", rock)
            game.rover_model.store_packet(pkt)
            game.drone_packets.remove(pkt)
        for rock in game.mission.rocks[:2]:
            rock.surveyed = True
            game._make_packet("gezgin", rock)
        for pkt in game.packets:
            pkt.delivered = True
            pkt.progress_mb = pkt.size_mb
        self.assertTrue(game.drone.docked)
        game.step(.1)
        self.assertTrue(game.mission.finished)
        self.assertFalse(game.mission.failed)

    def test_not_win_without_transmission(self):
        game = GameSession()
        for rock in game.mission.rocks:
            rock.scanned = True
            game._make_packet("gezgin", rock)
        for rock in game.mission.rocks[:2]:
            rock.surveyed = True
            game._make_packet("gezgin", rock)
        game.step(.02)
        self.assertFalse(game.mission.finished)

    def test_roundtrip_save_load(self):
        game = GameSession()
        game.take_photo()
        game.step(.1)
        game.switch_vehicle()
        game.step(.1, 1, 0)
        game.toggle_uplink()
        clone = GameSession.from_dict(json.loads(json.dumps(game.to_dict())))
        self.assertAlmostEqual(clone.rover.x, game.rover.x)
        self.assertAlmostEqual(clone.drone.x, game.drone.x)
        self.assertEqual(clone.selected, game.selected)
        self.assertEqual(clone.rover_model.uplink_enabled, True)
        self.assertEqual(clone.to_dict()["packets"], game.to_dict()["packets"])

    def test_version_1_load(self):
        game = GameSession()
        v1 = {"version": 1, "vehicle": {"x": 90, "y": 500, "vx": 0, "vy": 0,
                                         "altitude": 1, "vertical_speed": 0, "battery_wh": 22,
                                         "health": 100, "airborne": True},
              "elapsed": 12, "rocks": [{"scanned": True}, {"scanned": False}, {"scanned": False}]}
        clone = GameSession.from_dict(v1)
        self.assertEqual(clone.elapsed, 12)
        self.assertTrue(clone.mission.rocks[0].scanned)
        self.assertFalse(clone.drone.docked)

    def test_save_rejects_nan(self):
        game = GameSession()
        raw = game.to_dict()
        raw["drone"]["altitude"] = float("nan")
        with self.assertRaises(ValueError):
            GameSession.from_dict(raw)

    def test_save_rejects_invalid_packet(self):
        game = GameSession()
        raw = game.to_dict()
        raw["packets"] = [{"packet_id": "not a number"}]
        with self.assertRaises(ValueError):
            GameSession.from_dict(raw)

    def test_png_capture_is_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            fname = create_capture(Path(temporary), "drone", 1, 500, 350, 1.6, "Kaya")
            blob = Path(fname).read_bytes()
            self.assertTrue(blob.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertIn(b"IHDR", blob)
            self.assertGreater(len(blob), 200)
            self.assertEqual(Path(fname).suffix, ".png")

    def test_end_to_end_scanning_docking_uplink_victory(self):
        """Tarama ve aktarım işlevleriyle uçtan uca görev akışı."""
        game = GameSession()
        game.step(.02, climb=1)
        game.drone.altitude = 1.5
        for target in game.mission.rocks:
            game.drone.x, game.drone.y = target.x, target.y
            self.assertIn("başarıyla tarandı", game.scan_drone())
        self.assertEqual(len(game.drone_packets), 3)
        for target in game.mission.rocks[:2]:
            game.rover.x, game.rover.y = target.x, target.y
            self.assertIn("araştırma tamamladı", game.survey_rover())
        # Gezginin yanında güvenli alçalış / sensörlerin veri indirmesi.
        game.drone.x, game.drone.y = game.rover.x, game.rover.y
        game.drone.altitude = .5
        game.drone.vertical_speed = 0
        self.assertIn("3 görüntü", game.try_dock())
        self.assertEqual(game.mission_progress()["waiting_on_drone"], 0)
        game.rover.x, game.rover.y = BASE_X, BASE_Y
        game.toggle_uplink()
        for _ in range(150):
            game.step(.1)
            if game.mission.finished:
                break
        self.assertTrue(game.mission.finished)
        self.assertEqual(game.mission_progress()["transmitted"], 5)

    def test_dust_storm_and_shelter_protection(self):
        game = GameSession()
        game.elapsed = 99.9
        game.rover_model.step(.1, 0, 0, [], game.elapsed)
        self.assertTrue(game.rover_model.storm_active)
        sheltered_health = game.drone.health
        game.step(.1)
        self.assertEqual(game.drone.health, sheltered_health)
        game.step(.02, climb=1)
        airborne_health = game.drone.health
        game.step(.1)
        self.assertLess(game.drone.health, airborne_health)

    def test_reject_camera_path_escape(self):
        game = GameSession()
        game.take_photo()
        obj = game.to_dict()
        obj["packets"][0]["image_file"] = "../../private.png"
        with self.assertRaises(ValueError):
            GameSession.from_dict(obj)

    def test_legacy_physics_preserved(self):
        model = FlightModel(Config())
        model.step(.02, climb=1)
        self.assertTrue(model.vehicle.airborne)
        self.assertGreater(model.estimate_power(6.678), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
