from arekit.common.entities.base import Entity
from arekit.common.entities.types import OpinionEntityType

from entity.helper import EntityHelper


def is_entity_ignored(entity, e_type):
    """ субъектом всегда может быть только:
            [PERSON, ORGANIZATION, COUNTRY, PROFESSION]
        — объектом могут быть видимо все типы.
    """
    assert(isinstance(entity, Entity))
    assert(isinstance(e_type, OpinionEntityType))

    supported = [EntityHelper.PERSON, EntityHelper.ORGANIZATION, EntityHelper.COUNTRY, EntityHelper.PROFESSION]

    if e_type == OpinionEntityType.Subject:
        return entity.Type not in supported
    if e_type == OpinionEntityType.Object:
        return entity.Type not in supported
    else:
        return True
