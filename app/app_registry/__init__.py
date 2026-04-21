from app.app_registry.humanitarian_access import APP as HUMANITARIAN_ACCESS
from app.app_registry.immunization_report import APP as IMMUNIZATION_REPORT

REGISTRY = {
    'humanitarian_access': HUMANITARIAN_ACCESS,
    'immunization_report': IMMUNIZATION_REPORT,
}


def get_template(key):
    return REGISTRY.get(key)


def all_templates():
    return list(REGISTRY.values())
