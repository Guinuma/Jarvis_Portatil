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
    addSummaryAudio(panel, result.summary);
  } catch {
    body.textContent = 'Não foi possível contactar o servidor local.';
  } finally {
    summaryPending = false;
    summaryButton.disabled = false;
    setTimeout(() => panel.remove(), 20000);
  }
}
function addSummaryAudio(panel, summary) {
  if (!('speechSynthesis' in window)) return;

  const listen = document.createElement('button');
  listen.type = 'button';
  listen.style.pointerEvents = 'auto';
  listen.addEventListener('pointerdown', event => event.stopPropagation());
  listen.textContent = 'Ouvir resumo';
  const feedback = document.createElement('p');
  feedback.setAttribute('aria-live', 'polite');
  panel.append(listen, feedback);

  listen.addEventListener('click', () => {
    const voices = window.speechSynthesis.getVoices();
    const portuguese = voices.filter(voice => voice.localService && /^pt(?:-|_)/i.test(voice.lang));
    const voice = portuguese.find(voice => /^pt[-_]pt$/i.test(voice.lang)) || portuguese[0];
    if (!voice) {
      feedback.textContent = 'Ativa uma voz de português no Windows para ouvir o resumo.';
      return;
    }

    const speech = new SpeechSynthesisUtterance(summary);
    speech.voice = voice;
    speech.lang = voice.lang;
    speech.onerror = event => {
      if (event.error !== 'interrupted' && event.error !== 'canceled') {
        feedback.textContent = 'Não foi possível reproduzir o resumo.';
      }
    };
    feedback.textContent = '';
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(speech);
  });
}
