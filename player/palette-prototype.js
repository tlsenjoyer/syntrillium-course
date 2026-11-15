/* PROTOTYPE: compare palettes without changing the released player. */
(() => {
  const palettes = [
    ['slate', 'Сланец и синий', ['#f4f6f8', '#dbe4ee', '#eef2f6', '#285490']],
    ['ivory', 'Слоновая кость и терракота', ['#faf6ef', '#e8d9c6', '#f2e9dc', '#934425']],
    ['mint', 'Мята и хвойный', ['#f2f7f5', '#cce1da', '#e5f0eb', '#176553']],
    ['original', 'Текущая палитра', ['#f4f5eb', '#7c94ab', '#d4dfbd', '#314b87']],
  ];
  let index = Math.max(0, palettes.findIndex(([key]) => key === new URL(location.href).searchParams.get('variant')));
  const bar = document.createElement('aside');
  bar.className = 'palette-switcher';
  bar.setAttribute('aria-label', 'Прототип: сравнение палитр');
  bar.innerHTML = `<div class="palette-row"><button type="button" aria-label="Предыдущая палитра"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m14 6-6 6 6 6"/></svg></button><div><div class="palette-name" aria-live="polite"></div><div class="palette-colors" aria-hidden="true"></div></div><button type="button" aria-label="Следующая палитра"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m10 6 6 6-6 6"/></svg></button></div><p class="palette-note">Прототип · цвет интерфейса · 4 варианта</p>`;
  document.body.append(bar);
  function render() {
    const [key, name, colors] = palettes[index];
    document.documentElement.dataset.palette = key;
    bar.querySelector('.palette-name').textContent = `${index + 1}/4 · ${name}`;
    bar.querySelector('.palette-colors').innerHTML = colors.map(color => `<i style="--swatch:${color}" title="${color}"></i>`).join('');
    const url = new URL(location.href);
    url.searchParams.set('variant', key);
    history.replaceState(null, '', url);
  }
  function cycle(step) { index = (index + step + palettes.length) % palettes.length; render(); }
  bar.querySelectorAll('button')[0].onclick = () => cycle(-1);
  bar.querySelectorAll('button')[1].onclick = () => cycle(1);
  // Arrow shortcuts are scoped to the prototype bar, preserving playback seeking.
  bar.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault(); cycle(event.key === 'ArrowLeft' ? -1 : 1);
    }
  });
  window.addEventListener('popstate', () => {
    index = Math.max(0, palettes.findIndex(([key]) => key === new URL(location.href).searchParams.get('variant'))); render();
  });
  render();
})();
