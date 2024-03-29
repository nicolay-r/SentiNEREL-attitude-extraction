from arekit.contrib.utils.data.readers.csv_pd import PandasCsvReader
from tqdm import tqdm
from os.path import exists
from collections import OrderedDict

from arekit.common.evaluation.comparators.opinions import OpinionBasedComparator
from arekit.common.evaluation.evaluators.modes import EvaluationModes
from arekit.common.opinions.collection import OpinionCollection
from arekit.common.utils import progress_bar_defined
from arekit.common.data.row_ids.multiple import MultipleIDProvider
from arekit.common.data.storages.base import BaseRowsStorage
from arekit.common.data.views.samples import LinkedSamplesStorageView
from arekit.common.labels.scaler.base import BaseLabelScaler
from arekit.common.opinions.base import Opinion
from arekit.common.labels.base import Label
from arekit.contrib.utils.evaluation.iterators import DataPairsIterators
from arekit.contrib.utils.synonyms.stemmer_based import StemmerBasedSynonymCollection
from arekit.contrib.utils.processing.lemmatization.mystem import MystemWrapper

from SentiNEREL.labels.scaler import PosNegNeuRelationsLabelScaler
from evaluation.utils import row_to_context_opinion, row_to_opinion, \
    create_filter_labels_func, assign_labels, select_doc_ids, create_evaluator


def __extract_context_opinions_from_test(test_linked_view, storage, label_scaler, default_label):
    """ return: dict { tid: TextOpinion },
        where:  tid -- is a TextOpininID
    """
    assert(isinstance(test_linked_view, LinkedSamplesStorageView))
    assert(isinstance(storage, BaseRowsStorage))
    assert(isinstance(label_scaler, BaseLabelScaler))

    context_opinion_by_id = OrderedDict()
    context_opinion_by_row_id = OrderedDict()
    for linkage in tqdm(test_linked_view.iter_from_storage(storage)):
        for row in linkage:
            context_opinion = row_to_context_opinion(
                row=row, label_scaler=label_scaler, default_label=default_label)
            context_opinion_by_id[context_opinion.Tag] = context_opinion
            context_opinion_by_row_id[row["id"]] = context_opinion

    return context_opinion_by_id, context_opinion_by_row_id


def __gather_opinion_and_group_ids_from_view(linked_view, storage, label_scaler, default_label):
    """ Из связок берем только первое отношение и считаем его Opinion.
        А также группируем TextOpinons относительно первого id.
    """
    assert(isinstance(linked_view, LinkedSamplesStorageView))
    assert(isinstance(storage, BaseRowsStorage))
    assert(isinstance(default_label, Label))

    opinion_by_row_id = OrderedDict()
    context_opinion_ids_by_row_id = OrderedDict()
    opinions_by_doc_id = OrderedDict()
    for linkage in tqdm(linked_view.iter_from_storage(storage)):

        first_row = linkage[0]
        first_row_id = first_row["id"]
        doc_id = first_row["doc_id"]
        opinion = row_to_opinion(first_row, label_scaler, default_label=default_label)

        opinion_by_row_id[first_row_id] = opinion
        context_opinion_ids_by_row_id[first_row_id] = [
            row_to_context_opinion(row, label_scaler, default_label).Tag for row in linkage
        ]

        if doc_id not in opinions_by_doc_id:
            opinions_by_doc_id[doc_id] = []
        opinions_by_doc_id[doc_id].append(opinion)

    return opinion_by_row_id, context_opinion_ids_by_row_id, opinions_by_doc_id


def __vote_label_func(labels):
    """ Используем метод голосования.
    """
    assert(isinstance(labels, list))

    vote_label = sum(labels)
    if vote_label < 0:
        vote_label = -1
    if vote_label > 0:
        vote_label = 1

    return vote_label


def __compose_test_opinions_by_doc_id(etalon_opinions_by_row_id,
                                      etalon_context_opinion_ids_by_row_id,
                                      test_opinions_by_row_id,
                                      test_context_opinion_ids_by_row_id,
                                      test_context_opinions_by_id,
                                      label_scaler,
                                      filter_opinion_func,
                                      labels_agg_func):

    def __try_register_opinion(source_value, target_value, existed_tids):
        assert(isinstance(source_value, str))
        assert(isinstance(target_value, str))
        assert(isinstance(existed_tids, list))

        # если нет tids, то тогда нет смысла составлять отношение.
        if len(existed_tids) == 0:
            return

        # используем метод голосования.
        labels = [label_scaler.label_to_int(test_context_opinions_by_id[tid].Sentiment) for tid in existed_tids]
        actual_label = labels_agg_func(labels)

        # создаем Opinion и фиксируем его.
        opinion = Opinion(source_value=source_value,
                          target_value=target_value,
                          sentiment=label_scaler.int_to_label(actual_label))

        if not filter_opinion_func(opinion):
            return

        # регистрируем для doc_id.
        doc_id = test_context_opinions_by_id[existed_tids[0]].DocId
        if doc_id not in test_opinions_by_doc_id:
            test_opinions_by_doc_id[doc_id] = []
        test_opinions_by_doc_id[doc_id].append(opinion)

    test_opinions_by_doc_id = {}

    used_tids = set()
    for row_id, etalon_opinion in etalon_opinions_by_row_id.items():
        tid_list = etalon_context_opinion_ids_by_row_id[row_id]

        existed_tids = [tid for tid in tid_list if tid in test_context_opinions_by_id]

        # отмечаем как просмотренные.
        for tid in existed_tids:
            used_tids.add(tid)

        __try_register_opinion(source_value=etalon_opinion.SourceValue,
                               target_value=etalon_opinion.TargetValue,
                               existed_tids=existed_tids)

    # учитываем оставшиеся.
    for row_id, test_opinion in test_opinions_by_row_id.items():
        tid_list = test_context_opinion_ids_by_row_id[row_id]

        # выбираем только те, которые не были использованы ранее.
        existed_tids = list(filter(lambda tid: tid not in used_tids, tid_list))

        __try_register_opinion(source_value=test_opinion.SourceValue,
                               target_value=test_opinion.TargetValue,
                               existed_tids=existed_tids)

    return test_opinions_by_doc_id


