from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'  # Legge il parametro 'page_size' dall'URL
    max_page_size = 50  # Imposta il massimo numero di elementi per pagina
