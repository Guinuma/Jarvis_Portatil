# Jarvis Portátil

Assistente de voz local no Windows com uma interface controlada por gestos da webcam.

Acompanha as cinco fases no [checklist de implementação](checklist.md). Os ensaios e os resultados estão no [checklist de testes](docs/CHECKLIST_TESTES.md), que inclui o [guião manual da Fase 2](docs/TESTES_FASE_2.md).

## Estrutura do repositório

- `jarvis/` contém a aplicação normal e o servidor do painel de gestos.
- `jarvis/ui/` contém a interface de chat e o código que liga as notas do H.O.L.O ao Ollama.
- `jarvis/integrations/` contém os adaptadores do Windows, ficheiros, documentos, voz, HTTP e MCP.
- `jarvis/messaging/` contém email local, IMAP, SMTP, rascunhos e Matrix.
- `jarvis/research/` contém pesquisa web, consulta de fontes, meteorologia, trânsito e horários GTFS.
- `jarvis/planning/` contém calendários externos, reuniões e transcrições.
- `jarvis/education/` contém cartões de estudo, avaliação e explicações com o Ollama local.
- `jarvis/automation/` contém as revisões de eliminação, ações HTTPS, integração visual do Windows e execução isolada.
- `jarvis/personal/` contém a despensa, os planos de refeições e os rascunhos de vida prática.
- `scripts/` contém o diagnóstico, a comparação de modelos e o teste de aceitação da Fase 1. Executa os comandos com `python -m` a partir da raiz do repositório.
- `tests/` contém os testes automatizados. Corre `python -m unittest discover -v`.
- `holo/` é o submódulo H.O.L.O Hands.

Os dois atalhos Windows estão na raiz. O ficheiro `jarvis_files_mcp.py` na raiz mantém o caminho usado pelas instalações do Hermes já configuradas.

## Abrir a aplicação JARVIS

No Windows, abre **Iniciar Jarvis Normal.cmd** (ou executa `python -m jarvis.app --open`). O chat abre no navegador em `http://127.0.0.1:4889`. Com o gateway do Hermes local a correr, escreve «Que ficheiros tenho na pasta autorizada?». A atividade mostra as chamadas de ferramentas emitidas pelo Hermes durante o pedido.

Carrega em **Ditar** ou prime **Alt+Shift+D** com a janela do JARVIS em foco para iniciar ou parar o ditado. Podes usar o reconhecimento local em português de Portugal, se o navegador tiver suporte e o pacote de idioma estiver disponível. Revê a transcrição antes de carregar em **Enviar**. Para ouvir uma resposta, carrega em **Ouvir resposta**. A leitura usa uma voz portuguesa instalada no Windows e pode ser interrompida em **Parar leitura**. Ativa **Ler respostas automaticamente** para ouvir as frases à medida que chegam. A leitura automática começa desativada. Usa **Voz** para escolher uma voz local em português e **Velocidade** para ajustar o ritmo de leitura. A opção **Automática** dá preferência a português de Portugal.

Durante um pedido, carrega em **Cancelar pedido** ou inicia o ditado e diz «cancela». Para corrigir o último lembrete pendente, dita ou escreve «afinal, daqui a 30 minutos» e envia. A correção substitui o aviso anterior se este ainda estiver pendente.

Usa **Microfone** para escolher uma entrada que o navegador disponibilize. Se a lista ainda estiver vazia, autoriza o microfone no primeiro ditado. **Saída de áudio do Windows** abre as definições de som para escolher os altifalantes ou auscultadores usados na leitura.

Para abrir este repositório no editor, escreve «Jarvis, abre o meu projeto no VS Code». O JARVIS procura o VS Code pelo executável ou pelo atalho `code` do Windows.

Para adicionar outros projetos, define `JARVIS_PROJECTS_FILE` na sessão que arranca o JARVIS com o caminho de um ficheiro JSON como este:

```json
[
  {"nome": "Física", "pasta": "C:/Projetos/Física"},
  {"nome": "Física", "pasta": "D:/Arquivo/Física"}
]
```

Pede «Abre o projeto Física no VS Code». Se houver vários resultados, o chat mostra um pedido com o caminho completo para cada opção. Usa um desses pedidos para escolher. O JARVIS só abre caminhos presentes na lista ou a pasta do seu próprio repositório.

Para procurar as notas da última sessão, guarda os ficheiros `.md` ou `.txt` em `notes/AAAA-MM-DD/` dentro do projeto. Pede «Encontra as notas da última sessão» para este repositório ou «Encontra as notas da última sessão do projeto Física» para um projeto autorizado. O resultado inclui os caminhos e a data mais recente com notas, retirada do nome da pasta.

Para agendar um aviso, escreve «Lembra-me daqui a 45 minutos de fazer uma pausa». Mantém o separador do JARVIS aberto até à hora do lembrete. Também podes pedir «Jarvis, abre o meu projeto, encontra as notas da última sessão e lembra-me daqui a 45 minutos de fazer uma pausa» num único pedido.

Outros pedidos locais:

- «Cria um temporizador de 5 minutos», «Lembra-me às 18:30 de fazer uma pausa» e «Cancela o lembrete».
- «Encontra o ficheiro README», «Procura conteúdo Ollama» ou «Abre o ficheiro README.md».
- «Cria o ficheiro rascunho.txt» e «Guarda uma nota Rever os resultados». Estes pedidos operam na pasta do JARVIS.
- «Abre a calculadora» e «Abre o site example.org». As aplicações reconhecidas incluem Calculadora, Bloco de Notas, Explorador e Paint.

