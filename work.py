import json
import operator
import pathlib
import re
import time
import uuid
from functools import reduce
from pprint import pprint
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem.wordnet import WordNetLemmatizer
from termcolor import colored
import demoji
import enchant
import tweepy
from tweepy import OAuthHandler, Stream
from tweepy.streaming import StreamListener
from log import *
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


demoji.download_codes()
# neg : Negative. neu : Neutral. pos : Positive. compound : Compound (i.e. aggregated score)

TASK_HASH = uuid.uuid4().hex[:6]
API_KEY = "9z8OcETOR2XAlFFoiXJaRJdQk"
API_SECRET = "Qg6VavLuqaXBTemWob7a9Wvo5w6IdTPlW0e1nEyepe4LvdTg4k"
ACCESS_TOKEN = "1232002559042359298-8tVta4ifiaIPV7Ho0V6XEV21YPsRr5"
ACCESS_SECRET = "b7K0SokRBLQHWnDjV5MhGUvOMRCe8LgEGszwTO1VrYeQg"

AUTH = OAuthHandler(API_KEY, API_SECRET)
AUTH.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)

DATA_PATH = pathlib.Path("datas")
DATA_PATH.mkdir(exist_ok=True)


WORDS_CHECKER = enchant.Dict("en_US")  # CHECK WORDS
EMOTIONS_ANALYSER = SentimentIntensityAnalyzer()  # SCORE


# emoji type source https://emojipedia.org/search/?q=
TWITTER_EMOJI_TYPES_REG = {
    "excitement": {
        "reg": re.compile("[😎👻]*"),
        "rank": lambda _: _["compound"] >= 0.3,
        "color": "cyan",
    },
    "happy": {
        "reg": re.compile("[😛🤗😂🤣]*"),
        "rank": lambda _: _["compound"] >= 0.3,
        "color": "blue",
    },
    "pleasant": {
        "reg": re.compile("[😌🤥]*"),
        "rank": lambda _: _["compound"] >= 0,
        "color": "green",
    },
    "suprise": {
        "reg": re.compile("[😱😵🤯😩😔😿😫😰😶🙄🤦😕😑💀😐💔]*"),
        "rank": lambda _: _["compound"] < 0,
        "color": "magenta",
    },
    "fear": {
        "reg": re.compile("[🤮🤢😞💩]*"),
        "rank": lambda _: True,  # lambda _: _["compound"] < 0),
        "color": "yellow",
    },
    "angry": {
        "reg": re.compile("[💢😠👿😡🤬]*"),
        "rank": lambda _: True,  # _["compound"] <= -0.3),
        "color": "red",
    },
}  # emoji
TEXT_REG = {
    "href_reg": re.compile(
        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    ),
    "#_tag_reg": re.compile("#[0-9a-zA-Z]+"),
    "@_tag_reg": re.compile("@[0-9a-zA-Z]+"),
    "rt_tag_reg": re.compile("rt [@a-zA-Z_]{0,10}:"),
}  # 过滤正则


SAVE_ONLY_TEXT = True  # 是否只保存推文
DEBUG = True  # 是否开启debug , 开启后会无限爬取！！
ITEM_MAX = 150  # 单类项数量
MAX_TWEETS = len(TWITTER_EMOJI_TYPES_REG) * ITEM_MAX  # 最大推文量
SAVED_NUMS = 0  # 已过滤的推文数量
RUNED_NUMS = 0  # 已爬行的推文总量
TWEETS = {}  # 过滤后的推文集合
TWEETS_RAW = []  # 原推文数据
TWEETS_RAW_SAVED_LIMIT = 1000


def words_clean(text):  # delete hashtag
    text = text.lower()  # lower words
    text = demoji.replace(text)  #delete emoji
    for k, v in TEXT_REG.items():
        text = v.sub("", text)  

    words = [
        WordNetLemmatizer().lemmatize(
            (
                (word if WORDS_CHECKER.check(word) else WORDS_CHECKER.suggest(word)[0])
                if word.isalpha()
                else word
            ),
            pos="v",
        )  # correct words
        for word in word_tokenize(text)
        if word not in stopwords.words("english")
    ]
    for word in words:
        word = word.strip()
        if len(word) > 1 and word.isalpha():
            yield word.lower()


