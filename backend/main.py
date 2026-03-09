import os
import sys
import json
import gc
from fastapi import FastAPI, Depends, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from langchain_community.llms import LlamaCpp
from langchain_core.callbacks import BaseCallbackHandler
import queue
import threading

import database
import image_gen
import video_gen
import audio_gen
import faceswap_handler
from models import ChatRequest, CommandRequest, GenerateImageRequest, GenerateVideoRequest, GenerateAudioRequest, FaceSwapRequest

os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'data'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'generated', 'images'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'generated', 'videos'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'generated', 'audio'), exist_ok=True)
database.init_db()

app = FastAPI(title="Atlas Multimodal API")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.mount("/generated/images", StaticFiles(directory=os.path.join(os.path.dirname(__file__), '..', 'generated', 'images')), name="images")
app.mount("/generated/videos", StaticFiles(directory=os.path.join(os.path.dirname(__file__), '..', 'generated', 'videos')), name="videos")
app.mount("/generated/audio", StaticFiles(directory=os.path.join(os.path.dirname(__file__), '..', 'generated', 'audio')), name="audio")

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'Mistral-7B-Instruct-v0.3.Q4_K_M.gguf')
llm_instance = None

def free_vram_except(keep: str):
    if 'torch' in sys.modules:
        import torch
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            print(f"[*] Pre-check VRAM: {free/1024**3:.2f}GB free / {total/1024**3:.2f}GB total")
    
    print(f"[*] Allocating VRAM for '{keep}'. Evicting other pipelines...")
    global llm_instance
    if keep != "llm" and llm_instance:
        print("[*] Unloading MS-7B from VRAM...")
        del llm_instance
        llm_instance = None
    if keep != "image": image_gen.unload_image_pipeline()
    if keep != "video": video_gen.unload_video_pipeline()
    if keep != "audio": audio_gen.unload_audio_pipeline()
    if keep != "faceswap": faceswap_handler.unload_faceswap()
    gc.collect()
    if 'torch' in sys.modules:
        import torch
        if torch.cuda.is_available():
            print("[*] Clearing CUDA cache...")
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

def get_llm():
    global llm_instance
    if llm_instance is None:
        free_vram_except("llm")
        print("[*] Loading Mistral-7B to GPU...")
        llm_instance = LlamaCpp(
            model_path=MODEL_PATH, temperature=0.3, max_tokens=1024, n_ctx=4096,
            n_gpu_layers=33, n_threads=8, streaming=True, verbose=False,
        )
    return llm_instance

class QueueCallbackHandler(BaseCallbackHandler):
    def __init__(self, q: queue.Queue): self.q = q
    def on_llm_new_token(self, token: str, **kwargs) -> None: self.q.put(token)
    def on_llm_end(self, *args, **kwargs) -> None: self.q.put(None)
    def on_llm_error(self, *args, **kwargs) -> None: self.q.put(None)

def build_prompt(conversation_id: str, new_message: str, agent_mode: bool = False) -> str:
    history = database.get_conversation_history(conversation_id)
    sys_prompt = "You are Atlas, a high-capability local AI assistant running privately for a single trusted user on their own machine. You prioritize privacy, safety, accuracy, and efficiency."
    if agent_mode: sys_prompt += " AGENT MODE ACTIVE: You may execute purely local, safe commands in the AtlasLocalAI directory via exactly `<CMD> command </CMD>`."
    prompt = f"<s>[INST] {sys_prompt} [/INST] Understood.\n"
    for msg in history:
        if msg["role"] == "user": prompt += f"<s>[INST] {msg['content']} [/INST]"
        else: prompt += f" {msg['content']}</s>\n"
    prompt += f"<s>[INST] {new_message} [/INST]"
    return prompt

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    database.create_conversation(request.conversation_id)
    database.add_message(request.conversation_id, "user", request.message)
    prompt = build_prompt(request.conversation_id, request.message, request.agent_mode)
    llm = get_llm()

    async def event_generator():
        full_response = ""
        try:
            for chunk in llm.stream(prompt):
                full_response += chunk
                yield {"event": "message", "data": json.dumps({"token": chunk})}
                
            if request.agent_mode and "<CMD>" in full_response and "</CMD>" in full_response:
                import re, subprocess
                cmd_match = re.search(r"<CMD>(.*?)</CMD>", full_response, re.DOTALL)
                if cmd_match:
                    command = cmd_match.group(1).strip()
                    yield {"event": "message", "data": json.dumps({"token": f"\n\n[Atlas Agent executing: {command}]\n"})}
                    try:
                        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)), timeout=10)
                        output = result.stdout if result.returncode == 0 else result.stderr
                    except Exception as ce: output = f"[Execution Error: {ce}]"
                    output_str = f"```\n{output}\n```"
                    full_response += f"\n\n[Execution Result]\n{output_str}"
                    yield {"event": "message", "data": json.dumps({"token": f"\n[Execution Result]\n{output_str}"})}
        except Exception as e: print(f"[-] Generation error: {e}")
        database.add_message(request.conversation_id, "assistant", full_response)
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_generator())

