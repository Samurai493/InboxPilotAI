"""Memory service for retrieving user preferences and context."""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.user_preference import UserPreference
from app.models.user import User
import uuid


class MemoryService:
    """Service for managing user memory and preferences."""
    
    @staticmethod
    def get_user_preferences(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user preferences.
        
        Args:
            db: Database session
            user_id: User identifier
            
        Returns:
            User preferences dictionary or None
        """
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return None
        
        preference = db.query(UserPreference).filter(
            UserPreference.user_id == user_uuid
        ).first()
        
        if not preference:
            return None
        
        return {
            "tone": preference.tone,
            "reply_style": preference.reply_style,
            "signature": preference.signature,
            "auto_reply_enabled": preference.auto_reply_enabled == "true",
            "review_threshold": float(preference.review_threshold)
        }
    
    @staticmethod
    def create_or_update_preferences(
        db: Session,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> UserPreference:
        """
        Create or update user preferences.
        
        Args:
            db: Database session
            user_id: User identifier
            preferences: Preferences dictionary
            
        Returns:
            UserPreference object
        """
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise ValueError(f"Invalid user_id: {user_id}")
        
        preference = db.query(UserPreference).filter(
            UserPreference.user_id == user_uuid
        ).first()
        
        if not preference:
            preference = UserPreference(user_id=user_uuid)
            db.add(preference)
        
        # Update fields
        if "tone" in preferences:
            preference.tone = preferences["tone"]
        if "reply_style" in preferences:
            preference.reply_style = preferences["reply_style"]
        if "signature" in preferences:
            preference.signature = preferences["signature"]
        if "auto_reply_enabled" in preferences:
            preference.auto_reply_enabled = "true" if preferences["auto_reply_enabled"] else "false"
        if "review_threshold" in preferences:
            preference.review_threshold = str(preferences["review_threshold"])
        
        db.commit()
        db.refresh(preference)
        
        return preference
    
    @staticmethod
    def get_thread_memory(db: Session, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get thread-specific memory (for future use).
        
        Args:
            db: Database session
            thread_id: Thread identifier
            
        Returns:
            Thread memory dictionary or None
        """
        # Placeholder for thread memory
        # In future, this could retrieve previous interactions, context, etc.
        return None
