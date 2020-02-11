from peewee import ForeignKeyField, SQL, NodeList
import peewee
from playhouse.shortcuts import model_to_dict
from graphene import Int, Dynamic, NonNull
from graphene.types.generic import GenericScalar

from .queries import filter
from .fields import PeeweeNodeField, PeeweeConnectionField
from .types import PeeweeMutation

def _execute_query(query):
    database = query._database(query)
    cursor = db.execute_sql(query)

    return cursor

DELIM = '__'
FILTERS_FIELD = 'filters'
DATA_FIELD = 'data'
RELATED_FIELD = 'related'
AFFECTED_FIELD = 'affected'

def get_backref_by_name(model, name):
    return next((backref for backref in model._meta.backrefs if backref.backref == name), None)


def prepare_filters(query, filters):
    if isinstance(filters, int):
        filters = {query.model._meta.primary_key.name: filters}
    return filters


def filter_query(query, filters):
    if filters is not None:
        if isinstance(filters, dict) and filters:
            query = filter(query, filters)
    return query


def is_filter_deep(model, filter_key):
    if DELIM in filter_key:
        outer_field, inner_field = filter_key.split(DELIM, 1)
        field = getattr(model, outer_field, None)
        if field is not None and isinstance(field, ForeignKeyField):
            if getattr(field.rel_model, inner_field.split(DELIM, 1)[0], None):
                return True
    return False


def filter_query_with_subqueries(query, filters):
    """ For queries that does not support joining """
    plain_filters = {}
    subquery_filters = {}
    model = query.model
    filters = prepare_filters(query, filters)
    for key, val in filters.items():
        if is_filter_deep(model, key):
            join_field, join_filter_key = key.split(DELIM, 1)
            subquery_filters.setdefault(join_field, {}).update({join_filter_key: val})
        else:
            plain_filters[key] = val
    query = filter_query(query, plain_filters)
    for key, val in subquery_filters.items():
        field = getattr(model, key)
        rel_model = field.rel_model
        query = query.where(NodeList([
            SQL('EXISTS'),
            rel_model.select(SQL('1')).filter(**val).where(field == rel_model._meta.primary_key)
        ]))
    return query


def arguments_from_fields(fields, model):
    PeeweeModelField = Dynamic
    arguments = {}
    for name, field in fields.items():
        if isinstance(field, PeeweeModelField):
            if get_backref_by_name(model, name):
                arg = GenericScalar().Argument()
            else:
                arg = Int().Argument()
        elif isinstance(field.type, NonNull):
            arg = field.type.of_type().Argument()
        else:
            arg = field.type().Argument() # TODO: get rid of strange `NotNull is not callable` warning
        arguments[name] = arg
    return arguments


def split_data(model, data):
    plain_data = {}
    related_data = {}
    for key, val in data.items():
        dst = related_data if get_backref_by_name(model, key) else plain_data
        dst[key] = val
    return plain_data, related_data


class BaseMutation(PeeweeMutation):

    @classmethod
    def generate(cls, node_class, connection_class, arguments={}, returns={}):
        args_class = type('Arguments', (), arguments)
        meta_class = type('Meta', (), {'model': node_class._meta.model,
                                       'db': node_class._meta.db})
        attrs = {meta_class.__name__: meta_class,
                 args_class.__name__: args_class}
        attrs.update(returns)
        return type('{}{}'.format(node_class.__name__, cls.__name__), (cls,), attrs)

    @classmethod
    def set_related(cls, objs, related_data):
        model = cls._meta.model
        db = cls._meta.db
        for set_field_name, related_objs in related_data.items():
            field = getattr(model, set_field_name)
            related_model = field.rel_model
            related_field = field.field
            obj_pks = [obj if isinstance(obj, int) else obj._pk for obj in objs]
            delete_query = (related_model.delete()
                            .where(related_field.in_(obj_pks)))
            final_related_data = []
            for obj_pk in obj_pks:
                for related_obj in related_objs:
                    related_obj.pop(related_model._meta.primary_key.name, None)
                    final_related_obj = related_obj.copy()
                    final_related_obj[related_field.name] = obj_pk
                    final_related_data.append(final_related_obj)
            if final_related_data:
                related_model.insert_many(final_related_data).execute()

    @classmethod
    def clone_entity_tree(cls, obj, fields=[], new_data={}):
        # TODO: Simplify clone args (`fields` variable)
        db = cls._meta.db
        model = obj._meta.model
        pk_field = model._meta.primary_key
        data = model_to_dict(obj, recurse=False)
        data.pop(pk_field.name)
        env = {pk_field.name: obj._pk}
        new_data = new_data.copy()
        child_data = {}
        for key, val in tuple(new_data.items()):
            if key in map(
                    lambda x: list(x.keys())[0] if isinstance(x, dict) else x,
                    fields):
                child_data[key] = new_data.pop(key)
            elif isinstance(val, list):
                new_data[key] = ''.join(val).format(**env)
        data.update(new_data)
        
        new_obj = model(**data)
        pk = model.insert(**dict(new_obj.__data__)).execute()
        if new_obj._pk is None:
            new_obj._pk = pk

        for field in fields:
            child_fields = []
            if isinstance(field, dict):
                for key, val in field.items():
                    field = key
                    child_fields = val
            fkey = get_backref_by_name(model, field)
            rel_objs = getattr(obj, field)
            child_new_data = {fkey.name: new_obj._pk}
            child_new_data.update(child_data.get(field, {}))
            for rel_obj in rel_objs:
                cls.clone_entity_tree(rel_obj, child_fields, child_new_data)
        return new_obj

    class Meta:
        abstract = True


