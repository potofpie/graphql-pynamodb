import json
from typing import Tuple
from inspect import isclass
from graphql_relay import from_global_id, to_global_id
from pynamodb.attributes import Attribute
from pynamodb.models import Model
from collections import OrderedDict




import graphene

MODEL_KEY_REGISTRY = {}

def get_model_fields(model, excluding=None):
    excluding = excluding or []
    attributes = dict()
    for attr_name, attr in model._fields.items():
        if attr_name in excluding:
            continue
        attributes[attr_name] = attr
    return OrderedDict(sorted(attributes.items()))


def ast_to_dict(node, include_loc=False):
    from graphql import NodeField
    if isinstance(node, NodeField):
        d = {"kind": node.__class__.__name__}
        if hasattr(node, "keys"):
            for field in node.keys:
                d[field] = ast_to_dict(getattr(node, field), include_loc)

        if include_loc and hasattr(node, "loc") and node.loc:
            d["loc"] = {"start": node.loc.start, "end": node.loc.end}

        return d

    elif isinstance(node, list):
        return [ast_to_dict(item, include_loc) for item in node]

    return node



def get_query_fields(info):
    """A convenience function to call collect_query_fields with info
    Args:
        info (ResolveInfo)
    Returns:
        dict: Returned from collect_query_fields
    """

    fragments = {}
    node = ast_to_dict(info.field_nodes[0])

    for name, value in info.fragments.items():
        fragments[name] = ast_to_dict(value)

    query = collect_query_fields(node, fragments)
    if "edges" in query:
        return query["edges"]["node"].keys()
    return query


def is_valid_pynamo_model(model): 
    return model and isclass(model) and issubclass(model, Model)

def get_key_name(model):
    if not issubclass(model, Model):
        raise TypeError("Invalid type passed to get_key_name: %s" % model.__class__)

    if model in MODEL_KEY_REGISTRY:
        return MODEL_KEY_REGISTRY[model]

    for attr in model.get_attributes().values():
        if isinstance(attr, Attribute) and attr.is_hash_key:
            MODEL_KEY_REGISTRY[model] = attr.attr_name
            return attr.attr_name


def connection_for_type(_type):
    class Connection(graphene.relay.Connection):
        total_count = graphene.Int()

        class Meta:
            name = _type._meta.name + "Connection"
            node = _type

        def resolve_total_count(self, args, context, info):
            return self.total_count if hasattr(self, "total_count") else len(self.edges)

    return Connection


def to_cursor(item: Model) -> str:
    data = {}  # this will be same as last_evaluated_key returned by PageIterator
    for name, attr in item.get_attributes().items():
        if attr.is_hash_key or attr.is_range_key:
            data[name] = item._serialize_value(attr, getattr(item, name))
    return to_global_id(type(item).__name__, json.dumps(data))


def from_cursor(cursor: str) -> Tuple[str, dict]:
    model, data = from_global_id(cursor)
    return model, json.loads(data)
