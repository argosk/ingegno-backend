import re
from leads.models import Lead
from django.utils.timezone import now
from django.core import signing
from django.forms.models import model_to_dict
from django.conf import settings as ingegno_settings


def get_unsubscribe_link(lead):
    signed = signing.dumps({"lead_id": lead.id})
    return f"https://{ingegno_settings.DOMAIN}/api/leads/unsubscribe/?token={signed}"

# Funzioni personalizzate disponibili nei template
CUSTOM_PLACEHOLDER_FUNCTIONS = {
    "current_date": lambda lead: now().strftime("%d/%m/%Y"),
    "unsubscribe_link": get_unsubscribe_link,  
}

def replace_placeholders(text: str, lead: Lead) -> str:
    """
    Sostituisce {placeholder} nel testo con:
    - Campi del modello Lead (solo quelli del DB)
    - Funzioni personalizzate definite in CUSTOM_PLACEHOLDER_FUNCTIONS
    """
    lead_data = model_to_dict(lead)

    def replacer(match):
        key = match.group(1)

        # 1. Se è una funzione personalizzata, la eseguo
        if key in CUSTOM_PLACEHOLDER_FUNCTIONS:
            try:
                return str(CUSTOM_PLACEHOLDER_FUNCTIONS[key](lead))
            except Exception as e:
                return f"[Errore: {e}]"

        # 2. Se è un campo del modello Lead
        if key in lead_data:
            return str(lead_data[key])

        # 3. Altrimenti lo lascio così com'è
        return match.group(0)

    return re.sub(r"\{([a-zA-Z0-9_]+)\}", replacer, text)