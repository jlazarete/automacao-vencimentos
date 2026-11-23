#!/usr/bin/env python3
"""
Consolida o código e a documentação do projeto em UM arquivo Markdown para o NotebookLM.

O arquivo contém: a árvore de arquivos, o conteúdo dos arquivos de texto RASTREADOS pelo
Git (nunca .env, planilhas nem nada ignorado) e os últimos commits (hash, data e assunto,
sem autor). Se algum arquivo tiver cara de segredo (token, chave privada), nada é gerado.

Uso:
    python3 scripts/sync_notebooklm.py                       # só gera notebooklm_context.md
    python3 scripts/sync_notebooklm.py --copiar              # e copia para GOOGLE_DRIVE_PATH
    python3 scripts/sync_notebooklm.py --copiar --notificar  # e avisa por e-mail (EMAIL_USER/EMAIL_PASS)

Variáveis (no .env): GOOGLE_DRIVE_PATH (pasta local do Google Drive), EMAIL_USER, EMAIL_PASS.
"""
import argparse
import datetime
import os
import re
import shutil
import smtplib
import ssl
import subprocess  # nosec B404 - usado só para chamar o git com argumentos fixos
import sys
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
NOME_SAIDA = "notebooklm_context.md"
EXTENSOES = {".py", ".md", ".yml", ".yaml", ".txt", ".example", ".sh"}
LIMITE_ARQUIVO_BYTES = 200_000
COMMITS_RECENTES = 20
PADRAO_SEGREDO = re.compile(
    r"\bsl\.[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}|sk-ant-[A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)


class ErroSegredo(Exception):
    """Um arquivo rastreado parece conter um segredo. A mensagem cita só o nome do arquivo."""


def _git(raiz, *args):
    executavel = shutil.which("git")
    if not executavel:
        raise RuntimeError("git não encontrado no PATH.")
    resultado = subprocess.run(  # nosec B603 - executável resolvido e argumentos literais, sem shell
        [executavel, *args], cwd=raiz, capture_output=True, text=True, check=True, encoding="utf-8",
    )
    return resultado.stdout


def arquivos_rastreados(raiz):
    """Caminhos (relativos) dos arquivos de texto versionados que entram no contexto."""
    saida = _git(raiz, "ls-files", "-z")
    escolhidos = []
    for caminho in sorted(p for p in saida.split("\0") if p):
        arquivo = Path(raiz) / caminho
        if Path(caminho).name == NOME_SAIDA or not arquivo.is_file():
            continue
        if arquivo.suffix.lower() not in EXTENSOES and arquivo.name != "LICENSE":
            continue
        if arquivo.stat().st_size > LIMITE_ARQUIVO_BYTES:
            continue
        escolhidos.append(caminho)
    return escolhidos


def montar_contexto(raiz, agora=None):
    """Monta o texto do contexto. Levanta ErroSegredo se achar algo parecido com segredo."""
    agora = agora or datetime.datetime.now()
    caminhos = arquivos_rastreados(raiz)
    blocos = []
    for caminho in caminhos:
        try:
            conteudo = (Path(raiz) / caminho).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # arquivo binário
        if PADRAO_SEGREDO.search(conteudo):
            raise ErroSegredo(f"Possível segredo em {caminho}. Nada foi gerado.")
        blocos.append(f"## Arquivo: {caminho}\n\n````\n{conteudo.rstrip()}\n````\n")

    commits = _git(raiz, "log", f"-n{COMMITS_RECENTES}", "--date=short", "--format=- %h %ad %s")
    arvore = "\n".join(f"- {c}" for c in caminhos)
    return (
        "# Contexto do projeto para o NotebookLM\n\n"
        f"Gerado em {agora.strftime('%d/%m/%Y %H:%M')}. Somente arquivos versionados no Git.\n\n"
        f"## Arquivos incluídos\n\n{arvore}\n\n"
        f"## Últimos commits\n\n{commits}\n"
        + "\n".join(blocos)
    )


def copiar_para_drive(arquivo, pasta_drive):
    """Copia o arquivo para a pasta do Google Drive local e devolve o destino."""
    if not pasta_drive:
        raise ValueError("GOOGLE_DRIVE_PATH não definido (configure no .env).")
    destino_dir = Path(pasta_drive).expanduser()
    if not destino_dir.is_dir():
        raise ValueError("GOOGLE_DRIVE_PATH não aponta para uma pasta existente.")
    return Path(shutil.copy2(arquivo, destino_dir / Path(arquivo).name))


def notificar_por_email(arquivo, tamanho_kb):
    """Avisa o gestor que o contexto foi atualizado. O e-mail não leva conteúdo do projeto."""
    usuario, senha = os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASS")
    if not usuario or not senha:
        raise ValueError("EMAIL_USER e EMAIL_PASS são necessários para --notificar.")
    msg = MIMEText(
        f"O contexto do NotebookLM foi atualizado em {datetime.datetime.now():%d/%m/%Y %H:%M}.\n"
        f"Arquivo: {Path(arquivo).name} ({tamanho_kb} KB).\n"
        "Este aviso não contém conteúdo do projeto.",
        "plain", "utf-8",
    )
    msg["Subject"] = "Contexto do NotebookLM atualizado"
    msg["From"] = msg["To"] = usuario
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30, context=ssl.create_default_context()) as servidor:
        servidor.login(usuario, senha)
        servidor.sendmail(usuario, usuario, msg.as_string())


def main(argv=None):
    load_dotenv(RAIZ / ".env")
    parser = argparse.ArgumentParser(description="Gera o contexto do projeto para o NotebookLM.")
    parser.add_argument("--saida", default=str(RAIZ / NOME_SAIDA), help="arquivo de saída")
    parser.add_argument("--copiar", action="store_true", help="copia para GOOGLE_DRIVE_PATH")
    parser.add_argument("--notificar", action="store_true", help="envia aviso por e-mail ao gestor")
    args = parser.parse_args(argv)

    try:
        texto = montar_contexto(RAIZ)
    except ErroSegredo as erro:
        print(f"ERRO: {erro}")
        return 3
    except (RuntimeError, subprocess.CalledProcessError, OSError):
        print("ERRO: não foi possível ler o repositório Git (git instalado e pasta versionada?).")
        return 1
    saida = Path(args.saida)
    saida.write_text(texto, encoding="utf-8")
    tamanho_kb = max(1, len(texto.encode("utf-8")) // 1024)
    print(f"Contexto gerado: {saida.name} ({tamanho_kb} KB).")

    try:
        if args.copiar:
            destino = copiar_para_drive(saida, os.environ.get("GOOGLE_DRIVE_PATH", ""))
            print(f"Copiado para o Google Drive local: {destino.name}.")
        if args.notificar:
            notificar_por_email(saida, tamanho_kb)
            print("Aviso enviado por e-mail.")
    except (ValueError, OSError, smtplib.SMTPException) as erro:
        print(f"ERRO: {type(erro).__name__}" + (f": {erro}" if isinstance(erro, ValueError) else ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
