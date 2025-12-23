import base64
from IPython.display import HTML

import os
import shutil
import zipfile
import gdown
import contextlib
import io

def Download_DXF(Drive_link: str, show_output: bool = False):
    """
    Download a ZIP from Google Drive and extract its CONTENTS
    directly into /content (no extra folder).

    - Hides gdown/tqdm output by default
    - Handles single-root-folder ZIPs or flat ZIPs
    - Removes __MACOSX and hidden files
    - Safe re-runs
    """

    ROOT = "/content"

    # --------------------------------------------------
    # Extract file ID
    # --------------------------------------------------
    if "/d/" not in Drive_link:
        raise ValueError("Invalid Google Drive link (expected .../d/<FILE_ID>/...)")

    file_id = Drive_link.split("/d/")[1].split("/")[0]
    url = f"https://drive.google.com/uc?id={file_id}"

    zip_path = os.path.join(ROOT, "__download.zip")
    tmp_dir  = os.path.join(ROOT, "__tmp_extract")

    # --------------------------------------------------
    # Cleanup previous runs
    # --------------------------------------------------
    for p in (zip_path, tmp_dir):
        if os.path.exists(p):
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)

    os.makedirs(tmp_dir, exist_ok=True)

    # --------------------------------------------------
    # Download ZIP (silenced)
    # --------------------------------------------------
    if show_output:
        gdown.download(url, zip_path, quiet=True, fuzzy=True)
    else:
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            gdown.download(url, zip_path, quiet=True, fuzzy=True)

    # --------------------------------------------------
    # Extract ZIP
    # --------------------------------------------------
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp_dir)

    # --------------------------------------------------
    # Filter junk
    # --------------------------------------------------
    def is_junk(name: str) -> bool:
        return name.startswith(".") or name == "__MACOSX"

    items = [n for n in os.listdir(tmp_dir) if not is_junk(n)]

    # --------------------------------------------------
    # Unwrap single root folder if needed
    # --------------------------------------------------
    if len(items) == 1 and os.path.isdir(os.path.join(tmp_dir, items[0])):
        src_root = os.path.join(tmp_dir, items[0])
    else:
        src_root = tmp_dir

    # --------------------------------------------------
    # Move everything into /content
    # --------------------------------------------------
    for name in os.listdir(src_root):
        if is_junk(name):
            continue

        src = os.path.join(src_root, name)
        dst = os.path.join(ROOT, name)

        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)

        shutil.move(src, dst)

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------
    shutil.rmtree(tmp_dir, ignore_errors=True)
    if os.path.exists(zip_path):
        os.remove(zip_path)

    return "/content"


