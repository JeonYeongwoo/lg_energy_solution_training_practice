const $ = (selector) => document.querySelector(selector);
const conversation = $('#conversation');
const progressPanel = $('#progressPanel');
const progressBar = $('#progressBar');
let contractId = null;
let toastTimer = null;

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}

function showToast(message) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3200);
}

function showProgress(title, percent, detail) {
  progressPanel.hidden = false;
  $('#progressTitle').textContent = title;
  $('#progressLabel').textContent = `${percent}%`;
  $('#progressDetail').textContent = detail;
  progressBar.style.width = `${percent}%`;
}

function hideWelcome() { $('#welcome')?.remove(); }
function scrollBottom() { conversation.scrollTop = conversation.scrollHeight; }

function addMessage(role, text) {
  hideWelcome();
  const item = document.createElement('article');
  item.className = `message ${role}`;
  if (role === 'user') item.textContent = text;
  else item.innerHTML = `<div class="message-label">AI 답변</div><div class="message-body">${escapeHtml(text)}</div>`;
  conversation.appendChild(item);
  scrollBottom();
}

function uploadWithProgress(url, formData, {title, detail}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.upload.onprogress = event => {
      if (event.lengthComputable) {
        const percent = Math.min(90, Math.round(event.loaded / event.total * 90));
        showProgress(title, percent, detail);
      }
    };
    xhr.onload = () => {
      let result;
      try { result = JSON.parse(xhr.responseText); }
      catch { result = {error: '서버 응답을 읽을 수 없습니다.'}; }
      if (xhr.status >= 200 && xhr.status < 300) resolve(result);
      else reject(new Error(result.error || '업로드에 실패했습니다.'));
    };
    xhr.onerror = () => reject(new Error('서버에 연결할 수 없습니다.'));
    xhr.send(formData);
  });
}

$('#ragInput').addEventListener('change', async event => {
  const files = [...event.target.files];
  if (!files.length) return;
  const data = new FormData();
  files.forEach(file => data.append('files', file));
  try {
    const result = await uploadWithProgress('/api/rag/upload', data, {title: '가이드라인 등록 중', detail: `${files.length}개 PDF를 읽고 있습니다.`});
    showProgress('가이드라인 등록 완료', 100, `${result.chunk_count}개 청크를 Chroma DB에 저장했습니다.`);
    $('#ragStatus').textContent = `가이드라인 ${result.total_chunks}개 청크`;
    addMessage('assistant', result.message);
    setTimeout(() => { progressPanel.hidden = true; }, 1600);
  } catch (error) { showToast(error.message); progressPanel.hidden = true; }
  event.target.value = '';
});

$('#contractInput').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  const data = new FormData(); data.append('file', file);
  try {
    const result = await uploadWithProgress('/api/contract/upload', data, {title: '계약서 분석 중', detail: `${file.name}에서 문장을 나누고 있습니다.`});
    contractId = result.contract_id;
    showProgress('계약서 준비 완료', 100, `${result.sentence_count}개 검토 단위로 나눴습니다.`);
    $('#reviewButton').hidden = false;
    addMessage('assistant', `${result.filename}\n${result.message} (${result.sentence_count}개 문장)`);
    setTimeout(() => { progressPanel.hidden = true; }, 1600);
  } catch (error) { showToast(error.message); progressPanel.hidden = true; }
  event.target.value = '';
});

$('#reviewButton').addEventListener('click', () => {
  if (!contractId) return;
  hideWelcome();
  $('#reviewButton').disabled = true;
  const stream = new EventSource(`/api/contract/review/${contractId}`);
  showProgress('계약서 검토 중', 0, 'RAG에서 관련 가이드라인을 찾고 있습니다.');
  stream.addEventListener('clause', event => {
    const data = JSON.parse(event.data);
    const item = document.createElement('article');
    item.className = 'clause';
    item.innerHTML = `<div class="clause-number">검토 ${data.index} / ${data.total}</div>
      <div class="original"><span class="tag">[원문]</span>${escapeHtml(data.original)}</div>
      ${data.needs_revision ? `<div class="revision"><span class="tag">[수정 문구]</span>${escapeHtml(data.revised)}<p class="reason">검토 근거 · ${escapeHtml(data.reason)}</p></div>` : ''}`;
    conversation.appendChild(item);
    showProgress('계약서 검토 중', data.progress, `${data.index}번째 문장을 확인했습니다.`);
    scrollBottom();
  });
  stream.addEventListener('complete', event => {
    const data = JSON.parse(event.data);
    stream.close();
    showProgress('검토 완료', 100, `${data.total}개 문장 검토가 끝났습니다.`);
    $('#reviewButton').disabled = false;
    showToast(data.message);
    setTimeout(() => { progressPanel.hidden = true; }, 2200);
  });
  stream.addEventListener('error', event => {
    stream.close();
    $('#reviewButton').disabled = false;
    progressPanel.hidden = true;
    if (event.data) showToast(JSON.parse(event.data).message);
    else showToast('검토 연결이 종료되었습니다. 서버 로그를 확인해 주세요.');
  });
});

$('#chatForm').addEventListener('submit', async event => {
  event.preventDefault();
  const input = $('#questionInput');
  const question = input.value.trim();
  if (!question) return;
  addMessage('user', question); input.value = '';
  $('#sendButton').disabled = true;
  showProgress('답변 생성 중', 35, 'AI가 질문을 확인하고 있습니다.');
  try {
    const response = await fetch('/api/chat', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({question})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '답변 생성에 실패했습니다.');
    addMessage('assistant', result.answer);
  } catch (error) { showToast(error.message); }
  finally { $('#sendButton').disabled = false; progressPanel.hidden = true; input.focus(); }
});

$('#questionInput').addEventListener('input', event => {
  event.target.style.height = 'auto';
  event.target.style.height = `${Math.min(event.target.scrollHeight, 150)}px`;
});
$('#questionInput').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('#chatForm').requestSubmit(); }
});
$('#menuButton').addEventListener('click', () => $('.sidebar').classList.toggle('open'));

fetch('/api/status').then(response => response.json()).then(data => {
  $('#statusDot').classList.toggle('ready', data.api_key_ready);
  $('#systemStatus').textContent = data.api_key_ready ? 'AI 연결 준비됨' : 'API 키 확인 필요';
  $('#ragStatus').textContent = `가이드라인 ${data.rag_chunks}개 청크`;
}).catch(() => { $('#systemStatus').textContent = '서버 연결 확인 필요'; });
