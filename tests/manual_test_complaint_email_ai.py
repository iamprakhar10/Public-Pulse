from app.constants.complaint import ComplaintCategory
from app.database.models import Complaint, User
from app.services.complaint_email_ai import (
    generate_complaint_email_draft,
)

user = User(
    name="Prakhar Singh",
    email="prakhar@example.com",
    phone="9876543210",
    hashed_password="not-used-in-this-test",
) 
#For this manual test, these objects do not need to be saved to PostgreSQL.

def main() -> None:
    """
    Manually test real email generation using Groq.

    This test does not write anything to PostgreSQL.
    It creates a temporary SQLAlchemy Complaint object in memory.
    """

    complaint = Complaint(
        user_id=1,
        summary=(
            "The main road near Vijay Nagar, Jabalpur, "
            "pincode 482005 has been badly damaged for three months. "
            "Large potholes are creating a safety risk for commuters."
        ),
        category=ComplaintCategory.ROAD,
        city="Jabalpur",
        area="Vijay Nagar",
        pincode="482005",
    )

    draft = generate_complaint_email_draft(
        complaint=complaint,
        user=user,
    )

    print("\nGenerated email draft:\n")
    print(
        draft.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    main()