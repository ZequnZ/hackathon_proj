import os

from dotenv import load_dotenv
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

# This script initializes a SQLDatabase instance and creates a toolkit for interacting with it using an LLM.

uri = "postgresql://user:password@0.0.0.0:5432/northwind"
db = SQLDatabase.from_uri(uri)
print(db.dialect)
print(db.get_usable_table_names())


load_dotenv(override=True)

llm = AzureChatOpenAI(
    model="gpt-4.1", api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

tools = toolkit.get_tools()

print(tools)

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

Then you should query the schema of the most relevant tables.
""".format(
    dialect="PostgreSQL",
    top_k=5,
)

agent_executor = create_react_agent(llm, tools, prompt=system_message)


question = "Which five products brought in the most total sales revenue in the last quarter, and what product category does each belong to?"

for step in agent_executor.stream(
    {"messages": [{"role": "user", "content": question}]},
    stream_mode="values",
):
    step["messages"][-1].pretty_print()
