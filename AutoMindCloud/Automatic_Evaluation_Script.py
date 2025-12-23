import sympy

from re import I

import IPython

from AutoMindCloud.Latemix2 import *

global DatosList,Orden,Color

DatosList = []

Orden = 0

global documento

documento = []

Color = ""

def Inicializar(n,color):
  
  global DatosList,Orden,Color#Documento

  global documento

  documento = ""
  
  DatosList = []

  Orden = n

  Color = color

  return DatosList

def search(symbolo,DatosList):

  #display(DatosList)

  #global DatosList,Orden,Color#Documento
  #global DatosList
  
  for c_element in DatosList:
    if c_element[0] == symbolo:
      if isinstance(c_element[1],float):#Si tenemos un numero
          return "("+str(c_element[1])+")"
      elif isinstance(c_element[1],int):#Si tenemos un float
          return "("+str(c_element[1])+")"
      elif c_element[1] != None:#Si tenemos una expresión
          return "("+sympy.latex(c_element[1])+")"
      else:
        return sympy.latex(symbolo)#Si es None
  return sympy.latex(symbolo)


def Redondear(expr):#Redondeamos la expresión.
  if isinstance(expr, sympy.Expr) or isinstance(expr, sympy.Float):
    Aproximacion = expr.xreplace(sympy.core.rules.Transform(lambda x: x.round(Orden), lambda x: isinstance(x, sympy.Float)))
  elif isinstance(expr,float) or isinstance(expr,int):
    Aproximacion = round(expr,Orden)
  else:
    Aproximacion = expr
  return Aproximacion

def S(c_componente):#Guardar
  global DatosList,Orden,Color#Documento
  
  dentro = False#Supongamos que el elemento no esté dentro

  for elemento in DatosList:
    if elemento[0] == c_componente[0]:# si el componente esta adentro, entonces
      dentro = True

  if c_componente[1] == None:
    c_componente[1] = c_componente[0]
    
  if dentro == False:
    DatosList.append(c_componente)#Si el elemento no estaba adentro, simplemente lo agregamos.
    dentro = True

  #Renderizado Gris
  if c_componente[1] == None or dentro == False:
    D(c_componente)#Hacemos un print renderizado en color gris para indicar que el elemento ha sido definido/guardado
  else:
    D(c_componente)#Hacemos un print renderizado en color gris para indicar que el elemento ha sido definido/guardado


def D(elemento):#Por default se imprime en rojo, para indicar que es un derivado.
  #global DatosList,Orden,Color#Documento

  global documento
  
  print("")
  Tipo = None
  if isinstance(elemento,sympy.core.relational.Equality):#Si el elemento ingresado es una ecuación, entonces la identificamos
    Tipo = "Ecuacion"
  elif isinstance(elemento,list):#Si el elemento ingresado es un componente, entonces lo identificamos.
    Tipo = "Componente"
    c_componente = elemento
  else:
    Tipo = "Expresion"
  
  if Tipo == "Ecuacion":#Si hemos identificado el elemento ingresado como una ecuación, entonces la imprimimos en rojo

    a = sympy.latex(elemento.args[0])

    b = "="

    c = sympy.latex(elemento.args[1])

    texto = a + b + c
    #texto = texto.replace("text", Estilo)

    documento += "$\\textcolor{"+Color+"}{"+texto+"}$"
    IPython.display.display(IPython.display.Latex("$\\textcolor{"+Color+"}{"+texto+"}$"))
    #Documento.append(texto)

  if Tipo == "Componente":#Si hemos identificado el elemento ingresado como un componente, entonces lo imprimimos en rojo


    #if not isinstance(c_componente[0],str):#isinstance(c_componente[0],sy.core.symbol.Symbol) or isinstance(c_componente[0],sy.core.symbol.Symbol) :
    a = sympy.latex(c_componente[0])

    b = " = "

    if c_componente[1] == c_componente[0]:#== None:<---------------------------------------------------------------------------------------------------------------------------
      c = "None"
    else:
      c = sympy.latex(Redondear(c_componente[1]))
    
    texto = a + b + c
      #texto = texto.replace("text", Estilo)

    documento += "$\\textcolor{"+Color+"}{"+texto+"}$"
    
    IPython.display.display(IPython.display.Latex("$\\textcolor{"+Color+"}{"+texto+"}$"))
    #Documento.append(texto)

  if Tipo == "Expresion":

    exp = sympy.latex(elemento)

    texto = exp
    #texto = texto.replace("text", Estilo)

    documento += "$\\textcolor{"+Color+"}{"+texto+"}$"
    IPython.display.display(IPython.display.Latex("$\\textcolor{"+Color+"}{"+texto+"}$"))
  

