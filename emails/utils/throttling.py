from emails.models import ThrottleStatus

def is_account_throttled(account):
    throttle = ThrottleStatus.objects.filter(account=account).first()
    return throttle and throttle.is_throttled()

def update_throttle_status(account):
    throttle, _ = ThrottleStatus.objects.get_or_create(account=account)
    throttle.increase()

def reset_throttle_status(account):
    throttle = ThrottleStatus.objects.filter(account=account).first()
    if throttle:
        throttle.reset()
