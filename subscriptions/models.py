from django.db import models
from users.models import User


class StripeStatus(models.TextChoices):
    ACTIVE = 'active'
    CANCELED = 'canceled'
    CANCELLING = 'cancelling'
    INACTIVE = 'inactive'
    PENDING = 'pending'


class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    stripe_customer_id = models.CharField(max_length=255, unique=True)
    plan = models.CharField(max_length=50)  # 'monthly' o 'annual'
    status = models.CharField(max_length=50, choices=StripeStatus.choices, default=StripeStatus.INACTIVE)  # 'active', 'inactive', 'canceled'
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan} ({self.status})"



# class StripeCustomer(models.Model):
#     user = models.OneToOneField(to=User, on_delete=models.CASCADE, related_name='stripe_customer')
#     stripe_customer_id = models.CharField(max_length=255)
#     stripe_subscription_id = models.CharField(max_length=255)
#     status = models.CharField(max_length=50, choices=StripeStatus.choices, default=StripeStatus.ACTIVE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.user.email


# class StripePayment(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     amount = models.IntegerField()  # Amount in cents
#     payment_intent_id = models.CharField(max_length=255)
#     created_at = models.DateTimeField(auto_now_add=True)

