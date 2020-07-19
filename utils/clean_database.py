import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
TWEETS_DB = ROOT_DIR / "data" / "tweets.db"


def main():
    """Create database for storing Tweets"""
    conn = sqlite3.connect(TWEETS_DB)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM TWEETS WHERE DATE(TWEET_TIMESTAMP) < date('now', '-2 days')"
    )
    conn.close()
    return


if __name__ == "__main__":
    main()
