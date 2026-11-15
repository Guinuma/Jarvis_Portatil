# JARVIS Portátil — Checklist de implementação

Marca com **[x]** as funcionalidades implementadas. Deixa por marcar as que continuam parciais ou pendentes e indica o que já existe. Os ensaios, os resultados anteriores e os cenários de aceitação estão no [checklist de testes](docs/CHECKLIST_TESTES.md).

## Fase 1 — Base técnica

### Funcionamento local e desempenho

- [x] Instalar o Ollama no portátil.
- [x] Configurar o Hermes Agent para usar o Ollama como fornecedor local.
- [x] Configurar o modelo inicial `qwen3:8b`.
- [x] Escolher e configurar um modelo com suporte a chamadas de ferramentas. Modelo escolhido: `qwen3:8b`.

### Extensões e manutenção

- [x] Criar um registo de ferramentas com nome, finalidade, argumentos e permissões visíveis para cada ferramenta. A listagem publica o esquema e a indicação de leitura através de MCP.
- [x] Ligar a ferramenta de listagem ao Hermes por MCP.
- [x] Adicionar um diagnóstico que identifique falhas de ligação ao Ollama e ao Hermes Agent, um modelo em falta e uma ferramenta de listagem indisponível ou não executada.

### Permissões e privacidade

- [x] Aplicar permissões por ferramenta e utilizador antes de executar uma chamada.
- [x] Restringir ferramentas de ficheiros às pastas autorizadas.
- [x] Guardar credenciais fora das conversas.
- [x] Registar o que o JARVIS executou, porquê e com que resultado, incluindo pedidos recusados e falhas.
- [x] Tratar instruções encontradas em sites, emails e PDFs como conteúdo externo.

## Fase 2 — MVP

O ditado inclui uma alternativa local Whisper para navegadores sem reconhecimento local nativo.

### Voz

- [x] Implementar Alt+Shift+D para iniciar e parar o ditado com o JARVIS em foco.
- [x] Implementar o botão **Ditar** para iniciar e parar a transcrição local em PT-PT e rever o texto antes de enviar.
- [x] Disponibilizar **Ouvir resposta**, dar preferência a uma voz local PT-PT e expor **Parar leitura** durante a reprodução.
- [x] Executar comandos por voz através de uma transcrição editável e envio explícito para o mesmo fluxo de comandos do chat.
- [x] Enfileirar frases para leitura automática à medida que o Hermes envia a resposta.
- [x] Cancelar a fila de leitura e bloquear a leitura das frases seguintes da resposta em curso.
- [x] Reconhecer «cancela» durante um pedido e fechar a ligação ao Hermes.
- [x] Corrigir o último lembrete pendente com «afinal, daqui a 30 minutos» sem reiniciar a conversa.
- [x] Permitir alterar a voz local de leitura.
- [x] Permitir alterar a velocidade da leitura.
- [x] Permitir selecionar um microfone e passar a faixa selecionada ao reconhecimento local.
- [x] Abrir as definições de som do Windows a partir do JARVIS para escolher a saída de áudio.
- [x] Desativar **Ler respostas automaticamente** e receber a resposta por texto.

### Conversa

- [x] Manter o contexto entre perguntas sucessivas na mesma sessão.
- [x] Resolver referências como «esse ficheiro» e «a reunião de amanhã» quando o contexto identifica uma única opção. Depende da pesquisa de ficheiros ou da consulta da agenda.
- [x] Pedir esclarecimento quando duas opções correspondem ao pedido e aguardar a seleção antes de agir.
- [x] Alternar o idioma da resposta durante uma conversa quando o utilizador pedir.
- [x] Ajustar o nível de detalhe quando o utilizador pedir uma resposta mais curta ou mais completa.

### Windows e aplicações

- [x] Abrir aplicações Windows suportadas pelo nome.
- [x] Enviar um ficheiro de texto pelo caminho selecionado ao VS Code.
- [x] Encaminhar um endereço HTTP ou HTTPS para o navegador predefinido.
- [x] Alterar o volume do Windows e apresentar o nível resultante.
- [x] Mudar o dispositivo de áudio predefinido do Windows.

### Programação

