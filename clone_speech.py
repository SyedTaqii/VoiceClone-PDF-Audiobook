import os
import re
import shutil
from pathlib import Path
import torch
import torchaudio
import numpy as np
from TTS.api import TTS
import soundfile as sf

class PDFToSpeechWithVoiceCloning:
    def __init__(self):
        self.output_dir = Path("audio_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Check if CUDA is available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 Using device: {self.device}")
        
        # Clear corrupted model cache and setup TTS
        self.setup_tts_model()
    
    def clear_model_cache(self):
        """Clear potentially corrupted model cache"""
        try:
            import tempfile
            cache_dir = Path.home() / ".cache" / "tts"
            if cache_dir.exists():
                print("🧹 Clearing model cache...")
                shutil.rmtree(cache_dir)
                print("✅ Cache cleared")
        except Exception as e:
            print(f"⚠️  Could not clear cache: {e}")
    
    def setup_tts_model(self):
        """Initialize Coqui TTS model for voice cloning"""
        print("🚀 Setting up Coqui TTS model for voice cloning...")
        
        try:
            # Clear cache first to avoid corruption
            self.clear_model_cache()
            
            # Use YourTTS model as you specified
            model_name = "tts_models/multilingual/multi-dataset/your_tts"
            print(f"📥 Loading model: {model_name}")
            
            self.tts = TTS(model_name=model_name, progress_bar=True)
            if self.device == "cuda":
                self.tts = self.tts.to(self.device)
            
            print("✅ YourTTS model loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading TTS model: {e}")
            raise
    
    def load_text_from_file(self, text_file_path):
        """Load already extracted and cleaned text from file"""
        text_path = Path(text_file_path)
        
        if not text_path.exists():
            raise FileNotFoundError(f"Text file '{text_path}' not found!")
        
        print(f"\n📖 Loading text from: {text_path.name}")
        
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            
            if not text:
                print("⚠️  Warning: Text file is empty!")
                return ""
            
            print(f"   ✅ Loaded {len(text)} characters from text file")
            return text
            
        except Exception as e:
            print(f"❌ Error loading text file: {e}")
            return ""
    
    def prepare_reference_audio(self, audio_path):
        """Prepare reference audio for voice cloning with better format handling"""
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Reference audio file '{audio_path}' not found!")
        
        print(f"\n🎤 Preparing reference audio: {audio_path.name}")
        
        try:
            # Try multiple methods to load audio
            waveform = None
            sample_rate = None
            
            # Method 1: Try torchaudio with different backends
            try:
                waveform, sample_rate = torchaudio.load(str(audio_path))
                print("   ✅ Loaded with torchaudio")
            except Exception as e1:
                print(f"   ⚠️  torchaudio failed: {e1}")
                
                # Method 2: Try with soundfile
                try:
                    import soundfile as sf
                    audio_data, sample_rate = sf.read(str(audio_path))
                    waveform = torch.tensor(audio_data).unsqueeze(0)
                    print("   ✅ Loaded with soundfile")
                except Exception as e2:
                    print(f"   ⚠️  soundfile failed: {e2}")
                    
                    # Method 3: Try converting with ffmpeg first
                    try:
                        converted_path = self.convert_audio_format(audio_path)
                        waveform, sample_rate = torchaudio.load(str(converted_path))
                        print("   ✅ Loaded after format conversion")
                    except Exception as e3:
                        print(f"   ❌ All methods failed: {e3}")
                        return None
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
                print("   🔄 Converted to mono")
            
            # Resample to 22050 Hz if needed
            if sample_rate != 22050:
                resampler = torchaudio.transforms.Resample(sample_rate, 22050)
                waveform = resampler(waveform)
                sample_rate = 22050
                print(f"   🔄 Resampled to {sample_rate} Hz")
            
            # Check audio length
            duration = waveform.shape[1] / sample_rate
            print(f"   ⏱️  Audio duration: {duration:.2f} seconds")
            
            if duration < 3:
                print("⚠️  Warning: Audio is very short. For better cloning, use 10+ seconds")
            elif duration > 120:
                print("⚠️  Warning: Audio is very long. Consider trimming to 30-60 seconds")
            
            # Save as compatible WAV file
            output_path = self.output_dir / f"processed_{audio_path.stem}.wav"
            torchaudio.save(str(output_path), waveform, sample_rate)
            print(f"   💾 Processed audio saved: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            print(f"❌ Error preparing reference audio: {e}")
            return None
    
    def convert_audio_format(self, audio_path):
        """Convert audio to WAV format using ffmpeg"""
        try:
            import subprocess
            output_path = self.output_dir / f"converted_{audio_path.stem}.wav"
            
            cmd = [
                'ffmpeg', '-i', str(audio_path), 
                '-ar', '22050', '-ac', '1', '-y',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"   ✅ Converted to: {output_path}")
                return output_path
            else:
                print(f"   ❌ ffmpeg failed: {result.stderr}")
                return None
                
        except FileNotFoundError:
            print("   ❌ ffmpeg not found. Please install ffmpeg.")
            return None
        except Exception as e:
            print(f"   ❌ Conversion error: {e}")
            return None
    
    def clone_voice_and_generate(self, text, reference_audio_path, language="en", save_audio=True):
        """Clone voice from reference audio and generate speech"""
        if not text.strip():
            raise ValueError("No text provided for conversion!")
        
        # Prepare reference audio
        ref_audio_path = self.prepare_reference_audio(reference_audio_path)
        if ref_audio_path is None:
            return None
        
        print(f"\n🎭 Cloning voice and generating speech...")
        print(f"📝 Text length: {len(text)} characters")
        print(f"🗣️  Reference audio: {Path(reference_audio_path).name}")
        
        try:
            # Split text into smaller chunks if too long (XTTS has limits)
            max_chars = 250  # Conservative limit for XTTS
            text_chunks = self.split_text_into_chunks(text, max_chars)
            
            print(f"📊 Split text into {len(text_chunks)} chunks")
            
            audio_segments = []
            
            for i, chunk in enumerate(text_chunks):
                if not chunk.strip():
                    continue
                
                print(f"🔄 Processing chunk {i+1}/{len(text_chunks)}...")
                
                # Generate speech with cloned voice
                wav = self.tts.tts(
                    text=chunk,
                    speaker_wav=ref_audio_path,
                    language=language
                )
                
                audio_segments.append(wav)
            
            # Combine all audio segments
            if audio_segments:
                combined_audio = np.concatenate(audio_segments)
                
                # Save audio file if requested
                audio_path = None
                if save_audio:
                    filename = f"cloned_voice_output.wav"
                    audio_path = self.output_dir / filename
                    
                    # Save as WAV file
                    sf.write(str(audio_path), combined_audio, 22050)
                    print(f"💾 Cloned voice audio saved to: {audio_path}")
                
                return audio_path
            else:
                print("❌ No audio segments generated")
                return None
            
        except Exception as e:
            print(f"❌ Error in voice cloning: {e}")
            print(f"💡 Error details: {type(e).__name__}")
            return None
    
    def split_text_into_chunks(self, text, max_chars=250):
        """Split text into smaller chunks for processing"""
        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk + sentence) <= max_chars:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def process_text_with_voice_clone(self, text_file_path, reference_audio_path, language="en"):
        """Complete pipeline: load text and generate with cloned voice"""
        print(f"🚀 Starting Text to Cloned Voice Audiobook...")
        print(f"📝 Text file: {text_file_path}")
        print(f"🎤 Reference voice: {reference_audio_path}")
        
        try:
            cleaned_text = self.load_text_from_file(text_file_path)
            if not cleaned_text:
                return None
            
            # Step 2: Clone voice and generate speech
            audio_path = self.clone_voice_and_generate(
                text=cleaned_text,
                reference_audio_path=reference_audio_path,
                language=language
            )
            
            return audio_path
            
        except Exception as e:
            print(f"❌ Error in pipeline: {e}")
            return None

