import unittest
from mars_oyunu import (Config, FlightModel, Mission, Vehicle,
                        gerekliHavadaKalmaItisi, itisAnalizi)

class FlightTests(unittest.TestCase):
    def test_original_force(self):
        self.assertAlmostEqual(gerekliHavadaKalmaItisi(1.8), 6.678)
    def test_original_analysis(self):
        a = itisAnalizi(6.678)
        self.assertTrue(a['havadaKalabilir'])
        self.assertAlmostEqual(a['itisOrani'], 1)
    def test_invalid_mass(self):
        with self.assertRaises(ValueError): gerekliHavadaKalmaItisi(-1)
    def test_invalid_thrust(self):
        with self.assertRaises(ValueError): itisAnalizi(float('nan'))
    def test_power_positive(self):
        self.assertGreater(FlightModel().estimate_power(7), 0)
    def test_takeoff(self):
        model = FlightModel()
        for _ in range(100): model.step(.02, climb=1)
        self.assertGreater(model.vehicle.altitude, 0)
    def test_no_takeoff_without_command(self):
        model = FlightModel()
        model.step(.02)
        self.assertFalse(model.vehicle.airborne)
    def test_energy_decreases(self):
        model = FlightModel()
        for _ in range(100): model.step(.02, climb=1)
        self.assertLess(model.vehicle.battery_wh, 40)
    def test_scan_requires_altitude(self):
        self.assertIn('havalan', Mission().scan(Vehicle()))
    def test_mission_completion(self):
        mission = Mission()
        for rock in mission.rocks: rock.scanned = True
        mission.update(Vehicle())
        self.assertTrue(mission.finished)
    def test_efficiency_validation(self):
        with self.assertRaises(ValueError): Config(efficiency=1.5).validate()

if __name__ == '__main__': unittest.main()
