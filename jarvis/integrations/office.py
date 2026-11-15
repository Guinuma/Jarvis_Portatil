"""Criar e editar ficheiros Office locais com confirmação por releitura."""
import json
import os
import re
import tempfile
from io import BytesIO
from pathlib import Path
from threading import Lock

from .project_files import safe_path

OFFICE = re.compile(r'(cria|edita) (documento|folha|apresentação) "([^"]+)" com (.+)', re.I | re.S)
FORMATS = {"documento": ".docx", "folha": ".xlsx", "apresentação": ".pptx"}
CELL = re.compile(r"[A-Z]{1,3}[1-9][0-9]{0,6}")
EDIT_LOCK = Lock()


def office_module(suffix, existing=True):
    try:
        if suffix == ".docx":
            from docx import Document
            return Document
        if suffix == ".pptx":
            from pptx import Presentation
            return Presentation
        from openpyxl import Workbook, load_workbook
        return load_workbook if existing else Workbook
    except ImportError as error:
        package = {".docx": "python-docx", ".xlsx": "openpyxl", ".pptx": "python-pptx"}[suffix]
        raise ValueError(f"Instala {package} para trabalhar com ficheiros {suffix}.") from error


def office_command(text, root):
    command = OFFICE.fullmatch(text)
    if not command:
        return None
    action, kind, name, data = command.groups()
    editing = action.lower() == "edita"
    suffix = FORMATS[kind.lower()]
    target = safe_path(root, name)
    if target.suffix.lower() != suffix:
        raise ValueError(f"Escolhe um destino {suffix}.")
    payload = json.loads(data)
    with EDIT_LOCK:
        if editing:
            if not target.is_file() or target.stat().st_size > 32 * 1024 * 1024:
                raise ValueError("Escolhe um ficheiro existente com até 32 MB.")
            original = target.read_bytes()
            artifact = office_module(suffix)(BytesIO(original))
        else:
            artifact = office_module(suffix, existing=False)()
        verify = apply_content(suffix, artifact, payload, editing)
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=suffix, delete=False) as stream:
            temporary = stream.name
        try:
            artifact.save(temporary)
            if not verify(office_module(suffix)(temporary)):
                raise ValueError("O ficheiro reaberto não contém todos os valores pedidos.")
            if editing:
                if safe_path(root, name) != target or target.read_bytes() != original:
                    raise ValueError("O ficheiro mudou durante a edição. Volta a abrir e rever o documento.")
                os.replace(temporary, target)
            else:
                os.link(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return f"Ficheiro {'editado' if editing else 'criado'} e reaberto: {target.relative_to(root)}."


def apply_content(suffix, artifact, payload, editing):
    if suffix == ".docx":
        if editing:
            if not isinstance(payload, dict) or not payload:
                raise ValueError('Indica os parágrafos a substituir, por exemplo {"1":"Novo texto"}.')
            updates = numbered_updates(payload, len(artifact.paragraphs))
            for index, value in updates.items():
                paragraph = artifact.paragraphs[index]
                # Preserve existing run styling for ordinary replacement.
                if paragraph.runs:
                    paragraph.runs[0].text = value
                    for run in paragraph.runs[1:]:
                        run.text = ""
                else:
                    paragraph.add_run(value)
        else:
            if not isinstance(payload, list) or not payload or not all(isinstance(x, str) for x in payload):
                raise ValueError('Indica uma lista de parágrafos, por exemplo ["Título","Texto"].')
            updates = dict(enumerate(payload))
            for value in payload:
                artifact.add_paragraph(value)
        return lambda result: all(result.paragraphs[i].text == value for i, value in updates.items())
    if suffix == ".xlsx":
        if not isinstance(payload, dict) or set(payload) != {"folha", "células"}:
            raise ValueError('Indica a folha e as células, por exemplo {"folha":"Resumo","células":{"A1":10}}.')
        title, cells = payload["folha"], payload["células"]
        if not isinstance(title, str) or not 0 < len(title) <= 31 or re.search(r'[\\/*?:\[\]]', title):
            raise ValueError("O nome da folha é inválido.")
        if not isinstance(cells, dict) or not cells:
            raise ValueError("Indica pelo menos uma célula.")
        if editing and title not in artifact.sheetnames:
            raise ValueError("A folha indicada não existe.")
        sheet = artifact[title] if editing else artifact.active
        sheet.title = title
        for address, value in cells.items():
            if not CELL.fullmatch(address) or not isinstance(value, (str, int, float, bool, type(None))):
                raise ValueError("Usa endereços de célula como A1 e valores simples ou fórmulas.")
            sheet[address] = value
        return lambda result: all(
            result[title][address].value == (None if value == "" else value) for address, value in cells.items()
        )

    if editing:
        if not isinstance(payload, dict) or not payload:
            raise ValueError('Indica os diapositivos, por exemplo {"1":{"título":"Novo título","texto":"Novo texto"}}.')
        updates = []
        for key, fields in payload.items():
            index = numbered_index(key, len(artifact.slides))
            if isinstance(fields, str):
                fields = {"título": fields}
            if (not isinstance(fields, dict) or not fields or set(fields) - {"título", "texto"}
                    or not all(isinstance(value, str) for value in fields.values())):
                raise ValueError("Indica um título, texto ou ambos para cada diapositivo.")
            for field, value in fields.items():
                slide_text_shape(artifact.slides[index], field, index + 1).text = value
                updates.append((index, field, value))
        return lambda result: all(
            slide_text_shape(result.slides[index], field, index + 1).text == value
            for index, field, value in updates
        )

    if not isinstance(payload, list) or not payload:
        raise ValueError('Indica uma lista de diapositivos com título e texto.')
    for slide in payload:
        if (not isinstance(slide, dict) or set(slide) != {"título", "texto"}
                or not all(isinstance(value, str) for value in slide.values())):
            raise ValueError('Usa {"título":"Título","texto":"Conteúdo"} para cada diapositivo.')
        page = artifact.slides.add_slide(artifact.slide_layouts[1])
        page.shapes.title.text = slide["título"]
        page.placeholders[1].text = slide["texto"]
    return lambda result: len(result.slides) == len(payload) and all(
        page.shapes.title.text == expected["título"] and page.placeholders[1].text == expected["texto"]
        for page, expected in zip(result.slides, payload)
    )


def numbered_updates(payload, count):
    updates = {}
    for key, value in payload.items():
        if not isinstance(value, str):
            raise ValueError("Usa valores de texto.")
        updates[numbered_index(key, count)] = value
    return updates


def numbered_index(key, count):
    if not re.fullmatch(r"[1-9]\d{0,5}", key) or int(key) > count:
        raise ValueError("Usa números existentes, a partir de 1.")
    return int(key) - 1


def slide_text_shape(slide, field, number):
    from pptx.enum.shapes import PP_PLACEHOLDER

    if field == "título":
        title = slide.shapes.title
        if title is None:
            raise ValueError(f"O diapositivo {number} não tem um campo de título.")
        return title
    bodies = [
        shape for shape in slide.placeholders
        if shape.has_text_frame and shape.placeholder_format.type in {PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT}
    ]
    if len(bodies) != 1:
        raise ValueError(f"O diapositivo {number} precisa de um único campo de texto para esta alteração.")
    return bodies[0]
