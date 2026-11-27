"""HTML interamente sintetico. Nessun testo di terzi riprodotto."""

from html import escape


def article(title, paragraphs, *, source="aica", published="2026-11-20T10:00:00+01:00"):
    body = "".join(f"<p>{escape(p)}</p>" for p in paragraphs)
    if source == "aica":
        return (
            f'<main><div class="contenuto"><time datetime="{published}"></time>'
            f"<h1>{escape(title)}</h1>{body}</div></main>"
        ).encode()
    return (
        f'<nav><h2>Cerca qualcosa</h2></nav><li class="breadcrumb-item active" '
        f'aria-current="page">{escape(title)}</li><span datetime="{published}"></span>'
        f'<div class="content"><div class="wysiwyg-text-reset">{body}</div></div>'
    ).encode()


def calendar(
    *, value="08:00", second="Rinviato", full_dates=True, municipality="Agrigento", duplicate=False
):
    heading = 'data-date="2026-11-20"' if full_dates else ""
    second_heading = 'data-date="2026-11-21"' if full_dates else ""
    row = (
        f"<tr><td>ZONA TEST 1</td><td>VIA SINTETICA</td><td>{escape(value)}</td>"
        f"<td>{escape(second)}</td></tr>"
    )
    return (
        f'<main><p>FIXTURE SINTETICA</p><div class="turni-comune-blocco" '
        f'data-valid-from="2026-11-20" data-valid-until="2026-11-21">'
        f'<h2 class="turni-titolo-comune">{escape(municipality)}</h2>'
        '<div class="turni-serbatoio"><h3>Serbatoio sintetico</h3>'
        '<table class="turni-tabella"><thead><tr><th>Zona</th><th>Vie servite</th>'
        f"<th {heading}>Ven 20</th><th {second_heading}>Sab 21</th></tr></thead>"
        f"<tbody>{row}{row if duplicate else ''}</tbody></table></div></div></main>"
    ).encode()
