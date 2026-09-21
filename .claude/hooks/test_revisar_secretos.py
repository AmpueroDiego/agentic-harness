"""Pruebas reales con Git; solo configuran y commitean repos temporales."""
import html
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import revisar_secretos as revisor

RAIZ = Path(__file__).resolve().parents[2]
REVISOR = RAIZ / ".claude/hooks/revisar_secretos.py"
WRAPPER = RAIZ / ".claude/hooks/check-appsettings.py"
HOOKS = RAIZ / "scripts/hooks-repos"
SECRETO = "abc123realvalue"


def office(texto=None, xml=None, entrada="word/document.xml"):
    if xml is None:
        xml = '<w:document xmlns:w="urn:test"><w:p><w:r><w:t>' + html.escape(texto)
        xml += '</w:t></w:r></w:p></w:document>'
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as documento:
        documento.writestr(entrada, xml.encode("utf-8"))
    return salida.getvalue()


class PruebasSecretos(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="acmeorg-secretos-")
        self.addCleanup(self.temporal.cleanup)
        self.repo = Path(self.temporal.name) / "repo con espacios"
        self.repo.mkdir()
        self.env = os.environ.copy()
        for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.env.pop(variable, None)
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        # Permite que los hooks encuentren el mismo Python funcional que la suite.
        self.env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + self.env.get("PATH", "")
        self.git("init")
        self.git("config", "user.name", "Pruebas secretos")
        self.git("config", "user.email", "<email>")

    def ejecutar(self, argumentos, entrada=None, cwd=None):
        return subprocess.run([str(a) for a in argumentos], input=entrada,
                              cwd=cwd or self.repo, env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding="utf-8", errors="replace", check=False)

    def git(self, *args, check=True, repo=None):
        resultado = self.ejecutar(["git", *args], cwd=repo)
        if check:
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
        return resultado

    def stage(self, nombre, contenido, repo=None):
        destino = (repo or self.repo) / nombre
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido if isinstance(contenido, bytes) else contenido.encode("utf-8"))
        self.git("add", "--", nombre, repo=repo)
        return destino

    def revisar(self, *args):
        return self.ejecutar([sys.executable, REVISOR, *(args or ("--repo", self.repo))])

    def test_01_appsettings_secreto_staged(self):
        self.stage("appsettings.json", json.dumps({"ApiKey": SECRETO}))
        resultado = self.revisar()
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("appsettings.json: clave sensible", resultado.stdout)

    def test_02_appsettings_placeholders(self):
        for valor in ("", "REPLACE_ME", " replace_ME "):
            with self.subTest(valor=valor):
                self.stage("appsettings.json", json.dumps({"ApiKey": valor}))
                self.assertEqual(self.revisar().returncode, 0)

    def test_03_archivos_prohibidos(self):
        for nombre, esperado in (("appsettings.Development.json", 1),
                                 ("appsettings.LOCAL.JSON", 1), (".env", 1),
                                 (".env.prod.local", 1), (".env.example", 0),
                                 (".ENV.EXAMPLE", 0), (".env.waha.example", 0)):
            with self.subTest(nombre=nombre):
                self.stage(nombre, "{}")
                self.assertEqual(self.revisar().returncode, esperado)
                # Solo vacía el índice del repo temporal, conservando el archivo.
                self.git("read-tree", "--empty")

    def test_04_docx_runs_placeholder_y_conexion(self):
        xml = ('<w:document xmlns:w="urn:test"><w:p><w:r><w:t>API Key: abc123</w:t>'
               '</w:r><w:r><w:t>realvalue</w:t></w:r></w:p></w:document>')
        for datos, esperado in ((office(xml=xml), 1), (office("API Key: REPLACE_ME"), 0),
                                (office("Server=x;Database=y;User Id=u;Password=Sup3rS3cret!"), 1)):
            with self.subTest(esperado=esperado):
                self.stage("guia.docx", datos)
                resultado = self.revisar()
                self.assertEqual(resultado.returncode, esperado)
                self.assertNotIn(SECRETO, resultado.stdout + resultado.stderr)
                self.assertNotIn("Sup3rS3cret!", resultado.stdout + resultado.stderr)

    def test_05_readme_limpio(self):
        self.stage("README.md", "# Prueba\n")
        self.assertEqual(self.revisar().returncode, 0)

    def test_06_redaccion_y_limite(self):
        self.stage("appsettings.json", json.dumps([{"ApiKey": SECRETO}] * 25))
        resultado = self.revisar()
        self.assertEqual(resultado.returncode, 1)
        self.assertEqual(len(resultado.stdout.splitlines()), 20)
        self.assertNotIn(SECRETO, resultado.stdout + resultado.stderr)
        self.assertIn('"abc1...[REDACTADO, 15 chars]"', resultado.stdout)
        for valor in ("z", "abcd", "abc\ndefgh"):
            redactado = revisor.redactar(valor)
            self.assertNotIn(valor, redactado)
            self.assertNotIn("\n", redactado)

    def test_07_pre_commit_real(self):
        self.git("config", "core.hooksPath", HOOKS.as_posix())
        self.stage("appsettings.json", json.dumps({"ApiKey": SECRETO}))
        bloqueado = self.git("commit", "-m", "x", check=False)
        self.assertNotEqual(bloqueado.returncode, 0)
        self.assertIn("BLOQUEADO", bloqueado.stdout + bloqueado.stderr)
        self.assertNotIn(SECRETO, bloqueado.stdout + bloqueado.stderr)
        self.assertNotEqual(self.git("rev-parse", "--verify", "HEAD", check=False).returncode, 0)
        self.stage("appsettings.json", '{"ApiKey": "REPLACE_ME"}')
        self.stage("README.md", "# Sin secretos\n")
        limpio = self.git("commit", "-m", "x", check=False)
        self.assertEqual(limpio.returncode, 0, limpio.stdout + limpio.stderr)
        self.git("rev-parse", "--verify", "HEAD")

    def test_08_wrapper_stdin(self):
        for contenido, esperado in ((json.dumps({"ApiKey": SECRETO}), 1),
                                    ('{"ApiKey":""}', 0), ('{"ApiKey":"REPLACE_ME"}', 0),
                                    ('{json invalido', 0)):
            resultado = self.ejecutar([sys.executable, WRAPPER], entrada=contenido)
            self.assertEqual(resultado.returncode, esperado)
            self.assertNotIn(SECRETO, resultado.stdout + resultado.stderr)
            if esperado:
                self.assertEqual(resultado.stdout, '  ApiKey = "abc1...[REDACTADO, 15 chars]"\n')

    def test_09_docx_historico(self):
        anterior = revisor.git(RAIZ, "show", "0258855^:docs/guias/WAHA-Azure-VM.docx")
        if anterior.returncode:
            self.skipTest("No existe o no es accesible el blob histórico de WAHA")
        self.assertTrue(revisor.revisar_bytes("historico.docx", anterior.stdout))
        actual = revisor.git(RAIZ, "show", "HEAD:docs/guias/WAHA-Azure-VM.docx")
        self.assertEqual(actual.returncode, 0, "No se pudo leer el DOCX de HEAD")
        self.assertFalse(revisor.revisar_bytes("actual.docx", actual.stdout))

    def test_stage_no_working_tree_y_ruta_con_espacios(self):
        archivo = self.stage("carpeta con espacios/appsettings.json", json.dumps({"ApiKey": SECRETO}))
        archivo.write_text('{"ApiKey":""}', encoding="utf-8")
        self.assertEqual(self.revisar().returncode, 1)
        self.git("add", ".")
        archivo.write_text(json.dumps({"ApiKey": SECRETO}), encoding="utf-8")
        self.assertEqual(self.revisar().returncode, 0)

    def test_sin_repo_y_sin_stage(self):
        self.assertEqual(self.revisar().returncode, 0)
        self.assertEqual(self.revisar("--repo", self.repo.parent).returncode, 0)
        self.assertEqual(self.revisar("--repo", self.repo / "inexistente").returncode, 0)

    def test_json_bom_anidado_y_claves_exactas(self):
        contenido = '\ufeff' + json.dumps({"Config": [{"password": SECRETO}], "Token": SECRETO})
        self.stage("appsettings.QA.JSON", contenido)
        resultado = self.revisar()
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("Config[0].password", resultado.stdout)
        self.assertEqual(len(resultado.stdout.splitlines()), 1)
        self.assertEqual(revisor.revisar_json('{"Password":42}'), [])
        self.assertEqual(revisor.revisar_json('{invalido'), [])

    def test_json_como_lo_lee_dotnet(self):
        # Hallazgos de la revisión de Codex (2026-09-17): .NET acepta estas formas y el secreto funciona
        for contenido in ('{"Password":"%s",}' % SECRETO,
                          '{ // nota\n "ApiKey": "%s" /* fin */ }' % SECRETO,
                          '{"AdminSettings:Password":"%s"}' % SECRETO):
            with self.subTest(contenido=contenido):
                self.assertTrue(revisor.revisar_json(contenido))
        self.assertEqual(revisor.revisar_json('{"Url":"http://x//y", /* c */ "ApiKey":"",}'), [])
        self.assertEqual(revisor.revisar_json('{"AdminSettings:Password":"REPLACE_ME"}'), [])
        utf16 = b"\xff\xfe" + json.dumps({"Password": SECRETO}).encode("utf-16-le")
        self.stage("appsettings.json", utf16)
        self.assertEqual(self.revisar().returncode, 1)

    def test_auditoria_adversarial(self):
        # Hallazgos de la auditoría adversarial (Codex, 2026-09-17)
        self.assertTrue(revisor.revisar_bytes("a.docx", office('Password: "ab 123456789"')))
        self.assertFalse(revisor.revisar_bytes("a.docx", office('Password: "tu contraseña"')))
        # Opción A: frases entre comillas y palabras largas bloquean aunque sean solo letras
        for texto in ('Password: "correct horse battery staple"', "API_KEY=abcdefghijklmnop",
                      'Password: “Temporal 9x7k2m4p”', "Password: ‘ab 123456789’"):
            with self.subTest(texto=texto):
                self.assertTrue(revisor.revisar_bytes("a.docx", office(texto)))
        # Archivo ya commiteado limpio que después recibe un secreto (filtro M, no solo A)
        self.stage("appsettings.json", '{"ApiKey":""}')
        self.git("commit", "-m", "limpio")
        self.stage("appsettings.json", json.dumps({"ApiKey": SECRETO}))
        self.assertEqual(self.revisar().returncode, 1)
        # Si git no puede listar el stage, bloquea
        fallo = [subprocess.CompletedProcess([], 0, b".git", b""), subprocess.CompletedProcess([], 128, b"", b"x")]
        with mock.patch.object(revisor, "git", side_effect=fallo):
            self.assertTrue(revisor.revisar_repo(self.repo))
        # Zip bomb: se bloquea sin descomprimir
        with mock.patch.object(revisor, "MAX_BYTES_OFFICE", 10):
            self.assertIn("demasiado grande", revisor.revisar_bytes("a.docx", office("hola"))[0])

    def test_submodulo_no_bloquea(self):
        # El commit del submódulo no existe en este repo, como pasa en la realidad
        self.git("update-index", "--add", "--cacheinfo", "160000,0123456789abcdef0123456789abcdef01234567,vendor/lib")
        self.assertEqual(self.revisar().returncode, 0)

    def test_office_placeholders(self):
        for valor in ("", "REPLACE_ME", "<secreto-real>", "{secreto-real}", "${SECRETO_REAL}",
                      "%SECRETO_REAL%", "********", "xxxxxxxx", "........", "tu-secreto",
                      "tu_secreto", "YOUR-secreto", "your_secreto", "ejemplo123", "example123", "changeme123"):
            with self.subTest(valor=valor):
                self.assertFalse(revisor.revisar_bytes("a.docx", office(f'API Key: "{valor}"')))

    def test_office_prosa_y_nombres_placeholder(self):
        # Falsos positivos reales de la guía de WAHA ya limpia (HEAD de 2026-09-17)
        for texto in ("WAHA_DASHBOARD_PASSWORD=DASHBOARD_PASS", "Con X-Waha-Webhook-Secret: adelante, el webhook",
                      "un error de Jwt:SecretKey que no tiene nada que ver", "Contraseña: temporal"):
            with self.subTest(texto=texto):
                self.assertFalse(revisor.revisar_bytes("a.docx", office(texto)))
        for valor in ("Sup3rS3cret", "bVrmQxLpZtYk", "abc_def_ghi", "ABCDEF123456"):
            with self.subTest(valor=valor):
                self.assertTrue(revisor.revisar_bytes("a.docx", office(f"WAHA_API_KEY={valor}")))

    def test_office_claves_y_umbral(self):
        for clave in ("API Key", "API_KEY", "api-key", "x-api-key", "WAHA_API_KEY",
                      "WebhookSecret", "Password", "contraseña", "contrasena", "pwd", "access_token"):
            with self.subTest(clave=clave):
                self.assertTrue(revisor.revisar_bytes("a.docx", office(f'"{clave}" = "{SECRETO}"')))
        self.assertFalse(revisor.revisar_bytes("a.docx", office("password=1234567")))
        self.assertTrue(revisor.revisar_bytes("a.docx", office("Data Source=x;Pwd=abc")))
        self.assertTrue(revisor.revisar_bytes("a.docx", office('Server=x;Password="con espacios"')))

    def test_xlsx_pptx_y_todas_las_entradas_xml(self):
        for extension, entrada, xml in (
            ("XLSX", "xl/sharedStrings.xml", '<sst><si><t>token: </t><r><t>abc123realvalue</t></r></si></sst>'),
            ("PPTX", "ppt/notesSlides/notesSlide1.xml", '<a:p xmlns:a="urn:test"><a:r><a:t>secret=abc123realvalue</a:t></a:r></a:p>')):
            with self.subTest(extension=extension):
                self.assertTrue(revisor.revisar_bytes("a." + extension, office(xml=xml, entrada=entrada)))
        self.assertFalse(revisor.revisar_bytes("a.txt", b"password=abc123realvalue"))

    def test_errores_fail_closed_archivos(self):
        roto = self.stage("roto.docx", b"no es zip")
        resultado = self.revisar("--archivos", roto, self.repo / "no-existe.docx")
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("documento Office ilegible", resultado.stdout)
        self.assertIn("no se pudo leer el archivo", resultado.stdout)
        self.assertNotIn("Traceback", resultado.stdout + resultado.stderr)

    def test_error_lectura_staged_fail_closed(self):
        respuestas = [subprocess.CompletedProcess([], 0, b".git", b""),
                      subprocess.CompletedProcess([], 0, b":000000 100644 0000000 1234567 A\0a.docx\0", b""),
                      subprocess.CompletedProcess([], 1, b"", b"detalle privado")]
        with mock.patch.object(revisor, "git", side_effect=respuestas):
            fallos = revisor.revisar_repo(self.repo)
        self.assertEqual(len(fallos), 1)
        self.assertIn("no se pudo leer el archivo staged", fallos[0])
        self.assertNotIn("detalle privado", fallos[0])

    def test_worktree_pre_commit_real(self):
        self.git("config", "core.hooksPath", HOOKS.as_posix())
        self.stage("README.md", "# Inicial\n")
        self.git("commit", "-m", "inicial")
        worktree = self.repo.parent / "worktree con espacios"
        self.git("worktree", "add", "-b", "prueba-hook", str(worktree))
        anterior = self.git("rev-parse", "HEAD", repo=worktree).stdout
        self.stage("appsettings.json", json.dumps({"ApiKey": SECRETO}), repo=worktree)
        bloqueado = self.git("commit", "-m", "x", repo=worktree, check=False)
        self.assertNotEqual(bloqueado.returncode, 0)
        self.assertIn("BLOQUEADO", bloqueado.stdout + bloqueado.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD", repo=worktree).stdout, anterior)
        self.stage("appsettings.json", '{"ApiKey":""}', repo=worktree)
        self.git("commit", "-m", "limpio", repo=worktree)

    def test_git_guard_regla_2(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("Bash no está disponible")
        self.stage("guia.docx", office("API Key: " + SECRETO))
        # REPOS ya usa separación por espacios en el hook legado: usar '.' desde el repo.
        self.env["GIT_GUARD_REPOS"] = "."
        comando = json.dumps({"tool_input": {"command": "git commit -m x"}})
        resultado = self.ejecutar([bash, RAIZ / ".claude/hooks/git-guard.sh"], entrada=comando)
        self.assertEqual(resultado.returncode, 2)
        self.assertIn("secretos en el stage", resultado.stderr)
        self.assertNotIn(SECRETO, resultado.stdout + resultado.stderr)
        self.stage("guia.docx", office("API Key: REPLACE_ME"))
        self.assertEqual(self.ejecutar([bash, RAIZ / ".claude/hooks/git-guard.sh"], entrada=comando).returncode, 0)


if __name__ == "__main__":
    unittest.main()
