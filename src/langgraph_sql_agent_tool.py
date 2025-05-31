from typing import Annotated

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from tools import registry
from utils.get_langchain_llm import langchain_openai_client

# LLM
llm = langchain_openai_client

# System prompt
system_message = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.
You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.
You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.
To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.
If there are references to time suchs as "last quarter" or "last month", interpret
the time referring to last data that is available and check what is the most recent
temporal data that exists in the database. If you are not sure how to interpret the time,
ask the user for clarification.
Then you should query the schema of the most relevant tables.
""".format(
    dialect="PostgreSQL",
    top_k=5,
)


# State type
class State(TypedDict):
    messages: Annotated[list, add_messages]


# Model node
def call_model(state: State) -> State:
    # Call the LLM with the current messages and available tools (schemas)
    return {
        "messages": [
            llm.invoke(state["messages"], tools=registry.list_tools_by_schema())
        ]
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
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool = registry.get_tool(tool_name)
        if tool is None:
            result = f"Tool {tool_name} not found."
        else:
            result = tool(**tool_args)
        tool_response_message = {
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": str(result),
        }
        new_messages.append(tool_response_message)
    print(new_messages)
    return {"messages": new_messages}


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


# Build the graph
graph = StateGraph(State)
graph.add_node("call_model", call_model)
graph.add_node("tools", call_tool)
graph.add_edge(START, "call_model")
graph.add_conditional_edges(
    "call_model",
    route_tools,
    {"tools": "tools", END: END},
)
graph.add_edge("tools", "call_model")
graph_complete = graph.compile()

if __name__ == "__main__":
    question = "Which five products brought in the most total sales revenue in the last quarter, and what product category does each belong to?"
    message_stack = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": question},
    ]
    result = graph_complete.invoke({"messages": message_stack}, {"recursion_limit": 50})
    print(
        result["messages"][-1]["content"]
        if isinstance(result["messages"][-1], dict)
        else result["messages"][-1].content
    )
