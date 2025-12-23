# URDF_Render_Script.py
# Puente Colab <-> JS para descripciones de piezas del URDF. 
#
# Uso típico en Colab: 
#   from URDF_Render_Script import URDF_Render
#   URDF_Render("URDFModel")                      # solo viewer
#   URDF_Render("URDFModel", IA_Widgets=True)     # viewer + IA opt-in
#
# Este script:
#   - Busca /urdf y /meshes dentro de folder_path.
#   - Construye un meshDB embebido (base64) para el viewer JS.
#   - Renderiza un viewer HTML fullscreen para Colab.
#   - (Opcional) registra el callback "describe_component_images"
#     para que el JS pueda pedir descripciones vía API externa.
#
# Importante:
#   - IA_Widgets=False  -> no se manda nada a la API.
#   - IA_Widgets=True   -> JS llama a describe_component_images(entries).
#   - Aquí solo definimos el payload; el modelo (GPT-5, etc.) se configura
#     en tu servicio de Google Cloud.

import os
import re
import json
import base64
import shutil
import zipfile
import requests
from IPython.display import HTML

API_DEFAULT_BASE = "https://gpt-proxy-github-619255898589.us-central1.run.app"
API_INFER_PATH = "/infer"

_COLAB_CALLBACK_REGISTERED = False


def Download_URDF(Drive_Link, Output_Name="Model"):
  """
  Descarga un ZIP de Google Drive y lo deja en /content/Output_Name
  con subcarpetas /urdf y /meshes.
  """
  root_dir = "/content"
  file_id = Drive_Link.split("/d/")[1].split("/")[0]
  url = f"https://drive.google.com/uc?id={file_id}"
  zip_path = os.path.join(root_dir, Output_Name + ".zip")
  tmp_extract = os.path.join(root_dir, f"__tmp_extract_{Output_Name}")
  final_dir = os.path.join(root_dir, Output_Name)

  if os.path.exists(tmp_extract):
      shutil.rmtree(tmp_extract)
  os.makedirs(tmp_extract, exist_ok=True)
  if os.path.exists(final_dir):
      shutil.rmtree(final_dir)

  import gdown
  gdown.download(url, zip_path, quiet=True)

  with zipfile.ZipFile(zip_path, "r") as zf:
      zf.extractall(tmp_extract)

  def junk(name: str) -> bool:
      return name.startswith(".") or name == "__MACOSX"

  visibles = [n for n in os.listdir(tmp_extract) if not junk(n)]
  if len(visibles) == 1 and os.path.isdir(os.path.join(tmp_extract, visibles[0])):
      shutil.move(os.path.join(tmp_extract, visibles[0]), final_dir)
  else:
      os.makedirs(final_dir, exist_ok=True)
      for n in visibles:
          shutil.move(os.path.join(tmp_extract, n), os.path.join(final_dir, n))

  shutil.rmtree(tmp_extract, ignore_errors=True)
  return final_dir


