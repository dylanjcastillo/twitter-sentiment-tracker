import pandas as pd
import sqlite3
from pathlib import Path
import joblib
from fetch_tweets import (
    add_sentiment_to_tweets,
    extract_tweets_data,
    get_latest_tweets,
    process_text,
    insert_data,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
SAMPLE_TWEETS = DATA_DIR / "sample_tweets.joblib"
TWEETS_DB = DATA_DIR / "tweets.db"

TARGET = "pablo_casado"
TARGET_ACCOUNT = "pablocasado_"
DOWNLOAD_SAMPLE_TWEETS = False


def test_get_latest_tweets():
    """Check if downloading tweets using Tweepy works"""
    if DOWNLOAD_SAMPLE_TWEETS:
        latest_tweets, api_limits = get_latest_tweets(TARGET_ACCOUNT, 1)
        joblib.dump(latest_tweets, SAMPLE_TWEETS)
    assert Path(SAMPLE_TWEETS).is_file()


def test_process_text():
    """Check if the pre-processing text function works as expected"""
    df = pd.DataFrame(
        {
            "text": [
                "this text has an url: http://hello.com",
                "this text has an 🥑",
                "this text has a 🙄",
                "this text has a #hashtag",
                "this text has a @mention",
                "¿¿??!!this text has... punctuation!! éáó,",
                "RT this text is a RT",
                "this text has multiple      spaces",
            ]
        }
    )
    assert process_text(df["text"])[0] == "this text has an url"
    assert process_text(df["text"])[1] == "this text has an aguacate"
    assert process_text(df["text"])[2] == "this text has a cara con los ojos en blanco"
    assert process_text(df["text"])[3] == "this text has a hashtag"
    assert process_text(df["text"])[4] == "this text has a"
    assert process_text(df["text"])[5] == "this text has punctuation éáó"
    assert process_text(df["text"])[6] == "this text is a rt"
    assert process_text(df["text"])[7] == "this text has multiple spaces"


def test_extract_tweets_data():
    """Checks if extracting the relevant fields from the API response works as expected"""
    tweets_sample = joblib.load(SAMPLE_TWEETS)
    tweets = extract_tweets_data(tweets_sample, TARGET, TARGET_ACCOUNT)
    columns = [
        "TWEET_ID",
        "TARGET",
        "INSERT_TIMESTAMP",
        "FULL_TEXT",
        "PROCESSED_TEXT",
        "FOLLOWERS_COUNT",
        "FAVOURITES_COUNT",
        "FRIENDS_COUNT",
        "TWEETS_COUNT",
        "ACCOUNT_CREATION_DATE",
        "TWEET_TIMESTAMP",
        "IS_RT",
    ]

    assert (tweets.isna().sum() == 0).all()
    assert (tweets.columns == columns).all()


def test_add_sentiment_to_tweets():
    """Checks if the sentiment service works as expected"""
    tweets_sample = joblib.load(SAMPLE_TWEETS)
    tweets = extract_tweets_data(tweets_sample, TARGET, TARGET_ACCOUNT)
    print(tweets.columns)
    tweets_with_sentiment = add_sentiment_to_tweets(tweets, TARGET_ACCOUNT)
    columns = [
        "TWEET_ID",
        "TARGET",
        "INSERT_TIMESTAMP",
        "FULL_TEXT",
        "PROCESSED_TEXT",
        "FOLLOWERS_COUNT",
        "FAVOURITES_COUNT",
        "FRIENDS_COUNT",
        "TWEETS_COUNT",
        "ACCOUNT_CREATION_DATE",
        "TWEET_TIMESTAMP",
        "IS_RT",
        "SENTIMENT",
    ]
    assert (tweets_with_sentiment.columns == columns).all()
    assert (tweets_with_sentiment.isna().sum() == 0).all()


def test_insert_tweets_in_db():
    """Check if it is possible to insert tweets into the db"""
    tweets_sample = joblib.load(SAMPLE_TWEETS)
    tweets = extract_tweets_data(tweets_sample, TARGET, TARGET_ACCOUNT)
    tweets_with_sentiment = add_sentiment_to_tweets(tweets, TARGET_ACCOUNT)
    insert_data(tweets_with_sentiment)
    conn = sqlite3.connect(TWEETS_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM TWEETS WHERE TWEET_ID=1284798583040913410;")
    count = cur.fetchone()[0]
    assert count == 1
