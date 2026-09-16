"""
Context Memory Management and Entity Extraction Tests.
Verifies sliding-window truncation and pinned state preservation.
"""

from app.conversation_manager import Session
from app.prompt_builder import build_conversation_messages

def test_session_entity_extraction():
    """Verify regex/heuristic extraction of car rental details across turns."""
    session = Session(session_id="test-session-1")

    # Turn 1: Inquire about car and dates
    session.add_message("user", "Hi, I would like to rent an SUV for 4 days starting this Friday.")
    assert session.extracted_state["vehicle_category"] == "SUV ($75/day)"
    assert session.extracted_state["duration_days"] == 4

    # Turn 2: Age and location
    session.add_message("user", "I am 23 years old and will pick it up at the airport.")
    assert session.extracted_state["driver_age"] == 23
    assert session.extracted_state["pickup_location"] == "Airport Terminal"

    # Turn 3: Insurance preference
    session.add_message("user", "Please add the Zero Excess premium protection.")
    assert "Zero Excess" in session.extracted_state["insurance"]

    # Check pinned summary generation
    summary = session.get_pinned_summary()
    assert summary is not None
    assert "SUV" in summary
    assert "4" in summary
    assert "23" in summary
    assert "Zero Excess" in summary
    assert "Airport" in summary

def test_sliding_window_truncation():
    """Verify that dialogue history beyond max_turns slides out while pinned summary is added."""
    session = Session(session_id="test-session-2")

    # Add initial booking details
    session.add_message("user", "I want an Electric car for 5 days.")
    session.add_message("assistant", "We have the Tesla Model 3 and Polestar 2 available.")

    # Add 10 filler turns to exceed max_turns=4 (8 messages)
    for i in range(10):
        session.add_message("user", f"Question number {i+1} about features?")
        session.add_message("assistant", f"Answer number {i+1} regarding car features.")

    # Total messages is 22 (11 turns)
    assert len(session.history) == 22

    # Request prompt with max_turns=4 (should only keep 8 dialogue messages + 1 system message)
    prompt_msgs = session.get_prompt_messages(max_turns=4)

    # 1 system message + 8 recent dialogue messages = 9 total messages
    assert len(prompt_msgs) == 9
    assert prompt_msgs[0]["role"] == "system"

    # System message must include the pinned reservation context
    system_content = prompt_msgs[0]["content"]
    assert "CURRENT RESERVATION CONTEXT" in system_content
    assert "Electric" in system_content
    assert "5" in system_content

    # The oldest dialogue messages should have been truncated from the dialogue array
    dialogue_contents = [m["content"] for m in prompt_msgs[1:]]
    assert "I want an Electric car for 5 days." not in dialogue_contents
    assert "Question number 10 about features?" in dialogue_contents
