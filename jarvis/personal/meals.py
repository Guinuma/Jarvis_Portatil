"""Despensa, receitas e planos de refeições por perfil."""
import json
import re
from collections import Counter
from datetime import date, timedelta

from jarvis.integrations.editor import normalize
from jarvis.local_registers import saved_day

UNIT = r'(g|ml|un)'
DAY = r'(\d{4}-\d{2}-\d{2})'
PANTRY = re.compile(rf'(?:regista|põe) na despensa "([^"\r\n]{{1,100}})" (\d{{1,7}}) {UNIT}[.!]?', re.I)
LIST_PANTRY = re.compile(r'(?:mostra|consulta) a despensa[.!]?', re.I)
SAVE_RECIPE = re.compile(r'guarda receita "([^"\r\n]{1,100})" com (.+)', re.I | re.S)
RECIPE = re.compile(r'mostra a receita "([^"\r\n]{1,100})"(?: para (\d{1,2}) pessoas)?[.!]?', re.I)
SUGGEST = re.compile(r'sugere receitas(?: para (\d{1,2}) pessoas)?(?: sem (.+?))?[.!]?', re.I | re.S)
PLAN = re.compile(rf'planeia refeições de {DAY} a {DAY} para (\d{{1,2}}) pessoas(?: sem (.+?))?[.!]?', re.I | re.S)
SHOW_PLAN = re.compile(r'mostra o plano de refeições (\d{1,18})[.!]?', re.I)
SHOP = re.compile(r'adiciona as compras do plano (\d{1,18})[.!]?', re.I)
UNITS = {"g", "ml", "un"}

STARTERS = [
    ("Massa com tomate e grão", [("massa", 85, "g"), ("tomate triturado", 120, "g"), ("grão cozido", 90, "g"),
                                 ("azeite", 10, "ml"), ("alho", 5, "g")],
     ["Coze a massa segundo o tempo indicado na embalagem.", "Amolece o alho no azeite, junta o tomate e deixa apurar.",
      "Junta o grão escorrido ao molho e mistura com a massa."]),
    ("Arroz de ervilhas", [("arroz", 80, "g"), ("ervilhas", 90, "g"), ("cebola", 40, "g"), ("azeite", 10, "ml")],
     ["Refoga a cebola picada em azeite.", "Junta o arroz e as ervilhas, cobre com a água indicada para o arroz e deixa cozer."]),
    ("Salada de grão e pepino", [("grão cozido", 150, "g"), ("pepino", 100, "g"), ("tomate", 120, "g"),
                               ("azeite", 10, "ml"), ("limão", 1, "un")],
     ["Escorre o grão e corta o pepino e o tomate.", "Mistura tudo e tempera com azeite e sumo de limão ao gosto."]),
    ("Omelete de espinafres", [("ovos", 2, "un"), ("espinafres", 80, "g"), ("azeite", 8, "ml")],
     ["Salteia os espinafres no azeite até perderem volume.", "Junta os ovos batidos e cozinha em lume moderado até firmarem."]),
    ("Sopa de cenoura e batata", [("cenoura", 180, "g"), ("batata", 130, "g"), ("cebola", 40, "g"), ("azeite", 8, "ml")],
     ["Corta os legumes e cobre-os com água num tacho.", "Coze até ficarem macios, tritura e termina com azeite."]),
    ("Cuscuz com lentilhas", [("cuscuz", 75, "g"), ("lentilhas cozidas", 120, "g"), ("cenoura", 75, "g"),
                              ("azeite", 10, "ml")],
     ["Hidrata o cuscuz com água quente segundo a embalagem.", "Salteia a cenoura ralada em azeite.",
      "Junta as lentilhas escorridas e envolve no cuscuz."]),
    ("Batata com feijão branco", [("batata", 220, "g"), ("feijão branco cozido", 130, "g"), ("cebola", 35, "g"),
                                  ("azeite", 9, "ml")],
     ["Coze a batata em cubos até ficar macia.", "Amolece a cebola no azeite, junta o feijão e envolve com a batata."]),
    ("Arroz com cogumelos", [("arroz", 80, "g"), ("cogumelos", 140, "g"), ("cebola", 40, "g"), ("azeite", 9, "ml")],
     ["Salteia a cebola e os cogumelos em azeite.", "Junta o arroz e a água da cozedura e deixa cozinhar até o arroz ficar macio."]),
]


