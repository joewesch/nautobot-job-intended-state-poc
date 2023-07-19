# nautobot-job-intended-state-poc

A proof of concept for sending the intended state of objects to a Job in Nautobot

## Why

This POC exists solely to present an alternative solution to creating or updating many items in Nautobot. Instead of doing a `GET` call for each object, determining the current state of that object, sending a `PUT/PATCH` call to update an object or `POST` to create an object, you can instead send in a large amount of data in a single API call to a Job and let it deal with determining state and what needs to be updated.

## Requirements

[Nautobot](https://github.com/nautobot/nautobot)

## How to Use (as-is)

You can add this Job to any Nautobot instance by add it under [Extensibility > Git Repositories](https://docs.nautobot.com/projects/core/en/stable/models/extras/gitrepository/).

Once you have synced the repo, you can run the Job [via the GUI or an API call like any other Job](https://docs.nautobot.com/projects/core/en/stable/additional-features/jobs/#running-jobs). The only job data that is required is a JSON serialized object. Each top level key of the dictionary must be the app name and model in dot notation that you would like to create or update. The value of each `app_label.model` must be a list of dictionaries with field attributes. Here is an example:

```json
{
    "dcim.site": [
        {
            "name": "New Site",
            "status": ...,
            "region": ...,
        }
    ],
    "dcim.device": [
        {
            "name": "New Device",
            "device_role": ...,
            "device_type": ...,
        }
    ]
}
```

> Note: You can find the app_label and model for all current content types by going to https://your.nautobot.instance/api/extras/content-types/.

This payload must be sent as a string that will be serialized. Here is an example of an API payload:

```json
{
    "data": {
        "json_payload": "{\"extras.status\": [{\"name\": \"Test Status\"}]}"
    }
}
```

### References to Other Models

Some item fields are foreign key relationships to other instances. In those cases, you will need to look up the object before trying to use it. For this, I have added a simple colon separated string pattern to replace a value that is a reference with an object instance. You will need to format the reference string as such: `#ref:dcim.site:name:Site 1[:field_2:value_2:...]`

Elements of the reference string:
- `#ref`: must start the string; this denotes that this is a reference to a model instance
- `dcim.site`: the app and model name
- `name`: the identifying field name to query to get the object (i.e. name, slug, model, etc.)
- `Site 1`: the value of the field that uniquely identifies an object
- `field_2` (optional): additional identifying field
- `value_2` (optional): value for `field_2`

### Setting ManyToMany Relationships

Some item fields (M2M) cannot be directly assigned. An example of this would be Content Types or Tags. In this case, you would need to nest these items under a `#set` key in the item dictionary. They will be assigned to the object after it has been created or updated.

Example:
```json
{
    "extras.status": [
        {
            "name": "Active",
            "slug": "active",
            "#set": {
                "content_types": [
                        "#ref:contenttypes.contenttype:app_label:dcim:model:site",
                        "#ref:contenttypes.contenttype:app_label:dcim:model:device",
                    ]
            }
        }
    ]
}
```

### Using Defaults to Update

When using the `update_or_create` method, it will first attempt to use the fields passed in as a `.get()` call looking to see if the item exists with all of the provided fields and if not it will create it. If you are running the Job a second time to update a field on an item (i.e. `description`) then it will fail to find an object with that description and try and create a second instance. This will either fail with an IntegrityError due to duplicate unique fields or it will succeed and it will create a duplicate item which is undesired. To combat this, you should nest all fields that are not used to uniquely identify an object in a `defaults` key.

In this example, only the `name` field is used to uniquely identify the device:
```json
{
    "dcim.device": [
        {
            "name": "Device 1",
            "defaults": {
                "device_role": "#ref:dcim.devicerole:name:Role 1",
                "device_type": "#ref:dcim.devicetype:model:Model 1",
                "site": "#ref:dcim.site:name:Site 1",
            }
        }
    ]
}
```

### Example

Here is an example of a working (albeit rudimentary) example in python:

```python
import json
import requests

url = "https://nautobot.example.com"

token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

headers = {"Authorization": f"Token {token}"}

json_payload = {
    "extras.status": [
        {
            "name": "Active",
            "slug": "active",
            "#set": {
                "content_types": [
                        "#ref:contenttypes.contenttype:app_label:dcim:model:site",
                        "#ref:contenttypes.contenttype:app_label:dcim:model:device",
                    ]
            }
        }
    ],
    "dcim.manufacturer": [
        {"name": "Manufacturer 1"},
        {"name": "Manufacturer 2"},
    ],
    "dcim.devicetype": [
        {
            "model": "Model 1",
            "manufacturer": "#ref:dcim.manufacturer:name:Manufacturer 1",
        },
        {
            "model": "Model 2",
            "manufacturer": "#ref:dcim.manufacturer:name:Manufacturer 2",
        },
    ],
    "dcim.devicerole": [
        {"name": "Role 1"},
        {"name": "Role 2"},
    ],
    "dcim.site": [
        {"name": "Site 1", "status": "#ref:extras.status:slug:active"},
        {"name": "Site 2", "status": "#ref:extras.status:slug:active"},
    ],
    "dcim.device": [
        {
            "name": "Device 1",
            "defaults": {
                "device_role": "#ref:dcim.devicerole:name:Role 1",
                "device_type": "#ref:dcim.devicetype:model:Model 1",
                "site": "#ref:dcim.site:name:Site 1",
            }
        },
        {
            "name": "Device 2",
            "defaults": {
                "device_role": "#ref:dcim.devicerole:name:Role 2",
                "device_type": "#ref:dcim.devicetype:model:Model 2",
                "site": "#ref:dcim.site:name:Site 2",
            }
        },
    ],
}

payload = {"data": {"json_payload": json.dumps(json_payload)}}

requests.post(f"{url}/api/extras/jobs/git.poc-jobs/intended_state/IntendedState/run/", headers=headers, json=payload)
```

## Limitations

Note, this repo is not meant to be a perfect representation of how to implement this for every environment, but rather just a simple POC on how it _could_ be done. Feel free to fork/copy this code and modify it as you see fit to your required specifications.
