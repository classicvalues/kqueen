from kqueen.storages.etcd import IdField
from kqueen.storages.etcd import JSONField
from kqueen.storages.etcd import Model
from kqueen.storages.etcd import ModelMeta
from kqueen.storages.etcd import RelationField
from kqueen.storages.etcd import SecretField
from kqueen.storages.etcd import StringField

import pytest


def create_model(required=False):
    class TestModel(Model, metaclass=ModelMeta):
        id = IdField(required=required)
        string = StringField(required=required)
        json = JSONField(required=required)
        secret = SecretField(required=required)
        relation = RelationField(required=required)

    return TestModel


model_kwargs = {'string': 'abc123', 'json': {'a': 1, 'b': 2, 'c': 'tri'}, 'secret': 'pass'}
model_fields = ['id', 'string', 'json', 'secret', 'relation']
model_serialized = '{"string": "abc123", "json": "{\\"a\\": 1, \\"b\\": 2, \\"c\\": \\"tri\\"}", "secret": "pass"}'


@pytest.fixture
def create_object(**kwargs):
    model = create_model()
    if kwargs:
        use_kwargs = kwargs
    else:
        use_kwargs = model_kwargs

    return model(**use_kwargs)


class TestModelInit:
    def setup(self):
        self.model = create_model()
        self.obj = self.model(**model_kwargs)

    @pytest.mark.parametrize('field_name,field_value', model_kwargs.items())
    def test_init_string(self, field_name, field_value):
        """Initialization of new models is properly setting properties"""

        kwargs = {field_name: field_value}
        obj = self.model(**kwargs)

        assert getattr(obj, field_name) == field_value

    @pytest.mark.parametrize('attr', model_fields)
    @pytest.mark.parametrize('group', ['', '_'])
    def test_field_property_getters(self, attr, group):
        attr_name = '{}{}'.format(group, attr)

        assert hasattr(self.obj, attr_name)


class TestSave:
    def setup(self):
        model = create_model(required=True)
        self.obj = model()

    def test_model_invalid(self):
        assert not self.obj.validate()

    def test_save_raises(self):
        with pytest.raises(ValueError, match='Validation for model failed'):
            self.obj.save()

    def test_save_skip_validation(self):
        assert self.obj.save(validate=False)


class TestModelAddId:
    def test_id_added(self, create_object):
        obj = create_object

        assert obj.id is None
        assert obj.verify_id()
        assert obj.id is not None

        create_object.save()


class TestRequiredFields:
    @pytest.mark.parametrize('required', [True, False])
    def test_required(self, required):
        model = create_model(required=required)
        obj = model(**model_kwargs)

        assert obj.validate() != required


class TestGetFieldNames:
    def test_get_field_names(self, create_object):
        field_names = create_object.__class__.get_field_names()
        req = model_fields

        assert field_names == req

    def test_get_dict(self, create_object):
        print(create_object.__dict__)
        print(create_object.get_dict())


class TestFieldSetGet:
    """Validate getters and setters for fields"""
    @pytest.mark.parametrize('field_name', model_kwargs.keys())
    def test_get_fields(self, field_name, create_object):
        at = getattr(create_object, field_name)
        req = model_kwargs[field_name]

        assert at == req

    @pytest.mark.parametrize('field_name', model_kwargs.keys())
    def test_set_fields(self, field_name):
        model_class = create_model()
        obj = model_class()
        setattr(obj, field_name, model_kwargs[field_name])

        print(obj.get_dict())

        assert getattr(obj, field_name) == model_kwargs[field_name]
        assert obj.get_dict()[field_name] == model_kwargs[field_name]
        assert getattr(obj, '_{}'.format(field_name)).get_value() == model_kwargs[field_name]


class TestSerialization:
    """Serialization and deserialization create same objects"""

    def test_serizalization(self, create_object):
        serialized = create_object.serialize()

        assert serialized == model_serialized

    def test_deserialization(self, create_object):
        object_class = create_object.__class__
        create_object.save()
        new_object = object_class.deserialize(create_object.serialize())

        assert new_object.get_dict() == create_object.get_dict()


class TestDuplicateId:
    def setup(self):
        self.model = create_model()

        self.obj1_kwargs = {'string': 'object 1', 'json': {'a': 1, 'b': 2, 'c': 'tri'}, 'secret': 'pass'}
        self.obj2_kwargs = {'string': 'object 2', 'json': {'a': 1, 'b': 2, 'c': 'tri'}, 'secret': 'pass'}

    def test_with_save(self):
        """"Save object are not same"""
        obj1 = self.model(**self.obj1_kwargs)
        obj2 = self.model(**self.obj2_kwargs)

        assert obj1 != obj2

        obj1.save()
        obj2.save()

        print(obj1.get_dict())
        print(obj2.get_dict())

        assert obj1.id != obj2.id

#
# Relation Field
#


class TestRelationField:
    def setup(self):
        self.obj1 = create_object(name='obj1')
        self.obj2 = create_object(name='obj2')

        self.obj1.save()
        self.obj2.save()

        self.obj1.relation = self.obj2

    def test_relation_attrs(self):
        assert self.obj1.relation == self.obj2
        assert self.obj1._relation.value == self.obj2

    def test_relation_serialization(self):
        ser = self.obj1._relation.serialize()
        req = '{model_name}:{object_id}'.format(
            model_name=self.obj2.__class__.__name__,
            object_id=self.obj2.id
        )

        assert ser == req

    def test_relation_loading(self):
        self.obj1.save()

        loaded = self.obj1.__class__.load(self.obj1.id)
        print(loaded.get_dict())