def main():
    """Main execution function for voice cloning"""
    print("🎭 Text to Cloned Voice Audiobook using Coqui TTS")
    print("=" * 60)
    
    try:
        # Initialize converter
        converter = PDFToSpeechWithVoiceCloning()
        
        text_file = "audio_output/page_20_text.txt"  
        reference_audio = "myvoice.wav"  
        language = "en"  
        
        # Check if files exist
        if not os.path.exists(text_file):
            print(f"❌ Text file '{text_file}' not found!")
            print("💡 Available text files in audio_output folder:")
            audio_dir = Path("audio_output")
            if audio_dir.exists():
                text_files = list(audio_dir.glob("*_text_*.txt"))
                for tf in text_files:
                    print(f"   • {tf.name}")
            return
        
        if not os.path.exists(reference_audio):
            print(f"❌ Reference audio file '{reference_audio}' not found!")
            return
        
        # Process the text with voice cloning
        result = converter.process_text_with_voice_clone(
            text_file_path=text_file,
            reference_audio_path=reference_audio,
            language=language
        )
        
        if result:
            print(f"\n🎉 Success! Your cloned voice audiobook is ready!")
            print(f"🔊 Audio file: {result}")
            print(f"📁 All files saved in: {converter.output_dir}")
        else:
            print(f"\n❌ Voice cloning failed. Check the error messages above.")
            
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")

if __name__ == "__main__":
    main()