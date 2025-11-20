import pymongo
import redis
import os
from datetime import datetime

POSITIVE_WORDS = {'tốt', 'ngon', 'tuyệt', 'ngon tuyệt', 'xuất sắc', 'hài lòng', 'thích', 'đẹp', 'chất lượng', 'rất tốt'}
NEGATIVE_WORDS = {'tệ', 'dở', 'kém', 'không ngon', 'tồi', 'bình thường', 'không thích', 'xấu'}

def analyze_comment(comment):
    if not comment or not isinstance(comment, str):
        return 0
    comment = comment.lower()
    positive_score = sum(1 for word in POSITIVE_WORDS if word in comment)
    negative_score = sum(1 for word in NEGATIVE_WORDS if word in comment)
    return positive_score - negative_score

def connect_to_mongo():
    MONGODB_URI = f"mongodb+srv://{os.getenv('MONGODB_USERNAME')}:{os.getenv('MONGODB_PASSWORD')}@webbuycake.asd8v.mongodb.net/?retryWrites=true&w=majority&appName=WebBuyCake"
    DB_NAME = os.getenv('MONGODB_DATABASE', 'test')  # Sử dụng database name từ env, mặc định là 'test'
    try:
        client = pymongo.MongoClient(MONGODB_URI)
        db = client[DB_NAME]
        db.command("ping")
        print(f"Kết nối MongoDB thành công! Database: {DB_NAME}")
        return db
    except Exception as e:
        print(f"Lỗi kết nối MongoDB: {e}")
        return None

def connect_to_redis():
    try:
        redis_client = redis.Redis(
            host=os.getenv('UPSTASH_REDIS_HOST'),
            port=int(os.getenv('UPSTASH_REDIS_PORT')),
            password=os.getenv('UPSTASH_REDIS_PASSWORD'),
            ssl=True,
            decode_responses=True
        )
        redis_client.ping()
        print("Kết nối Upstash Redis thành công!")
        return redis_client
    except Exception as e:
        print(f"Không kết nối được Upstash Redis: {e}")
        return None