O servidor local lê a chave da API do Hermes a partir de `JARVIS_HERMES_API_KEY` ou do ficheiro `.env` do Hermes (em `%LOCALAPPDATA%\hermes` por predefinição). O botão **H.O.L.O Hands** inicia e abre o painel de gestos se o submódulo estiver instalado. O atalho **Iniciar Jarvis.cmd** continua a abrir diretamente esse painel.

## Instalação e comandos adicionais da Fase 2

Instala as dependências com `python -m pip install -r requirements.txt`. Para preparar o ditado local alternativo, executa `python -m scripts.setup_voice` uma vez com Internet. O modelo Whisper `small` fica em `~/.jarvis-portatil/models/whisper-small`; podes indicar outro caminho compatível com `JARVIS_WHISPER_MODEL` antes de arrancar.

Quando o reconhecimento local do navegador não está disponível, **Ditar** grava até 60 segundos e envia o áudio apenas ao servidor JARVIS no próprio computador. Prime **Parar ditado**, aguarda a transcrição, revê e corrige o texto antes de enviar. Esta alternativa não apresenta palavras em tempo real. Para cancelar um pedido por voz nesta alternativa, diz «cancela» e para o ditado; a ação acontece quando a transcrição termina. **Escape** interrompe a leitura, termina a escuta e cancela o pedido em curso.

Comandos adicionais:

- `Encontra o ficheiro notas no projeto "Física"` e `Procura conteúdo temporizadores no projeto "Física"`: pesquisar noutros projetos autorizados.
- «Abre esse ficheiro»: usar um resultado único da última pesquisa. Com vários resultados, escolher «opção 1», «opção 2», etc., ou cancelar a seleção.
- «Consulta o volume», «Define o volume para 25%», «Mostra as saídas de áudio» e «Muda a saída de áudio para NOME»: controlar o som do Windows.
- `Consulta agenda AAAA-MM-DD` e `Consulta disponibilidade AAAA-MM-DD 09:00 até 18:00`: consultar a **agenda local do perfil**, sem incluir Google Calendar ou Outlook.
- «A que horas é a reunião de amanhã?» e «Mostra o evento N»: consultar um compromisso; vários compromissos exigem escolher o número do evento.

Os lembretes do chat dependem do separador aberto e não sobrevivem a uma atualização da página. O teste manual de 45 minutos está descrito no guião; não é iniciado automaticamente.

## Memórias, histórico e rotinas

Abre **Memórias** para consultar, editar, apagar ou exportar registos. No chat, experimenta «Lembra-te de que o meu projeto principal é o JARVIS» e «Consulta a memória projeto principal». Usa **Histórico de conversas** para pesquisar e reabrir conversas guardadas no navegador. Usa **Nova conversa** para começar outra. Apagar uma memória remove-a do editor e de novas consultas. As conversas anteriores continuam a mostrar o texto que lhes foi enviado.

O servidor guarda memórias e horários em `~/.jarvis-portatil/default.sqlite3`. Define `JARVIS_PROFILE` antes de arrancar para carregar outro perfil local. O histórico no navegador usa o mesmo nome de perfil e fica associado ao endereço onde abres o JARVIS.

Em **Rotina de programação**, podes executar a rotina ou agendá-la para amanhã às 09:00. O JARVIS usa a hora local do Windows, guarda o horário e executa a rotina quando o servidor está em funcionamento. A rotina pede ao VS Code que abra a pasta do JARVIS e abre as notas da última sessão. Podes indicar outro destino autorizado na memória de tipo projeto «projeto de programação».

Para a lista de compras, usa «Adiciona pão à lista de compras», «Marca como comprado pão na lista de compras», «Remove pão da lista de compras» e «Mostra a lista de compras».

Corre `python -m scripts.backup_memory memoria.sqlite3` para copiar o perfil atual. Para restaurar sem substituir um perfil existente, corre `python -m scripts.backup_memory memoria.sqlite3 --restore-to recuperado`. A cópia inclui as definições de voz do perfil. O histórico guardado no navegador fica separado.

Para organizar ficheiros dentro do projeto, usa `Renomeia "rascunho.txt" para "nota.txt"`, `Move "nota.txt" para "notes/nota.txt"` ou «Encontra duplicados». O movimento requer uma pasta de destino existente e um sistema de ficheiros com ligações rígidas. Os duplicados são agrupados por conteúdo e apresentados para revisão.

### Consultar um calendário externo

Define `JARVIS_CALENDARS_FILE` com um ficheiro JSON de calendários autorizados por perfil. `calendario` pode ser `primary` ou o identificador publicado nas definições do Google Calendar. `token_env` indica a variável de ambiente que contém um token OAuth válido com o âmbito `https://www.googleapis.com/auth/calendar.events.readonly`. Renova o token no cliente que o emitiu e reinicia o JARVIS quando expirar.

```json
{"perfis":{"default":[{"id":"pessoal","calendario":"primary","token_env":"JARVIS_CALENDAR_TOKEN_PESSOAL"}]}}
```

