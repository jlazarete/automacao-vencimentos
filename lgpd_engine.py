"""
Motor LGPD: mascaramento e anonimização de dados pessoais (PII).

Princípio de projeto: falhar fechado. Toda coluna que não esteja na lista de
colunas públicas e não tenha uma regra de máscara específica é removida do
resultado ([TEXTO REMOVIDO - LGPD]). Assim, uma coluna nova na planilha nunca
sai em claro por esquecimento.
"""
import re
import unicodedata

import pandas as pd

TEXTO_REMOVIDO = "[TEXTO REMOVIDO - LGPD]"


def somente_digitos(valor):
    """
    Devolve só os dígitos de um valor de célula.

    Quando a coluna é numérica e tem células vazias, o pandas lê o número como float
    (11999998888.0). Sem este tratamento, o ".0" viraria um dígito 0 a mais no final.
    """
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\D", "", str(valor))


def mascarar_nome(valor):
    if pd.isna(valor):
        return valor
    valor_str = str(valor).strip()
    partes = valor_str.split()
    mascarado = []
    for p in partes:
        if len(p) > 1:
            mascarado.append(p[0] + "***")
        else:
            mascarado.append(p)
    return " ".join(mascarado)


def mascarar_cpf_cnpj(valor):
    if pd.isna(valor):
        return valor
    numeros = somente_digitos(valor)

    if len(numeros) == 11:
        # CPF
        return f"***.***.{numeros[6:9]}-{numeros[9:]}"
    elif len(numeros) == 14:
        # CNPJ: 12.345.678/0001-90 -> **.*45.678/0001-**
        return f"**.*{numeros[3:5]}.{numeros[5:8]}/{numeros[8:12]}-**"
    return "***.***.***-**"


def mascarar_rg(valor):
    if pd.isna(valor):
        return valor
    return "**.***.***-*"


def mascarar_email(valor):
    if pd.isna(valor):
        return valor
    valor_str = str(valor).strip()
    if "@" in valor_str:
        usuario, dominio = valor_str.split("@", 1)
        usuario_mascarado = usuario[0] + "***" if len(usuario) > 1 else "***"
        return f"{usuario_mascarado}@{dominio}"
    return "***@***"


def mascarar_telefone(valor):
    if pd.isna(valor):
        return valor
    numeros = somente_digitos(valor)
    # Remove o DDI do Brasil (55) quando presente: 12 ou 13 dígitos.
    if len(numeros) in (12, 13) and numeros.startswith('55'):
        numeros = numeros[2:]
    ddd = numeros[:2]
    if len(numeros) == 11:
        return f"({ddd}) 9****-{numeros[7:]}"
    if len(numeros) == 10:
        return f"({ddd}) ****-{numeros[6:]}"
    # Formato desconhecido: não revela nenhum dígito.
    return "(**) ****-****"


def mascarar_cartao(valor):
    if pd.isna(valor):
        return valor
    numeros = somente_digitos(valor)
    if len(numeros) >= 13:
        return f"**** **** **** {numeros[-4:]}"
    return "**** **** **** ****"


def mascarar_apolice_proposta(valor):
    if pd.isna(valor):
        return valor
    valor_str = str(valor).strip()
    if not valor_str:
        return valor_str
    if len(valor_str) <= 4:
        return valor_str
    return "*" * (len(valor_str) - 4) + valor_str[-4:]


def mascarar_placa(valor):
    if pd.isna(valor):
        return valor
    valor_str = str(valor).strip()
    # Assume formato ABC-1234 ou ABC1A23
    # Simplesmente troca as 3 primeiras letras por asteriscos
    if len(valor_str) >= 3:
        # Substitui letras do inicio, mantendo os numeros
        return "***" + valor_str[3:]
    return "***-****"


# Padrões de dado pessoal que podem aparecer digitados em colunas "públicas" de texto livre.
_PADROES_PII_EM_TEXTO = re.compile(
    r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+"                      # e-mail
    r"|\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"                    # CPF
    r"|\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"              # CNPJ
    r"|\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b"                    # telefone
    r"|\b[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}\b"                    # placa
)


def sanear_coluna_publica(valor):
    """
    Protege as colunas liberadas em claro contra dois riscos:
    dado pessoal digitado em texto livre (e-mail, CPF, telefone, placa) e injeção de
    fórmula no Excel (valor iniciado por = + - @ vira fórmula ao abrir a planilha).
    """
    if not isinstance(valor, str):
        return valor
    valor = _PADROES_PII_EM_TEXTO.sub("[REMOVIDO - LGPD]", valor)
    if valor.lstrip().startswith(("=", "+", "-", "@")) and not re.fullmatch(r"\s*[-+]?[\d.,]+\s*", valor):
        valor = "'" + valor
    return valor


def limpar_observacoes(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return valor
    return TEXTO_REMOVIDO


# Colunas sem dado pessoal, liberadas em claro na base anonimizada.
# Comparação feita pelo nome normalizado (sem acento, minúsculo, separadores "_").
COLUNAS_PUBLICAS = frozenset({
    "tipo_seguro",
    "seguradora",
    "corretora",
    "data_inicio",
    "data_vencimento",
    "valor_premio",
    "franquia",
    "forma_pagamento",
    "modelo_veiculo",
    "ano_modelo",
    "compreensiva",
})

# Regras de máscara por palavra-chave, avaliadas em ordem. A primeira que casar vale.
# Palavras com 4+ letras casam por trecho ("telefones", "emailcliente"); as curtas
# (rg, cpf, tel) só casam com a palavra inteira, para não mascarar "margem" ou "cargo".
REGRAS_MASCARA = (
    (("cpf", "cnpj"), mascarar_cpf_cnpj),
    (("rg",), mascarar_rg),
    (("email", "mail"), mascarar_email),
    (("telefone", "celular", "whatsapp", "fone", "tel"), mascarar_telefone),
    (("cartao",), mascarar_cartao),
    (("apolice", "proposta", "chassi", "renavam"), mascarar_apolice_proposta),
    (("placa",), mascarar_placa),
    (("nome", "sobrenome", "segurado", "condutor", "titular",
      "proprietario", "beneficiario", "corretor"), mascarar_nome),
)


def _normalizar(texto):
    """Minúsculo, sem acento e com separadores reduzidos a '_'."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return "_".join(t for t in re.split(r"[^a-z0-9]+", sem_acento.lower()) if t)


def _casa(palavra, token):
    return palavra == token if len(palavra) < 4 else palavra in token


def _funcao_para_coluna(nome_coluna):
    """Escolhe a função de mascaramento de uma coluna. Desconhecida = remover."""
    normalizado = _normalizar(nome_coluna)
    if normalizado in COLUNAS_PUBLICAS:
        return sanear_coluna_publica  # liberada em claro, mas saneada
    tokens = normalizado.split("_")
    for palavras, funcao in REGRAS_MASCARA:
        if any(_casa(p, t) for p in palavras for t in tokens):
            return funcao
    # Texto livre (observação, obs, ...) e qualquer coluna desconhecida.
    return limpar_observacoes


def anonimizar_dataframe(df):
    """
    Devolve uma cópia do DataFrame com as colunas mascaradas pelo nome.

    Colunas públicas passam em claro (saneadas), colunas com regra recebem a máscara
    correspondente e todas as demais são removidas (falha fechada).
    """
    resultado = df.copy()
    for col in resultado.columns:
        funcao = _funcao_para_coluna(col)
        if funcao is not None:
            resultado[col] = resultado[col].apply(funcao)
    return resultado
