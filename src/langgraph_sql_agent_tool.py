from typing import Annotated

import pandas as pd
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from tools import registry
from utils.get_langchain_llm import langchain_openai_client

# LLM
llm = langchain_openai_client

# System prompt
system_message = """
# YOUR HIGH LEVEL TASKS
You are an expert data analyst agent with deep knowledge of sql queries. Your task is to analyze data based on user's question and answer in a helpful way.

# GENERAL INSTRUCTIONS
- Please keep going until the user's query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved.
- You MUST plan extensively before each function call, and reflect extensively on the outcomes of the previous function calls.
- DO NOT do this entire process by making function calls only, as this can impair your ability to solve the problem and think insightfully.
- If it makes sense to crete a visualization to answer the data, please do so, also when user does not explicitly ask for it.

# SQL RELATED INSTRUCTIONS
- Use the {dialect} dialect for all SQL queries.
- To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.
- Ask the schema of the most relevant tables from the point of view of answering the uses's question
- If there are references to time suchs as "last quarter" or "last month", interpret
the time referring to last data that is available and check what is the most recent
temporal data that exists in the database. If you are not sure how to interpret the time,
ask the user for clarification.
- Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.
- You can order the results by a relevant column to return the most interesting
examples in the database.
- Never query for all the columns from a specific table, only ask for the relevant columns given the question.
- You MUST double check your query before executing it. If you get an error while 
executing a query, rewrite the query and try again.
- DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.
""".format(
    dialect="PostgreSQL",
    top_k=5,
)


# State type
class State(TypedDict):
    messages: Annotated[list, add_messages]
    data: pd.DataFrame | None


# Model node
def call_model(state: State) -> State:
    # Call the LLM with the current messages and available tools (schemas)
    return {
        "messages": [
            llm.invoke(state["messages"], tools=registry.list_tools_by_schema())
        ],
        "data": state["data"],
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
    print(new_messages)
    return {"messages": new_messages, "data": data}
    # return {"messages": new_messages}


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
    return END


def call_model_or_create_visualization(state: State):
    if state["data"] is not None:
        return "create_visual"
    return "call_model"


def create_visual(state: State) -> State:
    # print(code_to_be_executed)
    print("GRAPH GENERATED")
    return state


# Build the graph
graph = StateGraph(State)
graph.add_node("call_model", call_model)
graph.add_node("tools", call_tool)
graph.add_node("create_visual", create_visual)

graph.add_edge(START, "call_model")
graph.add_conditional_edges(
    "call_model",
    route_tools,
    {"tools": "tools", END: END},
)
# graph.add_edge("tools", "call_model")
graph.add_conditional_edges(
    "tools",
    call_model_or_create_visualization,
    {"call_model": "call_model", "create_visual": "create_visual"},
)
graph_complete = graph.compile()

# from pathlib import Path

# graph_png = graph_complete.get_graph(xray=True).draw_mermaid_png()
# with open(Path().cwd() / "graph.png", "wb") as f:
#     f.write(graph_png)


if __name__ == "__main__":
    # question = "Which five products brought in the most total sales revenue in the last quarter, and what product category does each belong to?"
    question = "Create a chart that compares total monthly revenue across countries for the last 12 months."
    message_stack = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": question},
    ]
    result = graph_complete.invoke(
        {"messages": message_stack, "data": None}, {"recursion_limit": 50}
    )
    print(
        result["messages"][-1]["content"]
        if isinstance(result["messages"][-1], dict)
        else result["messages"][-1].content
    )
