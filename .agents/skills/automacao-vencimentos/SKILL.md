---
name: automacao-vencimentos
description: Diretrizes de desenvolvimento, ativação do ambiente virtual, validação e layout para o projeto de automação de vencimentos.
---

# Guia e Diretrizes do Projeto de Automação de Vencimentos

Este guia documenta as tarefas mais importantes, comandos e padrões visuais do projeto para garantir a facilidade de manutenção por desenvolvedores ou agentes parceiros.

## 1. Ativação do Ambiente Virtual (Linux)

O ambiente de referência é Linux com bash. Na primeira vez, crie o ambiente (no Ubuntu/Debian o módulo `venv` precisa ser instalado):

```bash
sudo apt install python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Nas próximas vezes basta `source .venv/bin/activate`. Fora do ambiente virtual use `python3`, pois o comando `python` só existe dentro dele. No Windows o equivalente está no apêndice de `docs/execucao-local.md`.

## 2. Validação de Código (Agente de Validação)

Antes de qualquer commit, execute o **agente de validação** que verifica sintaxe, imports, estrutura de funções, YAML do workflow e requirements, e depois os testes:

```bash
python3 validar_codigo.py
python3 teste_lgpd.py && python3 teste_seguranca.py && python3 teste_scripts.py
```

Para uma verificação rápida somente de sintaxe:

```bash
python3 -m py_compile main.py
```

## 3. Pipeline CI/CD (GitHub Actions)

O projeto possui dois workflows no GitHub Actions, ambos em `ubuntu-latest`:

- **`validacao.yml`** — Roda em todo push/PR para `main` e `dev`. Executa o `validar_codigo.py`, os três arquivos de teste, o Bandit e o pip-audit. Se falhar, bloqueia o merge.
- **`automacao.yml`** — Robô principal (cron diário 08:30 BRT), com interruptor `AUTOMACAO_ATIVA`. Roda a validação e os testes antes do `main.py`.

Ambos os workflows usam **Python 3.12**, a mesma versão do `python3` do Ubuntu 24.04.


## 4. Padrões de Design e Estilo nos E-mails de Alerta

Para manter a consistência profissional e a sobriedade dos alertas enviados pelo script, utilize sempre as seguintes especificações no template HTML:

### Links de Ação
- **Formato:** O próprio texto do número de telefone e do e-mail do cliente deve conter o link (WhatsApp ou mailto) direto, acompanhado por um emoji indicativo e um tooltip (`title`).
- **Cor Unificada:** `#0275d8` (azul sóbrio) com `font-weight: bold;` e sem sublinhados desnecessários (`text-decoration: none;`).
- **Exemplos HTML:**
  - WhatsApp: `<a href="https://wa.me/..." style="color: #0275d8; text-decoration: none; font-weight: bold;" title="Chamar no WhatsApp">contato 💬</a>`
  - E-mail: `<a href="mailto:..." style="color: #0275d8; text-decoration: none; font-weight: bold;" title="Enviar E-mail">email ✉️</a>`

### Tabela de Dados (Destaques de Alerta)
- **Data de Vencimento:** A linha inteira deve ser destacada usando tons pasteis inspirados no padrão do "Gmail Pro".
- **Especificações de Estilo HTML:**
  ```html
  <tr style="background-color: #fce8e6; color: #c5221f;">
      <td style="padding: 10px; border: 1px solid #f5c2c2; font-weight: bold;">Data de Vencimento:</td>
      <td style="padding: 10px; border: 1px solid #f5c2c2; font-weight: bold;">{data_vencimento}</td>
  </tr>
  ```

## 5. Versionamento de Código (Git)

Ao final de cada etapa bem-sucedida de modificações, o fluxo do Git deve ser executado da seguinte forma:

```bash
# 1. Adicione as mudanças
git add main.py

# 2. Faça o commit com mensagem curta e descritiva
git commit -m "mensagem explicativa"

# 3. Envie para o repositório remoto
git push
```