@app.post("/generate-image")
async def gen_image(request: GenerateImageRequest):
    database.create_conversation(request.conversation_id)
    
    # 1. Enhance Prompt using the LLM (while VRAM still has the LLM loaded)
    llm = get_llm()
    # Concise instructions for the LLM to expand the prompt for SDXL
    enhance_prompt = f"<s>[INST] You are an expert image prompt engineer. Rewrite the following request into a high-detail, cinematic SDXL prompt. Focus on quality, lighting, and composition. Keep it to one paragraph. \nRequest: {request.prompt} [/INST]"
    print(f"[*] Enhancing prompt for quality...")
    enhanced_prompt = llm.invoke(enhance_prompt).strip()
    print(f"[+] Enhanced Prompt: {enhanced_prompt}")

    # 2. Swap VRAM from LLM to Image Generator
    free_vram_except("image")
    
    database.add_message(request.conversation_id, "user", f"[Image Request]: {request.prompt}", message_type="text")
    
    filename = image_gen.generate_image(
        enhanced_prompt, 
        steps=request.steps, 
        cfg_scale=request.cfg_scale, 
        width=request.width, 
        height=request.height
    )
    
    if filename:
        url = f"/generated/images/{filename}"
        database.add_message(request.conversation_id, "assistant", f"Generated image based on: {request.prompt}", message_type="image", file_path=url)
        print(f"[+] Image Generation Success: {url}")
        return {"status": "success", "file_path": url, "enhanced_prompt": enhanced_prompt}
    print("[-] Image Generation Failed.")
    return {"status": "error", "message": "Image generation failed."}

@app.post("/generate-video")
async def gen_video(request: GenerateVideoRequest):
    free_vram_except("video")
    database.create_conversation(request.conversation_id)
    database.add_message(request.conversation_id, "user", f"[Video Request]: {request.prompt}", message_type="text")
    filename = video_gen.generate_video(request.prompt, frames=request.frames)
    
    if filename:
        url = f"/generated/videos/{filename}"
        database.add_message(request.conversation_id, "assistant", f"Generated video based on: {request.prompt}", message_type="video", file_path=url)
        print(f"[+] Video Generation Success: {url}")
        return {"status": "success", "file_path": url}
    print("[-] Video Generation Failed.")
    return {"status": "error", "message": "Video generation failed."}

@app.post("/generate-audio")
async def gen_audio(request: GenerateAudioRequest):
    free_vram_except("audio")
    database.create_conversation(request.conversation_id)
    database.add_message(request.conversation_id, "user", f"[Audio Request]: {request.prompt}", message_type="text")
    filename = audio_gen.generate_audio(request.prompt, duration=request.duration)
    
    if filename:
        url = f"/generated/audio/{filename}"
        database.add_message(request.conversation_id, "assistant", f"Generated audio based on: {request.prompt}", message_type="audio", file_path=url)
        return {"status": "success", "file_path": url}
    return {"status": "error", "message": "Audio generation failed."}

@app.post("/upload-media")
async def upload_media(file: UploadFile = File(...)):
    import uuid, shutil
    upload_dir = os.path.join(os.path.dirname(__file__), '..', 'generated', 'faceswap', 'input')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "filename": filename}

@app.post("/faceswap")
async def faceswap_endpoint(request: FaceSwapRequest):
    free_vram_except("faceswap")
    database.create_conversation(request.conversation_id)
    database.add_message(request.conversation_id, "user", f"[Face Swap Request]: Source {request.source_filename} on Target {request.target_filename}")
    
    result_filename = faceswap_handler.process_face_swap(request.source_filename, request.target_filename)
    
    if result_filename:
        url = f"/generated/faceswap/{result_filename}"
        database.add_message(request.conversation_id, "assistant", "Face swap complete!", message_type="image", file_path=url)
        print(f"[+] Face Swap Success: {url}")
        return {"status": "success", "file_path": url}
    print("[-] Face Swap Failed.")
    return {"status": "error", "message": "Face swap failed."}

@app.get("/conversations")
def list_conversations(): return database.get_all_conversations()
@app.get("/conversations/{conversation_id}")
def get_conversation(id: str): return database.get_conversation_history(id)
@app.delete("/conversations/{conversation_id}")
def delete_conversation(id: str):
    database.delete_conversation(id)
    return {"status": "success"}
@app.delete("/conversations")
def delete_all():
    database.clear_all_conversations()
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
