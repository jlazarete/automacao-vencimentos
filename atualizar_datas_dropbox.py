#!/usr/bin/env python3
"""
Ferramenta de TESTE: reescreve as datas de vencimento de uma planilha FICTÍCIA no Dropbox
para forçar o gatilho de alerta (uma linha por dia, sempre 20 dias à frente).

Travas de segurança, porque este script SOBRESCREVE o arquivo no Dropbox:
  - exige o argumento --confirmar;
  - só altera o arquivo se o nome dele contiver "teste" (ex.: clientes_teste.xlsx).
    Uma planilha de produção nunca é tocada.

Uso:
    python3 atualizar_datas_dropbox.py --confirmar
"""
import calendar
import datetime
import io
import os
import sys

import dropbox

from main import (
    DROPBOX_PASTA,
    buscar_planilha_mais_recente,
    conectar_dropbox,
    ler_excel_da_memoria,
    obter_data_hora_brt,
)

MARCADOR_ARQUIVO_DE_TESTE = "teste"


def atualizar_planilha_dropbox():
    print("Iniciando a rotina de atualização de datas no Dropbox...")
    dbx = conectar_dropbox()

    caminho_arquivo = buscar_planilha_mais_recente(dbx, pasta=DROPBOX_PASTA)
    if not caminho_arquivo:
        print("Erro: planilha não encontrada.")
        return 1

    # path_lower já vem em minúsculas.
    if MARCADOR_ARQUIVO_DE_TESTE not in os.path.basename(caminho_arquivo):
        print(
            "RECUSADO: a planilha mais recente do Dropbox não é um arquivo de teste "
            f"(o nome precisa conter '{MARCADOR_ARQUIVO_DE_TESTE}'). Nada foi alterado."
        )
        return 1

    df = ler_excel_da_memoria(dbx, caminho_arquivo)
    if df is None:
        print("Erro ao ler a planilha na memória.")
        return 1
    if "data_vencimento" not in df.columns:
        print("Erro: a planilha não tem a coluna data_vencimento. Nada foi alterado.")
        return 1

    print(f"Planilha de teste possui {len(df)} linhas.")

    hoje = obter_data_hora_brt().date()

    # Janela de teste: de hoje até o último dia do mês corrente (inclusive)
    ultimo_dia_mes = calendar.monthrange(hoje.year, hoje.month)[1]
    fim_mes = hoje.replace(day=ultimo_dia_mes)
    dias_ate_fim_mes = (fim_mes - hoje).days + 1

    # Atualiza uma linha por dia até o fim do mês (ou menos, conforme o tamanho da planilha).
    # Linha i vence em hoje + 20 + i dias, então dispara o alerta de 20 dias em hoje + i.
    limite = min(dias_ate_fim_mes, len(df))
    for i in range(limite):
        nova_data = hoje + datetime.timedelta(days=20 + i)
        df.at[i, 'data_vencimento'] = nova_data.strftime("%Y-%m-%d")
        dia_disparo = hoje + datetime.timedelta(days=i)
        print(f"Linha {i + 1} dispara em {dia_disparo.strftime('%d/%m/%Y')} (vencimento {nova_data.strftime('%d/%m/%Y')}).")

    # Gera e envia direto da memória: nenhum arquivo com dados fica em disco.
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    print("Enviando a planilha de teste atualizada de volta ao Dropbox...")
    dbx.files_upload(buffer.getvalue(), caminho_arquivo, mode=dropbox.files.WriteMode.overwrite)

    print(f"Upload finalizado. Base de testes de {limite} dias (até {fim_mes.strftime('%d/%m/%Y')}) pronta.")
    return 0


if __name__ == "__main__":
    if "--confirmar" not in sys.argv[1:]:
        print("Este script SOBRESCREVE a planilha de teste no Dropbox. Rode com --confirmar para prosseguir.")
        sys.exit(2)
    sys.exit(atualizar_planilha_dropbox())
