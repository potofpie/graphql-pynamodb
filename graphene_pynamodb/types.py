from collections import OrderedDict
from inspect import isclass

from graphene import Field, Connection, Node, ConnectionField
from .fields import PynamoConnectionField
from graphene.relay import is_node
from graphene.types.objecttype import ObjectType, ObjectTypeOptions
from graphene.types.interface import Interface,  InterfaceOptions
from graphene.types.utils import yank_fields_from_attrs
from pynamodb.attributes import Attribute, NumberAttribute
from pynamodb.models import Model

from .converter import convert_pynamo_attribute
from .registry import Registry, get_global_registry
from .relationships import RelationshipResult
from .utils import get_key_name, connection_for_type, is_valid_pynamo_model, get_query_fields, get_model_fields
from graphene.utils.str_converters import to_snake_case


def construct_self_referenced_fields(self_referenced, registry):
    fields = OrderedDict()
    for name, field in self_referenced.items():
        converted = convert_pynamo_attribute(field, registry)
        if not converted:
            continue
        fields[name] = converted

    return fields


def get_model_fields(model, excluding=None):
    if excluding is None:
        excluding = []
    attributes = dict()

    for attr_name, attr in model.get_attributes().items():
        if attr_name in excluding:
            continue
        attributes[attr_name] = attr
    return OrderedDict(sorted(attributes.items(), key=lambda t: t[0]))


def construct_fields(model, registry, only_fields, exclude_fields):
    inspected_model = get_model_fields(model)

    fields = OrderedDict()

    for name, attribute in inspected_model.items():
        is_not_in_only = only_fields and name not in only_fields
        is_already_created = name in fields
        is_excluded = name in exclude_fields or is_already_created
        if is_not_in_only or is_excluded:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we excldue this field in exclude_fields
            continue
        converted_column = convert_pynamo_attribute(attribute, attribute, registry)
        fields[name] = converted_column

    return fields





class PynamoObjectTypeOptions(ObjectTypeOptions):
    model = None  # type: Model
    registry = None  # type: Registry
    connection = None  # type: Type[Connection]
    id = None  # type: str


class PynamoObjectType(ObjectType):
    @classmethod
    def __init_subclass_with_meta__(cls, model=None, registry=None, skip_registry=False,
                                    only_fields=(), exclude_fields=(), connection=None,
                                    use_connection=None, interfaces=(), id=None, **options):
        assert model and isclass(model) and issubclass(model, Model), (
            'You need to pass a valid PynamoDB Model in '
            '{}.Meta, received "{}".'
        ).format(cls.__name__, model)

        if not registry:
            registry = get_global_registry()

        assert isinstance(registry, Registry), (
            'The attribute registry in {} needs to be an instance of '
            'Registry, received "{}".'
        ).format(cls.__name__, registry)

        pynamo_fields = yank_fields_from_attrs(
            construct_fields(model, registry, only_fields, exclude_fields),
            _as=Field,
        )

        if use_connection is None and interfaces:
            use_connection = any((issubclass(interface, Node) for interface in interfaces))

        if use_connection and not connection:
            # We create the connection automatically
            connection = Connection.create_type('{}Connection'.format(cls.__name__), node=cls)

        if connection is not None:
            assert issubclass(connection, Connection), (
                "The connection must be a Connection. Received {}"
            ).format(connection.__name__)

        _meta = PynamoObjectTypeOptions(cls)
        _meta.model = model
        _meta.registry = registry
        _meta.fields = pynamo_fields
        _meta.connection = connection
        _meta.id = id or 'id'

        super(PynamoObjectType, cls).__init_subclass_with_meta__(_meta=_meta, interfaces=interfaces, **options)

        if not skip_registry:
            registry.register(cls)

    @classmethod
    def is_type_of(cls, root, info):
        if isinstance(root, RelationshipResult) and root.__wrapped__ == cls._meta.model:
            return True
        return isinstance(root, cls._meta.model)

    @classmethod
    def get_node(cls, info, id):
        if isinstance(getattr(cls._meta.model, get_key_name(cls._meta.model)), NumberAttribute):
            return cls._meta.model.get(int(id))
        else:
            return cls._meta.model.get(id)

    def resolve_id(self, info):
        graphene_type = info.parent_type.graphene_type
        if is_node(graphene_type):
            return getattr(self, get_key_name(graphene_type._meta.model))

    @classmethod
    def get_connection(cls):
        return connection_for_type(cls)








