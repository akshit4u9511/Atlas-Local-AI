# Atlas Local AI

Atlas Local AI is a **multimodal AI platform** that combines conversational AI, image generation, and video generation into a single powerful system.

Built for **local execution**, Atlas prioritizes **privacy, speed, and creative freedom** while allowing users to generate text, images, and videos directly from their own machine.

---

# Features

* Local AI Chat (LLM powered)
* Image generation
* Video generation
* Privacy-first (runs locally)
* Lightweight backend + frontend architecture

---

# Project Structure

```
Atlas-Local-AI
│
├── backend/
├── frontend/
├── images/
├── run_backend.py
├── run_frontend.py
├── README.md
```

---

# Setup Instructions

## 1. Clone the Repository

```bash
git clone https://github.com/akshit4u9511/Atlas-Local-AI.git
cd Atlas-Local-AI
```

---

## 2. Create a Virtual Environment

The `venv` folder is **not included in the repository** because it can be very large.

Create your own environment:

```bash
python -m venv venv
```

---

## 3. Activate the Virtual Environment

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

---

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Run the Project

Start the backend:

```bash
python run_backend.py
```

Start the frontend:

```bash
python run_frontend.py
```

---

# Download the Model

This project uses **Mistral-7B-Instruct-v0.3 (Q4_K_M)**.

Due to GitHub file size limits, the model is **not included in this repository**.

Download the model manually.

Model file:

```
Mistral-7B-Instruct-v0.3.Q4_K_M.gguf
```

Place the file inside:

```
models/
```

Final structure should look like:

```
Atlas-Local-AI
│
├── models
│   └── Mistral-7B-Instruct-v0.3.Q4_K_M.gguf
```

---

# Notes

* The virtual environment (`venv`) is ignored in this repository.
* Large AI model files are not stored in the repo due to GitHub size limits.
* Make sure the model file is placed correctly before running the backend.

---
