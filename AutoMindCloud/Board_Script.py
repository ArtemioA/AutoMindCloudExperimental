# Google Colab drawing board that plays a bundled click_sound.mp3 (base64) when
# any toolbar button is pressed. The audio is read into a global `b64_audio`
# variable (so you don't need to pass it to board()).
#
# Usage:
# 1) Put a file named "click_sound.mp3" next to this cell (or change the path).
# 2) Run this cell to define the board and the global b64_audio.
# 3) Call board("Dibujo 1") and click any toolbar button to hear the sound.
#
# Note: browser autoplay policies may block immediate playback; the player
# will still be shown so the user can press play.

from IPython.display import HTML, display, Audio
from google.colab import output
import re, base64, os, uuid

# Read and encode the mp3 file into global b64_audio (if the file exists).
b64_audio = None
_audio_filename = "click_sound.mp3"
if os.path.exists(_audio_filename):
    try:
        with open(_audio_filename, "rb") as _f:
            b64_audio = base64.b64encode(_f.read()).decode("ascii")
    except Exception:
        b64_audio = None

_SNAPSHOT_HANDLES = {}          # serial -> DisplayHandle (bloque oculto/externo con display_id)
_REGISTERED_CALLBACKS = set()   # callbacks registrados

def _sanitize_serial(s: str) -> str:
    s = (s or "board").strip()
    s = re.sub(r'[^A-Za-z0-9_]+', '_', s)
    return s or "board"

def _make_snapshot_callback(serial: str):
    container_id = f"amc_persisted_snapshot_container_{serial}"
    img_id = f"amc_persisted_snapshot_{serial}"
    png_path = f"/content/pizarra_cell_{serial}.png"

    def _cb(data_url_png: str):
        m = re.match(r'^data:image/png;base64,(.*)$', data_url_png or '')
        if m:
            try:
                with open(png_path, "wb") as f:
                    f.write(base64.b64decode(m.group(1)))
            except Exception:
                pass

        html = f"""
        <div id="{container_id}" aria-hidden="true"
             style="position:fixed; left:-9999px; top:-9999px; width:1px; height:1px; opacity:0; overflow:hidden; padding:0; margin:0; border:0; user-select:none; pointer-events:none;">
          <div style="font:0/0; height:0; overflow:hidden">Último dibujo (persistente)</div>
          <img id="{img_id}" src="{data_url_png}" alt="persisted snapshot" style="width:1px; height:1px; border:0; display:block" />
        </div>
        """
        handle = _SNAPSHOT_HANDLES.get(serial)
        if handle is None:
            _SNAPSHOT_HANDLES[serial] = display(HTML(html), display_id=True)
        else:
            handle.update(HTML(html))

        try:
            from google.colab import _message
            _message.blocking_request('notebook.save', {})
        except Exception:
            pass

        return {"ok": True}

    return _cb

def _ensure_callback_registered(serial: str):
    name = f"persist.pushSnapshot.{serial}"
    if name not in _REGISTERED_CALLBACKS:
        output.register_callback(name, _make_snapshot_callback(serial))
        _REGISTERED_CALLBACKS.add(name)
    return name

def _file_to_dataurl(path: str) -> str:
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return "data:image/png;base64," + b64
    except Exception:
        return ""

def _extract_snapshot_from_ipynb(serial: str) -> str:
    try:
        from google.colab import _message
        nbwrap = _message.blocking_request('get_ipynb', {}) or {}
        nb = nbwrap.get('ipynb', nbwrap) or {}
        ids = [
            f"amc_persisted_snapshot_{serial}",
            f"amc_persisted_snapshot_ext_{serial}",
            f"amc_persisted_snapshot_int_{serial}",
        ]
        pat = re.compile(
            r'id=["\'](' + '|'.join(map(re.escape, ids)) + r')["\']\s+[^>]*src=["\'](data:image/[^"\']+)["\']',
            re.IGNORECASE
        )
        for cell in reversed(nb.get('cells', [])):
            for out in reversed(cell.get('outputs', [])):
                data = out.get('data', {})
                html = None
                if 'text/html' in data:
                    v = data['text/html']
                    html = ''.join(v) if isinstance(v, list) else (v or '')
                elif 'text' in data:
                    v = data['text']
                    html = ''.join(v) if isinstance(v, list) else (v or '')
                if html:
                    m = None
                    for m in pat.finditer(html):
                        pass
                    if m:
                        src = m.group(2)
                        if src.startswith('data:image/'):
                            return src
        return ""
    except Exception:
        return ""

