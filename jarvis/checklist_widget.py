"""Native view of the active profile's personal checklists."""
import sqlite3
import tkinter as tk
from tkinter import ttk

from .personal_checklists import (
    checklist_items, list_checklists, save_widget_selection, set_item, widget_selection,
)


def checklist_widget(window, memory):
    frame = ttk.Frame(window, padding=14)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="As tuas listas").pack(anchor="w")
    picker = ttk.Combobox(frame, state="readonly")
    picker.pack(fill="x", pady=(4, 8))
    status = ttk.Label(frame, wraplength=295)
    status.pack(anchor="w")
    progress = ttk.Progressbar(frame, mode="determinate")
    progress.pack(fill="x", pady=(4, 8))

    viewport = ttk.Frame(frame)
    viewport.pack(fill="both", expand=True)
    canvas = tk.Canvas(viewport, highlightthickness=0, background=ttk.Style().lookup("TFrame", "background"))
    scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    rows = ttk.Frame(canvas)
    inner = canvas.create_window((0, 0), window=rows, anchor="nw")
    rows.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(inner, width=event.width))
    feedback = ttk.Label(frame, wraplength=295)
    feedback.pack(anchor="w")

    lists = []
    selected = None
    rendered = None
    variables = []

    def toggle(item_list, index, variable):
        try:
            set_item(memory, item_list, index, variable.get())
            refresh()
            feedback.config(text="")
        except sqlite3.Error:
            variable.set(not variable.get())
            feedback.config(text="Não consegui guardar a alteração. Tenta novamente.")

    def refresh(load_selection=False):
        nonlocal lists, selected, rendered, variables
        lists = list_checklists(memory)
        picker.configure(values=[f"{entry['title']} · #{entry['id']}" for entry in lists],
                         state="readonly" if lists else "disabled")
        if load_selection:
            selected = widget_selection(memory)
        available = [entry["id"] for entry in lists]
        if selected not in available:
            selected = available[0] if available else None
            if selected is not None:
                save_widget_selection(memory, selected)
        if selected is not None:
            picker.current(available.index(selected))
        else:
            picker.set("")
        items = checklist_items(memory, selected) if selected is not None else []
        completed = sum(item["done"] for item in items)
        status.configure(text=f"{completed} de {len(items)} concluídos" if items else
                         'Cria uma lista no chat. Ex.: «Cria uma lista "Ensaio": levar cabos, carregar a interface».')
        progress.configure(maximum=max(1, len(items)), value=completed)
        signature = (selected, tuple(item["label"] for item in items))
        if signature != rendered:
            for child in rows.winfo_children():
                child.destroy()
            rendered = signature
            variables = []
            canvas.yview_moveto(0)
            for index, item in enumerate(items):
                variable = tk.BooleanVar()
                variables.append(variable)
                check = tk.Checkbutton(
                    rows, text=item["label"], variable=variable, anchor="w", justify="left",
                    wraplength=245, background=canvas.cget("background"),
                    command=lambda list_id=selected, index=index, var=variable: toggle(list_id, index, var),
                )
                check.pack(fill="x", pady=2)
        for variable, item in zip(variables, items):
            variable.set(bool(item["done"]))

    def select_list(event):
        nonlocal selected
        index = picker.current()
        if index < 0:
            return
        try:
            save_widget_selection(memory, lists[index]["id"])
            selected = lists[index]["id"]
            refresh()
            feedback.config(text="")
        except sqlite3.Error:
            feedback.config(text="Não consegui guardar a seleção. Tenta novamente.")

    def poll():
        try:
            refresh(load_selection=True)
        except sqlite3.Error:
            feedback.config(text="Não consegui consultar as listas locais do JARVIS.")
        window.after(2500, poll)

    picker.bind("<<ComboboxSelected>>", select_list)
    poll()
