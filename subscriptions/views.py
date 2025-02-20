import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

from .models import Subscription, StripeStatus

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Assicura che l'utente sia autenticato
def create_checkout_session(request):
    try:
        user = request.user
        data = request.data
        price_id = data.get("price_id")
        plan = data.get("plan", "monthly")  # 'monthly' o 'annual'

        # Crea un cliente Stripe se non esiste già
        customer = stripe.Customer.create(email=user.email)

        # Crea una sessione di checkout
        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            success_url=f"{settings.FRONTEND_URL}/payments/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/payments/cancel",
        )

        # Salva i dettagli della sottoscrizione in modo preliminare
        Subscription.objects.update_or_create(
            user=user,
            defaults={
                'stripe_customer_id': customer.id,
                'plan': plan,
                'status': StripeStatus.PENDING,  # Stato iniziale
            }
        )

        return JsonResponse({'url': session.url})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get('stripe-signature')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Gestisci l'evento ricevuto
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_id = session['customer']

        # Attiva la sottoscrizione per l'utente
        subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if subscription:
            subscription.stripe_subscription_id = session['subscription']
            subscription.status = StripeStatus.ACTIVE
            subscription.save()
            # Add credits to user account
            user = subscription.user
            user.credits = 50
            user.save()

    elif event['type'] == 'customer.subscription.deleted':
        subscription_data = event['data']['object']
        stripe_subscription_id = subscription_data['id']

        # Aggiorna lo stato della sottoscrizione
        subscription = Subscription.objects.filter(stripe_subscription_id=stripe_subscription_id).first()
        if subscription:
            subscription.status = StripeStatus.CANCELED
            subscription.save()

    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice['customer']
        subscription_id = invoice['subscription']

        # Trova la sottoscrizione corrispondente
        subscription = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()
        if subscription:
            # Se il pagamento è andato a buon fine, aggiungi i crediti
            user = subscription.user
            user.credits = 50  # Accredita i crediti all'utente
            user.save()            

    return JsonResponse({'status': 'success'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    user = request.user
    subscription = Subscription.objects.filter(user=user).first()

    if subscription:
        return Response({
            'plan': subscription.plan,
            'status': subscription.status,
            'created_at': subscription.created_at,
        })
    return Response({'error': 'No active subscription'}, status=404)


# @csrf_exempt
# def stripe_webhook(request):
#     stripe.api_key = settings.STRIPE_SECRET_KEY
#     endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
#     payload = request.body
#     sig_header = request.META['HTTP_STRIPE_SIGNATURE']
#     event = None

#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, endpoint_secret
#         )
#     except ValueError as e:
#         # Invalid payload
#         return HttpResponse(status=400)
#     except stripe.error.SignatureVerificationError as e:
#         # Invalid signature
#         return HttpResponse(status=400)

#     # Handle the checkout.session.completed event
#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object']

#         # Fetch all the required data from session
#         client_reference_id = session.get('client_reference_id')
#         stripe_customer_id = session.get('customer')
#         stripe_subscription_id = session.get('subscription')

#         if stripe_subscription_id:
#             # Get the user and create a new StripeCustomer
#             user = User.objects.get(id=client_reference_id)
#             StripeCustomer.objects.create(
#                 user=user,
#                 stripe_customer_id=stripe_customer_id,
#                 stripe_subscription_id=stripe_subscription_id,
#             )
#             print(user.email + ' just subscribed.')

#     if event['type'] == 'customer.subscription.deleted':
#         subscription_id = event['data']['object']['id']

#         try:
#             # Aggiorna il database locale per riflettere che l'abbonamento è stato cancellato
#             subscription = StripeCustomer.objects.get(stripe_subscription_id=subscription_id)
#             subscription.status = StripeStatus.CANCELED
#             subscription.save()
#             print(subscription.user.email + ' just unsubscribed.')
#         except StripeCustomer.DoesNotExist:
#             pass

#     if event['type'] == 'payment_intent.succeeded':
#         payment_intent = event['data']['object']
#         print(payment_intent)

#         # Fetch all the required data from payment_intent
#         client_reference_id = payment_intent.get('metadata', {}).get('client_reference_id')
#         job_id = payment_intent.get('metadata', {}).get('job_id')
#         stripe_customer_id = payment_intent.get('customer')
#         amount_received = payment_intent.get('amount_received')

#         if client_reference_id:
#             # Get the user and create a new StripePayment
#             user = User.objects.get(id=client_reference_id)
#             job = Job.objects.get(id=job_id)
#             payment = StripePayment.objects.create(
#                 user=user,
#                 amount=amount_received,
#                 payment_intent_id=payment_intent.get('id'),
#             )
#             job.payment = payment
#             job.status = StatusPost.ACTIVE
#             job.save()
#             print(user.email + ' just made a one-time payment for ' + job.title)

#     return HttpResponse(status=200)


# from datetime import datetime

# import stripe
# from django.conf import settings
# from django.contrib.auth.decorators import login_required
# from django.http.response import JsonResponse, HttpResponse
# from django.shortcuts import render
# from django.views.decorators.csrf import csrf_exempt

# from subscriptions.models import StripeCustomer, StripeStatus, StripePayment
# from users.models import User


# def get_user_plan(user):
#     try:
#         # Retrieve the subscription & product
#         stripe_customer = StripeCustomer.objects.get(user=user)
#         stripe.api_key = settings.STRIPE_SECRET_KEY
#         subscription = stripe.Subscription.retrieve(stripe_customer.stripe_subscription_id)
#         product = stripe.Product.retrieve(subscription.plan.product)

#         # Feel free to fetch any additional data from 'subscription' or 'product'
#         # https://stripe.com/docs/api/subscriptions/object
#         # https://stripe.com/docs/api/products/object

#         info_status_subscription = {
#             'status': subscription.status,
#             # 'active', 'trialing', 'past_due', 'unpaid', 'canceled', 'incomplete', 'incomplete_expired'
#             # 'canceled_at': datetime.fromtimestamp(subscription.canceled_at),
#             'current_period_end': datetime.fromtimestamp(subscription.current_period_end),
#             # 'current_period_start': subscription.current_period_start,
#             # 'ended_at': subscription.ended_at,
#             'subscription': subscription,
#             'product': product,
#         }

#     except StripeCustomer.DoesNotExist:

#         info_status_subscription = {
#             'status': None,
#         }

#     return info_status_subscription

# # @login_required
# # @csrf_exempt
# def create_checkout_onetime_session(total, product_id, email, user_id):
#     try:
#         domain_url = 'http://localhost:8000/'
#         stripe.api_key = settings.STRIPE_SECRET_KEY
#         session = stripe.checkout.Session.create(
#             payment_method_types=['card'],
#             line_items=[
#                 {
#                     'price_data': {
#                         'currency': 'usd',
#                         'product_data': {
#                             'name': 'Job Post',
#                         },
#                         'unit_amount': int(total * 100),
#                     },
#                     'quantity': 1,
#                 },
#             ],
#             mode='payment',
#             customer_email=email,
#             success_url=domain_url + 'payment/success/',
#             cancel_url=domain_url + 'payment/cancel/',
#             payment_intent_data={
#                 'metadata': {
#                     'client_reference_id': user_id,
#                     'product_id': product_id,
#                 }
#             }
#         )
#         payment_intent = session.payment_intent
#         return {'session': session, 'order': payment_intent}
#     except Exception as e:
#         return {'error': str(e)}


# # @login_required
# # @csrf_exempt
# # def start_checkout_session(request):
# #     if request.method == 'GET':
# #         job_id = request.GET.get('id')
# #         job = Job.objects.get(id=job_id)
# #         if not job:
# #             return JsonResponse({'message': 'Job not found.', 'status': False})
# #         payment = create_checkout_onetime_session(job.total, job.id, request.user.email, request.user.id)
# #         return JsonResponse({'session': payment['session'], 'order': payment['order']})
# #     return JsonResponse({'message': 'Method not allowed.', 'status': False})


# @login_required
# @csrf_exempt
# def create_checkout_session(request):
#     if request.method == 'GET':
#         domain_url = 'http://localhost:8000/'  # TODO: Update this with your domain
#         subscription_type = request.GET.get('type')  # monthly or yearly
#         subscription_plan = request.GET.get('plan')  # basic or pro

#         if subscription_type not in ['monthly', 'yearly'] or subscription_plan not in ['basic', 'pro']:
#             return JsonResponse({'error': 'Invalid subscription type or plan'}, status=400)

#         price_id = settings.STRIPE_PRICE_IDS.get(f'{subscription_type}_{subscription_plan}')
#         stripe.api_key = settings.STRIPE_SECRET_KEY
#         try:
#             checkout_session = stripe.checkout.Session.create(
#                 client_reference_id=str(request.user.id),
#                 success_url=domain_url + 'subscriptions/success?session_id={CHECKOUT_SESSION_ID}',
#                 cancel_url=domain_url + 'subscriptions/cancel/',
#                 customer_email=request.user.email,
#                 payment_method_types=['card'],
#                 mode='subscription',
#                 line_items=[
#                     {
#                         'price': price_id,
#                         'quantity': 1,
#                     }
#                 ]
#             )
#             return JsonResponse({'sessionId': checkout_session['id']})
#         except Exception as e:
#             return JsonResponse({'error': str(e)})


# @csrf_exempt
# def stripe_config(request):
#     if request.method == 'GET':
#         stripe_configuration = {'publicKey': settings.STRIPE_PUBLISHABLE_KEY}
#         return JsonResponse(stripe_configuration, safe=False)


# @login_required
# def success(request):
#     return render(request, 'app/success.html')


# @login_required
# def cancel(request):
#     return render(request, 'app/cancel.html')


# # @csrf_exempt
# # def stripe_webhook(request):
# #     stripe.api_key = settings.STRIPE_SECRET_KEY
# #     endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
# #     payload = request.body
# #     sig_header = request.META['HTTP_STRIPE_SIGNATURE']
# #     event = None
# #
# #     try:
# #         event = stripe.Webhook.construct_event(
# #             payload, sig_header, endpoint_secret
# #         )
# #     except ValueError as e:
# #         # Invalid payload
# #         return HttpResponse(status=400)
# #     except stripe.error.SignatureVerificationError as e:
# #         # Invalid signature
# #         return HttpResponse(status=400)
# #
# #     # Handle the checkout.session.completed event
# #     if event['type'] == 'checkout.session.completed':
# #         session = event['data']['object']
# #
# #         # Fetch all the required data from session
# #         client_reference_id = session.get('client_reference_id')
# #         stripe_customer_id = session.get('customer')
# #         stripe_subscription_id = session.get('subscription')
# #
# #         # Get the user and create a new StripeCustomer
# #         user = User.objects.get(id=client_reference_id)
# #         StripeCustomer.objects.create(
# #             user=user,
# #             stripe_customer_id=stripe_customer_id,
# #             stripe_subscription_id=stripe_subscription_id,
# #         )
# #         print(user.email + ' just subscribed.')
# #
# #     if event['type'] == 'customer.subscription.deleted':
# #         subscription_id = event['data']['object']['id']
# #
# #         try:
# #             # Aggiorna il database locale per riflettere che l'abbonamento è stato cancellato
# #             subscription = StripeCustomer.objects.get(stripe_subscription_id=subscription_id)
# #             subscription.status = StripeStatus.CANCELED
# #             subscription.save()
# #             print(subscription.user.email + ' just unsubscribed.')
# #         except StripeCustomer.DoesNotExist:
# #             pass
# #
# #     return HttpResponse(status=200)


# @csrf_exempt
# def stripe_webhook(request):
#     stripe.api_key = settings.STRIPE_SECRET_KEY
#     endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
#     payload = request.body
#     sig_header = request.META['HTTP_STRIPE_SIGNATURE']
#     event = None

#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, endpoint_secret
#         )
#     except ValueError as e:
#         # Invalid payload
#         return HttpResponse(status=400)
#     except stripe.error.SignatureVerificationError as e:
#         # Invalid signature
#         return HttpResponse(status=400)

#     # Handle the checkout.session.completed event
#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object']

#         # Fetch all the required data from session
#         client_reference_id = session.get('client_reference_id')
#         stripe_customer_id = session.get('customer')
#         stripe_subscription_id = session.get('subscription')

#         if stripe_subscription_id:
#             # Get the user and create a new StripeCustomer
#             user = User.objects.get(id=client_reference_id)
#             StripeCustomer.objects.create(
#                 user=user,
#                 stripe_customer_id=stripe_customer_id,
#                 stripe_subscription_id=stripe_subscription_id,
#             )
#             print(user.email + ' just subscribed.')

#     if event['type'] == 'customer.subscription.deleted':
#         subscription_id = event['data']['object']['id']

#         try:
#             # Aggiorna il database locale per riflettere che l'abbonamento è stato cancellato
#             subscription = StripeCustomer.objects.get(stripe_subscription_id=subscription_id)
#             subscription.status = StripeStatus.CANCELED
#             subscription.save()
#             print(subscription.user.email + ' just unsubscribed.')
#         except StripeCustomer.DoesNotExist:
#             pass

#     if event['type'] == 'payment_intent.succeeded':
#         payment_intent = event['data']['object']
#         print(payment_intent)

#         # Fetch all the required data from payment_intent
#         client_reference_id = payment_intent.get('metadata', {}).get('client_reference_id')
#         job_id = payment_intent.get('metadata', {}).get('job_id')
#         stripe_customer_id = payment_intent.get('customer')
#         amount_received = payment_intent.get('amount_received')

#         if client_reference_id:
#             # Get the user and create a new StripePayment
#             user = User.objects.get(id=client_reference_id)
#             job = Job.objects.get(id=job_id)
#             payment = StripePayment.objects.create(
#                 user=user,
#                 amount=amount_received,
#                 payment_intent_id=payment_intent.get('id'),
#             )
#             job.payment = payment
#             job.status = StatusPost.ACTIVE
#             job.save()
#             print(user.email + ' just made a one-time payment for ' + job.title)

#     return HttpResponse(status=200)


# @login_required
# @csrf_exempt
# def cancel_subscription(request):
#     if request.method == 'POST':
#         try:
#             stripe_customer = StripeCustomer.objects.get(user=request.user)
#             stripe.api_key = settings.STRIPE_SECRET_KEY

#             stripe.Subscription.modify(
#                 stripe_customer.stripe_subscription_id,
#                 cancel_at_period_end=True
#             )

#             stripe_customer.status = StripeStatus.CANCELLING
#             stripe_customer.save()

#             return JsonResponse({'status': True, 'message': 'Subscription deleted.'})
#         except StripeCustomer.DoesNotExist:
#             return JsonResponse({'status': False, 'error': 'Subscription does not exist.'})
#     return JsonResponse({'error': 'Method not allowed.'})

# # Elimina la sottoscrizione immediatamente
# # @login_required
# # @csrf_exempt
# # def cancel_subscription(request):
# #     if request.method == 'POST':
# #         try:
# #             stripe_customer = StripeCustomer.objects.get(user=request.user)
# #             stripe.api_key = settings.STRIPE_SECRET_KEY
# #             stripe.Subscription.delete(stripe_customer.stripe_subscription_id)
# #             stripe_customer.status = StripeStatus.CANCELED
# #             stripe_customer.save()
# #             return JsonResponse({'status': True, 'message': 'Subscription deleted.'})
# #         except StripeCustomer.DoesNotExist:
# #             return JsonResponse({'status': False, 'error': 'Subscription does not exist.'})
# #     return JsonResponse({'error': 'Method not allowed.'})
