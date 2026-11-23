#!/usr/bin/env python3
import os
import io
import sys
import datetime
import hashlib
import smtplib
import ssl
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import tempfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html import escape
from urllib.parse import quote
import json
import re
import pandas as pd
from lgpd_engine import (
    anonimizar_dataframe,
    mascarar_apolice_proposta,
    mascarar_email,
    mascarar_nome,
    mascarar_telefone,
    somente_digitos,
)
import dropbox
from dropbox.exceptions import ApiError
from dotenv import load_dotenv

load_dotenv()

VARIAVEIS_OBRIGATORIAS = [
    "DROPBOX_REFRESH_TOKEN",
    "DROPBOX_APP_KEY",
    "DROPBOX_APP_SECRET",
    "EMAIL_USER",
    "EMAIL_PASS",
]

DROPBOX_REFRESH_TOKEN = os.environ.get("DROPBOX_REFRESH_TOKEN")
DROPBOX_APP_KEY = os.environ.get("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
DROPBOX_PASTA = os.environ.get("DROPBOX_PASTA", "").strip()

_dias_antecedencia = os.environ.get("DIAS_ANTECEDENCIA", "").strip()
try:
    DIAS_ANTECEDENCIA = int(_dias_antecedencia) if _dias_antecedencia else 20
except ValueError:
    DIAS_ANTECEDENCIA = -1

# Planilhas maiores que isso são recusadas (proteção contra arquivo malformado ou gigante).
TAMANHO_MAXIMO_PLANILHA = 20 * 1024 * 1024

# Arquivo de log da execução atual. Criado por configurar_logging() (não na importação).
LOG_FILE = None


class ErroControlado(RuntimeError):
    """Falha prevista pelo próprio robô. A mensagem é escrita por nós e é segura para o log."""


def configurar_logging():
    """Cria o log temporário da execução (permissão 0600, nome único) e liga saída no console."""
    global LOG_FILE
    descritor, LOG_FILE = tempfile.mkstemp(prefix="execucao_", suffix=".log")
    os.close(descritor)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True,
    )


def limpar_log_local():
    """Fecha os handlers e apaga o log temporário local (ele já foi enviado ao Dropbox)."""
    raiz = logging.getLogger()
    for handler in list(raiz.handlers):
        handler.close()
        raiz.removeHandler(handler)
    if LOG_FILE and os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)


def descrever_erro(erro):
    """
    Resume uma exceção para o log sem expor a mensagem original.

    Mensagens de bibliotecas podem conter valores de células da planilha, caminhos
    do Dropbox ou respostas do servidor. Por isso só o tipo (e o código SMTP) é registrado.
    """
    if isinstance(erro, ErroControlado):
        return str(erro)
    nome = type(erro).__name__
    if isinstance(erro, ApiError):
        return f"{nome} ({type(getattr(erro, 'error', None)).__name__})"
    if isinstance(erro, smtplib.SMTPResponseException):
        return f"{nome} (código {erro.smtp_code})"
    return nome


def validar_configuracao():
    """Valida credenciais obrigatórias e parâmetros de configuração antes da execução."""
    faltando = [nome for nome in VARIAVEIS_OBRIGATORIAS if not os.environ.get(nome)]
    if faltando:
        print(f"ERRO: Variáveis de ambiente ausentes ou vazias: {', '.join(faltando)}")
        return False

    if DIAS_ANTECEDENCIA <= 0:
        print("ERRO: DIAS_ANTECEDENCIA deve ser um número inteiro positivo.")
        return False

    return True


def obter_data_hora_brt():
    """Retorna o datetime atual no fuso horário de Brasília (BRT, UTC-3)."""
    tz_brt = datetime.timezone(datetime.timedelta(hours=-3))
    return datetime.datetime.now(tz_brt)


def registrar_log(mensagem):
    """Registra uma mensagem usando o módulo logging nativo."""
    logging.info(mensagem)


def email_valido(endereco):
    """Verifica se o endereço de e-mail tem formato válido (somente caracteres seguros)."""
    if not endereco:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}", endereco))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def conectar_dropbox():
    """Estabelece a conexão com a API do Dropbox utilizando o Refresh Token."""
    try:
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET,
            timeout=60
        )
        return dbx
    except Exception as e:
        registrar_log(f"Erro ao conectar ao Dropbox: {descrever_erro(e)}")
        raise


