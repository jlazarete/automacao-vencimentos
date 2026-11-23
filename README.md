<h1 align="center">Automação Inteligente de Alertas de Vencimento</h1>

<p align="center">
  <strong>Monitoramento preditivo e autônomo de renovação de apólices de seguros via Dropbox e Gmail com compliance LGPD.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Dropbox-API-0061FF?style=for-the-badge&logo=dropbox&logoColor=white" alt="Dropbox API" />
  <img src="https://img.shields.io/badge/Gmail-Alerts-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Gmail SMTP" />
  <img src="https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?style=for-the-badge&logo=github-actions&logoColor=white" alt="GitHub Actions" />
</p>

---

Uma solução automatizada baseada em **Python** e integrada ao **GitHub Actions**, projetada para monitorar planilhas consolidadas hospedadas no **Dropbox** e disparar alertas por e-mail (**Gmail**) de forma preditiva e 100% autônoma na nuvem.

O robô foi otimizado para atender regras de negócios dinâmicas, operando inteiramente sob as camadas gratuitas das ferramentas utilizadas, eliminando custos de infraestrutura e prevenindo a perda de prazos de renovação de apólices de seguros.

---

## Funcionalidades e Diferenciais Técnicos

- **Leitura Direta na Memória (Sem Downloads Físicos):** Utiliza a biblioteca `io.BytesIO` integrada ao `pandas` e `openpyxl` para carregar o arquivo binário `.xlsx` diretamente na memória RAM do servidor temporário, sem deixar rastros ou salvar arquivos no disco rígido.
- **Busca Dinâmica por Extensão:** Realiza uma varredura na pasta configurada do Dropbox (`dbx.files_list_folder`), localizando de forma automática o arquivo com extensão `.xlsx` modificado mais recentemente. Ideal para clientes que realizam downloads diários com nomenclaturas variáveis (ex: `Clientes_09072026.xlsx`).
- **Gatilho em Janela de Antecedência:** Analisa a coluna `data_vencimento` e calcula a diferença de dias. O alerta sai quando faltam **20 dias ou menos** (e o vencimento ainda não passou). Se uma execução diária falhar, o alerta sai na seguinte; o histórico de envios impede a duplicidade. Na primeira execução, apólices que já estão dentro da janela geram alerta.
- **Centralização de Alertas (Foco no Gestor):** Estruturado para ler as informações individuais de cada cliente e apólice, mas direcionar o e-mail de alerta **exclusivamente para a caixa de entrada do Gestor**, blindando a comunicação externa.
- **E-mails de Alertas Enriquecidos:** Contém dados adicionais como apólice, proposta, contatos e links rápidos de ação (iniciar conversa no WhatsApp e redigir e-mail em um clique).
- **Deduplicação de Disparos:** Salva o histórico de envios no arquivo `/enviados.json` do Dropbox para evitar o reenvio de alertas duplicados. A chave é um hash (nunca o nome do cliente) seguido da data de vencimento, usada para expirar entradas antigas.
- **Auditoria de Execução (Logs de Rotação Mensal):** Cria automaticamente relatórios detalhados de cada execução na pasta `/logs/` do Dropbox (ex: `/logs/execucao_2026_07.log`). Mantém apenas os últimos 3 meses de histórico, aplicando rotação automática.
- **Estrutura Robusta de Timeouts e Validações:** Configuração de timeouts em conexões externas e verificação preventiva das colunas antes da execução (Fail-Fast).
- **Execução Autônoma (Cron Job):** Agendado no GitHub Actions para rodar diariamente sem depender do computador local ligado. Um interruptor (`AUTOMACAO_ATIVA`) mantém o robô desligado em forks e cópias do repositório; veja [GitHub Secrets e Variáveis](./docs/configuracao-github-actions.md).

### Módulo de Compliance e Privacidade (LGPD by Design)

Este projeto possui um motor DPO (`lgpd_engine.py`) nativo, que mascara dados pessoais (PII) antes que qualquer informação saia do ambiente controlado. Mascarar é pseudonimizar: reduz o risco, mas não substitui a avaliação do encarregado (DPO) de cada operação.
- **Mascaramento em E-mails:** Os alertas exibem ao Gestor o e-mail, a apólice e o telefone mascarados (`(11) 9****-1234`). Como o alerta vai somente ao Gestor, os links de ação (WhatsApp e `mailto:`) continuam funcionais e carregam o contato completo no código-fonte da mensagem.
- **Tratamento Avançado de Placas e Documentos:** Identifica dinamicamente CPFs (11 dígitos) e CNPJs (14 dígitos), aplicando as máscaras correspondentes. Oculta os prefixos de placas de veículos (`***-1234`).
- **Limpeza Forense de Observações:** Campos de texto livre ("Observações"), altamente propensos a vazar dados sensíveis, são bloqueados por padrão através da substituição por `[TEXTO REMOVIDO - LGPD]`.
- **Criação de Base de Testes e BI (Safe Room):** Ao finalizar o alerta diário, o robô mascara 100% das colunas da planilha em memória e faz upload de uma base `base_anonimizada.xlsx` para a pasta `/compliance` no Dropbox. A base mantém iniciais, DDD, final do telefone, domínio do e-mail, últimos dígitos de documentos e as datas, o que a torna adequada a painéis estatísticos internos, mas não a publicação.
- **Falha Fechada:** Só passam em claro as colunas explicitamente classificadas como públicas (tipo de seguro, datas, valores). Uma coluna nova ou desconhecida na planilha sai removida da base anonimizada até ser classificada.
- **Logs sem Dados Pessoais:** Logs e mensagens de erro não registram nome, e-mail, telefone, caminhos do Dropbox nem o texto de exceções de bibliotecas. Nomes aparecem apenas mascarados (`M*** F***`). Ainda assim cada execução mostra contagens e números de linha, então **a operação real deve rodar em repositório privado**. Este repositório público é um case: a variável `AUTOMACAO_ATIVA` deve ficar sem definir aqui.

