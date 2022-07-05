from collections import OrderedDict
from os.path import exists, join

from arekit.common.data.row_ids.multiple import MultipleIDProvider
from arekit.common.data.storages.base import BaseRowsStorage
from arekit.common.data.views.samples import BaseSampleStorageView
from arekit.common.evaluation.comparators.text_opinions import TextOpinionBasedComparator
from arekit.common.evaluation.evaluators.modes import EvaluationModes
from arekit.common.evaluation.pairs.single import SingleDocumentDataPairsToCompare
from arekit.common.text_opinions.base import TextOpinion
from arekit.contrib.utils.evaluation.evaluators.two_class import TwoClassEvaluator
from pandas import np
from tqdm import tqdm

from labels.scaler import PosNegNeuRelationsLabelScaler


def __extract_text_opinions(filename, label_scaler, no_label):
    """ Reading data from tsv-gz via storage view
        returns: dict
            (row_id, text_opinion)
    """
    view = BaseSampleStorageView(storage=BaseRowsStorage.from_tsv(filepath=filename),
                                 row_ids_provider=MultipleIDProvider())
    etalon_linked_iter = view.iter_rows_linked_by_text_opinions()
    opinions_by_row_id = OrderedDict()
    for linkage in tqdm(etalon_linked_iter):
        for row in linkage:
            uint_label = int(row["label"]) if "label" in row \
                else label_scaler.label_to_uint(no_label)

            text_opinion = TextOpinion(
                doc_id=int(row["doc_id"]),
                text_opinion_id=None,
                source_id=int(row["s_ind"]),
                target_id=int(row["t_ind"]),
                owner=None,
                label=label_scaler.uint_to_label(uint_label))

            tid = TextOpinionBasedComparator.text_opinion_to_id(text_opinion)
            text_opinion.set_text_opinion_id(tid)

            opinions_by_row_id[row["id"]] = text_opinion

    return opinions_by_row_id


def __assign_labels(filename, text_opinions, row_id_to_text_opin_id_func, label_scaler):
    assert (callable(row_id_to_text_opin_id_func))

    text_opinons_by_id = {}
    for text_opinion in text_opinions:
        assert (isinstance(text_opinion, TextOpinion))
        text_opinons_by_id[text_opinion.TextOpinionID] = text_opinion

    predict_view = BaseSampleStorageView(storage=BaseRowsStorage.from_tsv(filepath=filename),
                                         row_ids_provider=MultipleIDProvider())
    test_linked_iter = predict_view.iter_rows_linked_by_text_opinions()
    for linkage in tqdm(test_linked_iter):
        for row in linkage:
            text_opinion_id = row_id_to_text_opin_id_func(row["id"])
            text_opinion = text_opinons_by_id[text_opinion_id]
            uint_labels = [int(row[str(c)]) for c in range(label_scaler.classes_count())]
            text_opinion.set_label(label_scaler.uint_to_label(int(np.argmax(uint_labels))))


def text_opinion_monolith_collection_result_evaluator(
        predict_filename, etalon_samples_filepath, test_samples_filepath,
        label_scaler=PosNegNeuRelationsLabelScaler()):
    """ Single-document like (whole collection) evaluator.
        Considering text_opinion instances as items for comparison.

        Оценка выполняется на уровне контекстных отношений.
        Учет по документам не идет, т.е. предполагается
        целая коллекция как один огромный документ.
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

    no_label = label_scaler.uint_to_label(0)

    # Reading collection through storage views.
    etalon_opins_by_row_id = __extract_text_opinions(filename=etalon_samples_filepath, label_scaler=label_scaler,
                                                     no_label=no_label)
    test_opins_by_row_id = __extract_text_opinions(filename=test_samples_filepath, label_scaler=label_scaler,
                                                   no_label=no_label)
    __assign_labels(filename=predict_filename,
                    text_opinions=test_opins_by_row_id.values(),
                    row_id_to_text_opin_id_func=lambda row_id: test_opins_by_row_id[row_id].TextOpinionID,
                    label_scaler=label_scaler)

    # Remove the one with NoLabel instance.
    test_opins_by_row_id = {row_id: text_opinion for row_id, text_opinion in test_opins_by_row_id.items()
                            if text_opinion.Sentiment != no_label}

    # Composing evaluator.
    evaluator = TwoClassEvaluator(
        comparator=TextOpinionBasedComparator(eval_mode=EvaluationModes.Extraction),
        label1=label_scaler.uint_to_label(1),
        label2=label_scaler.uint_to_label(2),
        get_item_label_func=lambda text_opinion: text_opinion.Sentiment)

    # evaluate every document.
    cmp_pair = SingleDocumentDataPairsToCompare(etalon_data=list(etalon_opins_by_row_id.values()),
                                                test_data=list(test_opins_by_row_id.values()))
    result = evaluator.evaluate(cmp_pairs=[cmp_pair])

    return result


if __name__ == '__main__':

    output_dir = "_out"
    source_filename = "predict-cnn.tsv.gz"
    samples_test = "sample-test-0.tsv.gz"
    samples_etalon = "sample-etalon-0.tsv.gz"
    serialize_dir = "serialize-nn_3l"

    result = text_opinion_monolith_collection_result_evaluator(
        predict_filename=join(output_dir, serialize_dir, source_filename),
        etalon_samples_filepath=join(output_dir, serialize_dir, samples_etalon),
        test_samples_filepath=join(output_dir, serialize_dir, samples_test))

    print(result.TotalResult)