class CreateOneMutation(BaseMutation):

    @classmethod
    def generate(cls, node_class, connection_class, arguments={}, returns={}):
        args = arguments_from_fields(node_class._meta.fields, node_class._meta.model)
        args.update(arguments)
        attrs = {AFFECTED_FIELD: PeeweeNodeField(node_class)}
        attrs.update(returns)
        return super().generate(node_class, connection_class, args, attrs)

    @classmethod
    def mutate(cls, instance, info, **args):
        model = cls._meta.model
        db = cls._meta.db
        plain_data, related_data = split_data(model, args)

        obj = model(**plain_data)
        pk = model.insert(**dict(obj.__data__)).execute()

        if obj._pk is None:
            obj._pk = pk

        cls.set_related([obj], related_data)
        return cls(**{AFFECTED_FIELD: obj})

    class Meta:
        abstract = True


class CreateManyMutation(BaseMutation):

    @classmethod
    def generate(cls, node_class, connection_class, arguments={}, returns={}):
        args = {DATA_FIELD: GenericScalar()}
        args.update(arguments)
        attrs = {AFFECTED_FIELD: PeeweeConnectionField(connection_class)}
        attrs.update(returns)
        return super().generate(node_class, connection_class, args, attrs)

    @classmethod
    def last_insert_id_async(cls, cursor):
        return cursor.fetchall()

    @classmethod
    def mutate(cls, instance, info, **args):
        model = cls._meta.model
        db = cls._meta.db
        data = args.get(DATA_FIELD, [])
        # TODO: detect if PKs returning is requested or required by `set_related`
        plain_data_list = []
        related_data_list = []
        for obj in data:
            plain_data, related_data = split_data(model, obj)
            plain_data_list.append(plain_data)
            related_data_list.append(related_data)

        rows = []
        with db.atomic() as txn:
            for row in plain_data_list:
                rows.append(model.insert(row).execute())

        inserted_pks = map(lambda row: row, rows)
        inserted_objects = []
        for i, inserted_pk in enumerate(inserted_pks):
            model_data = dict(plain_data_list[i])
            model_data[model._meta.primary_key.name] = inserted_pk
            obj = model(**model_data)
            inserted_objects.append(obj)
            cls.set_related([obj], related_data_list[i])
        return cls(**{AFFECTED_FIELD: inserted_objects})

    class Meta:
        abstract = True


class UpdateOneMutation(BaseMutation):

    @classmethod
    def generate(cls, node_class, connection_class, arguments={}, returns={}):
        args = arguments_from_fields(node_class._meta.fields, node_class._meta.model)
        args.update(arguments)
        attrs = {AFFECTED_FIELD: PeeweeNodeField(node_class)}
        attrs.update(returns)
        return super().generate(node_class, connection_class, args, attrs)

    @classmethod
    def mutate(cls, instance, info, **args):
        model = cls._meta.model
        db = cls._meta.db
        args_copy = args.copy()
        pk_field = model._meta.primary_key
        pk_value = args_copy.pop(pk_field.name)
        plain_data, related_data = split_data(model, args_copy)
        if plain_data:
            query = model.update(**plain_data)
            query = filter_query_with_subqueries(query, pk_value).execute()
        # TODO: check if it is requested
                
        if isinstance(model, peewee.Query):
            query = model
            model = query.model
        else:
            query = model.select()
            model = model
        args = () 
        kwargs = {pk_field.name: pk_value}

        conditions = list(args) + [(getattr(model, k) == v)
                                   for k, v in kwargs.items()]

        if conditions:
            result = query.where(*conditions).execute()
        else:
            result = query.execute()

        try:
            obj = list(result)[0]
        except IndexError:
            raise model.DoesNotExist

        cls.set_related([obj], related_data)
        return cls(**{AFFECTED_FIELD: obj})

    class Meta:
        abstract = True


