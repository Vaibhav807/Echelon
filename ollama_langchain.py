from typing import Annotated, Literal
from typing_extensions import TypedDict

# langgraph imports
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# langchain_core tools import (your existing @tool decorator)
from langchain_core.tools import tool

# Use ChatOllama for local model calls and tool binding
from langchain_ollama import ChatOllama

# -----------------------------
# 1. DEFINE STATE
# -----------------------------
class State(TypedDict):
    """A dictionary containing a list of messages (like chat history)."""
    messages: Annotated[list, add_messages]

# Create the StateGraph
graph = StateGraph(State)

# -----------------------------
# 2. DEFINE TOOLS
# -----------------------------
@tool
def get_weather(location: str):
    """Call to get the current weather."""
    print("get_weather called with location:", location)
    if location.lower() == "yorkshire":
        return "It's cold and wet."
    else:
        return "It's warm and sunny."

@tool
def get_joke():
    """Tool for returning a joke"""
    print("get_joke called")
    return "Why don't scientists trust atoms? Because they make up everything!"

@tool
def send_email(to: str, subject: str, body: str):
    """Tool for sending an email"""
    print("send_email called")
    #print(f"Sending email to {to} with subject: {subject} and body: {body}")
    return "Email sent successfully"

# -----------------------------
# 3. INITIALIZE ChatOllama
# -----------------------------
llm = ChatOllama(
    model="granite3.1-dense:8b",
    temperature=0,
).bind_tools([get_weather, get_joke, send_email])

# Create a ToolNode (langgraph’s node that handles tool calls)
tool_node = ToolNode([get_weather, get_joke, send_email])

graph.add_node("tool_node", tool_node)

# -----------------------------
# 4. PROMPT NODE
# -----------------------------
def prompt_node(state: State) -> State:
    """
    Sends the current messages to our local ChatOllama model.
    Returns the updated state with the model response appended.
    """
    new_message = llm.invoke(state["messages"])
    return {"messages": [new_message]}

graph.add_node("prompt_node", prompt_node)

# -----------------------------
# 5. CONDITIONAL EDGE
# -----------------------------
def conditional_edge(state: State) -> Literal["tool_node", "__end__"]:
    """
    If the last message includes a tool call, route to the tool node;
    otherwise, end the conversation.
    """
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tool_node"
    else:
        return "__end__"

graph.add_conditional_edges("prompt_node", conditional_edge)
graph.add_edge("tool_node", "prompt_node")
graph.set_entry_point("prompt_node")

# -----------------------------
# 6. COMPILE THE GRAPH
# -----------------------------
APP = graph.compile()

# -----------------------------
# 7. RUN EXAMPLE
# -----------------------------
if __name__ == "__main__":
    # Pass messages to the graph; the model may call tools if it decides to.
    state_combined = APP.invoke(
        {
            "messages": [
                "Tell me the weather in London, and then send an email to John Doe with the subject 'Meeting Reminder' and body 'This is a reminder that we have a meeting scheduled for tomorrow at 10 AM.'"
            ]
        }
    )

    # Retrieve the final assistant message
    final_ai_message = state_combined["messages"][-1].content

    # Print just the final AI response
    print("Final AI Response:", final_ai_message)
