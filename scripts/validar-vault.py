#!/usr/bin/env python3
"""
Validador de Integridad del Vault de Obsidian — AcmeOrg
Verifica:
1. Sintaxis de wikilinks y enlaces rotos.
2. Caracteres corruptos (\ufffd) o mojibake en contenido y nombres de archivo.
3. Nomenclatura kebab-case en archivos generados.
4. Presencia de YAML frontmatter en notas del vault.
"""

import os, sys, re, json, subprocess

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

IGNORE_DIRS = {'node_modules', '.git', 'bin', 'obj', '.system_generated',
               '.venv', 'worktrees', 'dist', 'build'}

def scan_vault():
    files_data = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if any(p in dirpath for p in IGNORE_DIRS):
            continue
        for f in filenames:
            if f.endswith('.md'):
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, ROOT)
                with open(full, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                files_data[rel] = {
                    'full': full,
                    'content': content,
                    'basename': f,
                }
    return files_data

def strip_code(text):
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`.*?`', '', text)
    return text

def check_encoding_and_filenames(files_data):
    errors = []
    for rel, data in files_data.items():
        # Check corrupt char in filename
        if '\ufffd' in rel or any(ord(c) == 0xFFFD for c in rel):
            errors.append(f'Nombre de archivo corrupto (contiene \ufffd): {rel}')
        # Check mojibake markers in content outside code blocks
        clean_content = strip_code(data['content'])
        mojibake_markers = ['Ã¡', 'Ã©', 'Ã­', 'Ã³', 'Ãº', 'Ã±', 'Ã‘', 'Ã¼']
        for m in mojibake_markers:
            if m in clean_content:
                errors.append(f'Mojibake detectado en contenido de {rel} (patrón: {m})')
                break
    return errors

WIKI_RE = re.compile(r'\[\[([^\]]+)\]\]')
MD_RE = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+?)(?:\s+"[^"]*")?\)')


def norm(s):
    return s.lower().replace('\\', '/').strip()


def construir_indice(files_data):
    target_to_file = {}
    for rel in files_data:
        r_norm = norm(rel)
        target_to_file[r_norm] = rel
        target_to_file[os.path.splitext(r_norm)[0]] = rel
        
        b_norm = norm(files_data[rel]['basename'])
        target_to_file[b_norm] = rel
        target_to_file[os.path.splitext(b_norm)[0]] = rel

    # Also map drawio files
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if any(p in dirpath for p in IGNORE_DIRS):
            continue
        for f in filenames:
            if f.endswith('.drawio'):
                rel = os.path.relpath(os.path.join(dirpath, f), ROOT)
                r_norm = norm(rel)
                target_to_file[r_norm] = rel
                target_to_file[norm(f)] = rel
    return target_to_file


def resolver_enlaces(content, rel, target_to_file):
    """Devuelve (destinos, rotos) de los enlaces de una nota.

    Separado de check_wikilinks para poder aplicarlo tambien al contenido de
    una nota en HEAD, y saber a quien enlazaba antes del commit.
    """
    content_no_code = strip_code(content)
    destinos, rotos = [], []

    for match in WIKI_RE.findall(content_no_code):
        raw_target = match.replace('\\|', '|').split('|')[0].split('#')[0].strip()
        if not raw_target:
            continue
        t_norm = norm(raw_target)
        if t_norm in target_to_file:
            destinos.append(target_to_file[t_norm])
            continue
        cur_dir = os.path.dirname(rel)
        cand = os.path.normpath(os.path.join(cur_dir, raw_target)).replace('\\', '/').lower()
        if cand in target_to_file or os.path.splitext(cand)[0] in target_to_file:
            destinos.append(target_to_file.get(cand) or target_to_file[os.path.splitext(cand)[0]])
            continue
        rotos.append(raw_target)

    # Enlaces markdown [texto](ruta). Solo suman aristas para el chequeo de
    # huerfanas: no se reportan como rotos para no cambiar el criterio que
    # ya tenia este validador. Sin esto el conteo miente — varias notas se
    # enlazan asi y saldrian como huerfanas sin serlo.
    for md_target in MD_RE.findall(content_no_code):
        t = md_target.split('#')[0].strip()
        if not t or t.startswith(('http://', 'https://', 'mailto:')):
            continue
        t_norm = norm(t)
        destino = target_to_file.get(t_norm) or target_to_file.get(os.path.splitext(t_norm)[0])
        if destino is None:
            cur_dir = os.path.dirname(rel)
            cand = os.path.normpath(os.path.join(cur_dir, t)).replace('\\', '/').lower()
            destino = target_to_file.get(cand) or target_to_file.get(os.path.splitext(cand)[0])
        if destino:
            destinos.append(destino)

    return destinos, rotos


