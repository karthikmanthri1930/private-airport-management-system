from .views import is_airport_admin


def airport_access(request):
    return {"is_airport_admin": is_airport_admin(request.user)}
