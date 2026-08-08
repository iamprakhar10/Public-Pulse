from app.services.complaint_ai import (
    analyse_complaint_conversation,
)


def main() -> None:
    """
    Run one real complaint analysis against the Groq API.

    This is a manual integration test because it makes a real,
    external API request.
    """

    messages = [
        
    {
        "role": "user",
        "content": (
            "The main road near Vijay Nagar in Jabalpur, "
            "pincode 482005, has been badly damaged for three months."
        ),
    }
]
    

    analysis = analyse_complaint_conversation(messages)

    print("\nComplaint analysis:")
    print(
        analysis.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    main()