def buscar_planilha_mais_recente(dbx, pasta=""):
    """Lista os arquivos da pasta e encontra o arquivo .xlsx mais recente."""
    try:
        # Não registra o caminho nem o nome do arquivo: o log pode ser público (Actions).
        registrar_log("Buscando planilhas no Dropbox (" + ("pasta configurada" if pasta else "raiz") + ").")
        resultado = dbx.files_list_folder(pasta)

        arquivos_xlsx = []
        for entrada in resultado.entries:
            if isinstance(entrada, dropbox.files.FileMetadata) and entrada.name.endswith('.xlsx'):
                arquivos_xlsx.append(entrada)

        if not arquivos_xlsx:
            registrar_log("Nenhum arquivo .xlsx encontrado no Dropbox.")
            return None

        arquivo_recente = max(arquivos_xlsx, key=lambda x: x.server_modified)
        registrar_log(
            f"Planilha mais recente identificada dinamicamente (modificada em: {arquivo_recente.server_modified})."
        )
        return arquivo_recente.path_lower

    except ApiError as e:
        registrar_log(f"Erro da API do Dropbox ao listar pasta: {descrever_erro(e)}")
        return None
    except Exception as e:
        registrar_log(f"Erro inesperado ao buscar arquivo: {descrever_erro(e)}")
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def ler_excel_da_memoria(dbx, caminho_arquivo):
    """Baixa o arquivo binário diretamente para a memória RAM e lê com o Pandas."""
    try:
        registrar_log("Lendo a planilha diretamente da memória de origem...")
        metadata, res = dbx.files_download(path=caminho_arquivo)

        if metadata.size > TAMANHO_MAXIMO_PLANILHA:
            registrar_log("Planilha recusada: tamanho acima do limite permitido.")
            return None

        conteudo_binario = io.BytesIO(res.content)
        df = pd.read_excel(conteudo_binario, engine='openpyxl')
        return df
    except ApiError as e:
        registrar_log(f"Erro ao descarregar arquivo do Dropbox: {descrever_erro(e)}")
        return None
    except Exception as e:
        registrar_log(f"Erro ao processar planilha na memória: {descrever_erro(e)}")
        return None


def formatar_whatsapp_link(telefone):
    """Gera um link direto para o WhatsApp do cliente se o telefone for válido."""
    if pd.isna(telefone) or not telefone:
        return None
    nums = somente_digitos(telefone)
    if not nums:
        return None
    if len(nums) in [10, 11] and not nums.startswith('55'):
        nums = '55' + nums
    return f"https://wa.me/{nums}"


def tentar_converter_data(valor):
    """Tenta converter um valor bruto em um objeto datetime.date usando vários formatos comuns."""
    if isinstance(valor, (datetime.datetime, datetime.date)):
        return valor.date() if isinstance(valor, datetime.datetime) else valor

    valor_str = str(valor).strip()
    if pd.isna(valor) or not valor_str:
        return None

    formatos = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S"
    ]

    for formato in formatos:
        try:
            return datetime.datetime.strptime(valor_str, formato).date()
        except ValueError:
            continue

    try:
        dt = pd.to_datetime(valor_str, errors='raise')
        return dt.date()
    except Exception:
        return None


def carregar_enviados(dbx, caminho="/enviados.json"):
    """Carrega o histórico de envios do arquivo JSON no Dropbox. Retorna um conjunto (set) de chaves."""
    try:
        metadata, res = dbx.files_download(path=caminho)
        dados = json.loads(res.content.decode('utf-8'))
        return set(dados)
    except ApiError:
        registrar_log("Arquivo enviados.json não encontrado no Dropbox. Iniciando histórico vazio.")
        return set()
    except Exception as e:
        registrar_log(f"Erro ao ler enviados.json do Dropbox: {descrever_erro(e)}. Usando histórico vazio.")
        return set()


