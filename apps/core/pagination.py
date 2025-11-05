from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    page_size = 20  # ← tamaño por defecto
    page_size_query_param = "page_size"  # permite ?page_size=50
    max_page_size = 100