def create_graphene_generic_class(object_type, option_type):
    class MongoengineGenericObjectTypeOptions(option_type):

        model = None
        registry = None  # type: Registry
        connection = None
        filter_fields = ()
        non_required_fields = ()
        order_by = None

    class GrapheneMongoengineGenericType(object_type):
        @classmethod
        def __init_subclass_with_meta__(
            cls,
            model=None,
            registry=None,
            skip_registry=False,
            only_fields=(),
            required_fields=(),
            exclude_fields=(),
            non_required_fields=(),
            filter_fields=None,
            connection=None,
            connection_class=None,
            use_connection=None,
            connection_field_class=None,
            interfaces=(),
            _meta=None,
            order_by=None,
            **options
        ):

            assert is_valid_pynamo_model(model), (
                "The attribute model in {}.Meta must be a valid Mongoengine Model. "
                'Received "{}" instead.'
            ).format(cls.__name__, type(model))

            if not registry:
                registry = get_global_registry()
                # input objects shall be registred in a separated registry
                # if issubclass(cls, InputObjectType):
                #     registry = get_inputs_registry()
                # else:

            assert isinstance(registry, Registry), (
                "The attribute registry in {}.Meta needs to be an instance of "
                'Registry({}), received "{}".'
            ).format(object_type, cls.__name__, registry)

            converted_fields, self_referenced = construct_fields(
                model, registry, only_fields, exclude_fields, non_required_fields
            )
            mongoengine_fields = yank_fields_from_attrs(
                converted_fields, _as=Field
            )
            if use_connection is None and interfaces:
                use_connection = any(
                    (issubclass(interface, Node) for interface in interfaces)
                )

            if use_connection and not connection:
                # We create the connection automatically
                if not connection_class:
                    connection_class = Connection

                connection = connection_class.create_type(
                    "{}Connection".format(cls.__name__), node=cls
                )

            if connection is not None:
                assert issubclass(connection, Connection), (
                    "The attribute connection in {}.Meta must be of type Connection. "
                    'Received "{}" instead.'
                ).format(cls.__name__, type(connection))

            if connection_field_class is not None:
                assert issubclass(connection_field_class, ConnectionField), (
                    "The attribute connection_field_class in {}.Meta must be of type graphene.ConnectionField. "
                    'Received "{}" instead.'
                ).format(cls.__name__, type(connection_field_class))
            else:
                connection_field_class = PynamoConnectionField

            if _meta:
                assert isinstance(_meta, MongoengineGenericObjectTypeOptions), (
                    "_meta must be an instance of MongoengineGenericObjectTypeOptions, "
                    "received {}"
                ).format(_meta.__class__)
            else:
                _meta = MongoengineGenericObjectTypeOptions(option_type)

            _meta.model = model
            _meta.registry = registry
            _meta.fields = mongoengine_fields
            _meta.filter_fields = filter_fields
            _meta.connection = connection
            _meta.connection_field_class = connection_field_class
            # Save them for later
            _meta.only_fields = only_fields
            _meta.required_fields = required_fields
            _meta.exclude_fields = exclude_fields
            _meta.non_required_fields = non_required_fields
            _meta.order_by = order_by

            super(GrapheneMongoengineGenericType, cls).__init_subclass_with_meta__(
                _meta=_meta, interfaces=interfaces, **options
            )

            if not skip_registry:
                registry.register(cls)
                # Notes: Take care list of self-reference fields.
                converted_fields = construct_self_referenced_fields(
                    self_referenced, registry
                )
                if converted_fields:
                    mongoengine_fields = yank_fields_from_attrs(
                        converted_fields, _as=Field
                    )
                    cls._meta.fields.update(mongoengine_fields)
                    registry.register(cls)

        @classmethod
        def rescan_fields(cls):
            """Attempts to rescan fields and will insert any not converted initially"""

            converted_fields, self_referenced = construct_fields(
                cls._meta.model,
                cls._meta.registry,
                cls._meta.only_fields,
                cls._meta.exclude_fields,
                cls._meta.non_required_fields
            )

            mongoengine_fields = yank_fields_from_attrs(
                converted_fields, _as=Field
            )

            # The initial scan should take precedence
            for field in mongoengine_fields:
                if field not in cls._meta.fields:
                    cls._meta.fields.update({field: mongoengine_fields[field]})
            # Self-referenced fields can't change between scans!

        @classmethod
        def is_type_of(cls, root, info):
            if isinstance(root, cls):
                return True
            # XXX: idk what this is
            # if isinstance(root, mongoengine.GridFSProxy):
            #     return True
            if not is_valid_pynamo_model(type(root)):
                raise Exception(('Received incompatible instance "{}".').format(root))
            return isinstance(root, cls._meta.model)

        @classmethod
        def get_node(cls, info, id):
            required_fields = list()
            for field in cls._meta.required_fields:
                if field in cls._meta.model._fields_ordered:
                    required_fields.append(field)
            for field in get_query_fields(info):
                if to_snake_case(field) in cls._meta.model._fields_ordered:
                    required_fields.append(to_snake_case(field))
            required_fields = list(set(required_fields))
            return cls._meta.model.objects.no_dereference().only(*required_fields).get(pk=id)

        def resolve_id(self, info):
            return str(self.id)

    return GrapheneMongoengineGenericType, MongoengineGenericObjectTypeOptions

MongoengineInterfaceType, MongoengineInterfaceTypeOptions = create_graphene_generic_class(Interface, InterfaceOptions)
