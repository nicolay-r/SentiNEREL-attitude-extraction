from arekit.common.entities.collection import EntityCollection
from arekit.common.labels.str_fmt import StringLabelsFormatter
from arekit.contrib.source.brat.annot import BratAnnotationParser
from arekit.contrib.source.brat.news import BratNews
from arekit.contrib.source.brat.sentences_reader import BratDocumentSentencesReader

from SentiNEREL.entities import CollectionEntityCollection
from SentiNEREL.io_utils import CollectionIOUtils, CollectionVersions
from SentiNEREL.opinions.converter import CollectionOpinionConverter


class SentiNERELDocReader(object):

    @staticmethod
    def read_text_opinions(filename, doc_id, entities, version, label_formatter, keep_any_type):
        assert(isinstance(filename, str))
        assert(isinstance(label_formatter, StringLabelsFormatter))
        assert(isinstance(entities, EntityCollection))
        assert(isinstance(doc_id, int))

        return CollectionIOUtils.read_from_zip(
            inner_path=CollectionIOUtils.get_annotation_innerpath(filename),
            process_func=lambda input_file: [
                CollectionOpinionConverter.to_text_opinion(relation, doc_id=doc_id, label_formatter=label_formatter)
                for relation in
                BratAnnotationParser.parse_annotations(input_file=input_file, encoding='utf-8-sig')["relations"]
                if label_formatter.supports_value(relation.Type) or keep_any_type],
            version=version)

    @staticmethod
    def read_document(filename, doc_id, label_formatter, keep_any_opinion):
        assert(isinstance(filename, str))
        assert(isinstance(doc_id, int))
        assert(isinstance(label_formatter, StringLabelsFormatter))
        assert(isinstance(keep_any_opinion, bool))

        def file_to_doc(input_file):
            sentences = BratDocumentSentencesReader.from_file(input_file=input_file, entities=entities)
            return BratNews(doc_id=doc_id,
                            sentences=sentences,
                            text_opinions=opinions)

        entities = CollectionEntityCollection.read_collection(filename=filename, version=CollectionVersions.NO)

        opinions = SentiNERELDocReader.read_text_opinions(
            doc_id=doc_id,
            filename=filename,
            entities=entities,
            version=CollectionVersions.NO,
            label_formatter=label_formatter,
            keep_any_type=keep_any_opinion)

        return CollectionIOUtils.read_from_zip(
            inner_path=CollectionIOUtils.get_news_innerpath(filename=filename),
            process_func=file_to_doc,
            version=CollectionVersions.NO)