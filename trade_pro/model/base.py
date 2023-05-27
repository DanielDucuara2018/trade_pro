from typing import Type, TypeVar, Union

from sqlalchemy.orm import registry

from trade_pro import db
from trade_pro.errors import NotDataFound

T = TypeVar("T", bound="Base")
mapper_registry = registry()


class Base:
    @classmethod
    def find(cls: Type[T], **filters) -> list[T]:
        query = db.session.query(cls)

        for_equality = True
        for key, value in filters.items():
            if key.startswith("!"):
                key = key[1:]
                for_equality = False

            column = getattr(cls, key)

            if for_equality:
                query = query.filter(column == value)
            else:
                query = query.filter(column != value)

        return query.all()

    @classmethod
    def get(cls: Type[T], **kwargs) -> Union[T, list[T]]:
        query = db.session.query(cls)
        if kwargs:
            result = query.get(kwargs)
            if not result:
                raise NotDataFound(key=kwargs, messages="Not data found in DB")
        else:
            result = query.all()
        return result

    def update(self: T, **kwargs) -> T:
        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)
        db.session.commit()
        return self

    def create(self: T) -> T:
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self: T) -> T:
        db.session.delete(self)
        db.session.commit()
        return self
