from django.urls import path
from .views import subscription_status, stripe_webhook, create_checkout_session

app_name = 'subscriptions'

urlpatterns = [
    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    path('subscription-status/', subscription_status, name='subscription_status'),
    path('webhook/', stripe_webhook, name='stripe_webhook'),
    # # path('config/', views.stripe_config),
    # path('create-checkout-session/', views.create_checkout_session),
    # path('cancel-subscription/', views.cancel_subscription),
    # path('success/', views.success),
    # path('cancel/', views.cancel),
    # path('webhook/', views.stripe_webhook),
    # path('start-order/', views.start_checkout_session),
]
