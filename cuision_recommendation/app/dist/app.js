const STORAGE_KEY = "fridge-mini-v1";
const BASIC_SEASONINGS = ["소금", "식용유", "간장"];
const sampleIngredients = [
  { id: crypto.randomUUID(), name: "달걀", qty: "4개", expiry: "", confidence: "high" },
  { id: crypto.randomUUID(), name: "밥", qty: "2공기", expiry: "", confidence: "high" },
  { id: crypto.randomUUID(), name: "대파", qty: "반 단", expiry: nextDate(2), confidence: "high" },
  { id: crypto.randomUUID(), name: "김치", qty: "1통", expiry: "", confidence: "high" },
  { id: crypto.randomUUID(), name: "두부", qty: "1모", expiry: nextDate(1), confidence: "low" },
  { id: crypto.randomUUID(), name: "치즈", qty: "3장", expiry: "", confidence: "low" }
];

const recipes = [
  {
    id: "soy-egg-rice", title: "초간단 간장계란밥", minutes: 8, dishes: 1,
    ingredients: ["달걀", "밥", "대파"], allergens: ["달걀"], tools: ["가스레인지"],
    usage: { "달걀": "2개", "밥": "1공기", "대파": "조금" },
    steps: [
      { text: "대파를 송송 썰고 달걀 2개를 준비해요." },
      { text: "팬에 식용유를 두르고 달걀을 반숙으로 익혀요.", seconds: 120 },
      { text: "따뜻한 밥 위에 달걀과 대파를 올리고 간장 1스푼을 둘러요." },
      { text: "가볍게 비비면 완성! 팬 하나만 씻으면 돼요." }
    ]
  },
  {
    id: "microwave-egg", title: "전자레인지 치즈계란찜", minutes: 10, dishes: 1,
    ingredients: ["달걀", "치즈", "대파"], allergens: ["달걀", "우유"], tools: ["전자레인지"],
    usage: { "달걀": "2개", "치즈": "1장", "대파": "조금" },
    steps: [
      { text: "전자레인지용 그릇에 달걀 2개와 물 3스푼을 잘 풀어요." },
      { text: "치즈와 대파를 올리고 뚜껑을 살짝 덮어 2분 돌려요.", seconds: 120 },
      { text: "가운데를 확인하고 덜 익었다면 30초 더 돌려요.", seconds: 30 },
      { text: "소금 한 꼬집으로 간하면 완성!" }
    ]
  },
  {
    id: "tofu-kimchi-bowl", title: "두부김치 한 그릇", minutes: 12, dishes: 1,
    ingredients: ["두부", "김치", "밥"], allergens: ["대두"], tools: ["전자레인지"],
    usage: { "두부": "반 모", "김치": "한 줌", "밥": "1공기" },
    steps: [
      { text: "두부 반 모를 한입 크기로 썰어 그릇에 담아요." },
      { text: "김치를 올리고 뚜껑을 살짝 덮어 전자레인지에 3분 돌려요.", seconds: 180 },
      { text: "따뜻한 밥 위에 두부김치를 올리고 참기름이 있다면 살짝 둘러요." }
    ]
  },
  {
    id: "kimchi-rice", title: "원팬 김치볶음밥", minutes: 14, dishes: 1,
    ingredients: ["김치", "밥", "달걀"], allergens: ["달걀"], tools: ["가스레인지"],
    usage: { "김치": "한 줌", "밥": "1공기", "달걀": "1개" },
    steps: [
      { text: "팬에 식용유를 두르고 김치를 2분 볶아요.", seconds: 120 },
      { text: "밥과 간장 반 스푼을 넣고 고루 볶아요.", seconds: 180 },
      { text: "팬 한쪽에서 달걀을 익힌 뒤 모두 섞으면 완성!" }
    ]
  }
];

const defaultState = {
  onboarded: false,
  settings: { allergies: "", restricted: "", dislikes: "", diet: "", tools: ["가스레인지", "전자레인지"] },
  ingredients: [], ratings: {}, completed: [], screen: "home", photoUrl: null,
  selectedRecipe: null, stepIndex: 0, timerRemaining: 0, timerRunning: false
};

