from arekit.common.evaluation.results.utils import calc_f1_macro
from arekit.common.evaluation.utils import OpinionCollectionsToCompareUtils
from arekit.common.opinions.collection import OpinionCollection
from arekit.common.utils import progress_bar_iter
from arekit.contrib.utils.evaluation.evaluators.three_class import ThreeClassOpinionEvaluator
from arekit.contrib.utils.evaluation.results.three_class import ThreeClassEvalResult
from arekit.contrib.utils.synonyms.stemmer_based import StemmerBasedSynonymCollection
from arekit.processing.lemmatization.mystem import MystemWrapper
from tqdm import tqdm
from collections import OrderedDict
from os.path import exists, join

from arekit.common.data.row_ids.multiple import MultipleIDProvider
from arekit.common.data.storages.base import BaseRowsStorage
from arekit.common.data.views.samples import BaseSampleStorageView
from arekit.common.evaluation.comparators.text_opinions import TextOpinionBasedComparator
from arekit.common.labels.base import NoLabel
from arekit.common.labels.scaler.base import BaseLabelScaler
from arekit.common.opinions.base import Opinion
from arekit.common.text_opinions.base import TextOpinion
from labels.scaler import PosNegNeuRelationsLabelScaler


def __row_to_opinion(row, label_scaler):
    """ составление Opinion из ряда данных sample.
    """

    uint_label = int(row["label"]) if "label" in row \
        else label_scaler.label_to_uint(NoLabel())

    source_index = int(row["s_ind"])
    target_index = int(row["t_ind"])
    entities = [int(e) for e in row["entities"].split(',')]
    entity_values = row["entity_values"].split(',')

    return Opinion(source_value=entity_values[entities.index(source_index)],
                   target_value=entity_values[entities.index(target_index)],
                   sentiment=label_scaler.uint_to_label(uint_label))


def __row_to_text_opinion(row, label_scaler):
    """ Чтение text_opinion из ряда данных sample.
    """
    assert(isinstance(label_scaler, BaseLabelScaler))

    uint_label = int(row["label"]) if "label" in row \
        else label_scaler.label_to_uint(NoLabel())

    text_opinion = TextOpinion(
        doc_id=int(row["doc_id"]),
        text_opinion_id=None,
        source_id=int(row["s_ind"]),
        target_id=int(row["t_ind"]),
        owner=None,
        label=label_scaler.uint_to_label(uint_label))

    tid = TextOpinionBasedComparator.text_opinion_to_id(text_opinion)
    text_opinion.set_text_opinion_id(tid)

    return text_opinion


def __extract_text_opinions_from_test(test_view, label_scaler):
    """
        return: dict { tid: TextOpinion },
        where:  tid -- is a TextOpininID
    """
    assert(isinstance(test_view, BaseSampleStorageView))
    assert(isinstance(label_scaler, BaseLabelScaler))

    text_opinion_by_id = OrderedDict()
    for linkage in tqdm(test_view.iter_rows_linked_by_text_opinions()):
        for row in linkage:
            text_opinion = __row_to_text_opinion(row, label_scaler)
            text_opinion_by_id[text_opinion.TextOpinionID] = text_opinion

    return text_opinion_by_id


def __gather_opinion_and_group_ids_from_etalon(etalon_view, label_scaler):
    """ Из связок берем только первое отношение и считаем его Opinion.
        А также группируем TextOpinons относительно первого id.
    """
    opinion_by_row_id = OrderedDict()
    text_opinion_ids_by_row_id = OrderedDict()
    etalon_opinions_by_doc_id = OrderedDict()
    for linkage in tqdm(etalon_view.iter_rows_linked_by_text_opinions()):

        first_row = linkage[0]
        first_row_id = first_row["id"]
        doc_id = first_row["doc_id"]
        opinion = __row_to_opinion(first_row, label_scaler)

        opinion_by_row_id[first_row_id] = opinion
        text_opinion_ids_by_row_id[first_row_id] = [__row_to_text_opinion(row, label_scaler).TextOpinionID
                                                    for row in linkage]

        if doc_id not in etalon_opinions_by_doc_id:
            etalon_opinions_by_doc_id[doc_id] = []
        etalon_opinions_by_doc_id[doc_id].append(opinion)

    return opinion_by_row_id, text_opinion_ids_by_row_id, etalon_opinions_by_doc_id


