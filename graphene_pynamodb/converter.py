from graphene import ID, Boolean, Int, List, String
from graphene.types.json import JSONString
from pynamodb import attributes
from singledispatch import singledispatch


def convert_relationship(relationship, registry):
    raise Exception(
        "PynamoDB doesn't support relationships out of the box yet %s (%s)" % (relationship, registry))
    # direction = relationship.direction
    # model = relationship.mapper.entity
    #
    # def dynamic_type():
    #     _type = registry.get_type_for_model(model)
    #     if not _type:
    #         return None
    #     if (direction == interfaces.MANYTOONE or not relationship.uselist):
    #         return Field(_type)
    #     elif (direction == interfaces.ONETOMANY or
    #                   direction == interfaces.MANYTOMANY):
    #         if is_node(_type):
    #             return PynamoConnectionField(_type)
    #         return Field(List(_type))
    #
    # return Dynamic(dynamic_type)


def convert_pynamo_composite(composite, registry):
    converter = registry.get_converter_for_composite(composite.composite_class)
    if not converter:
        try:
            raise Exception(
                "Don't know how to convert the composite field %s (%s)" %
                (composite, composite.composite_class))
        except AttributeError:
            # handle fields that are not attached to a class yet (don't have a parent)
            raise Exception(
                "Don't know how to convert the composite field %r (%s)" %
                (composite, composite.composite_class))
    return converter(composite, registry)


def _register_composite_class(cls, registry=None):
    if registry is None:
        from .registry import get_global_registry
        registry = get_global_registry()

    def inner(fn):
        registry.register_composite_converter(cls, fn)

    return inner


convert_pynamo_composite.register = _register_composite_class


@singledispatch
def convert_pynamo_attribute(type, attribute, registry=None):
    raise Exception(
        "Don't know how to convert the PynamoDB attribute %s (%s)" % (attribute, attribute.__class__))


@convert_pynamo_attribute.register(attributes.BinaryAttribute)
@convert_pynamo_attribute.register(attributes.UnicodeAttribute)
@convert_pynamo_attribute.register(attributes.UTCDateTimeAttribute)
def convert_column_to_string(type, attribute, registry=None):
    return String(description=getattr(attribute, 'attr_name'),
                  required=not (getattr(attribute, 'null', True)))


@convert_pynamo_attribute.register(attributes.NumberAttribute)
def convert_column_to_int_or_id(type, attribute, registry=None):
    if attribute.is_hash_key:
        return ID(description=attribute.attr_name, required=not attribute.null)
    else:
        return Int(description=attribute.attr_name, required=not attribute.null)


@convert_pynamo_attribute.register(attributes.BooleanAttribute)
def convert_column_to_boolean(type, attribute, registry=None):
    return Boolean(description=attribute.attr_name, required=not attribute.null)


@convert_pynamo_attribute.register(attributes.UnicodeSetAttribute)
@convert_pynamo_attribute.register(attributes.NumberSetAttribute)
@convert_pynamo_attribute.register(attributes.BinarySetAttribute)
def convert_scalar_list_to_list(type, attribute, registry=None):
    return List(String, description=attribute.attr_name)


@convert_pynamo_attribute.register(attributes.JSONAttribute)
def convert_json_to_string(type, attribute, registry=None):
    return JSONString(description=attribute.attr_name, required=not attribute.null)