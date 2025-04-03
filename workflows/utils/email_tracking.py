import re
from django.urls import reverse
from django.core import signing


def wrap_plain_links(text: str) -> str:
    """
    Wrappa i link nudi tipo http://example.com in <a href="...">...</a>
    evitando quelli già presenti come href="..."
    """
    pattern = r'(?<!href=["\'])\bhttps?://[^\s<"]+'

    def wrap(match):
        url = match.group(0)
        return f'<a href="{url}">{url}</a>'

    return re.sub(pattern, wrap, text)


def convert_links_to_trackable(body: str, lead_id: int, email_log_id: int, domain: str) -> str:
    """
    Sostituisce tutti gli href con URL firmati e tracciabili,
    ignorando i link già tracciati (dominio tuo).
    """
    def replacer(match):
        original_url = match.group(2)

        # Ignora link già tracciati (con tuo dominio)
        if domain in original_url:
            return match.group(0)

        signed_data = signing.dumps({
            "lead_id": lead_id,
            "email_log_id": email_log_id,
            "url": original_url,
        })
        tracking_url = f"https://{domain}{reverse('track_email_click', args=[signed_data])}"
        return f'{match.group(1)}="{tracking_url}"'

    # Trova href = "..." o '...' con link http/https
    pattern = r'(href)\s*=\s*["\'](https?://[^"\']+)["\']'
    return re.sub(pattern, replacer, body)


def prepare_email_body(body: str, lead_id: int, email_log_id: int, domain: str) -> str:
    """
    Wrappa link nudi e converte tutti i link in tracciabili.
    """
    # Step 1: Wrappa i link nudi
    body = wrap_plain_links(body)

    # Step 2: Converte i link wrappati in link tracciabili
    body = convert_links_to_trackable(body, lead_id, email_log_id, domain)

    return body