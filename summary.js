const summaryButton = document.createElement('button');
summaryButton.type = 'button';
summaryButton.textContent = 'Resumir com Qwen';
paneEl.querySelector('.hint').before(summaryButton);
summaryButton.addEventListener('pointerdown', event => event.stopPropagation());
summaryButton.addEventListener('click', () => {
  const card = reader.card;
  if (!card || summaryButton.disabled) return;
  closeReader();
  summarize(card);
});

let summaryPending = false;

async function summarize(card) {
  if (summaryPending) return;
  LAST_SUM = card.title;
  if (Q.has('probe')) return;
  summaryPending = true;
  summaryButton.disabled = true;

  document.querySelectorAll('.tldr').forEach(element => element.remove());
  const panel = document.createElement('div');
  panel.className = 'tldr show';
  panel.setAttribute('role', 'status');
  const heading = document.createElement('b');
  heading.textContent = 'Resumo · ' + card.title;
  const body = document.createElement('p');
  body.textContent = 'A gerar resumo…';
  panel.append(heading, body);
  panel.style.left = Math.max(8, Math.min(W - 300, card.x - 135)) + 'px';
  panel.style.top = Math.max(8, Math.min(H - 240, card.y - 60)) + 'px';
  document.getElementById('deck').appendChild(panel);

  try {
    const response = await fetch('/api/summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: (card.full || card.body || card.title).slice(0, 4000) })
    });
    const result = await response.json();
    if (!response.ok) {
      body.textContent = result.error;
      return;
    }
    body.textContent = result.summary;
    postState('sum', card.title);
    addAudioButton(panel, 'Ouvir resumo', result.summary);
  } catch {
    body.textContent = 'Não foi possível contactar o servidor local.';
  } finally {
    summaryPending = false;
    summaryButton.disabled = false;
    setTimeout(() => panel.remove(), 20000);
  }
}
function addAudioButton(container, label, text) {
  if (!('speechSynthesis' in window)) return;

  const listen = document.createElement('button');
  listen.type = 'button';
  listen.style.pointerEvents = 'auto';
  listen.addEventListener('pointerdown', event => event.stopPropagation());
  listen.textContent = label;
  const feedback = document.createElement('p');
  feedback.setAttribute('aria-live', 'polite');
  container.append(listen, feedback);

  listen.addEventListener('click', () => {
    const voices = window.speechSynthesis.getVoices();
    const portuguese = voices.filter(voice => voice.localService && /^pt(?:-|_)/i.test(voice.lang));
    const voice = portuguese.find(voice => /^pt[-_]pt$/i.test(voice.lang)) || portuguese[0];
    if (!voice) {
      feedback.textContent = 'Ativa uma voz de português no Windows para usar a leitura em voz alta.';
      return;
    }

    const speech = new SpeechSynthesisUtterance(text);
    speech.voice = voice;
    speech.lang = voice.lang;
    speech.onerror = event => {
      if (event.error !== 'interrupted' && event.error !== 'canceled') {
        feedback.textContent = 'Não foi possível reproduzir o áudio.';
      }
    };
    feedback.textContent = '';
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(speech);
  });
}

const questionForm = document.createElement('form');
questionForm.style.marginTop = '16px';
const questionLabel = document.createElement('label');
questionLabel.htmlFor = 'note-question';
questionLabel.textContent = 'Pergunta sobre esta nota';
const questionInput = document.createElement('input');
questionInput.id = questionLabel.htmlFor;
questionInput.required = true;
questionInput.maxLength = 500;
questionInput.style.cssText = 'display:block;width:100%;margin:6px 0;padding:8px';
const askButton = document.createElement('button');
askButton.type = 'submit';
askButton.textContent = 'Perguntar';
const answerBox = document.createElement('p');
answerBox.setAttribute('role', 'status');
answerBox.style.cssText = 'margin-top:8px;white-space:pre-wrap;overflow-wrap:anywhere';
const answerAudio = document.createElement('div');
questionForm.append(questionLabel, questionInput, askButton, answerBox, answerAudio);
paneEl.querySelector('.hint').before(questionForm);
questionForm.addEventListener('pointerdown', event => event.stopPropagation());
questionForm.addEventListener('keydown', event => {
  if (event.key !== 'Escape') event.stopPropagation();
});

let questionRequest;
const openNote = openReader;
openReader = function (card) {
  questionRequest?.abort();
  questionRequest = undefined;
  questionForm.reset();
  askButton.disabled = false;
  answerBox.textContent = '';
  answerAudio.replaceChildren();
  openNote(card);
};

questionForm.addEventListener('submit', async event => {
  event.preventDefault();
  const question = questionInput.value.trim();
  const card = reader.card;
  if (!question || !card || questionRequest) return;

  const request = new AbortController();
  questionRequest = request;
  askButton.disabled = true;
  answerAudio.replaceChildren();
  answerBox.textContent = 'A consultar a nota…';
  try {
    const response = await fetch('/api/question', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: (card.full || card.body || card.title).slice(0, 4000), question }),
      signal: request.signal
    });
    const result = await response.json();
    if (questionRequest === request) {
      answerBox.textContent = response.ok ? result.answer : result.error;
      if (response.ok) addAudioButton(answerAudio, 'Ouvir resposta', result.answer);
    }
  } catch {
    if (questionRequest === request) {
      answerBox.textContent = 'Não foi possível contactar o servidor local.';
    }
  } finally {
    if (questionRequest === request) {
      questionRequest = undefined;
      askButton.disabled = false;
    }
  }
});
