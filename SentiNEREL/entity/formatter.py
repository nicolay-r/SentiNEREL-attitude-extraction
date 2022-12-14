from arekit.common.entities.base import Entity
from arekit.common.entities.str_fmt import StringEntitiesFormatter
from arekit.common.entities.types import OpinionEntityType

from SentiNEREL.entity.helper import EntityHelper


class CustomTypedEntitiesFormatter(StringEntitiesFormatter):
    """ Отображение типов вместо значения сущностей для всех именованных сущностей.
    """
    def to_string(self, original_value, entity_type):
        return EntityHelper.format(original_value)


class CustomMaskedEntitiesFormatter(StringEntitiesFormatter):
    """ Форматирование сущностей. Было принято решение использовать тип сущности в качетстве значений.
        Поскольку тексты русскоязычные, то и типы были руссифицированы из соображений более удачных embeddings.

        В целях возможности применения модели к сырым текстам, с моей стороны предлагается форматирование только
        тех сущностей текста, которые могут быть распознаны существующими NER.

        Мое предположение таково, что не все типы, которые размечены в коллекции, могут быть распознаны существующими
        предобученными моделями NER (например BERT-OntoNotes, как одна из наиболее обширных по числу тегов разметки,
         содержит подмножество типов).
    """

    def __init__(self, subject_fmt='[субъект]', object_fmt="[объект]"):
        self.__subject_fmt = subject_fmt
        self.__object_fmt = object_fmt

    def to_string(self, original_value, entity_type):
        assert(isinstance(original_value, Entity))
        assert(isinstance(entity_type, OpinionEntityType))

        if entity_type == OpinionEntityType.Other:
            return EntityHelper.format(original_value)
        elif entity_type == OpinionEntityType.Object or entity_type == OpinionEntityType.SynonymObject:
            return self.__object_fmt
        elif entity_type == OpinionEntityType.Subject or entity_type == OpinionEntityType.SynonymSubject:
            return self.__subject_fmt

        return None