- [x] Abrir o projeto certo a partir de um nome reconhecido. Pedir a pasta ou a seleção quando houver vários projetos com o mesmo nome.
- [x] Abrir o JARVIS Portátil no VS Code com «Jarvis, abre o meu projeto no VS Code» e informar quando o editor está indisponível.
- [x] Resolver outros projetos autorizados por nome ou seleção e encaminhar a pasta para o VS Code.

### Pesquisa pessoal

- [x] Encontrar ficheiros pelo nome no projeto JARVIS e apresentar pedidos para os abrir.
- [x] Encontrar ficheiros de texto pelo conteúdo no projeto JARVIS.
- [x] Estender a pesquisa por nome e conteúdo aos restantes projetos autorizados.
- [x] Encontrar as notas da última sessão de um projeto autorizado em `notes/AAAA-MM-DD/`, mostrando os ficheiros e a origem da data.

### Ficheiros e documentos

- [x] Criar um ficheiro no projeto JARVIS sem sobrescrever e devolver a sua localização.
- [x] Guardar o texto de uma nota enviada pelo chat.

### Agenda e tarefas

- [x] Consultar os compromissos do dia na agenda local do perfil.
- [x] Consultar os compromissos do dia em calendários Google autorizados para o perfil, com ligações aos eventos disponíveis.
- [x] Consultar a disponibilidade num intervalo e apresentar os períodos livres.
- [x] Criar temporizadores com aviso ao terminar.
- [x] Criar um lembrete relativo no chat, mostrar a hora calculada e emitir um aviso com a página aberta.
- [x] Calcular a próxima ocorrência de uma hora absoluta para agendar um aviso.
- [x] Editar o último lembrete pendente e substituir o aviso anterior.
- [x] Cancelar o último lembrete pendente.

### Painel e acessibilidade

- [x] Apresentar um chat com entrada por texto e respostas legíveis.
- [x] Abrir o Jarvis normal no navegador com o atalho do Windows.
- [x] Apresentar o início e a conclusão de uma chamada real de ferramenta no painel de atividade do Hermes.
- [x] Abrir o painel H.O.L.O Hands a partir do Jarvis normal quando o submódulo está instalado.
- [x] Mostrar os estados do microfone no painel.
- [x] Mostrar a transcrição parcial durante a escuta com reconhecimento nativo compatível. Na alternativa Whisper, a transcrição aparece depois de parar.
- [x] Mostrar legendas ao início de cada trecho lido e ocultá-las no fim.
- [x] Mostrar **Cancelar pedido** durante a execução e fechar o fluxo de resposta ao cancelar.
- [x] Permitir usar o chat, a escuta e o botão **Parar** por teclado.

### Funcionamento local e desempenho

- [x] Mostrar erros de integrações externas no comando afetado e manter os comandos locais disponíveis.

## Fase 3 — Memória e rotinas

### Conversa

- [x] Guardar o histórico de uma sessão e reabrir a conversa com o contexto anterior após fechar o JARVIS.

### Memória

- [x] Guardar preferências e aplicá-las em conversas posteriores.
- [x] Guardar um contacto e recuperá-lo pelo nome.
- [x] Guardar um projeto e recuperar a pasta associada.
- [x] Guardar um nome de dispositivo e resolvê-lo num pedido posterior.
- [x] Guardar uma rotina com o nome escolhido e recuperá-la por esse nome.
- [x] Interpretar «lembra-te disto», guardar a informação indicada e mostrá-la no editor.
- [x] Interpretar «esquece isto» e remover a memória selecionada.
- [x] Pesquisar conversas anteriores e abrir a conversa onde aparece o resultado.
- [x] Identificar nas respostas se uma afirmação veio de uma memória guardada ou de uma dedução.
- [x] Mostrar a data e a origem de cada memória.
- [x] Editar uma memória e usar o valor atualizado nas consultas.
- [x] Apagar uma memória pelo editor e removê-la da pesquisa e das respostas.
- [x] Exportar as memórias num ficheiro legível, com a data e a origem dos registos.
- [x] Isolar as memórias e o histórico por perfil. Os perfis pertencem à mesma conta Windows.

### Pesquisa pessoal

- [x] Pesquisar texto em PDFs nas pastas autorizadas.
- [x] Pesquisar transcrições guardadas nas pastas autorizadas.
- [x] Indexar por OCR o texto de documentos digitalizados a pedido e pesquisar o texto extraído.
- [x] Resumir um documento encontrado e apresentar a ligação para o original.
- [x] Responder a perguntas com ligações para as fontes e páginas quando aplicável.
- [x] Atualizar o índice quando um ficheiro é criado, alterado, movido ou apagado.

