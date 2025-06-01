import base64
import logging
from typing import Annotated

import pandas as pd
from langgraph.graph import END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from backend.agent.tools import VISUALIZATION_TYPES, registry
from backend.utils.get_langchain_llm import langchain_openai_client


# State type
class State(TypedDict):
    messages: Annotated[list, add_messages]
    data: pd.DataFrame | None = None
    result: str | None
    visual_created: bool
    follow_up_question: str | None
    visualization_type: VISUALIZATION_TYPES | None
    visualization_image: str | None


# LLM
llm = langchain_openai_client


def post_process_message(message: dict) -> str:
    if message.type == "ai":
        # logging.error(f"AI message: {message.tool_calls}")
        if message.tool_calls:
            return {
                "type": "ai",
                "content": message.content,
                "tool_calls": message.tool_calls,
            }
        else:
            return {"type": "ai", "content": message.content}


# Model node
def call_model(state: State) -> State:
    # Call the LLM with the current messages and available tools (schemas)

    response_message = llm.invoke(
        state["messages"], tools=registry.list_tools_by_schema()
    )
    return {
        "messages": [
            post_process_message(response_message),
        ],
        "data": state["data"],
        "result": response_message.content,
        "visual_created": state["visual_created"],  # Initially set to False
        "follow_up_question": None,
        "visualization_type": state["visualization_type"],
        "visualization_image": state["visualization_image"],
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
            {"type": "system", "content": system_prompt},
            state["messages"][1],
            state["messages"][-1],
        ]
    )
    return {
        "follow_up_question": response_message.content,
        "result": state["result"],
        "visual_created": state["visual_created"],
        "visualization_type": state["visualization_type"],
        "visualization_image": state["visualization_image"],
    }


# Tool node
def call_tool(state: State) -> State:
    # Find the tool call in the last message
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls
    new_messages = []
    data = state["data"]
    visualization_type = state["visualization_type"]

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool = registry.get_tool(tool_name)
        if tool is None:
            result = f"Tool {tool_name} not found."
        elif tool_name == "create_visualization_with_python_code":
            logging.info(
                "create_visualization_with_python_code will be called separately"
            )
            continue
        else:
            result = tool(**tool_args)

        if isinstance(result, str):
            text_content = result
        elif isinstance(result, tuple):
            text_content, data, visualization_type = result
        else:
            raise ValueError(
                f"Unexpected result type from tool {tool_name}: {type(result)}"
            )
        tool_response_message = {
            "type": "tool",
            "tool_call_id": tool_call["id"],
            "content": str(text_content),
        }
        new_messages.append(tool_response_message)

    return {
        "messages": new_messages,
        "data": data,
        "result": None,
        "visualization_type": visualization_type,
        "visualization_image": state["visualization_image"],
    }


def create_visual(state: State) -> State:  # noqa: C901
    for last_message in state["messages"][::-1]:
        if last_message.type == "ai":
            for tool_call in last_message.tool_calls:
                if tool_call["name"] == "create_visualization_with_python_code":
                    tool_args = tool_call["args"]
                    python_code = tool_args["python_code"]

                    import io

                    import matplotlib.pyplot as plt
                    import seaborn as sns

                    df = state["data"].head(10).copy(deep=True)

                    local_vars = {
                        "pd": pd,
                        "sns": sns,
                        "plt": plt,
                        "df": df,
                    }

                    # Capture stdout for any print statements
                    stdout_buffer = io.StringIO()

                    try:
                        # Switch backend to prevent showing plot windows
                        plt.switch_backend("Agg")

                        # Redirect stdout to capture print outputs
                        import sys

                        original_stdout = sys.stdout
                        sys.stdout = stdout_buffer

                        # Execute the visualization code using the same dict for globals and locals
                        # This allows functions defined in the code string to access variables
                        # defined at the top level of the same code string.
                        exec(python_code, {}, local_vars)

                        # Get print output
                        # stdout_content = stdout_buffer.getvalue()

                        # Restore stdout
                        sys.stdout = original_stdout

                        # Check if a matplotlib figure was created
                        fig = None
                        for var_name, var_value in local_vars.items():
                            if isinstance(var_value, plt.Figure):
                                fig = var_value
                                break

                        # If no explicit figure was assigned to a variable, get the current figure
                        if fig is None and plt.get_fignums():
                            fig = plt.gcf()

                        # Process visualization results
                        if fig:
                            # Save the figure to a BytesIO object
                            buf = io.BytesIO()
                            fig.savefig(buf, format="png", bbox_inches="tight")
                            buf.seek(0)

                            # Convert to base64 for easy display in web
                            result = base64.b64encode(buf.getvalue()).decode("utf-8")

                    except Exception as e:
                        result = f"Error executing visualization code: {e}"

                    tool_response_message = {
                        "type": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(result),
                    }

                    if "Error executing visualization code" not in result:
                        print(
                            "GRAPH GENERATED, visualization_type: ",
                            state["visualization_type"],
                            "visualization_image: ",
                            result,
                        )
                        return {
                            "messages": [tool_response_message],
                            "data": None,
                            "result": state["result"],
                            "visualization_type": state["visualization_type"],
                            "visualization_image": result,
                            "visual_created": True,
                        }
                    else:
                        logging.error("Error creating visualization")
                        return {
                            "messages": [tool_response_message],
                            "data": state["data"],
                            "result": state["result"],
                            "visualization_type": state["visualization_type"],
                            "visualization_image": result,
                            "visual_created": False,
                        }


# Routing function
def route_tools(state: State):
    """
    Route the tools based on the state of the graph.
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "create_visualization_with_python_code":
                return "create_visual"
            else:
                return "tools"
    elif state["visual_created"] is False:
        return "create_visual"
    elif state["follow_up_question"] is None:
        return "suggest_follow_up_question"
    return END
