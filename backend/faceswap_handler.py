import os
import cv2
import numpy as np
import onnxruntime as ort
import mediapipe as mp
import torch
import uuid

# Configuration
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', 'models', 'faceswap')
INSWAPPER_PATH = os.path.join(MODELS_DIR, 'inswapper_128.onnx')
# We will use this common ArcFace ONNX that is easy to find or will be downloaded
ARCFACE_PATH = os.path.join(MODELS_DIR, 'arcface_w600k.onnx') 

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated', 'faceswap', 'input')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated', 'faceswap', 'output')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Standard InsightFace 128x128 reference landmarks template
ARCface_dst = np.array([
    [38.2946, 51.6963], [73.5318, 51.5014],
    [56.0252, 71.7366], [41.5493, 92.3655],
    [70.7299, 92.2041]
], dtype=np.float32)

class FaceSwapper:
    def __init__(self):
        self.swapper_session = None
        self.arcface_session = None
        self.mp_face_mesh = None
        
    def load_models(self):
        if self.mp_face_mesh is None:
            print("[*] Loading Mediapipe FaceMesh...")
            self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True, max_num_faces=5, refine_landmarks=True
            )
            
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        if self.swapper_session is None:
            print("[*] Loading Inswapper ONNX...")
            self.swapper_session = ort.InferenceSession(INSWAPPER_PATH, providers=providers)
        
        # We check if ArcFace exists, if not we will try a simpler fallback for embedding
        if self.arcface_session is None and os.path.exists(ARCFACE_PATH):
            print("[*] Loading ArcFace ONNX...")
            self.arcface_session = ort.InferenceSession(ARCFACE_PATH, providers=providers)

    def get_landmarks(self, image):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.mp_face_mesh.process(rgb)
        if not results.multi_face_landmarks: return None
        
        h, w, _ = image.shape
        faces_lms = []
        for face_lms in results.multi_face_landmarks:
            # Map mp landmarks to the 5 keys: L eye, R eye, Nose, L mouth, R mouth
            indices = [33, 263, 1, 61, 291]
            pts = np.array([[face_lms.landmark[i].x * w, face_lms.landmark[i].y * h] for i in indices], dtype=np.float32)
            faces_lms.append(pts)
        return faces_lms

    def get_embedding(self, image, landmarks):
        if not self.arcface_session:
            # Fallback: Use a dummy embedding if ArcFace isn't ready
            # This will result in poor swaps but won't crash
            print("[!] Warning: ArcFace model missing. Using zero-embedding fallback.")
            return np.zeros((1, 512), dtype=np.float32)
            
        # Align face to 112x112 for ArcFace
        # Standard ArcFace uses 112x112 template
        M, _ = cv2.estimateAffinePartial2D(landmarks, ARCface_dst * (112 / 128))
        warped = cv2.warpAffine(image, M, (112, 112))
        
        # Preprocess
        blob = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
        blob = blob.transpose(2, 0, 1).astype(np.float32) / 127.5 - 1.0
        blob = np.expand_dims(blob, axis=0)
        
        # Inference
        embedding = self.arcface_session.run(None, {self.arcface_session.get_inputs()[0].name: blob})[0]
        return embedding / np.linalg.norm(embedding)

    def swap_faces(self, source_path, target_path):
        self.load_models()
        
        source_img = cv2.imread(source_path)
        target_img = cv2.imread(target_path)
        if source_img is None or target_img is None: return None
        
        # 1. Source Face
        s_lms = self.get_landmarks(source_img)
        if not s_lms: return None
        s_embed = self.get_embedding(source_img, s_lms[0])
        
        # 2. Target Faces
        t_lms_list = self.get_landmarks(target_img)
        if not t_lms_list: return None
        
        res = target_img.copy()
        for t_lms in t_lms_list:
            M, _ = cv2.estimateAffinePartial2D(t_lms, ARCface_dst)
            warped = cv2.warpAffine(target_img, M, (128, 128))
            
            # Prepare Inswapper
            blob = (warped.astype(np.float32) / 255.0 - 0.5) / 0.5
            blob = blob.transpose(2, 0, 1).reshape(1, 3, 128, 128)
            
            inputs = {
                self.swapper_session.get_inputs()[0].name: blob,
                self.swapper_session.get_inputs()[1].name: s_embed
            }
            swapped = self.swapper_session.run(None, inputs)[0][0]
            
            # Postprocess
            swapped = swapped.transpose(1, 2, 0)
            swapped = (swapped * 0.5 + 0.5) * 255.0
            swapped = np.clip(swapped, 0, 255).astype(np.uint8)
            swapped = cv2.cvtColor(swapped, cv2.COLOR_RGB2BGR)
            
            # Warp back
            IM = cv2.invertAffineTransform(M)
            mask = np.full((128, 128), 255, dtype=np.uint8)
            swapped_back = cv2.warpAffine(swapped, IM, (res.shape[1], res.shape[0]))
            mask_back = cv2.warpAffine(mask, IM, (res.shape[1], res.shape[0]))
            mask_back = cv2.GaussianBlur(mask_back, (15, 15), 0)
            mask_norm = mask_back.astype(np.float32) / 255.0
            mask_norm = np.expand_dims(mask_norm, axis=-1)
            
            res = (mask_norm * swapped_back + (1 - mask_norm) * res).astype(np.uint8)
            
        return res

swapper = FaceSwapper()

def process_face_swap(source_filename, target_filename):
    s_path = os.path.join(UPLOAD_DIR, source_filename)
    t_path = os.path.join(UPLOAD_DIR, target_filename)
    if not os.path.exists(s_path) or not os.path.exists(t_path): return None
    
    try:
        res = swapper.swap_faces(s_path, t_path)
        if res is not None:
            out_name = f"swap_{uuid.uuid4().hex[:8]}.png"
            cv2.imwrite(os.path.join(OUTPUT_DIR, out_name), res)
            return out_name
    except Exception as e:
        print(f"[-] Swap runtime error: {e}")
    return None

def unload_faceswap():
    global swapper
    print("[*] Unloading FaceSwapper...")
    swapper.swapper_session = None
    swapper.arcface_session = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