def eprint(text, emj=""):
    if emj:
        print(
            f"[{RUNED_NUMS}]->{SAVED_NUMS}/{MAX_TWEETS} "
            + colored(f"({emj}): " + text, TWITTER_EMOJI_TYPES_REG[emj]["color"])
        )
    else:
        print(text)


def remote_empty(items):  # 这个方法将去除所有的空值
    return [_ for _ in items if _.strip()]


def analysis(words):  # 一个分析方法，判断是否存在某些类的表情
    score = EMOTIONS_ANALYSER.polarity_scores(words)
    for key, method in TWITTER_EMOJI_TYPES_REG.items():
        tags = remote_empty(method["reg"].findall(words))
        if tags and method["rank"](score):
            yield key


def get_full_text(data):  # 获得全文
    try:
        root = data["retweeted_status"]
        return (root if "full_text" in root else data["extended_tweet"])["full_text"]
    except Exception as e:
        return data["text"]


class Monitor(StreamListener):
    def on_data(self, data):
        global SAVED_NUMS
        global RUNED_NUMS
        RUNED_NUMS += 1

        if len(TWEETS_RAW) % TWEETS_RAW_SAVED_LIMIT == 0:
            file = pathlib.Path("raw.txt")
            with file.open("a") as f:
                f.write("\n".join(map(repr, TWEETS_RAW)))
                warning(f"saved raw: {file}")

        if SAVED_NUMS >= MAX_TWEETS and not DEBUG:  # 超过900条的时候回退出
            return False

        try:
            data = json.loads(data)
            text = get_full_text(data)
            TWEETS_RAW.append(text)
            emotions = list(analysis(text))
            if len(emotions) == 1:  # 如果只有一种属性，那就准备存储
                key = emotions[0]  # 获取属性名称
                words = list(words_clean(data["text"]))
                if len(words) < 2:  # 如果句子长度小于2 ，丢弃
                    return True
                data["text"] = " ".join(words)
                eprint(f"{data['user']['screen_name']}: {data['text']}", key)
                result = data["text"] if SAVE_ONLY_TEXT else data
                if key not in TWEETS:  # 判断在TWEETS中是否已经创建
                    TWEETS[key] = {result}  # 没有创建的话初始化创建
                    SAVED_NUMS += 1
                elif len(TWEETS[key]) < ITEM_MAX or DEBUG:  # 如果有且少于150条的话就存入
                    TWEETS[key].add(result)
                    SAVED_NUMS += 1
                    if len(TWEETS[key]) == ITEM_MAX:  # 如果每一项已经结束 那就更新过滤器
                        TWITTER_EMOJI_TYPES_REG.pop(key)
                        return False

            return True
        except Exception as e:
            error(e)
            # raise e
            time.sleep(1)

    def on_status(self, status):
        if status_code == 420:
            error("limited")
            return False
        return True


def main():
    try:
        while SAVED_NUMS < MAX_TWEETS or DEBUG:  # 当数量未满足时继续
            QUERYS = reduce(
                operator.add,
                [[key, f"#{key}"] for key in TWITTER_EMOJI_TYPES_REG.keys()],
            )  # 获取当前任务hashtag 及关键字
            try:
                worker = Monitor()  # 设定监听器
                info(f"querys: {QUERYS}")
                stream = Stream(AUTH, worker)
                stream.filter(track=QUERYS, languages=["en"])
            except KeyboardInterrupt:
                break
            except Exception as e:
                error(e)
                raise e
                time.sleep(5)
            finally:
                info(f"run tweets: {SAVED_NUMS}/{RUNED_NUMS}")
    finally:
        if TWEETS:
            file = (
                DATA_PATH
                / f"{TASK_HASH}{'_text' if SAVE_ONLY_TEXT else ''}_{len(TWEETS)}.json"
            )  # 保存结果
            with file.open("w") as f:
                f.write(
                    json.dumps(
                        {key: list(val) for key, val in TWEETS.items()},
                        indent=4,
                        ensure_ascii=False,
                    )
                )
                success(f"saved: {file}")


if __name__ == "__main__":
    main()
