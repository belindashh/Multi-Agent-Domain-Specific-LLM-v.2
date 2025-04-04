from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from Frontend.utils import *
from bs4 import BeautifulSoup
from Frontend.llm_agents import graph
from langchain_core.messages import HumanMessage
load_dotenv()

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Default Page"}

class QueryRequest(BaseModel):
    query: str

class UploadFile(BaseModel):
    query: str
    file_name: str
    

@app.post("/api/query")
async def query_agent(request: QueryRequest):
    agent_state = {
        "messages": [HumanMessage(content=request.query)]
    }
    try:
        async for output in graph.astream(agent_state, config={"configurable": {"thread_id": "1"}}):
            print("Output:", output)
            if isinstance(output, dict):
                for key, value in output.items():
                    if isinstance(value, dict) and "messages" in value and value["messages"]:
                        final_response = value["messages"][-1].content

            if "supervisor" in output and "next" in output["supervisor"] and output["supervisor"]["next"] == "__end__":
                return {"response": final_response}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

@app.put("/api/update_file")
async def update_file2sql(request: UploadFile): 
    tei_file = request.query
    main_file = request.file_name
    with open(tei_file, "r", encoding="utf-8") as f:
        tei_content = f.read()

    soup = BeautifulSoup(tei_content, "xml")
    for ref in soup.find_all("ref"):
        ref.unwrap()
    desc_text = soup.fileDesc.get_text(separator="\n", strip=True)
    title_text = soup.title.get_text(separator="\n", strip=True)
    abstract_text = soup.abstract.get_text(separator="\n", strip=True)
    body_text = soup.body.get_text(separator="\n", strip=True)
    add_file2database(main_file, desc_text, title_text, abstract_text, body_text)
