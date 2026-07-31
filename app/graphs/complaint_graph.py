from langgraph.graph import StateGraph, START, END

from app.database.complaint_crud import (
    get_user_complaint,
    update_complaint_fields,
    add_complaint_message,
    )
from app.database.session import SessionLocal
from app.graphs.complaint_state import ComplaintGraphState

from app.services.complaint_ai import (
    analyse_complaint_conversation
)
from app.services.location_resolver import resolve_city
from app.database.authority_crud import get_authority_for_complaint
from app.constants.complaint import (
    ComplaintStatus,
    MessageRole,
)

from typing import Literal



def load_conversation_node(
        state: ComplaintGraphState,
) -> dict:
    """
    Loads a complaint and it's messages

    LangGraph state should contain serializable values instead of
    SQLAlchemy ORM objects, so each message is converted into a 
    plain dictionary

    Returns: messages
    """

    complaint_id = state['complaint_id']
    user_id = state['user_id']

    db = SessionLocal()

    try:
        complaint = get_user_complaint(
            db=db,
            complaint_id=complaint_id,
            user_id=user_id,
        )

        if complaint is None:
            raise ValueError(
                "Complaint not found or does not belong to this user."
            )

        messages = [
            {
                'role': message.role.value,
                'content': message.content,
            }
            for message in complaint.messages
        ]

        return {
            "messages": messages,
        }

    finally:
        db.close()


def analyze_complaint_node(
        state: ComplaintGraphState,
) -> dict:
    """
    Analyzing the complete complaint conversation using the existing
    complaint-analysis LLM service

    Expected input state:
        messages

    Returns graph-state updates:
        summary
        category
        city
        area
        pincode
        is_complete
        next_question

    The node won't save anything to postgres yet. It will only
    place the LLM analysis into LangGraph state
    """

    messages = state.get("messages", [])

    if not messages:
        raise ValueError(
            "Complaint messages are required before analysis"
        )

    analysis = analyse_complaint_conversation(
        messages=messages,
    )

    return {
        'summary' : analysis.summary,
        'category': analysis.category,
        "city": analysis.city,
        "area": analysis.area,
        "pincode": analysis.pincode,
        "is_complete": analysis.is_complete,
        "next_question": analysis.next_question,
    }




def resolve_city_node(
        state: ComplaintGraphState,
) -> dict:
    """
    Resolving the city text extracted by the llm into a cononical city
    row

    Returns:
        city:
            Canonical city name from the database.

        city_id:
            Primary key of the matching City row.

        error:
            Error message when the city cannot be resolved.
    """
    city_name = state.get('city')

    if not city_name:
        return {
            'city': None,
            'city_id': None,
            'error': 'Complaint city has not been provided',
        }

    db = SessionLocal()

    try:
        resolved_city = resolve_city(
            db=db,
            city_name=city_name,
        )

        if resolved_city is None:
            return {
                'city_id': None,
                'error': (
                    "The complaint city could not be matched "
                    "to a supported city."
                ),
            }

        return {
            # Replace the LLM text with the canonical DB value.
            "city": resolved_city.name,
            "city_id": resolved_city.id,
            "error": None,
        }

    except ValueError:
        return {
            "city_id": None,
            "error": (
                "The complaint city could not be matched "
                "to a supported city."
            ),
        }

    finally:
        db.close()




def find_authority_node(
        state: ComplaintGraphState,
) -> dict:
    """
    Finding authority according to the complaint

    Authority matchign uses 
    - Canonical city ID
    - complaint pincode
    - complaint category

    Returns:
        authority_id:
            ID of the matched authority.

        is_complete:
            True only when the complaint information and authority
            match are both complete.

        error:
            Explanation when an authority cannot be found.

    This node does not save anything to the Complaint table yet.
    """


    city_id = state.get('city_id')
    pincode = state.get('pincode')
    category = state.get('category')

    if city_id is None:
        return {
            'authority_id': None,
            'is_complete': False,
            'error': 'A supported city is required'
        }

    if pincode is None:
        return {
            'authority_id': None,
            'is_complete': False,
            'error': 'A pincode is required'
        }

    if category is None:
        return {
            'authority_id': None,
            'is_complete': False,
            'error': "A complaint category is required"
        }


    db = SessionLocal()

    try:
        authority = get_authority_for_complaint(
            db=db,
            city_id=city_id,
            pincode=pincode,
            category=category,
        )

        if authority is None:
            return {
                "authority_id": None,
                "is_complete": False,
                "error": (
                    "No authority was found for this city, "
                    "pincode and complaint category."
                ),
            }

        return {
            "authority_id": authority.id,

            # The LLM may have considered the complaint complete,
            # but the backend considers it complete only after a
            # valid authority has also been matched.
            "is_complete": state.get('is_complete', False),

            "error": None,
        }
    finally:
        db.close()
    