def gerar_chaves_envio(nome_cliente, data_vencimento):
    """
    Devolve (chave_nova, chave_legada) do controle de duplicidade.

    A chave nova usa um hash do nome, para que o enviados.json não guarde nomes de
    clientes em claro. O sufixo _AAAA-MM-DD continua visível porque salvar_enviados()
    o usa para expirar chaves antigas. A chave legada (nome em claro) só é consultada,
    nunca gravada, para não reenviar alertas que já constam no histórico antigo.
    """
    data_str = data_vencimento.strftime('%Y-%m-%d')
    base = f"{nome_cliente.strip().casefold()}|{data_str}"
    digest = hashlib.sha256(base.encode('utf-8')).hexdigest()[:16]
    return f"{digest}_{data_str}", f"{nome_cliente}_{data_str}"


def salvar_enviados(dbx, enviados, hoje, caminho="/enviados.json"):
    """Filtra chaves expiradas e salva o conjunto de enviados de volta no Dropbox."""
    try:
        chaves_filtradas = set()
        for chave in enviados:
            try:
                partes = chave.rsplit('_', 1)
                if len(partes) == 2:
                    data_str = partes[1]
                    dt_venc = datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
                    if dt_venc >= hoje:
                        chaves_filtradas.add(chave)
                else:
                    chaves_filtradas.add(chave)
            except Exception:
                chaves_filtradas.add(chave)

        dados_ordenados = sorted(list(chaves_filtradas))
        conteudo_bytes = json.dumps(dados_ordenados, indent=4, ensure_ascii=False).encode('utf-8')
        buffer = io.BytesIO(conteudo_bytes)

        dbx.files_upload(
            buffer.getvalue(),
            caminho,
            mode=dropbox.files.WriteMode.overwrite
        )
        registrar_log("Histórico de envios (enviados.json) atualizado com sucesso no Dropbox.")
    except Exception as e:
        registrar_log(f"Erro ao salvar enviados.json no Dropbox: {descrever_erro(e)}")


def carregar_logs(dbx, caminho):
    """Carrega o histórico de logs do Dropbox. Retorna o conteúdo como string."""
    try:
        metadata, res = dbx.files_download(path=caminho)
        return res.content.decode('utf-8')
    except ApiError:
        return ""
    except Exception as e:
        print(f"Erro ao carregar logs do Dropbox: {descrever_erro(e)}")
        return ""


def limpar_logs_antigos(dbx, hoje, pasta_logs="/logs"):
    """Deleta arquivos de logs mais antigos que 3 meses de forma segura."""
    try:
        resultado = dbx.files_list_folder(pasta_logs)
        for entrada in resultado.entries:
            if isinstance(entrada, dropbox.files.FileMetadata) and entrada.name.startswith("execucao_") and entrada.name.endswith(".log"):
                try:
                    nome_sem_extensao = entrada.name.rsplit('.', 1)[0]
                    partes = nome_sem_extensao.split('_')
                    if len(partes) == 3:
                        ano = int(partes[1])
                        mes = int(partes[2])
                        diferenca_meses = (hoje.year - ano) * 12 + (hoje.month - mes)
                        
                        if diferenca_meses >= 3:
                            dbx.files_delete_v2(entrada.path_lower)
                            print(f"Log antigo deletado (retenção de 3 meses excedida): {entrada.name}")
                except ApiError as e:
                    print(f"Erro de API do Dropbox ao deletar log individual: {descrever_erro(e)}")
                except Exception as e:
                    print(f"Aviso: Não foi possível deletar o log antigo {entrada.name}. Erro: {descrever_erro(e)}")
                    continue
    except ApiError:
        pass
    except Exception as e:
        print(f"Erro geral ao limpar logs antigos: {descrever_erro(e)}")