def R(string):
  #global DatosList,Orden,Color#Documento

  global documento

  #documento += "$\\textcolor{"+Color+"}{"+string+"}$"
  documento += string
  IPython.display.display(IPython.display.Latex("$\\textcolor{"+Color+"}{"+string+"}$"))
  
def E(expr):
  
  print("")

  global DatosList,Orden,Color#Documento
  
  #display(DatosList)
  #display(Orden)
  #display(Color)

  #IPython.display.display(IPython.display.Latex("$\\textcolor{"+Color+"}{"+"400"+"}$"))
  global documento
  
  if isinstance(expr,sympy.core.relational.Equality):#Si tenemos una igualdad
    izquierda = expr.args[0]
    derecha = expr.args[1]
    #texto = RenderLatex(izquierda) + " = " + RenderLatex(derecha)
    texto = RenderLatex([izquierda,DatosList]) + " = " + RenderLatex([derecha,DatosList])

    

    documento += "$\\textcolor{"+Color+"}{"+texto+"}$"
    
    return IPython.display.display(IPython.display.Latex("$\\textcolor{"+Color+"}{"+texto+"}$"))
  elif isinstance(expr,list):#Si tenemos un componente
    texto = sympy.latex(expr[0]) + " = " + RenderLatex([expr[1],DatosList])

    documento += "$\\textcolor{"+Color+"}{"+texto+"}$"
    return IPython.display.display(IPython.display.Latex("$\\textcolor{"+Color+"}{"+texto+"}$"))
  elif isinstance(expr,sympy.core.mul.Mul):
    texto = RenderLatex([expr,DatosList])#latemix(expr)

    documento += "$\\textcolor{"+Color+"}{"+texto+"}$"
    
    return IPython.display.display(IPython.display.Latex("$\\textcolor{"+Color+"}{"+texto+"}$"))

def DocumentoStr():
  global documento

  return documento

import re
from IPython.display import display, Markdown



























import requests, base64, mimetypes, re, html, urllib.parse, json
from pathlib import Path
from IPython.display import display, HTML

# =========================================================
# 🔹 POLLI_TEXT: cliente robusto
# =========================================================
def polli_text(
    prompt: str,
    url: str = "https://gpt-proxy-github-619255898589.us-central1.run.app/infer",
    timeout: int = 60,
) -> str:
    # IMPORTANTE: tu backend /infer debe aceptar {"text": "..."}
    r = requests.post(url, json={"text": prompt}, timeout=timeout)
    r.raise_for_status()
    try:
        data = r.json()
    except Exception:
        return r.text.strip()

    if isinstance(data, str):
        return data.strip()

    if isinstance(data, dict):
        if "text" in data and isinstance(data["text"], str):
            return data["text"].strip()
        if "output" in data and isinstance(data["output"], str):
            return data["output"].strip()
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            ch = data["choices"][0]
            if isinstance(ch, dict):
                for k in ("text", "message", "content"):
                    if k in ch and isinstance(ch[k], str):
                        return ch[k].strip()
        return json.dumps(data, ensure_ascii=False)

    return str(data).strip()


# =====================================
# 🔹 Utilidades de limpieza y parsing
# =====================================
_num_pat = re.compile(r'^\s*(\d+)[\.\)]\s+(.*)')

_heading_patterns = [
    r'^\s*\(?\s*1\s*\)?\s*\.?\s*Resumen\s*:?\s*$',
    r'^\s*Resumen\s*:?\s*$',
    r'^\s*RESUMEN\s*:?\s*$',
    r'^\s*\(?\s*2\s*\)?\s*\.?\s*Pasos\s*:?\s*$',
    r'^\s*Pasos\s*:?\s*$',
    r'^\s*PASOS\s*:?\s*$',
]
_heading_regexes = [re.compile(p, re.IGNORECASE) for p in _heading_patterns]


def _looks_like_heading(line: str) -> bool:
    line = re.sub(r'[*_`~]+', '', line)
    line = re.sub(r'<[^>]+>', '', line)
    return any(rx.match(line.strip()) for rx in _heading_regexes)


