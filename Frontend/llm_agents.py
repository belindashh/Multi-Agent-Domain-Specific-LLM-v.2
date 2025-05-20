import os 
from dotenv import load_dotenv
from typing import Annotated, TypedDict, Literal
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from datetime import datetime
from langgraph.graph.message import add_messages
from Frontend.config import Config
import pandas as pd
from Frontend.utils import *
from langchain_core.tools import Tool
import sys
import re
from langchain.tools import StructuredTool
from langchain_core.messages import HumanMessage

sys.stdout = sys.__stdout__ 
print("Debug Message")
sys.stdout.flush()

load_dotenv()
max_tokens = 4096 - 500

GPT_MODEL_4_MINI = Config.OPENAI_MODEL
Data_TB = Config.DATA_TB_NAME

llm = ChatOpenAI(
    model=GPT_MODEL_4_MINI,
    temperature=0,
    max_completion_tokens=max_tokens,
    timeout=None,
    max_retries=2,
)


llm_table = ChatOpenAI(
    model=GPT_MODEL_4_MINI,
    model_kwargs={"response_format": "json"},
    temperature=0.3,
    max_completion_tokens=max_tokens,
    timeout=None,
    max_retries=2,
)

#TOOLS
@tool
def llm_tool(
    query: Annotated[str, "The query to search for."]
): 
    """A tool to call an LLM model to search for a query"""
    try:
        result = llm.invoke(query)
    except BaseException as e:
        return f"failed to execute. Error: {repr(e)}"
    return result.content


def llm_tool_func(input: str):
    try:
        result = llm.invoke(input)
        return result.content
    except Exception as e:
        return f"Failed to execute. Error: {repr(e)}"

strict_llm_tool = StructuredTool.from_function(
    llm_tool_func,
    name="strict_llm_tool",
    description="A tool to call an LLM model to search for a query",
    strict=True,
    openai_schema=True,
)

@tool
def read_file(
    query: Annotated[str, "The query to search for."]
): 
    """A tool to call an LLM model to search local database for files for a query"""
    try:
        conn = get_db_connection()
        call = f"SELECT file_name, content, content_bigram_embed FROM {Data_TB}"
        df = pd.read_sql(call, conn)

        message = query_message(query, df, model=GPT_MODEL_4_MINI, token_budget=4096 - 500, column="file_name")
    except BaseException as e:
        return f"failed to execute. Error: {repr(e)}"
    return message


@tool
def read_file_summary(
    query: Annotated[str, "The query to search for."]
): 
    """A tool to call an LLM model to search local database for information for a query"""
    try:
        conn = get_db_connection()
        call = f"SELECT file_name, content, content_bigram_embed FROM {Data_TB}"
        df = pd.read_sql(call, conn)

        message = query_message(query, df, model=GPT_MODEL_4_MINI, token_budget=4096 - 500, column="content")
    except BaseException as e:
        return f"failed to execute. Error: {repr(e)}"
    return message


tavily_tool = TavilySearchResults(max_results=5)
    

#AGENTS
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

class AgentState(MessagesState):
    next: str

members = ["General_LLM", "Math_LLM", "Researcher", "Local_File_Organiser", "Local_Researcher", "JSON_Generator"]

options = members + ["FINISH"]

