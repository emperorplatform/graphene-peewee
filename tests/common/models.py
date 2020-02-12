from peewee import (
    CharField,
    IntegerField,
    ForeignKeyField,
    Model,
    SqliteDatabase,
    MySQLDatabase
)

db = SqliteDatabase(':memory:', pragmas=(('foreign_keys', 'on'),))


class BaseModel(Model):

    class Meta:
        database = db


class Author(BaseModel):

    name = CharField()
    rating = IntegerField()


class Book(BaseModel):

    name = CharField()
    year = IntegerField()
    author = ForeignKeyField(Author)

class Page(BaseModel):

    chapter = IntegerField()
    number = IntegerField()
    book = ForeignKeyField(Book)

db.create_tables([
    Author,
    Book,
    Page,
], safe=True)