def salvar_logs(dbx, hoje, pasta_logs="/logs"):
    """Lê os logs do arquivo local, concatena ao mês corrente no Dropbox e faz upload."""
    if not LOG_FILE or not os.path.exists(LOG_FILE):
        return

    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        novos_logs_str = f.read()

    if not novos_logs_str.strip():
        return

    caminho_log = f"{pasta_logs}/execucao_{hoje.strftime('%Y_%m')}.log"
    try:
        historico = carregar_logs(dbx, caminho_log)

        agora_brt = obter_data_hora_brt()
        cabecalho = f"\n==================================================\n" \
                    f"EXECUÇÃO DO ROBÔ: {agora_brt.strftime('%d/%m/%Y %H:%M:%S')}\n" \
                    f"==================================================\n"
        log_completo = historico + cabecalho + novos_logs_str + "\n"

        limite_tamanho = 100000
        if len(log_completo) > limite_tamanho:
            aviso = "[LOGS CORTADOS PARA ECONOMIA DE ESPAÇO]\n"
            log_completo = aviso + log_completo[-limite_tamanho:]

        conteudo_bytes = log_completo.encode('utf-8')
        buffer = io.BytesIO(conteudo_bytes)

        dbx.files_upload(
            buffer.getvalue(),
            caminho_log,
            mode=dropbox.files.WriteMode.overwrite
        )
        print("Logs de execução salvos com sucesso no Dropbox.")

        limpar_logs_antigos(dbx, hoje, pasta_logs)

    except Exception as e:
        print(f"Erro ao salvar logs no Dropbox: {descrever_erro(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def enviar_email_alerta(cliente_nome, tipo_seguro, data_vencimento, dias_restantes, telefone, email, numero_apolice, numero_proposta):
    """Envia um e-mail com design profissional exclusivamente para o Gestor. Retorna True se enviado com sucesso."""
    try:
        destinatario = EMAIL_USER

        cliente_nome_safe = escape(cliente_nome)
        tipo_seguro_safe = escape(tipo_seguro)
        data_vencimento_safe = escape(data_vencimento)

        # Quebras de linha em header permitiriam injetar outros cabeçalhos (ex.: Bcc).
        cliente_nome_assunto = re.sub(r'[\r\n\t]+', ' ', cliente_nome)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 ALERTA: Renovação de Seguro - {cliente_nome_assunto}"
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario

        link_wa = formatar_whatsapp_link(telefone)
        telefone_mascarado = mascarar_telefone(telefone)
        if link_wa:
            texto_telefone = (
                f'<a href="{escape(link_wa, quote=True)}" style="color: #0275d8; text-decoration: none; font-weight: bold;" '
                f'title="Chamar no WhatsApp">{escape(telefone_mascarado)} 💬</a>'
            )
        else:
            texto_telefone = (
                escape(str(telefone_mascarado).strip())
                if pd.notna(telefone) and str(telefone).strip()
                else "Não informado"
            )

        if pd.notna(email) and str(email).strip():
            email_str = str(email).strip()
            if email_valido(email_str):
                email_mascarado = mascarar_email(email_str)
                # quote() codifica o endereço para URL e escape() protege o atributo HTML.
                email_href = escape(quote(email_str, safe='@'), quote=True)
                texto_email = (
                    f'<a href="mailto:{email_href}" style="color: #0275d8; text-decoration: none; font-weight: bold;" '
                    f'title="Enviar E-mail">{escape(email_mascarado)} ✉️</a>'
                )
            else:
                texto_email = "Não informado"
        else:
            texto_email = "Não informado"

        apolice_mascarada = mascarar_apolice_proposta(numero_apolice)
        texto_apolice = (
            escape(str(apolice_mascarada).strip())
            if pd.notna(numero_apolice) and str(numero_apolice).strip()
            else "Não informado"
        )
        proposta_mascarada = mascarar_apolice_proposta(numero_proposta)
        texto_proposta = (
            escape(str(proposta_mascarada).strip())
            if pd.notna(numero_proposta) and str(numero_proposta).strip()
            else "Não informado"
        )

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #d9534f; padding: 20px; text-align: center;">
                    <h2 style="color: #ffffff; margin: 0; font-size: 22px;">Aviso de Vencimento de Apólice</h2>
                </div>
                <div style="padding: 20px; background-color: #ffffff;">
                    <p>Olá, Gestor,</p>
                    <p>Identificamos um seguro que necessita de atenção para o processo de renovação comercial:</p>

                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr style="background-color: #f9f9f9;">
                            <td style="padding: 10px; border: 1px solid #dddddd; font-weight: bold; width: 35%;">Cliente:</td>
                            <td style="padding: 10px; border: 1px solid #dddddd;">{cliente_nome_safe}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #dddddd; font-weight: bold;">Tipo de Seguro:</td>
                            <td style="padding: 10px; border: 1px solid #dddddd;">{tipo_seguro_safe}</td>
                        </tr>
                        <tr style="background-color: #f9f9f9;">
                            <td style="padding: 10px; border: 1px solid #dddddd; font-weight: bold;">Nº Apólice:</td>
                            <td style="padding: 10px; border: 1px solid #dddddd;">{texto_apolice}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #dddddd; font-weight: bold;">Nº Proposta:</td>
                            <td style="padding: 10px; border: 1px solid #dddddd;">{texto_proposta}</td>
                        </tr>
                        <tr style="background-color: #f9f9f9;">
                            <td style="padding: 10px; border: 1px solid #dddddd; font-weight: bold;">Contato:</td>
                            <td style="padding: 10px; border: 1px solid #dddddd;">{texto_telefone}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #dddddd; font-weight: bold;">E-mail do Cliente:</td>
                            <td style="padding: 10px; border: 1px solid #dddddd;">{texto_email}</td>
                        </tr>
                        <tr style="background-color: #fce8e6; color: #c5221f;">
                            <td style="padding: 10px; border: 1px solid #f5c2c2; font-weight: bold;">Data de Vencimento:</td>
                            <td style="padding: 10px; border: 1px solid #f5c2c2; font-weight: bold;">{data_vencimento_safe}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #dddddd; font-weight: bold;">Prazo Restante:</td>
                            <td style="padding: 10px; border: 1px solid #dddddd; font-weight: bold; color: #f0ad4e;">{dias_restantes} dias</td>
                        </tr>
                    </table>

                    <p style="margin-top: 20px;">Por favor, entre em contato com o cliente para dar início às tratativas necessárias.</p>
                </div>
                <div style="background-color: #f5f5f5; padding: 15px; text-align: center; font-size: 12px; color: #777777; border-top: 1px solid #e0e0e0;">
                    Este é um alerta automático gerado pelo Sistema de Monitoramento de Apólices.
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        # Contexto padrão: valida o certificado e o hostname do servidor SMTP.
        # Sem ele, o SMTP_SSL do Python não verifica o certificado.
        contexto_tls = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30, context=contexto_tls) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, destinatario, msg.as_string())

        registrar_log(f"E-mail de alerta enviado com sucesso para o Gestor sobre o cliente: {mascarar_nome(cliente_nome)}")
        return True
    except Exception as e:
        registrar_log(f"Erro ao enviar e-mail: {descrever_erro(e)}")
        return False


