from django.conf import settings
from django.core.paginator import Paginator


def get_page_obj(posts, page_num):
    paginator = Paginator(posts, settings.LIMIT)
    return paginator.get_page(page_num)
