def record_to_dict(record):
    values = {}
    for rv in record.values:
        field = rv.entity_field
        if field:
            values[field.name] = rv.value_text

    return {
        'id': record.id,
        'entity_type_id': record.entity_type_id,
        'entity_type': record.entity_type.name if record.entity_type else None,
        'org_unit_id': record.org_unit_id,
        'org_unit': record.org_unit.name if record.org_unit else None,
        'parent_record_id': record.parent_record_id,
        'display_label': record.display_label,
        'values': values,
        'created_at': record.created_at.isoformat() if record.created_at else None,
        'updated_at': record.updated_at.isoformat() if record.updated_at else None,
        'is_active': record.is_active,
    }


def entity_type_to_dict(et):
    return {
        'id': et.id,
        'name': et.name,
        'slug': et.slug,
        'description': et.description,
        'icon': et.icon,
        'is_lookup': et.is_lookup,
        'parent_entity_type_id': et.parent_entity_type_id,
        'fields': [entity_field_to_dict(f) for f in et.fields],
    }


def entity_field_to_dict(f):
    return {
        'id': f.id,
        'name': f.name,
        'label': f.label,
        'field_type': f.field_type,
        'is_required': f.is_required,
        'is_unique': f.is_unique,
        'options': f.get_options_list(),
        'lookup_entity_type_id': f.lookup_entity_type_id,
        'display_in_list': f.display_in_list,
        'order': f.order,
    }


def form_to_dict(form):
    return {
        'id': form.id,
        'name': form.name,
        'description': form.description,
        'entity_type_id': form.entity_type_id,
        'entity_type': form.entity_type.name if form.entity_type else None,
        'version': form.version,
        'is_active': form.is_active,
        'fields': [form_field_to_dict(ff) for ff in form.form_fields if ff.is_visible],
    }


def form_field_to_dict(ff):
    ef = ff.entity_field
    d = entity_field_to_dict(ef) if ef else {}
    d['form_field_id'] = ff.id
    d['order'] = ff.order
    d['help_text'] = ff.help_text
    return d


def org_unit_to_dict(unit, include_children=False):
    d = {
        'id': unit.id,
        'name': unit.name,
        'code': unit.code,
        'level': unit.level,
        'path': unit.path,
        'parent_id': unit.parent_id,
        'is_active': unit.is_active,
    }
    if include_children:
        d['children'] = [org_unit_to_dict(c, include_children=True) for c in unit.children.filter_by(is_active=True)]
    return d
