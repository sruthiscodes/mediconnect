from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime, timedelta
import re

from app.models.schemas import SymptomInput, TriageResponse, SymptomLog, UrgencyLevel
from app.services.database import db_service
from app.services.embeddings import embedding_service
from app.services.llm import llm_service

logger = logging.getLogger(__name__)

class AdvancedTriageAgent:
    """
    Advanced AI Triage Agent with multi-step reasoning, ESI integration, and enhanced RAG
    """
    
    def __init__(self):
        self.esi_guidelines = {
            "ESI-1": {
                "description": "Resuscitation - Life-threatening conditions requiring immediate intervention",
                "examples": ["cardiac arrest", "respiratory failure", "severe trauma", "anaphylaxis"],
                "urgency": UrgencyLevel.EMERGENCY,
                "timeframe": "Immediate (0 minutes)"
            },
            "ESI-2": {
                "description": "Emergent - High-risk situations requiring rapid assessment",
                "examples": ["chest pain with cardiac risk", "severe difficulty breathing", "altered mental status", "severe pain"],
                "urgency": UrgencyLevel.EMERGENCY,
                "timeframe": "Immediate (≤10 minutes)"
            },
            "ESI-3": {
                "description": "Urgent - Stable but requiring multiple resources",
                "examples": ["moderate pain", "fever with concerning symptoms", "minor trauma requiring imaging"],
                "urgency": UrgencyLevel.URGENT,
                "timeframe": "Within 30 minutes"
            },
            "ESI-4": {
                "description": "Less urgent - Stable, requiring one resource or primary care evaluation",
                "examples": ["minor injuries", "simple infections", "routine follow-up", "persistent symptoms"],
                "urgency": UrgencyLevel.PRIMARY_CARE,
                "timeframe": "Within 1-2 hours or primary care appointment"
            },
            "ESI-5": {
                "description": "Non-urgent - Minor symptoms manageable with self-care",
                "examples": ["stuffy nose", "minor cold symptoms", "mild congestion", "minor skin irritation"],
                "urgency": UrgencyLevel.SELF_CARE,
                "timeframe": "Self-care appropriate, monitor symptoms"
            }
        }
        
        self.snomed_mappings = {
            # Cardiovascular
            "chest pain": "29857009",
            "shortness of breath": "267036007", 
            "palpitations": "80313002",
            "dizziness": "404640003",
            
            # Respiratory
            "cough": "49727002",
            "wheezing": "56018004",
            "difficulty breathing": "267036007",
            
            # Neurological
            "headache": "25064002",
            "confusion": "40917007",
            "seizure": "91175000",
            "weakness": "13791008",
            
            # Gastrointestinal
            "nausea": "422587007",
            "vomiting": "422400008",
            "abdominal pain": "21522001",
            "diarrhea": "62315008",
            
            # General
            "fever": "386661006",
            "fatigue": "84229001",
            "pain": "22253000"
        }

    async def analyze_symptoms(self, user_id: str, symptoms: str) -> TriageResponse:
        """
        Main triage analysis using agent-based reasoning
        """
        logger.info(f"Starting advanced triage analysis for user {user_id}")
        
        try:
            # Step 1: Gather contextual information
            context = await self._gather_context(user_id, symptoms)
            
            # Step 2: Perform multi-step reasoning
            reasoning_result = await self._perform_reasoning(symptoms, context)
            
            # Step 3: Apply ESI classification
            esi_classification = await self._apply_esi_classification(symptoms, reasoning_result)
            
            # Step 4: Generate final recommendation
            final_result = await self._generate_final_recommendation(
                symptoms, context, reasoning_result, esi_classification
            )
            
            # Step 5: Save to database
            await self._save_assessment(user_id, symptoms, final_result)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Triage analysis failed: {str(e)}")
            # Fallback to basic triage
            return await self._fallback_triage(symptoms)

    async def _gather_context(self, user_id: str, current_symptoms: str) -> Dict[str, Any]:
        """
        Gather comprehensive context including patient history and clinical guidelines
        """
        logger.info("Gathering contextual information")
        
        # Get patient history (last 6 months)
        recent_symptoms = await db_service.get_recent_user_symptoms(user_id, limit=10)
        
        # Get unresolved symptoms for critical context
        unresolved_symptoms = await db_service.get_unresolved_symptoms(user_id, limit=5)
        
        # Get related symptoms from history
        related_symptoms = await db_service.find_related_symptoms(user_id, current_symptoms, days_back=30)
        
        # Get relevant clinical guidelines
        clinical_context = await embedding_service.search_clinical_knowledge(
            current_symptoms, n_results=5
        )
        
        # Get similar patient cases from history
        if recent_symptoms:
            historical_context = await embedding_service.search_user_history(
                user_id, current_symptoms, n_results=3
            )
        else:
            historical_context = []
        
        # Extract SNOMED codes for current symptoms
        snomed_codes = self._extract_snomed_codes(current_symptoms)
        
        return {
            "patient_history": recent_symptoms,
            "unresolved_symptoms": unresolved_symptoms,
            "related_symptoms": related_symptoms,
            "clinical_guidelines": clinical_context,
            "similar_cases": historical_context,
            "snomed_codes": snomed_codes,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _perform_reasoning(self, symptoms: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multi-step reasoning process using Chain-of-Thought prompting
        """
        logger.info("Performing multi-step reasoning")
        
        reasoning_prompt = self._build_reasoning_prompt(symptoms, context)
        
        try:
            reasoning_response = await llm_service.generate_response(reasoning_prompt)
            
            # Parse the structured reasoning response
            if reasoning_response and "reasoning_steps" in reasoning_response:
                return reasoning_response
            else:
                # Fallback parsing if LLM doesn't return structured response
                return self._parse_reasoning_response(reasoning_response.get("response", ""))
                
        except Exception as e:
            logger.error(f"LLM reasoning failed: {str(e)}")
            return self._fallback_reasoning(symptoms, context)

    async def _apply_esi_classification(self, symptoms: str, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply Emergency Severity Index (ESI) classification
        """
        logger.info("Applying ESI classification")
        
        # Check for immediate life-threatening conditions (ESI-1)
        if self._check_esi_1_criteria(symptoms, reasoning):
            return {"esi_level": "ESI-1", **self.esi_guidelines["ESI-1"]}
        
        # Check for high-risk situations (ESI-2)
        if self._check_esi_2_criteria(symptoms, reasoning):
            return {"esi_level": "ESI-2", **self.esi_guidelines["ESI-2"]}
        
        # Check for truly minor symptoms that are safe for self-care (ESI-5)
        if self._check_esi_5_criteria(symptoms, reasoning):
            return {"esi_level": "ESI-5", **self.esi_guidelines["ESI-5"]}
        
        # Determine resource needs for ESI-3, 4
        resource_needs = self._assess_resource_needs(symptoms, reasoning)
        
        if resource_needs >= 2:
            return {"esi_level": "ESI-3", **self.esi_guidelines["ESI-3"]}
        else:
            # Default to ESI-4 (Primary Care) for safety
            return {"esi_level": "ESI-4", **self.esi_guidelines["ESI-4"]}

    async def _generate_final_recommendation(
        self, symptoms: str, context: Dict[str, Any], 
        reasoning: Dict[str, Any], esi: Dict[str, Any]
    ) -> TriageResponse:
        """
        Generate final triage recommendation with comprehensive explanation
        """
        logger.info("Generating final recommendation")
        
        # Build comprehensive prompt for final recommendation
        final_prompt = self._build_final_prompt(symptoms, context, reasoning, esi)
        
        try:
            final_response = await llm_service.generate_response(final_prompt)
            
            if final_response and "urgency_level" in final_response:
                return TriageResponse(
                    urgency_level=UrgencyLevel(final_response["urgency_level"]),
                    explanation=final_response.get("explanation", ""),
                    confidence=final_response.get("confidence", 0.8),
                    next_steps=final_response.get("next_steps"),
                    reasoning_chain=reasoning.get("steps", []),
                    esi_classification=esi["esi_level"],
                    snomed_codes=context.get("snomed_codes", [])
                )
            else:
                # Fallback to ESI-based recommendation
                return TriageResponse(
                    urgency_level=esi["urgency"],
                    explanation=f"Based on ESI classification {esi['esi_level']}: {esi['description']}",
                    confidence=0.7,
                    esi_classification=esi["esi_level"]
                )
                
        except Exception as e:
            logger.error(f"Final recommendation generation failed: {str(e)}")
            return TriageResponse(
                urgency_level=esi["urgency"],
                explanation=f"ESI {esi['esi_level']}: {esi['description']}. {esi['timeframe']}",
                confidence=0.6,
                esi_classification=esi["esi_level"]
            )

    def _build_reasoning_prompt(self, symptoms: str, context: Dict[str, Any]) -> str:
        """
        Build Chain-of-Thought reasoning prompt
        """
        patient_history = "\n".join(context.get("patient_history", [])[:5])
        
        # Format unresolved symptoms
        unresolved_symptoms = context.get("unresolved_symptoms", [])
        unresolved_text = "\n".join([
            f"- {symptom.symptoms} ({symptom.urgency_level.value}, {symptom.resolution_status.value if hasattr(symptom, 'resolution_status') else 'Unknown'}, {symptom.timestamp.strftime('%Y-%m-%d') if symptom.timestamp else 'Unknown date'})"
            for symptom in unresolved_symptoms[:3]
        ]) if unresolved_symptoms else "No unresolved symptoms"
        
        # Format related symptoms
        related_symptoms = context.get("related_symptoms", [])
        related_text = "\n".join([
            f"- {symptom.symptoms} ({symptom.urgency_level.value}, {symptom.timestamp.strftime('%Y-%m-%d') if symptom.timestamp else 'Unknown date'})"
            for symptom in related_symptoms[:3]
        ]) if related_symptoms else "No related symptoms found"
        
        clinical_guidelines = "\n".join([
            f"- {item['document'][:200]}..." 
            for item in context.get("clinical_guidelines", [])[:3]
        ])
        
        return f"""
You are an expert medical triage AI agent. Analyze the following case using step-by-step reasoning.

CURRENT SYMPTOMS: {symptoms}

UNRESOLVED SYMPTOMS (CRITICAL - these may be related or worsening):
{unresolved_text}

RELATED SYMPTOMS FROM HISTORY:
{related_text}

PATIENT HISTORY (last 10 assessments):
{patient_history or "No previous history available"}

RELEVANT CLINICAL GUIDELINES:
{clinical_guidelines}

SNOMED CODES IDENTIFIED: {', '.join(context.get('snomed_codes', []))}

⚠️ CRITICAL SAFETY CONSIDERATIONS:
- If current symptoms could be related to unresolved symptoms, consider escalation
- Coffee ground stool + dizziness/weakness = EMERGENCY (GI bleeding)
- Blood symptoms + hemodynamic instability = EMERGENCY
- Worsening of previously unresolved symptoms = Higher urgency

Please provide a structured analysis with the following format:

{{
    "reasoning_steps": [
        {{
            "step": 1,
            "analysis": "Initial symptom assessment and red flag identification",
            "findings": "List key findings and concerns, including any connections to unresolved symptoms"
        }},
        {{
            "step": 2, 
            "analysis": "Unresolved symptom correlation and progression analysis",
            "findings": "How current symptoms relate to unresolved conditions - escalation needed?"
        }},
        {{
            "step": 3,
            "analysis": "Clinical guideline application and risk stratification", 
            "findings": "Risk level assessment based on guidelines and symptom progression"
        }},
        {{
            "step": 4,
            "analysis": "Differential diagnosis consideration with historical context",
            "findings": "Possible conditions considering patient's ongoing health issues"
        }}
    ],
    "red_flags": ["list of concerning symptoms including GI bleeding indicators"],
    "risk_factors": ["list of risk factors from history and unresolved symptoms"],
    "preliminary_urgency": "Emergency|Urgent|Primary Care|Telehealth|Self-Care",
    "confidence": 0.0-1.0
}}

Think through each step carefully, prioritizing patient safety and considering symptom progression.
"""

    def _build_final_prompt(
        self, symptoms: str, context: Dict[str, Any], 
        reasoning: Dict[str, Any], esi: Dict[str, Any]
    ) -> str:
        """
        Build final recommendation prompt
        """
        return f"""
Based on the comprehensive analysis, provide the final triage recommendation:

SYMPTOMS: {symptoms}
ESI CLASSIFICATION: {esi['esi_level']} - {esi['description']}
REASONING ANALYSIS: {json.dumps(reasoning, indent=2)}

Provide response in this format:
{{
    "urgency_level": "Emergency|Urgent|Primary Care|Telehealth|Self-Care",
    "explanation": "Comprehensive explanation incorporating patient history, clinical guidelines, and ESI classification",
    "confidence": 0.0-1.0,
    "next_steps": {{
        "action": "Specific recommended action",
        "timeframe": "When to seek care",
        "additional_info": "Additional guidance and precautions",
        "booking_url": "Appropriate care booking URL"
    }},
    "clinical_reasoning": "Brief summary of the clinical decision-making process"
}}

Ensure the recommendation is consistent with ESI guidelines and incorporates patient history patterns.
"""

    def _extract_snomed_codes(self, symptoms: str) -> List[str]:
        """
        Extract relevant SNOMED CT codes from symptoms
        """
        symptoms_lower = symptoms.lower()
        found_codes = []
        
        for term, code in self.snomed_mappings.items():
            if term in symptoms_lower:
                found_codes.append(f"{term}:{code}")
        
        return found_codes

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

    def _check_esi_1_criteria(self, symptoms: str, reasoning: Dict[str, Any]) -> bool:
        """
        Check for ESI-1 (life-threatening) criteria
        """
        esi_1_keywords = [
            "cardiac arrest", "not breathing", "unresponsive", "severe trauma",
            "anaphylaxis", "severe allergic reaction", "respiratory failure",
            "unconscious", "choking", "major bleeding", "severe burns"
        ]
        
        symptoms_lower = symptoms.lower()
        red_flags = reasoning.get("red_flags", [])
        
        # Check for extremely high fever (≥104°F is life-threatening)
        temperature = self._extract_temperature(symptoms)
        if temperature and temperature >= 104.0:
            return True
        
        # CRITICAL: Chest pain + breathing difficulty = EMERGENCY
        chest_pain_patterns = [
            r'chest.*pain', r'chest.*discomfort', r'chest.*pressure', r'chest.*tightness',
            r'chest.*ache', r'chest.*burning', r'heart.*pain', r'cardiac.*pain'
        ]
        
        breathing_patterns = [
            r'shortness.*breath', r'short.*breath', r'difficulty.*breathing', r'trouble.*breathing',
            r'hard.*breathe', r'can\'?t.*breathe', r'cannot.*breathe', r'breathless',
            r'dyspnea', r'respiratory.*distress'
        ]
        
        has_chest_symptoms = any(re.search(pattern, symptoms_lower) for pattern in chest_pain_patterns)
        has_breathing_symptoms = any(re.search(pattern, symptoms_lower) for pattern in breathing_patterns)
        
        # Chest pain + breathing difficulty = Life-threatening emergency
        if has_chest_symptoms and has_breathing_symptoms:
            return True
        
        # Enhanced blood-related emergency symptoms including GI bleeding
        blood_emergency_patterns = [
            r'cough.*blood', r'blood.*cough', r'coughing.*blood', 
            r'vomit.*blood', r'blood.*vomit', r'vomiting.*blood',
            r'hematemesis', r'hemoptysis',
            # GI bleeding patterns - CRITICAL
            r'coffee.*ground.*stool', r'stool.*coffee.*ground', r'coffee.*ground.*bowel',
            r'black.*tarry.*stool', r'tarry.*stool', r'melena',
            r'dark.*stool.*dizzy', r'black.*stool.*weak', r'coffee.*ground.*dizzy',
            r'coffee.*ground.*weak', r'bloody.*stool.*dizzy', r'bloody.*stool.*weak'
        ]
        
        for pattern in blood_emergency_patterns:
            if re.search(pattern, symptoms_lower):
                return True
        
        # Check for GI bleeding with hemodynamic instability
        gi_bleeding_indicators = ['coffee ground', 'tarry stool', 'black stool', 'melena']
        hemodynamic_indicators = ['dizzy', 'dizziness', 'weak', 'weakness', 'lightheaded', 'faint']
        
        has_gi_bleeding = any(indicator in symptoms_lower for indicator in gi_bleeding_indicators)
        has_hemodynamic_signs = any(indicator in symptoms_lower for indicator in hemodynamic_indicators)
        
        if has_gi_bleeding and has_hemodynamic_signs:
            return True
        
        return any(keyword in symptoms_lower for keyword in esi_1_keywords) or \
               any("life-threatening" in flag.lower() for flag in red_flags)

    def _check_esi_2_criteria(self, symptoms: str, reasoning: Dict[str, Any]) -> bool:
        """
        Check for ESI-2 (emergent) criteria
        """
        esi_2_keywords = [
            "chest pain", "difficulty breathing", "severe pain", "altered mental status",
            "high fever", "severe headache", "stroke symptoms", "vomiting blood",
            "hematemesis", "coughing up blood", "hemoptysis", "severe bleeding",
            "severe abdominal pain", "severe burns", "head trauma", "seizure",
            "severe allergic reaction", "overdose", "suicide", "severe dehydration"
        ]
        
        symptoms_lower = symptoms.lower()
        red_flags = reasoning.get("red_flags", [])
        
        # Check for high fever (≥102°F requires urgent care)
        temperature = self._extract_temperature(symptoms)
        if temperature and temperature >= 102.0:
            return True
        
        # CRITICAL: Individual chest pain or breathing difficulty patterns
        chest_pain_patterns = [
            r'chest.*pain', r'chest.*discomfort', r'chest.*pressure', r'chest.*tightness',
            r'chest.*ache', r'chest.*burning', r'heart.*pain', r'cardiac.*pain',
            r'angina', r'myocardial'
        ]
        
        breathing_patterns = [
            r'shortness.*breath', r'short.*breath', r'difficulty.*breathing', r'trouble.*breathing',
            r'hard.*breathe', r'can\'?t.*breathe', r'cannot.*breathe', r'breathless',
            r'dyspnea', r'respiratory.*distress', r'wheezing.*severe', r'severe.*wheezing',
            r'shortness.*breat', r'short.*breat'  # Common typo for "breath"
        ]
        
        # Individual chest pain or breathing difficulty = Emergency
        has_chest_symptoms = any(re.search(pattern, symptoms_lower) for pattern in chest_pain_patterns)
        has_breathing_symptoms = any(re.search(pattern, symptoms_lower) for pattern in breathing_patterns)
        
        if has_chest_symptoms or has_breathing_symptoms:
            return True
        
        # Enhanced blood-related symptom detection
        blood_urgent_patterns = [
            r'cough.*blood', r'blood.*cough', r'coughing.*blood',
            r'spit.*blood', r'blood.*spit', r'spitting.*blood',
            r'vomit.*blood', r'blood.*vomit', r'vomiting.*blood',
            r'hematemesis', r'hemoptysis', r'bloody.*cough',
            r'blood.*phlegm', r'phlegm.*blood'
        ]
        
        for pattern in blood_urgent_patterns:
            if re.search(pattern, symptoms_lower):
                return True
        
        # Enhanced headache detection - persistent headaches need urgent care
        persistent_headache_patterns = [
            r'headache.*(?:for|lasting).*(?:days|weeks)',
            r'(?:persistent|chronic|ongoing).*headache',
            r'headache.*(?:five|5|six|6|seven|7).*days',
            r'throbbing.*headache.*(?:days|weeks)',
            r'severe.*headache.*(?:days|weeks)'
        ]
        
        for pattern in persistent_headache_patterns:
            if re.search(pattern, symptoms_lower):
                return True
        
        # Check direct keyword matches
        keyword_match = any(keyword in symptoms_lower for keyword in esi_2_keywords)
        
        # Check red flags from reasoning
        red_flag_match = any("emergency" in flag.lower() or "urgent" in flag.lower() 
                           for flag in red_flags)
        
        return keyword_match or red_flag_match

    def _check_esi_5_criteria(self, symptoms: str, reasoning: Dict[str, Any]) -> bool:
        """
        Check for ESI-5 (Self-Care) criteria - only for truly minor symptoms
        """
        symptoms_lower = symptoms.lower()
        red_flags = reasoning.get("red_flags", [])
        
        # Only allow self-care for very specific minor symptoms
        minor_cold_patterns = [
            r'^stuffy nose$', r'^runny nose$', r'^mild congestion$',
            r'^minor cold symptoms$', r'^slight congestion$',
            r'^blocked nose$', r'^nasal congestion$'
        ]
        
        # Check if symptoms match minor cold patterns exactly
        for pattern in minor_cold_patterns:
            if re.search(pattern, symptoms_lower.strip()):
                # Additional safety check - no red flags
                if not red_flags or all("minor" in flag.lower() for flag in red_flags):
                    return True
        
        # Check for other truly minor symptoms
        minor_symptoms = [
            "stuffy nose", "runny nose", "mild congestion", "nasal congestion",
            "blocked nose", "minor cold symptoms", "slight congestion"
        ]
        
        # Must be exact match or very close for safety
        if symptoms_lower.strip() in minor_symptoms:
            return True
        
        return False

    def _assess_resource_needs(self, symptoms: str, reasoning: Dict[str, Any]) -> int:
        """
        Assess anticipated resource needs for ESI classification
        """
        # This is a simplified resource assessment
        # In practice, this would be more sophisticated
        
        high_resource_indicators = ["imaging", "lab work", "specialist", "procedure"]
        medium_resource_indicators = ["examination", "medication", "monitoring"]
        
        symptoms_lower = symptoms.lower()
        resource_count = 0
        
        if any(indicator in symptoms_lower for indicator in high_resource_indicators):
            resource_count += 2
        elif any(indicator in symptoms_lower for indicator in medium_resource_indicators):
            resource_count += 1
            
        return resource_count

    def _parse_reasoning_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response if not in structured format
        """
        # Fallback parsing logic
        return {
            "reasoning_steps": [{"step": 1, "analysis": "Basic analysis", "findings": response[:200]}],
            "red_flags": [],
            "risk_factors": [],
            "preliminary_urgency": "Primary Care",
            "confidence": 0.6
        }

    def _fallback_reasoning(self, symptoms: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback reasoning when LLM is unavailable
        """
        symptoms_lower = symptoms.lower()
        
        # Enhanced emergency detection with blood symptoms and cardiopulmonary
        emergency_keywords = ["chest pain", "difficulty breathing", "severe", "blood"]
        blood_emergency_patterns = [
            r'cough.*blood', r'blood.*cough', r'coughing.*blood',
            r'vomit.*blood', r'blood.*vomit', r'vomiting.*blood',
            r'hematemesis', r'hemoptysis'
        ]
        
        # Chest pain and breathing patterns
        chest_pain_patterns = [
            r'chest.*pain', r'chest.*discomfort', r'chest.*pressure', r'chest.*tightness'
        ]
        breathing_patterns = [
            r'shortness.*breath', r'short.*breath', r'difficulty.*breathing', r'trouble.*breathing',
            r'hard.*breathe', r'can\'?t.*breathe', r'cannot.*breathe', r'breathless',
            r'dyspnea', r'respiratory.*distress',
            r'shortness.*breat', r'short.*breat'  # Common typo for "breath"
        ]
        
        urgent_keywords = ["pain", "fever", "headache"]
        
        # Check for blood-related emergencies first
        for pattern in blood_emergency_patterns:
            if re.search(pattern, symptoms_lower):
                return {
                    "reasoning_steps": [{"step": 1, "analysis": "Blood symptom detected", "findings": "Blood in cough/vomit requires emergency care"}],
                    "red_flags": ["blood symptoms"],
                    "preliminary_urgency": "Emergency",
                    "confidence": 0.9
                }
        
        # Check for chest pain + breathing difficulty
        has_chest_symptoms = any(re.search(pattern, symptoms_lower) for pattern in chest_pain_patterns)
        has_breathing_symptoms = any(re.search(pattern, symptoms_lower) for pattern in breathing_patterns)
        
        if has_chest_symptoms and has_breathing_symptoms:
            return {
                "reasoning_steps": [{"step": 1, "analysis": "Chest pain with breathing difficulty", "findings": "Potential cardiac or pulmonary emergency"}],
                "red_flags": ["chest pain", "breathing difficulty"],
                "preliminary_urgency": "Emergency",
                "confidence": 0.95
            }
        elif has_chest_symptoms or has_breathing_symptoms:
            return {
                "reasoning_steps": [{"step": 1, "analysis": "Cardiopulmonary symptom detected", "findings": "Requires emergency evaluation"}],
                "red_flags": ["chest symptoms" if has_chest_symptoms else "breathing difficulty"],
                "preliminary_urgency": "Emergency",
                "confidence": 0.9
            }
        
        if any(keyword in symptoms_lower for keyword in emergency_keywords):
            urgency = "Emergency"
            confidence = 0.7
        elif any(keyword in symptoms_lower for keyword in urgent_keywords):
            urgency = "Urgent" 
            confidence = 0.6
        else:
            urgency = "Primary Care"
            confidence = 0.5
            
        return {
            "reasoning_steps": [{"step": 1, "analysis": "Keyword-based analysis", "findings": f"Classified as {urgency}"}],
            "preliminary_urgency": urgency,
            "confidence": confidence
        }

    async def _save_assessment(self, user_id: str, symptoms: str, result: TriageResponse):
        """
        Save assessment to database and update embeddings
        """
        try:
            # Save to database
            from app.models.schemas import SymptomLog
            log = SymptomLog(
                user_id=user_id,
                symptoms=symptoms,
                urgency_level=result.urgency_level,
                explanation=result.explanation,
                confidence=result.confidence,
                esi_classification=getattr(result, 'esi_classification', None),
                timestamp=datetime.utcnow()
            )
            await db_service.save_symptom_log(log)
            
            # Add to user history embeddings for future RAG
            await embedding_service.add_user_symptom(
                user_id=user_id,
                symptoms=symptoms,
                urgency_level=result.urgency_level.value,
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "esi_classification": getattr(result, 'esi_classification', None),
                    "confidence": result.confidence
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to save assessment: {str(e)}")

    async def _fallback_triage(self, symptoms: str) -> TriageResponse:
        """
        Simple fallback triage when advanced analysis fails
        """
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
        
        # CRITICAL: Chest pain + breathing difficulty = EMERGENCY
        chest_pain_patterns = [
            r'chest.*pain', r'chest.*discomfort', r'chest.*pressure', r'chest.*tightness',
            r'chest.*ache', r'chest.*burning', r'heart.*pain', r'cardiac.*pain'
        ]
        
        breathing_patterns = [
            r'shortness.*breath', r'short.*breath', r'difficulty.*breathing', r'trouble.*breathing',
            r'hard.*breathe', r'can\'?t.*breathe', r'cannot.*breathe', r'breathless',
            r'dyspnea', r'respiratory.*distress',
            r'shortness.*breat', r'short.*breat'  # Common typo for "breath"
        ]
        
        has_chest_symptoms = any(re.search(pattern, symptoms_lower) for pattern in chest_pain_patterns)
        has_breathing_symptoms = any(re.search(pattern, symptoms_lower) for pattern in breathing_patterns)
        
        # Chest pain + breathing difficulty = Life-threatening emergency
        if has_chest_symptoms and has_breathing_symptoms:
            return TriageResponse(
                urgency_level=UrgencyLevel.EMERGENCY,
                explanation="Chest discomfort combined with shortness of breath is a medical emergency that could indicate a heart attack, pulmonary embolism, or other life-threatening condition. Call 911 or go to the nearest emergency room immediately - do not delay or drive yourself.",
                confidence=0.98,
                esi_classification="ESI-1"
            )
        
        # Individual chest pain or breathing difficulty = Emergency
        if has_chest_symptoms:
            return TriageResponse(
                urgency_level=UrgencyLevel.EMERGENCY,
                explanation="Chest pain or discomfort requires immediate medical evaluation to rule out heart attack or other serious cardiac conditions. Please call 911 or go to the nearest emergency room immediately.",
                confidence=0.95,
                esi_classification="ESI-2"
            )
        
        if has_breathing_symptoms:
            return TriageResponse(
                urgency_level=UrgencyLevel.EMERGENCY,
                explanation="Difficulty breathing or shortness of breath requires immediate medical attention as it could indicate serious respiratory or cardiac problems. Please call 911 or go to the nearest emergency room immediately.",
                confidence=0.95,
                esi_classification="ESI-2"
            )
        
        # Enhanced blood symptom detection
        blood_emergency_patterns = [
            r'cough.*blood', r'blood.*cough', r'coughing.*blood',
            r'vomit.*blood', r'blood.*vomit', r'vomiting.*blood',
            r'spit.*blood', r'blood.*spit', r'spitting.*blood',
            r'hematemesis', r'hemoptysis', r'bloody.*cough',
            r'blood.*phlegm', r'phlegm.*blood',
            # GI bleeding patterns - CRITICAL
            r'coffee.*ground.*stool', r'stool.*coffee.*ground', r'coffee.*ground.*bowel',
            r'black.*tarry.*stool', r'tarry.*stool', r'melena',
            r'dark.*stool.*dizzy', r'black.*stool.*weak', r'coffee.*ground.*dizzy',
            r'coffee.*ground.*weak', r'bloody.*stool.*dizzy', r'bloody.*stool.*weak'
        ]
        
        # Check for blood symptoms - these are always emergencies
        for pattern in blood_emergency_patterns:
            if re.search(pattern, symptoms_lower):
                return TriageResponse(
                    urgency_level=UrgencyLevel.EMERGENCY,
                    explanation="Blood in stool (especially coffee ground appearance) combined with dizziness and weakness indicates serious gastrointestinal bleeding with possible blood loss. This is a medical emergency requiring immediate evaluation. Please call 911 or go to the nearest emergency room immediately.",
                    confidence=0.95,
                    esi_classification="ESI-1"
                )
        
        # Check for GI bleeding with hemodynamic instability
        gi_bleeding_indicators = ['coffee ground', 'tarry stool', 'black stool', 'melena']
        hemodynamic_indicators = ['dizzy', 'dizziness', 'weak', 'weakness', 'lightheaded', 'faint']
        
        has_gi_bleeding = any(indicator in symptoms_lower for indicator in gi_bleeding_indicators)
        has_hemodynamic_signs = any(indicator in symptoms_lower for indicator in hemodynamic_indicators)
        
        if has_gi_bleeding and has_hemodynamic_signs:
            return TriageResponse(
                urgency_level=UrgencyLevel.EMERGENCY,
                explanation="Coffee ground stool appearance with dizziness and weakness strongly suggests upper gastrointestinal bleeding with significant blood loss. This is a life-threatening emergency. Call 911 or go to the nearest emergency room immediately - do not delay.",
                confidence=0.98,
                esi_classification="ESI-1"
            )
        
        # Enhanced persistent headache detection
        persistent_headache_patterns = [
            r'headache.*(?:for|lasting).*(?:days|weeks)',
            r'(?:persistent|chronic|ongoing).*headache',
            r'headache.*(?:five|5|six|6|seven|7).*days',
            r'throbbing.*headache.*(?:days|weeks)',
            r'severe.*headache.*(?:days|weeks)'
        ]
        
        for pattern in persistent_headache_patterns:
            if re.search(pattern, symptoms_lower):
                return TriageResponse(
                    urgency_level=UrgencyLevel.URGENT,
                    explanation="A persistent headache lasting several days requires medical evaluation to rule out serious conditions. Please contact your doctor today or visit an urgent care center for assessment.",
                    confidence=0.85,
                    esi_classification="ESI-2"
                )
        
        # Check for truly minor symptoms that are safe for self-care
        minor_cold_patterns = [
            r'^stuffy nose$', r'^runny nose$', r'^mild congestion$',
            r'^minor cold symptoms$', r'^slight congestion$',
            r'^blocked nose$', r'^nasal congestion$'
        ]
        
        for pattern in minor_cold_patterns:
            if re.search(pattern, symptoms_lower.strip()):
                return TriageResponse(
                    urgency_level=UrgencyLevel.SELF_CARE,
                    explanation="This appears to be a minor cold symptom that can typically be managed with self-care. Try rest, fluids, and over-the-counter remedies. If symptoms worsen or persist beyond a week, consider seeing a healthcare provider.",
                    confidence=0.8,
                    esi_classification="ESI-5"
                )
        
        # Basic keyword matching for other symptoms
        if any(word in symptoms_lower for word in ["emergency", "severe", "chest pain", "breathing"]):
            return TriageResponse(
                urgency_level=UrgencyLevel.EMERGENCY,
                explanation="Emergency keywords detected. Seek immediate medical attention.",
                confidence=0.6,
                esi_classification="ESI-2"
            )
        elif any(word in symptoms_lower for word in ["pain", "fever", "headache"]):
            return TriageResponse(
                urgency_level=UrgencyLevel.URGENT,
                explanation="Symptoms suggest urgent care may be needed.",
                confidence=0.5,
                esi_classification="ESI-3"
            )
        else:
            # NEVER default to Self-Care - always Primary Care minimum
            return TriageResponse(
                urgency_level=UrgencyLevel.PRIMARY_CARE,
                explanation="Based on your symptoms, we recommend scheduling an appointment with your primary care provider for proper evaluation. If symptoms worsen or you develop concerning signs, seek immediate medical attention.",
                confidence=0.6,
                esi_classification="ESI-4"
            )

# Create singleton instance
advanced_triage_agent = AdvancedTriageAgent()

class TriageService:
    """
    Main triage service that orchestrates the advanced agent
    """
    
    async def assess_symptoms(self, user_id: str, symptoms: str) -> Dict[str, Any]:
        """
        Assess symptoms using the advanced triage agent
        """
        logger.info(f"Starting triage assessment for user {user_id}")
        
        try:
            # Use the advanced agent for analysis
            result = await advanced_triage_agent.analyze_symptoms(user_id, symptoms)
            
            return {
                "urgency_level": result.urgency_level.value,
                "explanation": result.explanation,
                "confidence": result.confidence,
                "next_steps": getattr(result, 'next_steps', None),
                "esi_classification": getattr(result, 'esi_classification', None),
                "reasoning_chain": getattr(result, 'reasoning_chain', []),
                "snomed_codes": getattr(result, 'snomed_codes', []),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Triage assessment failed: {str(e)}")
            # Fallback to simple assessment
            fallback_result = await advanced_triage_agent._fallback_triage(symptoms)
            return {
                "urgency_level": fallback_result.urgency_level.value,
                "explanation": fallback_result.explanation,
                "confidence": fallback_result.confidence,
                "timestamp": datetime.utcnow().isoformat()
            }

# Create singleton instance
triage_service = TriageService() 