def processar_planilha():
    """Processa a planilha do Dropbox e dispara alertas. Retorna True em sucesso, False em falha crítica."""
    dbx = None
    hoje = obter_data_hora_brt().date()

    resumo = {
        "linhas_lidas": 0,
        "linhas_ignoradas": 0,
        "datas_invalidas": 0,
        "alertas_enviados": 0,
        "alertas_pulados": 0,
        "alertas_falha": 0,
        "erros_linha": 0,
    }

    try:
        dbx = conectar_dropbox()
        if not dbx:
            raise ErroControlado("Falha na conexão com o Dropbox.")

        registrar_log(f"Gatilho configurado: {DIAS_ANTECEDENCIA} dias de antecedência.")

        caminho_arquivo = buscar_planilha_mais_recente(dbx, pasta=DROPBOX_PASTA)
        if not caminho_arquivo:
            raise ErroControlado("Nenhuma planilha .xlsx encontrada no Dropbox.")

        df = ler_excel_da_memoria(dbx, caminho_arquivo)
        if df is None:
            raise ErroControlado("Falha ao ler a planilha do Dropbox.")

        colunas_obrigatorias = ['data_vencimento', 'nome_cliente']
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
        if colunas_faltantes:
            raise ErroControlado(
                f"Planilha inválida. As seguintes colunas obrigatórias estão ausentes: {colunas_faltantes}"
            )

        registrar_log("Processando linhas da planilha de clientes...")

        enviados = carregar_enviados(dbx)
        enviados_inicial = enviados.copy()

        for index, linha in df.iterrows():
            try:
                resumo["linhas_lidas"] += 1
                nome_cliente = str(linha.get('nome_cliente', '')).strip()
                tipo_seguro = str(linha.get('tipo_seguro', '')).strip()
                vencimento_bruto = linha.get('data_vencimento')

                if pd.isna(vencimento_bruto) or not nome_cliente:
                    resumo["linhas_ignoradas"] += 1
                    continue

                data_vencimento = tentar_converter_data(vencimento_bruto)
                if not data_vencimento:
                    resumo["datas_invalidas"] += 1
                    registrar_log(f"Formato de data inválido na linha {index + 2} da planilha.")
                    continue

                dias_restantes = (data_vencimento - hoje).days

                # Janela, não data exata: se uma execução diária falhar ou for pulada, o alerta
                # sai na execução seguinte. O histórico de envios impede a duplicidade.
                if 0 < dias_restantes <= DIAS_ANTECEDENCIA:
                    chave_envio, chave_legada = gerar_chaves_envio(nome_cliente, data_vencimento)
                    if chave_envio in enviados or chave_legada in enviados:
                        resumo["alertas_pulados"] += 1
                        registrar_log(
                            f"Alerta já enviado anteriormente (linha {index + 2}, vencimento {data_vencimento}). Pulando."
                        )
                        continue

                    telefone = linha.get('telefone')
                    email = linha.get('email')
                    numero_apolice = linha.get('numero_apolice')
                    numero_proposta = linha.get('numero_proposta')

                    registrar_log(
                        f"Gatilho ativado (linha {index + 2}, cliente {mascarar_nome(nome_cliente)})! "
                        f"Vence em {data_vencimento} (Faltam {dias_restantes} dias)."
                    )
                    sucesso = enviar_email_alerta(
                        cliente_nome=nome_cliente,
                        tipo_seguro=tipo_seguro,
                        data_vencimento=data_vencimento.strftime("%d/%m/%Y"),
                        dias_restantes=dias_restantes,
                        telefone=telefone,
                        email=email,
                        numero_apolice=numero_apolice,
                        numero_proposta=numero_proposta
                    )
                    if sucesso:
                        enviados.add(chave_envio)
                        resumo["alertas_enviados"] += 1
                    else:
                        resumo["alertas_falha"] += 1
                        registrar_log(
                            f"Falha no envio (linha {index + 2}) — alerta NÃO marcado como enviado."
                        )

            except Exception as item_error:
                resumo["erros_linha"] += 1
                registrar_log(f"Erro ao processar linha {index + 2}: {descrever_erro(item_error)}")

        if enviados != enviados_inicial:
            salvar_enviados(dbx, enviados, hoje)

        registrar_log(
            f"RESUMO: {resumo['linhas_lidas']} linhas | "
            f"{resumo['alertas_enviados']} alertas enviados | "
            f"{resumo['alertas_pulados']} pulados (duplicados) | "
            f"{resumo['alertas_falha']} falhas de envio | "
            f"{resumo['linhas_ignoradas']} ignoradas | "
            f"{resumo['datas_invalidas']} datas inválidas | "
            f"{resumo['erros_linha']} erros de linha"
        )

        try:
            registrar_log("Aplicando motor LGPD na base completa para upload de compliance...")
            df_anonimizado = anonimizar_dataframe(df)
            # Gerada e enviada direto da memória: nenhum arquivo com dados fica em disco.
            buffer_anonimizado = io.BytesIO()
            df_anonimizado.to_excel(buffer_anonimizado, index=False, engine='openpyxl')
            dbx.files_upload(
                buffer_anonimizado.getvalue(),
                f"{DROPBOX_PASTA}/compliance/base_anonimizada.xlsx",
                mode=dropbox.files.WriteMode.overwrite
            )
            registrar_log("Base anonimizada enviada com sucesso para a pasta /compliance do Dropbox.")
        except Exception as lgpd_err:
            registrar_log(f"Aviso: Erro ao gerar/subir base anonimizada (LGPD): {descrever_erro(lgpd_err)}")

        if resumo["alertas_falha"] > 0:
            raise ErroControlado(f"{resumo['alertas_falha']} alerta(s) falharam no envio.")

        return True

    except Exception as e:
        registrar_log(f"Erro crítico no processamento da planilha: {descrever_erro(e)}")
        raise
    finally:
        if dbx:
            salvar_logs(dbx, hoje)


if __name__ == "__main__":
    configurar_logging()
    try:
        if not validar_configuracao():
            sys.exit(1)
        try:
            processar_planilha()
        except Exception:
            # O erro já foi registrado (sem dados pessoais) em processar_planilha().
            sys.exit(1)
    finally:
        limpar_log_local()
