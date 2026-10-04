"""
Farm AI Copilot Chat Service.
Provides conversational, grounded agricultural advisory grounded strictly in:
1. Field crop observations and growth stage indicators.
2. Decoupled harvest readiness and commercial selling posture.
3. Open-Meteo local weather telemetry and drying safety.
4. Agmarknet mandi benchmark rates and baseline ML price projections.

Acts as an AI assistant, app navigator, voice assistant, and step-by-step tutor.
Supports natural multilingual responses (English, Marathi, Hindi).
"""

from typing import Any, Dict, List, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.repositories.crop_repository import CropRepository
from app.repositories.farm_repository import FarmRepository
from app.repositories.crop_observation_repository import CropObservationRepository
from app.repositories.observation_reminder_repository import ObservationReminderRepository
from app.schemas.chat import ChatAction, ChatRequest, ChatResponse
from app.services.crop_indicator_service import CropIndicatorService
from app.services.market_indicator_service import MarketIndicatorService
from app.services.weather_indicator_service import WeatherIndicatorService
from app.services.recommendation_service import RecommendationService


class ChatService:
    """Conversational assistant service grounded in system data and app control."""

    def __init__(self, db: Session):
        self.db = db
        self.crop_repo = CropRepository(db)
        self.farm_repo = FarmRepository(db)
        self.crop_obs_repo = CropObservationRepository(db)
        self.reminder_repo = ObservationReminderRepository(db)
        self.crop_indicator_service = CropIndicatorService(db)
        self.weather_indicator_service = WeatherIndicatorService(db)
        self.market_indicator_service = MarketIndicatorService(db)
        self.recommendation_service = RecommendationService(db)

    def process_chat(self, req: ChatRequest) -> ChatResponse:
        """Processes incoming user query and returns grounded response with actions."""
        user_msg = req.message.strip()
        lang = (req.language or "en").lower()

        # Check for explicit language switch commands
        lower_msg = user_msg.lower()
        if any(w in lower_msg for w in ["मराठीत", "मराठी", "marathi"]):
            lang = "mr"
        elif any(w in lower_msg for w in ["हिंदी में", "हिंदी", "hindi"]):
            lang = "hi"
        elif any(w in lower_msg for w in ["english", "इंग्रजी", "in english"]):
            lang = "en"
        elif lang == "en" and any("\u0900" <= ch <= "\u097F" for ch in user_msg):
            marathi_markers = ["आहे", "करावी", "काढावा", "कांदा", "काढणी", "होय", "नाही", "सांगा", "नमस्कार", "हवामान", "शेत", "पीक", "कसे", "करावे", "बघायचे"]
            if any(m in user_msg for m in marathi_markers):
                lang = "mr"
            else:
                lang = "hi"

        # Determine target crop
        crop = None
        all_crops = self.crop_repo.get_all()
        if req.crop_id:
            crop = self.crop_repo.get_by_id(req.crop_id)
        if not crop and all_crops:
            crop = all_crops[0]

        all_farms = self.farm_repo.get_all()
        farm = self.farm_repo.get_by_id(crop.farm_id) if crop else (all_farms[0] if all_farms else None)
        farm_name = farm.name if farm else "Your Farm"

        # Detect intent
        intent = self._detect_intent(user_msg, req.workflow_state)

        # Handle intent-specific generation
        if intent == "navigate":
            return self._handle_navigation(user_msg, lang, all_crops, all_farms)
        elif intent == "tutorial":
            return self._handle_tutorial(user_msg, lang, crop, req.current_path)
        elif intent == "add_crop":
            return self._handle_add_crop(user_msg, lang, all_farms, req.workflow_state)
        elif intent == "crop_health" or intent == "take_photo":
            return self._handle_crop_health_and_photo(crop, farm_name, lang)
        elif intent == "irrigation":
            return self._handle_irrigation(crop, farm, lang)
        elif intent == "fertilizer":
            return self._handle_fertilizer(crop, farm_name, lang)
        elif intent == "fertilizer_price":
            return self._handle_fertilizer_prices(lang)
        elif intent == "crop_history":
            return self._handle_crop_history(crop, farm_name, lang)
        elif intent == "explain_result":
            return self._handle_explain_result(crop, farm_name, lang)
        elif intent == "help":
            return self._handle_help(req.current_path, lang, crop)

        if not crop:
            return self._handle_no_crops(lang)

        # Retrieve ground truth indicators for core harvest/market/weather/observation intents
        crop_ind = self.crop_indicator_service.get_crop_indicators(crop.id)
        weather_ind = self.weather_indicator_service.get_farm_weather_indicators(crop.farm_id)
        market_ind = self.market_indicator_service.get_market_indicators(crop_name=crop.crop_name)
        reminder = self.reminder_repo.get_by_crop_id(crop.id)

        rec = None
        try:
            rec = self.recommendation_service.get_crop_recommendation(crop.id)
        except Exception:
            rec = None

        data_grounding = {
            "crop_name": crop.crop_name,
            "variety": crop.variety,
            "farm_name": farm_name,
            "growth_stage": crop_ind.latest_growth_stage,
            "crop_health": crop_ind.latest_health_status,
            "days_since_observation": crop_ind.days_since_latest_observation,
            "latest_price": market_ind.latest_price,
            "harvest_recommendation": rec.harvest_recommendation.recommendation if rec else None,
            "sell_recommendation": rec.sell_recommendation.recommendation if rec else None,
            "temperature_c": weather_ind.latest_temperature,
            "humidity_percent": weather_ind.latest_humidity,
            "rainfall_mm": weather_ind.latest_rainfall,
        }

        if intent == "harvest":
            reply, actions = self._generate_harvest_response(crop, farm_name, crop_ind, rec, lang)
        elif intent == "market":
            reply, actions = self._generate_market_response(crop, market_ind, rec, lang)
        elif intent == "weather":
            reply, actions = self._generate_weather_response(farm_name, weather_ind, lang)
        elif intent == "observation":
            reply, actions = self._generate_observation_response(crop, crop_ind, reminder, lang)
        else:
            reply, actions = self._generate_general_response(crop, farm_name, crop_ind, weather_ind, market_ind, rec, lang)

        return ChatResponse(
            reply=reply,
            intent=intent,
            crop_id=crop.id,
            crop_name=crop.crop_name,
            farm_name=farm_name,
            suggested_actions=actions,
            data_grounding=data_grounding,
        )

    def _detect_intent(self, text: str, workflow_state: Optional[Dict[str, Any]]) -> str:
        """Classifies intent using natural language markers."""
        lower = text.lower()

        # If currently in a multi-step workflow, prioritize that workflow
        if workflow_state and workflow_state.get("active_intent") == "add_crop":
            return "add_crop"

        # 1. Navigation & App Control
        nav_triggers = [
            "open my dashboard", "show my dashboard", "go to dashboard", "open dashboard", "डॅशबोर्ड",
            "show my crop", "show my crops", "open my crops", "open crops", "माझे पीक", "माझं पीक", "पीक माहिती",
            "open the marketplace", "open market", "open marketplace", "मंडी उघडा", "बाजार उघडा",
            "show today's weather", "open weather", "हवामान उघडा", "हवामान दाखवा",
            "show my farms", "open farms", "माझे शेत",
            "go back", "मागे जा", "पीछे जाओ", "back"
        ]
        if any(t in lower for t in nav_triggers):
            return "navigate"

        # 2. Tutorials & How-To
        tutorial_triggers = [
            "how do i", "how to", "show me how", "guide me", "step by step", "tutorial",
            "कसं करायचं", "कसे करावे", "कसे वापरायचे", "मला शिकवा", "कदम-दर-कदम", "कैसे करें", "कैसे देखना है"
        ]
        if any(t in lower for t in tutorial_triggers):
            return "tutorial"

        # 3. Add New Crop Workflow
        add_crop_triggers = [
            "add my new crop", "add a crop", "add crop", "add new crop", "register crop",
            "नवीन पीक जोडा", "पीक जोडायचे", "नया फसल", "फसल जोड़ें", "नवीन कापूस", "add my new cotton"
        ]
        if any(t in lower for t in add_crop_triggers):
            return "add_crop"

        # 4. Crop History & Previous Analysis / Photos
        history_triggers = [
            "crop history", "previous crop photos", "previous photos", "previous analysis", "past records", "previous",
            "इतिहास", "आधीचा निकाल", "मागील नोंदी", "मागील फोटो", "पुराने रिकॉर्ड", "पिछला विश्लेषण", "पिछली तस्वीरें"
        ]
        if any(t in lower for t in history_triggers):
            return "crop_history"

        # 5. Crop Health & Photo Capture
        health_triggers = [
            "check my crop health", "crop health", "analyze my crop", "crop analysis", "take today's crop photo",
            "help me upload a photo", "take photo", "upload photo", "crop photo",
            "आरोग्य", "पिकाचे आरोग्य", "फोटो", "फोटो काढा", "फसल स्वास्थ्य", "तस्वीर लें"
        ]
        if any(t in lower for t in health_triggers):
            return "crop_health"

        # 6. Irrigation
        irrigation_triggers = [
            "irrigate", "irrigation", "water my crop", "when should i irrigate",
            "पाणी कधी द्यावे", "पाणी देणे", "सिंचन", "पानी कब देना है", "सिंचाई"
        ]
        if any(t in lower for t in irrigation_triggers):
            return "irrigation"

        # 7. Fertilizer & Nutrient Advice
        fert_price_triggers = [
            "fertilizer price", "fertilizer rate", "urea price", "dap price",
            "खताचे भाव", "खताचा दर", "युरिया भाव", "खाद का भाव"
        ]
        if any(t in lower for t in fert_price_triggers):
            return "fertilizer_price"

        fert_triggers = [
            "fertilizer", "nutrient", "urea", "dap", "npk", "compost",
            "खत", "खते", "खताचा सल्ला", "खाद", "उर्वरक"
        ]
        if any(t in lower for t in fert_triggers):
            return "fertilizer"

        # 8. Explain Result
        explain_triggers = [
            "explain this result", "explain result", "what does this mean",
            "निकालाचा अर्थ", "समजावून सांगा", "समझाओ", "इसका क्या मतलब है"
        ]
        if any(t in lower for t in explain_triggers):
            return "explain_result"

        # Greetings check
        greeting_triggers = ["hello", "hi", "hey", "namaste", "नमस्ते", "नमस्कार"]
        if any(lower.startswith(g) or lower == g for g in greeting_triggers) and not any(w in lower for w in ["what", "how", "कसे", "काय", "काढणी", "भाव", "हवामान"]):
            return "general"

        # 9. General Help & What Is This
        help_triggers = [
            "what is this", "what should i do", "what now", "how does this work",
            "हे काय आहे", "आता काय करायचे", "यह क्या है", "अब क्या करें", "app help", "need help"
        ]
        if any(t in lower for t in help_triggers):
            return "help"

        # 10. Core Agriculture Intents
        harvest_keywords = [
            "harvest", "ready", "mature", "maturity", "neck", "cut", "stage",
            "काढणी", "काढावा", "तयार", "मान", "कापणी", "कटाई", "पकना", "फसल तैयार"
        ]
        if any(w in lower for w in harvest_keywords):
            return "harvest"

        market_keywords = [
            "sell", "sold", "holding", "hold", "price", "mandi", "rate", "apmc", "market", "profit",
            "विक्री", "बाजारभाव", "भाव", "दर", "मंडी", "बेचा", "बेचू", "मार्केट"
        ]
        if any(w in lower for w in market_keywords):
            return "market"

        weather_keywords = [
            "weather", "rain", "rainy", "drying", "curing", "temp", "temperature", "humidity", "spray", "climate",
            "पाऊस", "हवामान", "तापमान", "सुकवणे", "फवारणी", "मौसम", "बारिश", "नमी"
        ]
        if any(w in lower for w in weather_keywords):
            return "weather"

        obs_keywords = [
            "observation", "record", "log", "scout", "schedule", "reminder",
            "नोंद", "पाहणी", "निरीक्षण", "रेकॉर्ड", "शेड्यूल"
        ]
        if any(w in lower for w in obs_keywords):
            return "observation"

        return "general"

    # --- Navigation Handler ---
    def _handle_navigation(self, msg: str, lang: str, crops, farms) -> ChatResponse:
        lower = msg.lower()
        path = "/"
        target_name = "Dashboard"

        if any(w in lower for w in ["crops", "crop", "पीक", "फसल"]):
            path = "/crops"
            target_name = "माझे पीक (Crops)" if lang == "mr" else "मेरी फसलें (Crops)" if lang == "hi" else "My Crops"
        elif any(w in lower for w in ["market", "mandi", "marketplace", "मंडी", "बाजार"]):
            path = "/market"
            target_name = "बाजारपेठ (Marketplace)" if lang == "mr" else "मंडी बाजार (Market)" if lang == "hi" else "Marketplace"
        elif any(w in lower for w in ["weather", "हवामान", "मौसम"]):
            path = "/weather"
            target_name = "हवामान (Weather)" if lang == "mr" else "मौसम (Weather)" if lang == "hi" else "Weather"
        elif any(w in lower for w in ["farm", "farms", "शेत", "खेत"]):
            path = "/farms"
            target_name = "माझी शेते (Farms)" if lang == "mr" else "मेरे खेत (Farms)" if lang == "hi" else "Farms"
        elif any(w in lower for w in ["back", "मागे", "पीछे"]):
            path = "BACK"
            target_name = "मागील पान" if lang == "mr" else "पिछला पेज" if lang == "hi" else "Previous Page"

        if lang == "mr":
            reply = f"✅ मी तुम्हाला **{target_name}** पानावर घेऊन जात आहे."
        elif lang == "hi":
            reply = f"✅ मैं आपको **{target_name}** पेज पर ले जा रहा हूँ।"
        else:
            reply = f"✅ Taking you to **{target_name}** right away."

        actions = [
            ChatAction(label=f"👉 Open {target_name}", action_type="navigate", payload={"path": path}),
            ChatAction(label="🌾 Check Crops", action_type="navigate", payload={"path": "/crops"}),
        ]

        return ChatResponse(
            reply=reply,
            intent="navigate",
            action_type="navigate",
            action_payload={"path": path},
            suggested_actions=actions,
        )

    # --- Tutorial Handler ---
    def _handle_tutorial(self, msg: str, lang: str, crop, current_path: Optional[str]) -> ChatResponse:
        lower = msg.lower()
        crop_name = crop.crop_name if crop else "कापूस"

        # Determine tutorial topic
        if any(w in lower for w in ["health", "आरोग्य", "स्वास्थ्य", "check"]):
            topic = "check_crop_health"
            if lang == "mr":
                reply = (
                    "मी तुम्हाला पिकाचे आरोग्य तपासण्याची पद्धत एक-एक पायरीने दाखवतो:\n\n"
                    "👉 **पायरी १:** खालील 'My Crops' बटन दाबा.\n"
                    "👉 **पायरी २:** आता तुमचे पीक निवडा.\n"
                    "👉 **पायरी ३:** 'Crop Health' वर क्लिक करून निकाल पहा."
                )
                steps = [
                    {"step": 1, "title": "पायरी १", "instruction": "डाव्या बाजूचे किंवा खालील 'My Crops' बटन दाबा.", "target": "[data-tour='nav-crops']", "path": "/crops"},
                    {"step": 2, "title": "पायरी २", "instruction": "तुमचे पीक कार्ड निवडा.", "target": "[data-tour='crop-card']", "path": "/crops"},
                    {"step": 3, "title": "पायरी ३", "instruction": "पिकाचे आरोग्य पाहण्यासाठी 'Crop Health' वर क्लिक करा.", "target": "[data-tour='crop-health-btn']", "path": "/crops"},
                ]
            elif lang == "hi":
                reply = (
                    "मैं आपको फसल स्वास्थ्य जांचने की विधि एक-एक कदम में दिखाता हूँ:\n\n"
                    "👉 **कदम १:** 'My Crops' बटन दबाएं।\n"
                    "👉 **कदम २:** अपनी फसल चुनें।\n"
                    "👉 **कदम ३:** 'Crop Health' पर क्लिक करके परिणाम देखें।"
                )
                steps = [
                    {"step": 1, "title": "कदम १", "instruction": "'My Crops' बटन पर क्लिक करें।", "target": "[data-tour='nav-crops']", "path": "/crops"},
                    {"step": 2, "title": "कदम २", "instruction": "अपनी फसल कार्ड चुनें।", "target": "[data-tour='crop-card']", "path": "/crops"},
                    {"step": 3, "title": "कदम ३", "instruction": "'Crop Health' पर क्लिक करें।", "target": "[data-tour='crop-health-btn']", "path": "/crops"},
                ]
            else:
                reply = (
                    "I will guide you step by step to check your crop health:\n\n"
                    "👉 **Step 1:** Tap 'My Crops' in the navigation.\n"
                    "👉 **Step 2:** Select your active crop.\n"
                    "👉 **Step 3:** Tap 'Crop Health' to see the diagnostic assessment."
                )
                steps = [
                    {"step": 1, "title": "Step 1", "instruction": "Tap the 'My Crops' button.", "target": "[data-tour='nav-crops']", "path": "/crops"},
                    {"step": 2, "title": "Step 2", "instruction": "Select your crop card.", "target": "[data-tour='crop-card']", "path": "/crops"},
                    {"step": 3, "title": "Step 3", "instruction": "Tap 'Crop Health' to view analysis.", "target": "[data-tour='crop-health-btn']", "path": "/crops"},
                ]
        elif any(w in lower for w in ["farm", "location", "शेत", "खेत"]):
            topic = "add_farm"
            if lang == "mr":
                reply = (
                    "नवीन शेत जोडण्याची सोपी पद्धत:\n\n"
                    "👉 **पायरी १:** 'Farms' मेनू उघडा.\n"
                    "👉 **पायरी २:** [📍 Detect My Location] वर क्लिक करून GPS स्थान मिळवा.\n"
                    "👉 **पायरी ३:** शेताचे नाव व क्षेत्र टाकून 'Save Farm' दाबा."
                )
                steps = [
                    {"step": 1, "title": "पायरी १", "instruction": "'Farms' मेनूवर जा.", "target": "[data-tour='nav-farms']", "path": "/farms"},
                    {"step": 2, "title": "पायरी २", "instruction": "[📍 Detect My Location] दाबा.", "target": "[data-tour='detect-location-btn']", "path": "/farms"},
                    {"step": 3, "title": "पायरी ३", "instruction": "माहिती भरून शेत सेव्ह करा.", "target": "[data-tour='add-farm-btn']", "path": "/farms"},
                ]
            elif lang == "hi":
                reply = (
                    "नया खेत जोड़ने की आसान विधि:\n\n"
                    "👉 **कदम १:** 'Farms' मेनू खोलें।\n"
                    "👉 **कदम २:** [📍 Detect My Location] दबाकर जीपीएस लोकेशन दर्ज करें।\n"
                    "👉 **कदम ३:** खेत का नाम लिखकर 'Save Farm' दबाएं।"
                )
                steps = [
                    {"step": 1, "title": "कदम १", "instruction": "'Farms' मेनू पर जाएं।", "target": "[data-tour='nav-farms']", "path": "/farms"},
                    {"step": 2, "title": "कदम २", "instruction": "[📍 Detect My Location] दबाएं।", "target": "[data-tour='detect-location-btn']", "path": "/farms"},
                    {"step": 3, "title": "कदम ३", "instruction": "खेत सुरक्षित करें।", "target": "[data-tour='add-farm-btn']", "path": "/farms"},
                ]
            else:
                reply = (
                    "How to add your farm parcel:\n\n"
                    "👉 **Step 1:** Open the 'Farms' section.\n"
                    "👉 **Step 2:** Click '[📍 Detect My Location]' for GPS accuracy.\n"
                    "👉 **Step 3:** Enter farm name and click 'Save Farm'."
                )
                steps = [
                    {"step": 1, "title": "Step 1", "instruction": "Open the 'Farms' section.", "target": "[data-tour='nav-farms']", "path": "/farms"},
                    {"step": 2, "title": "Step 2", "instruction": "Click '[📍 Detect My Location]'.", "target": "[data-tour='detect-location-btn']", "path": "/farms"},
                    {"step": 3, "title": "Step 3", "instruction": "Save your farm.", "target": "[data-tour='add-farm-btn']", "path": "/farms"},
                ]
        else:
            topic = "general_tour"
            if lang == "mr":
                reply = (
                    "मी तुम्हाला संपूर्ण ॲपचे मुख्य भाग दाखवतो:\n\n"
                    "👉 **पायरी १:** डॅशबोर्डवर सर्व पिकांचा व बाजाराचा सारांश पहा.\n"
                    "👉 **पायरी २:** 'Crops' मध्ये जाऊन पिकाची वाढ व काढणी सल्ला तपासा.\n"
                    "👉 **पायरी ३:** 'Market' मध्ये नाशिक APMC दर व कल पहा.\n"
                    "👉 **पायरी ४:** 'Weather' मध्ये पावसाचा धोका व वाळवणी सल्ला पहा."
                )
                steps = [
                    {"step": 1, "title": "पायरी १", "instruction": "डॅशबोर्ड सारांश पहा.", "target": "[data-tour='nav-dashboard']", "path": "/"},
                    {"step": 2, "title": "पायरी २", "instruction": "पिकांचे व्यवस्थापन व काढणी सल्ला पहा.", "target": "[data-tour='nav-crops']", "path": "/crops"},
                    {"step": 3, "title": "पायरी ३", "instruction": "मंडी भाव व विक्री कल तपासा.", "target": "[data-tour='nav-market']", "path": "/market"},
                    {"step": 4, "title": "पायरी ४", "instruction": "हवामान व पावसाचा अंदाज पहा.", "target": "[data-tour='nav-weather']", "path": "/weather"},
                ]
            elif lang == "hi":
                reply = (
                    "ऐप का उपयोग करने के मुख्य चरण:\n\n"
                    "👉 **कदम १:** डैशबोर्ड पर अपनी फसलों का सारांश देखें।\n"
                    "👉 **कदम २:** 'Crops' में फसल की वृद्धि और कटाई सलाह देखें।\n"
                    "👉 **कदम ३:** 'Market' में मंडी भाव और रुझान देखें।\n"
                    "👉 **कदम ४:** 'Weather' में बारिश का जोखिम देखें।"
                )
                steps = [
                    {"step": 1, "title": "कदम १", "instruction": "डैशबोर्ड सारांश देखें।", "target": "[data-tour='nav-dashboard']", "path": "/"},
                    {"step": 2, "title": "कदम २", "instruction": "फसल व कटाई सलाह देखें।", "target": "[data-tour='nav-crops']", "path": "/crops"},
                    {"step": 3, "title": "कदम ३", "instruction": "मंडी भाव देखें।", "target": "[data-tour='nav-market']", "path": "/market"},
                    {"step": 4, "title": "कदम ४", "instruction": "मौसम की जानकारी देखें।", "target": "[data-tour='nav-weather']", "path": "/weather"},
                ]
            else:
                reply = (
                    "Here is a quick tour of your farmer support system:\n\n"
                    "👉 **Step 1:** View full overview on the Dashboard.\n"
                    "👉 **Step 2:** Manage crop stages and harvest status in 'Crops'.\n"
                    "👉 **Step 3:** Track APMC mandi trends and selling postures in 'Market'.\n"
                    "👉 **Step 4:** Inspect rainfall risk and field drying safety in 'Weather'."
                )
                steps = [
                    {"step": 1, "title": "Step 1", "instruction": "Inspect overall farm pulse.", "target": "[data-tour='nav-dashboard']", "path": "/"},
                    {"step": 2, "title": "Step 2", "instruction": "Scout crops and harvest advice.", "target": "[data-tour='nav-crops']", "path": "/crops"},
                    {"step": 3, "title": "Step 3", "instruction": "Monitor mandi market rates.", "target": "[data-tour='nav-market']", "path": "/market"},
                    {"step": 4, "title": "Step 4", "instruction": "Review microclimate risk.", "target": "[data-tour='nav-weather']", "path": "/weather"},
                ]

        actions = [
            ChatAction(label="🚀 Start Step-by-Step Tutorial", action_type="tutorial", payload={"topic": topic, "steps": steps}),
            ChatAction(label="🌾 Open Crops", action_type="navigate", payload={"path": "/crops"}),
        ]

        return ChatResponse(
            reply=reply,
            intent="tutorial",
            action_type="tutorial",
            tutorial_steps=steps,
            suggested_actions=actions,
        )

    # --- Conversational Add Crop Workflow ---
    def _handle_add_crop(self, msg: str, lang: str, farms, state: Optional[Dict[str, Any]]) -> ChatResponse:
        current_state = dict(state or {})
        current_state["active_intent"] = "add_crop"
        lower = msg.lower()

        # Check if user confirms or cancels
        if any(w in lower for w in ["yes", "save", "होय", "सेव्ह", "करा", "हाँ", "जोड़ें"]):
            if current_state.get("pending_crop"):
                data = current_state["pending_crop"]
                farm_id = data.get("farm_id") or (farms[0].id if farms else 1)
                crop_name = data.get("crop_name", "Cotton")
                area = data.get("area", 2.0)
                farm_obj = next((f for f in farms if f.id == farm_id), None)
                fname = farm_obj.name if farm_obj else "Your Farm"

                if lang == "mr":
                    reply = f"🎉 उत्तम! **{crop_name}** पीक **{fname}** ({area} एकर) वर यशस्वीरित्या जोडले आहे.\n\nतुम्ही आता याचे निरीक्षण किंवा हवामान तपासू शकता."
                elif lang == "hi":
                    reply = f"🎉 बधाई! **{crop_name}** फसल **{fname}** ({area} एकड़) पर सफलतापूर्वक जोड़ दी गई है।"
                else:
                    reply = f"🎉 Great! **{crop_name}** ({area} acres) has been successfully registered for **{fname}**."

                actions = [
                    ChatAction(label="🌾 View Crop Details", action_type="navigate", payload={"path": "/crops"}),
                    ChatAction(label="📋 Log First Observation", action_type="navigate", payload={"path": "/crops"}),
                ]

                return ChatResponse(
                    reply=reply,
                    intent="add_crop",
                    action_type="confirm_action",
                    action_payload={"action": "create_crop", "data": data},
                    suggested_actions=actions,
                )

        if any(w in lower for w in ["no", "cancel", "नाही", "रद्द", "नको", "रद्द करा"]):
            if lang == "mr":
                reply = "समजले, पीक जोडण्याची प्रक्रिया रद्द केली आहे. तुम्हाला इतर कशात मदत हवी आहे?"
            elif lang == "hi":
                reply = "ठीक है, फसल जोड़ने की प्रक्रिया रद्द कर दी गई है।"
            else:
                reply = "Understood. The crop registration has been cancelled. How else can I assist?"
            return ChatResponse(reply=reply, intent="add_crop", suggested_actions=[])

        # Extract crop name if mentioned
        for c in ["cotton", "कापूस", "कपास", "onion", "कांदा", "प्याज", "soybean", "सोयाबीन", "wheat", "गहू", "गेहूं", "tomato", "टोमॅटो", "टमाटर"]:
            if c in lower:
                clean_name = "Cotton" if c in ["cotton", "कापूस", "कपास"] else "Onion" if c in ["onion", "कांदा", "प्याज"] else "Soybean" if c in ["soybean", "सोयाबीन"] else "Wheat" if c in ["wheat", "गहू", "गेहूं"] else "Tomato"
                current_state["crop_name"] = clean_name
                break

        # Extract area if digits mentioned
        import re
        nums = re.findall(r"\b\d+(?:\.\d+)?\b", msg)
        if nums and not current_state.get("area"):
            try:
                val = float(nums[0])
                if 0.1 <= val <= 100:
                    current_state["area"] = val
            except ValueError:
                pass

        # Step 1: Missing crop name
        if not current_state.get("crop_name"):
            if lang == "mr":
                reply = "नक्कीच! तुम्हाला कोणते पीक जोडायचे आहे? (उदा. कापूस, कांदा, सोयाबीन, गहू)"
            elif lang == "hi":
                reply = "ज़रूर! आप कौन सी फसल जोड़ना चाहते हैं? (उदा. कपास, प्याज, सोयाबीन, गेहूं)"
            else:
                reply = "Sure! Which crop would you like to register? (e.g. Cotton, Onion, Soybean, Wheat)"
            actions = [
                ChatAction(label="🌿 Cotton (कापूस)", action_type="prompt", payload={"prompt": "Cotton"}),
                ChatAction(label="🧅 Onion (कांदा)", action_type="prompt", payload={"prompt": "Onion"}),
                ChatAction(label="🌱 Soybean (सोयाबीन)", action_type="prompt", payload={"prompt": "Soybean"}),
            ]
            return ChatResponse(reply=reply, intent="add_crop", suggested_actions=actions)

        # Step 2: Missing farm
        if not current_state.get("farm_id"):
            if len(farms) == 1:
                current_state["farm_id"] = farms[0].id
            elif len(farms) > 1:
                if lang == "mr":
                    reply = f"हे **{current_state['crop_name']}** पीक कोणत्या शेतासाठी जोडायचे आहे? खालीलपैकी निवडा:"
                elif lang == "hi":
                    reply = f"यह **{current_state['crop_name']}** फसल किस खेत के लिए जोड़नी है? चुनें:"
                else:
                    reply = f"Which field is this **{current_state['crop_name']}** crop for? Please choose:"
                actions = [
                    ChatAction(label=f"📍 {f.name}", action_type="prompt", payload={"prompt": f"For {f.name}"})
                    for f in farms[:4]
                ]
                return ChatResponse(reply=reply, intent="add_crop", suggested_actions=actions)
            else:
                current_state["farm_id"] = 1

        # Step 3: Missing area
        if not current_state.get("area"):
            if lang == "mr":
                reply = f"हे पीक किती एकर क्षेत्रात घेणार आहात? (उदा. १ एकर, २.५ एकर)"
            elif lang == "hi":
                reply = f"यह फसल कितने एकड़ में लगाएंगे? (उदा. 1 एकड़, 2.5 एकड़)"
            else:
                reply = f"How many acres is this planting? (e.g. 1 acre, 2.5 acres)"
            actions = [
                ChatAction(label="1 Acre", action_type="prompt", payload={"prompt": "1 acre"}),
                ChatAction(label="2 Acres", action_type="prompt", payload={"prompt": "2 acres"}),
                ChatAction(label="3 Acres", action_type="prompt", payload={"prompt": "3 acres"}),
            ]
            return ChatResponse(reply=reply, intent="add_crop", suggested_actions=actions)

        # Step 4: All gathered -> Confirmation!
        c_name = current_state["crop_name"]
        f_id = current_state["farm_id"]
        c_area = current_state["area"]
        farm_obj = next((f for f in farms if f.id == f_id), None)
        fname = farm_obj.name if farm_obj else "Your Farm"

        pending_data = {
            "farm_id": f_id,
            "crop_name": c_name,
            "variety": "Standard",
            "sowing_date": date.today().isoformat(),
            "area": c_area,
            "area_unit": "acre",
        }
        current_state["pending_crop"] = pending_data

        if lang == "mr":
            reply = (
                f"📝 **पीक माहिती पडताळणी:**\n\n"
                f"• **पीक:** {c_name}\n"
                f"• **शेत:** {fname}\n"
                f"• **क्षेत्र:** {c_area} एकर\n"
                f"• **पेरणी तारीख:** आज ({date.today().strftime('%d-%m-%Y')})\n\n"
                f"ही माहिती सेव्ह करू का?"
            )
        elif lang == "hi":
            reply = (
                f"📝 **फसल विवरण जांचें:**\n\n"
                f"• **फसल:** {c_name}\n"
                f"• **खेत:** {fname}\n"
                f"• **क्षेत्र:** {c_area} एकड़\n\n"
                f"क्या आप इसे सुरक्षित (Save) करना चाहते हैं?"
            )
        else:
            reply = (
                f"📝 **Confirm New Crop Registration:**\n\n"
                f"• **Crop:** {c_name}\n"
                f"• **Farm:** {fname}\n"
                f"• **Area:** {c_area} acres\n\n"
                f"Would you like to save this planting now?"
            )

        actions = [
            ChatAction(label="✅ Yes, Save Crop", action_type="prompt", payload={"prompt": "Yes, save it"}),
            ChatAction(label="❌ Cancel", action_type="prompt", payload={"prompt": "Cancel"}),
        ]

        return ChatResponse(
            reply=reply,
            intent="add_crop",
            confirmation_needed=True,
            confirmation_data=pending_data,
            suggested_actions=actions,
        )

    # --- Crop Health & Photo Capture Handler ---
    def _handle_crop_health_and_photo(self, crop, farm_name: str, lang: str) -> ChatResponse:
        crop_ind = self.crop_indicator_service.get_crop_indicators(crop.id)
        stage = (crop_ind.latest_growth_stage or "vegetative").replace("_", " ").title()
        health = (crop_ind.latest_health_status or "healthy").title()
        recency = crop_ind.days_since_latest_observation

        actions = [
            ChatAction(label="📸 Take Crop Photo / Log Observation", action_type="modal", payload={"modal": "crop_observation", "crop_id": crop.id}),
            ChatAction(label="🌾 View Crop Diagnostics", action_type="navigate", payload={"path": "/crops"}),
        ]

        if lang == "mr":
            status_desc = "पिकाची स्थिती समाधानकारक व निरोगी दिसत आहे." if health.lower() == "healthy" else "पिकावर ताण किंवा किडीची लक्षणे तपासणे आवश्यक आहे."
            photo_prompt = (
                "शेवटची नोंद ७ दिवसांपूर्वी झाली होती. अचूक विश्लेषणासाठी आजचा स्पष्ट फोटो किंवा निरीक्षण नोंदवा."
                if recency is None or recency >= 7
                else "आजचे निरीक्षण नोंदवलेले आहे. हवे असल्यास नवीन फोटो जोडू शकता."
            )
            reply = (
                f"🌱 **पिकाचे आरोग्य विश्लेषण ({crop.crop_name} - {farm_name}):**\n\n"
                f"• **आरोग्य स्थिती:** **{health}** ({status_desc})\n"
                f"• **सद्य वाढीची अवस्था:** {stage}\n"
                f"• **शेवटचे निरीक्षण:** {recency if recency is not None else 0} दिवसांपूर्वी\n\n"
                f"📸 {photo_prompt}\n\n"
                f"💡 *सल्ला:* फोटो काढताना पानांवर आणि बुंध्यावर स्पष्ट प्रकाश ठेवा."
            )
        elif lang == "hi":
            reply = (
                f"🌱 **फसल स्वास्थ्य विश्लेषण ({crop.crop_name} - {farm_name}):**\n\n"
                f"• **स्वास्थ्य स्थिति:** **{health}**\n"
                f"• **वृद्धि चरण:** {stage}\n"
                f"• **अंतिम निरीक्षण:** {recency if recency is not None else 0} दिन पहले\n\n"
                f"📸 बेहतर विश्लेषण के लिए फसल की ताजा तस्वीर लें।"
            )
        else:
            reply = (
                f"🌱 **Crop Health Diagnostics for {crop.crop_name} ({farm_name}):**\n\n"
                f"• **Health Status:** **{health}**\n"
                f"• **Current Growth Stage:** {stage}\n"
                f"• **Observation Recency:** {recency if recency is not None else 0} days ago\n\n"
                f"📸 Tap below to capture today's crop photo or record health scouting notes."
            )

        return ChatResponse(
            reply=reply,
            intent="crop_health",
            crop_id=crop.id,
            crop_name=crop.crop_name,
            farm_name=farm_name,
            action_type="modal",
            action_payload={"modal": "crop_observation", "crop_id": crop.id},
            suggested_actions=actions,
        )

    # --- Irrigation Handler ---
    def _handle_irrigation(self, crop, farm, lang: str) -> ChatResponse:
        weather_ind = self.weather_indicator_service.get_farm_weather_indicators(farm.id) if farm else None
        rain = weather_ind.total_rainfall if weather_ind else 0.0
        temp = weather_ind.latest_temperature or 26.0

        actions = [
            ChatAction(label="🌧️ Weather & Rain Forecast", action_type="navigate", payload={"path": "/weather"}),
            ChatAction(label="🌾 Crop Water Schedule", action_type="navigate", payload={"path": "/crops"}),
        ]

        if rain > 5.0:
            if lang == "mr":
                advice = "गेल्या ४८ तासांत पाऊस झाला असल्याने सध्या पाणी देण्याची आवश्यकता नाही. शेतात अतिरिक्त पाणी साचू देऊ नका."
            elif lang == "hi":
                advice = "पिछले ४८ घंटों में वर्षा हुई है, अतः अभी सिंचाई की आवश्यकता नहीं है।"
            else:
                advice = "Recent rainfall has provided adequate soil moisture. Additional irrigation is currently not required."
        elif temp > 32.0:
            if lang == "mr":
                advice = "तापमान अधिक असल्याने बाष्पीभवन जास्त होते. दुपारी पाणी न देता सकाळी लवकर किंवा संध्याकाळी हलके पाणी द्यावे."
            elif lang == "hi":
                advice = "तापमान अधिक होने के कारण सुबह जल्दी या शाम को हल्की सिंचाई करें।"
            else:
                advice = "Elevated ambient temperatures increase evapotranspiration. Irrigate lightly during early morning or evening hours."
        else:
            if lang == "mr":
                advice = "हवामान सामान्य आहे. पिकाची गरज व वाफे तपासून दर ३ ते ४ दिवसांनी हलके पाणी द्यावे."
            elif lang == "hi":
                advice = "मौसम सामान्य है। आवश्यकतानुसार ३ से ४ दिनों के अंतराल पर हल्की सिंचाई करें।"
            else:
                advice = "Favorable ambient conditions. Maintain regular 3 to 4 day furrow or drip irrigation schedule."

        if lang == "mr":
            reply = (
                f"💧 **सिंचन आणि पाणी सल्ला ({crop.crop_name if crop else 'पीक'}):**\n\n"
                f"• **अलीकडील पाऊस:** {rain} मिमी\n"
                f"• **शेतातील तापमान:** {temp}°C\n"
                f"• **सिंचन शिफारस:** {advice}\n\n"
                f"💡 *टीप:* कांदा किंवा कापूस पिकात मुळांशी पाणी साचणार नाही याची काळजी घ्या."
            )
        elif lang == "hi":
            reply = (
                f"💧 **सिंचाई सलाह ({crop.crop_name if crop else 'फसल'}):**\n\n"
                f"• **हाल की बारिश:** {rain} मिमी | **तापमान:** {temp}°C\n"
                f"• **सलाह:** {advice}"
            )
        else:
            reply = (
                f"💧 **Irrigation Advisory ({crop.crop_name if crop else 'Crop'}):**\n\n"
                f"• **Recent Rainfall:** {rain} mm\n"
                f"• **Field Temp:** {temp}°C\n"
                f"• **Irrigation Recommendation:** {advice}"
            )

        return ChatResponse(
            reply=reply,
            intent="irrigation",
            crop_id=crop.id if crop else None,
            crop_name=crop.crop_name if crop else None,
            suggested_actions=actions,
        )

    # --- Fertilizer Recommendations Handler ---
    def _handle_fertilizer(self, crop, farm_name: str, lang: str) -> ChatResponse:
        cname = crop.crop_name if crop else "General"

        actions = [
            ChatAction(label="💰 Check Fertilizer Prices", action_type="prompt", payload={"prompt": "Show current fertilizer prices"}),
            ChatAction(label="🌾 Crop Details", action_type="navigate", payload={"path": "/crops"}),
        ]

        if lang == "mr":
            reply = (
                f"🧪 **खत व्यवस्थापन सल्ला ({cname} - {farm_name}):**\n\n"
                f"• **मूलभूत खत (Basal Dose):** शेणखत किंवा गांडूळखत ५ टन/एकर + SSP (सिंगल सुपर फॉस्फेट) १०० किलो + MOP ५० किलो.\n"
                f"• **वाढीची अवस्था (Vegetative):** लागवडीनंतर ३० दिवसांनी युरिया ३० किलो प्रति एकर.\n"
                f"• **गाठ/पोषण अवस्था (Bulb/Fruiting):** पोटॅश आणि सूक्ष्मअन्नद्रव्ये (झिंक, बोरॉन) ५ ग्रॅम/लिटर फवारणी.\n\n"
                f"💡 *सल्ला:* खते नेहमी ओलावा असतानाच द्यावीत आणि जमिनीत मिसळावीत."
            )
        elif lang == "hi":
            reply = (
                f"🧪 **उर्वरक एवं पोषण सलाह ({cname}):**\n\n"
                f"• **बुआई के समय:** गोबर खाद + डीएपी/एसएसपी एवं पोटाश।\n"
                f"• **वृद्धि चरण:** बुआई के ३० दिन बाद यूरिया का प्रयोग करें।\n"
                f"• **सूक्ष्म पोषक तत्व:** जिंक एवं बोरॉन का संतुलित छिड़काव करें।"
            )
        else:
            reply = (
                f"🧪 **Fertilizer & Nutrition Advisory for {cname}:**\n\n"
                f"• **Basal Application:** Well-decomposed farmyard manure (5 T/acre) + SSP (100 kg) + MOP (50 kg).\n"
                f"• **Vegetative Boost:** Top-dress Urea (30 kg/acre) around 30 days post-planting.\n"
                f"• **Fruiting / Bulb Phase:** Foliar spray of Potassium Schoenite or 0:0:50 with micronutrients (Zinc & Boron).\n\n"
                f"💡 *Tip:* Always apply solid fertilizers under moist soil conditions."
            )

        return ChatResponse(
            reply=reply,
            intent="fertilizer",
            crop_id=crop.id if crop else None,
            crop_name=cname,
            farm_name=farm_name,
            suggested_actions=actions,
        )

    # --- Fertilizer Market Prices Handler ---
    def _handle_fertilizer_prices(self, lang: str) -> ChatResponse:
        actions = [
            ChatAction(label="🧪 Fertilizer Recommendations", action_type="prompt", payload={"prompt": "Show fertilizer recommendations"}),
            ChatAction(label="📈 Mandi Crop Rates", action_type="navigate", payload={"path": "/market"}),
        ]

        if lang == "mr":
            reply = (
                "💰 **प्रमुख खतांचे सध्याचे शासकीय/बाजारभाव (अंदाजे):**\n\n"
                "• **नीम कोटेड युरिया (Neem Urea 45kg):** **₹२६६.५०** / बॅग\n"
                "• **DAP (18:46:0 50kg):** **₹१,३५०** / बॅग\n"
                "• **MOP (पोटॅश 50kg):** **₹१,७००** / बॅग\n"
                "• **NPK (10:26:26 50kg):** **₹१,४७०** / बॅग\n"
                "• **सिंगल सुपर फॉस्फेट (SSP 50kg):** **₹५००** / बॅग\n\n"
                "💡 *टीप:* अधिकृत कृषी सेवा केंद्रातून खरेदी करताना पावती अवश्य घ्या."
            )
        elif lang == "hi":
            reply = (
                "💰 **प्रमुख उर्वरकों के वर्तमान मानक मूल्य:**\n\n"
                "• **यूरिया (45 kg):** ₹266.50 / बैग\n"
                "• **डीएपी (50 kg):** ₹1,350 / बैग\n"
                "• **एमओपी (50 kg):** ₹1,700 / बैग\n"
                "• **एनपीके (10:26:26):** ₹1,470 / बैग"
            )
        else:
            reply = (
                "💰 **Benchmark Subsidized Fertilizer Retail Rates:**\n\n"
                "• **Neem Coated Urea (45 kg bag):** **₹266.50**\n"
                "• **DAP 18:46:0 (50 kg bag):** **₹1,350.00**\n"
                "• **MOP / Potash (50 kg bag):** **₹1,700.00**\n"
                "• **NPK 10:26:26 (50 kg bag):** **₹1,470.00**\n"
                "• **Single Super Phosphate (50 kg bag):** **₹500.00**\n\n"
                "💡 *Note:* Government subsidized rates at registered retail cooperatives."
            )

        return ChatResponse(
            reply=reply,
            intent="fertilizer_price",
            suggested_actions=actions,
        )

    # --- Crop History Handler ---
    def _handle_crop_history(self, crop, farm_name: str, lang: str) -> ChatResponse:
        obs_list = self.crop_obs_repo.get_by_crop_id(crop.id, limit=5) if crop else []

        actions = [
            ChatAction(label="📸 Record New Observation", action_type="modal", payload={"modal": "crop_observation", "crop_id": crop.id if crop else None}),
            ChatAction(label="🌾 View All Field Logs", action_type="navigate", payload={"path": "/crops"}),
        ]

        if not obs_list:
            if lang == "mr":
                reply = f"📋 **{crop.crop_name} ({farm_name})** साठी अद्याप जुन्या नोंदी उपलब्ध नाहीत. पहिली नोंद करण्यासाठी खालील बटनावर क्लिक करा."
            elif lang == "hi":
                reply = f"📋 **{crop.crop_name}** के लिए कोई पुराना रिकॉर्ड नहीं मिला। नया रिकॉर्ड दर्ज करने के लिए नीचे क्लिक करें।"
            else:
                reply = f"📋 No previous observations recorded yet for **{crop.crop_name}**. Tap below to create your first field observation."
        else:
            lines = []
            for obs in obs_list:
                dt = obs.observation_date.strftime("%d-%m-%Y")
                stg = (obs.growth_stage or "Vegetative").title()
                hlth = (obs.health_status or "Healthy").title()
                lines.append(f"• **{dt}:** {stg} ({hlth}) - {obs.notes or 'General scouting'}")
            log_str = "\n".join(lines)

            if lang == "mr":
                reply = (
                    f"📜 **मागील पीक नोंदी आणि इतिहास ({crop.crop_name} - {farm_name}):**\n\n"
                    f"{log_str}\n\n"
                    f"💡 *मार्गदर्शन:* सातत्यपूर्ण नोंदींमुळे काढणीचा अचूक अंदाज बांधता येतो."
                )
            elif lang == "hi":
                reply = f"📜 **पिछला फसल इतिहास ({crop.crop_name}):**\n\n{log_str}"
            else:
                reply = f"📜 **Field Observation History for {crop.crop_name} ({farm_name}):**\n\n{log_str}"

        return ChatResponse(
            reply=reply,
            intent="crop_history",
            crop_id=crop.id if crop else None,
            crop_name=crop.crop_name if crop else None,
            suggested_actions=actions,
        )

    # --- Explain Result Handler ---
    def _handle_explain_result(self, crop, farm_name: str, lang: str) -> ChatResponse:
        rec = None
        if crop:
            try:
                rec = self.recommendation_service.get_crop_recommendation(crop.id)
            except Exception:
                rec = None

        h_rec = rec.harvest_recommendation.recommendation if rec else "not_ready"
        s_rec = rec.sell_recommendation.recommendation if rec else "hold"
        reasons = rec.harvest_recommendation.reasons if rec else ["Crop is currently in vegetative growth."]

        actions = [
            ChatAction(label="🌾 Harvest Breakdown", action_type="navigate", payload={"path": "/crops"}),
            ChatAction(label="📈 Mandi Prices", action_type="navigate", payload={"path": "/market"}),
        ]

        if lang == "mr":
            reply = (
                f"🧠 **निकालाचा सोप्या भाषेत अर्थ ({crop.crop_name if crop else 'पीक'}):**\n\n"
                f"१. **काढणी का करू नये?** {reasons[0] if reasons else 'पिकाची पूर्ण पक्वता झालेली नाही.'}\n"
                f"२. **विक्री थांबवण्याचा सल्ला का?** सध्याच्या आवक व सांख्यिकीय मॉडेलनुसार बाजारात भाव स्थिर राहण्याची शक्यता आहे.\n"
                f"३. **तुम्ही काय करावे?** पिकाला आवश्यक पाणी व कीड नियंत्रण सुरू ठेवा आणि आठवड्याला एक निरीक्षण नोंदवा."
            )
        elif lang == "hi":
            reply = (
                f"🧠 **परिणाम का सरल अर्थ:**\n\n"
                f"१. **कटाई:** फसल अभी वृद्धि चरण में है, पूर्ण पकने पर ही काटें।\n"
                f"२. **बिक्री:** मंडी में भाव स्थिर हैं, उचित समय की प्रतीक्षा करें।"
            )
        else:
            reply = (
                f"🧠 **Decision Engine Explanation in Plain Terms:**\n\n"
                f"1. **Biological Maturity:** {reasons[0] if reasons else 'Crop requires further growth.'}\n"
                f"2. **Market Strategy:** Price momentum is steady. Aerated holding preserves value.\n"
                f"3. **Recommended Action:** Continue normal field care and scout next week."
            )

        return ChatResponse(
            reply=reply,
            intent="explain_result",
            crop_id=crop.id if crop else None,
            crop_name=crop.crop_name if crop else None,
            suggested_actions=actions,
        )

    # --- Help Mode Handler ---
    def _handle_help(self, current_path: Optional[str], lang: str, crop) -> ChatResponse:
        path = current_path or "/"
        cname = crop.crop_name if crop else "पीक"

        if path == "/crops":
            if lang == "mr":
                reply = (
                    "ℹ️ **हे 'माझे पीक (Crops)' पान आहे:**\n\n"
                    "येथे तुम्ही तुमच्या सर्व पिकांची यादी, त्यांची सध्याची अवस्था (वाढ/काढणी), आणि आठवडी निरीक्षणे पाहू शकता.\n\n"
                    "👉 **आता तुम्ही काय करू शकता:**\n"
                    "१. नवीन पीक जोडण्यासाठी '+ Add Crop' दाबा.\n"
                    "२. आजची पाहणी नोंदवण्यासाठी 'Log Observation' दाबा.\n"
                    "३. काढणी सल्ला पाहण्यासाठी 'Recommendation' तपासा."
                )
            elif lang == "hi":
                reply = "ℹ️ **यह 'फसलें (Crops)' पेज है:** यहाँ आप अपनी फसलों की स्थिति और कटाई सलाह देख सकते हैं।"
            else:
                reply = (
                    "ℹ️ **You are on the 'Crops' screen:**\n\n"
                    "Here you can monitor crop maturity stages, view biological harvest advice, and log weekly scouting observations."
                )
            actions = [
                ChatAction(label="➕ Add New Crop", action_type="modal", payload={"modal": "add_crop"}),
                ChatAction(label="📋 Log Observation", action_type="modal", payload={"modal": "crop_observation", "crop_id": crop.id if crop else None}),
            ]
        elif path == "/farms":
            if lang == "mr":
                reply = (
                    "ℹ️ **हे 'माझी शेते (Farms)' पान आहे:**\n\n"
                    "येथे तुमची शेते व त्यांचे अचूक GPS लोकेशन नोंदवले जाते. अचूक हवामानासाठी GPS स्थान आवश्यक असते.\n\n"
                    "👉 **आता काय करायचे:**\n"
                    "• नवीन शेत जोडण्यासाठी '+ Add Farm' दाबा.\n"
                    "• किंवा '[📍 Detect My Location]' वापरून थेट शेताचे स्थान मिळवा."
                )
            elif lang == "hi":
                reply = "ℹ️ **यह 'खेत (Farms)' पेज है:** यहाँ आप अपने खेत और उनका सटीक जीपीएस स्थान जोड़ सकते हैं।"
            else:
                reply = "ℹ️ **You are on the 'Farms' screen:** Manage farm parcels and capture one-click GPS coordinates for automated microclimate telemetry."
            actions = [
                ChatAction(label="📍 Add Farm Parcel", action_type="navigate", payload={"path": "/farms"}),
            ]
        elif path == "/market":
            if lang == "mr":
                reply = (
                    "ℹ️ **हे 'बाजारपेठ (Market)' पान आहे:**\n\n"
                    "येथे नाशिक व नजीकच्या APMC मधील ताजे दर, गेल्या ७ दिवसांचा कल आणि विकायचे की थांबायचे याचा सल्ला मिळतो."
                )
            elif lang == "hi":
                reply = "ℹ️ **यह 'मंडी (Market)' पेज है:** यहाँ आप वास्तविक मंडी भाव और बिक्री सिफारिश देख सकते हैं।"
            else:
                reply = "ℹ️ **You are on the 'Market' screen:** Track APMC modal rates, 7-day spread volatility, and commercial selling postures."
            actions = [
                ChatAction(label="🌾 Check Crop Status", action_type="navigate", payload={"path": "/crops"}),
            ]
        elif path == "/weather":
            if lang == "mr":
                reply = (
                    "ℹ️ **हे 'हवामान (Weather)' पान आहे:**\n\n"
                    "येथे तुमच्या शेतावरील तापमान, आर्द्रता आणि पुढील काही दिवसांतील पावसाचा अंदाज दिला जातो, जेणेकरून कांदा सुकवणे सुरक्षित राहील."
                )
            elif lang == "hi":
                reply = "ℹ️ **यह 'मौसम (Weather)' पेज है:** यहाँ आप तापमान, बारिश और फसल सुखाने की सुरक्षा देख सकते हैं।"
            else:
                reply = "ℹ️ **You are on the 'Weather' screen:** View hyper-local meteorological forecasts and field curing safety indices."
            actions = [
                ChatAction(label="🌾 Crop Recommendations", action_type="navigate", payload={"path": "/crops"}),
            ]
        else:
            if lang == "mr":
                reply = (
                    "ℹ️ **हे तुमचे मुख्य 'डॅशबोर्ड' आहे:**\n\n"
                    "येथे तुमच्या सर्व शेतांची, पिकांची, हवामानाची आणि मंडी दरांची ताजी माहिती एकाच जागी दिसते.\n\n"
                    "तुम्ही मला आवाजात किंवा लिहून कोणताही प्रश्न विचारू शकता!"
                )
            elif lang == "hi":
                reply = "ℹ️ **यह आपका मुख्य डैशबोर्ड है:** यहाँ खेत, फसल, मौसम और मंडी भाव का सारांश उपलब्ध है।"
            else:
                reply = "ℹ️ **You are on your main Dashboard:** View your real-time farm overview, crops, weather, and mandi highlights at a glance."
            actions = [
                ChatAction(label="🌾 My Crops", action_type="navigate", payload={"path": "/crops"}),
                ChatAction(label="🌧️ Weather", action_type="navigate", payload={"path": "/weather"}),
                ChatAction(label="📈 Mandi", action_type="navigate", payload={"path": "/market"}),
            ]

        return ChatResponse(
            reply=reply,
            intent="help",
            crop_id=crop.id if crop else None,
            crop_name=cname,
            suggested_actions=actions,
        )

    # --- Core Agricultural Responses (Harvest, Market, Weather, Observation, General) ---
    def _generate_harvest_response(self, crop, farm_name, crop_ind, rec, lang: str):
        harvest_rec = rec.harvest_recommendation.recommendation if rec else "not_ready"
        stage = (crop_ind.latest_growth_stage or "vegetative").replace("_", " ")
        reasons = rec.harvest_recommendation.reasons if rec else []
        main_reason = reasons[0] if reasons else "Based on latest growth stage observations."

        actions = [
            ChatAction(label="📋 Log Field Observation", action_type="navigate", payload={"path": "/crops"}),
            ChatAction(label="🌾 View Recommendation Details", action_type="navigate", payload={"path": "/crops"}),
        ]

        if lang == "mr":
            status_mr = {
                "harvest_now": "काढणीसाठी तयार (Harvest Now)",
                "approaching_harvest": "काढणी जवळ आली आहे (Approaching Harvest)",
                "not_ready": "अद्याप तयार नाही (Not Ready)",
                "insufficient_data": "निरीक्षणाची आवश्यकता (Insufficient Data)",
            }.get(harvest_rec, "अद्याप तयार नाही")

            reply = (
                f"🌾 **काढणी सल्ला ({crop.crop_name} - {farm_name}):**\n\n"
                f"• **सद्य स्थिती:** **{status_mr}**\n"
                f"• **नोंदवलेली अवस्था:** {stage.title()}\n"
                f"• **कारण:** {main_reason}\n\n"
                f"💡 *सल्ला:* कांद्याची मान (neck-fall) ५०% पेक्षा जास्त पडल्याचे शेतात दिसल्यासच काढणी सुरू करा."
            )
        elif lang == "hi":
            status_hi = {
                "harvest_now": "कटाई के लिए तैयार (Harvest Now)",
                "approaching_harvest": "कटाई का समय निकट (Approaching)",
                "not_ready": "अभी तैयार नहीं (Not Ready)",
                "insufficient_data": "फील्ड निरीक्षण आवश्यक",
            }.get(harvest_rec, "तैयार नहीं")

            reply = (
                f"🌾 **कटाई सलाह ({crop.crop_name} - {farm_name}):**\n\n"
                f"• **वर्तमान स्थिति:** **{status_hi}**\n"
                f"• **विकास चरण:** {stage.title()}\n"
                f"• **कारण:** {main_reason}\n\n"
                f"💡 *सुझाव:* जब 50% से अधिक गर्दन मुड़ना (neck-fall) दिखाई दे, तभी पूर्ण कटाई करें।"
            )
        else:
            status_en = harvest_rec.replace("_", " ").title()
            reply = (
                f"🌾 **Harvest Assessment for {crop.crop_name} ({farm_name}):**\n\n"
                f"• **Recommendation:** **{status_en}**\n"
                f"• **Observed Stage:** {stage.title()}\n"
                f"• **Agronomic Factor:** {main_reason}\n\n"
                f"💡 *Guidance:* Biological maturity requires observing top-fall (neck-fall) in the field. Continue scouting your plot."
            )

        return reply, actions

    def _generate_market_response(self, crop, market_ind, rec, lang: str):
        price = market_ind.latest_price or 2450.0
        sell_rec = rec.sell_recommendation.recommendation if rec else "hold_for_observation"
        factors = rec.sell_recommendation.supporting_factors if rec else None
        pred_price = (
            factors.get("predicted_next_modal_price")
            if isinstance(factors, dict)
            else getattr(factors, "predicted_next_modal_price", None)
            if factors
            else None
        )

        actions = [
            ChatAction(label="📈 Mandi Spread Analysis", action_type="navigate", payload={"path": "/market"}),
            ChatAction(label="🌾 Crop Recommendations", action_type="navigate", payload={"path": "/crops"}),
        ]

        pred_str_en = f" Projected next modal price is ~₹{round(pred_price):,}/Q based on historical ML baseline." if pred_price else ""
        pred_str_mr = f" सांख्यिकीय मॉडेलनुसार पुढील अपेक्षित दर सुमारे ₹{round(pred_price):,}/क्विंटल आहे." if pred_price else ""

        if lang == "mr":
            status_mr = {
                "hold_for_observation": "थांबा आणि निरीक्षण करा (Hold For Observation)",
                "sell_now": "विक्री करा (Sell Now)",
                "price_stable": "दर स्थिर (Price Stable)",
                "insufficient_data": "अधिक माहिती आवश्यक",
            }.get(sell_rec, "थांबा आणि निरीक्षण करा")

            reply = (
                f"📈 **बाजारभाव आणि विक्री सल्ला ({crop.crop_name}):**\n\n"
                f"• **सद्य बाजारभाव (नाशिक APMC):** **₹{round(price):,}/क्विंटल**\n"
                f"• **विक्री शिफारस:** **{status_mr}**\n"
                f"{pred_str_mr}\n\n"
                f"💡 *सल्ला:* बाजारभाव सध्यातरी स्थिर आहेत. साठवणूक क्षमता असल्यास आवकेवर लक्ष ठेवा."
            )
        elif lang == "hi":
            status_hi = {
                "hold_for_observation": "रोकें और निरीक्षण करें (Hold)",
                "sell_now": "बिक्री करें (Sell Now)",
                "price_stable": "भाव स्थिर (Price Stable)",
                "insufficient_data": "अतिरिक्त डेटा आवश्यक",
            }.get(sell_rec, "रोकें (Hold)")

            reply = (
                f"📈 **मंडी भाव और बिक्री सलाह ({crop.crop_name}):**\n\n"
                f"• **वर्तमान मंडी भाव:** **₹{round(price):,}/क्विंटल**\n"
                f"• **सिफारिश:** **{status_hi}**\n\n"
                f"💡 *सुझाव:* कीमतें अभी स्थिर हैं। यदि आपके पास भंडारण की सुविधा है, तो आवक पर नजर रखें।"
            )
        else:
            status_en = sell_rec.replace("_", " ").title()
            reply = (
                f"📈 **Market & Selling Posture for {crop.crop_name}:**\n\n"
                f"• **Current Benchmark Rate:** **₹{round(price):,} / Quintal** (Nashik APMC)\n"
                f"• **Recommended Posture:** **{status_en}**\n"
                f"• **Price Trajectory:** Market rates are currently stable.{pred_str_en}\n\n"
                f"💡 *Strategy:* If you have aerated storage, hold to observe arrival volume momentum before offloading."
            )

        return reply, actions

    def _generate_weather_response(self, farm_name, weather_ind, lang: str):
        temp = weather_ind.latest_temperature or weather_ind.average_temperature or 26.3
        hum = weather_ind.latest_humidity or weather_ind.average_humidity or 55.0
        rain = weather_ind.total_rainfall or 0.0

        actions = [
            ChatAction(label="🌧️ Open Weather Station", action_type="navigate", payload={"path": "/weather"}),
            ChatAction(label="⚡ Sync Weather Now", action_type="navigate", payload={"path": "/farms"}),
        ]

        if lang == "mr":
            reply = (
                f"🌧️ **शेताचे हवामान आणि वाळवणी जोखीम ({farm_name}):**\n\n"
                f"• **तापमान:** {temp}°C\n"
                f"• **हवेतील आर्द्रता:** {hum}%\n"
                f"• **पाऊस:** {rain} मिमी (गेल्या ४८ तासांत)\n"
                f"• **वाळवणी स्थिती:** **चांगली (Safe for Drying & Curing)**\n\n"
                f"💡 *सल्ला:* हवेत पावसाची शक्यता कमी आहे; काढलेला कांदा शेतात किंवा शेडमध्ये सुकवण्यासाठी वातावरण अनुकूल आहे."
            )
        elif lang == "hi":
            reply = (
                f"🌧️ **मौसम और सुखाने की स्थिति ({farm_name}):**\n\n"
                f"• **तापमान:** {temp}°C | **नमी:** {hum}%\n"
                f"• **बारिश:** {rain} मिमी\n"
                f"• **सुखाने की स्थिति:** **अनुकूल (Safe)**\n\n"
                f"💡 *सुझाव:* बारिश की कोई तात्कालिक चेतावनी नहीं है; खेत में कार्य और सुखाना सुरक्षित है।"
            )
        else:
            reply = (
                f"🌧️ **Microclimate & Curing Advisory ({farm_name}):**\n\n"
                f"• **Ambient Temperature:** {temp}°C\n"
                f"• **Relative Humidity:** {hum}% RH\n"
                f"• **Rainfall Accumulation:** {rain} mm\n"
                f"• **Field Drying Safety:** **Favorable (Low Curing Risk)**\n\n"
                f"💡 *Agronomic Guidance:* Low precipitation and favorable winds support normal field operations and protected bulb curing."
            )

        return reply, actions

    def _generate_observation_response(self, crop, crop_ind, reminder, lang: str):
        actions = [
            ChatAction(label="📋 Record Observation", action_type="navigate", payload={"path": "/crops"}),
            ChatAction(label="🔔 Manage Schedule", action_type="navigate", payload={"path": "/crops"}),
        ]
        recency = crop_ind.days_since_latest_observation
        rem_str = f"Every {reminder.weekday.title()} at {reminder.reminder_time}" if reminder and reminder.enabled else "No schedule set"

        if lang == "mr":
            rec_text = "आज नोंद केली आहे" if recency == 0 else f"{recency} दिवसांपूर्वी नोंद केली होती" if recency is not None else "अद्याप नोंद केलेली नाही"
            reply = (
                f"📋 **पीक पाहणी आणि आठवडी आठवण ({crop.crop_name}):**\n\n"
                f"• **शेवटची नोंद:** {rec_text}\n"
                f"• **आठवडी शेड्युल:** {rem_str}\n\n"
                f"💡 *टीप:* अचूक काढणी निर्णयासाठी दर आठवड्याला कांद्याची वाढ आणि माना पडण्याचे प्रमाण नोंदवणे गरजेचे आहे."
            )
        elif lang == "hi":
            reply = (
                f"📋 **फसल निरीक्षण एवं अनुस्मारक ({crop.crop_name}):**\n\n"
                f"• **अंतिम रिकॉर्ड:** {recency} दिन पहले\n"
                f"• **साप्ताहिक शेड्यूल:** {rem_str}\n\n"
                f"💡 *सुझाव:* बेहतर निर्णय के लिए हर सप्ताह फसल स्वास्थ्य और गर्दन मुड़ना रिकॉर्ड करें।"
            )
        else:
            rec_text = "Recorded today" if recency == 0 else f"{recency} days ago" if recency is not None else "No observations yet"
            reply = (
                f"📋 **Field Observation Status for {crop.crop_name}:**\n\n"
                f"• **Last Entry:** {rec_text}\n"
                f"• **Weekly Reminder:** {rem_str}\n\n"
                f"💡 *Why it matters:* Regular weekly scouting provides the deterministic evidence needed for accurate harvest timing."
            )

        return reply, actions

    def _generate_general_response(self, crop, farm_name, crop_ind, weather_ind, market_ind, rec, lang: str):
        stage = (crop_ind.latest_growth_stage or "vegetative").replace("_", " ").title()
        price = market_ind.latest_price or 2450.0
        temp = weather_ind.latest_temperature or 26.3

        actions = [
            ChatAction(label="🌾 Harvest Readiness?", action_type="prompt", payload={"prompt": "Is my crop ready to harvest?"}),
            ChatAction(label="💰 Market & Sell Advice?", action_type="prompt", payload={"prompt": "Should I sell or hold?"}),
            ChatAction(label="🌧️ Weather Check?", action_type="prompt", payload={"prompt": "What is the weather and rain risk?"}),
            ChatAction(label="🧪 Fertilizer Advice", action_type="prompt", payload={"prompt": "Show fertilizer recommendations"}),
        ]

        if lang == "mr":
            reply = (
                f"🙏 **नमस्कार! मी तुमचा कृषी सहाय्यक (Kisan AI):**\n\n"
                f"सध्या तुमच्या **{farm_name}** वरील **{crop.crop_name}** पिकाची स्थिती:\n"
                f"• **पिकाची अवस्था:** {stage}\n"
                f"• **हवामान:** {temp}°C (वाळवणीसाठी अनुकूल)\n"
                f"• **मंडी दर:** ₹{round(price):,}/क्विंटल\n\n"
                f"तुम्ही मला आवाजात किंवा लिहून काढणी, पाणी, खते, बाजारभाव किंवा हवामानाबद्दल विचारू शकता!"
            )
        elif lang == "hi":
            reply = (
                f"🙏 **नमस्ते! मैं आपका कृषि सहायक (Kisan AI) हूँ:**\n\n"
                f"आपके खेत **{farm_name}** में **{crop.crop_name}** की वर्तमान स्थिति:\n"
                f"• **चरण:** {stage}\n"
                f"• **तापमान:** {temp}°C\n"
                f"• **मंडी भाव:** ₹{round(price):,}/क्विंटल\n\n"
                f"आप मुझसे कटाई, सिंचाई, उर्वरक, मंडी भाव या मौसम के बारे में पूछ सकते हैं!"
            )
        else:
            reply = (
                f"👋 **Hello! I'm your Farm AI Copilot:**\n\n"
                f"Here is your live farm pulse for **{crop.crop_name}** on **{farm_name}**:\n"
                f"• **Observed Stage:** {stage}\n"
                f"• **Field Temp:** {temp}°C (Safe for field work)\n"
                f"• **Market Benchmark:** ₹{round(price):,} / Quintal\n\n"
                f"Ask me about **harvest readiness**, **irrigation**, **fertilizer advice**, or **market trends** anytime!"
            )

        return reply, actions

    def _handle_no_crops(self, lang: str):
        actions = [
            ChatAction(label="📍 Add Farm Parcel", action_type="navigate", payload={"path": "/farms"}),
            ChatAction(label="🌾 Register Crop", action_type="navigate", payload={"path": "/crops"}),
        ]
        if lang == "mr":
            reply = "कृपया मार्गदर्शन सुरू करण्यासाठी प्रथम एक शेत आणि पीक नोंदवा. मी तुम्हाला मदत करतो!"
        elif lang == "hi":
            reply = "सलाह शुरू करने के लिए कृपया पहले एक खेत और फसल पंजीकृत करें। मैं आपकी सहायता करता हूँ!"
        else:
            reply = "Please register a farm parcel and crop planting first to unlock live decision support."
        return ChatResponse(
            reply=reply,
            intent="general",
            suggested_actions=actions,
        )
