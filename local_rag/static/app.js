const input = document.querySelector('#pdf-input');
const statusBox = document.querySelector('#upload-status');
const fileList = document.querySelector('#file-list');
const form = document.querySelector('#chat-form');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');
const messages = document.querySelector('#messages');

input.addEventListener('change', async () => {
  if (!input.files.length) return;
  const invalid = [...input.files].filter(file => !file.name.toLowerCase().endsWith('.pdf'));
  if (invalid.length) return setStatus('PDF 파일만 업로드할 수 있습니다.', 'error');
  const data = new FormData();
  [...input.files].forEach(file => data.append('files', file));
  setStatus('PDF를 읽고 벡터 DB에 저장하는 중입니다…');
  try {
    const result = await api('/api/upload', { method: 'POST', body: data });
    result.files.forEach(name => {
      const chip = document.createElement('div'); chip.className = 'file-chip'; chip.textContent = `▣ ${name}`; fileList.append(chip);
    });
    setStatus(`${result.message} (${result.chunks}개 청크)`, 'success');
  } catch (error) { setStatus(error.message, 'error'); }
  input.value = '';
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message || sendButton.disabled) return;
  addMessage('user', message); messageInput.value = ''; resizeInput(); setBusy(true);
  const typing = addTyping();
  try {
    await streamChat(message, typing);
  } catch (error) {
    typing.remove(); addMessage('assistant', `오류: ${error.message}`);
  }
  setBusy(false); messageInput.focus();
});

messageInput.addEventListener('input', resizeInput);
messageInput.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });
document.querySelector('#reset-button').addEventListener('click', async () => {
  try { await api('/api/reset', {method:'POST'}); messages.innerHTML = ''; fileList.innerHTML = ''; location.reload(); } catch(error) { setStatus(error.message,'error'); }
});

function addMessage(role, text) { document.querySelector('#empty-state')?.remove(); const row=document.createElement('div'); row.className=`message ${role}`; const bubble=document.createElement('div'); bubble.className='bubble'; bubble.textContent=text; row.append(bubble); messages.append(row); scrollDown(); return row; }
function addTyping(){ document.querySelector('#empty-state')?.remove(); const row=document.createElement('div'); row.className='message assistant'; row.innerHTML='<div class="bubble typing"><i></i><i></i><i></i></div>'; messages.append(row); scrollDown(); return row; }
function addSources(sources){ const box=document.createElement('div'); box.className='sources'; const title=document.createElement('div'); title.className='sources-title'; title.textContent=`참고한 문서 조각 ${sources.length}개`; box.append(title); sources.forEach((source,index)=>{ const item=document.createElement('div'); item.className='source'; const meta=document.createElement('div'); meta.className='source-meta'; meta.textContent=`${index+1}. ${source.file} · ${source.page}페이지`; const summary=document.createElement('div'); summary.className='source-summary'; summary.textContent=source.summary; item.append(meta,summary); box.append(item); }); messages.append(box); scrollDown(); }
function setStatus(text,type=''){ statusBox.textContent=text; statusBox.className=`upload-status ${type}`; }
function setBusy(busy){ sendButton.disabled=busy; messageInput.disabled=busy; }
function resizeInput(){ messageInput.style.height='auto'; messageInput.style.height=`${Math.min(messageInput.scrollHeight,150)}px`; }
function scrollDown(){ messages.scrollTop=messages.scrollHeight; }
async function api(url,options){ const response=await fetch(url,options); const data=await response.json().catch(()=>({})); if(!response.ok) throw new Error(data.error || '요청을 처리하지 못했습니다.'); return data; }

async function streamChat(message, typing) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message}),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || '요청을 처리하지 못했습니다.');
  }
  if (!response.body) throw new Error('스트리밍 응답을 읽을 수 없습니다.');

  const bubble = typing.querySelector('.bubble');
  const renderer = createTextRenderer(bubble);
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  let started = false;
  let sources = [];

  const handleLine = line => {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.event === 'token') {
      if (!started) {
        bubble.className = 'bubble streaming';
        bubble.textContent = '';
        started = true;
      }
      renderer.push(event.text);
    } else if (event.event === 'done') {
      sources = event.sources || [];
    } else if (event.event === 'error') {
      throw new Error(event.message);
    }
  };

  while (true) {
    const {value, done} = await reader.read();
    buffer += value || '';
    const lines = buffer.split('\n');
    buffer = lines.pop();
    lines.forEach(handleLine);
    if (done) break;
  }
  if (buffer.trim()) handleLine(buffer);
  await renderer.finish();
  bubble.classList.remove('streaming');
  if (sources.length) addSources(sources);
}

function createTextRenderer(bubble) {
  let pending = '';
  let running = false;
  let finishing = false;
  let resolveFinished;
  const finished = new Promise(resolve => { resolveFinished = resolve; });

  const draw = () => {
    if (pending.length) {
      const count = Math.max(1, Math.ceil(pending.length / 100));
      bubble.textContent += pending.slice(0, count);
      pending = pending.slice(count);
      scrollDown();
      window.setTimeout(() => requestAnimationFrame(draw), 12);
      return;
    }
    running = false;
    if (finishing) resolveFinished();
  };

  return {
    push(text) {
      pending += text;
      if (!running) {
        running = true;
        requestAnimationFrame(draw);
      }
    },
    finish() {
      finishing = true;
      if (!running && !pending.length) resolveFinished();
      return finished;
    },
  };
}