Usa «Mostra os calendários externos» ou «Mostra a agenda externa "pessoal" de amanhã». A consulta usa o dia no fuso horário do computador e apresenta os títulos, os horários e os links que a API disponibiliza. A agenda local continua acessível com «Mostra a agenda de amanhã». [Google Calendar API](https://developers.google.com/workspace/calendar/api/v3/reference/events/list)

Para executar um pedido de voz, usa **Ditar**, revê o campo de texto e escolhe **Enviar transcrição**. O JARVIS encaminha a versão revista pelo chat, com as permissões e confirmações do comando correspondente.

### Comandos da Fase 3

- **PDFs:** «Procura nos PDFs temporizadores», «Procura nos PDFs com OCR temporizadores» e `Resume o PDF "notas.pdf"`. Instala `pypdf` para pesquisar e resumir PDFs. Para OCR, instala também Poppler com `pdftoppm` e Tesseract. A pesquisa mostra ligações por página e atualiza o índice ao consultar os ficheiros. O OCR a pedido cobre páginas sem texto dentro das primeiras 20 páginas de cada PDF. Para reconhecer português, guarda [por.traineddata](https://github.com/tesseract-ocr/tessdata_fast/blob/main/por.traineddata) em `~/.jarvis-portatil/ocr/` ou aponta `JARVIS_TESSDATA_DIR` para a pasta que contém o ficheiro.
- **Agenda local:** `Cria um evento "Reunião" em 2026-11-15 10:00 por 30 minutos`, «Mostra a agenda de amanhã», «Reagenda o evento 1 para 2026-11-15 11:00» e «Avisa-me 10 minutos antes do evento 1». Mantém o chat aberto para receber os avisos.
- **Rotinas:** «Bom dia» mostra a agenda e as tarefas. «Fecha o dia» guarda uma nota com as tarefas. `Quando aparecer "pronto.txt" e existir "ok.txt", ativa o modo programação` guarda uma regra que executa uma vez enquanto o servidor estiver aberto.
- **Ficheiros:** `Comprime "nota.txt" para "nota.zip"`, `Extrai "nota.zip" para "extraido"`, `Copia "nota.txt" para "backup.txt"` e `Converte "nota.txt" para "nota.md"`.
- **Downloads:** «Previsualiza a organização de Downloads» mostra um plano. Revê-o e usa «Aprova o plano de Downloads 1» com o número recebido. Para testar noutra pasta, define `JARVIS_DOWNLOADS_DIR` antes de arrancar.
- **Windows:** «Consulta a bateria», «Consulta o armazenamento da unidade C», «Faz uma captura de ecrã», «Mostra os monitores» e `Move a janela "Calculadora" para o monitor 2`. As capturas são guardadas na pasta `capturas/` do projeto e requerem Pillow. Usa «Ativa o modo de foco» ou «Consulta o modo de foco» para controlar a sessão de concentração. Usa `Lê a seleção da janela "título"` numa aplicação que exponha a seleção à acessibilidade do Windows.

### Comandos da Fase 4

Usa caminhos relativos à pasta do JARVIS. A pesquisa de código e as consultas Git também aceitam o sufixo `no projeto "Nome autorizado"`. Para ativar os formatos de documentos, instala as dependências opcionais com `python -m pip install pypdf python-docx openpyxl python-pptx pdfplumber`.

| Pedido | Exemplo |
| --- | --- |
| Comparar PDFs e preparar um rascunho | `Compara versões do PDF "orçamento" e prepara um email` |
| Comparar dois documentos | `Compara "anterior.pdf" com "atual.pdf"` |
| Criar um documento | `Cria documento "notas.docx" com ["Título","Primeiro parágrafo"]` |
| Editar um parágrafo | `Edita documento "notas.docx" com {"2":"Texto revisto"}` |
| Criar ou editar uma folha | `Cria folha "resumo.xlsx" com {"folha":"Resumo","células":{"A1":10,"A2":"=A1*2"}}` |
| Criar uma apresentação | `Cria apresentação "reuniao.pptx" com [{"título":"Abertura","texto":"Agenda do dia"}]` |
| Editar um diapositivo | `Edita apresentação "reuniao.pptx" com {"1":{"título":"Reunião de projeto","texto":"Agenda revista"}}` |
| Extrair uma tabela | `Extrai a tabela 1 da página 2 de "orçamento.pdf" para "tabela.csv"` |
| Acompanhar um download | `Avisa-me quando o download "relatorio.pdf" acabar` |
| Cancelar um aviso | `Cancela o aviso de download 1` |
| Registar e consultar despensa | `Regista na despensa "arroz" 300 g` e `Mostra a despensa` |
| Sugerir receitas e ver passos | `Sugere receitas para 2 pessoas sem ["ovos"]` e `Mostra a receita "Arroz de ervilhas" para 2 pessoas` |
| Guardar uma receita | `Guarda receita "Arroz simples" com {"porções":2,"ingredientes":[{"nome":"arroz","quantidade":160,"unidade":"g"}],"passos":["Coze o arroz segundo a embalagem."]}` |
| Planear refeições e adicionar compras | `Planeia refeições de 2026-11-16 a 2026-11-19 para 2 pessoas` e `Adiciona as compras do plano 1` |
| Preparar um carrinho | `Prepara carrinho "Papelaria" com {"artigos":[{"nome":"Caderno","quantidade":2,"preço":"3,50"}],"portes":"2,00"}` |
| Rever opções de reserva | `Prepara reserva "Hotel" com {"opções":[{"nome":"Quarto duplo","início":"2026-12-01","fim":"2026-12-03","condições":"Cancelamento até dia 29","total":"180,00"}]}` |
| Preparar formulário | `Prepara formulário "Inscrição" com {"Nome":"Maria","Sessão":"Manhã"}` |
| Preparar itinerário | `Prepara viagem "Coimbra" com {"dias":[{"data":"2026-12-01","locais":["Baixa"]}],"transportes":[{"meio":"comboio","origem":"Lisboa","destino":"Coimbra","partida":"2026-12-01T09:00+00:00","chegada":"2026-12-01T10:45+00:00"}]}` |
| Consultar rascunhos | `Mostra as pré-visualizações` ou `Mostra a pré-visualização 1` |
| Registar um artigo no inventário | `Regista no inventário "Pilhas AA" em "Gaveta da cozinha" quantidade 8` |
| Consultar o inventário | `Consulta o inventário nome "pilhas"` ou `Consulta o inventário local "cozinha"` |
| Catalogar e consultar recibos | `Regista recibo "recibos/compra.pdf" de "Mercado" em 2026-11-15` e `Procura recibos de "Mercado"` |
| Registar uma despesa | `Regista despesa 12,45 euros em "Mercado" na categoria "Alimentação" em 2026-11-15` |
| Consultar despesas | `Mostra despesas de 2026-11-01 a 2026-11-15` com `na categoria "Alimentação"` opcional |
| Anular uma despesa | `Anula a despesa 1` |
| Consultar o checklist do projeto | `Mostra o progresso do projeto na fase 4` |
| Pesquisar código | `Procura código "schedule_programming"` |
| Listar contas autorizadas | `Mostra as contas de email` |
| Importar emails | `Importa emails da conta "trabalho" da pasta "INBOX" até 10` |
| Pesquisar email importado | `Procura emails da conta "trabalho" por assunto "orçamento"` |
| Responder a um email importado | `Prepara resposta à mensagem 1 da conta "trabalho" com "Confirmo a receção."` |
| Consultar o estado de envio | `Já enviaste o email da tarefa 1?` ou `Verifica o envio da tarefa 1` |
| Pesquisar email local | `Procura emails por contacto "mercado"` ou `Procura emails por assunto "orçamento"` ou `Procura emails por conteúdo "entrega"` |
| Ler uma conversa local | `Resume a conversa "emails/orcamento.eml"` |
| Rever perguntas e compromissos | `Mostra as perguntas da conversa "emails/orcamento.eml"` ou `Extrai tarefas da conversa "emails/orcamento.eml"` |
| Rever datas de uma conversa | `Extrai datas da conversa "emails/orcamento.eml"` |
| Preparar uma resposta | `Prepara resposta ao "emails/orcamento.eml" com "Confirmo a receção do orçamento."` |
| Guardar cartões de estudo | `Cria cartões de estudo sobre "Redes" com [{"pergunta":"O que significa DNS?","resposta":"Domain Name System","explicação":"Traduz nomes para dados como endereços IP."}]` |
| Explicar um tópico | `Explica "DNS" para nível iniciante` |
| Explicar um erro no código | `Explica o erro em "jarvis/app.py" na linha 50 com "NameError: variável indefinida"` |
| Avaliar respostas em linguagem livre | `Avalia o teste de estudo 1 com {"1":"O sistema que resolve nomes de domínio"}` |
| Gerar um documento a partir de materiais | `Prepara um documento "resumo.md" sobre "DNS" a partir de ["notas/redes.md","materiais/guia.pdf"]` |
| Importar definições de estudo | `Cria cartões de estudo sobre "Redes" de "notas/redes.md"` |
| Gerar e corrigir um teste | `Gera um teste de estudo sobre "Redes" com 3 perguntas` e `Corrige o teste de estudo 1 com {"1":"Domain Name System"}` |
| Registar dificuldade | `Regista dificuldade em "Redes" com "Sub-redes IPv4"` e `Mostra as dificuldades de estudo` |
| Planear o estudo | `Cria um plano de estudo até 2026-11-25 com 45 minutos por dia para ["Redes","Bases de dados"]` |
| Preparar notas de reunião | `Prepara notas para o evento 1 com ["reunioes/orcamento.pdf"]` |
| Guardar notas de reunião | `Guarda notas do evento 1 com "Assuntos levantados na reunião."` |
| Identificar decisões e tarefas | `Identifica decisões e tarefas do evento 1` ou `Identifica decisões e tarefas do evento 1 entre 00:05:00 e 00:10:00` |
| Analisar uma transcrição | `Analisa a transcrição "reunioes/orcamento.vtt" do evento 1` |
| Preparar seguimento e consultar materiais | `Prepara seguimento do evento 1` e `Mostra os materiais do evento 1` |
| Pesquisar na web e nas notícias | `Procura na web "transportes públicos em Lisboa"` ou `Procura notícias sobre "transportes públicos"` |
| Ler uma fonte na origem | `Lê a fonte "https://example.org" sobre "termo"` |
| Comparar fontes | `Compara fontes sobre "Qual é a diferença?" com ["https://example.org","https://example.net"]` |
| Consultar preço anunciado | `Consulta o preço em "https://example.org/produto"` |
| Consultar transportes GTFS | `Horários de "Origem" para "Destino" em 2026-11-16 a partir das 09:00 no GTFS "transportes.zip"` |
| Pesquisar email diretamente | `Pesquisa diretamente emails da conta "trabalho" na pasta "INBOX" por assunto "orçamento"` |
| Analisar uma conversa IMAP | `Resume a conversa online da mensagem 1 da conta "trabalho"` ou `Identifica perguntas pendentes da conversa online da mensagem 1 da conta "trabalho"` |
| Ler e abrir uma sala Matrix | `Mostra mensagens Matrix em "equipa"` e `Abre a sala Matrix "equipa"` |
| Rever uma mensagem Matrix | `Prepara mensagem Matrix para "equipa" com "Recebi os documentos."` |
| Correr testes ou um script em isolamento | `Corre testes Python de "tests"` ou `Executa "exemplo.py" em isolamento` |
| Rever eliminação permanente | `Prepara a eliminação permanente de "rascunho.txt"` |
| Preparar uma ação HTTPS | `Prepara ação "inscricao" da pré-visualização 1` |
| Navegar ou preencher pela interface Windows | `Executa navegação visual "historico"` ou `Preenche o formulário visual "inscricao" da pré-visualização 1` |
| Consultar o trânsito | `Trânsito de "Lisboa, PT" para "Cascais, PT"` ou `Trânsito de "38.72,-9.14" para "38.70,-9.42"` |
| Consultar a meteorologia | `Meteorologia em "Lisboa, PT" amanhã às 15:00` |
| Guardar uma pesquisa | `Guarda pesquisa "Como funciona o serviço?" com {"fontes":[{"título":"Documentação","url":"https://example.org","nota":"Condições consultadas"}],"conclusões":[{"tipo":"facto atribuído","texto":"A documentação descreve as condições.","fontes":[1]}]}` |
| Consultar uma pesquisa e uma fonte | `Mostra a pesquisa 1` e `Abre a fonte 1 da pesquisa 1` |
| Exportar um relatório de investigação | `Gera o relatório da pesquisa 1 para "relatorio.md"` |
| Preparar um PR | `Prepara um pull request para "origin/main" com {"título":"Melhorar o painel","testes":"Resultado verificado"}` |
| Consultar o Git | `Estado do Git`, `histórico do Git`, `ramo do Git`, `diff do Git` |
| Propor e aprovar uma alteração | `Propõe alteração em "jarvis/app.py" com {"antes":"trecho original","depois":"trecho revisto"}`, seguido de `Aplica a proposta 1` ou `Descarta a proposta 1` |

No painel **Tarefas em vários passos**, confirma os dois PDFs para iniciar a comparação. Podes corrigir os caminhos antes de comparar, cancelar a tarefa ou repetir um passo que falhou. O painel mantém os passos concluídos e o rascunho por perfil após reiniciar. O rascunho tem campos editáveis para destinatários, assunto e conteúdo. Usa **Guardar e rever** para confirmar os nomes e as versões dos anexos do projeto. O painel aceita até cinco ficheiros, com 10 MB no total. **Descarregar email (.eml)** exporta a versão guardada com os anexos. Se um anexo mudar, guarda e revê a nova versão. O TXT continua disponível para exportar só o texto.

Para importar email por IMAP, aponta `JARVIS_IMAP_ACCOUNTS_FILE` para um ficheiro JSON e guarda a credencial na variável indicada em `segredo_env`. Exemplo para o perfil `default` com o servidor e o utilizador de exemplo.

```json
{
  "perfis": {
    "default": [
      {
        "id": "trabalho",
        "host": "imap.example.org",
        "porta": 993,
        "utilizador": "utilizador@example.org",
        "autenticacao": "password",
        "segredo_env": "JARVIS_IMAP_TRABALHO",
        "pastas": ["INBOX", "Sent"],
        "enviados": "Sent",
        "smtp": {
          "host": "smtp.example.org",
          "porta": 587,
          "tls": "starttls",
          "remetente": "utilizador@example.org"
        }
      }
    ]
  }
}
```

O conector aceita autenticação por senha ou `xoauth2` com um token fornecido e renovado fora do JARVIS. Cada importação lê até 20 mensagens recentes da pasta autorizada e guarda cópias na base local do perfil. A leitura IMAP usa TLS com verificação do certificado e evita marcar mensagens como lidas. A pesquisa usa as cópias já importadas. Retirar uma conta ou pasta da configuração bloqueia o acesso pela aplicação e conserva as cópias na base local. A exportação de uma resposta gera um EML para revisão.

O bloco `smtp` é opcional. Define `tls` como `starttls` (porta 587 por omissão) ou `ssl` (465 por omissão). O envio usa o utilizador, a autenticação e a variável de credencial da conta IMAP, a menos que definas `utilizador`, `autenticacao` ou `segredo_env` no bloco SMTP. Se o utilizador SMTP for um endereço inteiro, `remetente` pode ser omitido. A pasta em `enviados` tem de ser o nome IMAP da pasta do fornecedor e também constar em `pastas`.

No cartão do rascunho, **Ditar resposta** usa o Whisper local, com o microfone selecionado no JARVIS. Ao parar, a transcrição é acrescentada ao corpo editável. Revê o corpo e o destinatário e guarda novamente antes de preparar o envio.

No cartão do rascunho, usa **Guardar e rever**, escolhe a conta e clica em **Preparar envio**. Depois de conferires os dados, usa **Confirmar e enviar** ou **Cancelar confirmação**. Uma confirmação vale para a revisão mostrada. Se a aceitação for parcial, o JARVIS mostra os destinatários recusados. Se o serviço não confirmar o resultado, o JARVIS guarda o Message-ID e pode procurá-lo em **Enviados**. Uma cópia ausente em Enviados mantém o estado por confirmar e bloqueia uma nova tentativa nesse rascunho.

A pesquisa direta consulta a pasta IMAP indicada, lê até 12 correspondências recentes e guarda cópias por perfil. O comando de conversa pesquisa na pasta da mensagem escolhida pelos cabeçalhos de referência. Podes usar **Extrai tarefas da conversa online** e **Extrai datas da conversa online** com a mesma identificação. Um campo opcional `webmail` no objeto da conta dá acesso à mensagem no fornecedor quando a sua URL aceita `{uid}`, `{pasta}` ou `{message_id}`. A URL deve ser HTTPS e usar o formato publicado pelo fornecedor. Configura também `rascunhos` com o nome IMAP de uma pasta em `pastas` para disponibilizar **Guardar rascunho no serviço**. Uma revisão gera no máximo uma cópia por conta de destino. Se a confirmação se perder, o mesmo botão procura o Message-ID na pasta.

Para analisar mensagens exportadas, coloca os ficheiros `.eml` na pasta `emails/` dentro do projeto. Os comandos consultam até 300 ficheiros ou 40 MB no total por pedido. Cada mensagem pode ter até 4 MB. A conversa é reconstruída pelos cabeçalhos que ligam as respostas. O leitor abre as mensagens em texto e não carrega imagens remotas. As perguntas e tarefas são excertos para revisão. Datas ambíguas ficam por confirmar.

Para importar cartões, usa uma lista com linhas como `- O que significa DNS? :: Domain Name System`. Pede **Mostra cartões de estudo** para rever as respostas e explicações. A correção compara o texto com a resposta de referência após normalizar acentos, maiúsculas e espaços. Cada teste conserva as respostas de referência da altura em que foi gerado.

As explicações, a avaliação em linguagem livre e os rascunhos a partir de materiais usam um modelo instalado no Ollama local. O JARVIS usa `JARVIS_MODEL` ou `qwen3:8b` e valida se o modelo aparece instalado e sem indicação de origem remota. A avaliação em linguagem livre é orientativa. A correção literal continua disponível. Os documentos permitem até quatro fontes PDF com texto, Markdown, TXT, VTT ou SRT. O modelo recebe os primeiros 3.400 caracteres de cada uma e o rascunho inclui os caminhos usados.

Em **Gravar reunião**, indica o número do evento, confirma que obtiveste consentimento e inicia a captura do microfone selecionado. A gravação dura até 30 minutos e o Whisper processa o áudio em blocos de cerca de 40 segundos. **Parar gravação** desliga o microfone e termina a transcrição dos blocos pendentes. O áudio é processado em memória e o JARVIS guarda o texto em VTT no projeto. Se o navegador fechar, podes recuperar os blocos que já chegaram ao servidor.

A identificação de decisões e tarefas usa o Ollama local e apresenta sugestões ligadas às marcas de tempo ou linhas originais. Para reuniões longas, podes analisar vários intervalos. O seguimento distingue as sugestões do modelo das marcações explícitas da transcrição.

Os materiais de reunião ficam associados a um evento da agenda local. A análise aceita VTT, SRT, TXT ou Markdown já guardados. Usa linhas iniciadas por **Decisão**, **Ação**, **Tarefa**, **Responsável** ou **Prazo**, separadas do texto por dois pontos, para as incluir no seguimento.

A pesquisa e as notícias usam [Brave Search](https://api-dashboard.search.brave.com/app/documentation/web-search). Define `JARVIS_BRAVE_SEARCH_KEY` no ambiente do servidor do JARVIS. Os resultados da Brave ficam na conversa aberta e a app não os guarda no histórico. Para guardar investigação, indica os teus próprios apontamentos e as ligações escolhidas nos sites de origem. Para cada conclusão, indica o tipo e os números das fontes. Os tipos disponíveis são **facto atribuído**, **inferência**, **concordância** e **divergência**. As comparações usam pelo menos duas fontes distintas.

O leitor de fontes consulta páginas públicas HTTPS em HTML ou texto simples. Segue até quatro redirecionamentos públicos e lê até 1,5 MB por página. A comparação usa o Ollama local e apresenta apenas itens cujas citações aparecem nos excertos que foram enviados ao modelo. Os preços apresentados vêm dos metadados de oferta da origem, com valor, moeda e hora da consulta.

O trânsito usa [TomTom Routing](https://docs.tomtom.com/routing-api/documentation/tomtom-maps/v1/calculate-route) com `JARVIS_TOMTOM_KEY` no ambiente do servidor. Para um ponto exato, indica latitude e longitude. Com nomes de localidades, o percurso usa os pontos devolvidos pela geocodificação do Open-Meteo. A consulta devolve uma estimativa para carro no momento do pedido.

Para horários de transporte, usa um [ZIP GTFS Schedule](https://gtfs.org/documentation/schedule/reference/) no projeto. A consulta lê viagens diretas com hora fixa, o fuso do operador, a sequência de paragens e o calendário, incluindo exceções. Se a paragem for ambígua, repete a consulta com `id:IDENTIFICADOR`. As viagens de frequência, os transbordos e os dados em tempo real ficam fora desta consulta.

A [previsão Open-Meteo](https://open-meteo.com/en/docs) é consultada para o fuso horário do local. O pedido pode ser para agora, para um dia até 15 dias à frente ou para uma hora certa desse dia. Se houver localidades com nomes semelhantes, escolhe um dos pedidos com número de local mostrados no chat.

Em **Estado das integrações**, o botão **Verificar ligações** consulta Ollama, Hermes Agent e Open-Meteo. A pesquisa Brave permite verificar o acesso com a chave configurada.

O rascunho de pull request usa os commits do ramo atual relativamente à base local indicada. Os resultados de testes são os que forneces ao comando. O rascunho fica na conversa, pronto a rever.

A despensa usa `g`, `ml` e `un` e é independente do inventário doméstico. Registar novamente o mesmo ingrediente e unidade substitui a quantidade. Usa zero para remover o stock. O plano cobre uma refeição por dia, até sete dias, e regista as compras da versão que viste no chat. As quantidades do plano são calculadas sem alterar o stock. A lista de compras só muda quando pedes para adicionar os ingredientes do plano.

Carrinhos, reservas, itinerários e formulários são rascunhos locais construídos com os dados indicados. Usa «Marca a pré-visualização 1 como revista» para registar a revisão ou «Descarta a pré-visualização 1» para a retirar da lista. A revisão fica registada localmente. Os preços e horários dependem dos valores fornecidos.

Inventário, recibos e despesas ficam guardados por perfil. Registar de novo um artigo no mesmo local atualiza a quantidade. Os recibos continuam na pasta original. A consulta de despesas sem datas usa o mês corrente até hoje.

O aviso acompanha o nome final de um ficheiro na pasta Downloads (ou na pasta definida em `JARVIS_DOWNLOADS_DIR`). O pedido sem nome é suficiente quando existe um único download com nome provisório reconhecível. Para nomes como `Unconfirmed 123.crdownload`, indica o nome final. O JARVIS assinala a conclusão quando o ficheiro final está estável e deixa de existir um marcador temporário conhecido para esse nome. O painel conserva o estado e os avisos concluídos após reiniciar.

O resumo de progresso lê `checklist.md` ou `README.md` no projeto autorizado e mostra as linhas de origem. Os próximos prazos são detetados em tarefas em aberto que incluam `prazo AAAA-MM-DD`.

A comparação apresenta excertos das secções alteradas e aponta para as páginas dos PDFs. A extração de tabelas usa a grelha detetada na página e confirma a estrutura do CSV por releitura. Confere a grelha extraída com o PDF, sobretudo se a estrutura visual for complexa. Para PDFs digitalizados, prepara primeiro uma versão com texto selecionável. As fórmulas são guardadas e relidas no XLSX. Abre-o numa aplicação de folha de cálculo para calcular os resultados.

### Integrações adicionais da Fase 4

**Matrix.** Define `JARVIS_MATRIX_ROOMS_FILE` com as salas autorizadas por perfil. Cada sala precisa de um `id`, do `servidor` HTTPS, do identificador `sala` e do nome da variável `token_env`. `enviar` dá autorização para enviar texto depois de uma revisão explícita. O token fica na variável indicada, nunca no JSON. O envio suporta salas sem cifragem. Ao repetir uma confirmação incerta, o JARVIS reutiliza a mesma transação. [API Matrix](https://spec.matrix.org/latest/client-server-api/)

```json
{"perfis":{"default":[{"id":"equipa","servidor":"https://matrix.example.org","sala":"!exemplo:example.org","token_env":"JARVIS_MATRIX_EQUIPA","enviar":false}]}}
```

**Ações externas.** Define `JARVIS_EXTERNAL_ACTIONS_FILE` para mapear os campos de um carrinho, uma reserva ou um formulário para uma API compatível. O fornecedor tem de aceitar `PUT` idempotente por identificador, respeitar a chave `Idempotency-Key` e devolver por `GET` o estado final e os mesmos campos guardados. Para compras, a API tem de rejeitar valores diferentes do total e moeda revistos. Usa `opção N` ao preparar uma reserva com várias opções. Os campos de carrinho incluem `items`, `shipping`, `total_centimos` e `moeda`. Os campos de uma reserva podem usar `opção.name`, `opção.start`, `opção.end`, `opção.total` e `moeda`. Em formulários, usa `campos.Nome do campo`.

```json
{"perfis":{"default":[{"id":"inscricao","tipo":"formulário","url":"https://api.example.org/inscricoes/{id}","contrato":"put-idempotente","token_env":"JARVIS_ACTION_TOKEN_INSCRICAO","campo_estado":"estado","estado_confirmado":"confirmada","campos":{"nome":"campos.Nome","sessao":"campos.Sessão"}}]}}
```

**Windows UI Automation.** Define `JARVIS_WINDOWS_ACTIONS_FILE` para indicar o processo, a janela e os controlos autorizados. Usa apenas controlos de navegação ou de edição. Cada passo de navegação espera um identificador de destino visível. O preenchimento rejeita campos de senha e relê os valores para revisão. O nome do processo não inclui `.exe`. O título deve corresponder à janela e os identificadores são os `AutomationId` expostos pela aplicação.

```json
{"perfis":{"default":{"historico":{"tipo":"navegação","processo":"AppExemplo","janela":"Exemplo","passos":[{"invocar":"abrirHistorico","esperar":"listaHistorico"}]},"inscricao":{"tipo":"formulário","processo":"AppExemplo","janela":"Exemplo","campos":{"Nome":"nome","Sessão":"sessao"}}}}}
```

**Python isolado.** O JARVIS usa um Docker Linux local com a imagem `JARVIS_DOCKER_PYTHON_IMAGE` já instalada, por omissão `python:3.12-slim`. A execução recebe uma cópia dos ficheiros versionados, excluindo diretórios locais de dados e formatos habituais de credenciais. O contentor tem rede desativada, origem de código só de leitura, limites de CPU, memória e processos, e um máximo de 90 segundos. [Isolamento no Docker](https://docs.docker.com/engine/containers/run/)

**Eliminação permanente.** Pedir a eliminação mostra primeiro o caminho, o tamanho e o SHA-256 de um único ficheiro autorizado. A revisão dá um número e um código. Se o ficheiro mudar, cria uma revisão nova. Consulta o estado com «Mostra a eliminação 1».

**MCP.** Acrescenta `--extensions caminho/extensoes.sqlite3` aos argumentos do servidor MCP existente. Usa `python jarvis_files_mcp.py RAIZ --extensions caminho/extensoes.sqlite3 --install-extension metadados` ou `--disable-extension metadados`. Acrescenta `consultar_metadados` à lista da conta em `--policy` para a publicar. O servidor relê a política e o registo a cada pedido.

## Verificar a base local

Com o Ollama aberto, corre `python -m scripts.check_local --ollama-only`. O diagnóstico confirma que o Ollama está a responder e que o modelo instalado anuncia suporte a ferramentas. O modelo predefinido é `qwen3:8b`. Para verificar outro modelo instalado, passa `--model nome:versão`. O Hermes 3 é uma opção de modelo a avaliar.

Para testar também o Hermes Agent, configura-o para usar o mesmo modelo no Ollama em `http://127.0.0.1:11434/v1`. Ativa a API do Hermes em `127.0.0.1:8642`, define a chave `API_SERVER_KEY` na configuração do Hermes e arranca com `hermes gateway`. Na sessão do PowerShell onde vais correr o diagnóstico, define `JARVIS_HERMES_API_KEY` com a mesma chave e corre `python -m scripts.check_local`.

O teste envia uma pergunta curta em português e verifica a hora na resposta. Depois de configurar a ferramenta de leitura, corre `python -m scripts.check_local --check-files` para confirmar que o Hermes emite um evento de conclusão para a listagem. O diagnóstico também pode ler a chave do ficheiro local do Hermes. A opção `--model` só verifica o modelo no Ollama. A escolha do modelo usado pelo agente é feita na configuração do Hermes. A execução efetiva de ferramentas ainda faz parte da base técnica em desenvolvimento.

[Configuração do Ollama no Hermes Agent](https://hermes-agent.nousresearch.com/docs/guides/local-ollama-setup) · [API local do Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server)

### Testar a ferramenta de leitura

Para disponibilizar apenas a ferramenta de listagem à API local do Hermes, acrescenta ao `config.yaml` do Hermes as entradas abaixo. Se as secções já existirem, acrescenta as chaves às secções correspondentes. Usa o caminho absoluto do Python, do script e da pasta autorizada. No Windows, podes usar barras normais nos caminhos.

```yaml
mcp_servers:
  jarvis_files:
    command: C:/caminho/python.exe
    args:
      - C:/caminho/Jarvis_Portatil/jarvis/integrations/files_mcp.py
      - C:/caminho/Jarvis_Portatil/holo/sample-notes
platform_toolsets:
  api_server: [jarvis_files]
```

Reinicia o gateway e pede «Que ficheiros tenho na pasta autorizada?». A ferramenta devolve os nomes dos ficheiros na pasta indicada. Testa a recusa com «Usa listar_ficheiros com pasta ..». A ferramenta verifica o caminho resolvido e recusa pastas fora da raiz configurada.

Para verificar a Fase 1 de ponta a ponta, configura também os argumentos `--policy caminho/permissoes.json` e `--audit caminho/auditoria.jsonl` no servidor MCP. O JSON de permissões mapeia o nome da conta local que executa o gateway para as ferramentas autorizadas, por exemplo `{"conta-windows":["listar_ficheiros"]}`. A política é relida a cada chamada. A API do Hermes serve uma única conta local nesta fase. Usa as notas de exemplo como raiz e um ficheiro de auditoria fora da raiz.

Corre `python -m scripts.verify_phase1 --policy caminho/permissoes.json --audit caminho/auditoria.jsonl` sem outros pedidos em curso. O teste retira temporariamente a permissão, verifica a recusa e repõe a política no final. Para o teste de serviço parado, usa a opção `--offline` com o Ollama desligado e volta a abri-lo depois.


## Projetos de referência

- [Jarvis](https://github.com/isair/jarvis) para voz, chat e memória local com Ollama.
- [H.O.L.O Hands](https://github.com/zubair-trabzada/holo-gestures) para interagir com cartões e objetos 3D por gestos.

## Primeiro protótipo

Agarra um cartão de exemplo no H.O.L.O Hands e comprime-o com as duas mãos para pedir um resumo curto em português. O resumo aparece no painel. A pinça rápida abre a nota. O gesto de comprimir já pede um resumo no H.O.L.O e será reutilizado.

## Testar o protótipo no Windows

Com o Python instalado e o Ollama aberto, faz duplo clique em **Iniciar Jarvis.cmd**. O painel abre no navegador predefinido. Mantém a janela do Jarvis aberta enquanto usas o painel e prime **Ctrl+C** nessa janela para terminar.

Se for a primeira vez numa cópia do repositório, prepara o H.O.L.O e o modelo com estes comandos na pasta do projeto:

```powershell
git submodule update --init
ollama pull qwen3:8b
```

Para arrancar pelo terminal, usa `python -m jarvis.holo` e abre [o painel local](http://localhost:4890). Abre uma pasta e uma nota com o rato e carrega em **Resumir com Qwen**. Com a webcam, agarra um cartão e comprime-o com as duas mãos para pedir o mesmo resumo.

O servidor usa o Ollama na própria máquina. Para usar outro modelo instalado, define `$env:JARVIS_MODEL` antes de arrancar. Quando o resumo aparecer no painel, carrega em **Ouvir resumo**. A reprodução usa uma voz local em português do navegador, com preferência por português de Portugal. Se o botão indicar que falta uma voz, adiciona uma voz portuguesa nas definições de Voz do Windows e volta a abrir o navegador. A ligação ao Jarvis de desktop faz parte da etapa seguinte.

Para perguntar sobre um cartão, abre a nota, escreve no campo **Pergunta sobre esta nota** e carrega em **Perguntar**. O Qwen usa o conteúdo desse cartão para responder no leitor. Carrega em **Ouvir resposta** para ler o resultado com a mesma voz local usada nos resumos.

Para usar o microfone, carrega em **Ditar pergunta**, permite o acesso ao microfone e revê a transcrição antes de enviar. É preciso um navegador com reconhecimento no dispositivo e um pacote de português compatível. O primeiro uso pode descarregar esse pacote. Se o ditado local estiver indisponível, escreve a pergunta.

## Roadmap

| Etapa | Resultado esperado |
| --- | --- |
| 1. Validar a base | H.O.L.O com webcam, Jarvis com microfone e Ollama a responder no Windows. |
| 2. Ligar o gesto ao modelo | Uma nota de exemplo gera um resumo em português que aparece no painel. |
| 3. Integrar a voz | O resumo é lido em voz alta e o mesmo cartão pode dar contexto a uma pergunta por voz. |
| 4. Preparar a instalação | Uma pessoa consegue montar e testar o protótipo com as instruções do repositório. |

O progresso do protótipo está no [checklist de implementação](checklist.md#protótipo-holo-hands) e no [checklist de testes](docs/CHECKLIST_TESTES.md#protótipo-holo-hands).
