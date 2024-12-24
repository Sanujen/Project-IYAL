import os
from dotenv import load_dotenv
import streamlit as st
import requests

# Load environment variables
load_dotenv()

all_encodings = [
    "anjal2unicode",
    "bamini2unicode",
    "boomi2unicode",
    "dinakaran2unicode",
    "dinathanthy2unicode",
    "kavipriya2unicode",
    "murasoli2unicode",
    "mylai2unicode",
    "nakkeeran2unicode",
    "roman2unicode",
    "tab2unicode",
    "tam2unicode",
    "tscii2unicode",
    "indoweb2unicode",
    "koeln2unicode",
    "libi2unicode",
    "oldvikatan2unicode",
    "webulagam2unicode",
    "auto2unicode",
    "dinamani2unicode",
    "pallavar2unicode",
    "diacritic2unicode",
    "shreelipi2unicode",
    "softview2unicode",
    "tace2unicode",
    "vanavil2unicode",
]

# Define the API endpoint
API_URL = f"{os.getenv('BASE_API_URL')}/analyze/"

# Streamlit UI
st.title("Quality Analyzer")

# Input text box
input_text = st.text_area("Enter text to analyze:")

# Option selection
option = st.radio("Choose an option:", ("Default", "Select Encoding"))

# Encoding selection (only visible if "Select Encoding" is chosen)
selected_encoding = None
if option == "Select Encoding":
    selected_encoding = st.selectbox("Select an encoding:", all_encodings)

# Analyze button
if st.button("Analyze"):
    if input_text:
        # Prepare the payload based on the selected option
        payload = {"input_text": input_text}
        if selected_encoding:
            payload["encoding"] = selected_encoding
        
        # Make a request to the API
        response = requests.post(API_URL, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            st.write("Normalized Text:")
            st.write(result["output"])
            st.write("Classification Results:")
            st.json(result["result"])
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
    else:
        st.warning("Please enter some text to analyze.")