### Windows e aplicações

- [x] Gerir janelas, incluindo mover, minimizar, maximizar e restaurar uma janela identificada.
- [x] Mover uma janela para o monitor indicado.
- [x] Ativar e consultar o modo de foco do Windows.
- [x] Consultar a bateria e apresentar a percentagem e o estado de carregamento.
- [x] Consultar o armazenamento e apresentar o espaço disponível na unidade pedida.
- [x] Fazer uma captura de ecrã e devolver o ficheiro criado.
- [x] Ler a seleção ativa a pedido e apresentar o texto selecionado.
- [x] Ler a área de transferência a pedido e exigir autorização antes da consulta.
- [x] Criar espaços de trabalho como «modo estudo» e «modo programação» com as aplicações, pastas e janelas correspondentes.

### Ficheiros e documentos

- [x] Renomear um ficheiro.
- [x] Mover um ficheiro e impedir sobrescrita.
- [x] Pré-visualizar uma reorganização de Downloads e aplicar apenas os movimentos aprovados.
- [x] Identificar duplicados por SHA-256 e apresentar os caminhos.
- [x] Comprimir os ficheiros selecionados.
- [x] Extrair um arquivo para a pasta escolhida.
- [x] Converter um ficheiro para o formato pedido.
- [x] Preparar cópias de segurança de ficheiros selecionados e permitir restaurá-los.

### Agenda e tarefas

- [x] Criar eventos com título, data e hora no calendário indicado.
- [x] Reagendar um evento.
- [x] Detetar conflitos antes de criar ou reagendar um evento e mostrar os compromissos que se sobrepõem.
- [x] Preparar a agenda do dia por ordem cronológica.
- [x] Criar tarefas recorrentes e calcular a próxima ocorrência após concluir a atual.
- [x] Criar lembretes associados a eventos e atualizá-los quando o evento é reagendado.
- [x] Reservar blocos de foco na agenda.
- [x] Configurar a antecedência de um aviso de compromisso.

### Vida prática

- [x] Adicionar, remover e marcar como comprados itens numa lista de compras e recuperar a lista na sessão seguinte.

### Rotinas e fluxos

- [x] Criar regras do tipo «quando acontecer X, faz Y».
- [x] Agendar o modo programação.
- [x] Adicionar condições às rotinas.
- [x] Pré-visualizar as etapas, os destinos e os efeitos previstos de uma rotina.
- [x] Executar uma rotina manualmente a partir do painel, independentemente do horário.
- [x] Mostrar o histórico da rotina com a hora, os passos executados e o resultado.
- [x] Configurar «bom dia» para preparar a agenda e mostrar as tarefas do dia.
- [x] Configurar «modo programação» para ativar o espaço de trabalho escolhido e abrir as notas do projeto.
- [x] Configurar «fecha o dia» para rever o que ficou pendente e guardar uma nota de fecho.
- [x] Interpretar «faz como da última vez» e recuperar a rotina correspondente. Pedir esclarecimento se houver duas rotinas plausíveis.

### Painel e acessibilidade

- [x] Mostrar o histórico de conversas e permitir reabrir uma sessão.
- [x] Disponibilizar um editor para consultar, editar, apagar e exportar memórias. Depende das operações de memória.
- [x] Disponibilizar um editor para configurar, pré-visualizar e executar rotinas. Depende do motor de rotinas.

### Funcionamento local e desempenho

- [x] Consultar, editar e recuperar a memória local após reiniciar sem acesso externo.

### Extensões e manutenção

- [x] Criar cópias de segurança das definições, memórias e rotinas.
- [x] Restaurar uma cópia de segurança das definições, memórias e rotinas.

## Fase 4 — Tarefas em vários passos

