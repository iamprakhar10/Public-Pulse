import json

from groq import Groq
from pydantic import ValidationError

from app.database.models import Complaint, User
from app.schemas.complaint import ComplaintEmailDraft
from dotenv import load_dotenv

load_dotenv()

client = Groq()

EMAIL_SYSTEM_PROMPT = """
You are the email-drafting component of Public Pulse, an Indian civic
complaint assistant.

Generate a formal complaint email based only on the supplied complaint
and complainant information.

Rules:
1. Do not invent facts.
2. Use a polite, professional and firm tone.
3. Clearly explain the civic problem.
4. Mention the city, area and pincode as the location of the reported
   problem.
5. Never claim that the complainant lives in, resides in, owns property
   in, or is personally located at the complaint location unless that
   information is explicitly provided.
6. Do not infer the complainant's address or place of residence from
   the complaint city, area or pincode.
7. Mention how long the issue has existed when provided.
8. Explain public inconvenience or safety concerns only when supported
   by the complaint information.
9. Request timely inspection and appropriate action.
10. Use the complainant's name naturally.
11. End the email with the complainant's name.
12. Do not include the complainant's phone number, home address or
    email address unless explicitly supplied for inclusion.
13. Do not include a recipient email address.
14. Do not claim that photos, documents or evidence are attached unless
    explicitly stated.
15. Do not include markdown headings such as **Subject** or **Body**.
16. Return structured output matching the supplied schema.
""".strip()

def build_email_complaint_context(
        complaint: Complaint,
        user: User,
) -> str:
    """
    Converting a Complaint object into a readable context for 
    email drafting model

    Only stored complaint facts are included in this
    """

    return f"""
Complainant name:
{user.name}

Complaint summary:
{complaint.summary}

Category:
{complaint.category.value if complaint.category else "Not available"}

City:
{complaint.city or "Not available"}

Area:
{complaint.area or "Not available"}

Pincode:
{complaint.pincode or "Not available"}
""".strip()

def generate_complaint_email_draft(
        complaint: Complaint,
        user: User,
) -> ComplaintEmailDraft:
    """
    Generate and validate a formal complaint email draft.

    Raises ValueError if required complaint information is
    missing or if ai model returns empty or invalid data
    """

    if not user.name.strip():
        raise ValueError(
            "The user's name is required before generating an email."
        )

    if complaint.summary is None:
        raise ValueError(
            'Complain summary is required for generating email'
        )

    if complaint.category is None:
        raise ValueError(
            "A complaint category is required before generating an email."
        )

    if complaint.city is None:
        raise ValueError(
            "A complaint city is required before generating an email."
        )

    if complaint.area is None:
        raise ValueError(
            "A complaint area is required before generating an email."
        )

    if complaint.pincode is None:
        raise ValueError(
            "A complaint pincode is required before generating an email."
        )

    complaint_context = build_email_complaint_context(
        complaint=complaint,
        user=user,
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        temperature=0,
        messages=[
            {
                'role':'system',
                'content': EMAIL_SYSTEM_PROMPT,
            },
            {
                'role':'user',
                'content': (
                    "Generate a formal complaint email from the "
                    "following complaint information:\n\n"
                    f"{complaint_context}"
                ),
            },
        ],
        response_format={
            'type':'json_schema',
            'json_schema':{
                'name':'complaint_amail_draft',
                'strict':False,
                'schema': ComplaintEmailDraft.model_json_schema(),
            },
        },
    )

    response_content = response.choices[0].message.content

    if not response_content:
        raise ValueError(
            "No response came from llm for email draft"
        )

    try:
        # Converting json formatted llm response into a dictionary
        response_data = json.loads(response_content)

        # Validating the dict and converting it into a 
        # ComplaintEmailDraft Pydatic object
        return ComplaintEmailDraft.model_validate(
            response_data
        ) 
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(
            "The model returned an invalid complaint email draft."
        ) from exc


"""complaint.summary = (
    "Road near the user's house in Vijay Nagar, Jabalpur, "
    "pincode 482002 has been badly damaged for three months."
)

complaint.category = ComplaintCategory.ROAD
complaint.city = "Jabalpur"
complaint.area = "Vijay Nagar"
complaint.pincode = "482002"""