# --------------------
# Button-pressed callback registration (uses global b64_audio if available)
# --------------------
def _make_button_pressed_callback(serial: str, provided_b64_audio: str = None):
    """
    Returns a callback that runs in the Python kernel when a toolbar button
    is pressed. It prints "button pressed" and, if an audio base64 is available
    (either provided_b64_audio or the global b64_audio), decodes it to an MP3
    file under /content and displays an audio player (autoplay requested).
    """
    def _cb(*args, **kwargs):
        print("button pressed")
        # prefer explicitly provided b64, else check the module/global b64_audio
        audio_b64 = provided_b64_audio if provided_b64_audio is not None else globals().get('b64_audio')

        if not audio_b64:
            return {"ok": True}

        try:
            # Accept either a full data URL or raw base64
            m = re.match(r'^data:audio/[^;]+;base64,(.*)$', audio_b64 or '')
            b64 = m.group(1) if m else audio_b64

            mp3_path = f"/content/pizarra_audio_{serial}.mp3"
            with open(mp3_path, "wb") as f:
                f.write(base64.b64decode(b64))

            # Try to display an audio player that requests autoplay.
            # Note: browsers may block autoplay; controls will still be shown.
            try:
                display(Audio(mp3_path, autoplay=True))
            except Exception:
                # Fallback to an HTML <audio> element
                try:
                    display(HTML(f'<audio controls autoplay><source src="file://{mp3_path}" type="audio/mpeg">Your browser does not support the audio element.</audio>'))
                except Exception as e:
                    print("Saved audio to", mp3_path, "but could not render player:", e)

        except Exception as e:
            print("Error decoding/playing audio:", str(e))

        return {"ok": True}
    return _cb

def _ensure_button_pressed_registered(serial: str, provided_b64_audio: str = None):
    """
    Register a unique callback name for this board instance so re-calling
    board(...) registers a fresh callback and the JS side gets the correct name.
    """
    unique_suffix = uuid.uuid4().hex
    name = f"persist.buttonPressed.{serial}.{unique_suffix}"
    output.register_callback(name, _make_button_pressed_callback(serial, provided_b64_audio))
    _REGISTERED_CALLBACKS.add(name)
    return name

