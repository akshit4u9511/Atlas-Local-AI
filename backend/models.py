from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    stream: Optional[bool] = True
    agent_mode: Optional[bool] = False

class CommandRequest(BaseModel):
    command: str
    require_confirmation: Optional[bool] = True

class GenerateImageRequest(BaseModel):
    prompt: str
    conversation_id: str
    width: Optional[int] = 512
    height: Optional[int] = 512
    steps: Optional[int] = 20
    cfg_scale: Optional[float] = 7.5
    
class GenerateVideoRequest(BaseModel):
    prompt: str
    conversation_id: str
    frames: Optional[int] = 16
    
class GenerateAudioRequest(BaseModel):
    prompt: str
    conversation_id: str
    duration: Optional[int] = 5

class FaceSwapRequest(BaseModel):
    conversation_id: str
    source_filename: str
    target_filename: str