let state = loadState();
let timerId = null;
const screen = document.querySelector("#screen");
const dialog = document.querySelector("#settings-dialog");
const settingsForm = document.querySelector("#settings-form");

function nextDate(days) {
  const date = new Date(); date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return { ...defaultState, ...saved, settings: { ...defaultState.settings, ...(saved?.settings || {}) }, photoUrl: null, timerRunning: false };
  } catch { return structuredClone(defaultState); }
}

function saveState() {
  const persistable = { ...state, photoUrl: null, timerRunning: false };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(persistable));
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function render() {
  clearInterval(timerId); timerId = null;
  const views = { home: renderHome, ingredients: renderIngredients, recommendations: renderRecommendations, cook: renderCook, complete: renderComplete, fridge: renderFridge, likes: renderLikes };
  (views[state.screen] || renderHome)();
  document.querySelectorAll("[data-nav]").forEach(button => button.classList.toggle("is-active", button.dataset.nav === state.screen || (button.dataset.nav === "home" && ["ingredients", "recommendations", "cook", "complete"].includes(state.screen))));
  if (!state.onboarded && !dialog.open) openSettings(true);
}

function renderHome() {
  screen.innerHTML = `
    <div class="section-head"><div><p class="eyebrow">QUICK COOK</p><h1>사진 한 장이면<br>오늘 저녁 결정 끝!</h1><p class="lead">가장 빠르고, 설거지는 가장 적은 메뉴부터 골라드려요.</p></div></div>
    <section class="upload-card">
      <div class="camera-visual" aria-hidden="true">▣</div>
      <h2>냉장고 안을 보여주세요</h2>
      <p class="lead">재료를 찾아 목록으로 만들고, 확인 후 바로 추천해요.</p>
      <div class="upload-actions">
        <label class="primary" style="display:grid;place-items:center;text-align:center">사진 찍기<input class="hidden" id="camera-input" type="file" accept="image/*" capture="environment"></label>
        <label class="secondary" style="display:grid;place-items:center;text-align:center">앨범에서<input class="hidden" id="gallery-input" type="file" accept="image/*"></label>
      </div>
      <button class="text-button full" type="button" data-action="use-sample">사진 없이 샘플로 체험하기</button>
      <p class="microcopy">사진은 분석 화면에서만 사용하고 저장하지 않아요.</p>
    </section>
    <div class="tip-strip"><span>★</span><div><strong>사진 팁</strong><br>문을 활짝 열고 전체가 보이게 찍으면 더 잘 찾아요.</div></div>`;
}

function startScan(file) {
  if (file && !file.type.startsWith("image/")) { showToast("이미지 파일을 선택해 주세요."); return; }
  if (state.photoUrl) URL.revokeObjectURL(state.photoUrl);
  state.photoUrl = file ? URL.createObjectURL(file) : null;
  screen.innerHTML = `<div class="loading"><div><div class="scanner" style="${state.photoUrl ? `background-image:url('${state.photoUrl}')` : "background-image:url('./meal.png')"}"></div><p class="eyebrow">ANALYZING</p><h2>냉장고 속 재료를 찾는 중</h2><p class="lead">잠시만 기다려 주세요 <span class="dots" aria-hidden="true"><i></i><i></i><i></i></span></p></div></div>`;
  setTimeout(() => {
    state.ingredients = sampleIngredients.map(item => ({ ...item, id: crypto.randomUUID() }));
    state.screen = "ingredients"; saveState(); render();
  }, 1300);
}

function renderIngredients() {
  screen.innerHTML = `
    <div class="section-head"><div><p class="eyebrow">CHECK LIST</p><h1>찾은 재료가 맞나요?</h1><p class="lead">틀린 건 고치고, 가려진 재료는 직접 추가해 주세요.</p></div><button class="text-button" data-action="rescan">다시 촬영</button></div>
    <div class="ingredient-list">${state.ingredients.map(ingredientRow).join("")}</div>
    <button class="soft-button full" style="margin-top:12px" data-action="add-ingredient">＋ 재료 추가</button>
    <div class="sticky-actions"><button class="primary full" data-action="confirm-ingredients">${state.ingredients.length}개 재료로 추천받기</button></div>`;
}

