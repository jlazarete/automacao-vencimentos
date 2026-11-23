#!/usr/bin/env python3
"""
Agente de Validação — Automação de Vencimentos
===============================================
Script que valida a integridade do código antes de qualquer execução no pipeline.
Pode ser executado localmente ou pelo GitHub Actions.

Uso:
    python3 validar_codigo.py
"""

import sys
import os
import io
import py_compile
import ast
import importlib

# Garante saída UTF-8 mesmo em terminais com outra codificação (ex.: locale C ou cp1252 no Windows)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")



# ============================================================
# Configuração
# ============================================================

ARQUIVOS_PYTHON = ["main.py", "lgpd_engine.py"]

FUNCOES_OBRIGATORIAS_MAIN = [
    "validar_configuracao",
    "obter_data_hora_brt",
    "registrar_log",
    "conectar_dropbox",
    "buscar_planilha_mais_recente",
    "ler_excel_da_memoria",
    "enviar_email_alerta",
    "processar_planilha",
    "carregar_enviados",
    "salvar_enviados",
    "salvar_logs",
    "limpar_logs_antigos",
]

FUNCOES_OBRIGATORIAS_LGPD = [
    "mascarar_telefone",
    "mascarar_email",
    "mascarar_cartao",
    "anonimizar_dataframe",
]

MODULOS_IMPORTAVEIS = [
    "dropbox",
    "pandas",
    "openpyxl",
    "tenacity",
    "dotenv",
]

WORKFLOW_PATH = os.path.join(".github", "workflows", "automacao.yml")


# ============================================================
# Funções de Validação
# ============================================================

def validar_sintaxe(arquivo):
    """Compila o arquivo Python para verificar erros de sintaxe."""
    try:
        py_compile.compile(arquivo, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)


def validar_imports(modulos):
    """Tenta importar cada módulo para garantir que estão instalados."""
    erros = []
    for modulo in modulos:
        try:
            importlib.import_module(modulo)
        except ImportError as e:
            erros.append(f"{modulo}: {e}")
    return erros


def extrair_funcoes_definidas(arquivo):
    """Usa AST para extrair nomes de funções definidas no arquivo."""
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=arquivo)
        funcoes = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        ]
        return funcoes, None
    except SyntaxError as e:
        return [], f"Erro de sintaxe ao analisar {arquivo}: {e}"


def validar_estrutura(arquivo, funcoes_obrigatorias):
    """Verifica se todas as funções obrigatórias estão presentes no arquivo."""
    funcoes_encontradas, erro = extrair_funcoes_definidas(arquivo)
    if erro:
        return False, [erro]

    faltantes = [
        f for f in funcoes_obrigatorias
        if f not in funcoes_encontradas
    ]
    return len(faltantes) == 0, faltantes


def validar_yaml_workflow(caminho):
    """Valida a sintaxe do arquivo YAML do workflow."""
    if not os.path.exists(caminho):
        return False, "Arquivo não encontrado"
    try:
        import yaml
        with open(caminho, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f)
        if not isinstance(dados, dict):
            return False, "YAML não contém um dicionário válido"
        if "jobs" not in dados:
            return False, "YAML não contém a chave 'jobs'"
        return True, None
    except ImportError:
        # Se pyyaml não está instalado, faz validação básica
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                conteudo = f.read()
            if "jobs:" not in conteudo:
                return False, "YAML não contém a chave 'jobs:'"
            return True, None
        except Exception as e:
            return False, str(e)
    except Exception as e:
        return False, str(e)


def validar_requirements():
    """Verifica se o requirements.txt existe e tem conteúdo."""
    if not os.path.exists("requirements.txt"):
        return False, "requirements.txt não encontrado"
    with open("requirements.txt", "r", encoding="utf-8") as f:
        conteudo = f.read().strip()
    if not conteudo:
        return False, "requirements.txt está vazio"
    linhas = [l.strip() for l in conteudo.splitlines() if l.strip() and not l.strip().startswith("#")]
    if len(linhas) == 0:
        return False, "requirements.txt não contém nenhuma dependência"
    return True, None


# ============================================================
# Execução Principal
# ============================================================

def main():
    print("=" * 60)
    print("  AGENTE DE VALIDAÇÃO — Automação de Vencimentos")
    print("=" * 60)
    print()

    total_erros = 0

    # --- 1. Compilação Python ---
    print("📋 1/5 — Compilação Python (Sintaxe)")
    for arquivo in ARQUIVOS_PYTHON:
        if not os.path.exists(arquivo):
            print(f"  ❌ {arquivo} — arquivo não encontrado!")
            total_erros += 1
            continue
        ok, erro = validar_sintaxe(arquivo)
        if ok:
            print(f"  ✅ {arquivo}")
        else:
            print(f"  ❌ {arquivo} — {erro}")
            total_erros += 1
    print()

    # --- 2. Importações ---
    print("📋 2/5 — Importações de Módulos")
    erros_import = validar_imports(MODULOS_IMPORTAVEIS)
    if not erros_import:
        print(f"  ✅ Todos os {len(MODULOS_IMPORTAVEIS)} módulos importados com sucesso")
    else:
        for erro in erros_import:
            print(f"  ❌ {erro}")
            total_erros += 1
    print()

    # --- 3. Estrutura do código ---
    print("📋 3/5 — Estrutura do Código (Funções Obrigatórias)")
    for arquivo, funcoes in [
        ("main.py", FUNCOES_OBRIGATORIAS_MAIN),
        ("lgpd_engine.py", FUNCOES_OBRIGATORIAS_LGPD),
    ]:
        if not os.path.exists(arquivo):
            print(f"  ❌ {arquivo} — arquivo não encontrado!")
            total_erros += 1
            continue
        ok, faltantes = validar_estrutura(arquivo, funcoes)
        if ok:
            print(f"  ✅ {arquivo} — todas as {len(funcoes)} funções presentes")
        else:
            print(f"  ❌ {arquivo} — funções ausentes: {', '.join(faltantes)}")
            total_erros += 1
    print()

    # --- 4. YAML do Workflow ---
    print("📋 4/5 — Workflow do GitHub Actions (YAML)")
    ok, erro = validar_yaml_workflow(WORKFLOW_PATH)
    if ok:
        print(f"  ✅ {WORKFLOW_PATH}")
    else:
        print(f"  ❌ {WORKFLOW_PATH} — {erro}")
        total_erros += 1
    print()

    # --- 5. Requirements ---
    print("📋 5/5 — Arquivo de Dependências")
    ok, erro = validar_requirements()
    if ok:
        print("  ✅ requirements.txt")
    else:
        print(f"  ❌ requirements.txt — {erro}")
        total_erros += 1
    print()

    # --- Resultado Final ---
    print("=" * 60)
    if total_erros == 0:
        print("  ✅ VALIDAÇÃO COMPLETA — Nenhum problema encontrado!")
        print("=" * 60)
        return 0
    else:
        print(f"  ❌ VALIDAÇÃO FALHOU — {total_erros} problema(s) encontrado(s)")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
