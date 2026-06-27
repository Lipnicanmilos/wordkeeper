/* Informačná cookie lišta — nie je to súhlas (appka používa len nevyhnutné
   session cookie + funkčný localStorage, žiadne sledovanie). Zobrazí sa raz,
   po zatvorení sa uloží do localStorage a už sa neukáže. Dvojjazyčná (SK/EN). */
(function () {
  if (localStorage.getItem('cookieNoticeDismissed') === '1') return;

  var lang = localStorage.getItem('preferredLang') || 'sk';
  var T = {
    sk: {
      msg: 'Používame iba nevyhnutné cookies (prihlásenie) a localStorage (nastavenia, offline). Žiadne sledovanie ani reklamy.',
      more: 'Viac v Ochrane súkromia',
      ok: 'Rozumiem'
    },
    en: {
      msg: 'We use only essential cookies (login) and localStorage (preferences, offline). No tracking or ads.',
      more: 'More in Privacy Policy',
      ok: 'Got it'
    }
  };
  var t = T[lang] || T.sk;

  var bar = document.createElement('div');
  bar.id = 'cookieNotice';
  bar.setAttribute('role', 'region');
  bar.setAttribute('aria-label', 'Cookies');
  bar.style.cssText = [
    'position:fixed', 'left:0', 'right:0', 'bottom:0', 'z-index:9999',
    'background:rgba(15,23,42,.97)', 'color:#e2e8f0',
    'box-shadow:0 -4px 24px rgba(0,0,0,.25)',
    'padding:.85rem 1rem', 'display:flex', 'flex-wrap:wrap',
    'align-items:center', 'justify-content:center', 'gap:.75rem 1.25rem',
    'font-family:Inter,system-ui,sans-serif', 'font-size:.85rem', 'line-height:1.5'
  ].join(';');

  var text = document.createElement('span');
  text.style.cssText = 'max-width:760px;';
  text.textContent = t.msg + ' ';

  var link = document.createElement('a');
  link.href = '/privacy';
  link.textContent = t.more;
  link.style.cssText = 'color:#40ffaa;font-weight:600;text-decoration:none;';
  text.appendChild(link);

  var btn = document.createElement('button');
  btn.type = 'button';
  btn.textContent = t.ok;
  btn.style.cssText = [
    'background:linear-gradient(135deg,#4079ff,#40ffaa)', 'color:#0f172a',
    'border:none', 'border-radius:10px', 'padding:.55rem 1.25rem',
    'font-weight:700', 'font-size:.85rem', 'cursor:pointer', 'white-space:nowrap'
  ].join(';');
  btn.addEventListener('click', function () {
    localStorage.setItem('cookieNoticeDismissed', '1');
    bar.remove();
  });

  bar.appendChild(text);
  bar.appendChild(btn);
  document.body.appendChild(bar);
})();
