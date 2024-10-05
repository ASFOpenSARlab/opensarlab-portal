def convert_to_dict(record, callback_after=None) -> dict:
    """
    Convert SqlAlchemy Row object to a dictionary

    callback_after: a callable callback function (self-contained) to apply to row dictionary after conversion, returns new obj

    """

    try:
        obj = dict(record._mapping)
    except:
        try:
            obj = dict(vars(record))
        except:
            try:
                obj = dict(record)
            except Exception as e:
                raise Exception(f"Cannot convert record {record} of type {type(record)} to dict... {e}")

    if type(obj) == 'dict':
        raise Exception(f"While record {record} of type {type(record)} can be cast as a dict, it needs to be simpler... {e}")
    
    if obj.get('_sa_instance_state', None):
        del obj['_sa_instance_state']

    if callback_after:
        obj = callback_after(obj)

    return obj