# ========= FUNCIÓN CLAVE: evita texto pegado y corrige "\ (" =========
def _escape_keep_math(s: str) -> str:
    # Corrige intentos de \( ... \) escritos con espacio: "\ (" -> "\(" y "\ )" -> "\)"
    s = s.replace("\\ (", "\\(").replace("\\ )", "\\)")

    # Detecta TODOS los bloques "matemáticos"
    math_pattern = re.compile(
        r'(\$\$.*?\$\$|\$.*?\$|\\\[.*?\\\]|\\\(.*?\\\))',
        re.S
    )

    # símbolos / macros típicamente matemáticos (operadores, \lambda, \frac, etc.)
    math_ops_re = re.compile(r'(\\[a-zA-Z]+|[_^=+\-*/=])')

    def _maybe_unmath(seg: str) -> str:
        # Detecta tipo de delimitador y extrae el interior
        if seg.startswith("$$") and seg.endswith("$$"):
            # $$...$$ suele ser fórmula de verdad → lo respetamos
            return seg

        if seg.startswith("\\(") and seg.endswith("\\)"):
            inner = seg[2:-2]
        elif seg.startswith("\\[") and seg.endswith("\\]"):
            inner = seg[2:-2]
        elif seg.startswith("$") and seg.endswith("$"):
            inner = seg[1:-1]  # $...$
        else:
            return seg  # algo raro → lo dejamos como está

        inner_stripped = inner.strip()
        if not inner_stripped:
            return ""

        # Palabras aproximadas (separando por espacios)
        tokens = inner_stripped.replace("\n", " ").split()

        # ¿Tiene símbolos / macros claramente matemáticos?
        has_math_ops = bool(math_ops_re.search(inner_stripped))

        # Heurística 1:
        #   - muchas palabras (>= 6)
        #   - y NO hay símbolos matemáticos claros
        #   => probablemente es TEXTO que el modelo metió entre delimitadores
        if len(tokens) >= 6 and not has_math_ops:
            return html.escape(inner_stripped)

        # Heurística 2: bastantes palabras y casi todo letras/números
        letters_digits = re.sub(r'[^A-Za-z0-9]+', '', inner_stripped)
        if letters_digits:
            letters_count = sum(c.isalpha() for c in letters_digits)
            letters_ratio = letters_count / len(letters_digits)
        else:
            letters_ratio = 0.0

        if len(tokens) >= 4 and not has_math_ops and letters_ratio > 0.6:
            return html.escape(inner_stripped)

        # En los demás casos (fórmulas cortas de verdad), lo dejamos como math
        return seg

    parts = math_pattern.split(s)
    out = []
    for p in parts:
        if not p:
            continue
        if math_pattern.fullmatch(p):
            # Segmento marcado como "math" → aplicamos heurística
            out.append(_maybe_unmath(p))
        else:
            # Texto normal → solo escapamos HTML
            out.append(html.escape(p))

    return "".join(out)
# ================= FIN _escape_keep_math =========================


def _strip_boilerplate(s: str) -> str:
    s = s.lstrip()
    s = re.sub(
        r"^(claro|por supuesto|aquí tienes|a continuación).*?\n+",
        "",
        s,
        flags=re.IGNORECASE,
    )
    lines = [l.rstrip() for l in s.splitlines()]
    lines = [l for l in lines if not _looks_like_heading(l)]
    return "\n".join(lines).strip()


def _split_summary_and_steps(text: str):
    text = _strip_boilerplate(text)
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.splitlines() if l.strip()]

    # Quita encabezados tipo "1. Resumen" / "2. Pasos"
    lines = [
        re.sub(r"^\s*\(?\s*1\s*\)?\s*\.?\s*Resumen\s*:?\s*", "", l, flags=re.IGNORECASE)
        for l in lines
    ]
    lines = [
        re.sub(r"^\s*\(?\s*2\s*\)?\s*\.?\s*Pasos\s*:?\s*", "", l, flags=re.IGNORECASE)
        for l in lines
    ]

    first_idx = None
    for i, line in enumerate(lines):
        if _num_pat.match(line):
            first_idx = i
            break

    if first_idx is None:
        return " ".join(lines).strip(), []

    summary = " ".join(lines[:first_idx]).strip()
    steps = []
    current = None

    for line in lines[first_idx:]:
        m = _num_pat.match(line)
        if m:
            if current:
                steps.append(current.strip())
            current = m.group(2)
        else:
            if current:
                current += " " + line

    if current:
        steps.append(current.strip())

    steps = [re.sub(r"^\s*[-–•]\s*", "", s).strip() for s in steps]
    return summary, steps


