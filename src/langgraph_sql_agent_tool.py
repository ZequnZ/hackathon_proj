from typing import Annotated

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from tools import registry
from utils.get_langchain_llm import langchain_openai_client

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
You are a data analyst agent designed to provive insights and answer questions from clients.
You have the ability to extract what clients want and then convert necessary info in SQL query to interact with a SQL database.

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

If there are references to time suchs as "last quarter" or "last month", interpret
the time referring to last data that is available and check what is the most recent
temporal data that exists in the database. If you are not sure how to interpret the time,
ask the user for clarification.
Then you should query the schema of the most relevant tables.
Down below is the instruction for the database:

{DB_instruction_prompt}
""".format(
    dialect="PostgreSQL",
    DB_instruction_prompt=DB_instruction_prompt,
    top_k=5,
)


# State type
class State(TypedDict):
    messages: Annotated[list, add_messages]
    result: str | None
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
        "result": response_message.content,
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
        print(tool_response_message["content"])
    return {"messages": new_messages, "result": None}


# Routing function
def route_tools(state: State):
    print(state)
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    elif (
        isinstance(last_message, dict)
        and "tool_calls" in last_message
        and last_message["tool_calls"]
    ):
        return "tools"
    elif state["follow_up_question"] is None:
        return "suggest_follow_up_question"
    return END


# Build the graph
graph = StateGraph(State)
graph.add_node("call_model", call_model)
graph.add_node("tools", call_tool)
graph.add_node("suggest_follow_up_question", suggest_follow_up_question)

graph.add_edge(START, "call_model")
graph.add_conditional_edges(
    "call_model",
    route_tools,
    # {"tools": "tools", "result_summarizer": "result_summarizer", END: END},
    {
        "tools": "tools",
        "suggest_follow_up_question": "suggest_follow_up_question",
        END: END,
    },
)
graph.add_edge("tools", "call_model")
graph.add_edge("suggest_follow_up_question", END)
# graph.add_edge("result_summarizer", END)
graph_complete = graph.compile()

if __name__ == "__main__":
    # question = "Which five products brought in the most total sales revenue in the last quarter, and what product category does each belong to?"
    # question = "What is the average value of an order for each customer segment over the 1997?"
    # question = "In 1997, what are the top 10 cities by order shipping?"
    question = "Which employee has the most orders? and show me the top 5 products."
    message_stack = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": question},
    ]
    result = graph_complete.invoke({"messages": message_stack}, {"recursion_limit": 50})

    # print(
    #     result["messages"][-1]["content"]
    #     if isinstance(result["messages"][-1], dict)
    #     else result["messages"][-1].content
    # )

    print(
        "Final result: ",
        result["result"]
        if result["result"] is not None
        else result["messages"][-1]["content"],
    )

    print("follow_up_question: ", result["follow_up_question"])