def meal_command(text, memory):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := PANTRY.fullmatch(command):
        return stock_item(memory, match[1], int(match[2]), match[3].lower())
    if LIST_PANTRY.fullmatch(command):
        stock = pantry(memory)
        return format_quantities(stock) if stock else "A despensa ainda não tem ingredientes registados."
    if match := SAVE_RECIPE.fullmatch(command):
        return save_recipe(memory, match[1], json.loads(match[2]))
    if match := RECIPE.fullmatch(command):
        recipes = recipe_book(memory)
        recipe = recipes.get(ingredient_name(match[1])[0])
        if recipe is None:
            raise ValueError("Não encontrei essa receita. Pede sugestões para ver as receitas disponíveis.")
        return render_recipe(recipe, servings(match[2] or recipe["servings"]))
    if match := SUGGEST.fullmatch(command):
        return suggest(memory, servings(match[1]), excluded_ingredients(match[2]))
    if match := PLAN.fullmatch(command):
        return new_plan(memory, match[1], match[2], servings(match[3]), excluded_ingredients(match[4]))
    if match := SHOW_PLAN.fullmatch(command):
        return render_plan(int(match[1]), read_plan(memory, int(match[1])))
    if match := SHOP.fullmatch(command):
        return add_plan_shopping(memory, int(match[1]))
    return None


def ingredient_name(value):
    if not isinstance(value, str):
        raise ValueError("Indica nomes em texto.")
    name = " ".join(value.split())
    key = normalize(name)
    if not 0 < len(name) <= 100 or not key:
        raise ValueError("Indica um nome entre 1 e 100 caracteres.")
    return key, name


def servings(value):
    result = int(value) if value is not None else 1
    if not 1 <= result <= 12:
        raise ValueError("Indica de 1 a 12 pessoas.")
    return result


def excluded_ingredients(value):
    if value is None:
        return set()
    data = json.loads(value)
    if not isinstance(data, list) or len(data) > 15:
        raise ValueError("Indica os ingredientes a excluir numa lista JSON com até 15 nomes.")
    return {ingredient_name(name)[0] for name in data}


def stock_item(memory, raw_name, quantity, unit):
    key, name = ingredient_name(raw_name)
    if not quantity:
        removed = memory.execute("DELETE FROM pantry WHERE item_key=? AND unit=? RETURNING name", (key, unit))
        return f"Removido da despensa · {name}." if removed else "Esse ingrediente já não está na despensa nessa unidade."
    memory.execute(
        """INSERT INTO pantry (item_key, unit, name, quantity) VALUES (?, ?, ?, ?)
           ON CONFLICT(item_key, unit) DO UPDATE SET name=excluded.name, quantity=excluded.quantity""",
        (key, unit, name, quantity),
    )
    return f"Despensa atualizada · {name} · {quantity} {unit}."


def pantry(memory):
    rows = memory.execute("SELECT item_key, unit, name, quantity FROM pantry ORDER BY item_key, unit")
    return {(row["item_key"], row["unit"]): (row["name"], row["quantity"]) for row in rows}


def save_recipe(memory, title, contents):
    key, title = ingredient_name(title)
    if not isinstance(contents, dict) or set(contents) != {"porções", "ingredientes", "passos"}:
        raise ValueError("Indica as porções, os ingredientes e os passos da receita.")
    people, ingredients, steps = (contents[field] for field in ("porções", "ingredientes", "passos"))
    if type(people) is not int or not 1 <= people <= 12:
        raise ValueError("Indica de 1 a 12 porções na receita.")
    if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 20:
        raise ValueError("Indica de 1 a 20 ingredientes com nome, quantidade e unidade.")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 12 or not all(
        isinstance(step, str) and 0 < len(step.strip()) <= 500 for step in steps
    ):
        raise ValueError("Indica de 1 a 12 passos, cada um com até 500 caracteres.")
    amounts = []
    seen = set()
    for ingredient in ingredients:
        if not isinstance(ingredient, dict) or set(ingredient) != {"nome", "quantidade", "unidade"}:
            raise ValueError("Cada ingrediente precisa de nome, quantidade e unidade.")
        item, name = ingredient_name(ingredient["nome"])
        quantity, unit = ingredient["quantidade"], ingredient["unidade"]
        if type(quantity) is not int or not 1 <= quantity <= 100_000 or not isinstance(unit, str) or unit not in UNITS:
            raise ValueError("Usa uma quantidade inteira positiva e a unidade g, ml ou un.")
        if (item, unit) in seen:
            raise ValueError("Junta as linhas repetidas do mesmo ingrediente e unidade.")
        seen.add((item, unit))
        amounts.append([name, quantity, unit])
    recipe = {"title": title, "servings": people, "ingredients": amounts, "steps": [step.strip() for step in steps]}
    memory.execute(
        """INSERT INTO meal_recipes (name_key, recipe) VALUES (?, ?)
           ON CONFLICT(name_key) DO UPDATE SET recipe=excluded.recipe""",
        (key, json.dumps(recipe, ensure_ascii=False)),
    )
    return f"Receita guardada · {title} · {people} porção(ões)."


def recipe_book(memory):
    recipes = {normalize(title): {"title": title, "servings": 1, "ingredients": ingredients, "steps": steps}
               for title, ingredients, steps in STARTERS}
    recipes.update({row["name_key"]: json.loads(row["recipe"])
                    for row in memory.execute("SELECT name_key, recipe FROM meal_recipes")})
    return recipes


