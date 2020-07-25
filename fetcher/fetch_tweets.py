import datetime
import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from time import sleep

import numpy as np
import pandas as pd

import emoji
import requests
import tweepy
from dotenv import load_dotenv

load_dotenv()
sqlite3.register_adapter(np.int32, lambda val: int(val))
sqlite3.register_adapter(np.int64, lambda val: int(val))

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
TWEETS_DB = DATA_DIR / "tweets.db"
LOGS_PATH = Path(__file__).parent / "logs" / "fetcher.log"
TARGETS_DF = pd.read_csv(DATA_DIR / "accounts.csv")
EMOJI_TO_ORIG_LANG = (
    pd.read_csv(DATA_DIR / "emojis_dict.csv").set_index("name")["name_es"].to_dict()
)

CONSUMER_KEY = os.getenv("TWITTER_KEY")
CONSUMER_SECRET = os.getenv("TWITTER_SECRET")
SENTIMENT_APP_HOST = os.getenv("SENTIMENT_APP_HOST")
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL"))
LANGUAGE = os.getenv("LANGUAGE")
AUTH = tweepy.AppAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)


def process_text(column):
    """Processes pandas Series for using it when predicting sentiment

    Args:
        column: pandas Series with tweets

    Returns:
        Column after processing
    """
    column = column.str.replace(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        "",
    )
    column = column.map(emoji.demojize)
    column = column.replace(EMOJI_TO_ORIG_LANG, regex=True)
    column = column.str.replace("^RT", "")
    column = column.str.replace(r"(?<=@)\w+", "")
    column = column.str.replace(r"[.,\/#@!¡\?¿$%\^&\*;:{}=\-_`~()”“\"]", " ")
    column = column.str.replace(r"\s+", " ")
    column = column.str.lower()
    column = column.str.strip()
    return column


def extract_tweets_data(response, target, target_account):
    """Extract data from queried tweets

    Args:
        response: Response from Tweepy
        target: Identifier of user of interest
        target_account: Twitter account of user of interest

    Returns:
        Dataframe of processed tweets
    """
    output = []
    timestamp = datetime.datetime.utcnow()
    for status in response:
        tweet_id = status.id
        tweeted_at = status.created_at
        is_retweet = 0
        try:
            # Get full response if it is a RT
            text = (
                f"RT @{status.retweeted_status.author.screen_name} "
                + status.retweeted_status.full_text
            )
            is_retweet = 1
        except AttributeError:
            text = status.full_text

        # Filter tweets where the target account is mentioned but
        # it is not mentioned first (so it's hard to know if it is
        # related to the target account)
        if (
            text.startswith("@")
            and not text.startswith(f"@{target_account}")
            and (
                not status.in_reply_to_screen_name
                or status.in_reply_to_screen_name != target_account
            )
        ):
            continue

        # Filters tweets that includes too many accounts but are not
        # RTs or responses to the target account
        if (
            not text.startswith(f"RT @{target_account}")
            and not text.startswith(f"@{target_account}")
            and (
                not status.in_reply_to_screen_name
                or status.in_reply_to_screen_name != target_account
            )
            and len(re.findall(r"@", text)) > 2
        ):
            continue

        user = status.author
        followers_count = user.followers_count
        favourites_count = user.favourites_count
        friends_count = user.friends_count
        tweets_count = user.statuses_count
        created_at = user.created_at

        output.append(
            (
                tweet_id,
                target,
                timestamp,
                text,
                followers_count,
                favourites_count,
                friends_count,
                tweets_count,
                created_at,
                tweeted_at,
                is_retweet,
            )
        )
    df_output = pd.DataFrame(
        output,
        columns=[
            "TWEET_ID",
            "TARGET",
            "INSERT_TIMESTAMP",
            "FULL_TEXT",
            "FOLLOWERS_COUNT",
            "FAVOURITES_COUNT",
            "FRIENDS_COUNT",
            "TWEETS_COUNT",
            "ACCOUNT_CREATION_DATE",
            "TWEET_TIMESTAMP",
            "IS_RT",
        ],
    )
    df_output.insert(
        loc=4, column="PROCESSED_TEXT", value=process_text(df_output["FULL_TEXT"]),
    )
    return df_output


