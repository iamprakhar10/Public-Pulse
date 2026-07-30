from langgraph.graph import StateGraph, START, END

from app.database.complaint_crud import get_user_complaint
from app.database.session import SessionLocal
from app.graphs.complaint_state import ComplaintGraphState

from app.services.complaint_ai import (
    analyse_complaint_conversation
)
from app.services.location_resolver import resolve_city


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
        END,
    )

    return graph_builder.compile()

complaint_graph = build_complaint_graph()