def __compose_test_opinions_by_doc_id(etalon_opinions_by_row_id, etalon_text_opinion_ids_by_row_id,
                                      test_opinions_by_id, label_scaler):

    used = set()

    test_opinions_by_doc_id = {}
    for row_id, etalon_opinion in etalon_opinions_by_row_id.items():
        tid_list = etalon_text_opinion_ids_by_row_id[row_id]

        existed_tids = [tid for tid in tid_list if tid in test_opinions_by_id]

        if len(existed_tids) == 0:
            continue

        labels = [label_scaler.label_to_int(test_opinions_by_id[tid].Sentiment) for tid in existed_tids]

        # используем метод голосования
        vote_label = sum(labels)
        if vote_label < 0:
            vote_label = -1
        if vote_label > 0:
            vote_label = 1

        test_opinion = Opinion(source_value=etalon_opinion.SourceValue,
                               target_value=etalon_opinion.TargetValue,
                               sentiment=label_scaler.int_to_label(vote_label))

        doc_id = test_opinions_by_id[existed_tids[0]].DocID

        if doc_id not in test_opinions_by_doc_id:
            test_opinions_by_doc_id[doc_id] = []
        test_opinions_by_doc_id[doc_id].append(test_opinion)

        # отмечаем как used.
        for tid in tid_list:
            used.add(test_opinions_by_id[tid])

    # TODO. Осталось учесть тех, что нет в Etalon.

    return test_opinions_by_doc_id


def opinions_per_document_result_evaluation(
        predict_filename, etalon_samples_filepath, test_samples_filepath,
        label_scaler=PosNegNeuRelationsLabelScaler()):
    """ Подокументное вычисление результатов разметки отношений типа Opninon (пар на уровне документа)
    """
    assert(isinstance(predict_filename, str))
    assert(isinstance(etalon_samples_filepath, str))
    assert(isinstance(test_samples_filepath, str))

    if not exists(predict_filename):
        raise FileNotFoundError(predict_filename)

    if not exists(etalon_samples_filepath):
        raise FileNotFoundError(etalon_samples_filepath)

    if not exists(test_samples_filepath):
        raise FileNotFoundError(test_samples_filepath)

    test_view = BaseSampleStorageView(storage=BaseRowsStorage.from_tsv(filepath=test_samples_filepath),
                                      row_ids_provider=MultipleIDProvider())
    etalon_view = BaseSampleStorageView(storage=BaseRowsStorage.from_tsv(filepath=etalon_samples_filepath),
                                        row_ids_provider=MultipleIDProvider())

    test_opinions_by_id = __extract_text_opinions_from_test(
        test_view=test_view, label_scaler=label_scaler)
    etalon_opinions_by_row_id, etalon_text_opinion_ids_by_row_id, etalon_opinions_by_doc_id = \
        __gather_opinion_and_group_ids_from_etalon(etalon_view=etalon_view, label_scaler=label_scaler)
    test_opinions_by_doc_id = __compose_test_opinions_by_doc_id(
        etalon_opinions_by_row_id=etalon_opinions_by_row_id,
        etalon_text_opinion_ids_by_row_id=etalon_text_opinion_ids_by_row_id,
        test_opinions_by_id=test_opinions_by_id,
        label_scaler=label_scaler)

    synonyms = StemmerBasedSynonymCollection(iter_group_values_lists=[],
                                             stemmer=MystemWrapper(),
                                             is_read_only=False,
                                             debug=False)

    cmp_pairs_iter = OpinionCollectionsToCompareUtils.iter_comparable_collections(
        doc_ids=test_opinions_by_doc_id.keys(),
        read_etalon_collection_func=lambda doc_id: OpinionCollection(
            opinions=etalon_opinions_by_doc_id[doc_id],
            synonyms=synonyms,
            error_on_duplicates=False,
            error_on_synonym_end_missed=True),
        read_test_collection_func=lambda doc_id: OpinionCollection(
            opinions=test_opinions_by_doc_id[doc_id],
            synonyms=synonyms,
            error_on_duplicates=False,
            error_on_synonym_end_missed=False))

    # getting evaluator.
    evaluator = ThreeClassOpinionEvaluator(label1=label_scaler.uint_to_label(1),
                                           label2=label_scaler.uint_to_label(2),
                                           no_label=label_scaler.uint_to_label(0))

    # evaluate every document.
    logged_cmp_pairs_it = progress_bar_iter(cmp_pairs_iter, desc="Evaluate", unit='pairs')
    result = evaluator.evaluate(cmp_pairs=logged_cmp_pairs_it)

    return result


if __name__ == '__main__':

    output_dir = "_out"
    source_filename = "predict-cnn.tsv.gz"
    samples_test = "sample-test-0.tsv.gz"
    samples_etalon = "sample-etalon-0.tsv.gz"
    serialize_dir = "serialize-nn_3l"

    result = opinions_per_document_result_evaluation(
        predict_filename=join(output_dir, serialize_dir, source_filename),
        etalon_samples_filepath=join(output_dir, serialize_dir, samples_etalon),
        test_samples_filepath=join(output_dir, serialize_dir, samples_test))

    r = calc_f1_macro(pos_prec=result.TotalResult[ThreeClassEvalResult.C_POS_PREC],
                      neg_prec=result.TotalResult[ThreeClassEvalResult.C_NEG_PREC],
                      pos_recall=result.TotalResult[ThreeClassEvalResult.C_POS_RECALL],
                      neg_recall=result.TotalResult[ThreeClassEvalResult.C_NEG_RECALL])

    print(result.TotalResult)
    print(r)