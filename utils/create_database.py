import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
TWEETS_DB = ROOT_DIR / "data" / "tweets.db"


def main():
    """Create database for storing Tweets"""
    conn = sqlite3.connect(TWEETS_DB)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS TWEETS")
    cur.execute(
        """
        CREATE TABLE TWEETS (
            ID INTEGER PRIMARY KEY,
            TWEET_ID INTEGER NOT NULL, 
            TARGET TEXT NOT NULL,
            INSERT_TIMESTAMP TEXT NOT NULL,
            FULL_TEXT TEXT,
            PROCESSED_TEXT TEXT,
            FOLLOWERS_COUNT INTEGER,
            FAVOURITES_COUNT INTEGER,
            FRIENDS_COUNT INTEGER,  
            TWEETS_COUNT INTEGER,
            ACCOUNT_CREATION_DATE TEXT,
            TWEET_TIMESTAMP TEXT NOT NULL,
            IS_RT INTEGER NOT NULL,
            SENTIMENT REAL
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IDX_TWEETS
        ON TWEETS(TWEET_TIMESTAMP, TARGET, IS_RT);
        """
    )
    conn.close()
    return


if __name__ == "__main__":
    main()
