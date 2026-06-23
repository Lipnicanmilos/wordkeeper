/* LexiNova – globálna pätička: odkaz na autora + formulár "Zanechať dotaz".
   Jeden súbor, ktorý sa pridá pred </body> na všetkých stránkach. */
(function () {
  if (window.__lexinovaFooterLoaded) return;
  window.__lexinovaFooterLoaded = true;

  var css = `
  .ln-footer{margin-top:auto;padding:1.5rem 1.25rem;border-top:1px solid rgba(128,128,128,.2);
    font-size:.82rem;color:#64748b;background:transparent;}
  [data-theme="dark"] .ln-footer{color:#94a3b8;border-top-color:rgba(255,255,255,.08);}
  .ln-footer-inner{max-width:1100px;margin:0 auto;display:flex;align-items:center;
    justify-content:space-between;flex-wrap:wrap;gap:.75rem 1.25rem;}
  .ln-footer-links{display:flex;gap:1.25rem;flex-wrap:wrap;align-items:center;}
  .ln-footer a, .ln-footer button.ln-link{color:inherit;text-decoration:none;background:none;
    border:none;cursor:pointer;font-size:inherit;font-family:inherit;padding:0;transition:color .2s;}
  .ln-footer a:hover, .ln-footer button.ln-link:hover{color:#4079ff;}
  @media(max-width:640px){.ln-footer-inner{flex-direction:column;text-align:center;}}

  .ln-overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;
    align-items:center;justify-content:center;z-index:9999;padding:1rem;}
  .ln-overlay.open{display:flex;}
  .ln-modal{background:#fff;color:#0f172a;border-radius:16px;padding:1.75rem;
    width:100%;max-width:440px;box-shadow:0 20px 60px rgba(0,0,0,.25);max-height:90vh;overflow:auto;}
  [data-theme="dark"] .ln-modal{background:#1e293b;color:#e2e8f0;}
  .ln-modal h3{margin:0 0 .25rem;font-size:1.25rem;}
  .ln-modal p.ln-sub{margin:0 0 1rem;font-size:.85rem;color:#64748b;}
  [data-theme="dark"] .ln-modal p.ln-sub{color:#94a3b8;}
  .ln-modal label{display:block;font-weight:600;font-size:.8rem;margin:.7rem 0 .3rem;}
  .ln-modal input, .ln-modal textarea{width:100%;box-sizing:border-box;padding:.65rem .8rem;
    border:1px solid rgba(128,128,128,.35);border-radius:10px;font-size:.9rem;font-family:inherit;
    background:rgba(255,255,255,.6);color:inherit;}
  [data-theme="dark"] .ln-modal input,[data-theme="dark"] .ln-modal textarea{background:rgba(15,23,42,.6);}
  .ln-modal textarea{min-height:110px;resize:vertical;}
  .ln-modal-actions{display:flex;gap:.6rem;margin-top:1.2rem;}
  .ln-btn{flex:1;padding:.7rem 1rem;border-radius:10px;border:none;font-weight:700;cursor:pointer;font-size:.9rem;}
  .ln-btn-primary{background:#4079ff;color:#fff;}
  .ln-btn-primary:disabled{opacity:.6;cursor:not-allowed;}
  .ln-btn-ghost{background:rgba(128,128,128,.15);color:inherit;}
  .ln-status{margin-top:.8rem;font-size:.85rem;display:none;}
  .ln-status.ok{display:block;color:#16a34a;}
  .ln-status.err{display:block;color:#dc2626;}
  `;

  var html = `
  <footer class="ln-footer">
    <div class="ln-footer-inner">
      <span>© 2025 LexiNova · <a href="https://lipnicanmilos.github.io/" target="_blank" rel="noopener">Miloš Lipničan</a></span>
      <div class="ln-footer-links">
        <button type="button" class="ln-link" id="lnInquiryOpen">✉️ Zanechať dotaz</button>
        <a href="https://lipnicanmilos.github.io/" target="_blank" rel="noopener">Autor</a>
      </div>
    </div>
  </footer>

  <div class="ln-overlay" id="lnOverlay">
    <div class="ln-modal" role="dialog" aria-modal="true">
      <h3>Zanechať dotaz</h3>
      <p class="ln-sub">Napíšte nám správu — ozveme sa vám e-mailom.</p>
      <label for="lnName">Meno</label>
      <input id="lnName" type="text" maxlength="120" placeholder="Vaše meno (nepovinné)">
      <label for="lnEmail">E-mail</label>
      <input id="lnEmail" type="email" maxlength="255" placeholder="vas@email.com (aby sme vám odpovedali)">
      <label for="lnMessage">Správa *</label>
      <textarea id="lnMessage" maxlength="4000" placeholder="Vaša otázka alebo postreh…"></textarea>
      <div class="ln-status" id="lnStatus"></div>
      <div class="ln-modal-actions">
        <button type="button" class="ln-btn ln-btn-ghost" id="lnCancel">Zrušiť</button>
        <button type="button" class="ln-btn ln-btn-primary" id="lnSend">Odoslať</button>
      </div>
    </div>
  </div>
  `;

  function init() {
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    var wrap = document.createElement('div');
    wrap.innerHTML = html;
    document.body.appendChild(wrap);

    var overlay = document.getElementById('lnOverlay');
    var statusEl = document.getElementById('lnStatus');
    var sendBtn = document.getElementById('lnSend');

    function open() { statusEl.className = 'ln-status'; statusEl.textContent = ''; overlay.classList.add('open'); }
    function close() { overlay.classList.remove('open'); }

    document.getElementById('lnInquiryOpen').addEventListener('click', open);
    document.getElementById('lnCancel').addEventListener('click', close);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });

    sendBtn.addEventListener('click', async function () {
      var msg = document.getElementById('lnMessage').value.trim();
      if (msg.length < 2) {
        statusEl.className = 'ln-status err';
        statusEl.textContent = 'Napíšte prosím správu.';
        return;
      }
      sendBtn.disabled = true;
      statusEl.className = 'ln-status';
      statusEl.textContent = 'Odosielam…';
      try {
        var res = await fetch('/api/inquiry', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: document.getElementById('lnName').value.trim(),
            email: document.getElementById('lnEmail').value.trim(),
            message: msg,
            page: window.location.pathname
          })
        });
        if (res.ok) {
          statusEl.className = 'ln-status ok';
          statusEl.textContent = 'Ďakujeme! Dotaz bol odoslaný.';
          document.getElementById('lnName').value = '';
          document.getElementById('lnEmail').value = '';
          document.getElementById('lnMessage').value = '';
          setTimeout(close, 1500);
        } else {
          statusEl.className = 'ln-status err';
          statusEl.textContent = 'Nepodarilo sa odoslať. Skúste znova.';
        }
      } catch (e) {
        statusEl.className = 'ln-status err';
        statusEl.textContent = 'Chyba siete. Skúste znova.';
      } finally {
        sendBtn.disabled = false;
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
