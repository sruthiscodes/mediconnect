from supabase import create_client, Client
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import httpx
import re
import logging
from supabase.lib.client_options import ClientOptions

from app.core.config import settings
from app.models.schemas import SymptomLog, AuthUser

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        # Configure Supabase client
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise Exception("Supabase configuration is missing. Please check your environment variables.")
            
        # Create client with default options
        self.supabase: Client = create_client(
            settings.supabase_url, 
            settings.supabase_anon_key,
            options=ClientOptions(
                schema='public',
                headers={
                    'Content-Type': 'application/json'
                },
                auto_refresh_token=True,
                persist_session=True
            )
        )

        # Set timeout for HTTP client
        self.supabase.postgrest.timeout = httpx.Timeout(30.0, connect=20.0)

    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _validate_password(self, password: str) -> tuple[bool, str]:
        """Validate password requirements"""
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        return True, ""

    async def create_user(self, email: str, password: str) -> Dict[str, Any]:
        """Create a new user account"""
        logger.info(f"Attempting to create user with email: {email}")
        
        try:
            # Input validation
            if not email or not password:
                logger.error("Email or password is empty")
                raise ValueError("Email and password are required")

            if not self._validate_email(email):
                logger.error(f"Invalid email format: {email}")
                raise ValueError("Invalid email format")

            is_valid_password, password_error = self._validate_password(password)
            if not is_valid_password:
                logger.error(f"Password validation failed: {password_error}")
                raise ValueError(password_error)

            # Prepare signup data
            signup_data = {
                "email": email,
                "password": password,
                "data": {}  # Additional user metadata if needed
            }
            
            logger.info(f"Sending signup request to Supabase for email: {email}")
            response = self.supabase.auth.sign_up(signup_data)
            logger.info(f"Supabase response received: {type(response)}")
            
            if not response:
                logger.error("No response from Supabase")
                raise Exception("No response from authentication service")
                
            if hasattr(response, 'user') and response.user:
                logger.info(f"User created successfully: {response.user.id}")
                if hasattr(response.user, 'identities') and response.user.identities and len(response.user.identities) == 0:
                    logger.warning("User created but no identities found - may indicate email already registered")
                    raise Exception("Email already registered")
            else:
                logger.error("User creation failed - no user in response")
                raise Exception("User creation failed")
                
            return response
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout exception: {str(e)}")
            raise Exception("Connection to authentication service timed out. Please try again.")
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise Exception(str(e))
        except Exception as e:
            logger.error(f"Unexpected error during user creation: {str(e)}")
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                raise Exception("Connection timed out. Please check your internet connection and try again.")
            elif "already registered" in error_msg or "already exists" in error_msg:
                raise Exception("This email is already registered. Please try logging in instead.")
            elif "invalid email" in error_msg:
                raise Exception("Please provide a valid email address.")
            elif "password" in error_msg:
                raise Exception("Password does not meet requirements. It must be at least 6 characters long.")
            else:
                raise Exception(f"Failed to create user: {str(e)}")

    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user login"""
        try:
            if not email or not password:
                raise ValueError("Email and password are required")
                
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not response or not response.user:
                raise Exception("Invalid credentials")
                
            return response
            
        except httpx.TimeoutException:
            raise Exception("Connection to authentication service timed out. Please try again.")
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                raise Exception("Connection timed out. Please check your internet connection and try again.")
            elif "invalid credentials" in error_msg.lower():
                raise Exception("Invalid email or password")
            else:
                raise Exception(f"Failed to login: {error_msg}")

    async def get_user(self, access_token: str) -> Optional[AuthUser]:
        """Get user information from access token"""
        try:
            if not access_token:
                raise ValueError("Access token is required")
                
            response = self.supabase.auth.get_user(access_token)
            if response.user:
                return AuthUser(
                    id=response.user.id,
                    email=response.user.email
                )
            return None
            
        except httpx.TimeoutException:
            raise Exception("Connection timed out while fetching user data")
        except Exception as e:
            raise Exception(f"Failed to get user: {str(e)}")

    async def save_symptom_log(self, symptom_log: SymptomLog) -> Dict[str, Any]:
        """Save a symptom log to the database"""
        try:
            # Create a service client for admin operations
            service_client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )
            
            data = {
                "user_id": symptom_log.user_id,
                "symptoms": symptom_log.symptoms,
                "urgency_level": symptom_log.urgency_level.value,
                "explanation": symptom_log.explanation,
                "confidence": symptom_log.confidence,
                "esi_classification": getattr(symptom_log, 'esi_classification', None),
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Use service client to bypass RLS for system operations
            response = service_client.table("symptom_logs").insert(data).execute()
            return response.data[0] if response.data else {}
            
        except httpx.TimeoutException:
            raise Exception("Connection timed out while saving symptom log")
        except Exception as e:
            logger.error(f"Database save error: {str(e)}")
            raise Exception(f"Failed to save symptom log: {str(e)}")

    async def get_user_history(self, user_id: str, limit: int = 10) -> List[SymptomLog]:
        """Get user's symptom history"""
        try:
            response = self.supabase.table("symptom_logs")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            logs = []
            for item in response.data:
                logs.append(SymptomLog(
                    id=item["id"],
                    user_id=item["user_id"],
                    symptoms=item["symptoms"],
                    urgency_level=item["urgency_level"],
                    explanation=item["explanation"],
                    confidence=item.get("confidence"),
                    esi_classification=item.get("esi_classification"),
                    resolution_status=item.get("resolution_status", "Unknown"),
                    timestamp=datetime.fromisoformat(item["created_at"].replace('Z', '+00:00'))
                ))
            
            return logs
            
        except httpx.TimeoutException:
            raise Exception("Connection timed out while fetching history")
        except Exception as e:
            raise Exception(f"Failed to get user history: {str(e)}")

    async def get_recent_user_symptoms(self, user_id: str, limit: int = 3) -> List[str]:
        """Get recent user symptoms for RAG context"""
        try:
            logs = await self.get_user_history(user_id, limit)
            return [log.symptoms for log in logs]
        except Exception:
            return []

    async def update_resolution_status(self, symptom_log_id: str, resolution_status: str, user_id: str) -> Dict[str, Any]:
        """Update the resolution status of a symptom log"""
        try:
            service_client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )
            
            data = {
                "resolution_status": resolution_status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = service_client.table("symptom_logs")\
                .update(data)\
                .eq("id", symptom_log_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return response.data[0] if response.data else {}
            
        except Exception as e:
            logger.error(f"Failed to update resolution status: {str(e)}")
            raise Exception(f"Failed to update resolution status: {str(e)}")

    async def get_unresolved_symptoms(self, user_id: str, limit: int = 5) -> List[SymptomLog]:
        """Get user's unresolved symptoms for triage context"""
        try:
            response = self.supabase.table("symptom_logs")\
                .select("*")\
                .eq("user_id", user_id)\
                .in_("resolution_status", ["Ongoing", "Worsened", "Unknown"])\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            logs = []
            for item in response.data:
                logs.append(SymptomLog(
                    id=item["id"],
                    user_id=item["user_id"],
                    symptoms=item["symptoms"],
                    urgency_level=item["urgency_level"],
                    explanation=item["explanation"],
                    confidence=item.get("confidence"),
                    esi_classification=item.get("esi_classification"),
                    timestamp=datetime.fromisoformat(item["created_at"].replace('Z', '+00:00')),
                    resolution_status=item.get("resolution_status", "Unknown")
                ))
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get unresolved symptoms: {str(e)}")
            return []

    async def find_related_symptoms(self, user_id: str, current_symptoms: str, days_back: int = 30) -> List[SymptomLog]:
        """Find potentially related symptoms from user's history"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            response = self.supabase.table("symptom_logs")\
                .select("*")\
                .eq("user_id", user_id)\
                .gte("created_at", cutoff_date.isoformat())\
                .order("created_at", desc=True)\
                .execute()
            
            logs = []
            current_lower = current_symptoms.lower()
            
            for item in response.data:
                # Simple keyword matching for related symptoms
                item_symptoms = item["symptoms"].lower()
                
                # Check for common keywords or symptom patterns
                common_keywords = self._extract_keywords(current_lower)
                item_keywords = self._extract_keywords(item_symptoms)
                
                # If there's overlap in keywords, consider it related
                if len(common_keywords.intersection(item_keywords)) > 0:
                    logs.append(SymptomLog(
                        id=item["id"],
                        user_id=item["user_id"],
                        symptoms=item["symptoms"],
                        urgency_level=item["urgency_level"],
                        explanation=item["explanation"],
                        confidence=item.get("confidence"),
                        esi_classification=item.get("esi_classification"),
                        timestamp=datetime.fromisoformat(item["created_at"].replace('Z', '+00:00')),
                        resolution_status=item.get("resolution_status", "Unknown")
                    ))
            
            return logs[:5]  # Return top 5 related symptoms
            
        except Exception as e:
            logger.error(f"Failed to find related symptoms: {str(e)}")
            return []

    def _extract_keywords(self, text: str) -> set:
        """Extract relevant medical keywords from symptom text"""
        # Common medical keywords to look for
        medical_keywords = {
            'pain', 'ache', 'fever', 'headache', 'nausea', 'vomiting', 'dizziness', 
            'weakness', 'fatigue', 'cough', 'breathing', 'chest', 'stomach', 'abdominal',
            'blood', 'stool', 'urine', 'rash', 'swelling', 'joint', 'muscle', 'back',
            'neck', 'throat', 'ear', 'eye', 'nose', 'mouth', 'heart', 'lung'
        }
        
        words = set(text.lower().split())
        return words.intersection(medical_keywords)

# Create singleton instance
db_service = DatabaseService() 