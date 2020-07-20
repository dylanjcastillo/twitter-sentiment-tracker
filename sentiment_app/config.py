import transformers

MAX_LEN = 256
PREDICT_BATCH_SIZE = 32
NUM_WORKERS = 4
MODEL_PATH = "./input/model.bin"
BERT_MODEL = "dccuchile/bert-base-spanish-wwm-uncased"
TOKENIZER = transformers.BertTokenizerFast.from_pretrained(
    "./input/", do_lower_case=True, truncation=True
)
