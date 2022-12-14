# Default pretrained BERT.
from os.path import join

MODEL_DIR = "_model"

# BERT+RuAttitudes
BERT_DEFAULT_STATE_NAME = "ra-20-srubert-large-neut-nli-pretrained-3l"
BERT_PRETRAINED_MODEL_PATHDIR = join(MODEL_DIR, BERT_DEFAULT_STATE_NAME)
BERT_PRETRAINED_MODEL_TAR = BERT_PRETRAINED_MODEL_PATHDIR + '.tar.gz'
BERT_CONFIG_PATH = join(BERT_PRETRAINED_MODEL_PATHDIR, "bert_config.json")
BERT_CKPT_PATH = join(BERT_PRETRAINED_MODEL_PATHDIR, "model.ckpt-30238")
BERT_VOCAB_PATH = join(BERT_PRETRAINED_MODEL_PATHDIR, "vocab.txt")
BERT_DO_LOWERCASE = False

# BERT+RuAttitudes+RuSentRel
BERT_TARGET_DIR = MODEL_DIR
BERT_DEFAULT_FINETUNED = BERT_DEFAULT_STATE_NAME + '-finetuned'
BERT_FINETUNED_MODEL_PATHDIR = join(MODEL_DIR, BERT_DEFAULT_FINETUNED)
BERT_FINETUNED_MODEL_TAR = BERT_FINETUNED_MODEL_PATHDIR + '.tar.gz'
BERT_FINETUNED_CKPT_PATH = join(BERT_FINETUNED_MODEL_PATHDIR, BERT_DEFAULT_STATE_NAME)

# Дообученная версия BERT+RuAttitudes но на текущем корпусе.
BERT_DEFAULT_FINETUNED2 = BERT_DEFAULT_FINETUNED + '-finetuned'
BERT_FINETUNED2_MODEL_PATHDIR = join(MODEL_DIR, BERT_DEFAULT_FINETUNED2)
BERT_FINETUNED2_MODEL_TAR = BERT_FINETUNED2_MODEL_PATHDIR + '.tar.gz'
BERT_FINETUNED2_CKPT_PATH = join(BERT_FINETUNED2_MODEL_PATHDIR, BERT_DEFAULT_STATE_NAME)
