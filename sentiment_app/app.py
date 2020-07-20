import logging
import os
import time

import numpy as np
import pandas as pd
from flask import Flask, Response, request

import config
import dataset
import torch
import torch.utils.data
from model import BERTBaseUncased

app = Flask(__name__)

MODEL = None
DEVICE = "cpu"
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def generate_predictions(df):
    df.reset_index(drop=True, inplace=True)
    predict_dataset = dataset.BERTDataset(review=df.PROCESSED_TEXT.values)
    predict_data_loader = torch.utils.data.DataLoader(
        predict_dataset,
        batch_size=config.PREDICT_BATCH_SIZE,
        num_workers=config.NUM_WORKERS,
    )
    test_preds = np.zeros(df.shape[0])
    with torch.no_grad():
        for bi, d in enumerate(predict_data_loader):
            ids = d["ids"]
            token_type_ids = d["token_type_ids"]
            mask = d["mask"]

            ids = ids.to(DEVICE, dtype=torch.long)
            token_type_ids = token_type_ids.to(DEVICE, dtype=torch.long)
            mask = mask.to(DEVICE, dtype=torch.long)
            preds = MODEL(ids=ids, mask=mask, token_type_ids=token_type_ids)
            test_preds[
                bi * config.PREDICT_BATCH_SIZE : (bi + 1) * config.PREDICT_BATCH_SIZE
            ] = (preds[:, 0].detach().cpu().squeeze().numpy())

    output = torch.sigmoid(torch.tensor(test_preds)).numpy().ravel()
    return output


@app.route("/predict")
def predict():
    data = request.args.get("data")
    account = request.args.get("account")
    df = pd.read_json(data)
    start_time = time.time()

    rt_mask = df.FULL_TEXT.str.startswith(f"RT @{account}")
    retweets_frame = df.loc[rt_mask, :].copy()
    retweets_frame["SENTIMENT"] = 1.0

    tweets_frame = df.loc[~rt_mask, :].copy()
    tweets_frame["SENTIMENT"] = generate_predictions(tweets_frame)
    output_frame = pd.concat([retweets_frame, tweets_frame], axis=0)
    output_frame.reset_index(drop=True, inplace=True)

    print(time.time() - start_time)
    return Response(output_frame.to_json(), mimetype="application/json")


if __name__ == "__main__":
    logging.basicConfig(
        filename="./logs/sentiment_app.log", filemode="w", level=logging.DEBUG
    )
    MODEL = BERTBaseUncased()
    MODEL.to(DEVICE)
    MODEL.load_state_dict(
        torch.load(config.MODEL_PATH, map_location=torch.device(DEVICE))
    )
    MODEL.eval()
    app.run(host="0.0.0.0", port=5000)
