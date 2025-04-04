import subprocess
import threading
import sys
import time

def start_grobid():
    try:
        process = subprocess.Popen([
            "docker", "run", "--rm", "--init", "--ulimit", "core=0",
            "-p", "8070:8070", "lfoppiano/grobid:0.8.1"
        ])

        time.sleep(20)

        print("GROBID container started on port 8070")

        return process

    except Exception as e:
        print(f"Error starting GROBID: {e}")
        return None

def run_streamlit():
    try: 
        subprocess.run([sys.executable, "-m", "streamlit", "run", "Frontend/streamlit_main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit: {e}")
        sys.exit(1)

def run_fastapi():
    try:
        subprocess.run(["uvicorn", "Frontend.app:app", "--reload"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running FastAPI: {e}")
        sys.exit(1)

def run_apps():
    streamlit_thread = threading.Thread(target=run_streamlit)
    fastapi_thread = threading.Thread(target=run_fastapi)

    streamlit_thread.start()
    fastapi_thread.start()

    streamlit_thread.join()
    fastapi_thread.join()

if __name__ == "__main__":
    grobid_process = start_grobid()
    
    try:
        run_app = run_apps()
    except KeyboardInterrupt:
        print("Shutting down GROBID and apps...")
        grobid_process.terminate()
        run_apps.terminate()

