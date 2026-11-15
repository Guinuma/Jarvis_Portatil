"""Guardar matéria, dificuldades e exercícios de estudo por perfil."""
import json
import re
from datetime import date, timedelta

from jarvis.integrations.editor import normalize
from jarvis.integrations.project_files import safe_path

SAVE_CARD = re.compile(r'cria cartões de estudo sobre "([^"]{1,100})" com (.+)', re.I | re.S)
IMPORT_CARDS = re.compile(r'cria cartões de estudo sobre "([^"]{1,100})" de "([^"]{1,500})"[.!]?', re.I)
LIST_CARDS = re.compile(r'(?:revê|mostra) cartões de estudo sobre "([^"]{1,100})"[.!]?', re.I)
QUIZ = re.compile(r'(?:cria|gera) (?:um )?teste de estudo sobre "([^"]{1,100})"(?: com ([1-9]|10) perguntas)?[.!]?', re.I)
GRADE = re.compile(r'corrige (?:o )?teste de estudo (\d{1,18}) com (.+)', re.I | re.S)
DIFFICULTY = re.compile(r'regista dificuldade (?:em|sobre) "([^"]{1,100})" com "([^"]{1,500})"[.!]?', re.I)
LIST_DIFFICULTIES = re.compile(r'(?:mostra|consulta) (?:as )?dificuldades de estudo[.!]?', re.I)
PLAN = re.compile(
    r'(?:cria|gera) (?:um )?plano de estudo até (\d{4}-\d{2}-\d{2}) com (\d{1,3}) minutos por dia para (.+)',
    re.I | re.S,
)
DEFINITION = re.compile(r"^\s*[-*]\s+(.{1,240}?)\s+::\s+(.{1,500})$")
CARD_LIMITS = {"pergunta": 240, "resposta": 500, "explicação": 700}


def study_command(text, memory, root):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := SAVE_CARD.fullmatch(command):
        return save_cards(memory, match[1], json.loads(match[2]))
    if match := IMPORT_CARDS.fullmatch(command):
        return import_cards(memory, root, *match.groups())
    if match := LIST_CARDS.fullmatch(command):
        return list_cards(memory, match[1])
    if match := QUIZ.fullmatch(command):
        return create_quiz(memory, match[1], int(match[2] or 5))
    if match := GRADE.fullmatch(command):
        return grade_quiz(memory, int(match[1]), json.loads(match[2]))
    if match := DIFFICULTY.fullmatch(command):
        return save_difficulty(memory, *match.groups())
    if LIST_DIFFICULTIES.fullmatch(command):
        return list_difficulties(memory)
    if match := PLAN.fullmatch(command):
        return create_plan(memory, match[1], int(match[2]), json.loads(match[3]))
    return None


def topic_name(text):
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 100:
        raise ValueError("Indica um tópico com até 100 caracteres.")
    name = " ".join(text.split())
    key = normalize(name)
    if not key:
        raise ValueError("Indica um nome para o tópico de estudo.")
    return key, name


def save_cards(memory, topic, payload, source=None):
    key, name = topic_name(topic)
    if not isinstance(payload, list) or not 1 <= len(payload) <= 15:
        raise ValueError("Indica de 1 a 15 cartões.")
    saved = {}
    for card in payload:
        if (not isinstance(card, dict) or not {"pergunta", "resposta"} <= set(card) <= set(CARD_LIMITS)
                or any(not isinstance(value, str) or not 0 < len(value.strip()) <= CARD_LIMITS[field]
                       for field, value in card.items())):
            raise ValueError("Cada cartão precisa de pergunta, resposta e, opcionalmente, explicação.")
        question = card["pergunta"].strip()
        question_key = normalize(question)
        if not question_key or question_key in saved:
            raise ValueError("Cada pergunta deve ser diferente.")
        saved[question_key] = {"key": question_key, "question": question, "answer": card["resposta"].strip(),
                               "explanation": card.get("explicação", "").strip(), "source": source}
    memory.execute(
        """INSERT INTO study_cards (topic_key, topic, question_key, question, answer, explanation, source)
           SELECT ?, ?, json_extract(value, '$.key'), json_extract(value, '$.question'),
                  json_extract(value, '$.answer'), json_extract(value, '$.explanation'), json_extract(value, '$.source')
           FROM json_each(?) WHERE 1
           ON CONFLICT(topic_key, question_key) DO UPDATE SET topic=excluded.topic, question=excluded.question,
               answer=excluded.answer, explanation=excluded.explanation, source=excluded.source""",
        (key, name, json.dumps(list(saved.values()), ensure_ascii=False)),
    )
    return f"{len(saved)} cartão(ões) guardado(s) em {name}. Pede «Mostra cartões de estudo sobre \"{name}\"»."


def import_cards(memory, root, topic, filename):
    path = safe_path(root, filename)
    if path.suffix.lower() not in {".md", ".txt"} or not path.is_file() or path.stat().st_size > 128_000:
        raise ValueError("Indica um ficheiro Markdown ou TXT do projeto com até 128 kB.")
    cards = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if match := DEFINITION.fullmatch(line):
            question, answer = match.groups()
            cards.append({"pergunta": question, "resposta": answer})
    if not cards:
        raise ValueError("Usa uma lista com o formato «- pergunta :: resposta» na matéria de origem.")
    return save_cards(memory, topic, cards, path.relative_to(root).as_posix())


