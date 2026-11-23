"""
Testes de segurança e privacidade do robô. Usa Dropbox e SMTP simulados, dados
FICTÍCIOS e nenhuma credencial real. Não acessa a rede.

Uso:
    python3 teste_seguranca.py
"""
import contextlib
import datetime
import email
import io
import json
import os
import re
import ssl
import tempfile
import types
import unittest
from unittest import mock

# Variáveis definidas ANTES de importar o robô (ele lê o ambiente na importação).
# load_dotenv() não sobrescreve variáveis já definidas, então um .env real não interfere.
os.environ.update({
    "DROPBOX_REFRESH_TOKEN": "token-ficticio",
    "DROPBOX_APP_KEY": "chave-ficticia",
    "DROPBOX_APP_SECRET": "segredo-ficticio",
    "EMAIL_USER": "gestor@exemplo.invalido",
    "EMAIL_PASS": "senha-ficticia",
    "DROPBOX_PASTA": "/pasta-secreta-ficticia",
    "DIAS_ANTECEDENCIA": "20",
})

import dropbox  # noqa: E402
import pandas as pd  # noqa: E402
from dropbox.exceptions import ApiError  # noqa: E402

import main as robo  # noqa: E402

NOME_A = "Maria Fulana Testeira"
EMAIL_A = "maria.testeira@exemplo.invalido"
TEL_A = "(11) 98765-4321"
NOME_B = "<script>alert(1)</script> Hacker"
EMAIL_B_MALICIOSO = 'x"><a/href=//exemplo.invalido>clique</a>@b.co'
PASTA = "/pasta-secreta-ficticia"
PLANILHA = "/planilha-teste.xlsx"
NOME_ARQUIVO = "clientes_ficticios.xlsx"


def _planilha_bytes():
    hoje = robo.obter_data_hora_brt().date()
    gatilho = (hoje + datetime.timedelta(days=20)).strftime("%Y-%m-%d")
    longe = (hoje + datetime.timedelta(days=50)).strftime("%Y-%m-%d")
    df = pd.DataFrame([
        {"nome_cliente": NOME_A, "tipo_seguro": "Auto", "data_vencimento": gatilho,
         "telefone": TEL_A, "email": EMAIL_A, "numero_apolice": "1234567890", "numero_proposta": "9876543210"},
        {"nome_cliente": NOME_B, "tipo_seguro": "<b>Vida</b>", "data_vencimento": gatilho,
         "telefone": "11 91234-5678", "email": EMAIL_B_MALICIOSO, "numero_apolice": "5555566666", "numero_proposta": "1111122222"},
        {"nome_cliente": "Fora Do Prazo", "tipo_seguro": "Auto", "data_vencimento": longe,
         "telefone": "11 90000-0000", "email": "fora@exemplo.invalido", "numero_apolice": "0000011111", "numero_proposta": "2222233333"},
    ])
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue(), gatilho


class DropboxFalso:
    """Imita só o trecho da API do Dropbox usado pelo robô, guardando tudo em memória."""

    def __init__(self, arquivos):
        self.arquivos = dict(arquivos)
        self.uploads = {}

    def files_list_folder(self, pasta):
        agora = datetime.datetime.now()
        meta = dropbox.files.FileMetadata(
            name=NOME_ARQUIVO, id="id:1", client_modified=agora, server_modified=agora,
            rev="0123456789abcdef", size=len(self.arquivos[PLANILHA]), path_lower=PLANILHA)
        return types.SimpleNamespace(entries=[meta])

    def files_download(self, path):
        if path not in self.arquivos:
            raise ApiError("req-id", None, "nao encontrado", "pt")
        conteudo = self.arquivos[path]
        return types.SimpleNamespace(size=len(conteudo)), types.SimpleNamespace(content=conteudo)

    def files_upload(self, dados, caminho, mode=None):
        self.uploads[caminho] = dados
        self.arquivos[caminho] = dados