system_prompt = (
    f"""You are a supervisor managing a team of specialized workers: {members}.

Your role is to route the user's query to the appropriate worker based on the nature of the query and the current state of the conversation.

**Routing Guidelines**

1. Analyze the user's query to determine the appropriate worker:
   - For general queries that are NOT relevant to the finding information: 'General_LLM'
   - For mathematical or scientific calculation queries: 'Math_LLM'
   - For searching the internet or finding recent information: 'Researcher'
   - For file operations (reading, listing local database files): 'Local_File_Organiser'
   - For local database search operations (reading and provide information): 'Local_Researcher'
   - For generating json output: 'JSON_Generator'

2. If the query requires multiple steps, route to the first appropriate worker, then based on the response, route to the next worker as needed.

3. After each worker completes its task, review the response and conversation history:
   - Only if the task is complete, route to 'FINISH'
   - If further action is needed (e.g., processing data into a table), route to the next appropriate worker

4. Important constraints:
   - Avoid redundant actions by checking the conversation history

**Examples**

- User: "What is the current time in New York?"
  - Route to 'General_LLM'

- User: "A ball is dropped from height of 20 meters. Assuming no air resistance, how long will it take to reach the ground?"
  - Route to 'Math_LLM'

- User: "Provide all information available on websearch about Laser Melting"
  - Route to 'Researcher'

- User: "What are all the files in the local database related to Laser Melting"
  - Route to 'Local_File_Organiser'

- User: "What are all the information available in the local database about Laser Melting"
  - Route to 'Local_Researcher'

- User: "Can you organise a TABLE with the columns (material, formula electronegativity) for all materials that have been mentioned in the local database. If there are any missing information, can you research and add in the accurate information?"
  - Route to 'Local_Researcher' and then to 'Researcher'

- User: "Can you organise a json output based on table with the columns (material, formula electronegativity) for all materials that have been mentioned in the local database. If there are any missing information, can you research and add in the accurate information? Then generate the json output based on the information found"
  - For generating json output: route to 'JSON_Generator'
   BUT ONLY after routing to:
   a. 'Local_Researcher' has gathered the relevant data, and
   b. 'Researcher' has filled in missing information.
   Check the conversation history to ensure these steps are complete first.

Respond ONLY with the name of the next worker from: {options}.
"""
)

class SupervisorState(TypedDict):

    next: Literal["General_LLM", "Math_LLM", "Researcher", "Local_File_Organiser", "Local_Researcher", "JSON_Generator", "FINISH"]

#Nodes
def supervisor_node(state: AgentState) -> AgentState:

    print("--- Supervisor Node ---")
    # print(f"Current messages: {state['messages']}")
    messages = [
        {"role": "system", "content": system_prompt},
    ] + state["messages"]

    response = llm.with_structured_output(SupervisorState).invoke(messages)
    next_ = response["next"]
    print(f"Routing to: {next_}")

    if next_ == "FINISH":
        next_ = END

    return {"next": next_}


llm_agent = create_react_agent(
    llm, tools=[llm_tool, tavily_tool], state_modifier="Respond to user's questions to the best of your knowledge. You can use the tools for aid: llm_tool and tavily_tool. "
)
def llm_node(state: AgentState) -> AgentState:
    result = llm_agent.invoke(state)
    return {
        "messages": [
            HumanMessage(content=result["messages"][-1].content, name="General_LLM")
        ]
    }

