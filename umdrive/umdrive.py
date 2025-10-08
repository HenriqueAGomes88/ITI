# umdrive.py
from flask import Flask, request, jsonify, send_from_directory, abort, render_template_string # type: ignore
from werkzeug.utils import secure_filename # type: ignore
from werkzeug.exceptions import RequestEntityTooLarge # type: ignore
from pathlib import Path
import os, json, time

app = Flask(__name__)

# Config
STORAGE_DIR = Path('storage')
METADATA_FILE = STORAGE_DIR / 'metadata.json'
STORAGE_DIR.mkdir(exist_ok=True)
if not METADATA_FILE.exists():
    METADATA_FILE.write_text(json.dumps({}, indent=2), encoding='utf-8')

# Limite de upload (ex.: 100 MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# Helpers
def load_metadata():
    try:
        return json.loads(METADATA_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}

def save_metadata(md):
    METADATA_FILE.write_text(json.dumps(md, indent=2), encoding='utf-8')

def is_within_directory(child: Path, parent: Path) -> bool:
    # Evita directory traversal (works para a maioria dos casos)
    parent_real = str(parent.resolve())
    child_real = str(child.resolve())
    return child_real == parent_real or child_real.startswith(parent_real + os.sep)

def file_info(path: Path):
    st = path.stat()
    return {
        'name': path.name,
        'size': st.st_size,
        'mtime': int(st.st_mtime),
        'download_url': f'/api/files/{path.name}/download',
        'metadata': load_metadata().get(path.name, {})
    }

# Basic index (mantém a tua mensagem simples)
@app.route("/")
def index():
    return "<h1>Olá — o UM Drive está a funcionar!</h1><p>Servidor ativo.</p>"

# API: listar ficheiros
@app.route("/api/files", methods=['GET'])
def list_files():
    files = [file_info(p) for p in STORAGE_DIR.iterdir() if p.is_file() and p.name != METADATA_FILE.name]
    # ordena por nome
    files_sorted = sorted(files, key=lambda x: x['name'].lower())
    return jsonify(files_sorted)

# API: upload (multipart/form-data, campo 'file')
@app.route("/api/files", methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado (campo "file" ausente)'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': 'Nome do ficheiro vazio'}), 400
    filename = secure_filename(f.filename)
    target = STORAGE_DIR / filename
    # grava o ficheiro (sobrescreve se existir)
    f.save(str(target))
    # garante metadado padrão
    md = load_metadata()
    md.setdefault(filename, {})
    save_metadata(md)
    return jsonify({'message': 'uploaded', 'file': filename}), 201

# API: download
@app.route("/api/files/<path:filename>/download", methods=['GET'])
def download_file(filename):
    safe_name = secure_filename(filename)
    file_path = STORAGE_DIR / safe_name
    if not file_path.exists():
        return jsonify({'error': 'Ficheiro não encontrado'}), 404
    # verificação extra de segurança
    if not is_within_directory(file_path, STORAGE_DIR):
        return jsonify({'error': 'Caminho inválido'}), 400
    return send_from_directory(str(STORAGE_DIR), safe_name, as_attachment=True)

# API: apagar ficheiro
@app.route("/api/files/<path:filename>", methods=['DELETE'])
def delete_file(filename):
    safe_name = secure_filename(filename)
    file_path = STORAGE_DIR / safe_name
    if not file_path.exists():
        return jsonify({'error': 'Ficheiro não encontrado'}), 404
    if not is_within_directory(file_path, STORAGE_DIR):
        return jsonify({'error': 'Caminho inválido'}), 400
    file_path.unlink()
    md = load_metadata()
    md.pop(safe_name, None)
    save_metadata(md)
    return jsonify({'message': 'deleted', 'file': safe_name})

# API: ler / escrever metadados (JSON)
@app.route("/api/files/<path:filename>/metadata", methods=['GET','POST'])
def metadata(filename):
    safe_name = secure_filename(filename)
    file_path = STORAGE_DIR / safe_name
    md = load_metadata()
    if request.method == 'GET':
        return jsonify(md.get(safe_name, {}))
    else:
        # POST -> receber JSON e guardar como metadados
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({'error': 'Esperado body JSON object'}), 400
        md[safe_name] = data
        save_metadata(md)
        return jsonify({'message': 'metadata updated', 'file': safe_name})

# Tratamento de erro para ficheiros muito grandes
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({'error': 'Ficheiro demasiado grande'}), 413

# UI simples para testes (upload + list + download + delete)
UI_HTML = """
<!doctype html>
<title>umDrive - UI simples</title>
<h1>umDrive — UI simples</h1>

<form id="uploadForm">
  <input type="file" name="file" id="fileInput">
  <button type="submit">Enviar</button>
</form>

<h2>Ficheiros</h2>
<ul id="files"></ul>

<script>
async function loadFiles(){
  const res = await fetch('/api/files');
  const files = await res.json();
  const ul = document.getElementById('files');
  ul.innerHTML = '';
  files.forEach(f => {
    const li = document.createElement('li');
    li.innerHTML = `${f.name} (${f.size} bytes) - <a href="${f.download_url}">download</a> - <button onclick="del('${encodeURIComponent(f.name)}')">apagar</button>`;
    ul.appendChild(li);
  });
}

async function del(name){
  const decoded = decodeURIComponent(name);
  const res = await fetch('/api/files/' + decoded, {method: 'DELETE'});
  if(res.ok) loadFiles();
  else alert('Erro ao apagar');
}

document.getElementById('uploadForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const inp = document.getElementById('fileInput');
  if(!inp.files.length) return alert('Escolhe um ficheiro');
  const fd = new FormData();
  fd.append('file', inp.files[0]);
  const res = await fetch('/api/files', {method: 'POST', body: fd});
  if(res.ok){
    document.getElementById('fileInput').value = '';
    loadFiles();
  } else {
    const txt = await res.text();
    alert('Erro upload: ' + txt);
  }
});

loadFiles();
</script>
"""

@app.route("/ui")
def ui():
    return render_template_string(UI_HTML)

if __name__ == "__main__":
    # Executa em 0.0.0.0 para poderes aceder desde host/VM
    app.run(host="0.0.0.0", port=5000, debug=True)