def quantities(recipe, people):
    base = recipe["servings"]
    return {(ingredient_name(name)[0], unit): (name, (amount * people + base - 1) // base)
            for name, amount, unit in recipe["ingredients"]}


def format_quantities(items, limit=100):
    records = list(items.items())
    lines = [f"- {name} · {count} {unit}" for (_, unit), (name, count) in records[:limit]]
    if len(records) > limit:
        lines.append(f"Mais {len(records) - limit} ingrediente(s) na lista.")
    return "\n".join(lines)


def render_recipe(recipe, people):
    lines = [f"{recipe['title']} · {people} porção(ões)", "", "Ingredientes", format_quantities(quantities(recipe, people)), "", "Preparação"]
    lines.extend(f"{number}. {step}" for number, step in enumerate(recipe["steps"], 1))
    return "\n".join(lines)


def catalog(memory, people, excluded):
    items = []
    for recipe in recipe_book(memory).values():
        required = quantities(recipe, people)
        if any(key in excluded for key, _ in required):
            continue
        items.append((recipe["title"], required))
    if not items:
        raise ValueError("As exclusões eliminaram todas as receitas disponíveis.")
    return items


def split_stock(required, stock):
    available, missing = {}, {}
    for key, (name, amount) in required.items():
        stocked = min(amount, stock.get(key, 0))
        if stocked:
            available[key] = (name, stocked)
        if amount > stocked:
            missing[key] = (name, amount - stocked)
    return available, missing


def rank(items, stock, used):
    def score(item):
        title, required = item
        _, missing = split_stock(required, stock)
        proportion = sum(missing[key][1] / amount for key, (_, amount) in required.items() if key in missing)
        return len(missing), used[title], proportion, title.casefold()
    return sorted(items, key=score)


def suggest(memory, people, excluded):
    stock = {key: entry[1] for key, entry in pantry(memory).items()}
    candidates = rank(catalog(memory, people, excluded), stock, Counter())
    lines = [f"Sugestões para {people} pessoa(s), pela quantidade de ingredientes em falta."]
    for title, required in candidates[:4]:
        available, missing = split_stock(required, stock)
        lines.append(f"{title}\nDa despensa\n{format_quantities(available) or 'Sem stock registado.'}"
                     f"\nFalta comprar\n{format_quantities(missing) or 'Com os ingredientes registados na despensa.'}")
    return "\n\n".join(lines)


def new_plan(memory, lower, upper, people, excluded):
    start, end = [date.fromisoformat(saved_day(value)) for value in (lower, upper)]
    days = (end - start).days + 1
    if not 1 <= days <= 7:
        raise ValueError("Indica um período de 1 a 7 dias com a data inicial antes da final.")
    available = {key: entry[1] for key, entry in pantry(memory).items()}
    items = catalog(memory, people, excluded)
    covered, shopping, dates = Counter(), Counter(), []
    labels = {}
    for offset in range(days):
        title, required = rank(items, available, covered)[0]
        covered[title] += 1
        uses, missing = split_stock(required, available)
        for key, (_, amount) in uses.items():
            available[key] -= amount
        for key, (name, amount) in missing.items():
            labels[key] = name
            shopping[key] += amount
        dates.append({"date": (start + timedelta(days=offset)).isoformat(), "title": title})
    purchases = [[labels[key], count, key[1]] for key, count in sorted(shopping.items())]
    plan = {"people": people, "meals": dates, "shopping": purchases}
    row = memory.execute("INSERT INTO meal_plans (plan) VALUES (?) RETURNING id",
                         (json.dumps(plan, ensure_ascii=False),))[0]
    return render_plan(row["id"], plan)


def read_plan(memory, identifier):
    rows = memory.execute("SELECT plan FROM meal_plans WHERE id=?", (identifier,))
    if not rows:
        raise ValueError("Não encontrei esse plano de refeições neste perfil.")
    return json.loads(rows[0]["plan"])


def render_plan(identifier, plan):
    lines = [f"Plano de refeições {identifier} · {plan['people']} pessoa(s) · uma refeição por dia"]
    lines.extend(f"{meal['date']} · {meal['title']}" for meal in plan["meals"])
    lines.append("\nIngredientes por comprar")
    lines.extend(f"- {name} · {amount} {unit}" for name, amount, unit in plan["shopping"])
    if not plan["shopping"]:
        lines.append("A despensa registada cobre o plano.")
    else:
        lines.append(f'\nPara juntar estes ingredientes à lista de compras, pede «Adiciona as compras do plano {identifier}».')
    return "\n".join(lines)


def add_plan_shopping(memory, identifier):
    plan = read_plan(memory, identifier)
    names = [f"{name} · {amount} {unit}".casefold() for name, amount, unit in plan["shopping"]]
    if not names:
        return "Este plano não tem ingredientes em falta."
    inserted = memory.execute(
        """INSERT INTO shopping (name) SELECT value FROM json_each(?) WHERE 1
           ON CONFLICT(name) DO NOTHING RETURNING name""", (json.dumps(names, ensure_ascii=False),),
    )
    return f"Acrescentei {len(inserted)} artigo(s) à lista de compras. {len(names) - len(inserted)} já constava(m) da lista."