def opinions_per_document_two_class_result_evaluation(
        test_predict_filepath, etalon_samples_filepath, test_samples_filepath,
        synonyms=None, doc_ids_mode="joined", evaluator_type="two_class",
        labels_agg_func=__vote_label_func,
        label_scaler=PosNegNeuRelationsLabelScaler()):
    """ Подокументное вычисление результатов разметки отношений типа Opninon (пар на уровне документа)
        Замечания:
            - Коллекция синонимов составляется на лету в случае, когда она по-умолчанию не задана.
    """
    assert(isinstance(test_predict_filepath, str))
    assert(isinstance(etalon_samples_filepath, str))
    assert(isinstance(test_samples_filepath, str))
    assert(isinstance(evaluator_type, str))
    assert(callable(labels_agg_func))

    if not exists(test_predict_filepath):
        raise FileNotFoundError(test_predict_filepath)

    if not exists(etalon_samples_filepath):
        raise FileNotFoundError(etalon_samples_filepath)

    if not exists(test_samples_filepath):
        raise FileNotFoundError(test_samples_filepath)

    if synonyms is None:
        synonyms = StemmerBasedSynonymCollection(iter_group_values_lists=[],
                                                 stemmer=MystemWrapper(),
                                                 is_read_only=False,
                                                 debug=False)

    no_label = label_scaler.uint_to_label(0)

    # Setup views.
    reader = PandasCsvReader()
    test_samples_storage = reader.read(test_samples_filepath)
    etalon_samples_storage = reader.read(etalon_samples_filepath)
    test_predict_storage = reader.read(test_predict_filepath)

    view = LinkedSamplesStorageView(row_ids_provider=MultipleIDProvider())

    test_context_opinions_by_id, test_context_opinions_by_row_id = __extract_context_opinions_from_test(
        test_linked_view=view, storage=test_samples_storage, label_scaler=label_scaler, default_label=no_label)

    etalon_opinions_by_row_id, etalon_context_opinion_ids_by_row_id, etalon_opinions_by_doc_id = \
        __gather_opinion_and_group_ids_from_view(
            linked_view=view, storage=etalon_samples_storage, label_scaler=label_scaler, default_label=no_label)

    test_opinions_by_row_id, test_context_opinion_ids_by_row_id, orig_test_opinion_by_doc_id = \
        __gather_opinion_and_group_ids_from_view(
            linked_view=view, storage=test_samples_storage, label_scaler=label_scaler, default_label=no_label)

    assign_labels(view=view,
                  storage=test_predict_storage,
                  text_opinions=test_context_opinions_by_id.values(),
                  row_id_to_context_opin_id_func=lambda row_id: test_context_opinions_by_row_id[row_id].Tag,
                  label_scaler=label_scaler)

    filter_opinion_func = create_filter_labels_func(evaluator_type=evaluator_type,
                                                    get_label_func=lambda opinion: opinion.Sentiment,
                                                    no_label=no_label)

    test_opinions_by_doc_id = __compose_test_opinions_by_doc_id(
        etalon_opinions_by_row_id=etalon_opinions_by_row_id,
        etalon_context_opinion_ids_by_row_id=etalon_context_opinion_ids_by_row_id,
        test_opinions_by_row_id=test_opinions_by_row_id,
        test_context_opinion_ids_by_row_id=test_context_opinion_ids_by_row_id,
        test_context_opinions_by_id=test_context_opinions_by_id,
        label_scaler=label_scaler,
        filter_opinion_func=filter_opinion_func,
        labels_agg_func=labels_agg_func)                                        # создаем на основе метода голосования.

    doc_ids = select_doc_ids(doc_ids_mode=doc_ids_mode,
                             test_doc_ids=orig_test_opinion_by_doc_id.keys(),
                             etalon_doc_ids=etalon_opinions_by_doc_id.keys())

    cmp_pairs_iter = DataPairsIterators.iter_func_based_collections(
        doc_ids=[int(doc_id) for doc_id in doc_ids],
        read_etalon_collection_func=lambda doc_id: OpinionCollection(
            # В некоторых случаях может быть ситуация, что в эталонной разметке для документа отсутствуют данные.
            opinions=[opinion for opinion in etalon_opinions_by_doc_id[doc_id]
                      if filter_opinion_func(opinion)] if doc_id in etalon_opinions_by_doc_id else [],
            synonyms=synonyms,
            error_on_duplicates=False,
            error_on_synonym_end_missed=True),
        read_test_collection_func=lambda doc_id: OpinionCollection(
            opinions=test_opinions_by_doc_id[doc_id] if doc_id in test_opinions_by_doc_id else [],
            synonyms=synonyms,
            error_on_duplicates=False,
            error_on_synonym_end_missed=False))

    # getting evaluator.
    evaluator = create_evaluator(evaluator_type=evaluator_type,
                                 comparator=OpinionBasedComparator(eval_mode=EvaluationModes.Extraction),
                                 uint_labels=[1, 2, 0],
                                 get_item_label_func=lambda opinion: opinion.Sentiment,
                                 label_scaler=label_scaler)

    # evaluate every document.
    logged_cmp_pairs_it = progress_bar_defined(cmp_pairs_iter, total=len(doc_ids), desc="Evaluate", unit='docs')
    result = evaluator.evaluate(cmp_pairs=logged_cmp_pairs_it)

    return result
