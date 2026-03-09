import os
import torch
import uuid
from diffusers import AutoPipelineForText2Image
from typing import Optional

# Switching to SDXL Turbo for high speed and extreme quality without T5 dependencies
MODEL_ID = "stabilityai/sdxl-turbo"
IMAGE_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated', 'images')
os.makedirs(IMAGE_DIR, exist_ok=True)

pipeline_instance = None

def get_image_pipeline():
    global pipeline_instance
    if pipeline_instance is None:
        print("[*] Allocating SDXL Turbo pipeline on GPU...")
        try:
            pipeline_instance = AutoPipelineForText2Image.from_pretrained(
                MODEL_ID, 
                torch_dtype=torch.float16,
                variant="fp16"
            )
            # Memory offloading for 8GB VRAM
            pipeline_instance.enable_model_cpu_offload()
            pipeline_instance.enable_vae_tiling()
        except Exception as e:
            print(f"[-] Error loading SDXL Turbo pipeline: {e}")
            return None
    return pipeline_instance

def generate_image(prompt: str, width: int = 512, height: int = 512, steps: int = 4, cfg_scale: float = 0.0) -> Optional[str]:
    # SDXL Turbo is optimized for 512x512 at 1-4 steps with CFG = 0 or 1
    pipe = get_image_pipeline()
    if not pipe: return None
        
    try:
        print(f"[*] SDXL Turbo Generating: '{prompt}'...")
        image = pipe(
            prompt=prompt, 
            num_inference_steps=steps, 
            guidance_scale=cfg_scale, 
            width=width, 
            height=height
        ).images[0]
        
        filename = f"atlas_turbo_{uuid.uuid4().hex[:8]}.png"
        file_path = os.path.join(IMAGE_DIR, filename)
        image.save(file_path)
        print(f"[+] Saved SDXL Turbo image to {file_path}")
        return filename
    except Exception as e:
        print(f"[-] SDXL Turbo generation failed: {e}")
        return None
        
def unload_image_pipeline():
    global pipeline_instance
    if pipeline_instance:
        print("[*] Unloading SDXL Turbo pipeline from VRAM...")
        del pipeline_instance
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        pipeline_instance = None
