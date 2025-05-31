from typing import Annotated

import pandas as pd
from langgraph.graph import END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from backend.agent.tools import registry
from backend.utils.get_langchain_llm import langchain_openai_client


# State type
class State(TypedDict):
    messages: Annotated[list, add_messages]
    data: pd.DataFrame | None = None
    result: str | None
    visual_created: bool
    follow_up_question: str | None


# LLM
llm = langchain_openai_client


# Model node
def call_model(state: State) -> State:
    # Call the LLM with the current messages and available tools (schemas)

    response_message = llm.invoke(
        state["messages"], tools=registry.list_tools_by_schema()
    )
    return {
        "messages": [
            response_message,
        ],
        "data": state["data"],
        "result": response_message.content,
        "visual_created": False,  # Initially set to False
        "follow_up_question": None,
    }


def suggest_follow_up_question(state: State) -> State:
    """
    Suggest a follow-up question to the user based on the result of the query.
    """
    system_prompt = """You will be given a question from clients and an answer provided by a data analyst agent.
    Please suggest 3 follow-up question to the user based on that.
    Make sure that they are relevant to the answer and the question and use concise language that can inspire the client to know more they want.

    Down below is the instruction for the database being discussed:

    {DB_instruction_prompt}
    """
    response_message = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            state["messages"][1],
            state["messages"][-1],
        ]
    )
    return {
        "follow_up_question": response_message.content,
        "result": state["result"],
    }


# Tool node
def call_tool(state: State) -> State:
    # Find the tool call in the last message
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls"):
        tool_calls = last_message.tool_calls
    elif isinstance(last_message, dict) and "tool_calls" in last_message:
        tool_calls = last_message["tool_calls"]
    else:
        tool_calls = []
    print(tool_calls)
    new_messages = []
    data = None  # Initialize data to None
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool = registry.get_tool(tool_name)
        if tool is None:
            result = f"Tool {tool_name} not found."
        else:
            result = tool(**tool_args)
        if isinstance(result, str):
            text_content = result
        elif isinstance(result, tuple):
            text_content, data = result
        else:
            raise ValueError(
                f"Unexpected result type from tool {tool_name}: {type(result)}"
            )
        tool_response_message = {
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": str(text_content),
        }
        new_messages.append(tool_response_message)
        print(tool_response_message["content"])
    return {"messages": new_messages, "data": data, "result": None}


def create_visual(state: State) -> State:
    # print(code_to_be_executed)
    print("GRAPH GENERATED")
    state["visual_created"] = True
    return state


# Routing function
def route_tools(state: State):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    elif (
        isinstance(last_message, dict)
        and "tool_calls" in last_message
        and last_message["tool_calls"]
    ):
        return "tools"
    elif state["visual_created"] is False:
        return "create_visual"
    elif state["follow_up_question"] is None:
        return "suggest_follow_up_question"
    return END
