"""
Pydantic response schemas for public pulse dashboar data
"""

from pydantic import BaseModel






class DashboardSummaryResponse(BaseModel):
    """
    Aggregating complaint statistics ofr the dashboard


    <total_complaints, by_status, by_category, by_pincode>

    period_days:
    None -> all time data
    7 means complaints created in last 7 days
    """

    period_days: int | None

    total_complaints: int

    by_status: dict[str, int]

    by_category: dict[str, int]

    by_pincode: dict[str, int]


# {
#   "by_status": {
#     "draft": 5,
#     "sent": 12
#   }
# }