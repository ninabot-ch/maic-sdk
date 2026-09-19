"""Point d'entrée de l'agent. Le bac à sable appelle run(ctx, params) et attend un Report.
Seuls `ctx` (SDK maic) et la stdlib sont disponibles : pas de réseau, pas de fichiers hors /work, pas d'environnement."""


def run(ctx, params):
    lang = ctx.lang                                    # "fr" ou "en" : le rapport est dans la langue de la compagnie
    prompt = ctx.prompt("main", **params)              # prompt/<lang>/main.txt avec les variables {{sujet}} {{ton}}
    context = ctx.memory.search(params["sujet"], k=5)  # ce que la Bibliothèque sait du sujet
    ctx.progress(20)
    text = ctx.llm("tool", [{"role": "system", "content": prompt}, {"role": "user", "content": context}], max_tokens=800)
    ctx.progress(90)
    return ctx.report(title=None,                       # None = titre du manifeste
                      html=f"<p>{ctx.esc(text)}</p>",
                      facts=[])                        # faits courts à retenir dans la Bibliothèque (optionnel)