class TesteExecucaoCompleta(unittest.TestCase):
    """Roda processar_planilha() inteiro e examina tudo o que sai do robô."""

    def executar(self, enviados_previos=None):
        planilha, self.vencimento = _planilha_bytes()
        arquivos = {PLANILHA: planilha}
        if enviados_previos is not None:
            arquivos["/enviados.json"] = json.dumps(enviados_previos).encode("utf-8")
        self.dbx = DropboxFalso(arquivos)

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tempdir_original = tempfile.tempdir
        tempfile.tempdir = self.tmp.name
        self.addCleanup(setattr, tempfile, "tempdir", tempdir_original)

        self.stdout = io.StringIO()
        with mock.patch.object(robo.smtplib, "SMTP_SSL") as smtp_ssl, \
                mock.patch.object(robo, "conectar_dropbox", return_value=self.dbx), \
                contextlib.redirect_stdout(self.stdout):
            smtp = mock.MagicMock()
            smtp.__enter__.return_value = smtp
            smtp_ssl.return_value = smtp
            robo.configurar_logging()
            try:
                robo.processar_planilha()
            finally:
                robo.limpar_log_local()
        self.smtp_ssl, self.smtp = smtp_ssl, smtp
        self.mensagens = [email.message_from_string(c.args[2]) for c in smtp.sendmail.call_args_list]

    def _html(self, mensagem):
        for parte in mensagem.walk():
            if parte.get_content_type() == "text/html":
                return parte.get_payload(decode=True).decode("utf-8")
        self.fail("mensagem sem parte HTML")

    def test_logs_e_arquivos_do_dropbox_nao_expoem_dados_pessoais(self):
        self.executar()
        log_dropbox = next(v for k, v in self.dbx.uploads.items() if k.startswith("/logs/")).decode("utf-8")
        enviados = self.dbx.uploads["/enviados.json"].decode("utf-8")
        proibidos = [NOME_A, "Fulana", "Testeira", "Hacker", EMAIL_A, "98765-4321", "91234-5678",
                     "pasta-secreta-ficticia", NOME_ARQUIVO, "planilha-teste", "1234567890"]
        for nome_saida, texto in (("stdout", self.stdout.getvalue()), ("log no Dropbox", log_dropbox),
                                  ("enviados.json", enviados)):
            for proibido in proibidos:
                self.assertNotIn(proibido, texto, f"'{proibido}' vazou em {nome_saida}")

    def test_enviados_json_guarda_apenas_hash_com_data(self):
        self.executar()
        chaves = json.loads(self.dbx.uploads["/enviados.json"])
        self.assertEqual(len(chaves), 2)
        for chave in chaves:
            self.assertRegex(chave, r"^[0-9a-f]{16}_\d{4}-\d{2}-\d{2}$")

    def test_base_de_compliance_sai_anonimizada(self):
        self.executar()
        caminho = f"{PASTA}/compliance/base_anonimizada.xlsx"
        base = pd.read_excel(io.BytesIO(self.dbx.uploads[caminho]), engine="openpyxl")
        texto = " | ".join(str(v) for v in base.to_numpy().ravel())
        for proibido in (NOME_A, EMAIL_A, "98765-4321", "1234567890", "9876543210", "Hacker"):
            self.assertNotIn(proibido, texto)

    def test_dois_alertas_enviados_e_fora_do_prazo_ignorado(self):
        self.executar()
        self.assertEqual(len(self.mensagens), 2)

    def test_alerta_atrasado_sai_na_janela_e_vencido_nao_sai(self):
        # Execução perdida: o vencimento está a 5 dias e ainda não houve alerta. Deve sair.
        # Já vencida (ontem): não deve sair.
        hoje = robo.obter_data_hora_brt().date()
        df = pd.DataFrame([
            {"nome_cliente": "Atrasado Ficticio", "tipo_seguro": "Auto",
             "data_vencimento": (hoje + datetime.timedelta(days=5)).strftime("%Y-%m-%d")},
            {"nome_cliente": "Vencido Ficticio", "tipo_seguro": "Auto",
             "data_vencimento": (hoje - datetime.timedelta(days=1)).strftime("%Y-%m-%d")},
        ])
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        with mock.patch.object(robo, "buscar_planilha_mais_recente", return_value=PLANILHA), \
             mock.patch.object(robo, "ler_excel_da_memoria", return_value=pd.read_excel(io.BytesIO(buf.getvalue()))), \
             mock.patch.object(robo, "carregar_enviados", return_value=set()), \
             mock.patch.object(robo, "salvar_enviados"), \
             mock.patch.object(robo, "salvar_logs"), \
             mock.patch.object(robo, "conectar_dropbox", return_value=mock.MagicMock()), \
             mock.patch.object(robo, "enviar_email_alerta", return_value=True) as envio:
            robo.processar_planilha()
        self.assertEqual(envio.call_count, 1)
        self.assertEqual(envio.call_args.kwargs["dias_restantes"], 5)

    def test_tls_com_verificacao_de_certificado(self):
        self.executar()
        contexto = self.smtp_ssl.call_args.kwargs["context"]
        self.assertTrue(contexto.check_hostname)
        self.assertEqual(contexto.verify_mode, ssl.CERT_REQUIRED)

    def test_html_do_email_nao_aceita_injecao(self):
        self.executar()
        html_a, html_b = (self._html(m) for m in self.mensagens)
        self.assertIn("mailto:" + EMAIL_A, html_a)
        # Linha B: nome com <script>, tipo com <b> e e-mail que tenta quebrar o href.
        self.assertNotIn("<script>", html_b)
        self.assertIn("&lt;script&gt;", html_b)
        self.assertNotIn("<b>Vida</b>", html_b)
        self.assertNotIn("<a/href", html_b)
        self.assertNotIn('mailto:x"', html_b)

    def test_chave_legada_com_nome_evita_reenvio(self):
        # enviados.json antigo guardava "Nome_AAAA-MM-DD" em claro.
        planilha, vencimento = _planilha_bytes()
        self.executar(enviados_previos=[f"{NOME_A}_{vencimento}"])
        self.assertEqual(len(self.mensagens), 1)

    def test_nenhum_arquivo_temporario_fica_no_disco(self):
        self.executar()
        self.assertEqual(os.listdir(self.tmp.name), [])


