import os
import torch
import uuid
import scipy.io.wavfile
from diffusers import AudioLDMPipeline
from typing import Optional

MODEL_ID = "cvssp/audioldm-s-full-v2"
AUDIO_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated', 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

pipeline_instance = None

def get_audio_pipeline():
    global pipeline_instance
    if pipeline_instance is None:
        print("[*] Allocating AudioLDM pipeline on GPU...")
        try:
            pipeline_instance = AudioLDMPipeline.from_pretrained(
                MODEL_ID, 
                torch_dtype=torch.float16
            )
            # Memory offloading
            pipeline_instance.enable_model_cpu_offload()
        except Exception as e:
            print(f"[-] Error loading audio pipeline: {e}")
            return None
    return pipeline_instance

def generate_audio(prompt: str, duration: int = 5, steps: int = 10, cfg_scale: float = 2.5) -> Optional[str]:
    pipe = get_audio_pipeline()
    if not pipe: return None
        
    try:
        print(f"[*] Audio Generating: '{prompt}' for {duration}s...")
        audio = pipe(
            prompt, 
            num_inference_steps=steps, 
            audio_length_in_s=duration, 
            guidance_scale=cfg_scale
        ).audios[0]
        
        filename = f"atlas_audio_{uuid.uuid4().hex[:8]}.wav"
        file_path = os.path.join(AUDIO_DIR, filename)
        
        # Save as WAV using scipy
        scipy.io.wavfile.write(file_path, rate=16000, data=audio)
        print(f"[+] Saved audio to {file_path}")
        
        return filename
    except Exception as e:
        print(f"[-] Audio generation failed: {e}")
        return None
        
def unload_audio_pipeline():
    global pipeline_instance
    if pipeline_instance:
        print("[*] Unloading audio pipeline from VRAM...")
        del pipeline_instance
        torch.cuda.empty_cache()
        pipeline_instance = None