class UpdateManyMutation(BaseMutation):

    @classmethod
    def generate(cls, node_class, connection_class, arguments={}, returns={}):
        args = {FILTERS_FIELD: GenericScalar(), DATA_FIELD: GenericScalar()}
        args.update(arguments)
        attrs = {AFFECTED_FIELD: PeeweeConnectionField(connection_class)}
        attrs.update(returns)
        return super().generate(node_class, connection_class, args, attrs)

    @classmethod
    def mutate(cls, instance, info, **args):
        model = cls._meta.model
        db = cls._meta.db
        data = args.get(DATA_FIELD, {})
        filters = args.get(FILTERS_FIELD)
        plain_data, related_data = split_data(model, data)
        if plain_data:
            query = model.update(**plain_data)
            query = filter_query_with_subqueries(query, filters).execute()
        # FIXME: After update select results could be different cause changed data could interfere with filters
        # TODO: check if it is requested
        select_query = model.select()
        result = filter(select_query, filters).execute()
        cls.set_related(result, related_data)
        # TODO: Seems like list conversion was fixed in peewee>=0.5.10, check it out
        return cls(**{AFFECTED_FIELD: result})

    class Meta:
        abstract = True


class DeleteOneMutation(BaseMutation):

    @classmethod
    def generate(cls, node_class, connection_class, arguments={}, returns={}):
        pk_field_name = node_class._meta.model._meta.primary_key.name
        args = {pk_field_name: node_class._meta.fields[pk_field_name].type.Argument()}
        args.update(arguments)
        attrs = {AFFECTED_FIELD: PeeweeNodeField(node_class)}
        attrs.update(returns)
        return super().generate(node_class, connection_class, args, attrs)

    @classmethod
    def mutate(cls, instance, info, **args):
        model = cls._meta.model
        db = cls._meta.db
        pk_field = model._meta.primary_key
        pk_value = args.get(pk_field.name)
        assert pk_value is not None
        query = model.delete()
        query = filter_query_with_subqueries(query, pk_value).execute()
        return cls(**{AFFECTED_FIELD: model(**{pk_field.name: pk_value})})

    class Meta:
        abstract = True


class DeleteManyMutation(BaseMutation):

    @classmethod
    def generate(cls, node_class, connection_class, arguments={}, returns={}):
        args = {FILTERS_FIELD: GenericScalar()}
        args.update(arguments)
        attrs = {AFFECTED_FIELD: PeeweeConnectionField(connection_class)}
        attrs.update(returns)
        return super().generate(node_class, connection_class, args, attrs)

    @classmethod
    def mutate(cls, instance, info, **args):
        model = cls._meta.model
        db = cls._meta.db
        filters = args.get(FILTERS_FIELD)
        query = model.delete()
        total = filter_query_with_subqueries(query, filters).execute()
        # TODO: Add .returning() when it will be supported
        return cls(**{AFFECTED_FIELD: [model() for _ in range(total)]})

    class Meta:
        abstract = True


class CloneOneMutation(BaseMutation):

    @classmethod
    def generate(cls, node_class, connection_class, arguments={}, returns={}):
        pk_field_name = node_class._meta.model._meta.primary_key.name
        args = {pk_field_name: node_class._meta.fields[pk_field_name].type.Argument(),
                RELATED_FIELD: GenericScalar(),
                DATA_FIELD: GenericScalar()}
        args.update(arguments)
        attrs = {AFFECTED_FIELD: PeeweeNodeField(node_class)}
        attrs.update(returns)
        return super().generate(node_class, connection_class, args, attrs)

    @classmethod
    def mutate(cls, instance, info, **args):
        model = cls._meta.model
        db = cls._meta.db
        pk_field = model._meta.primary_key
        pk_value = args.get(pk_field.name)
        related = args.get(RELATED_FIELD, [])
        data = args.get(DATA_FIELD, {})
        
        if isinstance(model, peewee.Query):
            query = model
            model = query.model
        else:
            query = model.select()
            model = model
        args = ()
        kwargs = {pk_field.name: pk_value}

        conditions = list(args) + [(getattr(model, k) == v)
                                   for k, v in kwargs.items()]
        if conditions:
            query = query.where(*conditions)

        try:
            obj = query[0]
        except IndexError:
            raise model.DoesNotExist

        new_obj = cls.clone_entity_tree(obj, related, data)
        return cls(**{AFFECTED_FIELD: new_obj})

    class Meta:
        abstract = True
