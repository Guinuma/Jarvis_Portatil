"""Extrair texto legível de fragmentos de HTML."""
from html.parser import HTMLParser


class PlainHTML(HTMLParser):
    BLOCKS = {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "blockquote"}
    HIDDEN = {"script", "style", "head", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = []

    def handle_starttag(self, tag, attrs):
        if tag in self.HIDDEN:
            self.hidden.append(tag)
        elif not self.hidden and tag in self.BLOCKS:
            self.parts.append("\n")
            if tag == "blockquote":
                self.parts.append("> ")

    def handle_endtag(self, tag):
        if self.hidden and self.hidden[-1] == tag:
            self.hidden.pop()
        elif not self.hidden and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, content):
        if not self.hidden:
            self.parts.append(content)
