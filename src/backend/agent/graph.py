from langgraph.graph import END, START, StateGraph

from backend.agent.node import (
    State,
    call_model,
    call_tool,
    create_visual,
    route_tools,
    suggest_follow_up_question,
)

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
graph.add_edge("create_visual", "call_model")
graph.add_edge("suggest_follow_up_question", END)
compiled_graph = graph.compile()