def _register_colab_callback(api_base: str = API_DEFAULT_BASE, timeout: int = 120):
  """
  Registra el callback 'describe_component_images' si estamos en Colab.
  Ahora soporta:
    - Una entrada opcional __robot_iso__ con la imagen isométrica del robot completo.
    - Entradas de componentes con:
        { "key", "name", "index", "image_b64" }
    - Construye una secuencia ordenada de nombres y la envía como contexto
      en cada request a la API externa.
  """
  global _COLAB_CALLBACK_REGISTERED
  if _COLAB_CALLBACK_REGISTERED:
      return

  try:
      from google.colab import output  # type: ignore

      api_base = api_base.rstrip("/")
      infer_url = api_base + API_INFER_PATH

      def _describe_component_images(entries):
          """
          entries: [
            { "key": "__robot_iso__", "image_b64": "...", ... }?,
            { "key": assetKey, "name": baseName, "index": i, "image_b64": "..." },
            ...
          ]
          Devuelve: { assetKey: descripcion }
          """
          print(f"[Colab] describe_component_images: payload recibido")

          if not isinstance(entries, (list, tuple)):
              print("[Colab] Payload inválido (no lista).")
              return {}

          # --- Detectar ISO robot + normalizar componentes ---
          iso_b64 = None
          components = []

          for raw in entries:
              if not isinstance(raw, dict):
                  continue

              key = (raw.get("key") or "").strip()
              img_b64 = (raw.get("image_b64") or "").strip()
              name = (raw.get("name") or "").strip()
              idx = raw.get("index", None)

              # ISO del robot completo
              if key in (
                  "__robot_iso__",
                  "robot_iso",
                  "__iso__",
                  "robot",
                  "full_robot",
              ):
                  if img_b64 and not iso_b64:
                      iso_b64 = img_b64
                      print("[Colab] Detectada imagen ISO del robot completo.")
                  continue

              if not img_b64:
                  continue

              if not key:
                  key = name or f"comp_{len(components)}"
              if not name:
                  name = key

              if not isinstance(idx, int) or idx < 0:
                  idx = len(components)

              components.append(
                  {
                      "key": key,
                      "name": name,
                      "index": idx,
                      "image_b64": img_b64,
                  }
              )

          if not components:
              print("[Colab] Sin componentes válidos en entries.")
              return {}

          # Ordenar por índice para fijar secuencia lógica
          components.sort(key=lambda c: c.get("index", 0))

          # Secuencia de nombres para contexto global
          sequence_names = [c["name"] for c in components]
          sequence_str = ", ".join(sequence_names)

          print(
              f"[Colab] Componentes para IA: {len(components)} "
              f"(secuencia nombres incluida)."
          )
          if iso_b64:
              print("[Colab] Se usará ISO global como contexto en cada request.")

          results = {}

          for comp in components:
              key = comp["key"]
              name = comp["name"]
              idx = comp["index"]
              img_b64 = comp["image_b64"]

              # Construir lista de imágenes: primero ISO (si existe), luego componente
              images = []
              if iso_b64:
                  images.append(
                      {"image_b64": iso_b64, "mime": "image/png"}
                  )
              images.append({"image_b64": img_b64, "mime": "image/png"})

              # Prompt con contexto fuerte
              prompt = (
                  "Eres un modelo experto en robótica y diseño mecánico.\n"
                  "Analiza exclusivamente el componente actual del robot industrial utilizando "
                  "la imagen isométrica del robot completo como contexto global, la imagen específica del componente "
                  "y la secuencia ordenada de nombres de todos los componentes renderizados.\n"
                  f"Secuencia de nombres: {sequence_str}\n"
                  f"Componente actual: archivo '{name}' (índice {idx}).\n"
                  "Explica qué es y cuál es su función con la máxima precisión técnica posible, "
                  "manteniendo un estilo formal, directo y robótico. "
                  "No uses expresiones como 'En esta imagen se muestra', 'La pieza es', 'El componente...'"
                  "'Se observa', 'Podemos ver' o similares. "
                  "No repitas la consigna ni agregues comentarios sobre el análisis. "
                  "responde con un máximo de 2 frases."
              )

              payload = {
                  "text": prompt,
                  "images": images,
              }

              try:
                  r = requests.post(infer_url, json=payload, timeout=timeout)
              except Exception as e:
                  print(f"[Colab] Error conexión API para {key}: {e}")
                  results[key] = ""
                  continue

              if r.status_code != 200:
                  print(
                      f"[Colab] API {r.status_code} para {key}: {r.text[:200]}"
                  )
                  results[key] = ""
                  continue

              txt = (r.text or "").strip()

              # Si viene como JSON con campo 'text' o similar, intentar parsear
              try:
                  if txt.startswith("{") and txt.endswith("}"):
                      j = json.loads(txt)
                      if isinstance(j, dict):
                          txt = (
                              j.get("text")
                              or j.get("message")
                              or j.get("content")
                              or txt
                          )
              except Exception:
                  pass

              # Si viene entre comillas, parsear como string JSON
              try:
                  if txt.startswith('"') and txt.endswith('"'):
                      txt = json.loads(txt)
              except Exception:
                  pass

              results[key] = txt or ""

          print(
              f"[Colab] describe_component_images: descripciones devueltas "
              f"para {len(results)} componentes."
          )

          # Guardado automático del notebook (best-effort)
          try:
              from google.colab import _message  # type: ignore

              _message.blocking_request("notebook.save", {})
              print("[Colab] 💾 Notebook guardado tras recibir descripciones IA.")
          except Exception as e:
              print(
                  f"[Colab] Aviso: no se pudo guardar auto el notebook: {e}"
              )

          return results

      output.register_callback(
          "describe_component_images", _describe_component_images
      )
      _COLAB_CALLBACK_REGISTERED = True
      print(
          "[Colab] ✅ Callback 'describe_component_images' registrado "
          "(IA_Widgets=True, listo para usar tu API con GPT-5 + contexto ISO + secuencia)."
      )

  except Exception as e:
      print(
          f"[Colab] (Opcional) No se pudo registrar callback describe_component_images: {e}"
      )


