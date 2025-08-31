import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

from tts import PDFToSpeech
from clone_speech import PDFToSpeechWithVoiceCloning

# Load env variables
load_dotenv()
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")

st.set_page_config(page_title="VoiceClone-PDF-Audiobook", layout="wide")

st.title("🎧 VoiceClone-PDF-Audiobook")
st.write("Convert PDF pages into audiobooks using ElevenLabs or Coqui TTS, with optional voice cloning.")

# Sidebar options
engine = st.sidebar.selectbox("Choose TTS Engine", ["ElevenLabs", "Coqui TTS"])
pdf_file = st.file_uploader("📂 Upload PDF", type=["pdf"])
page_number = st.number_input("Page Number", min_value=1, value=1)

# Temporary save dir
os.makedirs("uploads", exist_ok=True)

if pdf_file:
    pdf_path = Path("uploads") / pdf_file.name
    with open(pdf_path, "wb") as f:
        f.write(pdf_file.read())

    if st.button("Extract & Convert"):
        if engine == "ElevenLabs":
            converter = PDFToSpeech()
            voice_id = st.text_input("Enter ElevenLabs Voice ID", "JBFqnCBsd6RMkjVDRZzb")

            if voice_id:
                audio_path = converter.process_pdf_page(pdf_path, page_number, voice_id, play_audio=False)
                if audio_path:
                    st.success("Audio generated successfully!")
                    st.audio(str(audio_path))

        elif engine == "Coqui TTS":
            converter = PDFToSpeechWithVoiceCloning()
            text_file = converter.extract_page_text(pdf_path, page_number)
            st.info("Use Voice Cloning section below to generate narration.")

# Voice cloning section
st.header("🎭 Voice Cloning (Coqui TTS)")
ref_audio = st.file_uploader("Upload Reference Voice (wav/mp3)", type=["wav", "mp3"])
text_file = st.file_uploader("Upload Extracted Text File", type=["txt"])

if ref_audio and text_file and st.button("Clone Voice & Generate Audio"):
    ref_path = Path("uploads") / ref_audio.name
    txt_path = Path("uploads") / text_file.name

    with open(ref_path, "wb") as f:
        f.write(ref_audio.read())
    with open(txt_path, "wb") as f:
        f.write(text_file.read())

    cloner = PDFToSpeechWithVoiceCloning()
    result = cloner.process_text_with_voice_clone(str(txt_path), str(ref_path), language="en")

    if result:
        st.success("Cloned voice audio generated!")
        st.audio(str(result))