# =====================================
# 🔹 Render con fuentes + MathJax
# =====================================
def _render_html(summary: str, steps: list, font_type: str, language: str):
    global Color  # Color definido por ti afuera

    lang = (language or "spanish").strip().lower()
    if lang.startswith("en"):
        title_resumen = "Summary"
        title_pasos = "Steps"
    else:
        title_resumen = "Resumen"
        title_pasos = "Pasos"

    css = f"""
<link href="https://fonts.googleapis.com/css2?family=Anton:wght@400;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
<link href="https://fonts.cdnfonts.com/css/latin-modern-roman" rel="stylesheet">
<style>
  .calc-wrap {{
    max-width:980px;
    margin:8px auto;
    padding:8px 4px;
    font-family:'{font_type}','Fira Sans',system-ui;
  }}

  .title {{
    font-family:'Anton',sans-serif;
    color:{Color};
    font-size:22px;
    font-weight:700;
    letter-spacing:1.5px;
    margin:8px 0 10px;
  }}

  .p {{
    font-size:18px;
    line-height:1.6;
    margin:8px 0;
  }}

  .summary {{
    color:{Color};
  }}

  .step {{
    margin:10px 0;
    color:{Color};
  }}

  .idx {{
    margin-right:8px;
    font-weight:700;
  }}
</style>
<script>
window.MathJax={{tex:{{inlineMath:[['$','$'],['\\\\(','\\\\)']],
displayMath:[['$$','$$'],['\\\\[','\\\\]']]}},
options:{{skipHtmlTags:['script','noscript','style','textarea','pre','code']}}}};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>
"""

    body = f"""
<div class="calc-wrap">
  <div class="title">{title_resumen}</div>
  <p class="p summary">{_escape_keep_math(summary)}</p>

  {"<div class='title'>" + title_pasos + "</div>" if steps else ""}
  {''.join(
      f'<p class="p step"><span class="idx">{i}.</span>{_escape_keep_math(s)}</p>'
      for i, s in enumerate(steps, 1)
  )}
</div>
"""
    return css + body


# =====================================
# 🔹 Función principal con idioma
# =====================================
def IA_CalculusSummary(
    numero: int,
    language: str = "spanish",
    font_type: str = "Latin Modern Roman",
):
    """
    IA_CalculusSummary(numero, language="spanish"/"english", font_type=...)
    Usa la variable global 'documento' como entrada.
    """
    global documento

    lang = (language or "spanish").strip().lower()

    if lang.startswith("en"):  # english
        base = (
            "Write in English, academic tone, formal and impersonal (third person). "
            "Start directly with the content. "
            "Structure the output in two parts: "
            "(1) one summary paragraph; "
            "(2) then a numbered list of steps 1., 2., 3., etc. "
            "IMPORTANT: All mathematical notation MUST be correctly delimited: "
            "use \\( ... \\) for inline formulas and \\[ ... \\] for display equations. "
            "Use LaTeX ONLY for short mathematical expressions, never for whole sentences. "
            "If the model tries to wrap an entire sentence with \\( ... \\) or $ ... $, rewrite it so that "
            "only the specific mathematical expressions are in LaTeX."
        )
    else:  # default: spanish
        base = (
            "Escribe en español, tono académico, formal e impersonal (tercera persona). "
            "Empieza directamente con el contenido. "
            "Estructura la salida en dos partes: "
            "(1) un párrafo de resumen; "
            "(2) luego una enumeración con pasos numerados 1., 2., 3., etc. "
            "IMPORTANTE: Toda notación matemática DEBE ir delimitada correctamente: "
            "usa \\( ... \\) para fórmulas en línea y \\[ ... \\] para ecuaciones en bloque. "
            "Usa LaTeX SOLO para expresiones matemáticas cortas, nunca para oraciones completas. "
            "Si el modelo intenta rodear una oración completa con \\( ... \\) o $ ... $, "
            "reformula la oración para que únicamente las expresiones matemáticas específicas "
            "aparezcan en LaTeX."
        )

    if numero == 1:
        detalle = (
            " Redacta un resumen conciso (5-7 líneas) y 7 pasos generales sin fórmulas."
        )
    elif numero == 2:
        detalle = (
            " Redacta un resumen preciso (7-9 líneas) y 15 pasos con detalles clave."
        )
    elif numero == 3:
        detalle = (
            " Redacta un resumen muy preciso (9-12 líneas) y 30 pasos con notación LaTeX."
        )
    else:
        detalle = " Redacta un resumen breve y pasos razonables."

    prompt = (
        f"{base}{detalle}\n\nContenido a resumir / Content to summarize:\n\n{documento}"
    )

    raw = polli_text(prompt)
    summary, steps = _split_summary_and_steps(raw)
    html_out = _render_html(summary, steps, font_type, language)
    display(HTML(html_out))