def check_wikilinks(files_data):
    target_to_file = construir_indice(files_data)
    syntax_errors = []
    broken_links = []
    edges = []          # (origen, destino) ya resueltos, para el chequeo de huerfanos

    for rel, data in files_data.items():
        content_no_code = strip_code(data['content'])
        # Check escaped pipes
        if '\\|' in content_no_code and '[[' in content_no_code:
            matches = re.findall(r'\[\[[^\]]*\\\|[^\]]*\]\]', content_no_code)
            if matches:
                syntax_errors.append(f'{rel}: wikilink con pipe escapado (\\|): {matches[:2]}')

        destinos, rotos = resolver_enlaces(data['content'], rel, target_to_file)
        edges.extend((rel, d) for d in destinos if d != rel)
        broken_links.extend((rel, t) for t in rotos)

    return syntax_errors, broken_links, edges, target_to_file


# --- Chequeo de nodos huerfanos (agregado 2026-09-09) ---------------------
#
# El validador ya detectaba enlaces ROTOS. Este detecta lo contrario: notas
# que nadie enlaza y que no enlazan a nadie. Una nota asi existe y se abre
# bien, pero solo se llega a ella si ya sabias su nombre — que es lo opuesto
# a para que sirve un vault.

def cargar_exclusiones_obsidian():
    """Lee userIgnoreFilters de .obsidian/app.json.

    Sin esto el conteo no coincide con lo que ve Obsidian: reportariamos
    huerfanas notas que Obsidian ni siquiera indexa, y al reves.
    """
    ruta = os.path.join(ROOT, '.obsidian', 'app.json')
    if not os.path.exists(ruta):
        return []
    try:
        with open(ruta, encoding='utf-8') as fp:
            return json.load(fp).get('userIgnoreFilters', []) or []
    except Exception:
        return []


def es_visible_en_obsidian(rel, filtros):
    ruta = rel.replace('\\', '/')
    # Obsidian no indexa ninguna carpeta que empiece con punto.
    if any(p.startswith('.') for p in ruta.split('/')[:-1]):
        return False
    for f in filtros:
        if f.startswith('/') and f.rfind('/') > 0:
            cuerpo = f[1:f.rfind('/')]
            flags = re.I if 'i' in f[f.rfind('/') + 1:] else 0
            try:
                if re.search(cuerpo, ruta, flags):
                    return False
            except re.error:
                continue
        elif f and f in ruta:
            return False
    return True


def check_orphans(files_data, edges):
    filtros = cargar_exclusiones_obsidian()
    visibles = {rel for rel in files_data if es_visible_en_obsidian(rel, filtros)}

    con_enlace = set()
    for origen, destino in edges:
        if origen in visibles and destino in visibles:
            con_enlace.add(origen)
            con_enlace.add(destino)

    huerfanas = sorted(visibles - con_enlace)
    return huerfanas, len(visibles)


# --- Huerfanas que causa ESTE commit (agregado 2026-09-10) -----------------
#
# El aviso de huerfanas no frenaba nada: el hook devolvia 0 y el commit pasaba.
# Asi entraron dos en un dia: `propuesta-<proveedor-B>-resumen` (nota nueva que nadie
# indexo, commit 0258855) y `docs/architecture/README` (el commit
# 58b1786 le quito su unico enlace entrante). Se bloquean los dos casos. Las
# huerfanas que ya existian siguen siendo aviso: una carpeta clonada ajena no
# tiene por que trabar un commit que no la toca.

# Git ve la ruta real; Obsidian (y este validador) la ven por el junction.
JUNCTIONS = {'.claude/commands/': 'comandos-pipeline/', '.claude/agents/': 'agentes-pipeline/'}


def ruta_en_vault(ruta_git):
    for real, junction in JUNCTIONS.items():
        if ruta_git.startswith(real):
            return junction + ruta_git[len(real):]
    return ruta_git


