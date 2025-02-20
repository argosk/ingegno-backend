from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Blog
from .serializers import BlogSerializer


class BlogListView(ListAPIView):
    """
    Vista per ottenere tutti i post, con paginazione.
    """
    queryset = Blog.objects.all().order_by('-created_at')
    serializer_class = BlogSerializer


class BlogDetailView(RetrieveAPIView):
    """
    Vista per ottenere un singolo post tramite lo slug.
    """
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    lookup_field = 'slug'  # Usa lo slug invece dell'ID per la ricerca
