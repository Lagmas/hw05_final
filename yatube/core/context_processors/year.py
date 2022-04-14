from django.utils import timezone


def year(request):
    current_datetime = timezone.now().year
    return {'year': current_datetime}
