const API_URL = 'http://localhost:8000';
let currentConversationId = crypto.randomUUID();
let currentGenerationMode = 'text';

const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const conversationList = document.getElementById('conversation-list');
const clearHistoryBtn = document.getElementById('clear-history-btn');
const agentModeToggle = document.getElementById('agent-mode-toggle');
const modeBtns = document.querySelectorAll('.mode-btn');

const genSettings = document.getElementById('generation-settings');
const groupImg = document.getElementById('settings-image');
const groupVid = document.getElementById('settings-video');
const groupAud = document.getElementById('settings-audio');

window.addEventListener('DOMContentLoaded', () => {
    loadConversations();
    setupTextareaAutoResize();
});

modeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        modeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentGenerationMode = btn.dataset.mode;

        genSettings.classList.add('hidden');
        groupImg.classList.add('hidden');
        groupVid.classList.add('hidden');
        groupAud.classList.add('hidden');

        if (currentGenerationMode === 'image') {
            genSettings.classList.remove('hidden'); groupImg.classList.remove('hidden');
            messageInput.placeholder = "Describe the image to generate...";
        } else if (currentGenerationMode === 'video') {
            genSettings.classList.remove('hidden'); groupVid.classList.remove('hidden');
            messageInput.placeholder = "Describe the video to generate...";
        } else if (currentGenerationMode === 'audio') {
            genSettings.classList.remove('hidden'); groupAud.classList.remove('hidden');
            messageInput.placeholder = "Describe the audio / sound effect...";
        } else if (currentGenerationMode === 'faceswap') {
            document.getElementById('faceswap-upload-zone').classList.remove('hidden');
            messageInput.placeholder = "Add optional notes or hit enter...";
            sendBtn.disabled = !sourceFile || !targetFile;
        } else {
            messageInput.placeholder = "Message Atlas...";
        }
    });
});

let sourceFile = null;
let targetFile = null;

// Handle uploads
['source', 'target'].forEach(type => {
    const input = document.getElementById(`${type}-input`);
    const preview = document.getElementById(`${type}-preview`);
    const container = document.getElementById(`${type}-upload`);

    container.addEventListener('click', () => input.click());
    input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Visual feedback
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (re) => { preview.src = re.target.result; container.classList.add('has-file'); };
            reader.readAsDataURL(file);
        } else {
            container.classList.add('has-file');
            preview.style.display = 'none'; // Fallback for video
        }

        // Upload to server immediately
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await fetch(`${API_URL}/upload-media`, { method: 'POST', body: formData });
            const data = await res.json();
            if (type === 'source') sourceFile = data.filename;
            else targetFile = data.filename;

            if (currentGenerationMode === 'faceswap') sendBtn.disabled = !sourceFile || !targetFile;
        } catch (err) { alert('Upload failed'); }
    });
});

function setupTextareaAutoResize() {
    messageInput.addEventListener('input', function () {
        this.style.height = 'auto'; this.style.height = (this.scrollHeight) + 'px';
        sendBtn.disabled = this.value.trim().length === 0;
    });
    messageInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (this.value.trim().length > 0) chatForm.dispatchEvent(new Event('submit'));
        }
    });
}

newChatBtn.addEventListener('click', () => {
    currentConversationId = crypto.randomUUID();
    chatMessages.innerHTML = `<div class="empty-state"><h1>How can I help you today?</h1><p>I am Atlas, processing locally and privately.</p></div>`;
    document.querySelectorAll('.conv-item-wrapper').forEach(el => el.classList.remove('active'));
    messageInput.value = ''; messageInput.style.height = 'auto'; sendBtn.disabled = true; messageInput.focus();
});

clearHistoryBtn.addEventListener('click', async () => {
    if (confirm('Are you sure you want to clear all history?')) {
        await fetch(`${API_URL}/conversations`, { method: 'DELETE' });
        loadConversations(); newChatBtn.click();
    }
});

async function deleteConversation(id, e) {
    e.stopPropagation();
    await fetch(`${API_URL}/conversations/${id}`, { method: 'DELETE' });
    if (currentConversationId === id) newChatBtn.click();
    loadConversations();
}

async function loadConversations() {
    try {
        const res = await fetch(`${API_URL}/conversations`);
        const convos = await res.json();
        conversationList.innerHTML = '';
        convos.forEach(c => {
            const wrapper = document.createElement('div');
            wrapper.className = 'conv-item-wrapper';
            if (c.id === currentConversationId) wrapper.classList.add('active');

            const div = document.createElement('div');
            div.className = 'conv-item'; div.textContent = c.title || 'New Chat';
            div.addEventListener('click', () => loadChatHistory(c.id));

            const delBtn = document.createElement('button');
            delBtn.className = 'delete-conv-btn'; delBtn.innerHTML = '✕';
            delBtn.addEventListener('click', (e) => deleteConversation(c.id, e));

            wrapper.appendChild(div); wrapper.appendChild(delBtn);
            conversationList.appendChild(wrapper);
        });
    } catch (err) { }
}

async function loadChatHistory(id) {
    currentConversationId = id; loadConversations();
    try {
        const res = await fetch(`${API_URL}/conversations/${id}`);
        const history = await res.json();
        chatMessages.innerHTML = '';
        if (history.length === 0) return newChatBtn.click();
        history.forEach(msg => appendMessage(msg.role === 'user' ? 'user' : 'atlas', msg.content, msg.message_type, msg.file_path));
        scrollToBottom();
    } catch (err) { }
}

