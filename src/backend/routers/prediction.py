import logging

from fastapi import APIRouter, Request, Response, status

from backend.agent.graph import compiled_graph
from backend.agent.prompt import SYSTEM_PROMPT
from backend.api_schema import ChatRequest, ChatResponse, ErrorResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={
        status.HTTP_200_OK: {"description": "Success", "model": ChatResponse},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Unprocessable Entity"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error",
            "model": ErrorResponse,
        },
    },
)


@router.post(
    "/ask_agent",
    description="Chat with the data analyst agent",
    status_code=status.HTTP_200_OK,
)
def ask_agent(request: Request, body: ChatRequest, response: Response):
    # Check if the first message is a system message
    if body.messages[0]["type"] != "system":
        body.messages = [{"type": "system", "content": SYSTEM_PROMPT}] + body.messages

    result = compiled_graph.invoke(
        {
            "messages": body.messages,
            "data": None,
            "visual_created": False,
            "follow_up_question": body.follow_up_question,
            "visualization_type": None,
            "visualization_image": None,
        },
        {"recursion_limit": 50},
    )
    response = ChatResponse(
        messages=result["messages"],
        result=result["messages"][-1].content,
        follow_up_question=result["follow_up_question"],
        visualization_image=result["visualization_image"],
    )
    return response