def URDF_Visualization(
  folder_path: str = "Model",
  select_mode: str = "link",
  background: int | None = 0xFFFFFF,
  repo: str = "Arthemioxz/AutoMindCloudExperimental",
  branch: str = "main",
  compFile: str = "AutoMindCloud/viewer/urdf_viewer_main.js",
  api_base: str = API_DEFAULT_BASE,
  IA_Widgets: bool = False,
):
  """
  Renderiza el URDF Viewer para Colab.
  """
  if IA_Widgets:
      _register_colab_callback(api_base=api_base)

  # --- Buscar directorios urdf / meshes ---

  def find_dirs(root: str):
      # Layouts soportados:
      #  1) NUEVO (preferido):
      #       root/
      #         meshes/
      #         *.urdf
      #  2) ANTIGUO:
      #       root/
      #         urdf/*.urdf
      #         meshes/
      #
      # Devuelve: (urdf_dir, meshes_dir) donde urdf_dir es la carpeta que contiene los .urdf

      def has_urdf_files(p: str) -> bool:
          try:
              return any(name.lower().endswith(".urdf") for name in os.listdir(p))
          except Exception:
              return False

      # Root directo
      m = os.path.join(root, "meshes")
      u = os.path.join(root, "urdf")
      if os.path.isdir(m):
          if has_urdf_files(root):
              return root, m
          if os.path.isdir(u) and has_urdf_files(u):
              return u, m

      # Buscar un nivel abajo
      if os.path.isdir(root):
          try:
              for name in os.listdir(root):
                  cand = os.path.join(root, name)
                  if not os.path.isdir(cand):
                      continue

                  mm = os.path.join(cand, "meshes")
                  uu = os.path.join(cand, "urdf")

                  if os.path.isdir(mm):
                      if has_urdf_files(cand):
                          return cand, mm
                      if os.path.isdir(uu) and has_urdf_files(uu):
                          return uu, mm
          except Exception:
              pass

      return None, None

  urdf_dir, meshes_dir = find_dirs(folder_path)
  if not urdf_dir or not meshes_dir:
      return HTML(
          f"<b style='color:red'>No se encontró .urdf (en root o /urdf) y /meshes dentro de {folder_path}</b>"
      )

  # --- URDF principal ---

  urdf_files = [
      os.path.join(urdf_dir, f)
      for f in os.listdir(urdf_dir)
      if f.lower().endswith(".urdf")
  ]

  urdf_files.sort(
      key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0,
      reverse=True,
  )

  urdf_raw = ""
  mesh_refs: list[str] = []

  for upath in urdf_files:
      try:
          with open(upath, "r", encoding="utf-8", errors="ignore") as f:
              txt = f.read().lstrip("\ufeff")
          refs = re.findall(
              r'filename="([^"]+\.(?:stl|dae|STL|DAE))"', txt, re.IGNORECASE
          )
          if refs:
              urdf_raw = txt
              mesh_refs = list(dict.fromkeys(refs))
              break
      except Exception:
          pass

  if not urdf_raw and urdf_files:
      with open(urdf_files[0], "r", encoding="utf-8", errors="ignore") as f:
          urdf_raw = f.read().lstrip("\ufeff")

  # --- Construir meshDB embedido ---

  disk_files = []
  for root, _, files in os.walk(meshes_dir):
      for name in files:
          if name.lower().endswith((".stl", ".dae", ".png", ".jpg", ".jpeg")):
              disk_files.append(os.path.join(root, name))

  meshes_root_abs = os.path.abspath(meshes_dir)
  by_rel, by_base = {}, {}
  for path in disk_files:
      rel = (
          os.path.relpath(os.path.abspath(path), meshes_root_abs)
          .replace("\\", "/")
          .lower()
      )
      by_rel[rel] = path
      by_base[os.path.basename(path).lower()] = path

  _cache: dict[str, str] = {}
  mesh_db: dict[str, str] = {}

  def b64(path: str) -> str:
      if path not in _cache:
          with open(path, "rb") as f:
              _cache[path] = base64.b64encode(f.read()).decode("ascii")
      return _cache[path]

  def add_entry(key: str, path: str):
      k = key.replace("\\", "/")
      if k not in mesh_db:
          mesh_db[k] = b64(path)

  for ref in mesh_refs:
      raw = ref.replace("\\", "/")
      lower = raw.lower()
      base = os.path.basename(lower)
      rel = lower.lstrip("./")
      cand = (
          by_rel.get(rel)
          or by_rel.get(rel.replace("package://", ""))
          or by_base.get(base)
      )
      if cand:
          add_entry(raw, cand)
          add_entry(lower, cand)
          add_entry(base, cand)

  for base_name, path in by_base.items():
      if base_name not in mesh_db:
          add_entry(base_name, path)

  def esc_js(s: str) -> str:
      return (
          s.replace("\\", "\\\\")
          .replace("`", "\\`")
          .replace("$", "\\$")
          .replace("</script>", "<\\/script>")
      )

  urdf_js = esc_js(urdf_raw or "")
  mesh_js = json.dumps(mesh_db)
  bg_js = "null" if background is None else str(int(background))
  sel_js = json.dumps(select_mode)
  ia_js = "true" if IA_Widgets else "false"

  html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport"
        content="width=device-width, initial-scale=1, maximum-scale=1,
                 user-scalable=no, viewport-fit=cover"/>
  <title>URDF Viewer</title>
  <style>
    :root {{
      --vh: 1vh;
    }}
    html, body {{
      margin:0;
      padding:0;
      width:100%;
      height:100dvh;
      overflow:hidden;
      background:#{int(background or 0xFFFFFF):06x};
    }}
    @supports not (height: 100dvh) {{
      html, body {{ height: calc(var(--vh) * 100); }}
    }}
    body {{
      padding-top: env(safe-area-inset-top);
      padding-right: env(safe-area-inset-right);
      padding-bottom: env(safe-area-inset-bottom);
      padding-left: env(safe-area-inset-left);
    }}
    #app {{
      position:fixed;
      inset:0;
      width:100vw;
      height:100dvh;
      touch-action:none;
    }}
    @supports not (height: 100dvh) {{
      #app {{ height: calc(var(--vh) * 100); }}
    }}
    .badge {{
      position:fixed;
      right:14px;
      bottom:10px;
      z-index:10;
      user-select:none;
      pointer-events:none;
    }}
    .badge img {{
      max-height:40px;
      display:block;
    }}
  </style>
