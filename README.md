# Project-IYAL
CSE Final Year Research and Development Project

## Steps to start the development
1. Clone the repository
2. Create and activate a virtual environment
```bash
python3 -m venv .venv
# or
python -m venv .venv

.venv\Scripts\activate
```
3. Install the requirements
```bash
pip install -r requirements.txt
```
4. Create a branch from development branch
```bash
git checkout development
git pull origin development
git checkout -b <name of the dev>/dev/<feature>
```

## .env file
1. Create a `.env` file in the root directory
2. Add the following environment variables
```env
BASE_API_URL="http://127.0.0.1:8000"
```

## FastAPI
1. Run the FastAPI server
```bash
# you may need to,
pip install "fastapi[standard]"

fastapi dev .\server\server.py

# The default port is 8000
# if you want to specify the port
fastapi dev .\server\server.py --port 8000
```

## Streamlit
1. Run the Streamlit server
```bash
streamlit run .\streamlit\app.py

# The default port is 8501
# if you want to specify the port
streamlit run .\streamlit\app.py --server.port 8989
```