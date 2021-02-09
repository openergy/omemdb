# Developers documentation

## Authorized fields

We allow all simple fields (List or Dicts are forbidden).

However, we created a Tuple field to replace list fields. The reason is that we want to ensure that we control
all modification on database (for link modification management). Tuple fields are immutable: __setitem__ is
necessarily called if changed.


## Link modification management

Only four methods impact links and trigger a link management workflow:

### add record

    [table].add
        [record]: .__init__ -> ._dev_link
            [record_link]: .activate
                [db]: ._dev_register_link
                  
                  

### remove

    [table]: .remove
        [record]: ._dev_unlink
            [record_link]: .deactivate
                [db]: ._dev_unregister_link & db._dev_remove_pointing_links
                    [record_link]: .deactivate
                        [record]:    ._dev_remove_link

### __setitem__
if link :

    [record]: .__setitem__
        [record_link]: .deactivate
            [db]: ._dev_unregister_link

### from_json
1. all records are added: table._dev_add(link=False, sanitize=False) => records are appended, without registering links nor checking table sanity
2. table._dev_sanitize() is called on table
3. all records of table are linked: table._dev_link() => record._dev_link()

### missing, default, allow_none:
* Never use default (it is used to specify a default value when serializing)
* Use missing instead. Use missing=None to allow null values by default
* Use allow_none when you want to allow null values, and want to specify another default 
(in this case, both allow_none and missing must be used)

### cross-validation
* For cross validation, use post_load instead of pre_load (unless you have a good reason not to)