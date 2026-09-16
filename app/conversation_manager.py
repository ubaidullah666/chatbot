"""
Conversation Manager and Session State Store.
Handles multi-turn dialogue memory, context window optimization (sliding window + pinned state),
turn-taking hygiene, and concurrent session safety.
"""

import asyncio
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.config import settings
from app.models import ChatMessage
from app.prompt_builder import build_conversation_messages

def utc_now():
    return datetime.now(timezone.utc)

class Session:
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.created_at: datetime = utc_now()
        self.last_active: datetime = utc_now()
        self.history: List[ChatMessage] = []
        self.lock: asyncio.Lock = asyncio.Lock()
        # Extracted reservation state tracking (ensures consistency across long conversations)
        self.extracted_state: Dict[str, Any] = {
            "vehicle_category": None,
            "duration_days": None,
            "driver_age": None,
            "insurance": None,
            "pickup_location": None,
            "confirmed": False,
            "confirmation_code": None
        }

    def add_message(self, role: str, content: str) -> ChatMessage:
        self.last_active = utc_now()
        msg = ChatMessage(role=role, content=content, timestamp=self.last_active)
        self.history.append(msg)
        self._update_extracted_state(role, content)
        return msg

    def _update_extracted_state(self, role: str, content: str):
        """Heuristic reservation entity extraction to persist memory across window sliding."""
        text = content.lower()

        # Vehicle detection
        if "economy" in text or "corolla" in text or "elantra" in text:
            self.extracted_state["vehicle_category"] = "Economy ($45/day)"
        elif "suv" in text or "rav4" in text or "explorer" in text:
            self.extracted_state["vehicle_category"] = "SUV ($75/day)"
        elif "electric" in text or "tesla" in text or "polestar" in text or "ev" in text:
            self.extracted_state["vehicle_category"] = "Electric ($85/day)"
        elif "luxury" in text or "bmw" in text or "mercedes" in text:
            self.extracted_state["vehicle_category"] = "Luxury ($135/day)"

        # Days / Duration detection
        day_match = re.search(r"(\d+)\s*(?:day|days)", text)
        if day_match:
            self.extracted_state["duration_days"] = int(day_match.group(1))

        # Driver Age detection
        age_match = re.search(r"(?:i am|age|aged|i'm)\s*(\d{2})", text)
        if age_match:
            self.extracted_state["driver_age"] = int(age_match.group(1))

        # Insurance tier detection
        if "zero excess" in text or "premium" in text:
            self.extracted_state["insurance"] = "Zero Excess Premium ($28/day, $0 deductible)"
        elif "standard" in text or "cdw" in text:
            self.extracted_state["insurance"] = "Standard CDW ($15/day, $500 deductible)"
        elif "roadside" in text:
            self.extracted_state["insurance"] = "Roadside Plus ($7/day)"

        # Location detection
        if "airport" in text:
            self.extracted_state["pickup_location"] = "Airport Terminal"
        elif "downtown" in text:
            self.extracted_state["pickup_location"] = "Downtown City Center"

        # Confirmation code detection
        code_match = re.search(r"APX-\d{5}", content)
        if code_match:
            self.extracted_state["confirmation_code"] = code_match.group(0)
            self.extracted_state["confirmed"] = True

    def get_pinned_summary(self) -> Optional[str]:
        """Formats the extracted state into a compact memory block for prompt injection."""
        items = []
        for k, v in self.extracted_state.items():
            if v is not None:
                readable_k = k.replace("_", " ").title()
                items.append(f"- {readable_k}: {v}")
        if items:
            return "\n".join(items)
        return None

    def get_prompt_messages(self, max_turns: int = 8) -> List[Dict[str, str]]:
        """
        Implements Sliding Window Memory Management:
        - Keeps only the last max_turns (turns = user + assistant pairs)
        - Injects pinned summary of earlier entities if history was truncated
        - Cleans up turn alternation
        """
        # Exclude system messages from history list
        dialogue = [
            {"role": m.role, "content": m.content}
            for m in self.history
            if m.role in ["user", "assistant"]
        ]

        # Calculate sliding window
        max_messages = max_turns * 2
        was_truncated = len(dialogue) > max_messages
        recent_dialogue = dialogue[-max_messages:] if was_truncated else dialogue

        # Pinned summary generated if conversation history has grown
        pinned_summary = self.get_pinned_summary() if was_truncated else None

        return build_conversation_messages(recent_dialogue, pinned_summary)

    def clear(self):
        self.history.clear()
        self.last_active = utc_now()
        self.extracted_state = {
            "vehicle_category": None,
            "duration_days": None,
            "driver_age": None,
            "insurance": None,
            "pickup_location": None,
            "confirmed": False,
            "confirmation_code": None
        }


class ConversationManager:
    """Thread-safe session repository and orchestrator."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._global_lock = asyncio.Lock()

    async def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        async with self._global_lock:
            if not session_id or session_id not in self._sessions:
                new_id = session_id or str(uuid.uuid4())
                session = Session(session_id=new_id)
                self._sessions[new_id] = session
                return session
            return self._sessions[session_id]

    async def get_session(self, session_id: str) -> Optional[Session]:
        async with self._global_lock:
            return self._sessions.get(session_id)

    async def list_sessions(self) -> List[Session]:
        async with self._global_lock:
            return list(self._sessions.values())

    async def reset_session(self, session_id: str) -> bool:
        async with self._global_lock:
            if session_id in self._sessions:
                self._sessions[session_id].clear()
                return True
            return False

    async def delete_session(self, session_id: str) -> bool:
        async with self._global_lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def get_welcome_message(self) -> str:
        return (
            "Hello and welcome to **ApexDrive**! 🚗\n\n"
            "I'm your AI Rental Concierge. I can help you check fleet availability, "
            "calculate exact rates, explore insurance packages, or finalize your reservation.\n\n"
            "To get started, what dates or vehicle category (Economy, SUV, Electric, Luxury) are you looking for?"
        )

conversation_manager = ConversationManager()