def insert_data(tweets):
    """Insert data into SQLite database"""
    conn = sqlite3.connect(TWEETS_DB)
    insert_query = """
    INSERT INTO TWEETS (
        TWEET_ID,
        TARGET,
        INSERT_TIMESTAMP,
        FULL_TEXT,
        PROCESSED_TEXT,
        FOLLOWERS_COUNT,
        FAVOURITES_COUNT,
        FRIENDS_COUNT,
        TWEETS_COUNT,
        ACCOUNT_CREATION_DATE,
        TWEET_TIMESTAMP,
        IS_RT,
        SENTIMENT
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    tweets["ACCOUNT_CREATION_DATE"] = tweets["ACCOUNT_CREATION_DATE"].astype(str)
    tweets["INSERT_TIMESTAMP"] = tweets["INSERT_TIMESTAMP"].astype(str)
    tweets["TWEET_TIMESTAMP"] = tweets["TWEET_TIMESTAMP"].astype(str)
    conn.executemany(insert_query, tweets.to_records(index=False))
    conn.commit()
    conn.close()
    return


def get_latest_tweets(target_account, since_id):
    """Get latest tweets directed at certain account

    Args:
        target_account: Account of interest
        since_id: Identifier of tweet after which the query will get tweets

    Returns:
        JSON results from request to the Twitter API and API rate limit status
    """
    api = tweepy.API(AUTH)
    query = f"to:{target_account} OR (@{target_account}"
    for target in TARGETS_DF.itertuples():
        if target_account != target.account:
            query += f" -@{target.account}"
    query += ")"
    results = api.search(
        q=query,
        lang=LANGUAGE,
        result_type="recent",
        count="100",
        tweet_mode="extended",
        since_id=since_id,
    )
    search_limits = (
        api.rate_limit_status()
        .get("resources", {})
        .get("search", {})
        .get("/search/tweets", {})
    )
    return results, search_limits


def add_sentiment_to_tweets(processed_tweets, account):
    """Gets sentiment per tweet from inference service

    Args:
        processed_tweets: Processed tweets
        account: Target account used in query

    Returns:
        Dataframe with tweets and sentiment
    """
    df_deduplicated = processed_tweets[["FULL_TEXT", "PROCESSED_TEXT"]].drop_duplicates()
    logging.debug(f"Deduplicated DF: {df_deduplicated.shape[0]}")
    payload = df_deduplicated.to_json()
    req = requests.get(
        f"http://{SENTIMENT_APP_HOST}:5000/predict",
        params={"data": payload, "account": account},
        headers={"content-type": "application/json"},
    )
    response = req.json()
    df_response = pd.DataFrame.from_dict(response)
    output = processed_tweets.merge(
        df_response, on=["FULL_TEXT", "PROCESSED_TEXT"], how="left"
    )
    logging.debug(f"{output.columns}")
    return output


def main(target, target_account):
    """Download tweets directed at target

    Args:
        target: Identifier of user of interest
        target_account: Twitter account of user of interest
    """
    start_time = datetime.datetime.utcnow()
    logging.info(f"{target} Started new execution ({target}) at: {start_time}")
    logging.info(f"{target} Getting last TWEET_ID from the database")
    conn = sqlite3.connect(TWEETS_DB)
    cur = conn.cursor()
    cur.execute("SELECT MAX(TWEET_ID) FROM TWEETS WHERE TARGET=?;", (target,))
    last_id = cur.fetchone()[0]

    logging.info(f"{target} Getting most recent tweets from API")
    for trial in range(3):  # Tries to get data from API 3 times, unless rate limit error
        try:
            latest_tweets, api_limits = get_latest_tweets(target_account, last_id)
            logging.info(f"{target} Limits of API: {api_limits}")
            logging.info(f"{target} Got {len(latest_tweets)} tweets")
            processed_tweets = extract_tweets_data(latest_tweets, target, target_account)
            logging.info(
                f"{target} Inserting {processed_tweets.shape[0]} tweets into the DB"
            )
            if processed_tweets.shape[0] > 0:
                logging.debug(
                    f"{target} Sample of tweets with sentiment: {processed_tweets.head(1)}"
                )
                processed_tweets_with_sentiment = add_sentiment_to_tweets(
                    processed_tweets, target_account
                )
                logging.debug(
                    f"{target} Sample of tweets with sentiment: {processed_tweets_with_sentiment.head(1)}"
                )
                insert_data(processed_tweets_with_sentiment)
        except tweepy.error.RateLimitError:
            logging.warning(f"{target} Rate Limit Error!")
            raise
        except Exception:
            logging.exception(
                f"{target} Could not retrieve tweets. Will retry in {5} seconds."
            )
            sleep(5)
        else:
            break
    logging.info(
        f"{target} Completed process. It took {(datetime.datetime.utcnow() - start_time).total_seconds()} seconds"
    )


if __name__ == "__main__":
    logging.basicConfig(
        filename=LOGS_PATH,
        filemode="w",
        format="[%(levelname)s] %(threadName)s %(asctime)s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    time.sleep(30)
    start_time = datetime.datetime.now()
    end_time = datetime.datetime.now() + datetime.timedelta(hours=12)
    while True:
        diff = (end_time - start_time).total_seconds()
        logging.info(f"Execution took {diff} seconds")
        if diff >= FETCH_INTERVAL:
            logging.info("Will start execution now")
            start_time = datetime.datetime.now()
            for target in TARGETS_DF.itertuples():
                main(target.id, target.account)
        else:
            logging.info(f"Will start execution in {FETCH_INTERVAL - diff} seconds")
            time.sleep(FETCH_INTERVAL - diff)
            start_time = datetime.datetime.now()
            for target in TARGETS_DF.itertuples():
                main(target.id, target.account)
        end_time = datetime.datetime.now()