function ingredientRow(item) {
  return `<article class="ingredient-row" data-id="${item.id}">
    <div class="ingredient-main"><input class="ingredient-name" aria-label="재료 이름" value="${escapeHtml(item.name)}"><button class="remove-button" data-action="remove-ingredient" aria-label="${escapeHtml(item.name)} 삭제">×</button></div>
    <span class="confidence ${item.confidence === "low" ? "low" : ""}">${item.confidence === "low" ? "확인이 필요해요" : "사진에서 찾았어요"}</span>
    <div class="ingredient-meta"><label>남은 양 (선택)<input class="ingredient-qty" value="${escapeHtml(item.qty)}" placeholder="예: 2개"></label><label>유통기한 (선택)<input class="ingredient-expiry" type="date" value="${item.expiry}"></label></div>
  </article>`;
}

function syncIngredientsFromDom() {
  state.ingredients = [...document.querySelectorAll(".ingredient-row")].map(row => ({
    id: row.dataset.id, name: row.querySelector(".ingredient-name").value.trim(), qty: row.querySelector(".ingredient-qty").value.trim(), expiry: row.querySelector(".ingredient-expiry").value, confidence: "high"
  })).filter(item => item.name);
}

function getRecommendations() {
  const available = new Set([...state.ingredients.map(i => i.name.trim()), ...BASIC_SEASONINGS]);
  const settingsText = [state.settings.allergies, state.settings.restricted, state.settings.dislikes].join(",");
  const blocked = settingsText.split(/[,，]/).map(v => v.trim()).filter(Boolean);
  const tools = state.settings.tools.length ? state.settings.tools : ["가스레인지", "전자레인지"];
  return recipes
    .filter(recipe => recipe.ingredients.every(i => available.has(i)))
    .filter(recipe => recipe.tools.some(tool => tools.includes(tool)))
    .filter(recipe => !recipe.ingredients.some(i => blocked.includes(i)) && !recipe.allergens.some(i => blocked.includes(i)))
    .map(recipe => ({ ...recipe, expiryCount: recipe.ingredients.filter(isExpiring).length, rating: state.ratings[recipe.id] || 0 }))
    .sort((a, b) => a.minutes - b.minutes || a.dishes - b.dishes || b.expiryCount - a.expiryCount || b.rating - a.rating)
    .slice(0, 3);
}

function isExpiring(name) {
  const item = state.ingredients.find(i => i.name === name);
  if (!item?.expiry) return false;
  const days = Math.ceil((new Date(`${item.expiry}T23:59:59`) - new Date()) / 86400000);
  return days >= 0 && days <= 3;
}

function renderRecommendations() {
  const results = getRecommendations();
  screen.innerHTML = `
    <div class="section-head"><div><p class="eyebrow">TOP 3</p><h1>지금 바로 만들 수 있어요</h1><p class="lead">빠른 순서대로, 같으면 설거지가 적은 메뉴가 먼저예요.</p></div><button class="text-button" data-action="edit-ingredients">재료 수정</button></div>
    <div class="summary-strip">⌁ 기본 양념 ${BASIC_SEASONINGS.join(" · ")}은 있다고 계산했어요.</div>
    ${results.length ? `<div class="recipe-list">${results.map((r, i) => recipeCard(r, i)).join("")}</div>` : `<div class="empty-state"><span class="emoji">☁</span><h2>딱 맞는 요리가 없어요</h2><p class="lead">재료 이름이나 내 식탁 설정을 조금 바꿔보세요.</p><button class="primary full" style="margin-top:16px" data-action="edit-ingredients">재료 다시 보기</button></div>`}`;
}