def extract_json(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    raise ValueError("No valid JSON found")

JSON_agent = create_react_agent( 
    llm_table, tools=[strict_llm_tool], state_modifier="""
    You are a JSON data transformer.

    Your task is to extract structured tabular data from any summary or text messages in the current conversation and output it as a **valid JSON array**

    You will be penalised if you do not follow these rules:
    - Output **only** valid JSON. No explanations, no markdown formatting, no extra text. The output must be parseable by `json.loads()` directly.
    Provide the JSON object starting from `{` or `[` and ending with `}` or `]` only.
    - **DO NOT** add any introduction, explanation or notes.
    - If no data is available, return an empty list: []
    - Return strictly valid JSON only
    """
)
def json_node(state: AgentState) -> AgentState:
    messages = state["messages"][:]

    combined_text = "\n".join(msg.content for msg in messages if hasattr(msg, "content"))

    if "local_researcher_data" in state:
        combined_text += "\n" + state["local_researcher_data"]

    if "researcher_data" in state:
        combined_text += "\n" + state["researcher_data"]

    try:
        input_instance = combined_text

        output= strict_llm_tool.invoke(input_instance)

        clean_output = extract_json(output)

        print("LLM output:", clean_output)

        data = json.loads(clean_output)
        df = pd.DataFrame(data)
        df.to_csv('CSV_Files/new_output.csv', index=False)
        return {
            "messages": [HumanMessage(content="JSON output generated successfully.", name="JSON_Generator")]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "messages": [HumanMessage(content=f"JSON output generation failed. Error: {str(e)}", name="JSON_Generator")]
        }
    

math_agent = create_react_agent(
    llm, tools=[llm_tool, tavily_tool], state_modifier="You are a scientist that is very good  at math and science calculations. Analyse and provide answers to user's question in proper Latex formatting. Make use of the tools available if necessary."
)
def math_node(state: AgentState) -> AgentState:
    print("--- Math Node ---")
    result = math_agent.invoke(state)
    state["previous_agent"] = "Math_LLM"
    return {
        "messages": [
            HumanMessage(content=result["messages"][-1].content, name="Math_LLM")
        ]
    }

file_organizer_agent = create_react_agent(
    llm, tools=[read_file], state_modifier="You are a highly-trained research analyst and can provide the user with the information they need. Use the information from Tool: read_file to compile and organise the relevant file names based on the information provided. Answer the user's question to the best of your ability."
)
def file_organizer_node(state: AgentState) -> AgentState:
    print("--- File Organizer Node ---")
    result = file_organizer_agent.invoke(state) 
    state["previous_agent"] = "Local_File_Organiser"
    return{
        "messages": [
            HumanMessage(content=result["messages"][-1].content, name="Local_File_Organiser")
        ]
    }

local_researcher_agent = create_react_agent(
    llm, tools=[read_file_summary], state_modifier="You are a highly-trained research analyst and can provide the user with the information they need. Use the information from Tool: read_file to compile and organise a comprehensive summary according to user's query. Include the files names information is sourced from. Answer the user's question to the best of your ability. If user requests for json output, it will be arranged by subequent agents, just prepare data in text format."
)
def local_researcher_node(state: AgentState) -> AgentState:
    print("--- Local Researcher ---")
    result = local_researcher_agent.invoke(state) 
    data = result["messages"][-1].content 
    state["local_researcher_data"] = data
    state["previous_agent"] = "Local_Researcher"
    return{
        "messages": [
            HumanMessage(content=result["messages"][-1].content, name="Local_Researcher")
        ]
    }

research_agent = create_react_agent(
    llm,
    tools=[tavily_tool],
    state_modifier="You are a highly-trained researcher. You are tasked with finding the answer to the user's question. Use the following tools: Tavily Search to get updated information to answer query. If user requests for json output, it will be arranged by subequent agents, just prepare data in text format."
)
def research_node(state: AgentState) -> AgentState:
    previous_agent = state.get("previous_agent", "Unknown")
    if previous_agent =="Local_Researcher":
        local_researcher_data = state.get("local_researcher_data", None)
        local_researcher_data = local_researcher_data["messages"][-1].content 
        if local_researcher_data:
            print(f"Using data from Local Researcher: {local_researcher_data}")
    result = research_agent.invoke(state)
    data = result["messages"][-1].content 
    state["researcher_data"] = data
    state["previous_agent"] = "Researcher"
    return{
        "messages": [
            HumanMessage(content=result["messages"][-1].content, name="Researcher")
        ]
    }

builder = StateGraph(AgentState)
builder.add_node("supervisor", supervisor_node)
builder.add_edge(START, "supervisor")
builder.add_node("General_LLM", llm_node)
builder.add_node("Math_LLM", math_node)
builder.add_node("Researcher", research_node)
builder.add_node("Local_File_Organiser", file_organizer_node)
builder.add_node("Local_Researcher", local_researcher_node)
builder.add_node("JSON_Generator", json_node)

config = {"configurable": {"thread_id": "1"}, "recursion_limit": 50}
memory = MemorySaver()

for member in members:
    builder.add_edge(member, "supervisor")
    
builder.add_conditional_edges("supervisor", lambda state: state["next"])

graph = builder.compile(checkpointer=memory)

try:
    graph.get_graph(xray=True).draw_mermaid_png(output_file_path="graph.png")
except Exception:
    pass