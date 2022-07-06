from arekit.common.experiment.name_provider import ExperimentNameProvider
from arekit.common.pipeline.base import BasePipeline
from arekit.contrib.bert.samplers.nli_m import NliMultipleSampleProvider
from arekit.contrib.bert.terms.mapper import BertDefaultStringTextTermsMapper
from arekit.contrib.utils.entities.formatters.str_simple_sharp_prefixed_fmt import SharpPrefixedEntitiesSimpleFormatter

from entity.formatter import CustomEntitiesFormatter
from labels.formatter import SentimentLabelFormatter
from labels.scaler import PosNegNeuRelationsLabelScaler
from models.bert.serialize import BertTextsSerializationPipelineItem

if __name__ == '__main__':

    # TODO. EntityFormatter сделать как и для нейросетей, только #S и #O задать.

    ppl = BasePipeline([
        BertTextsSerializationPipelineItem(
            terms_per_context=50,
            output_dir="_out",
            fixed_split_filepath="data/split_fixed.txt",
            name_provider=ExperimentNameProvider(name="serialize", suffix="bert"),
            entity_fmt=CustomEntitiesFormatter(),
            label_formatter=SentimentLabelFormatter(),
            sample_row_provider=NliMultipleSampleProvider(
                label_scaler=PosNegNeuRelationsLabelScaler(),
                text_b_labels_fmt=SentimentLabelFormatter(),
                text_terms_mapper=BertDefaultStringTextTermsMapper(
                    entity_formatter=SharpPrefixedEntitiesSimpleFormatter()
                )))
    ])

    ppl.run(input_data=None)
