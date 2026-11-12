'use strict';

(() => {
  const byId = id => document.getElementById(id);
  const error = byId('error');
  const status = byId('playback-status');
  const audio = byId('narration');
  const data = window.LESSON;
  function showError(message) {
    byId('error-message').textContent = message;
    error.hidden = false;
  }
  if (!data?.segments?.length) {
    showError('Не удалось открыть материалы урока. Распакуйте папку курса целиком и откройте её заново.');
    byId('open-lesson').disabled = true;
    return;
  }
  const segments = data.segments;
  const starts = [];
  let total = 0;
  for (const segment of segments) { starts.push(total); total += segment.duration; }
  let current = 0;
  let pendingOffset = 0;
  let finished = false;
  let animation = 0;
  let lastDraw = 0;
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  function commandSvg(item) {
    const {x, y, width, height} = item;
    let shape;
    switch (item.kind) {
      case 'image':
        shape = `<image href="assets/${item.asset}.svg" x="${x}" y="${y}" width="${width}" height="${height}" preserveAspectRatio="none"/>`;
        break;
      case 'text':
        shape = `<text x="${x}" y="${y}" text-anchor="middle" font-size="${item.font_size}">${item.lines.map((value, i) => `<tspan x="${x}" dy="${i ? item.font_size * 1.15 : 0}">${escape(value)}</tspan>`).join('')}</text>`;
        break;
      case 'line':
        shape = `<path d="M${item.x1} ${item.y1}L${item.x2} ${item.y2}" stroke="${item.color}" stroke-width="${item.stroke_width}" fill="none"/>`;
        break;
      case 'ellipse':
        shape = `<ellipse cx="${item.cx}" cy="${item.cy}" rx="${item.rx}" ry="${item.ry}" fill="${item.color}"/>`;
        break;
      case 'amplitude-bracket':
        shape = `<path d="M${x + width / 2} ${y - height / 2}H${x - width / 2}V${y + height / 2}H${x + width / 2}" fill="none" stroke="#111" stroke-width="2"/>`;
        break;
      case 'wavelength-bracket':
        shape = `<path d="M${x - width / 2} ${y - height / 2}V${y + height / 2}H${x + width / 2}V${y - height / 2}" fill="none" stroke="#111" stroke-width="2"/>`;
        break;
      case 'symbol':
        shape = `<text x="${x}" y="${y}" text-anchor="middle" font-size="${item.font_size}">${escape(item.value)}</text>`;
        break;
      default:
        throw new Error('Unrecognized lesson drawing command');
    }
    return `<g opacity="${item.opacity}">${shape}</g>`;
  }
  function draw(progress) {
    const frames = segments[current].frames;
    let index = 0;
    while (index + 1 < frames.length && frames[index + 1].at <= progress) index++;
    byId('visualization').innerHTML = `<title>${escape(segments[current].caption)}</title>${frames[index].items.map(commandSvg).join('')}`;
  }

  const time = value => `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, '0')}`;
  function updatePosition() {
    const elapsed = finished ? total : starts[current] + Math.min(audio.currentTime || 0, segments[current].duration);
    byId('position').value = String(Math.round(elapsed / total * 1000));
    byId('position').setAttribute('aria-valuetext', `${time(elapsed)} из ${time(total)}`);
    byId('clock').textContent = `${time(elapsed)} / ${time(total)}`;
  }
  function animate(timestamp) {
    if (audio.paused || byId('lesson').hidden) return;
    if (timestamp - lastDraw > 60) {
      draw(Math.min(1, audio.currentTime / (audio.duration || segments[current].duration)));
      lastDraw = timestamp;
    }
    animation = requestAnimationFrame(animate);
  }
  function updateControls() {
    const playing = !audio.paused && !finished;
    byId('toggle').textContent = playing ? 'Пауза' : (finished ? 'Повторить' : 'Продолжить');
    byId('toggle').setAttribute('aria-label', playing ? 'Приостановить' : (finished ? 'Повторить урок' : 'Продолжить'));
    byId('previous').disabled = current === 0 && !finished;
    byId('next').disabled = current === segments.length - 1;
    cancelAnimationFrame(animation);
    if (playing) animation = requestAnimationFrame(animate);
  }
  function play() {
    audio.play().catch(reason => {
      if (reason.name === 'AbortError') return;
      status.textContent = 'Нажмите «Продолжить», чтобы включить запись.';
      updateControls();
    });
  }
  function start(index, offset = 0, playing = true) {
    current = index;
    finished = false;
    pendingOffset = Math.max(0, offset);
    byId('completion').hidden = true;
    error.hidden = true;
    byId('caption').textContent = segments[current].caption;
    audio.src = segments[current].audio;
    audio.load();
    draw(pendingOffset / segments[current].duration);
    updateControls();
    updatePosition();
    if (playing) play();
  }
  function complete() {
    audio.pause();
    finished = true;
    byId('completion').hidden = false;
    status.textContent = '';
    updatePosition();
    updateControls();
  }
  byId('open-lesson').addEventListener('click', () => {
    byId('menu').hidden = true;
    byId('lesson').hidden = false;
    start(0);
    byId('toggle').focus();
  });
  byId('back').addEventListener('click', () => {
    audio.pause();
    byId('lesson').hidden = true;
    byId('menu').hidden = false;
    error.hidden = true;
    byId('open-lesson').focus();
  });
  byId('toggle').addEventListener('click', () => {
    if (finished) start(0);
    else if (audio.paused) play();
    else audio.pause();
  });
  byId('previous').addEventListener('click', () => start(Math.max(0, current - 1)));
  byId('next').addEventListener('click', () => start(Math.min(segments.length - 1, current + 1)));
  byId('replay').addEventListener('click', () => start(0));
  byId('retry').addEventListener('click', () => start(current));
  byId('position').addEventListener('input', event => {
    const position = Number(event.target.value) / 1000 * total;
    if (position >= total) { complete(); return; }
    const next = starts.findIndex((startTime, i) => position >= startTime && position < startTime + segments[i].duration);
    start(Math.max(0, next), position - starts[Math.max(0, next)], !audio.paused || finished);
  });
  audio.addEventListener('loadedmetadata', () => {
    audio.currentTime = Math.min(pendingOffset, Math.max(0, audio.duration - 0.01));
    updatePosition();
  });
  audio.addEventListener('play', () => { status.textContent = 'Воспроизведение'; updateControls(); });
  audio.addEventListener('pause', () => { if (!finished) status.textContent = 'Приостановлено'; updateControls(); });
  audio.addEventListener('timeupdate', () => { updatePosition(); if (audio.paused) draw(audio.currentTime / (audio.duration || segments[current].duration)); });
  audio.addEventListener('ended', () => { if (current + 1 < segments.length) start(current + 1); else complete(); });
  audio.addEventListener('error', () => {
    showError('Не удалось открыть запись. Убедитесь, что папка урока распакована целиком, и повторите.');
    updateControls();
  });
})();