### Segurança

- **Conexão SMTP com validação de certificado** e HTML do e-mail com escape de todo valor vindo da planilha.
- **Testes automatizados** (`teste_lgpd.py`, `teste_seguranca.py` e `teste_scripts.py`) rodam no CI com Dropbox e SMTP simulados, sem rede e sem credenciais.
- **Análise estática** (Bandit) e **auditoria de dependências** (pip-audit) a cada push; GitHub Actions fixadas por SHA e com permissão mínima.
- Para relatar uma vulnerabilidade, veja a [Política de Segurança](./SECURITY.md).

---

## Início Rápido (Linux)

```bash
git clone https://github.com/jlazarete/automacao-vencimentos.git
cd automacao-vencimentos
sudo apt install python3-venv            # somente na primeira vez (Ubuntu/Debian)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 teste_lgpd.py && python3 teste_seguranca.py && python3 teste_scripts.py   # sem rede e sem credenciais
cp .env.example .env && chmod 600 .env   # depois preencha as credenciais
python3 main.py
```

O guia completo, a resolução de problemas e o apêndice para Windows estão em [Execução Local](./docs/execucao-local.md).

---

## Estrutura Padrão do Projeto

Abaixo está a disposição das pastas e arquivos do repositório:

```text
├── .github/
│   └── workflows/
│       ├── automacao.yml         # Workflow principal (cron diário 08:30 BRT, com interruptor)
│       └── validacao.yml         # CI: validação, testes, Bandit e pip-audit (push/PR)
├── docs/                         # Manuais técnicos de apoio operacional
├── .env.example                  # Modelo das variáveis de ambiente (somente placeholders)
├── .gitignore                    # Segredos, planilhas, CSVs e logs ficam fora do Git
├── LICENSE                       # Licença MIT (uso livre por terceiros)
├── SECURITY.md                   # Política de segurança e relato de vulnerabilidades
├── main.py                       # Código-fonte principal do robô em Python
├── lgpd_engine.py                # Motor DPO de anonimização LGPD
├── validar_codigo.py             # Agente de validação (sintaxe, imports, estrutura)
├── teste_lgpd.py                 # Testes do motor LGPD (dados fictícios)
├── teste_seguranca.py            # Testes de segurança e privacidade de ponta a ponta
├── teste_scripts.py              # Testes dos scripts auxiliares (NotebookLM e planilha fictícia)
├── atualizar_datas_dropbox.py    # Ferramenta de teste: reescreve datas de uma planilha fictícia
├── scripts/
│   ├── sync_notebooklm.py        # Consolida código e docs em um Markdown para o NotebookLM
│   ├── gerar_planilha_ficticia.py  # Gera uma planilha de clientes 100% fictícia
│   └── hooks/post-commit         # Hook opcional: atualiza o contexto após cada commit
├── requirements.txt              # Dependências obrigatórias com versões fixadas
└── README.md                     # Documentação do projeto
```

---

## Documentação de Apoio Operacional

Para manter as credenciais protegidas, configurar o ambiente local e garantir uma manutenção simplificada do robô, consulte os manuais detalhados criados na pasta `/docs`:

- [Central de Documentação (Índice Geral)](./docs/README.md)
- [Quadro Kanban e Backlog](./docs/backlog.md)
- [Guia de Implantação no Cliente](./docs/implantacao-cliente.md)
- [Guia de Execução Local e Resolução de Problemas](./docs/execucao-local.md)
- [Instruções para Gerar Senha de Aplicativo Google](./docs/gerar-senha-app-google.md)
- [Guia de Cadastro de Credenciais no GitHub Secrets](./docs/configuracao-github-actions.md)
- [Configuração da API do Dropbox & Refresh Token](./docs/token-dropbox.md)
- [Sincronização do NotebookLM e Planilha Fictícia](./docs/sincronizacao-notebooklm.md)

---

## Licença

Distribuído sob a licença MIT: veja o arquivo [LICENSE](./LICENSE). Você pode usar, modificar e redistribuir o código, inclusive comercialmente, mantendo o aviso de copyright. Todos os dados de exemplo e de teste deste repositório são fictícios.
