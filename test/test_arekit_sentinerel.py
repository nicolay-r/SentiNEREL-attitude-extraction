import unittest
from os.path import dirname, realpath, join

from arekit.contrib.bert.input.providers.cropped_sample import CroppedBertSampleRowProvider
from arekit.contrib.bert.terms.mapper import BertDefaultStringTextTermsMapper
from arekit.contrib.utils.bert.text_b_rus import BertTextBTemplates
from arekit.contrib.utils.data.writers.csv_pd import PandasCsvWriter
from arekit.contrib.utils.data.writers.json_opennre import OpenNREJsonWriter

from SentiNEREL.labels.scaler import PosNegNeuRelationsLabelScaler
from SentiNEREL.entity.formatter import CustomTypedEntitiesFormatter
from framework.arekit.serialize_bert import serialize_bert
from framework.arekit.serialize_nn import serialize_nn


class TestSerialize(unittest.TestCase):

    current_dir = dirname(realpath(__file__))
    output_dir = join(current_dir, "_out")
    output_nn_dir = join(output_dir, "serialize-nn")
    output_bert_dir = join(output_dir, "serialize-bert")

    def test_nn_tsv(self):
        serialize_nn(limit=1,
                     output_dir=self.output_nn_dir,
                     folding_type="fixed",
                     writer=PandasCsvWriter(write_header=True),
                     labels_scaler=PosNegNeuRelationsLabelScaler(),
                     split_filepath="../data/split_fixed.txt")

    def test_nn_json(self):
        serialize_nn(limit=1,
                     output_dir=self.output_nn_dir,
                     folding_type="fixed",
                     writer=OpenNREJsonWriter(text_columns=["text_a"]),
                     labels_scaler=PosNegNeuRelationsLabelScaler(),
                     split_filepath="../data/split_fixed.txt")

    def test_bert_json(self, limit=1):
        serialize_bert(limit=limit,
                       terms_per_context=50,
                       output_dir=self.output_bert_dir,
                       split_filepath="../data/split_fixed.txt",
                       writer=OpenNREJsonWriter(text_columns=["text_a", "text_b"]),
                       folding_type="fixed",
                       sample_row_provider=CroppedBertSampleRowProvider(
                           crop_window_size=50,
                           text_b_template=BertTextBTemplates.NLI.value,
                           label_scaler=PosNegNeuRelationsLabelScaler(),
                           text_terms_mapper=BertDefaultStringTextTermsMapper(
                               entity_formatter=CustomTypedEntitiesFormatter()
                           )))

    def test_bert_json_full(self):
        self.test_bert_json(limit=None)


if __name__ == '__main__':
    unittest.main()