</head>
<body>
  <div id="app"></div>
  <div style="padding-left:20px; overflow:visible; position:fixed; right:0; bottom:0; z-index:999999;">
    <div class="badge" style="display:inline-block; transform: scale(2.5) translateX(-15px); transform-origin: bottom right; margin:0; overflow:visible; pointer-events:none;">
      <img src="https://raw.githubusercontent.com/Arthemioxz/AutoMindCloudExperimental/main/AutoMindCloud/AutoMindCloud2.png" alt="AutoMind" style="display:block; height:40px; width:auto;"/>
    </div>
  </div>




  <script defer src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/STLLoader.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/ColladaLoader.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/urdf-loader@0.12.6/umd/URDFLoader.js"></script>

  <script type="module">
    function applyVHVar() {{
      const viewport = window.visualViewport?.height || window.innerHeight || 600;
      const vh = viewport * 0.01;
      document.documentElement.style.setProperty('--vh', `${{vh}}px`);
    }}
    applyVHVar();

    function computeDesiredHeight() {{
      const viewportH =
        window.visualViewport?.height ||
        window.innerHeight ||
        document.documentElement.clientHeight ||
        0;

      const docScrollH = Math.max(
        document.documentElement?.scrollHeight || 0,
        document.body?.scrollHeight || 0
      );

      return Math.max(viewportH, docScrollH, 600);
    }}

    function setColabFrameHeight() {{
      const h = Math.ceil(computeDesiredHeight());
      try {{
        if (window.google?.colab?.output?.setIframeHeight) {{
          window.google.colab.output.setIframeHeight(h, true);
        }}
      }} catch (_e) {{}}
    }}

    const ro = new ResizeObserver(() => {{
      applyVHVar();
      setColabFrameHeight();
    }});
    ro.observe(document.body);

    window.addEventListener('resize', () => {{
      applyVHVar();
      setColabFrameHeight();
    }});
    if (window.visualViewport) {{
      window.visualViewport.addEventListener('resize', () => {{
        applyVHVar();
        setColabFrameHeight();
      }});
    }}

    setTimeout(setColabFrameHeight, 60);

    const repo     = {json.dumps(repo)};
    const branch   = {json.dumps(branch)};
    const compFile = {json.dumps(compFile)};

    async function latestSha() {{
      try {{
        const url = 'https://api.github.com/repos/' + repo + '/commits/' + branch + '?_=' + Date.now();
        const r = await fetch(url, {{
          headers: {{ 'Accept': 'application/vnd.github+json' }},
          cache: 'no-store'
        }});
        if (!r.ok) throw 0;
        const j = await r.json();
        return (j.sha || '').slice(0, 7) || branch;
      }} catch (_e) {{
        return branch;
      }}
    }}

    const SELECT_MODE = {sel_js};
    const BACKGROUND  = {bg_js};
    const IA_WIDGETS  = {ia_js};

    const opts = {{
      container: document.getElementById('app'),
      urdfContent: `{urdf_js}`,
      meshDB: {mesh_js},
      selectMode: SELECT_MODE,
      background: BACKGROUND,
      pixelRatio: Math.min(window.devicePixelRatio || 1, 2),
      autoResize: true,
      IA_Widgets: IA_WIDGETS
    }};

    let mod = null;
    try {{
      const sha = await latestSha();
      const base = 'https://cdn.jsdelivr.net/gh/' + repo + '@' + sha + '/';
      mod = await import(base + compFile + '?v=' + Date.now());
      console.debug('[URDF] Módulo viewer desde', sha);
    }} catch (_e) {{
      console.debug('[URDF] Fallback branch', branch);
      mod = await import(
        'https://cdn.jsdelivr.net/gh/' + repo + '@' + branch + '/' + compFile + '?v=' + Date.now()
      );
    }}

    if (!mod || typeof mod.render !== 'function') {{
      console.error('[URDF] No se pudo cargar urdf_viewer_main.js o falta render()');
    }} else {{
      const app = mod.render(opts);

      function onResize() {{
        try {{
          if (!app || typeof app.resize !== 'function') return;
          const w =
            window.innerWidth ||
            document.documentElement.clientWidth ||
            document.body.clientWidth ||
            800;
          const h = computeDesiredHeight();
          app.resize(w, h, Math.min(window.devicePixelRatio || 1, 2));
        }} catch (_e) {{}}
      }}

      window.addEventListener('resize', onResize);
      if (window.visualViewport) {{
        window.visualViewport.addEventListener('resize', onResize);
      }}

      setTimeout(() => {{
        onResize();
        setColabFrameHeight();
      }}, 0);

      setTimeout(() => {{
        onResize();
        setColabFrameHeight();
      }}, 500);
    }}
  </script>
</body>
</html>
"""
  return HTML(html)
