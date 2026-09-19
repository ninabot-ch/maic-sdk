"""Résumé de la semaine — lit prospects, commandes, factures et contacts (scopes déclarés), s'appuie sur la mémoire,
demande une synthèse au palier `tool`, rend un rapport HTML et 1 à 3 faits à retenir."""
import json, re, time


def _recent(rows, days):
    since = time.time() - days * 86400
    return [r for r in rows if float(r.get("ts") or 0) >= since]


def run(ctx, params):
    days = int(params.get("periode") or 7)
    leads = _recent(ctx.data.leads(), days); orders = _recent(ctx.data.orders(), days); invoices = ctx.data.invoices(); contacts = ctx.data.contacts()
    ctx.progress(25)
    unpaid = [i for i in invoices if i.get("status") in ("sent", "viewed") ]
    paid = [i for i in _recent(invoices, days) if i.get("status") == "paid"]
    chf = lambda c: f"{(c or 0) / 100:.2f} CHF"
    facts = {
        "periode_jours": days,
        "prospects": [{"nom": l.get("name"), "message": (l.get("message") or "")[:160], "statut": l.get("status")} for l in leads[:15]],
        "commandes": [{"client": o.get("contact_name"), "total": chf(o.get("total_cents")), "statut": o.get("status")} for o in orders[:15]],
        "factures_payees": [{"numero": i.get("number"), "client": i.get("contact_name"), "montant": chf(i.get("amount_cents"))} for i in paid[:15]],
        "factures_en_attente": [{"numero": i.get("number"), "client": i.get("contact_name"), "montant": chf(i.get("amount_cents"))} for i in unpaid[:15]],
        "nb_contacts": len(contacts), "nb_clients": sum(1 for c in contacts if c.get("status") == "client"),
    }
    notes = ctx.memory.search("prix délai client commande priorité", k=3)
    ctx.progress(45)
    memo = "\n".join(f"- {n.get('description') or n.get('name')}" for n in notes) or ("(pas de note en mémoire)" if ctx.lang == "fr" else "(no memory note)")
    user = ("Données (JSON) :\n" if ctx.lang == "fr" else "Data (JSON):\n") + json.dumps(facts, ensure_ascii=False) + ("\n\nNotes de la mémoire :\n" if ctx.lang == "fr" else "\n\nMemory notes:\n") + memo
    text = ctx.llm("tool", [{"role": "system", "content": ctx.prompt("main")}, {"role": "user", "content": user}], max_tokens=900)
    ctx.progress(90)
    keep = []
    text = re.sub(r"```[a-z]*\s*|```", "", text)
    m = re.search(r"FAITS\s*:\s*(\[.*?\]|\{.*?\})", text, re.S)   # liste demandée ; certains modèles rendent un objet
    if m:
        try:
            got = json.loads(m.group(1)); keep = [(" ".join(map(str, x)) if isinstance(x, (list, tuple)) else str(x)) for x in (got.values() if isinstance(got, dict) else got)][:3]
        except Exception: keep = []
        text = text[:m.start()].strip()
    if not text.strip():
        text = "<p>" + ("Rien à résumer : aucune donnée sur la période." if ctx.lang == "fr" else "Nothing to summarise: no data over the period.") + "</p>"
    head = (f"<p class=\"meta\">{len(leads)} prospect(s), {len(orders)} commande(s), {len(paid)} facture(s) payée(s), {len(unpaid)} en attente — {days} j.</p>" if ctx.lang == "fr"
            else f"<p class=\"meta\">{len(leads)} lead(s), {len(orders)} order(s), {len(paid)} invoice(s) paid, {len(unpaid)} pending — {days} d.</p>")
    return ctx.report(title=None, html=head + text, facts=keep)