function recipeCard(recipe, index) {
  return `<button class="recipe-card ${index === 0 ? "featured" : ""}" data-action="select-recipe" data-recipe-id="${recipe.id}">
    ${index === 0 ? `<span class="recipe-photo" aria-hidden="true"></span>` : ""}
    <span class="recipe-content"><span class="rank">${index === 0 ? "★ 오늘의 1순위" : `${index + 1}순위`}</span><h2 class="recipe-title">${recipe.title}</h2>
    <span class="chips">${recipe.ingredients.map(i => `<span class="chip ${isExpiring(i) ? "expiry" : ""}">${escapeHtml(i)}${isExpiring(i) ? " · 임박" : ""}</span>`).join("")}</span>
    <span class="recipe-metrics"><span class="metric">⏱ <strong>${recipe.minutes}분</strong></span><span class="metric">♨ 설거지 <strong>${recipe.dishes}개</strong></span></span></span>
  </button>`;
}

function renderCook() {
  const recipe = recipes.find(r => r.id === state.selectedRecipe);
  if (!recipe) { state.screen = "recommendations"; render(); return; }
  const step = recipe.steps[state.stepIndex];
  if (!state.timerRemaining && step.seconds) state.timerRemaining = step.seconds;
  screen.innerHTML = `
    <div class="cook-hero"><button class="back-button" data-action="back-results" aria-label="추천 목록으로">‹</button><h1>${recipe.title}</h1></div>
    <div class="progress-row"><span>STEP ${state.stepIndex + 1}/${recipe.steps.length}</span><div class="progress-track"><div class="progress-fill" style="width:${((state.stepIndex + 1) / recipe.steps.length) * 100}%"></div></div></div>
    <article class="step-card"><span class="step-number">${state.stepIndex + 1}</span><h2>${state.stepIndex + 1 === recipe.steps.length ? "거의 다 됐어요!" : "차근차근 따라 해요"}</h2><p>${step.text}</p>
      ${step.seconds ? `<div class="timer-box"><span class="timer-time" id="timer-time">${formatTime(state.timerRemaining)}</span><div class="timer-actions"><button data-action="toggle-timer">${state.timerRunning ? "일시 정지" : "타이머 시작"}</button><button data-action="reset-timer">초기화</button></div></div>` : ""}
    </article>
    <div class="step-actions"><button class="soft-button" data-action="prev-step" ${state.stepIndex === 0 ? "disabled" : ""}>이전</button><button class="primary" data-action="next-step">${state.stepIndex === recipe.steps.length - 1 ? "요리 완료" : "다음 단계"}</button></div>`;
  if (state.timerRunning) startTimer();
}

function startTimer() {
  clearInterval(timerId);
  timerId = setInterval(() => {
    state.timerRemaining = Math.max(0, state.timerRemaining - 1);
    const display = document.querySelector("#timer-time"); if (display) display.textContent = formatTime(state.timerRemaining);
    if (state.timerRemaining === 0) { clearInterval(timerId); state.timerRunning = false; showToast("타이머가 끝났어요! 다음 단계를 확인해요."); render(); }
  }, 1000);
}

