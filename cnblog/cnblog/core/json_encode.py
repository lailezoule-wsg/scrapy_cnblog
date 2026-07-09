import json
from datetime import datetime, date

class ArticleTimeJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        # 如果还有其他不可序列化的类型，可以继续添加
        return super().default(o)