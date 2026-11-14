'use strict';

(() => {
  const byId = id => document.getElementById(id);
  const error = byId('error');
  const audio = byId('narration');
  const data = window.LESSON;
  const captionsToggle = byId('captions-toggle');
  let captionsVisible = true;
  try { captionsVisible = localStorage.getItem('syntrillium-captions') !== 'off'; } catch {}
  function setCaptionsVisible(visible) {
    captionsVisible = visible;
    byId('caption').hidden = !visible;
    captionsToggle.setAttribute('aria-pressed', String(visible));
    try { localStorage.setItem('syntrillium-captions', visible ? 'on' : 'off'); } catch {}
  }
  setCaptionsVisible(captionsVisible);
  // Navigation is independent of narration. Keep the native details fallback,
  // but defer removing `open` until its closing animation has finished.
  const lesson = byId('lesson');
  const navigation = byId('lesson-navigation');
  const navigationToggle = navigation.querySelector('summary');
  const navigationPanel = navigation.querySelector('nav');
  let navigationTimer;
  function setNavigationExpanded(expanded) {
    clearTimeout(navigationTimer);
    if (!expanded && navigationPanel.contains(document.activeElement)) navigationToggle.focus();
    const label = `${expanded ? 'Закрыть' : 'Открыть'} список уроков`;
    navigationToggle.setAttribute('aria-expanded', String(expanded));
    navigationToggle.setAttribute('aria-label', label);
    navigationToggle.title = label;
    navigationPanel.inert = !expanded;
    navigationPanel.setAttribute('aria-hidden', String(!expanded));
    if (expanded) {
      navigation.open = true;
      // Establish the closed frame when native details content reappears.
      navigationPanel.getBoundingClientRect();
    }
    navigation.dataset.expanded = String(expanded);
    lesson.dataset.navigationOpen = String(expanded);
    if (!expanded) {
      const duration = parseFloat(getComputedStyle(navigationPanel).transitionDuration) * 1000;
      navigationTimer = setTimeout(() => {
        if (navigation.dataset.expanded === 'false') navigation.open = false;
      }, duration + 30);
    }
  }
  navigationToggle.addEventListener('click', event => {
    event.preventDefault();
    setNavigationExpanded(navigation.dataset.expanded === 'false');
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !lesson.hidden && navigation.dataset.expanded !== 'false') {
      event.preventDefault();
      setNavigationExpanded(false);
    }
  });
  function showError(message) {
    byId('error-message').textContent = message;
    error.hidden = false;
  }
  if (!data?.utterances?.length && !data?.segments?.length) {
    showError('Не удалось открыть материалы урока. Распакуйте папку курса целиком и откройте её заново.');
    byId('open-lesson').disabled = true;
    return;
  }
  const utterances = data.utterances || data.segments;
  const starts = [];
  let total = 0;
  for (const utterance of utterances) { starts.push(total); total += utterance.duration; }
  let current = 0;
  let pendingOffset = 0;
  let finished = false;
  let shouldPlay = false;
  let seeking = false;
  let seekWasPlaying = false;
  let previewPosition = null;
  let pendingSeek = null;
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
  function draw(position, segmentIndex = current) {
    const utterance = utterances[segmentIndex];
    let frames = utterance.frames;
    let progress = Math.min(1, position / utterance.duration);
    let caption = utterance.caption;
    if (utterance.cues?.length) {
      let cueIndex = 0;
      while (cueIndex + 1 < utterance.cues.length && utterance.cues[cueIndex + 1].at <= position) cueIndex++;
      const cue = utterance.cues[cueIndex];
      const cueEnd = utterance.cues[cueIndex + 1]?.at ?? utterance.duration;
      frames = cue.frames;
      progress = Math.min(1, Math.max(0, (position - cue.at) / Math.max(0.001, cueEnd - cue.at)));
      caption = cue.caption;
    }
    let index = 0;
    while (index + 1 < frames.length && frames[index + 1].at <= progress) index++;
    const frame = frames[index];
    const items = segmentIndex === 0 && utterance.cues?.[0]?.frames === frames && index < 2
      ? frame.items.filter(item => item.asset !== 'ball')
      : frame.items;
    byId('visualization').innerHTML = `<desc>${escape(caption || utterance.caption)}</desc>${items.map(commandSvg).join('')}`;
  }

  const time = value => `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, '0')}`;
  byId('lesson-duration').textContent = time(total);
  function updatePosition() {
    const elapsed = previewPosition !== null
      ? previewPosition
      : (finished ? total : starts[current] + Math.min(audio.currentTime || 0, utterances[current].duration));
    byId('position').value = String(Math.round(elapsed / total * 1000));
    byId('position').setAttribute('aria-valuetext', `${time(elapsed)} из ${time(total)}`);
    byId('clock').textContent = `${time(elapsed)} / ${time(total)}`;
  }
  function animate(timestamp) {
    if (audio.paused || byId('lesson').hidden) return;
    if (timestamp - lastDraw > 60) {
      draw(audio.currentTime);
      lastDraw = timestamp;
    }
    animation = requestAnimationFrame(animate);
  }
  function updateControls() {
    const playing = shouldPlay && !finished;
    const toggle = byId('toggle');
    const icon = byId('toggle-icon');
    const label = playing ? 'Приостановить' : (finished ? 'Повторить' : 'Воспроизвести');
    icon.setAttribute('d', playing ? 'M7 5v14M17 5v14' : (finished ? 'M4 10a8 8 0 1 1 1 8M4 4v6h6' : 'M8 5v14l11-7Z'));
    toggle.setAttribute('aria-label', label);
    toggle.setAttribute('title', label);
    byId('previous').disabled = current === 0 && !finished;
    byId('next').disabled = current === utterances.length - 1;
    cancelAnimationFrame(animation);
    if (playing && !seeking && !audio.paused) animation = requestAnimationFrame(animate);
  }
  function play() {
    shouldPlay = true;
    updateControls();
    audio.play().catch(reason => {
      if (reason.name === 'AbortError') return;
      shouldPlay = false;
      showError('Не удалось начать воспроизведение. Нажмите значок воспроизведения ещё раз.');
      updateControls();
    });
  }
  function start(index, offset = 0, playing = true) {
    current = index;
    finished = false;
    shouldPlay = playing;
    previewPosition = null;
    pendingSeek = null;
    pendingOffset = Math.max(0, offset);
    error.hidden = true;
    byId('caption').textContent = utterances[current].caption || utterances[current].russian;
    audio.src = utterances[current].audio;
    audio.load();
    draw(pendingOffset);
    updateControls();
    updatePosition();
    if (playing) play();
  }
  function complete() {
    shouldPlay = false;
    audio.pause();
    finished = true;
    previewPosition = null;
    pendingSeek = null;
    updatePosition();
    updateControls();
  }
  function locate(position) {
    if (position >= total) {
      const index = utterances.length - 1;
      return {position: total, index, offset: utterances[index].duration};
    }
    const index = starts.findIndex((startTime, i) => position >= startTime && position < startTime + utterances[i].duration);
    const safeIndex = Math.max(0, index);
    return {position, index: safeIndex, offset: position - starts[safeIndex]};
  }
  function beginSeek() {
    if (seeking) return;
    seeking = true;
    seekWasPlaying = shouldPlay && !finished;
    finished = false;
    if (!audio.paused) audio.pause();
    updateControls();
  }
  function previewSeek(position) {
    beginSeek();
    const selection = locate(position);
    pendingSeek = selection;
    previewPosition = selection.position;
    byId('caption').textContent = utterances[selection.index].caption || utterances[selection.index].russian;
    draw(selection.offset, selection.index);
    updatePosition();
  }
  function commitSeek() {
    if (!seeking) return;
    const selection = pendingSeek || locate(Number(byId('position').value) / 1000 * total);
    const playing = seekWasPlaying;
    seeking = false;
    previewPosition = null;
    pendingSeek = null;
    if (selection.position >= total) {
      complete();
      return;
    }
    if (selection.index === current) {
      audio.currentTime = selection.offset;
      byId('caption').textContent = utterances[current].caption || utterances[current].russian;
      draw(selection.offset);
      updatePosition();
      shouldPlay = playing;
      updateControls();
      if (playing) play();
      return;
    }
    start(selection.index, selection.offset, playing);
  }
  let route = '';
  function syncRoute() {
    const nextRoute = location.hash === '#lesson/waveforms' ? 'lesson' : 'menu';
    if (nextRoute === route) return;
    if (nextRoute === 'lesson') {
      byId('menu').hidden = true;
      byId('lesson').hidden = false;
      route = nextRoute;
      start(0, 0, false);
      return;
    }
    shouldPlay = false;
    audio.pause();
    seeking = false;
    previewPosition = null;
    pendingSeek = null;
    byId('lesson').hidden = true;
    byId('menu').hidden = false;
    error.hidden = true;
    route = nextRoute;
  }
  window.addEventListener('hashchange', syncRoute);
  byId('open-lesson').addEventListener('click', () => { location.hash = 'lesson/waveforms'; });
  byId('back').addEventListener('click', () => { location.hash = ''; });
  captionsToggle.addEventListener('click', () => setCaptionsVisible(!captionsVisible));
  byId('toggle').addEventListener('click', () => {
    if (finished) start(0);
    else if (shouldPlay) {
      shouldPlay = false;
      audio.pause();
      updateControls();
    } else play();
  });
  byId('previous').addEventListener('click', () => start(Math.max(0, current - 1)));
  byId('next').addEventListener('click', () => start(Math.min(utterances.length - 1, current + 1)));
  byId('retry').addEventListener('click', () => start(current));
  byId('position').addEventListener('input', event => previewSeek(Number(event.target.value) / 1000 * total));
  byId('position').addEventListener('change', commitSeek);
  byId('position').addEventListener('pointerup', commitSeek);
  document.addEventListener('keydown', event => {
    if (event.code !== 'Space' || byId('lesson').hidden || event.target?.closest?.('button, summary, select, textarea, [contenteditable="true"]')) return;
    event.preventDefault();
    if (finished) start(0);
    else if (shouldPlay) {
      shouldPlay = false;
      audio.pause();
      updateControls();
    } else play();
  });
  audio.addEventListener('loadedmetadata', () => {
    audio.currentTime = Math.min(pendingOffset, Math.max(0, audio.duration - 0.01));
    updatePosition();
  });
  audio.addEventListener('play', updateControls);
  audio.addEventListener('pause', updateControls);
  audio.addEventListener('timeupdate', () => { updatePosition(); if (audio.paused && !seeking) draw(audio.currentTime); });
  audio.addEventListener('ended', () => { if (current + 1 < utterances.length) start(current + 1); else complete(); });
  audio.addEventListener('error', () => {
    showError('Не удалось открыть запись. Убедитесь, что папка урока распакована целиком, и повторите.');
    updateControls();
  });
  syncRoute();
})();
