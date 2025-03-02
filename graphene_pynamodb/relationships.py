from pynamodb.attributes import Attribute, NumberAttribute
from pynamodb.constants import STRING, MAP, NUMBER, LIST, STRING_SET
from pynamodb.models import Model
from six import string_types
from wrapt import ObjectProxy

from graphene_pynamodb.utils import get_key_name


class RelationshipResult(ObjectProxy):
    def __init__(self, key_name, key, obj):
        if isinstance(obj, type) and not issubclass(obj, Model):
            raise TypeError("Invalid class passed to RelationshipResult, expected a Model class, got %s" % type(obj))
        super(RelationshipResult, self).__init__(obj)
        self._self_key = key
        self._self_key_name = key_name
        self._self_model = obj

    def __getattr__(self, name):
        if name == self._self_key_name:
            return self._self_key
        if not name.startswith('_') and isinstance(self.__wrapped__, type):
            self.__wrapped__ = self._self_model.get(self._self_key)
        return super(RelationshipResult, self).__getattr__(name)

    def __eq__(self, other):
        return isinstance(other, self._self_model) and self._self_key == getattr(other, self._self_key_name)

    def __ne__(self, other):
        return not self.__eq__(other)


class RelationshipResultList(list):
    def __init__(self, hash_key_name, model, keys):
        self._hash_key_name = hash_key_name
        self._model = model
        self._keys = keys
        super(RelationshipResultList, self).__init__(keys)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return RelationshipResultList(self._hash_key_name, self._model, self._keys[item])

        return RelationshipResult(self._hash_key_name, self._keys[item], self._model)

    def __getslice__(self, i, j):
        return RelationshipResultList(self._hash_key_name, self._model, self._keys[i:j])

    def __iter__(self):
        for key in self._keys:
            yield RelationshipResult(self._hash_key_name, key, self._model)

    def resolve(self):
        models = dict((getattr(entity, self._hash_key_name), entity) for entity in self._model.batch_get(self._keys))
        return [models[key] for key in self._keys]


class Relationship(Attribute):
    _models = None

    @classmethod
    def sub_classes(cls, klass):
        return klass.__subclasses__() + [g for s in klass.__subclasses__() for g in Relationship.sub_classes(s)]

    @classmethod
    def get_model(cls, model_name):
        # Resolve a model name into a model class by looking in all Model subclasses
        if not Relationship._models:
            Relationship._models = Relationship.sub_classes(Model)
        return next((model for model in Relationship._models if model.__name__ == model_name), None)

    def __init__(self, model, lazy=True, **args):
        if not isinstance(model, string_types) and not issubclass(model, Model):
            raise TypeError("Expected PynamoDB Model argument, got: %s " % model.__class__.__name__)

        Attribute.__init__(self, **args)
        self._model = model
        self._lazy = lazy
        self._hash_key_name = None

    @property
    def hash_key_name(self):
        if not self._hash_key_name:
            self._hash_key_name = get_key_name(self.model)
        return self._hash_key_name

    @property
    def model(self):
        if isinstance(self._model, string_types):
            self._model = Relationship.get_model(self._model)

        return self._model


class OneToOne(Relationship):
    attr_type = STRING

    def serialize(self, model):
        return str(getattr(model, self.hash_key_name))

    def deserialize(self, hash_key):
        if isinstance(getattr(self.model, self.hash_key_name), NumberAttribute):
            hash_key = int(hash_key)

        if self._lazy:
            return RelationshipResult(self.hash_key_name, hash_key, self.model)
        else:
            return self.model.get(hash_key)


class OneToMany(Relationship):
    attr_type = LIST

    def serialize(self, models):
        key_type = MAP[getattr(self.model, self.hash_key_name).attr_type]
        return [{key_type: str(getattr(model, self.hash_key_name))} for model in models]

    def deserialize(self, hash_keys):
        if hash_keys and isinstance(hash_keys[0], dict):
            key_type = list(hash_keys[0].keys())[0]
            if key_type == NUMBER:
                hash_keys = [int(hash_key[key_type]) for hash_key in hash_keys]
            else:
                hash_keys = [hash_key[key_type] for hash_key in hash_keys]
        else:
            if isinstance(getattr(self.model, self.hash_key_name), NumberAttribute):
                hash_keys = [hash_key for hash_key in hash_keys]

        if self._lazy:
            return RelationshipResultList(self.hash_key_name, self.model, hash_keys)
        else:
            return self.model.batch_get(hash_keys)

    def get_value(self, value):
        # we need this for legacy compatibility.
        # deserialize previous string set implementation
        if isinstance(value, dict) and STRING_SET in value:
            return value[STRING_SET]

        return value[LIST]
