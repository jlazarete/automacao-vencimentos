# Guia de Execução Local e Resolução de Problemas

---
<p align="center">
  <a href="../README.md">Início</a> •
  <a href="README.md">Índice Geral</a> •
  <a href="backlog.md">Backlog/Kanban</a> •
  <strong>Execução Local</strong> •
  <a href="gerar-senha-app-google.md">Senha App Google</a> •
  <a href="configuracao-github-actions.md">GitHub Secrets</a> •
  <a href="token-dropbox.md">API Dropbox</a> •
  <a href="PLANO_RESILIENCIA.md">Resiliência & Logs</a>
</p>

---

Este guia orienta como configurar o ambiente, testar localmente o robô de alertas de vencimento de seguros e solucionar erros comuns. O ambiente de referência é **Linux (Ubuntu/Debian, terminal bash)**, o mesmo sistema usado pelo GitHub Actions. Os equivalentes para Windows estão no [apêndice](#apêndice-windows-powershell).

---

## Configuração do Ambiente Local

### 1. Criar o ambiente virtual e instalar as dependências

Na raiz do projeto:

```bash
sudo apt install python3-venv        # somente na primeira vez (Ubuntu/Debian)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> [!NOTE]
> No Ubuntu o comando `python` só existe **dentro do ambiente virtual ativado**. Fora dele, use sempre `python3`. Os exemplos deste guia usam `python3`, que funciona nas duas situações.

### 2. Criar o arquivo `.env` de configuração

```bash
cp .env.example .env
chmod 600 .env          # somente você pode ler o arquivo de credenciais
```

Edite o `.env` com os seus valores. O arquivo contém:

```text
EMAIL_USER=seu-email@gmail.com
EMAIL_PASS=suasenhaappgoogle16digitos
DROPBOX_APP_KEY=sua_app_key
DROPBOX_APP_SECRET=seu_app_secret
DROPBOX_REFRESH_TOKEN=seu_refresh_token

# Opcionais (padrões: 20 dias de antecedência e pasta raiz do Dropbox)
DIAS_ANTECEDENCIA=20
DROPBOX_PASTA=
```

> [!NOTE]
> Consulte os manuais específicos de [Senhas de App Google](gerar-senha-app-google.md) e [API do Dropbox](token-dropbox.md) para obter esses valores.

### Variáveis opcionais

| Variável | Padrão | Descrição |
| :--- | :--- | :--- |
| `DIAS_ANTECEDENCIA` | `20` | Janela em dias: alerta quando faltam esse número de dias ou menos (sem repetir). |
| `DROPBOX_PASTA` | *(raiz)* | Caminho da pasta no Dropbox onde a planilha `.xlsx` está localizada (ex: `/planilhas`). |

### 3. Executar o robô

```bash
python3 validar_codigo.py     # confere sintaxe, imports e estrutura
python3 main.py               # processa a planilha e envia os alertas
```

> [!WARNING]
> `main.py` envia e-mails reais quando encontra um vencimento no prazo. Para testar sem risco, use uma planilha de teste com dados fictícios (o arquivo precisa ter "teste" no nome).

---

## Validação Rápida de Código e Testes

Sempre que alterar o código, compile e rode os testes. Eles usam Dropbox e SMTP simulados, então não precisam de credenciais nem de rede:

```bash
python3 -m py_compile main.py
python3 teste_lgpd.py
python3 teste_seguranca.py
```

> [!IMPORTANT]
> Se o `py_compile` não exibir nenhuma saída, o código está sintaticamente correto.

---

## Resolução de Problemas Comuns (Linux)

### Erro: `ensurepip is not available` ao criar o `.venv`

O pacote do módulo `venv` não vem instalado por padrão no Ubuntu e no Debian. Instale e crie o ambiente novamente:

```bash
sudo apt install python3-venv
python3 -m venv .venv
```

### Erro: `python: command not found`

No Ubuntu só existe o `python3`. Use `python3 ...` ou ative o ambiente virtual (`source .venv/bin/activate`), que passa a oferecer o comando `python`.

### Erro: `externally-managed-environment` ao rodar `pip install`

O Ubuntu 23.04 ou superior bloqueia o `pip` fora de um ambiente virtual. Ative o `.venv` e instale lá. Evite `--break-system-packages`, que pode quebrar ferramentas do sistema.

### O `.venv` não ativa (pasta `Scripts/` em vez de `bin/`)

Um `.venv` criado no Windows não funciona no Linux. Apague e recrie:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Erro: `Permission denied` ao rodar `./main.py`

Os scripts já vêm com permissão de execução e `#!/usr/bin/env python3`. Se o seu sistema de arquivos perdeu o bit de execução, rode `chmod +x main.py` ou use `python3 main.py`.

### Acentos e emojis aparecem quebrados no terminal

O terminal precisa estar em UTF-8. Verifique com `locale` e, se preciso, rode `export LANG=C.UTF-8`.

---

## Apêndice: Windows (PowerShell)

O projeto também roda no Windows. A diferença está só na criação e na ativação do ambiente virtual:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Erro: `UnauthorizedAccess` ou "execução de scripts desabilitada"

A política padrão do Windows bloqueia scripts `.ps1` não assinados. Libere a execução **somente na janela atual** e ative novamente:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Os demais comandos (`python main.py`, `python teste_lgpd.py` e assim por diante) são iguais aos do Linux, trocando `python3` por `python`.