Consulta os [comandos e dependências da Fase 4](README.md#comandos-da-fase-4).

### Conversa

- [x] Mostrar os passos planeados, em execução e concluídos de uma tarefa longa. **Implementado no painel do fluxo PDF → rascunho.**
- [x] Permitir que o utilizador intervenha numa tarefa longa para corrigir um ficheiro, destino ou outro parâmetro antes do passo que o utiliza. **Implementado para a escolha dos PDFs antes da comparação e a correção após falha.**

### Automatização de aplicações

- [x] Abrir uma sala Matrix autorizada no navegador e navegar para os recursos de um fluxo Windows configurado.
- [x] Preencher campos de texto autorizados num formulário Windows via UI Automation e reler os valores para revisão.
- [x] Transferir uma resposta revista de uma mensagem IMAP para a pasta de rascunhos de uma conta autorizada e mapear campos de rascunhos para APIs configuradas.
- [x] Gerar um ficheiro como resultado de uma sequência, incluindo o EML do fluxo PDF → rascunho com os anexos revistos.
- [x] Executar sequências pela API local e aplicar ações HTTPS confirmadas, verificando o estado e os campos no destino.
- [x] Automatizar navegação numa aplicação Windows através de controlos de acessibilidade configurados e verificar o resultado após cada passo.
- [x] Interromper a sequência se um resultado esperado não for confirmado e mostrar o passo que falhou. **Implementado no fluxo PDF → rascunho.**

### Ficheiros e documentos

- [x] Criar documentos DOCX e reler o conteúdo antes de guardar a versão final.
- [x] Editar parágrafos em documentos DOCX existentes e reler as alterações.
- [x] Criar folhas XLSX e reler os valores e fórmulas gravados.
- [x] Editar células e fórmulas em folhas XLSX existentes e reler as células gravadas. O recálculo depende de uma aplicação de folha de cálculo.
- [x] Criar apresentações PPTX com diapositivos de título e texto.
- [x] Editar títulos e campos de texto de conteúdo em apresentações PPTX existentes. A edição de conteúdo suporta diapositivos com um único campo de texto.
- [x] Comparar duas versões de um documento e indicar as diferenças e a respetiva localização. **Implementado para texto de PDF, DOCX, TXT e Markdown.**
- [x] Extrair tabelas de PDFs com texto e guardar em CSV.

### Pesquisa pessoal

- [x] Pesquisar emails EML na pasta local do projeto por contacto, assunto ou conteúdo e abrir a mensagem original em texto.
- [x] Pesquisar mensagens importadas de contas IMAP autorizadas por contacto, assunto ou conteúdo e abrir a cópia local.
- [x] Pesquisar diretamente numa pasta IMAP autorizada e ligar ao correio online quando houver um modelo de URL do fornecedor configurado.
- [x] Localizar as versões pedidas de um documento, compará-las e apresentar as diferenças com referências às duas origens. Depende da pesquisa e da comparação de documentos. **Implementado no fluxo PDF → rascunho com pesquisa por nome e seleção explícita.**

### Email e mensagens

- [x] Configurar contas e pastas IMAP por perfil e importar mensagens recentes em modo de leitura por TLS.
- [x] Ler e enviar mensagens de texto em salas Matrix não cifradas autorizadas no perfil.
- [x] Reconstruir conversas EML locais por referências entre mensagens, mostrar um resumo por excertos e indicar as fontes.
- [x] Destacar perguntas e pedidos candidatos a seguimento nos EML locais com referências às mensagens. As perguntas assinaladas ficam para revisão.
- [x] Extrair datas numéricas e expressões temporais de EML locais e pedir confirmação das datas ambíguas.
- [x] Pesquisar conversas diretamente numa pasta IMAP e mostrar resumos, tarefas e datas com referências.
- [x] Usar o Ollama local para identificar perguntas possivelmente pendentes pelo contexto da conversa e mostrar o excerto correspondente.
- [x] Gerar, editar e guardar um rascunho local de email a partir da comparação de PDFs e permitir descarregá-lo em TXT.
- [x] Preparar e rever uma resposta a um EML local com destinatário e assunto preenchidos e preservar as referências da conversa na exportação.
- [x] Preparar uma resposta a uma mensagem recebida por IMAP e revê-la no painel de rascunhos, com opção de exportar em EML.
- [x] Guardar uma cópia de um rascunho revisto numa pasta IMAP autorizada e guardar a referência no painel.
- [x] Selecionar ficheiros do projeto como anexos de um rascunho local, rever nomes e versões e exportar o email em EML. O JARVIS pede nova revisão se um ficheiro mudar.
- [x] Associar aos envios SMTP os anexos revistos e bloquear o envio quando a versão de um ficheiro mudou.
- [x] Mostrar e permitir editar o destinatário, o assunto e o conteúdo no rascunho local.
- [x] Mostrar remetente, destinatários, assunto, conteúdo e anexos da versão que será enviada antes de pedir confirmação.
- [x] Enviar a versão confirmada por SMTP com TLS e guardar a referência e o resultado da tentativa.
- [x] Ditar o corpo de uma resposta de email com a transcrição local Whisper, rever e editar o texto e o destinatário, e confirmar o envio num passo separado.
- [x] Responder a «já enviaste o email?» com o estado da tentativa e consultar a pasta Enviados por Message-ID quando o resultado estiver por confirmar.
- [x] Cancelar a confirmação de envio e manter o rascunho local para edição.

### Reuniões

- [x] Preparar notas para um evento da agenda local e ligar os documentos selecionados do projeto.
- [x] Gravar a reunião pelo microfone após confirmação de consentimento, parar a captura no painel e guardar a transcrição VTT por evento.
- [x] Agrupar decisões, tarefas, responsáveis e prazos explicitamente marcados em transcrições locais.
- [x] Inferir decisões e tarefas em transcrições sem marcações explícitas usando o Ollama local, indicar os excertos de origem e incluir responsáveis e prazos presentes nesses excertos.
- [x] Apresentar um resumo por excertos com marcas temporais de VTT e SRT ou referências a linhas de texto.
- [x] Preparar uma mensagem de seguimento a partir das decisões e tarefas assinaladas ou de sugestões do modelo local, que ficam identificadas para revisão.
- [x] Associar as notas, a transcrição e o seguimento ao evento da agenda local e recuperá-los mais tarde.

### Internet e investigação

- [x] Pesquisar na web com Brave Search e apresentar resultados com excertos e ligações.
- [x] Abrir fontes selecionadas no navegador a partir da pesquisa ou de um relatório guardado.
- [x] Consultar o texto de páginas HTTPS públicas selecionadas e mostrar os excertos e a ligação à origem.
- [x] Registar concordâncias e divergências fornecidas pelo utilizador, associadas a duas ou mais fontes.
- [x] Comparar automaticamente até quatro páginas pelo Ollama local e apresentar concordâncias e divergências com citações de fontes diferentes.
- [x] Distinguir factos atribuídos e inferências nos relatórios de investigação a partir dos tipos indicados pelo utilizador.
- [x] Separar automaticamente afirmações atribuídas e inferências do modelo na comparação e mostrar apenas itens com citações presentes nos excertos consultados.
- [x] Consultar meteorologia pelo Open-Meteo para um local, dia e hora suportados e mostrar as ligações à previsão e à geocodificação.
- [x] Consultar uma rota de carro com dados de trânsito da TomTom e indicar duração estimada, atraso fornecido e hora da consulta.
- [x] Consultar viagens diretas com hora fixa em GTFS para a data e o percurso pedidos, incluindo exceções do calendário.
- [x] Consultar preços anunciados em páginas de produto que disponibilizem valor e moeda em dados estruturados e mostrar a origem e a hora da consulta.
- [x] Consultar notícias sobre um tema e apresentar a data indicada pelo serviço e a fonte de cada resultado.
- [x] Guardar perguntas de investigação com fontes escolhidas, observações e conclusões por perfil.
- [x] Preparar um relatório de investigação no chat ou em Markdown com ligações para as fontes usadas em cada conclusão.

### Programação

- [x] Pesquisar código no projeto autorizado e devolver os ficheiros e linhas relevantes. **Implementado com pesquisa literal e resultados por ficheiro e linha.**
- [x] Explicar um erro pelo Ollama local usando a mensagem, a linha indicada e o excerto de código autorizado.
- [x] Preparar uma proposta de alteração para os ficheiros autorizados e mostrar as diferenças para revisão. **Implementado para uma substituição textual localizada num ficheiro.**
- [x] Aplicar a proposta após aprovação e mostrar os ficheiros alterados. Se um ficheiro tiver mudado desde a revisão, pedir nova revisão antes de aplicar. **Implementado com aprovação por número e verificação da versão do ficheiro.**
- [x] Executar testes Python unittest do projeto autorizado num contentor local e mostrar a saída e o código de saída.
- [x] Consultar o estado, o histórico ou o ramo do Git conforme o pedido. **Implementado.**
- [x] Resumir alterações Git preparadas e por preparar, com ficheiros, estatísticas e excertos das linhas alteradas.
- [x] Preparar um rascunho local de pull request com título, commits, ficheiros afetados e resultados de testes fornecidos pelo utilizador.
- [x] Executar Python numa cópia só de leitura dos ficheiros versionados, com rede desativada e limites confirmados antes de arrancar.

### Estudo e trabalho

- [x] Explicar um tópico com exemplos de acordo com o nível iniciante, intermédio ou avançado, pelo Ollama local.
- [x] Criar e rever cartões de estudo a partir de perguntas e respostas fornecidas ou de definições em Markdown e TXT.
- [x] Gerar um teste de estudo a partir dos cartões de um tópico e guardar as perguntas por perfil.
- [x] Corrigir respostas do teste por comparação com a referência e mostrar a explicação guardada com o cartão, quando disponível.
- [x] Avaliar a equivalência de respostas em linguagem livre pelo Ollama local e apresentar uma explicação orientativa junto da referência.
- [x] Registar dificuldades de estudo por tópico e recuperá-las em sessões posteriores.
- [x] Gerar um plano de estudo até à data de avaliação com os tópicos e minutos disponíveis por dia, começando pelas dificuldades registadas.
- [x] Preparar um rascunho em Markdown com o Ollama local a partir de até quatro materiais autorizados e identificar as fontes de cada secção.
- [x] Acompanhar o progresso de um projeto e mostrar tarefas concluídas, pendentes e próximos prazos. **Implementado a partir do checklist Markdown de um projeto autorizado. Os prazos vêm das datas explícitas nas tarefas.**

### Vida prática

- [x] Sugerir receitas da coleção local por número de porções e distinguir as quantidades disponíveis na despensa das que faltam.
- [x] Planear uma refeição por dia durante o período pedido, descontar o stock entre dias e preparar a lista de compras.
- [x] Preparar um itinerário local com as datas, locais e opções de transporte fornecidos, incluindo os fusos horários e a duração de cada percurso.
- [x] Registar itens e quantidades no inventário doméstico por perfil e recuperá-los por nome ou localização.
- [x] Catalogar recibos PDF do projeto por data e comerciante e abrir os originais a partir da pesquisa.
- [x] Registar despesas em euros, anulá-las por número e apresentar totais por período e categoria.
- [x] Preparar um carrinho local para revisão com vendedor, artigos, quantidades, preços, portes e total quando conhecido.
- [x] Preparar um rascunho local de reserva com as opções fornecidas, as datas, os preços indicados e as condições para revisão.
- [x] Preparar um rascunho local de formulário e mostrar os campos preenchidos para revisão.
- [x] Ligar carrinhos, reservas e formulários a APIs configuradas que aceitam referência idempotente e devolvem estado e campos para verificação.

### Rotinas e fluxos

- [x] Inserir uma etapa de aprovação que bloqueia o próximo passo até à decisão. Implementado para a confirmação dos PDFs.
- [x] Persistir o estado das tarefas em curso, incluindo passos concluídos, passo atual e aprovações pendentes, e retomar nesse ponto após reiniciar. Implementado no fluxo PDF → rascunho por perfil.
  - [x] Implementar o acompanhamento persistente de downloads e o aviso de conclusão no painel.
  - [x] Guardar os blocos transcritos de uma reunião e permitir recuperar os que chegaram ao JARVIS quando a gravação foi interrompida.
- [x] Permitir repetir apenas o passo em falta após uma falha e manter os passos concluídos registados. Implementado no fluxo PDF → rascunho.
- [x] Guardar a tentativa SMTP antes do envio, bloquear novas tentativas após aceitação ou resultado incerto e permitir a consulta em Enviados.
- [x] Evitar duplicar rascunhos IMAP, mensagens Matrix e ações HTTPS com referências persistentes e reconciliação no serviço.
- [x] Cancelar uma tarefa entre dois passos e mostrar o que já aconteceu e o que ficou por executar. **Implementado no painel do fluxo PDF → rascunho.**

### Painel e acessibilidade

- [x] Mostrar as ações pendentes com os detalhes necessários para aprovar ou recusar cada uma. **Implementado para a seleção de PDFs pendente de confirmação.**
- [x] Mostrar as tarefas em execução, o passo atual e os controlos disponíveis para intervir. **Implementado no painel do fluxo PDF → rascunho.**

### Permissões e privacidade

- [x] Restringir a importação, consulta e exportação de rascunhos IMAP às contas e pastas autorizadas para o perfil.
- [x] Restringir o envio SMTP às contas configuradas para o perfil.
- [x] Pedir confirmação explícita antes de enviar email com a conta, o conteúdo e os anexos revistos.
- [x] Aplicar permissões por sala Matrix e exigir confirmação explícita de cada mensagem.
- [x] Rever vendedor, artigos, total e campos do pedido antes de confirmar uma compra numa integração configurada.
- [x] Exigir confirmação por código antes de eliminar permanentemente um ficheiro individual autorizado e verificar a versão revista.
- [x] Invalidar a confirmação SMTP quando o rascunho, destinatários, anexos ou configuração de envio mudam e exigir nova revisão.
- [x] Invalidar confirmações quando a versão do ficheiro, os dados do rascunho ou a configuração do destino mudam.

### Extensões e manutenção

- [x] Integrar a ferramenta MCP de metadados de ficheiros e aplicar permissões por conta e raiz autorizada.
- [x] Instalar a extensão integrada de metadados e publicar as ferramentas autorizadas no registo MCP.
- [x] Desativar a extensão integrada e retirar as respetivas ferramentas do registo e da execução.
- [x] Mostrar no painel o estado da ligação ao Ollama, ao Hermes Agent e ao Open-Meteo e indicar se a chave da Brave Search está configurada.
- [x] Recuperar o estado guardado de tarefas e reconciliar envios SMTP, mensagens Matrix, rascunhos IMAP e ações HTTPS através da referência persistente.

## Fase 5 — Versão avançada

### Programação

- [ ] Criar uma extensão opcional do VS Code para mostrar a seleção ou o ficheiro ativo antes de o enviar ao JARVIS.
- [ ] Mostrar a proposta do JARVIS como uma comparação dentro do VS Code e permitir aprová-la ou descartá-la. Depende da geração e aplicação de propostas da Fase 4.

### Voz

- [ ] Ativar a transcrição com «Olá, Jarvis». Depende da transcrição e da indicação do estado do microfone.

### Ecrã, imagens e câmara

- [ ] Interpretar uma captura de ecrã fornecida pelo utilizador e explicar o que nela aparece.
- [ ] Interpretar a janela ativa a pedido e identificar a aplicação e o conteúdo visível.
- [ ] Ler uma mensagem de erro no ecrã e reproduzir o texto relevante.
- [ ] Identificar o botão referido pelo utilizador numa captura ou janela.
- [ ] Extrair dados de uma imagem e permitir que sejam revistos.
- [ ] Partilhar uma janela temporariamente para acompanhamento em direto e parar a captura ao terminar a partilha.
- [ ] Digitalizar um documento com a câmara após ativação explícita e devolver a imagem ou o texto extraído.
- [ ] Interpretar uma imagem da câmara após ativação explícita e desativar a captura quando a operação termina.

### Internet e investigação

- [ ] Vigiar alterações numa página indicada e mostrar o que mudou desde a última verificação. Depende da pesquisa web e das rotinas agendadas.

### Casa inteligente

- [ ] Ligar o Home Assistant ou os serviços dos dispositivos e apresentar os dispositivos autorizados.
- [ ] Controlar luzes e apresentar o estado final reportado.
- [ ] Controlar tomadas e apresentar o estado final reportado.
- [ ] Controlar estores e apresentar a posição final reportada.
- [ ] Ajustar a climatização e apresentar a temperatura alvo ou o modo definido.
- [ ] Controlar a reprodução de música através da integração da casa e apresentar o estado do dispositivo.
- [ ] Controlar o aspirador e apresentar o estado reportado.
- [ ] Consultar os sensores da divisão pedida e mostrar a leitura e a hora.
- [ ] Consultar consumos e apresentar os valores para o dispositivo e o período pedidos.
- [ ] Criar e ativar cenas por divisão e apresentar o estado de cada dispositivo após ativação.
- [ ] Agendar a ativação de uma cena por hora.
- [ ] Mostrar quando um dispositivo não confirmou a mudança e apresentar o último estado conhecido.

### Música e entretenimento

- [ ] Reproduzir a música encontrada no serviço escolhido.
- [ ] Reproduzir o episódio de um podcast selecionado.
- [ ] Reproduzir um vídeo selecionado.
- [ ] Gerir a fila de reprodução, permitindo adicionar, remover e mover itens.
- [ ] Consultar e controlar o que está a tocar na divisão indicada.
- [ ] Ajustar o volume da reprodução na divisão escolhida e apresentar o nível resultante.
- [ ] Retomar um episódio na posição guardada.
- [ ] Encontrar uma música pela descrição e apresentar as correspondências.
- [ ] Encontrar um filme ou uma série pela descrição e apresentar as correspondências.

### Telemóvel e acesso remoto

- [ ] Enviar pedidos por chat no telemóvel e receber a resposta.
- [ ] Usar voz no telemóvel com transcrição e resposta falada.
- [ ] Receber notificações com uma ação rápida no telemóvel e aplicar a ação à tarefa associada.
- [ ] Sincronizar alterações de tarefas entre PC e telemóvel.
- [ ] Enviar fotografias do telemóvel para uma pasta de destino no PC.
- [ ] Enviar documentos do telemóvel para o PC.
- [ ] Consultar no telemóvel o estado das automações a correr no PC.
- [ ] Suspender remotamente uma tarefa iniciada noutro dispositivo e bloquear a execução da etapa seguinte enquanto está suspensa.
- [ ] Cancelar remotamente uma tarefa e mostrar o resultado nos dois dispositivos.

### Conversa

- [ ] Retomar no telemóvel uma conversa do PC preservando contexto e perfil. Depende da sincronização e do histórico.

### Agenda e tarefas

- [ ] Criar lembretes por localização com acesso autorizado. Depende das notificações no telemóvel.

### Proatividade

- [ ] Entregar um briefing da manhã à hora definida, com a agenda e as tarefas relevantes.
- [ ] Alertar quando surge um conflito na agenda e mostrar os eventos envolvidos.
- [ ] Avisar de um prazo com a antecedência configurada.
- [ ] Alertar quando um serviço monitorizado falha e indicar qual deixou de responder.
- [ ] Notificar o utilizador quando se cumpre uma condição que pediu para vigiar, com uma ligação ou referência ao resultado.
- [ ] Aplicar horas de silêncio e manter pendentes os avisos sem permissão para interromper.
- [ ] Agrupar notificações relacionadas mantendo cada evento identificável.
- [ ] Configurar que tipos de alerta podem interromper o utilizador.

### Painel e acessibilidade

- [ ] Configurar um controlo físico opcional para iniciar a escuta ou parar uma tarefa.

### Permissões e privacidade

- [ ] Aplicar permissões por dispositivo.
- [ ] Atribuir uma permissão própria a ações físicas sensíveis, como abrir uma porta.
- [ ] Mostrar o dispositivo e o efeito pretendido antes de confirmar uma ação física sensível.
- [ ] Permitir revogar a partilha de janela, câmara ou localização e terminar a recolha dependente.

### Funcionamento local e desempenho

- [ ] Encaminhar pedidos simples para um modelo rápido.
- [ ] Encaminhar tarefas longas para um modelo mais capaz.
- [ ] Ativar o modelo de visão quando o utilizador pede uma análise de imagem, janela ou câmara.
- [ ] Permitir ativar ou desativar serviços externos preservando os comandos locais.

## Protótipo H.O.L.O Hands

### Validar a base

- [ ] Inspecionar o fluxo de chat e voz do Jarvis para identificar por onde enviar contexto de um cartão e ler a resposta.

### Ligar o gesto ao modelo

- [x] Fixar a revisão do H.O.L.O usada no protótipo e preservar a licença e os créditos.
- [x] Reutilizar a ação de resumo do H.O.L.O para enviar a nota selecionada a uma rota local.
- [x] Implementar o resumo no Ollama e a apresentação do resultado no painel.
- [x] Mostrar o estado de processamento e tratar pedidos repetidos, Ollama indisponível e modelo em falta.

### Integrar a voz

- [x] Adicionar a leitura pelo navegador, com seleção de voz local e indicação de voz indisponível.
- [x] Usar a nota aberta como contexto de uma pergunta escrita.
- [x] Adicionar ditado local ao campo de pergunta.

### Preparar a instalação

- [ ] Documentar a configuração e o arranque no Windows, incluindo a instalação inicial dos modelos.
- [ ] Registar os passos para resolver problemas de câmara, microfone ou Ollama.
