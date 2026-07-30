"""
Manual test for the first version of the complaint LangGraph.

Replace the IDs below with a complaint and user that exist in
your local database.
"""

from pprint import pprint

from app.graphs.complaint_graph import complaint_graph


result = complaint_graph.invoke(
    {
        "complaint_id": 151,
        "user_id": 5,
    }
)

pprint(result)