# --------------------
# Main board function (does not require passing audio)
# --------------------
def board(serial: str = "board"):
    serial = _sanitize_serial(serial)
    cb_name = _ensure_callback_registered(serial)
    # Register the "button pressed" callback and get name to expose to JS.
    # We do NOT pass audio here; the callback will pick up the global b64_audio.
    button_cb_name = _ensure_button_pressed_registered(serial, None)

    STORAGE_KEY  = f"amc_pizarra_snapshot_dataurl_{serial}"
    IMG_ID       = f"amc_persisted_snapshot_{serial}"
    CONTAINER_ID = f"amc_persisted_snapshot_container_{serial}"
    PNG_PATH     = f"/content/pizarra_cell_{serial}.png"

    initial_data_url = _extract_snapshot_from_ipynb(serial) or _file_to_dataurl(PNG_PATH)

    js_code = f"""
<script>
(function(){{
  const STORAGE_KEY   = "{STORAGE_KEY}";
  const CALLBACK_NAME = "{cb_name}";
  const BUTTON_CB_NAME = "{button_cb_name}";
  const IMG_ID        = "{IMG_ID}";
  const INITIAL_DATA_URL = {('"%s"' % initial_data_url) if initial_data_url else '""'};
  const MAX_HISTORY = 40;

  const canvas = document.getElementById('board_{serial}');
  const ctx = canvas.getContext('2d');
  const colorEl = document.getElementById('color_{serial}');
  const sizeEl  = document.getElementById('size_{serial}');
  let drawing=false, last={{x:0,y:0}}, tool='pen', dpr=window.devicePixelRatio||1;

  const undoStack = [];
  const redoStack = [];

  function pushHistory(dataURL=null){{
    try {{
      const snap = dataURL || canvas.toDataURL('image/png');
      undoStack.push(snap);
      while (undoStack.length > MAX_HISTORY) undoStack.shift();
      redoStack.length = 0;
    }} catch(_) {{}}
  }}

  function drawFromDataURL(dataURL){{
    if(!dataURL) return;
    const im = new Image();
    im.onload = () => {{
      ctx.save();
      ctx.globalCompositeOperation='source-over';
      ctx.drawImage(im,0,0,im.naturalWidth,im.naturalHeight,0,0,canvas.width,canvas.height);
      ctx.restore();
    }};
    im.src = dataURL;
  }}

  function doUndo(){{
    if (undoStack.length === 0) return;
    const current = canvas.toDataURL('image/png');
    const prev = undoStack.pop();
    redoStack.push(current);
    drawFromDataURL(prev);
    schedulePersist();
  }}

  function doRedo(){{
    if (redoStack.length === 0) return;
    const current = canvas.toDataURL('image/png');
    const next = redoStack.pop();
    undoStack.push(current);
    drawFromDataURL(next);
    schedulePersist();
  }}

  function initCanvas(w,h){{ canvas.width=w; canvas.height=h; ctx.lineJoin="round"; ctx.lineCap="round"; ctx.fillStyle="#fff"; ctx.fillRect(0,0,w,h); }}
  function firstLayout(){{ const w=Math.max(1,canvas.clientWidth*dpr); const h=Math.max(1,canvas.clientHeight*dpr); initCanvas(w,h); }}
  function resize(){{ const w=Math.max(1,canvas.clientWidth*dpr); const h=Math.max(1,canvas.clientHeight*dpr); const tmp = document.createElement('canvas'); tmp.width = canvas.width; tmp.height = canvas.height; tmp.getContext('2d').drawImage(canvas,0,0); initCanvas(w,h); ctx.drawImage(tmp,0,0,w,h); }}
  setTimeout(firstLayout,0); window.addEventListener('resize', resize);

  function pos(e){{ const r=canvas.getBoundingClientRect(); return {{x:(e.clientX-r.left)*dpr, y:(e.clientY-r.top)*dpr}}; }}
  function line(a,b){{ ctx.save(); ctx.globalCompositeOperation=(tool==='eraser'?'destination-out':'source-over'); ctx.strokeStyle=(tool==='eraser'? 'rgba(0,0,0,1)':colorEl.value); ctx.lineWidth=sizeEl.value*dpr; ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); ctx.restore(); }}

  canvas.addEventListener('pointerdown', e=>{{ drawing=true; pushHistory(); last=pos(e); line(last,last); }});
  canvas.addEventListener('pointermove', e=>{{ if(drawing){{ const p=pos(e); line(last,p); last=p; }} }});
  ['pointerup','pointerleave','pointercancel'].forEach(ev=>canvas.addEventListener(ev,()=>{{ if(drawing){{ schedulePersist(); }} drawing=false; }}));

  document.getElementById('penBtn_{serial}').onclick=()=>tool='pen';
  document.getElementById('eraserBtn_{serial}').onclick=()=>tool='eraser';
  document.getElementById('clearBtn_{serial}').onclick=()=>{{ pushHistory(); ctx.fillStyle='#fff'; ctx.fillRect(0,0,canvas.width,canvas.height); schedulePersist(); }};
  document.getElementById('undoBtn_{serial}').onclick=doUndo;
  document.getElementById('redoBtn_{serial}').onclick=doRedo;

  document.getElementById('downloadBtn_{serial}').onclick = () => {{
    try {{
      const dataURL = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = dataURL;
      const now = new Date();
      const pad = n => String(n).padStart(2,'0');
      const fname = "pizarra_{serial}_" +
                    now.getFullYear() + "-" + pad(now.getMonth()+1) + "-" + pad(now.getDate()) + "_" +
                    pad(now.getHours()) + "-" + pad(now.getMinutes()) + "-" + pad(now.getSeconds()) + ".png";
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      a.remove();
    }} catch(e) {{
      console.error(e);
      alert('No se pudo descargar la imagen.');
    }}
  }};

  window.addEventListener('keydown', (e)=>{{ const z=(e.key==='z'||e.key==='Z'); const cm=e.ctrlKey||e.metaKey; if(!cm||!z) return; e.preventDefault(); if(e.shiftKey) doRedo(); else doUndo(); }});

  let persistTimer=null;
  function schedulePersist(){{ clearTimeout(persistTimer); persistTimer=setTimeout(pushSnapshot, 500); }}
  async function pushSnapshot(){{
    try {{
      const dataURL = canvas.toDataURL('image/png');
      try {{ const snapEl = document.getElementById("{IMG_ID}"); if (snapEl && dataURL) snapEl.src = dataURL; }} catch(_){{}}
      try {{ localStorage.setItem(STORAGE_KEY, dataURL); }} catch(_){{}}
      if (window.google?.colab?.kernel?.invokeFunction) {{
        await google.colab.kernel.invokeFunction(CALLBACK_NAME, [dataURL], {{}} );
      }}
    }} catch(e) {{ console.error(e); }}
  }}

  function loadPersisted(){{
    if (INITIAL_DATA_URL) {{ drawFromDataURL(INITIAL_DATA_URL); pushHistory(INITIAL_DATA_URL); return; }}
    let snap = document.getElementById("{IMG_ID}");
    if (snap && snap.src && snap.src.startsWith('data:image/')) {{ drawFromDataURL(snap.src); pushHistory(snap.src); return; }}
    try {{ const ls = localStorage.getItem(STORAGE_KEY); if (ls && ls.startsWith('data:image/')) {{ drawFromDataURL(ls); pushHistory(ls); }} }} catch(_){{}}
  }}
  setTimeout(loadPersisted, 30);

  // -------------------------------
  // Attach a handler to ALL buttons in the toolbar that invokes the kernel callback
  // -------------------------------
  function invokePythonButtonPressed() {{
    try {{
      if (window.google?.colab?.kernel?.invokeFunction) {{
        google.colab.kernel.invokeFunction(BUTTON_CB_NAME, [], {{}} );
        return;
      }}
    }} catch(e) {{
      console.warn('colab invoke failed', e);
    }}
    try {{
      if (window.Jupyter && window.Jupyter.notebook && window.Jupyter.notebook.kernel) {{
        window.Jupyter.notebook.kernel.execute("print('button pressed')");
        return;
      }}
    }} catch(e) {{
      console.warn('jupyter fallback failed', e);
    }}
    console.log("button pressed (no kernel available)");
  }}

  try {{
    const toolbar = document.querySelector('.toolbar');
    if (toolbar) {{
      const btns = toolbar.querySelectorAll('button');
      btns.forEach(b => {{
        b.addEventListener('click', () => {{
          invokePythonButtonPressed();
        }});
      }});
    }}
  }} catch(e) {{ console.warn('attach toolbar listeners failed', e); }}

}})();
</script>
"""

    html = f"""
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>Pizarra {serial}</title>
<style>
  :root{{ --muted:#e2e8f0; }}
  *{{ box-sizing:border-box; }}
  body{{ margin:0; font-family:ui-sans-serif,system-ui; background:#f8fafc; }}
  .toolbar{{ display:flex; gap:10px; flex-wrap:wrap; margin:12px; align-items:center; }}
  .toolbar button{{ padding:8px 12px; border:1px solid var(--muted); border-radius:8px; cursor:pointer; background:#fff; }}
  .toolbar input[type="color"], .toolbar input[type="range"]{{ height:36px; }}
  canvas{{ border:1px solid var(--muted); border-radius:12px; width:100%; height:460px; touch-action:none; cursor:crosshair; background:#fff; }}
  .serial{{ margin:8px 12px; font:12px/1.2 ui-sans-serif,system-ui; color:#64748b; }}
</style>
</head>
<body>
  <div class="serial">Board: <strong>{serial}</strong></div>

  <div class="toolbar">
    <button id="penBtn_{serial}">✏️ Lápiz</button>
    <button id="eraserBtn_{serial}">🧹 Borrador</button>
    <label>Color <input id="color_{serial}" type="color" value="#0f172a"></label>
    <label>Grosor <input id="size_{serial}" type="range" min="1" max="50" value="8"></label>
    <button id="undoBtn_{serial}">↩️ Undo</button>
    <button id="redoBtn_{serial}">↪️ Redo</button>
    <button id="clearBtn_{serial}">🗑️ Limpiar</button>
    <button id="downloadBtn_{serial}">⬇️ Descargar PNG</button>
  </div>

  <!-- (INTERNO oculto) para rehidratar el canvas y seguir editando -->
  <div id="{CONTAINER_ID}" style="display:none">
    <img id="{IMG_ID}" src="{initial_data_url or ''}" />
  </div>

  <canvas id="board_{serial}"></canvas>
  {js_code}
</body>
</html>
"""
    # create/update the hidden snapshot block in the notebook
    snapshot_html = f"""
    <div id="{CONTAINER_ID}" aria-hidden="true"
         style="position:fixed; left:-9999px; top:-9999px; width:1px; height:1px; opacity:0; overflow:hidden; padding:0; margin:0; border:0; user-select:none; pointer-events:none;">
      <div style="font:0/0; height:0; overflow:hidden">Último dibujo (persistente)</div>
      <img id="{IMG_ID}" src="{initial_data_url or ''}" alt="persisted snapshot" style="width:1px; height:1px; border:0; display:block" />
    </div>
    """
    if serial not in _SNAPSHOT_HANDLES:
        _SNAPSHOT_HANDLES[serial] = display(HTML(snapshot_html), display_id=True)
    else:
        _SNAPSHOT_HANDLES[serial].update(HTML(snapshot_html))

    # show the board
    display(HTML(html))
