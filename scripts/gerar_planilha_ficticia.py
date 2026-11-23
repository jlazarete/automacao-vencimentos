#!/usr/bin/env python3
"""
Gera uma planilha de clientes 100% FICTÍCIA para testar e demonstrar o robô.

Todos os dados são óbvios placeholders (Cliente Ficticio 01, e-mails em
exemplo.invalido, telefones 90000-xxxx). A linha i vence em hoje + 20 + i dias,
então a linha i dispara o alerta de 20 dias exatamente i dias depois de hoje.

Uso:
    python3 scripts/gerar_planilha_ficticia.py
    python3 scripts/gerar_planilha_ficticia.py --linhas 30 --saida dados_teste/clientes_teste.xlsx

O nome do arquivo precisa conter "teste" para ser aceito por atualizar_datas_dropbox.py.
"""
import argparse
import datetime
import sys
from pathlib import Path

import pandas as pd

COLUNAS = [
    "nome_cliente", "tipo_seguro", "data_vencimento",
    "telefone", "email", "numero_apolice", "numero_proposta",
]
TIPOS_SEGURO = ["Auto", "Residencial", "Vida", "Empresarial", "Viagem"]
SAIDA_PADRAO = Path("dados_teste") / "clientes_teste.xlsx"
ANTECEDENCIA_DIAS = 20


def montar_linhas(quantidade, hoje=None):
    """Devolve a lista de linhas fictícias, uma por cliente."""
    hoje = hoje or datetime.date.today()
    linhas = []
    for i in range(quantidade):
        numero = i + 1
        vencimento = hoje + datetime.timedelta(days=ANTECEDENCIA_DIAS + i)
        linhas.append({
            "nome_cliente": f"Cliente Ficticio {numero:02d}",
            "tipo_seguro": TIPOS_SEGURO[i % len(TIPOS_SEGURO)],
            "data_vencimento": vencimento.strftime("%Y-%m-%d"),
            "telefone": f"(11) 90000-{numero:04d}",
            "email": f"cliente{numero:02d}@exemplo.invalido",
            "numero_apolice": f"9{numero:09d}",
            "numero_proposta": f"8{numero:09d}",
        })
    return linhas


def gerar(linhas, saida, sobrescrever=False, hoje=None):
    """Grava a planilha em `saida` e devolve o caminho. Não sobrescreve sem pedir."""
    saida = Path(saida)
    if saida.exists() and not sobrescrever:
        raise FileExistsError(f"{saida} já existe. Use --sobrescrever para substituir.")
    saida.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(montar_linhas(linhas, hoje), columns=COLUNAS).to_excel(saida, index=False, engine="openpyxl")
    return saida


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gera uma planilha de clientes fictícia.")
    parser.add_argument("--linhas", type=int, default=14, help="quantidade de clientes (padrão: 14)")
    parser.add_argument("--saida", default=str(SAIDA_PADRAO), help=f"arquivo de saída (padrão: {SAIDA_PADRAO})")
    parser.add_argument("--sobrescrever", action="store_true", help="substitui o arquivo se ele já existir")
    args = parser.parse_args(argv)

    if args.linhas < 1:
        print("ERRO: --linhas deve ser maior que zero.")
        return 2
    try:
        caminho = gerar(args.linhas, args.saida, args.sobrescrever)
    except FileExistsError as erro:
        print(f"ERRO: {erro}")
        return 1
    print(f"Planilha fictícia gerada: {caminho} ({args.linhas} linhas, todos os dados são fictícios).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
