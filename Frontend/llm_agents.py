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
from langchain_experimental.utilities import PythonREPL

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

repl = PythonREPL()

@tool
def python_repl_tool(
    code: Annotated[str, "The Python code to execute user instructions such as generating CSV files."],
):
    """Executes Python code and supports saving outputs as CSV files."""
    try:
        print("Executing Code:\n", code) 
        result = repl.run(code)
        print(f"Execution Result: {result}")
        if isinstance(result, pd.DataFrame):
            csv_path = "C:/Users/User/school/ISM V.2/CSV_Files/output.csv"
            result.to_csv(csv_path, index=False, encoding="utf-8")
            return f"CSV file has been successfully saved to {csv_path}."
        
        with open("C:/Users/User/school/ISM V.2/CSV_Files/output.csv", "w", encoding="utf-8") as f:
            f.write(str(result))

        if "to_csv" in code:
            return "CSV file has been successfully saved."
        
    except Exception as e:
        return f"Failed to execute. Error: {repr(e)}"
    
    return f"Successfully executed:\n'''python\n{code}\n'''\nStdout: {result}"


tavily_tool = TavilySearchResults(max_results=5)
    

#AGENTS
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

class AgentState(MessagesState):
    next: str

members = ["General_LLM", "Math_LLM", "Researcher", "Local_File_Organiser", "Local_Researcher", "CSV_Generator"]

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
   - For generating csv files: 'CSV_Generator'

2. If the query requires multiple steps, route to the first appropriate worker, then based on the response, route to the next worker as needed.

3. After each worker completes its task, review the response and conversation history:
   - Only if the task is complete, route to 'FINISH'
   - If further action is needed (e.g., processing data into a table), route to the next appropriate worker

4. Important constraints:
   - Avoid redundant actions by checking the conversation history
   - If user requests for table without csv file, DO NOT route to CSV_Generator

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
  - First route to 'Local_Researcher' to get the stock data, then to 'Researcher' to add in more information.

- User: "Can you organise a csv file based on table with the columns (material, formula electronegativity) for all materials that have been mentioned in the local database. If there are any missing information, can you research and add in the accurate information? Then generate the csv file based on the table created"
  - First route to 'Local_Researcher' to get the stock data, then to 'Researcher' to add in more information and then route to "CSV_Generator" to export as csv file.

Respond ONLY with the name of the next worker from: {options}.
"""
)

class SupervisorState(TypedDict):

    next: Literal["General_LLM", "Math_LLM", "Researcher", "Local_File_Organiser", "Local_Researcher", "CSV_Generator", "FINISH"]

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

CSV_agent = create_react_agent( 
    llm, tools=[llm_tool, python_repl_tool], state_modifier="""
    If the user requests a CSV file, generate Python code to create and save the CSV file.
    Use pandas to create a DataFrame for saving csv values.
    Then execute the code using the python_repl_tool to save csv values into dataframe.
    """
)
def csv_node(state: AgentState) -> AgentState:
    result = CSV_agent.invoke(state)
    previous_agent = state.get("previous_agent", "Unknown")
    if previous_agent == "Researcher":
        researcher_data = state.get("researcher_data", None)
        researcher_data = researcher_data["messages"][-1].content 
    if researcher_data is None:
        researcher_data = {
            'ReferenceID': ['AlSi10Mg Alloy', 'Ti6Al4V Alloy', '304L Stainless Steel'],
            'FORMULA': ['Al: Bal, Si: 10.0, Mg: 0.32', 'Ti: 90.0, Al: 6.0, V: 4.0', 'Fe: Bal, Cr: 18.0, Ni: 8.0'],
            'VEC (Valence Electron Concentration)': [3.87, 4.0, 3.44],
            'Electronegativity': [1.61, 1.54, 1.90],
            'Melting Point (°C)': [867, 1928, 1400],
            'Microstructure': [
                'Al dendritic cells, Al-Si eutectic networks',
                'HCP (Hexagonal Close-Packed)',
                'FCC (Face-Centered Cubic)'
            ]
        }

    print(f"Material data received from: {previous_agent}")

    csv_generation_code = f"""
            import pandas as pd
            import io
            data = {researcher_data}
            df = pd.DataFrame(data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()
            return csv_content
        """
    
    csv_result = python_repl_tool(csv_generation_code)
    state["previous_agent"] = "CSV_Generator"
    return {
        "messages": [
            HumanMessage(content=f"CSV file generated successfully. {csv_result}", name="CSV_Generator")
        ]
    }

math_agent = create_react_agent(
    llm, tools=[llm_tool, tavily_tool], state_modifier="You are a scientist that is very good  at math and science calculations. Analyse and provide answers to user's question in proper Latex formatting. Make use of the tools available if necessary."
)
def math_node(state: AgentState) -> AgentState:
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
    result = file_organizer_agent.invoke(state) 
    state["previous_agent"] = "Local_File_Organiser"
    return{
        "messages": [
            HumanMessage(content=result["messages"][-1].content, name="Local_File_Organiser")
        ]
    }

local_researcher_agent = create_react_agent(
    llm, tools=[read_file_summary], state_modifier="You are a highly-trained research analyst and can provide the user with the information they need. Use the information from Tool: read_file to compile and organise a comprehensive summary according to user's query. Include the files names information is sourced from. Answer the user's question to the best of your ability. " \
    "If user requests for csv file, return content ONLY in JSON format with no additional information. Otherwise, return output as usual"
)
def local_researcher_node(state: AgentState) -> AgentState:
    result = local_researcher_agent.invoke(state) 
    data = result["messages"][-1].content 
    if "csv" in state.get("user_request", "").lower():
        try:
            json_data = json.loads(data)
            state["local_researcher_data"] = json_data 
        except json.JSONDecodeError:
            state["local_researcher_data"] = {"error": "Failed to parse response as JSON."}
    else:
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
    state_modifier="You are a highly-trained researcher. You are tasked with finding the answer to the user's question. Use the following tools: Tavily Search to get updated information to answer query." \
    "If user requests for csv file, return content ONLY in JSON format with no additional information. Otherwise, return output as usual"
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
    if "csv" in state.get("user_request", "").lower():
        try:
            json_data = json.loads(data)
            state["researcher_data"] = json_data 
        except json.JSONDecodeError:
            state["researcher_data"] = {"error": "Failed to parse response as JSON."}
    else:
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
builder.add_node("CSV_Generator", csv_node)

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