def list_cards(memory, topic):
    key, name = topic_name(topic)
    rows = memory.execute(
        """SELECT question, answer, explanation, source FROM study_cards
           WHERE topic_key=? ORDER BY question_key LIMIT 11""", (key,),
    )
    if not rows:
        return f"Não há cartões guardados sobre {name}."
    cards = []
    for index, row in enumerate(rows[:10], 1):
        source = f"\nOrigem — {row['source']}" if row["source"] else ""
        explanation = f"\nExplicação — {row['explanation'][:260]}" if row["explanation"] else ""
        cards.append(f"{index}. {row['question']}\nResposta — {row['answer']}{explanation}{source}")
    if len(rows) > 10:
        cards.append("A revisão mostra os primeiros 10 cartões por ordem de pergunta.")
    return "\n\n".join(cards)


def create_quiz(memory, topic, count):
    key, name = topic_name(topic)
    cards = memory.execute(
        "SELECT question, answer, explanation FROM study_cards WHERE topic_key=? ORDER BY random() LIMIT ?",
        (key, count),
    )
    if not cards:
        return f"Cria primeiro cartões de estudo sobre {name}."
    row = memory.execute(
        "INSERT INTO study_quizzes (topic, cards) VALUES (?, ?) RETURNING id",
        (name, json.dumps(cards, ensure_ascii=False)),
    )[0]
    lines = [f"Teste de estudo {row['id']} · {name} · {len(cards)} pergunta(s)"]
    lines.extend(f"{index}. {card['question']}" for index, card in enumerate(cards, 1))
    lines.append(f'Para corrigir, usa «Corrige o teste de estudo {row["id"]} com {{"1":"Resposta"}}».')
    return "\n".join(lines)


def compare_answer(answer):
    return " ".join(normalize(answer).strip(" .!?\r\n\t").split())


def quiz_answers(memory, identifier, answers):
    rows = memory.execute("SELECT cards FROM study_quizzes WHERE id=?", (identifier,))
    if not rows:
        return None
    cards = json.loads(rows[0]["cards"])
    valid = {str(index) for index in range(1, len(cards) + 1)}
    if (not isinstance(answers, dict) or not answers or set(answers) - valid
            or not all(isinstance(answer, str) and 0 < len(answer.strip()) <= 500 for answer in answers.values())):
        raise ValueError("Usa os números das perguntas e as respostas em texto.")
    return cards


def grade_quiz(memory, identifier, answers):
    cards = quiz_answers(memory, identifier, answers)
    if cards is None:
        return "Não encontrei esse teste de estudo neste perfil."
    matches, feedback = 0, []
    for number in sorted(answers, key=int):
        card = cards[int(number) - 1]
        answer = answers[number]
        exact = compare_answer(answer) == compare_answer(card["answer"])
        matches += exact
        status = "corresponde à resposta de referência" if exact else "revê com a resposta de referência"
        line = f"{number}. {status}\nResposta — {card['answer']}"
        if card["explanation"]:
            line += f"\nExplicação — {card['explanation']}"
        feedback.append(line)
    return f"{matches} de {len(answers)} resposta(s) coincidem com a referência.\n\n" + "\n\n".join(feedback)


def save_difficulty(memory, topic, detail):
    key, name = topic_name(topic)
    detail = detail.strip()
    if not detail:
        raise ValueError("Descreve a dificuldade numa frase.")
    stamp = date.today().isoformat()
    memory.execute(
        """INSERT INTO study_difficulties (topic_key, topic, detail, updated) VALUES (?, ?, ?, ?)
           ON CONFLICT(topic_key) DO UPDATE SET topic=excluded.topic, detail=excluded.detail, updated=excluded.updated""",
        (key, name, detail, stamp),
    )
    return f"Dificuldade guardada em {name} · {stamp}."


def list_difficulties(memory):
    rows = memory.execute(
        "SELECT topic, detail, updated FROM study_difficulties ORDER BY updated DESC, topic_key LIMIT 20"
    )
    return "\n".join(f"{row['topic']} · {row['detail']} · {row['updated']}" for row in rows) or "Sem dificuldades registadas."


def create_plan(memory, when, minutes, topics):
    today = date.today()
    try:
        exam = date.fromisoformat(when)
    except ValueError as error:
        raise ValueError("Indica a data de avaliação no formato AAAA-MM-DD.") from error
    days = (exam - today).days
    if not 1 <= days <= 30 or not 10 <= minutes <= 360:
        raise ValueError("Indica uma avaliação entre amanhã e 30 dias e uma disponibilidade de 10 a 360 minutos por dia.")
    if not isinstance(topics, list) or not 1 <= len(topics) <= 12:
        raise ValueError("Indica os tópicos numa lista com 1 a 12 nomes.")
    subjects = dict(topic_name(topic) for topic in topics)
    difficulties = {row["topic_key"] for row in memory.execute("SELECT topic_key FROM study_difficulties")}
    keys = sorted(subjects, key=lambda key: key not in difficulties)
    intervals = min(3, len(keys), minutes // 10)
    if days * intervals < len(keys):
        raise ValueError("A disponibilidade não chega a todos os tópicos. Indica mais tempo ou reduz os tópicos.")
    review_minutes = max(0, minutes // 5) if minutes >= 25 else 0
    if minutes - review_minutes < 10 * intervals:
        review_minutes = minutes - 10 * intervals
    block, remainder = divmod(minutes - review_minutes, intervals)
    schedule = [f"Avaliação a {exam:%d/%m/%Y} · {minutes} min/dia"]
    for offset in range(days):
        entries = []
        for index in range(intervals):
            key = keys[(offset * intervals + index) % len(keys)]
            period = block + (index < remainder)
            entries.append(f"{subjects[key]} ({period} min)")
        if review_minutes:
            entries.append(f"recordação ativa ({review_minutes} min)")
        schedule.append(f"{today + timedelta(days=offset):%d/%m} · " + " · ".join(entries))
    return "\n".join(schedule)