def save_complaint_node(
        state: ComplaintGraphState,
) -> dict:
    """
    Saving the complaint analysis and database matches

    This node persists
    - extracted complaint details
    - canonical city ID
    - matched authority id
    - complaint status

    Complaint will become AWAITING_APPROVAL only when:
    - the LLM finds all the information
    - city is resolved
    -  authority is found

    Otherwise DRAFT
    """
    complaint_id = state['complaint_id']
    user_id = state['user_id']

    city_id = state.get('city_id')
    authority_id = state.get('authority_id')
    is_complete = state.get('is_complete', False)

    # Complaint is operationally complete only when the backend
    # has resolved both city and authority 

    complaint_is_ready = (
        is_complete
        and city_id is not None
        and authority_id is not None
    )

    if complaint_is_ready:
        complaint_status = ComplaintStatus.AWAITING_APPROVAL
    else:
        complaint_status = ComplaintStatus.DRAFT

    changes = {
        "summary": state.get("summary"),
        "category": state.get("category"),
        "city": state.get("city"),
        "city_id": city_id,
        "area": state.get("area"),
        "pincode": state.get("pincode"),
        "authority_id": authority_id,
        "status": complaint_status,
    }

    db = SessionLocal()

    try:
        complaint = get_user_complaint(
            db=db,
            complaint_id=complaint_id,
            user_id=user_id,
        )
        if complaint is None:
            raise ValueError(
                "Complaint not found or does not belong to this user."
            )

        updated_complaint = update_complaint_fields(
            db=db,
            complaint=complaint,
            changes=changes,
        )

        return {
            'is_complete':complaint_is_ready,
            "status": updated_complaint.status,
        }

    finally:
        db.close()





def ask_clarification_node(
        state: ComplaintGraphState,
) -> dict:
    """
    This saves one assistant clarification question for an 
    incomplete complaint.

    The LLM will normally supply next_question if it doesn't have all 
    required information. Our backend will supply a "fallback" question
    if authority or city is not resolved
    """
    complaint_id = state['complaint_id']

    next_question = state.get('next_question')
    error = state.get('error')

    if state.get('city_id') is None and state.get('city'):
        next_question = (
            "I could not identify the city reliably." \
            "Which city is this issue located in?"
        )


    # The city was resolved, but the authority lookup failed.
    elif (
        state.get('city_id') is not None
        and state.get('authority_id') is None
        and state.get('pincode') is not None
        and state.get('category') is not None
    ):
        next_question = (
            "I could not verify that pincode for this location. "
            "What is the correct pincode?"
        )

    # Safe fallback when neither the LLM nor backend validation
    # produced a useful question.
    elif not next_question:
        next_question = (
            "Could you provide the remaining details about "
            "the issue and its location?"
        )

    db = SessionLocal()

    try:
        add_complaint_message(
            db=db,
            complaint_id=complaint_id,
            content=next_question,
            role=MessageRole.ASSISTANT,
        )

    finally:
        db.close()





def route_after_save(
        state: ComplaintGraphState,
) -> Literal['ask_clarification', 'complete']:
    """
    This decides what should happen after complaint data is saved

    Complete complaints finish the analysis graph

    Incomplete complaint move to the clarification node therefore
    next_question is persisted
    """

    if state.get('is_complete', False):
        return 'complete'

    return 'ask_clarification'

    

























    

def build_complaint_graph():
    """
    Building an initial complaint-processing graph
    Current graph:

        START
          ↓
        load_conversation
          ↓
         END

    More nodes afterwards
    """
    graph_builder = StateGraph(ComplaintGraphState)

    graph_builder.add_node(
        "load_conversation",
        load_conversation_node,
    )

    graph_builder.add_node(
        "analyze_complaint",
        analyze_complaint_node,
    )

    graph_builder.add_node(
        "resolve_city",
        resolve_city_node,
    )

    graph_builder.add_node(
        "find_authority",
        find_authority_node,
    )

    graph_builder.add_node(
        "save_complaint",
        save_complaint_node,
    )
    graph_builder.add_node(
        "ask_clarification",
        ask_clarification_node,
    )

    graph_builder.add_edge(
        START,
        "load_conversation",
    )

    graph_builder.add_edge(
        "load_conversation",
        "analyze_complaint",
    )

    graph_builder.add_edge(
        "analyze_complaint",
        "resolve_city",
    )

    graph_builder.add_edge(
        "resolve_city",
        "find_authority",
    )

    graph_builder.add_edge(
        "find_authority",
        "save_complaint",
    )

    graph_builder.add_conditional_edges(
        "save_complaint",
        route_after_save,
        {
            "ask_clarification": "ask_clarification",
            "complete": END,
        },
    )

    graph_builder.add_edge(
        "ask_clarification",
        END,
    )
    return graph_builder.compile()

complaint_graph = build_complaint_graph()