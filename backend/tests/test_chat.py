"""
Unit tests for Farm AI Copilot Chat endpoint and service.
"""

import unittest
from fastapi.testclient import TestClient

from datetime import date, datetime
from app.main import app
from app.db.session import SessionLocal
from app.models.farmer import Farmer
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.crop_observation import CropObservation
from app.models.weather_observation import WeatherObservation
from app.models.market_observation import MarketObservation


class TestChatEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.db = SessionLocal()
        # Clean test records
        self.db.query(CropObservation).delete()
        self.db.query(WeatherObservation).delete()
        self.db.query(MarketObservation).delete()
        self.db.query(Crop).delete()
        self.db.query(Farm).delete()
        self.db.query(Farmer).delete()
        self.db.commit()

        # Seed minimal test farmer, farm, and crop
        farmer = Farmer(name="Dnyaneshwar Bhor", phone="9822012345")
        self.db.add(farmer)
        self.db.commit()
        self.db.refresh(farmer)

        farm = Farm(farmer_id=farmer.id, name="Shiva Mala Shivar", location="19.9975, 73.7898", area=3.5, area_unit="acre")
        self.db.add(farm)
        self.db.commit()
        self.db.refresh(farm)

        crop = Crop(farm_id=farm.id, crop_name="Onion", variety="Bhima Super", sowing_date=date(2026, 8, 1), area=2.0, area_unit="acre")
        self.db.add(crop)
        self.db.commit()
        self.db.refresh(crop)

        # Seed market rate
        market = MarketObservation(crop_name="Onion", market_name="Nashik", price=2450.0, observed_date=date(2026, 10, 1), unit="Rs/Quintal")
        self.db.add(market)

        # Seed weather record
        weather = WeatherObservation(farm_id=farm.id, observed_at=datetime(2026, 10, 1, 12, 0, 0), temperature=28.0, humidity=65.0, rainfall=0.0, wind_speed=5.0)
        self.db.add(weather)

        # Seed crop observation
        obs = CropObservation(crop_id=crop.id, observation_date=date(2026, 10, 1), growth_stage="vegetative", health_status="healthy", notes="Good growth")
        self.db.add(obs)
        self.db.commit()

        self.crop_id = crop.id
        self.farm_id = farm.id

    def tearDown(self):
        self.db.close()

    def test_chat_general_greeting_english(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "Hello, can you help me?",
            "crop_id": self.crop_id,
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "general")
        self.assertIn("Farm AI Copilot", data["reply"])
        self.assertEqual(data["crop_name"], "Onion")
        self.assertTrue(len(data["suggested_actions"]) > 0)

    def test_chat_harvest_intent(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "Is my onion crop ready for harvest?",
            "crop_id": self.crop_id,
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "harvest")
        self.assertIn("Harvest Assessment", data["reply"])
        self.assertIn("Not Ready", data["reply"])

    def test_chat_market_intent(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "What is the mandi price and should I sell today?",
            "crop_id": self.crop_id,
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "market")
        self.assertIn("2,450", data["reply"])
        self.assertIn("Selling Posture", data["reply"])

    def test_chat_weather_intent(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "Is there any rain risk or can I dry onions?",
            "crop_id": self.crop_id,
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "weather")
        self.assertIn("28", data["reply"])
        self.assertIn("Curing Advisory", data["reply"])

    def test_chat_marathi_language(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "कांदा काढणी कधी करावी?",
            "crop_id": self.crop_id,
            "language": "mr"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "harvest")
        self.assertIn("काढणी सल्ला", data["reply"])

    def test_chat_hindi_language(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "मंडी भाव क्या है और क्या मुझे बेचना चाहिए?",
            "crop_id": self.crop_id,
            "language": "hi"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "market")
        self.assertIn("मंडी भाव", data["reply"])

    def test_chat_navigation_intent(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "Show my crops",
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "navigate")
        self.assertEqual(data["action_type"], "navigate")
        self.assertEqual(data["action_payload"]["path"], "/crops")

    def test_chat_tutorial_intent(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "How do I check my crop health?",
            "language": "mr"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "tutorial")
        self.assertEqual(data["action_type"], "tutorial")
        self.assertTrue(len(data["tutorial_steps"]) > 0)
        self.assertIn("पायरी", data["reply"])

    def test_chat_add_crop_workflow(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "Add my new cotton crop 2 acres",
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "add_crop")
        self.assertTrue(data["confirmation_needed"])
        self.assertEqual(data["confirmation_data"]["crop_name"], "Cotton")

    def test_chat_irrigation_intent(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "When should I irrigate?",
            "crop_id": self.crop_id,
            "language": "mr"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "irrigation")
        self.assertIn("सिंचन", data["reply"])

    def test_chat_fertilizer_intent(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "Show fertilizer recommendations",
            "crop_id": self.crop_id,
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "fertilizer")
        self.assertIn("Fertilizer", data["reply"])

    def test_chat_fertilizer_price_intent(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "Show current fertilizer prices",
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "fertilizer_price")
        self.assertIn("266.50", data["reply"])

    def test_chat_crop_history_intent(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "Show my previous crop photos and history",
            "crop_id": self.crop_id,
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "crop_history")
        self.assertIn("History", data["reply"])

    def test_chat_help_mode(self):
        res = self.client.post("/api/v1/chat", json={
            "message": "What is this screen and what should I do now?",
            "current_path": "/crops",
            "language": "en"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "help")
        self.assertIn("Crops", data["reply"])


if __name__ == "__main__":
    unittest.main()
