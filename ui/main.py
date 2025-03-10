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
API_URL_GET_ENCODING = f"{base_api_url}/get_encoding/"


def get_encoding(input_text):
    """
    Sends a request to the API to detect the encoding of the input text.

    Args:
        input_text (str): The input text to analyze.

    Returns:
        str: The detected encoding of the input text.    

    """
    if input_text:
        payload = {"input_text": input_text}
        response = requests.post(API_URL_GET_ENCODING, json=payload)
        if response.status_code == 200:
            result = response.json()
            return result["encoding"]
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
    else:
        st.warning("Please enter some text to analyze.")


def analyze_text_with_selected_encoding(
    selected_encoding, payload, need_translation, colloquial_to_standard
):
    """
    Sends a request to the API to analyze the input text with the selected encoding.

    Args:
        selected_encoding (str): The selected encoding.
        payload (dict): The payload containing the input text and encoding.
        need_translation (bool): Whether translation is needed.
        colloquial_to_standard (bool): Whether colloquial to standard conversion is needed.

    """
    payload["encoding"] = selected_encoding
    payload["need_translation"] = need_translation
    payload["colloquial_to_standard"] = colloquial_to_standard

    # Make a request to the API
    response = requests.post(API_URL_ANALYZE, json=payload)

    if response.status_code == 200:
        result = response.json()
        output_text = result["output"]
        st.write("Normalized Text:")
        st.write(output_text)
        st.write("Classification Results:")
        st.json(result["result"])
    else:
        st.error(f"Error: {response.status_code} - {response.text}")


# Streamlit UI
st.title("IYAL: Quality Analyzer")

tabs = st.tabs(["Analyze Text", "Convert Legacy to Unicode"])

# Analyze Text tab
with tabs[0]:
    st.subheader("Analyze Text")

    # Input text box
    input_text = st.text_area("Enter text to analyze:")

    # Option selection
    option1 = st.radio(
        "Choose an option:",
        ("Find Automatically", "Select Font Style"),
        key="analyze_option",
    )

    # Encoding selection (only visible if "Select Font Style" is chosen)
    selected_encoding = None
    if option1 == "Select Font Style":
        selected_encoding = st.selectbox("Select a font style:", all_encodings)

    # toggle button for need translation
    need_translation = st.checkbox("Need Translation", key="need_translation")

    colloquial_to_standard = st.checkbox(
        "Colloquial to Standard", key="colloquial_to_standard"
    )

    # Analyze button
    if st.button("Analyze", key="analyze_button"):
        if input_text:
            # Prepare the payload based on the selected option
            auto_encoding = ""
            payload = {"input_text": input_text}
            if selected_encoding:
                analyze_text_with_selected_encoding(
                    selected_encoding,
                    payload,
                    need_translation,
                    colloquial_to_standard,
                )

            else:
                auto_encoding = get_encoding(input_text)
                st.write(f"Auto-detected Font style: {auto_encoding}")
                if not auto_encoding == "legacy_font_not_found":
                    st.session_state.selected_encoding = auto_encoding
                    st.session_state.confirmed = False
                else:
                    analyze_text_with_selected_encoding(
                        auto_encoding,
                        payload,
                        need_translation,
                        colloquial_to_standard,
                    )

    if "selected_encoding" in st.session_state and not st.session_state.confirmed:
        st.session_state.selected_encoding = (
            "anjal2utf8"
            if st.session_state.selected_encoding not in all_encodings
            else st.session_state.selected_encoding
        )
        selected_encoding = st.selectbox(
            "Select an Font Style:",
            all_encodings,
            index=all_encodings.index(st.session_state.selected_encoding),
        )
        if st.button("Confirm Encoding", key="confirm_encoding_button"):
            st.session_state.confirmed = True
            analyze_text_with_selected_encoding(
                selected_encoding,
                {"input_text": input_text, "encoding": selected_encoding},
                need_translation,
                colloquial_to_standard,
            )
    elif "confirmed" in st.session_state and st.session_state.confirmed:
        analyze_text_with_selected_encoding(
            st.session_state.selected_encoding,
            {"input_text": input_text, "encoding": st.session_state.selected_encoding},
            need_translation,
            colloquial_to_standard,
        )

# Convert Legacy to Unicode tab
with tabs[1]:
    st.subheader("Convert Legacy to Unicode")

    # Input text box
    input_text = st.text_area("Enter text to convert:")

    option2 = st.radio(
        "Choose an option:",
        ("Find Automatically", "Select Font Style"),
        key="convert_option",
    )

    # Encoding selection (only visible if "Select Font Style" is chosen)
    selected_encoding = None
    if option2 == "Select Font Style":
        selected_encoding = st.selectbox("Select a Font Style:", all_encodings)

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
