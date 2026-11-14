"""Resolver referências locais sem delegar ações ambíguas ao modelo."""
import re
from datetime import date, datetime, timedelta
from .integrations.editor import normalize


def resolve_reference(messages, memory):
    text = messages[-1]['content'].strip()
    command = normalize(text).rstrip('.!?')
    previous = next((m['content'] for m in reversed(messages[:-1]) if m['role'] == 'assistant'), '')
    if command in {'cancela', 'cancela a escolha', 'cancela a selecao'}:
        return text, 'Seleção cancelada. Nenhuma ação foi executada.'
    if command in {'abre esse ficheiro', 'abre o ficheiro', 'abre esse'}:
        options = re.findall(r'^Abre o ficheiro "[^"\n]+"(?: no projeto "[^"\n]+")?$', previous, re.M)
        if len(options) == 1:
            return options[0], None
        if options:
            return text, 'Encontrei vários ficheiros. Escolhe o pedido completo ou diz «opção 1», «opção 2», etc.:\n' + '\n'.join(options)
        return text, 'Qual é o ficheiro? Pesquisa pelo nome ou indica o caminho relativo ao projeto.'
    selection = re.fullmatch(r'(?:opcao|opção) (\d+)', command)
    if selection:
        options = [line for line in previous.splitlines() if re.match(r'^(Abre o ficheiro|Abre o projeto|Encontra as notas da última sessão do projeto) "', line)]
        index = int(selection[1]) - 1
        if 0 <= index < len(options):
            return options[index], None
        return text, 'Escolhe uma das opções da última resposta.'
    if command in {'a reuniao de amanha', 'mostra a reuniao de amanha', 'qual e a reuniao de amanha', 'a que horas e a reuniao de amanha'}:
        tomorrow = date.today() + timedelta(days=1)
        start = datetime.combine(tomorrow, datetime.min.time()).timestamp()
        end = datetime.combine(tomorrow + timedelta(days=1), datetime.min.time()).timestamp()
        rows = memory.execute('SELECT * FROM agenda WHERE starts < ? AND ends > ? ORDER BY starts', (end, start))
        if not rows:
            return text, 'Não há compromissos amanhã na agenda local.'
        listing = '\n'.join(f'{r["title"]} · {datetime.fromtimestamp(r["starts"]):%H:%M} · evento {r["id"]}' for r in rows)
        return text, ('Amanhã na agenda local:\n' if len(rows) == 1 else 'Há vários compromissos amanhã. Indica o número do evento:\n') + listing
    return text, None