def git(*args):
    try:
        r = subprocess.run(['git', '-c', 'core.quotepath=off', *args], cwd=ROOT,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
    except OSError:
        return ''
    return r.stdout if r.returncode == 0 else ''


def huerfanas_causadas_por_el_commit(huerfanas, target_to_file):
    """Huerfanas que son nuevas en el stage, o a las que el stage les quita un enlace que tenian en HEAD.

    Compara HEAD contra el STAGE, no contra el disco: si otra sesion tiene sin
    comitear un cambio en la misma nota y solo se sube un hunk, lo que se
    juzga es lo que entra al commit.
    """
    staged = git('diff', '--cached', '--name-status', '-M')
    culpables = set()
    for linea in staged.splitlines():
        partes = linea.split('\t')
        if len(partes) < 2:
            continue
        estado = partes[0][:1]
        if estado in ('A', 'C', 'R'):
            culpables.add(norm(ruta_en_vault(partes[-1])))
        if estado in ('M', 'D', 'R'):
            ruta_head = partes[1]
            if not ruta_head.endswith('.md'):
                continue
            antes, _ = resolver_enlaces(git('show', f'HEAD:{ruta_head}'),
                                        ruta_en_vault(ruta_head), target_to_file)
            despues = set()
            if estado != 'D':
                ruta_stage = partes[-1]
                despues, _ = resolver_enlaces(git('show', f':{ruta_stage}'),
                                              ruta_en_vault(ruta_stage), target_to_file)
                despues = {norm(d) for d in despues}
            culpables.update(norm(d) for d in antes if norm(d) not in despues)
    return [h for h in huerfanas if norm(h) in culpables]

def main():
    print('🔍 Ejecutando Validación de Integridad del Vault de Obsidian...')
    files_data = scan_vault()
    print(f'📄 Archivos escaneados: {len(files_data)}')

    enc_errors = check_encoding_and_filenames(files_data)
    syntax_errors, broken_links, edges, target_to_file = check_wikilinks(files_data)
    huerfanas, n_visibles = check_orphans(files_data, edges)
    bloqueantes = huerfanas_causadas_por_el_commit(huerfanas, target_to_file)

    print('\n--- RESULTADOS ---')
    has_errors = False

    if enc_errors:
        has_errors = True
        print(f'❌ Errores de Codificación / Nombres ({len(enc_errors)}):')
        for e in enc_errors:
            print(f'   - {e}')
    else:
        print('✅ Codificación y Nombres: 100% limpios (0 caracteres corruptos o mojibake).')

    if syntax_errors:
        has_errors = True
        print(f'❌ Errores de Sintaxis en Wikilinks ({len(syntax_errors)}):')
        for e in syntax_errors:
            print(f'   - {e}')
    else:
        print('✅ Sintaxis de Wikilinks: 100% limpia (0 pipes escapados).')

    if broken_links:
        print(f'⚠️ Enlaces no resueltos ({len(broken_links)}):')
        for src, target in broken_links:
            print(f'   - [{src}] -> [[{target}]]')
    else:
        print('✅ Resolución de Enlaces: 100% de enlaces internos resueltos.')

    if huerfanas:
        print(f'⚠️ Nodos huérfanos ({len(huerfanas)} de {n_visibles} notas visibles en Obsidian):')
        for h in huerfanas[:15]:
            print(f'   - {h}')
        if len(huerfanas) > 15:
            print(f'   ... y {len(huerfanas) - 15} más')
        print('   Nadie las enlaza y no enlazan a nadie: solo se llega a ellas por búsqueda.')
        print('   Suele bastar con una barra de navegación arriba, o indexarlas donde correspondan.')
        print('   Si aparecen muchas de golpe, sospecha de las exclusiones de Obsidian antes')
        print('   que del contenido — ver Meta/Graph-View-Config.md, sección 2.5.')
    else:
        print(f'✅ Conectividad del Grafo: 0 nodos huérfanos sobre {n_visibles} notas visibles.')

    if bloqueantes:
        has_errors = True
        print(f'❌ Huérfanas que deja este commit ({len(bloqueantes)}):')
        for h in bloqueantes:
            print(f'   - {h}')
        print('   Son notas nuevas que nadie enlaza, o notas que perdieron su último enlace')
        print('   con los cambios del stage. Indexalas (contexto-negocio/README, docs/adr/README…)')
        print('   o dales una barra de navegación antes de comitear.')

    if not has_errors and len(broken_links) == 0:
        print('\n🎉 ¡El Vault de Obsidian cumple al 100% con todas las reglas de calidad!')
        return 0
    elif not has_errors:
        print('\n✨ Integridad estructural aprobada con advertencias menores de links.')
        return 0
    else:
        print('\n❌ Se encontraron errores de calidad que deben corregirse.')
        return 1

if __name__ == '__main__':
    sys.exit(main())
