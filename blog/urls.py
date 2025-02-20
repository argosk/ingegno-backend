from django.urls import path
from .views import BlogListView, BlogDetailView

app_name = 'blog'

urlpatterns = [
    path('', BlogListView.as_view(), name='blog-list'),  # Endpoint per tutti i post
    path('<slug:slug>/', BlogDetailView.as_view(), name='blog-detail'),  # Endpoint per un post tramite slug
]
