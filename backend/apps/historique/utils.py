from .models import Historique


def log_action(user, action, module, objet_id=None, description='', ip=None):
    try:
        Historique.objects.create(
            utilisateur=user if user and user.is_authenticated else None,
            action=action,
            module=module,
            objet_id=str(objet_id) if objet_id else '',
            description=description,
            adresse_ip=ip,
        )
    except Exception:
        pass  # Ne jamais bloquer une action métier pour un log