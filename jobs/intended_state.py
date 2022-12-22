import json

from django.apps import apps
from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError

from nautobot.extras.jobs import Job, TextVar

name = "POC Jobs"


def replace_ref(ref):
    """Recursively replace references."""
    if isinstance(ref, dict):
        for key, value in ref.items():
            ref[key] = replace_ref(value)
        return ref

    if isinstance(ref, (list, set, tuple)):
        return [replace_ref(r) for r in ref]

    if not isinstance(ref, (str, bytes)):
        return ref

    if not ref.startswith("#ref"):
        return ref

    ref_split = ref.split(":")
    # pop off #ref
    ref_split.pop(0)
    # Grab the app.model
    app_name = ref_split.pop(0)
    object_class = apps.get_model(app_name)
    # Get every other item in the list for fields
    fields = [f for f in ref_split[::2]]
    # and for values start at index 1
    values = [v for v in ref_split[1::2]]
    obj_lookup = {fields[i]: values[i] for i in range(len(fields))}
    return object_class.objects.get(**obj_lookup)


def obj_set(obj, _set):
    set_ref, set_list = _set.items()
    ref_split = set_ref.split(":")
    field_name = ref_split[1]
    if not isinstance(set_list, (list, set, tuple)):
        set_list = [set_list]
    field = getattr(obj, field_name)
    field.set(set_list, clear=True)


class IntendedState(Job):

    json_payload = TextVar()

    class Meta:
        name = "Intended State Job POC"
        description = "Create or update objects in Nautobot by passing in an intended state JSON payload."

    def run(self, data, commit):
        json_payload = data["json_payload"]
        intended_state = json.loads(json_payload)
        for object_name, objects in intended_state.items():
            object_class = apps.get_model(object_name)
            for object_data in objects:
                _set = None
                for key, value in object_data.items():
                    try:
                        object_data[key] = replace_ref(value)
                        if isinstance(key, (str, bytes)) and key.startswith("#set"):
                            _set = object_data.pop(key)
                    except (AttributeError, ObjectDoesNotExist, ValidationError) as e:
                        self.log_warning(message=f"Error on key {key}. Error: {e}.")
                        continue
                try:
                    obj, created = object_class.objects.update_or_create(**object_data)
                    if _set:
                        obj_set(obj, _set)
                except (FieldError, ObjectDoesNotExist) as e:
                    self.log_warning(message=f"Unable to create object. Error: {e}.")
                    continue
                self.log_success(obj=obj, message=f"Object {obj} has been {'created' if created else 'updated'}.")


jobs = [IntendedState]
