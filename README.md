## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/akshit4u9511/Atlas-Local-AI.git
cd Atlas-Local-AI
```

### 2. Create a Virtual Environment

The `venv` folder is **not included in the repository** because it can be very large.
Create your own virtual environment:

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

**Windows**

```bash
venv\Scripts\activate
```

**Linux / Mac**

```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Project

```bash
python run_backend.py
python run_frontend.py
```

NOTE*
(Download the Model)

This project uses Mistral-7B-Instruct-v0.3 (Q4_K_M).

Due to GitHub file size limits, the model is not included in this repository.

Download the model manually:

Go to the Hugging Face model page

Download the file:

Mistral-7B-Instruct-v0.3.Q4_K_M.gguf

Place the file inside:

/models/

Final structure should look like:

Atlas-Local-AI
│
├── models
│   └── Mistral-7B-Instruct-v0.3.Q4_K_M.ggufDownload the Model
