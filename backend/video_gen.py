import os
import torch
import uuid
import tempfile
import imageio
from diffusers import TextToVideoSDPipeline
from diffusers.utils import export_to_video
from typing import Optional

MODEL_ID = "cerspense/zeroscope_v2_576w"
VIDEO_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated', 'videos')
os.makedirs(VIDEO_DIR, exist_ok=True)

pipeline_instance = None

def get_video_pipeline():
    global pipeline_instance
    if pipeline_instance is None:
        print("[*] Allocating Zeroscope Video pipeline on GPU...")
        try:
            pipeline_instance = TextToVideoSDPipeline.from_pretrained(
                MODEL_ID, 
                torch_dtype=torch.float16
            )
            # Critical for 8GB VRAM video generation
            pipeline_instance.enable_model_cpu_offload()
            pipeline_instance.enable_vae_slicing()
        except Exception as e:
            print(f"[-] Error loading video pipeline: {e}")
            return None
    return pipeline_instance

def generate_video(prompt: str, frames: int = 24, steps: int = 25, cfg_scale: float = 9.0) -> Optional[str]:
    pipe = get_video_pipeline()
    if not pipe: return None
        
    try:
        print(f"[*] Video Generating: '{prompt}' ({frames} frames)...")
        video_frames = pipe(
            prompt, 
            num_inference_steps=steps, 
            num_frames=frames, 
            guidance_scale=cfg_scale
        ).frames[0]
        
        filename = f"atlas_video_{uuid.uuid4().hex[:8]}.mp4"
        file_path = os.path.join(VIDEO_DIR, filename)
        
        export_to_video(video_frames, file_path, fps=8)
        print(f"[+] Saved video to {file_path}")
        
        return filename
    except Exception as e:
        print(f"[-] Video generation failed: {e}")
        return None
        
def unload_video_pipeline():
    global pipeline_instance
    if pipeline_instance:
        print("[*] Unloading video pipeline from VRAM...")
        del pipeline_instance
        torch.cuda.empty_cache()
        pipeline_instance = None