function formatTime(seconds) { return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`; }

function renderComplete() {
  const recipe = recipes.find(r => r.id === state.selectedRecipe);
  screen.innerHTML = `<div class="complete-card"><div class="celebrate" aria-hidden="true">★ ♪</div><p class="eyebrow">COOKING COMPLETE</p><h1>${recipe.title}<br>완성했어요!</h1><p class="lead">실제로 사용한 만큼만 냉장고에서 빼둘게요.</p>
    <div class="usage-list">${recipe.ingredients.map(name => `<label class="usage-row"><span><strong>${name}</strong><br><small>예상 ${recipe.usage[name]}</small></span><select data-usage="${name}" aria-label="${name} 사용량"><option value="all">전부 사용</option><option value="part" selected>일부 사용</option><option value="none">사용 안 함</option></select></label>`).join("")}</div>
    <button class="primary full" data-action="save-usage">재고에 반영하기</button>
    <div class="rating"><h3>오늘 메뉴, 마음에 들었나요?</h3><div class="rating-actions"><button data-action="rate" data-rating="1" aria-label="좋았어요">♡</button><button data-action="rate" data-rating="-1" aria-label="아쉬웠어요">☂</button></div></div>
  </div>`;
}

function renderFridge() {
  screen.innerHTML = `<div class="section-head"><div><p class="eyebrow">MY FRIDGE</p><h1>우리 집 냉장고</h1><p class="lead">최근에 확인한 재료예요.</p></div></div>
    ${state.ingredients.length ? `<div class="inventory-list">${state.ingredients.map(i => `<div class="inventory-item"><div><strong>${escapeHtml(i.name)}</strong><br><small>${escapeHtml(i.qty || "수량 미입력")}</small></div><small>${i.expiry ? `~ ${i.expiry}` : "기한 미입력"}</small></div>`).join("")}</div>` : `<div class="empty-state"><span class="emoji">▦</span><h2>아직 비어 있어요</h2><p class="lead">냉장고 사진을 찍으면 재료가 여기에 모여요.</p><button class="primary full" style="margin-top:16px" data-action="go-home">사진 찍으러 가기</button></div>`}`;
}

function renderLikes() {
  const rated = recipes.filter(r => state.ratings[r.id]);
  screen.innerHTML = `<div class="section-head"><div><p class="eyebrow">MY TASTE</p><h1>내 취향 기록</h1><p class="lead">평가한 메뉴는 다음 추천 순서에 반영해요.</p></div></div>
    ${rated.length ? `<div class="likes-list">${rated.map(r => `<div class="like-item"><strong>${r.title}</strong><span>${state.ratings[r.id] > 0 ? "♡ 좋았어요" : "☂ 아쉬웠어요"}</span></div>`).join("")}</div>` : `<div class="empty-state"><span class="emoji">♡</span><h2>아직 평가한 메뉴가 없어요</h2><p class="lead">요리를 완성하고 취향을 알려주세요.</p></div>`}`;
}

function openSettings(onboarding = false) {
  const s = state.settings;
  settingsForm.elements.allergies.value = s.allergies;
  settingsForm.elements.restricted.value = s.restricted;
  settingsForm.elements.dislikes.value = s.dislikes;
  settingsForm.elements.diet.value = s.diet;
  [...settingsForm.querySelectorAll('[name="tools"]')].forEach(input => input.checked = s.tools.includes(input.value));
  dialog.dataset.onboarding = onboarding ? "true" : "false";
  dialog.showModal();
}

function showToast(message) {
  const toast = document.querySelector("#toast"); toast.textContent = message; toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2300);
}

document.addEventListener("change", event => {
  if (event.target.matches("#camera-input, #gallery-input")) startScan(event.target.files[0]);
});

document.addEventListener("click", event => {
  const target = event.target.closest("[data-action], [data-nav]"); if (!target) return;
  if (target.dataset.nav) { state.screen = target.dataset.nav; saveState(); render(); return; }
  const action = target.dataset.action;
  if (action === "go-home" || action === "rescan") { state.screen = "home"; render(); }
  if (action === "open-settings") openSettings(false);
  if (action === "use-sample") startScan(null);
  if (action === "add-ingredient") { syncIngredientsFromDom(); state.ingredients.push({ id: crypto.randomUUID(), name: "", qty: "", expiry: "", confidence: "high" }); renderIngredients(); document.querySelector(".ingredient-row:last-child .ingredient-name")?.focus(); }
  if (action === "remove-ingredient") { syncIngredientsFromDom(); state.ingredients = state.ingredients.filter(i => i.id !== target.closest(".ingredient-row").dataset.id); renderIngredients(); }
  if (action === "confirm-ingredients") { syncIngredientsFromDom(); if (!state.ingredients.length) { showToast("재료를 하나 이상 추가해 주세요."); return; } state.screen = "recommendations"; saveState(); render(); }
  if (action === "edit-ingredients") { state.screen = "ingredients"; render(); }
  if (action === "select-recipe") { state.selectedRecipe = target.dataset.recipeId; state.stepIndex = 0; state.timerRemaining = 0; state.timerRunning = false; state.screen = "cook"; saveState(); render(); }
  if (action === "back-results") { state.screen = "recommendations"; render(); }
  if (action === "prev-step") { state.stepIndex = Math.max(0, state.stepIndex - 1); state.timerRemaining = 0; state.timerRunning = false; render(); }
  if (action === "next-step") { const recipe = recipes.find(r => r.id === state.selectedRecipe); if (state.stepIndex < recipe.steps.length - 1) { state.stepIndex++; state.timerRemaining = 0; state.timerRunning = false; render(); } else { state.screen = "complete"; render(); } }
  if (action === "toggle-timer") { state.timerRunning = !state.timerRunning; render(); }
  if (action === "reset-timer") { const recipe = recipes.find(r => r.id === state.selectedRecipe); state.timerRemaining = recipe.steps[state.stepIndex].seconds || 0; state.timerRunning = false; render(); }
  if (action === "save-usage") { document.querySelectorAll("[data-usage]").forEach(select => { if (select.value === "all") state.ingredients = state.ingredients.filter(i => i.name !== select.dataset.usage); }); if (!state.completed.includes(state.selectedRecipe)) state.completed.push(state.selectedRecipe); saveState(); showToast("냉장고 재고에 반영했어요."); }
  if (action === "rate") { state.ratings[state.selectedRecipe] = Number(target.dataset.rating); saveState(); showToast(target.dataset.rating === "1" ? "좋아요! 다음 추천에 반영할게요." : "다음엔 더 잘 맞춰볼게요."); setTimeout(() => { state.screen = "home"; render(); }, 800); }
});

settingsForm.addEventListener("submit", event => {
  event.preventDefault();
  const data = new FormData(settingsForm);
  state.settings = { allergies: data.get("allergies").trim(), restricted: data.get("restricted").trim(), dislikes: data.get("dislikes").trim(), diet: data.get("diet").trim(), tools: data.getAll("tools") };
  if (!state.settings.tools.length) state.settings.tools = ["가스레인지", "전자레인지"];
  state.onboarded = true; saveState(); dialog.close(); showToast("내 식탁 설정을 저장했어요."); render();
});

dialog.addEventListener("cancel", event => {
  if (!state.onboarded) { event.preventDefault(); state.onboarded = true; saveState(); dialog.close(); render(); }
});

function registerWebMCP() {
  const context = document.modelContext;
  if (!context?.registerTool) return;
  const controller = new AbortController();
  const register = tool => Promise.resolve(context.registerTool(tool, { signal: controller.signal })).catch(() => {});
  const validateNoInput = input => {
    if (!input || typeof input !== "object" || Array.isArray(input) || Object.keys(input).length) throw new TypeError("입력값이 없는 객체여야 합니다.");
  };
  register({ name: "start_sample_fridge_scan", title: "샘플 냉장고 분석 시작", description: "샘플 재료로 냉장고 사진 분석 흐름을 시작하고 화면을 재료 확인 단계로 이동합니다.", inputSchema: { type: "object", properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false, untrustedContentHint: false }, async execute(input) { validateNoInput(input); state.ingredients = sampleIngredients.map(i => ({ ...i, id: crypto.randomUUID() })); state.screen = "ingredients"; saveState(); render(); return { screen: state.screen, ingredientCount: state.ingredients.length }; } });
  register({ name: "get_current_fridge", title: "현재 냉장고 읽기", description: "현재 확정된 냉장고 재료와 수량, 유통기한을 읽습니다.", inputSchema: { type: "object", properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true, untrustedContentHint: false }, async execute(input) { validateNoInput(input); return { ingredients: state.ingredients.map(({ name, qty, expiry }) => ({ name, qty, expiry })) }; } });
}

if ("serviceWorker" in navigator) window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
registerWebMCP();
render();
