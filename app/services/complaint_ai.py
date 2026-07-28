import json
import os

from dotenv import load_dotenv
from groq import Groq

from app.schemas.complaint import ComplaintAnalysis
from app.constants.complaint import ComplaintCategory
from pydantic import ValidationError


load_dotenv()

client = Groq()

SYSTEM_PROMPT = f"""
You are the complaint-analysis component of Public Pulse application,
an Indian civic complaint assistant.

Analyze the complete conversation and extract structured complaint
details.

Allowed complaint categories:
{', '.join(category.value for category in ComplaintCategory)}

Required details:
- summary
- category
- city
- area
- pincode

Rules:
1. Use only information provided in the conversation.
2. Never invent a location, pincode, date or incident detail.
3. Keep the summary factual and concise.
4. Add every missing required field to missing fields.
5. Ask only one useful follow-up question at a time.
6. If information is missing:
   - is_complete must be false
   - next_question must contain a question
7. If all required information is available:
 - is_complete must be true
 - missing_fields must be empty
 - Next question must be null
8. Pincode must contain exactly six digits when available
9. Return structured output matching the supplied schema
""".strip()

def build_conversation_text(
      messages: list[dict[str,str]],  
) -> str:
    """
    Converting the conversation into readable text for the LLM.

    input will be like this:

    [
        {
            "role": "user",
            "content": "The road is broken."
        },
        {
            "role": "assistant",
            "content": "Where is it located?"
        }
    ]
    """
    conversation_lines: list[str] = []

    for message in messages:
        role = message['role'].upper()
        content = message['content'].strip()

        conversation_lines.append(
            f"{role}: {content}"
        )
    return '\n'.join(conversation_lines)


def analyse_complaint_conversation(
        messages: list[dict[str,str]],
) -> ComplaintAnalysis:
    """
    Send the complete conversation to Groq and return validated,
    structured complaint information

    Returns:
        ComplaintAnalysis:
            Pydantic object with containing extracted fields,
            missing info and ASSISTANT'S NEXT QUESTION

    Raises :
        ValueError:
            If no messages were supplied otr the model returns 
            invalid structured data
    """

    if not messages:
        raise ValueError(
            "Atleast one complaint message is required"
        )

    conversation_text = build_conversation_text(messages)


    #response is and SDK object, not a dictionary
    # <class 'groq.types.chat.chat_completion.ChatCompletion'>
    response = client.chat.completions.create(
        model='openai/gpt-oss-20b',
        temperature=0,
        messages=[
            {
                'role':'system',
                'content': SYSTEM_PROMPT,
            },
            {
                'role':'user',
                'content': (
                    "Analyse this complaint conversation:\n\n"
                    f"{conversation_text}"
                ),
            },
            
        ],
        response_format={
            'type': 'json_schema', #expected response format is based on a JSON Schema
            'json_schema':{
                'name':'complaint_analysis',
                # Best-effort schema adherence.
                #
                # Pydantic still validates the result afterward.
                'strict': False, #This controls how strictly the provider tries to enforce the schema
                'schema': ComplaintAnalysis.model_json_schema(),
            },
        },
    )

    response_content = response.choices[0].message.content

    if not response_content:
        raise ValueError(
            'The complaint-analysis model returned an empty response.'
        )

    try:
        # response_data will be a python dictionary
        response_data = json.loads(response_content)

        # Validating the model's JSON using our pydantic schema
        # But after validating it will return a ComplaintAnalysis
        # python object 
        return ComplaintAnalysis.model_validate(response_data)

    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(
            'The model returned an invalid ComplaintAnalysis response.'
        ) from exc


#response_format={
#     "type": "json_schema",
#     "json_schema": {
#         "name": "complaint_analysis",
#         "strict": False,
#         "schema": ComplaintAnalysis.model_json_schema(),
#     },
# },
#This part tells the model that don't return the response
#  as a paragraph, return JSON that follow this exact structure
# 

# "schema": ComplaintAnalysis.model_json_schema()
"""
class ComplaintAnalysis(BaseModel):
    summary: str | None
    category: ComplaintCategory | None
    city: str | None
    area: str | None
    pincode: Pincode | None
    missing_fields: list[str]
    next_question: str | None
    is_complete: bool

    IS CONVERTED INTO

{
    "type": "object",
    "properties": {
        "summary": {
            "type": ["string", "null"]
        },
        "category": {
            "enum": [
                "road",
                "water",
                "electricity"
            ]
        },
        "city": {
            "type": ["string", "null"]
        },
        "area": {
            "type": ["string", "null"]
        },
        "pincode": {
            "type": ["string", "null"],
            "pattern": "^\\d{6}$"
        },
        "missing_fields": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "next_question": {
            "type": ["string", "null"]
        },
        "is_complete": {
            "type": "boolean"
        }
    }
}
"""

# Our pydantic class is converted into a standard JSON Schema dictionary.
# We normally don't need to write this manually. Pydantic will
# generate if from class 