function appendMessage(sender, text, type = "text", filePath = null) {
    const existingEmpty = chatMessages.querySelector('.empty-state');
    if (existingEmpty) existingEmpty.remove();

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    let contentHtml = escapeHtml(text).replace(/\n/g, '<br>');

    if (filePath) {
        if (type === 'image') {
            contentHtml += `<br><img src="${API_URL}${filePath}" class="generated-media" />
                            <br><a href="${API_URL}${filePath}" download target="_blank" class="download-link">📥 Download Image</a>`;
        } else if (type === 'video') {
            contentHtml += `<br><video src="${API_URL}${filePath}" controls autoplay loop class="generated-media"></video>
                            <br><a href="${API_URL}${filePath}" download target="_blank" class="download-link">📥 Download Video</a>`;
        } else if (type === 'audio') {
            contentHtml += `<br><audio src="${API_URL}${filePath}" controls class="generated-media"></audio>
                            <br><a href="${API_URL}${filePath}" download target="_blank" class="download-link">📥 Download Audio</a>`;
        }
    }

    msgDiv.innerHTML = contentHtml;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;

    messageInput.value = ''; messageInput.style.height = 'auto'; sendBtn.disabled = true;
    appendMessage('user', text);

    const assistantDiv = document.createElement('div');
    assistantDiv.className = `message atlas`;

    if (currentGenerationMode === 'text') {
        assistantDiv.classList.add('blinking-cursor');
        chatMessages.appendChild(assistantDiv); scrollToBottom();

        try {
            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, conversation_id: currentConversationId, stream: true, agent_mode: agentModeToggle.checked })
            });
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            assistantDiv.classList.remove('blinking-cursor');

            let fullResponse = "";
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const lines = decoder.decode(value, { stream: true }).split('\\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.replace('data: ', '');
                        if (dataStr === '[DONE]') break;
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.token) {
                                fullResponse += data.token;
                                assistantDiv.innerHTML = escapeHtml(fullResponse).replace(/\\n/g, '<br>');
                                scrollToBottom();
                            }
                        } catch (e) { }
                    }
                }
            }
            loadConversations();
        } catch (err) {
            assistantDiv.classList.remove('blinking-cursor');
            assistantDiv.innerHTML = `<span style="color: #ff5555;">[Connection Error] Atlas is unreachable.</span>`;
        }
    } else {
        const modeLabel = currentGenerationMode.charAt(0).toUpperCase() + currentGenerationMode.slice(1);
        assistantDiv.innerHTML = `<div style="display:flex;align-items:center;"><div class="spinner"></div> Generating high-quality ${currentGenerationMode}... (Unloading VRAM automatically avoiding OOM)</div>`;
        chatMessages.appendChild(assistantDiv); scrollToBottom();

        let endpoint = `${API_URL}/generate-${currentGenerationMode}`;
        let bodyPayload = { prompt: text, conversation_id: currentConversationId };

        if (currentGenerationMode === 'image') {
            bodyPayload.width = parseInt(document.getElementById('img-res').value);
            bodyPayload.height = bodyPayload.width;
            bodyPayload.steps = parseInt(document.getElementById('img-steps').value);
            bodyPayload.cfg_scale = parseFloat(document.getElementById('img-cfg').value);
        } else if (currentGenerationMode === 'video') {
            bodyPayload.frames = parseInt(document.getElementById('vid-frames').value);
        } else if (currentGenerationMode === 'audio') {
            bodyPayload.duration = parseInt(document.getElementById('aud-dur').value);
        } else if (currentGenerationMode === 'faceswap') {
            endpoint = `${API_URL}/faceswap`;
            bodyPayload = {
                conversation_id: currentConversationId,
                source_filename: sourceFile,
                target_filename: targetFile
            };
        }

        try {
            const response = await fetch(endpoint, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyPayload)
            });
            const data = await response.json();
            if (data.status === 'success') {
                if (currentGenerationMode === 'image' || currentGenerationMode === 'faceswap') {
                    assistantDiv.innerHTML = `Operation complete!<br><img src="${API_URL}${data.file_path}" class="generated-media" /><br><a href="${API_URL}${data.file_path}" download target="_blank" class="download-link">📥 Download</a>`;
                } else if (currentGenerationMode === 'video') {
                    assistantDiv.innerHTML = `Generated video based on: ${escapeHtml(text)}<br><video src="${API_URL}${data.file_path}" controls autoplay loop class="generated-media"></video><br><a href="${API_URL}${data.file_path}" download target="_blank" class="download-link">📥 Download Video</a>`;
                } else if (currentGenerationMode === 'audio') {
                    assistantDiv.innerHTML = `Generated audio based on: ${escapeHtml(text)}<br><audio src="${API_URL}${data.file_path}" controls class="generated-media"></audio><br><a href="${API_URL}${data.file_path}" download target="_blank" class="download-link">📥 Download Audio</a>`;
                }
            } else {
                assistantDiv.innerHTML = `<span style="color:#ff5555"><b>Generation Failed</b>: ${data.message}</span>`;
            }
            loadConversations(); scrollToBottom();
        } catch (err) {
            console.error("Endpoint error:", err);
            assistantDiv.innerHTML = `<span style="color: #ff5555;">[Generation Error] Failed to contact ${currentGenerationMode} generator. Check if the backend is crashing.</span>`;
        }
    }
});

function scrollToBottom() { chatMessages.scrollTop = chatMessages.scrollHeight; }
function escapeHtml(u) { return u.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;"); }
