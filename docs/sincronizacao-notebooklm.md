# Sincronização do NotebookLM e Planilha Fictícia

---
<p align="center">
  <a href="../README.md">Início</a> •
  <a href="README.md">Índice Geral</a> •
  <a href="backlog.md">Backlog/Kanban</a> •
  <a href="execucao-local.md">Execução Local</a> •
  <a href="gerar-senha-app-google.md">Senha App Google</a> •
  <a href="configuracao-github-actions.md">GitHub Secrets</a> •
  <a href="token-dropbox.md">API Dropbox</a> •
  <a href="PLANO_RESILIENCIA.md">Resiliência & Logs</a> •
  <strong>NotebookLM</strong>
</p>

---

Este manual descreve dois scripts auxiliares da pasta `scripts/`: o que consolida o projeto em um único arquivo para o NotebookLM e o que gera uma planilha de clientes totalmente fictícia para testes e demonstrações.

---

## Sincronização com o NotebookLM

O script `scripts/sync_notebooklm.py` reúne o código, a documentação e os últimos commits em um único Markdown (`notebooklm_context.md`), que pode ser copiado para a pasta local do Google Drive e usado como fonte no NotebookLM.

### O que entra no arquivo

- Somente arquivos de texto **versionados no Git** (`.py`, `.md`, `.yml`, `.txt`, `.sh`, `.env.example` e `LICENSE`). Tudo o que está no `.gitignore` fica de fora: `.env`, planilhas, logs e anotações locais.
- Os últimos 20 commits, com hash, data e assunto. O nome e o e-mail do autor não entram.
- Arquivos acima de 200 KB e arquivos binários são ignorados.

> [!WARNING]
> Se algum arquivo versionado tiver cara de segredo (token do Dropbox ou do GitHub, chave da AWS, chave privada), o script aborta e **não gera nada**. A mensagem cita só o nome do arquivo, nunca o valor.

### Como usar

```bash
# 1. Só gera o arquivo notebooklm_context.md na raiz do projeto
python3 scripts/sync_notebooklm.py

# 2. Gera e copia para a pasta do Google Drive (GOOGLE_DRIVE_PATH no .env)
python3 scripts/sync_notebooklm.py --copiar

# 3. Gera, copia e avisa por e-mail (usa EMAIL_USER e EMAIL_PASS do .env)
python3 scripts/sync_notebooklm.py --copiar --notificar
```

| Variável (`.env`) | Para que serve |
| :--- | :--- |
| `GOOGLE_DRIVE_PATH` | Pasta local do Google Drive que recebe o arquivo (`--copiar`). |
| `EMAIL_USER` e `EMAIL_PASS` | Remetente e destinatário do aviso (`--notificar`). O e-mail só informa que o contexto foi atualizado, sem conteúdo do projeto. |

### Atualização automática após cada commit (opcional)

O repositório traz um hook de Git pronto em `scripts/hooks/post-commit`. Ele não vem instalado: a instalação é uma escolha sua, local à sua máquina.

```bash
cp scripts/hooks/post-commit .git/hooks/post-commit && chmod +x .git/hooks/post-commit
```

Para remover: `rm .git/hooks/post-commit`. Uma falha do hook nunca impede nem desfaz o commit.

> [!NOTE]
> O hook usa `--copiar` e exige `GOOGLE_DRIVE_PATH`. Ele não envia e-mail, para não gerar um aviso a cada commit. Para receber avisos, rode o script com `--notificar` quando fizer sentido.

---

## Planilha de Clientes Fictícia

O script `scripts/gerar_planilha_ficticia.py` cria uma planilha com a mesma estrutura que o robô lê (`nome_cliente`, `tipo_seguro`, `data_vencimento`, `telefone`, `email`, `numero_apolice`, `numero_proposta`), usando somente dados óbvios de exemplo: `Cliente Ficticio 01`, e-mails em `exemplo.invalido` e telefones `(11) 90000-xxxx`.

```bash
python3 scripts/gerar_planilha_ficticia.py                      # 14 linhas em dados_teste/clientes_teste.xlsx
python3 scripts/gerar_planilha_ficticia.py --linhas 30          # outra quantidade
python3 scripts/gerar_planilha_ficticia.py --sobrescrever       # substitui o arquivo existente
```

A linha `i` vence em hoje + 20 + `i` dias, então dispara o alerta de 20 dias exatamente `i` dias depois de hoje. Sem `--sobrescrever`, o script nunca apaga uma planilha existente.

> [!TIP]
> Para usar a planilha no teste de ponta a ponta, envie o arquivo para o Dropbox mantendo `teste` no nome. Depois, `atualizar_datas_dropbox.py --confirmar` reescreve as datas para a janela atual. Esse script recusa qualquer arquivo cujo nome não contenha `teste`.
