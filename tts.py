import os
import re
import pdfplumber
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play, save
import io

class PDFToSpeech:
    def __init__(self):
        load_dotenv()
        
        # Initialize ElevenLabs client
        self.elevenlabs = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
        )
        
        # Create output directory
        self.output_dir = Path("audio_output")
        self.output_dir.mkdir(exist_ok=True)
    #     self.available_voices = self.get_voices()
    
    # def get_voices(self):
    #     """Get available voices from ElevenLabs"""
    #     try:
    #         print("🔍 Testing ElevenLabs connection...")
    #         voices = self.elevenlabs.voices.get_all()
    #         print("\n🎤 Available ElevenLabs voices:")
    #         for voice in voices.voices:
    #             print(f"   • {voice.name} (ID: {voice.voice_id})")
    #         return voices.voices
    #     except Exception as e:
    #         print(f"❌ Error fetching voices: {e}")
    #         print("💡 Troubleshooting tips:")
    #         print("   1. Check your API key is correct")
    #         print("   2. Verify your .env file is in the same directory")
    #         print("   3. Make sure your ElevenLabs account is active")
    #         return []
    
    def extract_page_text(self, pdf_path, page_number=1):
        """Extract text from a specific page of the PDF"""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file '{pdf_path}' not found!")
        
        print(f"\n📖 Extracting text from page {page_number} of '{pdf_path.name}'...")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                print(f"   📄 PDF has {total_pages} total pages")
                
                if page_number > total_pages:
                    raise IndexError(f"Page {page_number} not found. PDF has {total_pages} pages.")
                
                page = pdf.pages[page_number - 1]
                text = page.extract_text()
                
                if not text:
                    print("⚠️  Warning: No text found on this page!")
                    return ""
                
                print(f"   ✅ Extracted {len(text)} characters from page {page_number}")
                return text
                
        except Exception as e:
            print(f"❌ Error extracting with pdfplumber: {e}")
            return ""
    
    def clean_text(self, text):
        if not text:
            return ""
        
        print("\n🧹 Cleaning extracted text...")
        
        # Remove extra whitespace and normalize line breaks
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers
        text = re.sub(r'^\d+\s*', '', text)  # Page numbers at start
        text = re.sub(r'\s*\d+$', '', text)  # Page numbers at end
        text = re.sub(r'^(Chapter \d+|CHAPTER \d+|Life 3\.0)', '', text, flags=re.IGNORECASE)
        
        # Fix common PDF extraction issues
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between joined words
        text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)  # Space between letters and numbers
        text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)  # Space between numbers and letters
        
        # Clean up punctuation
        text = re.sub(r'\.{3,}', '...', text)  # Multiple dots to ellipsis
        text = re.sub(r'-{2,}', ' -- ', text)  # Multiple dashes
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([,.!?;:])\s*', r'\1 ', text)  # Add single space after punctuation
        
        # Remove unwanted characters but keep essential punctuation
        text = re.sub(r'[^\w\s.,!?;:\'"()[\]{}\-–—]', '', text)
        
        # Fix sentence capitalization
        sentences = re.split(r'(?<=[.!?])\s+', text)
        cleaned_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 1:
                # Capitalize first letter
                sentence = sentence[0].upper() + sentence[1:]
                cleaned_sentences.append(sentence)
        
        cleaned_text = ' '.join(cleaned_sentences)
        
        # Final cleanup
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        print(f"   ✅ Text cleaned: {len(cleaned_text)} characters")
        return cleaned_text
    
    def text_to_speech(self, text, voice_id, play_audio=True, save_audio=True):
        """Convert text to speech using ElevenLabs SDK"""
        if not text.strip():
            raise ValueError("No text provided for conversion!")
        
        if not voice_id:
            raise ValueError("Voice ID is required!")
        
        print(f"🔊 Converting {len(text)} characters to speech...")
        
        try:
            # Convert text to speech
            audio = self.elevenlabs.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            
            # Save audio file if requested
            audio_path = None
            if save_audio:
                filename = f"life3_page_audio.mp3"
                audio_path = self.output_dir / filename
                
                save(audio, str(audio_path))
                print(f"💾 Audio saved to: {audio_path}")
            
            # Play audio if requested
            if play_audio:
                print("🔊 Playing audio...")
                play(audio)
            
            return audio_path
            
        except Exception as e:
            print(f"❌ Error converting text to speech: {e}")
            return None
    
    def process_pdf_page(self, pdf_path, page_number=1, voice_id=None, play_audio=True):
        """Complete pipeline: extract page, clean text, and convert to speech"""
        print(f"🚀 Starting PDF to Speech conversion...")
        print(f"📁 PDF: {pdf_path}")
        
        try:
            raw_text = self.extract_page_text(pdf_path, page_number)
            if not raw_text:
                return None
            
            cleaned_text = self.clean_text(raw_text)
            if not cleaned_text:
                return None
            
            # Save cleaned text for review
            text_file = self.output_dir / f"page_{page_number}_text.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            print(f"📝 Cleaned text saved: {text_file}")
            
            # Step 3: Convert to speech
            audio_path = self.text_to_speech(
                text=cleaned_text, 
                voice_id=voice_id, 
                play_audio=play_audio
            )
            
            return audio_path
            
        except Exception as e:
            print(f"❌ Error in pipeline: {e}")
            return None

def main():
    """Main execution function"""
    print("🎧 PDF to Audiobook Converter using ElevenLabs")
    print("=" * 50)
    
    converter = PDFToSpeech()
    
    # Configuration
    pdf_file = "life_3_0.pdf"  
    page_to_convert = 20       
    
    voice_id = "JBFqnCBsd6RMkjVDRZzb" 

    # Check if PDF exists
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file '{pdf_file}' not found!")
        return
    
    # Process the page
    result = converter.process_pdf_page(
        pdf_path=pdf_file,
        page_number=page_to_convert,
        voice_id=voice_id,
        play_audio=False
    )

    if result:
        print(f"\n🎉 Success! Your audiobook page is ready!")
        print(f"🔊 Audio file: {result}")
        print(f"📁 All files saved in: {converter.output_dir}")
    else:
        print(f"\n❌ Conversion failed. Check the error messages above.")

if __name__ == "__main__":
    main()