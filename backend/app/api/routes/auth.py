from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from app.models.schemas import LoginRequest, SignupRequest, AuthResponse, AuthUser
from app.services.database import db_service

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

@router.get("/debug")
async def debug_supabase():
    """Debug endpoint to test Supabase connection"""
    try:
        # Test basic connection
        response = db_service.supabase.table("symptom_logs").select("count", count="exact").limit(1).execute()
        return {
            "status": "success",
            "message": "Supabase connection working",
            "supabase_url": db_service.supabase.supabase_url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Supabase connection failed: {str(e)}",
            "supabase_url": getattr(db_service.supabase, 'supabase_url', 'Not set')
        }

@router.post("/signup", response_model=AuthResponse)
async def signup(signup_request: SignupRequest):
    """Create a new user account"""
    logger.info(f"Signup request received for email: {signup_request.email}")
    logger.info(f"Password length: {len(signup_request.password)}")
    
    try:
        response = await db_service.create_user(
            email=signup_request.email,
            password=signup_request.password
        )
        
        logger.info("User creation successful, preparing response")
        
        if response.user:
            logger.info(f"User found, user ID: {response.user.id}")
            
            # Check if we have a session (auto-login) or need email confirmation
            if response.session and response.session.access_token:
                logger.info("Session found - user logged in automatically")
                return AuthResponse(
                    access_token=response.session.access_token,
                    token_type="bearer",
                    user=AuthUser(
                        id=response.user.id,
                        email=response.user.email
                    )
                )
            else:
                logger.info("No session found - email confirmation may be required")
                # User created but needs email confirmation
                # For now, we'll try to sign them in immediately
                try:
                    login_response = await db_service.login_user(
                        email=signup_request.email,
                        password=signup_request.password
                    )
                    
                    if login_response.user and login_response.session:
                        logger.info("Successfully logged in user after signup")
                        return AuthResponse(
                            access_token=login_response.session.access_token,
                            token_type="bearer",
                            user=AuthUser(
                                id=login_response.user.id,
                                email=login_response.user.email
                            )
                        )
                    else:
                        logger.warning("User created but email confirmation required")
                        raise HTTPException(
                            status_code=201, 
                            detail="Account created successfully! Please check your email to confirm your account, then try logging in."
                        )
                except Exception as login_error:
                    logger.error(f"Login after signup failed: {str(login_error)}")
                    raise HTTPException(
                        status_code=201,
                        detail="Account created successfully! Please check your email to confirm your account, then try logging in."
                    )
        else:
            logger.error("No user found in response")
            raise HTTPException(status_code=400, detail="Failed to create user account")
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Signup failed with error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=AuthResponse)
async def login(login_request: LoginRequest):
    """Authenticate user login"""
    try:
        response = await db_service.login_user(
            email=login_request.email,
            password=login_request.password
        )
        
        if response.user and response.session:
            return AuthResponse(
                access_token=response.session.access_token,
                token_type="bearer",
                user=AuthUser(
                    id=response.user.id,
                    email=response.user.email
                )
            )
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/me", response_model=AuthUser)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user information"""
    try:
        user = await db_service.get_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency to get current user ID from token"""
    try:
        user = await db_service.get_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user.id
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e)) 