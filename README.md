# Multi-Agent-Domain-Specific-LLM

**Multi-Agent-Domain-Specific-LLM** is a web-based application designed to monitor and analyze global disruption events such as cyber-attacks, supply chain disruptions, natural disasters, and other business-critical incidents. It allows users to visualize trends, perform keyword analysis, and filter events by various criteria like time range, disruption type, and severity.

---

## 🚀 Features

- **Multi-Agent**: LLM routes to different agents based on the query type (General, Math, Local Database File Search, Local Database Information Search, Table Building)
- **Domain Specific**: LLM can search through local database to find relevant informations
- **PDF Import**: Allows add on to local database through importing PDF

---

## 🛠️ Technologies Used

### Backend
- **MySQL** (Database)
- **OpenAI API**: For developing each LLM agent
- **Langgraph**: To develop graph workflow for dynamic routing of LLM Agents

### Frontend
- **Streamlit**
- **FastAPI** for routings of backend system to frontend

---

## ⚙️ Installation and Setup

Follow these steps to set up the project on your local machine:

### Prerequisites
- **XAMPP**, **Docker** and **wsl2** installed
- **MySQL** instance running locally 
- API keys for:
  - [OpenAI API](https://platform.openai.com/) to be filled in OPENAI_API_KEY in `.env` file
  - [Tavily API](https://tavily.com/) to be filled in TAVILY_API_KEY in `.env` file
  ```env
   OPENAI_API_KEY=<Your OpenAI Key>
   TAVILY_API_KEY=<Your TAVILY Key>
   ```

---

### 1. Clone the Repository

```bash
git clone https://github.com/belindashh/Multi-Agent-Domain-Specific-LLM.git
cd Multi-Agent-Domain-Specific-LLM
```
---

### 2. Start GROBID
This is the lightweight version which has the best runtime performance, memory usage and Docker image size but accuracy is lesser:
```bash
docker run --rm --init --ulimit core=0 -p 8070:8070 lfoppiano/grobid:0.8.1
```

If accuracy is important and space allows, run full image instead.
```bash
docker run --rm --gpus all --init --ulimit core=0 -p 8070:8070 grobid/grobid:0.8.1
```
This is configured in `main.py` file. Edit Line 9-10 as necessary.

### 3. Create Virtual Env and Install Requirements.txt
```bash
pip install -r requirements.txt
```

### 4. Create Local Databases in MySQL
```bash
python Setup/setup_localDB.py
```

Creates new databases for local database and chat history. Only erases existing chat histories unless uncomment:
```bash
# cursor.execute(f"DROP TABLE IF EXISTS {Data_TB}")
```

### 4. Mass File Setup for Local Database

1. Navigate to the `Mass Datafile Setup` folder:

2. Store all PDF files intended in `pdf_input` folder:

3. Run read_pdf.ipynb (Ensure all information is stated clearly - especially input file and output file):
```bash
client.process("processFulltextDocument", "pdf_input", output="../tei_output", consolidate_citations=True, tei_coordinates=True, force=True, n=15)
```
This process may need to be repeated as process may timeout for certain PDF files. 

4. Run save_to_sql.ipynb to save file to MySQL. Take note:

Enter API Key here for OpenAI
   ```bash
   client = OpenAI(api_key= "Enter API key")
   ```

Ensure XML file for reading for upload is correct
   ```bash
   folder_path = "../tei_output" 
   ```

Ensure Database information is correct:
```bash
   conn = mysql.connector.connect(user='root',  
        password='',  
        host='localhost',
        database='ism') 
```
---

### 5. Run Chatbot

1. Run the following command in the main folder:
```bash
   python main.py
```
If GROBID is already running, ignore error. Otherwise main.py will run GROBID.

2. The frontend will run at `http://localhost:8501`.


## 🌐 API Keys Management

- Replace placeholders in the `.env` file with your API keys:
  - `OPENAI_API_KEY` for LLM Agent Creation
  - `TAVILY_API_KEY` for web search

---

## 👨‍💻 Author

Developed by **[belindashh](https://github.com/belindashh)**.
