def serialize_workflow_settings(settings):
    if not settings:
        return None

    return {
        "max_emails_per_day": settings.max_emails_per_day,
        "pause_between_emails": settings.pause_between_emails,
        "reply_action": settings.reply_action,
        "sending_time_start": str(settings.sending_time_start),  # orario in formato stringa
        "sending_time_end": str(settings.sending_time_end),
        "sending_days": settings.sending_days,
        "unsubscribe_handling": settings.unsubscribe_handling,
        "bounce_handling": settings.bounce_handling,
    }