import os
from dotenv import load_dotenv
import streamlit as st
import requests

# Load environment variables
load_dotenv()

all_encodings = [
    "anjal2utf8",
    "bamini2utf8",
    "boomi2utf8",
    "dinakaran2utf8",
    "dinathanthy2utf8",
    "kavipriya2utf8",
    "murasoli2utf8",
    "mylai2utf8",
    "nakkeeran2utf8",
    "roman2utf8",
    "tab2utf8",
    "tam2utf8",
    "tscii2utf8",
    "indoweb2utf8",
    "koeln2utf8",
    "libi2utf8",
    "oldvikatan2utf8",
    "webulagam2utf8",
    "auto2utf8",
    "dinamani2utf8",
    "pallavar2utf8",
    "diacritic2utf8",
    "shreelipi2utf8",
    "softview2utf8",
    "tace2utf8",
    "vanavil2utf8",
]

# Define the API endpoint
base_api_url = os.getenv("BASE_API_URL")
API_URL_ANALYZE = f"{base_api_url}/analyze/"
API_URL_LEGACY2UNICODE = f"{base_api_url}/legacy2unicode/"

# Streamlit UI
st.title("Quality Analyzer")

tabs = st.tabs(["Analyze Text", "Convert Legacy to Unicode"])

# Analyze Text tab
with tabs[0]:
    st.subheader("Analyze Text")

    # Input text box
    input_text = st.text_area("Enter text to analyze:")

    # Option selection
    option1 = st.radio("Choose an option:", ("Find Automatically",
                       "Select Encoding"), key="analyze_option")

    # Encoding selection (only visible if "Select Encoding" is chosen)
    selected_encoding = None
    if option1 == "Select Encoding":
        selected_encoding = st.selectbox("Select an encoding:", all_encodings)

    # Analyze button
    if st.button("Analyze", key="analyze_button"):
        if input_text:
            # Prepare the payload based on the selected option
            payload = {"input_text": input_text}
            if selected_encoding:
                payload["encoding"] = selected_encoding

            # Make a request to the API
            response = requests.post(API_URL_ANALYZE, json=payload)

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

# Convert Legacy to Unicode tab
with tabs[1]:
    st.subheader("Convert Legacy to Unicode")

    # Input text box
    input_text = st.text_area("Enter text to convert:")

    option2 = st.radio("Choose an option:", ("Find Automatically",
                       "Select Encoding"), key="convert_option")

    # Encoding selection (only visible if "Select Encoding" is chosen)
    selected_encoding = None
    if option2 == "Select Encoding":
        selected_encoding = st.selectbox("Select an encoding:", all_encodings)

    # Convert button
    if st.button("Convert", key="convert_button"):
        if input_text:
            # Prepare the payload based on the selected option
            payload = {"input_text": input_text}
            if selected_encoding:
                payload["encoding"] = selected_encoding

            # Make a request to the API
            response = requests.post(API_URL_LEGACY2UNICODE, json=payload)

            if response.status_code == 200:
                result = response.json()
                st.write("Converted Text:")
                st.write(result["output"])
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        else:
            st.warning("Please enter some text to convert.")
