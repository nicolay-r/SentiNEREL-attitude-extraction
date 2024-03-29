from os.path import join

from arekit.contrib.utils.data.readers.csv_pd import PandasCsvReader
from arekit.contrib.utils.data.storages.pandas_based import PandasBasedRowsStorage
from deeppavlov.models.bert import bert_classifier
from deeppavlov.models.preprocessors.bert_preprocessor import BertPreprocessor

from arekit.common.labels.scaler.base import BaseLabelScaler
from arekit.common.pipeline.context import PipelineContext
from arekit.common.pipeline.items.base import BasePipelineItem
from arekit.contrib.networks.core.predict.base_writer import BasePredictWriter
from arekit.contrib.networks.core.predict.provider import BasePredictProvider


class BertInferencePipelineItem(BasePipelineItem):
    """ This is a DeepPavlov based BERT model inference Pipeline Item
    """

    def __init__(self, bert_config_file, model_checkpoint_path, vocab_filepath,
                 predict_writer, labels_scaler, max_seq_length, do_lowercase,
                 data_type, batch_size=10):
        assert(isinstance(predict_writer, BasePredictWriter))
        assert(isinstance(labels_scaler, BaseLabelScaler))
        assert(isinstance(do_lowercase, bool))
        assert(isinstance(max_seq_length, int))

        # Model classifier.
        self.__model = bert_classifier.BertClassifierModel(
            bert_config_file=bert_config_file,
            load_path=model_checkpoint_path,
            keep_prob=1.0,
            n_classes=labels_scaler.LabelsCount,
            save_path="")

        # Setup processor.
        self.__proc = BertPreprocessor(vocab_file=vocab_filepath,
                                       do_lower_case=do_lowercase,
                                       max_seq_length=max_seq_length)

        self.__writer = predict_writer
        self.__labels_scaler = labels_scaler
        self.__predict_provider = BasePredictProvider()
        self.__batch_size = batch_size
        self.__data_type = data_type

    def apply_core(self, input_data, pipeline_ctx):
        assert(isinstance(input_data, dict))
        assert(isinstance(pipeline_ctx, PipelineContext))
        assert("samples_dir" in input_data)
        assert("predict_dir" in input_data)             # То, куда нужно записать результат.

        def __iter_predict_result(tsv_filepath):
            reader = PandasCsvReader()
            samples = PandasBasedRowsStorage(reader.read(tsv_filepath))

            used_row_ids = set()

            data = {"text_a": [], "text_b": [], "row_ids": []}

            for row_ind, row in samples:

                # Considering unique rows only.
                if row["id"] in used_row_ids:
                    continue

                data["text_a"].append(row['text_a'])
                data["text_b"].append(row['text_b'])
                data["row_ids"].append(row["id"])

                used_row_ids.add(row["id"])

            for i in range(0, len(data["text_a"]), self.__batch_size):

                texts_a = data["text_a"][i:i + self.__batch_size]
                texts_b = data["text_b"][i:i + self.__batch_size]
                row_ids = data["row_ids"][i:i + self.__batch_size]

                batch_features = self.__proc(texts_a=texts_a, texts_b=texts_b)

                for i, uint_label in enumerate(self.__model(batch_features)):
                    yield [row_ids[i], int(uint_label)]

        # Setup predicted result writer.
        full_model_name = pipeline_ctx.provide_or_none("full_model_name")

        predict_target = join(input_data["predict_dir"], "predict-{fmn}-{dtype}.tsv.gz".format(
            fmn=full_model_name, dtype=str(self.__data_type).lower().split('.')[-1]))

        samples_target = join(input_data["samples_dir"], "sample-{dtype}-{index}.tsv.gz".format(
            dtype=str(self.__data_type).lower().split('.')[-1], index=0))

        # Setup target filepath.
        self.__writer.set_target(predict_target)

        # Gathering the content
        title, contents_it = self.__predict_provider.provide(
            sample_id_with_uint_labels_iter=__iter_predict_result(tsv_filepath=samples_target),
            labels_scaler=self.__labels_scaler)

        with self.__writer:
            self.__writer.write(title=title, contents_it=contents_it)
