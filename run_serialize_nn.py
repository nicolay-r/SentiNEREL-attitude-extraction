from arekit.common.data.input.writers.tsv import TsvWriter

from models.nn.serialize import serialize_nn
from writers.opennre_json import OpenNREJsonWriter

if __name__ == '__main__':
    serialize_nn(output_dir="_out/serialize-nn", split_filepath="data/split_fixed.txt",
                 writer=OpenNREJsonWriter())
