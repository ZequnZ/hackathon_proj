from typing import Annotated

import pandas as pd
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from backend.tools import registry
from backend.utils.get_langchain_llm import langchain_openai_client

# LLM
llm = langchain_openai_client

DB_instruction_prompt = """
You will beworking with the Northwind database, a classic relational schema for business data. Here is a summary of the tables and their relationships:

Main Tables and Relationships:

- categories: Stores product categories. Each product belongs to a category.
- customer_customer_demo: Junction table linking customers and customer_demographics, representing many-to-many relationships.
- customer_demographics: Stores demographic information for customers.
- customers: Stores customer information. Each order is placed by a customer.
- employees: Stores employee information. Each order is handled by an employee. Employees are assigned to territories (many-to-many).
- employee_territories: Junction table linking employees and territories.
- order_details: Junction table linking orders and products, containing details for each product in an order (many-to-many).
- orders: Stores order information. Linked to customers, employees, shippers, and order_details.
- products: Stores product information. Each product belongs to a category and a supplier. Linked to order_details.
- region: Stores region information. Linked to territories.
- shippers: Stores shipping company information. Each order is shipped by a shipper.
- suppliers: Stores supplier information. Each product has a supplier.
- territories: Stores sales territory information. Linked to region and employee_territories.
- us_states: Stores US state information (for address normalization).

Key Relationship Types:

One-to-Many:
  - categories → products
  - suppliers → products
  - customers → orders
  - employees → orders
  - shippers → orders
  - region → territories

Many-to-Many (via junction tables):
  - orders ↔ products (order_details)
  - employees ↔ territories (employee_territories)
  - customers ↔ customer_demographics (customer_customer_demo)

Summary:
The Northwind schema models a business where customers place orders for products, which are supplied by suppliers and shipped by shippers. Employees manage orders and are assigned to territories, which are grouped into regions. Junction tables are used for many-to-many relationships, ensuring data normalization and flexibility.

Instructions:
Use this schema context to inform your data analysis, SQL query generation, and insights. When asked about relationships, always refer to this structure. If you need to join tables, use the described relationships to construct accurate queries.

"""

# System prompt
# To start you should ALWAYS look at the tables in the database to see what you
# can query. Do NOT skip this step.
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

# DATABASE INSTRUCTIONS

{DB_instruction_prompt}

""".format(
    dialect="PostgreSQL",
    DB_instruction_prompt=DB_instruction_prompt,
    top_k=5,
)


# State type
class State(TypedDict):
    messages: Annotated[list, add_messages]
    data: pd.DataFrame | None
    result: str | None
    visual_created: bool
    follow_up_question: str | None


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


# Build the graph
graph = StateGraph(State)
graph.add_node("call_model", call_model)
graph.add_node("tools", call_tool)
graph.add_node("create_visual", create_visual)
graph.add_node("suggest_follow_up_question", suggest_follow_up_question)

graph.add_edge(START, "call_model")
graph.add_conditional_edges(
    "call_model",
    route_tools,
    {
        "tools": "tools",
        "suggest_follow_up_question": "suggest_follow_up_question",
        "create_visual": "create_visual",
        END: END,
    },
)
graph.add_edge("tools", "call_model")
graph.add_edge("create_visual", "suggest_follow_up_question")
graph.add_edge("suggest_follow_up_question", END)
# graph.add_edge("result_summarizer", END)
graph_complete = graph.compile()

if __name__ == "__main__":
    # question = "Which five products brought in the most total sales revenue in the last quarter, and what product category does each belong to?"
    # question = "What is the average value of an order for each customer segment over the 1997?"
    # question = "In 1997, what are the top 10 cities by order shipping?"
    # question = "Which employee has the most orders? and show me the top 5 products."
    question = "Create a chart that compares total monthly revenue across countries for the last 12 months."
    message_stack = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": question},
    ]
    result = graph_complete.invoke(
        {
            "messages": message_stack,
            "data": None,
            "visual_created": False,
            "follow_up_question": None,
        },
        {"recursion_limit": 50},
    )

    # print(
    #     result["messages"][-1]["content"]
    #     if isinstance(result["messages"][-1], dict)
    #     else result["messages"][-1].content
    # )

    print(
        "Final result: \n",
        result["result"]
        if result["result"] is not None
        else result["messages"][-1]["content"],
    )

    print("follow_up_question: \n", result["follow_up_question"])