class TesteUnidades(unittest.TestCase):
    def test_link_whatsapp_com_telefone_lido_como_float(self):
        # Antes da correção: 11999998888.0 gerava wa.me/119999988880 (número de terceiro).
        self.assertEqual(robo.formatar_whatsapp_link(11999998888.0), "https://wa.me/5511999998888")
        self.assertEqual(robo.formatar_whatsapp_link("(11) 99999-8888"), "https://wa.me/5511999998888")
        self.assertIsNone(robo.formatar_whatsapp_link(None))

    def test_email_valido(self):
        for bom in ("a@b.co", "maria.silva+tag@sub.exemplo.com.br"):
            self.assertTrue(robo.email_valido(bom), bom)
        for ruim in (EMAIL_B_MALICIOSO, 'x"onmouseover="alert(1)"@b.co', "a@b", "a b@c.de",
                     "<x>@b.co", "a@b.c", "", None):
            self.assertFalse(robo.email_valido(ruim), repr(ruim))

    def test_chave_de_envio_nao_contem_o_nome(self):
        nova, legada = robo.gerar_chaves_envio(NOME_A, datetime.date(2026, 12, 1))
        self.assertNotIn("Maria", nova)
        self.assertTrue(nova.endswith("_2026-12-01"))
        self.assertEqual(legada, f"{NOME_A}_2026-12-01")
        # Mesmo cliente com caixa/espaços diferentes gera a mesma chave nova.
        self.assertEqual(nova, robo.gerar_chaves_envio("  maria fulana testeira ", datetime.date(2026, 12, 1))[0])

    def test_descrever_erro_nao_vaza_a_mensagem(self):
        self.assertEqual(robo.descrever_erro(ValueError("valor-secreto-da-celula")), "ValueError")
        self.assertEqual(robo.descrever_erro(robo.ErroControlado("mensagem nossa")), "mensagem nossa")
        self.assertNotIn("segredo", robo.descrever_erro(ApiError("req", None, "segredo", "pt")))

    def test_assunto_com_quebra_de_linha_nao_injeta_cabecalho(self):
        with mock.patch.object(robo.smtplib, "SMTP_SSL") as smtp_ssl:
            smtp = mock.MagicMock()
            smtp.__enter__.return_value = smtp
            smtp_ssl.return_value = smtp
            ok = robo.enviar_email_alerta(
                cliente_nome="Fulano\r\nBcc: alvo@exemplo.invalido", tipo_seguro="Auto",
                data_vencimento="01/12/2026", dias_restantes=20, telefone=None, email=None,
                numero_apolice=None, numero_proposta=None)
        self.assertTrue(ok)
        bruto = smtp.sendmail.call_args.args[2]
        self.assertIsNone(re.search(r"^Bcc:", bruto, re.MULTILINE | re.IGNORECASE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