def DXF_Visualization(file_path):
    # Leer el archivo DXF y convertirlo a base64
    with open(file_path, "rb") as f:
        data = f.read()

    b64 = base64.b64encode(data).decode("utf-8")
    
    # Crear el HTML y reemplazar el marcador de base64
    html = """
    <div id='viewer' style='width:900px;height:650px;border:1px solid #ccc;position:relative;'>
      Cargando archivo...
    </div>

    <script>
    (async function(){
        const base64Data = "__B64__";

        function base64ToArrayBuffer(base64){
            const bin = atob(base64);
            const bytes = new Uint8Array(bin.length);
            for(let i=0;i<bin.length;i++) bytes[i] = bin.charCodeAt(i);
            return bytes.buffer;
        }

        let dxfText = new TextDecoder("utf-8").decode(base64ToArrayBuffer(base64Data));

        // ==========================================================
        // PARSER DXF FINAL (BLOCKS + INSERT + LWPOLYLINE + POLYLINE)
        // ==========================================================

        function parseDXF(text){
            const parts = text.split(/\\r\\n|\\r|\\n/);
            let i = 0;
            let section = null;
            let blocks = {};
            let currentBlock = null;
            let inBlock = false;
            let entities = [];

            function P(idx){
                return {code: parts[idx]?.trim(), value: parts[idx+1]?.trim()};
            }

            // ------------------ LINE ------------------
            function parseLINE(start){
                let x1,y1,x2,y2;
                for(let j=start; j < parts.length-1; j+=2){
                    let c = parts[j].trim();
                    let v = parts[j+1].trim();
                    if(c==="0") break;
                    if(c==="10") x1=parseFloat(v);
                    if(c==="20") y1=parseFloat(v);
                    if(c==="11") x2=parseFloat(v);
                    if(c==="21") y2=parseFloat(v);
                }
                return [{x1,y1,x2,y2}];
            }

            // ----------- ARC/CIRCLE SEGMENTS -----------
            function arcSeg(cx,cy,r,a1,a2,n=48){
                let arr=[];
                let da=(a2-a1)/n;
                for(let k=0;k<n;k++){
                    let t1=a1+k*da;
                    let t2=a1+(k+1)*da;
                    arr.push({
                        x1: cx+r*Math.cos(t1), y1: cy+r*Math.sin(t1),
                        x2: cx+r*Math.cos(t2), y2: cy+r*Math.sin(t2),
                    });
                }
                return arr;
            }

            // ----------- LWPOLYLINE -----------
            function parseLWPOLY(start){
                let pts = [];
                let closed = false;

                for(let j=start; j < parts.length-1; j+=2){
                    let c = parts[j].trim();
                    let v = parts[j+1].trim();

                    if(c==="0") break;

                    if(c==="10"){
                        let x = parseFloat(v);
                        let y = parseFloat(parts[j+3]);
                        pts.push([x,y]);
                    }
                    if(c==="70"){
                        closed = (parseInt(v)&1)!==0;
                    }
                }
                let segs=[];
                for(let k=0;k<pts.length-1;k++)
                    segs.push({x1:pts[k][0],y1:pts[k][1],x2:pts[k+1][0],y2:pts[k+1][1]});
                if(closed && pts.length>1)
                    segs.push({x1:pts.at(-1)[0],y1:pts.at(-1)[1],x2:pts[0][0],y2:pts[0][1]});
                return segs;
            }

            // ------------ POLYLINE ----------------
            function parsePOLYLINE(start){
                let pts=[];
                for(let j=start;j<parts.length-1;j+=2){
                    let q=P(j);
                    if(q.code==="0" && q.value==="VERTEX"){
                        let vx,vy;
                        for(let k=j+2;k<parts.length-1;k+=2){
                            let v=P(k);
                            if(v.code==="0") break;
                            if(v.code==="10") vx=parseFloat(v.value);
                            if(v.code==="20") vy=parseFloat(v.value);
                        }
                        if(vx!=null) pts.push([vx,vy]);
                    }
                    if(q.value==="SEQEND") break;
                }
                let segs=[];
                for(let k=0;k<pts.length-1;k++)
                    segs.push({x1:pts[k][0],y1:pts[k][1],x2:pts[k+1][0],y2:pts[k+1][1]});
                return segs;
            }

            // --------- TRANSFORM SEGMENT FOR INSERT ---------
            function applyTransform(seg, px, py, sx, sy, rot){
                function t(x,y){
                    let X = x * sx;
                    let Y = y * sy;

                    let xr = X*Math.cos(rot) - Y*Math.sin(rot);
                    let yr = X*Math.sin(rot) + Y*Math.cos(rot);

                    return [xr + px, yr + py];
                }

                let p1 = t(seg.x1, seg.y1);
                let p2 = t(seg.x2, seg.y2);
                return {x1:p1[0], y1:p1[1], x2:p2[0], y2:p2[1]};
            }

            // ======================================================
            // MAIN LOOP
            // ======================================================
            while(i < parts.length-1){
                let p = P(i);
                i += 2;

                // Detect section
                if(p.code==="0" && p.value==="SECTION"){
                    let sec = P(i);
                    if(sec.code==="2") section = sec.value;
                    continue;
                }

                if(p.code==="0" && p.value==="ENDSEC"){
                    section = null;
                    continue;
                }

                // -------------------------
                // BLOCKS
                // -------------------------
                if(section==="BLOCKS"){

                    if(p.value==="BLOCK"){
                        currentBlock = {name:null, items:[]};
                        inBlock = true;
                    }

                    if(inBlock && p.code==="2" && !currentBlock.name){
                        currentBlock.name = p.value;
                    }

                    if(inBlock && p.value==="LINE"){
                        currentBlock.items.push(...parseLINE(i));
                    }

                    if(inBlock && p.value==="LWPOLYLINE"){
                        currentBlock.items.push(...parseLWPOLY(i));
                    }

                    if(inBlock && p.value==="POLYLINE"){
                        currentBlock.items.push(...parsePOLYLINE(i));
                    }

                    if(inBlock && p.value==="ARC"){
                        let cx,cy,r,a1,a2;
                        for(let j=i;j<parts.length-1;j+=2){
                            let q=P(j);
                            if(q.code==="0")break;
                            if(q.code==="10") cx=parseFloat(q.value);
                            if(q.code==="20") cy=parseFloat(q.value);
                            if(q.code==="40") r=parseFloat(q.value);
                            if(q.code==="50") a1=parseFloat(q.value)*Math.PI/180;
                            if(q.code==="51") a2=parseFloat(q.value)*Math.PI/180;
                        }
                        currentBlock.items.push(...arcSeg(cx,cy,r,a1,a2));
                    }

                    if(inBlock && p.value==="CIRCLE"){
                        let cx,cy,r;
                        for(let j=i;j<parts.length-1;j+=2){
                            let q=P(j);
                            if(q.code==="0")break;
                            if(q.code==="10") cx=parseFloat(q.value);
                            if(q.code==="20") cy=parseFloat(q.value);
                            if(q.code==="40") r=parseFloat(q.value);
                        }
                        currentBlock.items.push(...arcSeg(cx,cy,r,0,Math.PI*2));
                    }

                    if(p.value==="ENDBLK"){
                        blocks[currentBlock.name] = currentBlock.items;
                        inBlock = false;
                    }

                    continue;
                }

                // -------------------------
                // ENTITIES
                // -------------------------
                if(section==="ENTITIES"){

                    if(p.value==="LINE")
                        entities.push(...parseLINE(i));

                    if(p.value==="LWPOLYLINE")
                        entities.push(...parseLWPOLY(i));

                    if(p.value==="POLYLINE")
                        entities.push(...parsePOLYLINE(i));

                    if(p.value==="ARC"){
                        let cx,cy,r,a1,a2;
                        for(let j=i;j<parts.length-1;j+=2){
                            let q=P(j);
                            if(q.code==="0")break;
                            if(q.code==="10") cx=parseFloat(q.value);
                            if(q.code==="20") cy=parseFloat(q.value);
                            if(q.code==="40") r=parseFloat(q.value);
                            if(q.code==="50") a1=parseFloat(q.value)*Math.PI/180;
                            if(q.code==="51") a2=parseFloat(q.value)*Math.PI/180;
                        }
                        entities.push(...arcSeg(cx,cy,r,a1,a2));
                    }

                    if(p.value==="CIRCLE"){
                        let cx,cy,r;
                        for(let j=i;j<parts.length-1;j+=2){
                            let q=P(j);
                            if(q.code==="0")break;
                            if(q.code==="10") cx=parseFloat(q.value);
                            if(q.code==="20") cy=parseFloat(q.value);
                            if(q.code==="40") r=parseFloat(q.value);
                        }
                        entities.push(...arcSeg(cx,cy,r,0,Math.PI*2));
                    }

                    if(p.value==="INSERT"){
                        let name=null, px=0, py=0, rot=0, sx=1, sy=1;

                        for(let j=i;j<parts.length-1;j+=2){
                            let q=P(j);
                            if(q.code==="0") break;

                            if(q.code==="2") name=q.value;
                            if(q.code==="10") px=parseFloat(q.value);
                            if(q.code==="20") py=parseFloat(q.value);
                            if(q.code==="50") rot=parseFloat(q.value)*Math.PI/180;
                            if(q.code==="41") sx=parseFloat(q.value);
                            if(q.code==="42") sy=parseFloat(q.value);
                        }

                        if(blocks[name]){
                            for(const seg of blocks[name]){
                                entities.push(applyTransform(seg,px,py,sx,sy,rot));
                            }
                        }
                    }
                }
            }

            return entities;
        }

        // ==========================================================
        // RENDER FINAL EN CANVAS
        // ==========================================================
        const segments = parseDXF(dxfText);

        const viewer = document.getElementById("viewer");
        viewer.innerHTML = "";

        const canvas = document.createElement("canvas");
        canvas.width = viewer.clientWidth;
        canvas.height = viewer.clientHeight;
        viewer.appendChild(canvas);

        const ctx = canvas.getContext("2d");
        ctx.fillStyle="#FFF";
        ctx.fillRect(0,0,canvas.width,canvas.height);

        let minX=1e9,minY=1e9,maxX=-1e9,maxY=-1e9;

        for(const s of segments){
            minX=Math.min(minX,s.x1,s.x2);
            minY=Math.min(minY,s.y1,s.y2);
            maxX=Math.max(maxX,s.x1,s.x2);
            maxY=Math.max(maxY,s.y1,s.y2);
        }

        let dx=maxX-minX, dy=maxY-minY;
        let scale=Math.min((canvas.width-40)/dx, (canvas.height-40)/dy);

        function worldToScreen(x,y){
            return [20+(x-minX)*scale, canvas.height-20-(y-minY)*scale];
        }

        ctx.beginPath();
        ctx.strokeStyle="#000";
        ctx.lineWidth=1;

        for(const s of segments){
            let p1=worldToScreen(s.x1,s.y1);
            let p2=worldToScreen(s.x2,s.y2);
            ctx.moveTo(p1[0],p1[1]);
            ctx.lineTo(p2[0],p2[1]);
        }

        ctx.stroke();

    })();
    </script>
    """

    html = html.replace("__B64__", b64)
    display(HTML(html))

# Ejemplo de uso:
