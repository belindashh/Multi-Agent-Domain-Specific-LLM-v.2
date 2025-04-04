import streamlit as st
import requests
from grobid_client.grobid_client import GrobidClient
import os
import time
import json
import pandas as pd

API_URL = "http://127.0.0.1:8000/api/"
UPDATE_FILE_URL = API_URL + "update_file"
GPT_URL = API_URL + "query"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def log_message(sender: str, message: str):
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.chat_history.append({"sender": sender, "message": message, "timestamp": timestamp})

def is_latex(chunk):
    latex_keywords = ["\\frac", "_", "^", "\\cdot", "\\text", "\\times", "\\sum", "\\int"]
    return any(symbol in chunk for symbol in latex_keywords) or "$" in chunk

    
def get_gpt_response(query):
    payload = {"query": query}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(GPT_URL, json=payload, headers=headers)
        return (response.json()).get("response")
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to FastAPI server. Make sure it is running."
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"
    
    
def export_chat_history():
    df = pd.DataFrame(st.session_state.chat_history)
    csv_data = df.to_csv(index=False)
    st.download_button(
        label=f"📥 Export  Chat History as CSV",
        data=csv_data,
        file_name=f"chat_history.csv",
        mime="text/csv"
    )

def get_latest_csv():
    DATA_DIR = "C:/Users/User/school/ISM V.2/CSV_Files/output.csv"
    if os.path.exists(DATA_DIR):
        return DATA_DIR
    else:
        return 0

def export_csv():
    latest_csv = get_latest_csv()

    if latest_csv:
        st.success(f"New CSV detected: {os.path.basename(latest_csv)}")
        
        df = pd.read_csv(latest_csv)
        # st.dataframe(df) 
        
        with open(latest_csv, "rb") as f:
            csv_bytes = f.read()
        st.download_button(
            label="Download CSV",
            data=csv_bytes,
            file_name=os.path.basename(latest_csv),
            mime="text/csv"
        )



def main():
    st.title("Chatbot & File Upload")

    tab1, tab2 = st.tabs(["Chatbot", "Upload PDF"])

    with tab1:
        st.markdown("""
            <style>
                .stTextInput, .stTextArea {
                    position: fixed;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    width: 60%;
                    z-index: 100;
                }
            </style>
        """, unsafe_allow_html=True)

        st.subheader("Chat with AI")

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        input_placeholder = st.empty()
        prompt = input_placeholder.chat_input("What is up?")

        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            response_text = ""
            response = get_gpt_response(prompt)
            if response == None: 
                response_text = response
            else:
                response = response.replace("\\[\n", "\\[")
                response = response.replace("\n\\]", "\\]")
                response = response.replace("\\(", r"\(").replace("\\)", r"\)")
                response_chunk = response.splitlines()
                with st.chat_message("assistant"):
                    for line in response_chunk:
                        if "\\["in line:
                            line = line.replace("\\[", "$$")
                        if "\\]" in line:
                            line = line.replace("\\]", "$$")
                        if "\\("in line:
                            line = line.replace("\\(", "$$")
                        if "\\)" in line:
                            line = line.replace("\\)", "$$")
                        st.markdown(line)
                        response_text += f"\n{line}"

            log_message(prompt, response_text)

            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.rerun()

        export_chat_history()
        export_csv()
    
    with tab2:
        st.subheader("Upload & Process PDF")
        uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

        if uploaded_file is not None:
            temp_path = f"./temp_files/temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            client = GrobidClient(config_path="config.json", timeout=300)
            client.process("processFulltextDocument", "temp_files", output="./temp_files/", consolidate_citations=True , tei_coordinates=True, force=True)
            tei_file = temp_path.replace(".pdf", ".grobid.tei.xml")
            counter=0
            while not os.path.exists(tei_file) and counter != 300:
                print("⏳ Waiting for GROBID to process the document...", end="\r", flush=True)
                time.sleep(10)
                counter += 10
            try:
                payload = {"query": tei_file, 
                           "file_name": uploaded_file.name}
                headers = {'Content-Type': 'application/json'}
                st.subheader("Extracting text using GROBID...")
                response = requests.put(UPDATE_FILE_URL, json=payload, headers=headers)
                time.sleep(30)
                st.success(f"File uploaded: {uploaded_file.name}")
                os.remove(temp_path)
                if os.path.exists(tei_file):
                    os.remove(tei_file)
            except:
                st.error(f"File upload failed: {uploaded_file.name}")


if __name__ == "__main__":
    main()
