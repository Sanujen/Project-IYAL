import os
from dotenv import load_dotenv
import streamlit as st
import requests

# Load environment variables
load_dotenv()

# Define the API endpoint
API_URL = f"{os.getenv('BASE_API_URL')}/analyze/"

# Streamlit UI
st.title("Quality Analyzer")

# Input text box
input_text = st.text_area("Enter text to analyze:")

# Analyze button
if st.button("Analyze"):
    if input_text:
        # Make a request to the API
        response = requests.post(API_URL, json={"input_text": input_text})
        
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