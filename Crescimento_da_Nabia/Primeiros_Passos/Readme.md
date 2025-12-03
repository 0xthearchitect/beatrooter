## Olha só aquelas perninhas a mexer(quer dizer cauda)

Conseguimos uma Nábia que finalmente explora, pensa e dá um resultado, ainda não é nada muito grande ou rápido(longe disso), mas estamos a dar os primeiros passos, ou melhor dizendo a Nábia está a dar os primeiros passos para o futuro.

---

### Como fizemos este feito?

Usamos um modelo pequeno e mais fraquito, mas bastante eficaz. O que para nos poupa tempo e recursos, já que somos uma empresa pequena e ainda a começar no mercado da cibersegurança, software e tecnologia.

Em python:

Usamos a biblioteca *playwright*, para mapeamento do htmls, links, forms e scripts do site.

Exemplo:
```python
from playwright.sync_api import sync_playwright

def crawl(url: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        data = {
            "url": url,
            "html": page.content(),
            "links": page.eval_on_selector_all("a", "els => els.map(e => e.href)"),
            "forms": page.eval_on_selector_all("form", "els => els.map(e => e.outerHTML)"),
            "scripts": page.eval_on_selector_all("script", "els => els.map(e => e.outerHTML)")
        }

        browser.close()
        return data
```

Modelo Ollama usado:

Com aquilo que achamos anteriormente, entregamos ao modelo *qwen2.5-coder* para analisar e com um prompt personalizado entregar-nos exatamente aquilo que queriamos.
