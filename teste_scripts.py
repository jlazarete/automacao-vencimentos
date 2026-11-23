"""
Testes dos scripts auxiliares (gerador de planilha fictícia e sincronização do NotebookLM).
Usa repositório Git temporário, dados FICTÍCIOS, SMTP simulado e nenhuma rede.

Uso:
    python3 teste_scripts.py
"""
import datetime
import os
import ssl
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import gerar_planilha_ficticia as gerador  # noqa: E402
import sync_notebooklm as sync  # noqa: E402

AMBIENTE_GIT = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Autor Ficticio", "GIT_AUTHOR_EMAIL": "autor@exemplo.invalido",
    "GIT_COMMITTER_NAME": "Autor Ficticio", "GIT_COMMITTER_EMAIL": "autor@exemplo.invalido",
}


def _git(pasta, *args):
    subprocess.run(["git", *args], cwd=pasta, check=True, capture_output=True, env=AMBIENTE_GIT)


def criar_repositorio(pasta, arquivos, ignorados=None):
    """Cria um repositório Git temporário com `arquivos` versionados e `ignorados` só no disco."""
    _git(pasta, "init", "-q")
    (Path(pasta) / ".gitignore").write_text(".env\n*.xlsx\nnotas_privadas.txt\n", encoding="utf-8")
    for nome, conteudo in {**arquivos, **(ignorados or {})}.items():
        (Path(pasta) / nome).write_text(conteudo, encoding="utf-8")
    _git(pasta, "add", ".")
    _git(pasta, "commit", "-q", "-m", "feat: primeiro commit ficticio")


class TesteGeradorDePlanilha(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.saida = Path(self.tmp.name) / "clientes_teste.xlsx"

    def test_colunas_dados_ficticios_e_datas(self):
        hoje = datetime.date(2026, 1, 10)
        gerador.gerar(5, self.saida, hoje=hoje)
        df = pd.read_excel(self.saida, engine="openpyxl", dtype=str)
        self.assertEqual(list(df.columns), gerador.COLUNAS)
        self.assertEqual(len(df), 5)
        self.assertTrue(all(df["email"].str.endswith("@exemplo.invalido")))
        self.assertTrue(all(df["nome_cliente"].str.startswith("Cliente Ficticio")))
        for i, valor in enumerate(df["data_vencimento"]):
            self.assertEqual(valor, (hoje + datetime.timedelta(days=20 + i)).strftime("%Y-%m-%d"))

    def test_nao_sobrescreve_sem_pedir(self):
        gerador.gerar(2, self.saida)
        with self.assertRaises(FileExistsError):
            gerador.gerar(2, self.saida)
        gerador.gerar(3, self.saida, sobrescrever=True)
        self.assertEqual(len(pd.read_excel(self.saida, engine="openpyxl")), 3)

    def test_nome_padrao_passa_na_trava_do_atualizador(self):
        self.assertIn("teste", gerador.SAIDA_PADRAO.name)

    def test_linhas_invalidas(self):
        self.assertEqual(gerador.main(["--linhas", "0", "--saida", str(self.saida)]), 2)


class TesteSincronizacaoNotebookLM(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name) / "repo"
        self.raiz.mkdir()

    def test_inclui_so_arquivos_versionados_e_nunca_o_env(self):
        criar_repositorio(
            self.raiz,
            {"app.py": "print('codigo do projeto')\n", "README.md": "# Demo\n", ".env.example": "CHAVE=placeholder\n"},
            # notas_privadas.txt tem extensão permitida: só o "rastreado pelo Git" a mantém de fora.
            ignorados={".env": "CHAVE=valor-secreto-123\n", "dados.xlsx": "planilha",
                       "notas_privadas.txt": "NOTA-PRIVADA-999\n"},
        )
        texto = sync.montar_contexto(self.raiz)
        self.assertIn("codigo do projeto", texto)
        self.assertIn("CHAVE=placeholder", texto)
        self.assertNotIn("valor-secreto-123", texto)
        self.assertNotIn("NOTA-PRIVADA-999", texto)
        self.assertNotIn("Arquivo: .env\n", texto)
        self.assertNotIn("dados.xlsx", texto)

    def test_commits_sem_autor(self):
        criar_repositorio(self.raiz, {"app.py": "x = 1\n"})
        texto = sync.montar_contexto(self.raiz)
        self.assertIn("primeiro commit ficticio", texto)
        self.assertNotIn("exemplo.invalido", texto)
        self.assertNotIn("Autor Ficticio", texto)

    def test_segredo_em_arquivo_versionado_aborta_sem_vazar(self):
        token = "ghp_" + "a" * 30
        criar_repositorio(self.raiz, {"config.py": f"TOKEN = '{token}'\n"})
        with self.assertRaises(sync.ErroSegredo) as ctx:
            sync.montar_contexto(self.raiz)
        self.assertNotIn(token, str(ctx.exception))
        self.assertIn("config.py", str(ctx.exception))

    def test_ssl_create_default_context_nao_e_falso_positivo(self):
        criar_repositorio(self.raiz, {"main.py": "contexto = ssl.create_default_context()\n"})
        self.assertIn("create_default_context", sync.montar_contexto(self.raiz))

    def test_projeto_real_gera_contexto_sem_segredo(self):
        raiz_real = Path(__file__).resolve().parent
        if not (raiz_real / ".git").exists():
            self.skipTest("sem repositório Git neste ambiente")
        texto = sync.montar_contexto(raiz_real)
        self.assertIn("lgpd_engine.py", texto)
        self.assertNotIn("Arquivo: .env\n", texto)

    def test_copia_para_pasta_do_drive(self):
        origem = Path(self.tmp.name) / "ctx.md"
        origem.write_text("conteudo", encoding="utf-8")
        drive = Path(self.tmp.name) / "drive"
        drive.mkdir()
        destino = sync.copiar_para_drive(origem, str(drive))
        self.assertEqual(destino.read_text(encoding="utf-8"), "conteudo")
        with self.assertRaises(ValueError):
            sync.copiar_para_drive(origem, "")
        with self.assertRaises(ValueError):
            sync.copiar_para_drive(origem, str(drive / "nao-existe"))

    def test_notificacao_valida_certificado_e_nao_leva_conteudo(self):
        arquivo = Path(self.tmp.name) / "ctx.md"
        arquivo.write_text("CONTEUDO-SECRETO-DO-PROJETO", encoding="utf-8")
        ambiente = {"EMAIL_USER": "gestor@exemplo.invalido", "EMAIL_PASS": "senha-ficticia"}
        with mock.patch.dict(os.environ, ambiente), mock.patch.object(sync.smtplib, "SMTP_SSL") as smtp_ssl:
            servidor = mock.MagicMock()
            servidor.__enter__.return_value = servidor
            smtp_ssl.return_value = servidor
            sync.notificar_por_email(arquivo, 3)
        contexto = smtp_ssl.call_args.kwargs["context"]
        self.assertTrue(contexto.check_hostname)
        self.assertEqual(contexto.verify_mode, ssl.CERT_REQUIRED)
        enviado = servidor.sendmail.call_args.args[2]
        self.assertNotIn("CONTEUDO-SECRETO-DO-PROJETO", enviado)

    def test_notificacao_exige_credenciais(self):
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            sync.notificar_por_email(Path("x.md"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
