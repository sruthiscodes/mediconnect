import httpx
import json
import re
from typing import Dict, List, Optional, Any
import asyncio

from app.core.config import settings
from app.models.schemas import TriageResponse, UrgencyLevel

class LLMService:
    def __init__(self):
        self.together_api_key = settings.together_api_key
        self.base_url = "https://api.together.xyz/v1/chat/completions"
        self.model = "mistralai/Mistral-7B-Instruct-v0.1"

    async def generate_response(self, prompt: str) -> Dict[str, Any]:
        """Generate response from LLM - used by the advanced triage agent"""
        
        if not self.together_api_key:
            # Return fallback response
            return {"response": "LLM unavailable, using fallback logic"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.together_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": 1000,
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Try to parse as JSON first
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # Return as text response if not JSON
                        return {"response": content}
                else:
                    print(f"LLM API error: {response.status_code} - {response.text}")
                    return {"response": "LLM API error"}
                    
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return {"response": f"LLM error: {str(e)}"}

    def _construct_triage_prompt(
        self, 
        current_symptoms: str,
        user_history: List[str],
        clinical_guidelines: List[str]
    ) -> str:
        """Construct the triage prompt with RAG context"""
        
        user_history_text = ""
        if user_history:
            user_history_text = "\n".join([f"- {symptom}" for symptom in user_history])
        else:
            user_history_text = "No previous symptom history available."

        clinical_context = ""
        if clinical_guidelines:
            clinical_context = "\n".join([f"- {guideline}" for guideline in clinical_guidelines])
        else:
            clinical_context = "No specific clinical guidelines found for these symptoms."

        prompt = f"""You are a healthcare triage AI assistant. Your role is to assess symptoms and determine appropriate urgency levels.

URGENCY LEVELS (choose exactly one):
- Emergency: Life-threatening conditions requiring immediate ER visit
- Urgent: Serious conditions requiring same-day medical attention  
- Primary Care: Non-urgent conditions suitable for routine doctor visit
- Telehealth: Minor conditions that can be addressed via remote consultation
- Self-Care: Minor conditions manageable with home care

USER'S PREVIOUS SYMPTOM HISTORY:
{user_history_text}

RELEVANT CLINICAL GUIDELINES:
{clinical_context}

CURRENT SYMPTOMS:
{current_symptoms}

Based on the user's history, clinical guidelines, and current symptoms, provide your assessment as a JSON response with exactly this format:

{{
    "urgency_level": "one of: Emergency, Urgent, Primary Care, Telehealth, Self-Care",
    "explanation": "Clear, concise explanation of your assessment and recommended next steps"
}}

Important guidelines:
- Be conservative and prioritize patient safety
- Consider the user's symptom history for context
- Reference clinical guidelines when applicable
- Keep explanations clear and actionable
- If symptoms suggest serious conditions (chest pain, difficulty breathing, severe bleeding, etc.), lean toward higher urgency levels
"""
        return prompt

    async def get_triage_response(
        self,
        current_symptoms: str,
        user_history: List[str],
        clinical_guidelines: List[str]
    ) -> TriageResponse:
        """Get triage response from LLM"""
        
        if not self.together_api_key:
            # Fallback for when no API key is provided
            return self._fallback_triage(current_symptoms)

        prompt = self._construct_triage_prompt(current_symptoms, user_history, clinical_guidelines)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.together_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": 500,
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    try:
                        triage_data = json.loads(content)
                        return TriageResponse(
                            urgency_level=UrgencyLevel(triage_data["urgency_level"]),
                            explanation=triage_data["explanation"]
                        )
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        print(f"Error parsing LLM response: {e}")
                        return self._fallback_triage(current_symptoms)
                else:
                    print(f"LLM API error: {response.status_code} - {response.text}")
                    return self._fallback_triage(current_symptoms)
                    
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return self._fallback_triage(current_symptoms)

    def _extract_temperature(self, symptoms: str) -> Optional[float]:
        """
        Extract temperature values from symptoms text
        """
        # Look for temperature patterns like "105 degrees", "105°F", "105F", etc.
        temp_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:degrees?\s*)?(?:fahrenheit|f)\b',
            r'(\d+(?:\.\d+)?)\s*°\s*f\b',
            r'(\d+(?:\.\d+)?)\s*f\b',
            r'fever\s+of\s+(\d+(?:\.\d+)?)',
            r'temperature\s+(?:of\s+)?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*degree'
        ]
        
        symptoms_lower = symptoms.lower()
        
        for pattern in temp_patterns:
            matches = re.findall(pattern, symptoms_lower)
            if matches:
                try:
                    temp = float(matches[0])
                    # Assume Fahrenheit if reasonable range, otherwise might be Celsius
                    if temp > 80:  # Likely Fahrenheit
                        return temp
                    elif temp > 35 and temp < 45:  # Likely Celsius, convert to Fahrenheit
                        return (temp * 9/5) + 32
                except ValueError:
                    continue
        
        return None

    def _fallback_triage(self, symptoms: str) -> TriageResponse:
        """Enhanced fallback triage logic when LLM is unavailable"""
        symptoms_lower = symptoms.lower()
        
        # Check for specific temperature values first
        temperature = self._extract_temperature(symptoms)
        if temperature:
            if temperature >= 104.0:  # Extremely high fever - Emergency
                return TriageResponse(
                    urgency_level=UrgencyLevel.EMERGENCY,
                    explanation=f"A fever of {temperature}°F is extremely dangerous and potentially life-threatening. Please call 911 or go to the nearest emergency room immediately. This requires immediate medical attention.",
                    confidence=0.95,
                    esi_classification="ESI-1"
                )
            elif temperature >= 102.0:  # High fever - Urgent
                return TriageResponse(
                    urgency_level=UrgencyLevel.URGENT,
                    explanation=f"A fever of {temperature}°F is concerning and requires prompt medical attention. Please contact your doctor immediately or visit an urgent care center today.",
                    confidence=0.9,
                    esi_classification="ESI-2"
                )
            elif temperature >= 100.4:  # Moderate fever - Primary Care
                return TriageResponse(
                    urgency_level=UrgencyLevel.PRIMARY_CARE,
                    explanation=f"A fever of {temperature}°F should be evaluated by a healthcare provider, especially if accompanied by other symptoms.",
                    confidence=0.8,
                    esi_classification="ESI-4"
                )
        
        # Enhanced blood symptom detection - CRITICAL SAFETY CHECK
        blood_emergency_patterns = [
            r'cough.*blood', r'blood.*cough', r'coughing.*blood',
            r'vomit.*blood', r'blood.*vomit', r'vomiting.*blood',
            r'spit.*blood', r'blood.*spit', r'spitting.*blood',
            r'hematemesis', r'hemoptysis', r'bloody.*cough',
            r'blood.*phlegm', r'phlegm.*blood'
        ]
        
        # Check for blood symptoms first - these are always emergencies
        for pattern in blood_emergency_patterns:
            if re.search(pattern, symptoms_lower):
                return TriageResponse(
                    urgency_level=UrgencyLevel.EMERGENCY,
                    explanation="Coughing up blood or vomiting blood is a serious medical emergency that requires immediate attention. Please call 911 or go to the nearest emergency room immediately. This could indicate serious internal bleeding, lung problems, or other life-threatening conditions.",
                    confidence=0.95,
                    esi_classification="ESI-1"
                )
        
        # Enhanced emergency detection with comprehensive patterns - CHECK THESE FIRST
        emergency_patterns = [
            # Neurological emergencies - MOST SPECIFIC FIRST
            r'worst.*headache.*(?:of.*)?(?:my.*)?life', r'worst.*headache.*ever',
            r'thunderclap.*headache', r'sudden.*(?:severe|worst).*headache',
            r'headache.*worst.*(?:of.*)?(?:my.*)?life', r'headache.*worst.*ever',
            
            # Blood-related emergencies
            r'cough.*blood', r'blood.*cough', r'coughing.*blood',
            r'vomit.*blood', r'blood.*vomit', r'vomiting.*blood',
            r'hematemesis', r'hemoptysis',
            
            # Cardiac emergencies
            r'crushing.*chest.*pain', r'severe.*chest.*pain',
            r'chest.*pain.*radiating', r'elephant.*(?:on.*)?chest',
            
            # Respiratory emergencies
            r'can\'?t.*breathe', r'unable.*(?:to.*)?breathe', r'gasping.*(?:for.*)?air',
            r'severe.*shortness.*(?:of.*)?breath', r'respiratory.*distress',
            
            # Other emergencies
            r'severe.*bleeding', r'massive.*bleeding',
            r'loss.*(?:of.*)?consciousness', r'unconscious',
            r'seizure', r'convulsion'
        ]
        
        # Check for emergency patterns FIRST (before keyword matching)
        for pattern in emergency_patterns:
            if re.search(pattern, symptoms_lower):
                return TriageResponse(
                    urgency_level=UrgencyLevel.EMERGENCY,
                    explanation="Based on your symptoms, this appears to be a medical emergency. Please call 911 or go to the nearest emergency room immediately. Do not delay seeking care.",
                    confidence=0.95,
                    esi_classification="ESI-1"
                )
        
        # EMERGENCY - Life-threatening conditions (ESI-1/ESI-2)
        emergency_keywords = [
            "chest pain", "heart attack", "stroke", "difficulty breathing", "can't breathe",
            "severe bleeding", "unconscious", "unresponsive", "severe allergic reaction",
            "suicide", "overdose", "severe trauma", "cannot breathe", "choking",
            "vomiting blood", "hematemesis", "coughing up blood", "hemoptysis",
            "severe head injury", "seizure", "anaphylaxis", "cardiac arrest",
            "respiratory failure", "severe burns", "major trauma"
        ]
        
        # URGENT - Serious conditions requiring same-day care (ESI-3)
        urgent_keywords = [
            "high fever", "severe pain", "severe headache", "broken bone", 
            "severe abdominal pain", "severe nausea", "persistent vomiting",
            "signs of infection", "severe diarrhea", "dehydration",
            "moderate bleeding", "eye injury", "severe allergic reaction",
            "mental health crisis", "severe depression", "panic attack"
        ]
        
        # PRIMARY CARE - Non-urgent but needs medical attention (ESI-4)
        primary_care_keywords = [
            "fever", "headache", "pain", "nausea", "vomiting", "diarrhea",
            "cough", "cold symptoms", "minor injury", "rash", "fatigue",
            "mild infection", "routine check", "medication refill"
        ]
        
        # Check for emergency conditions
        for keyword in emergency_keywords:
            if keyword in symptoms_lower:
                return TriageResponse(
                    urgency_level=UrgencyLevel.EMERGENCY,
                    explanation=f"Your symptoms (including '{keyword}') indicate a potential medical emergency. Please call 911 or go to the nearest emergency room immediately. Do not delay seeking care.",
                    confidence=0.9,
                    esi_classification="ESI-1/ESI-2"
                )
        
        # Check for urgent conditions
        for keyword in urgent_keywords:
            if keyword in symptoms_lower:
                return TriageResponse(
                    urgency_level=UrgencyLevel.URGENT,
                    explanation=f"Your symptoms suggest you need medical attention today. Please contact your doctor, visit an urgent care center, or go to the emergency room if symptoms worsen.",
                    confidence=0.8,
                    esi_classification="ESI-3"
                )
        
        # Check for primary care conditions
        for keyword in primary_care_keywords:
            if keyword in symptoms_lower:
                return TriageResponse(
                    urgency_level=UrgencyLevel.PRIMARY_CARE,
                    explanation="Based on your symptoms, consider scheduling an appointment with your primary care provider for evaluation within the next few days.",
                    confidence=0.7,
                    esi_classification="ESI-4"
                )
        
        # Default to PRIMARY CARE for safety (never default to self-care)
        return TriageResponse(
            urgency_level=UrgencyLevel.PRIMARY_CARE,
            explanation="Based on your symptoms, we recommend scheduling an appointment with your primary care provider for proper evaluation. If symptoms worsen or you develop concerning signs, seek immediate medical attention.",
            confidence=0.6,
            esi_classification="ESI-4"
        )

# Create singleton instance
llm_service = LLMService() 