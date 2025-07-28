import scrapy
import os
import xmltodict
import datetime


class SsrnSpider(scrapy.Spider):
    name = "ssrn"
    allowed_domains = ["ssrn.com"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 获得参数
        categories = kwargs.get('CATEGORIES', "IS,MKT,ECON,MG")
        date = kwargs.get('DATE', datetime.datetime.now().strftime("%Y-%m-%d"))

        self.target_categories = set(map(str.strip, categories.split(",")))
        self.date = datetime.datetime.strptime(date, "%Y-%m-%d")
        self.date_str = self.date.strftime("%d %b %Y")

        self.category2id = {
            'IS': 304241,
            'MKT': 298223,
            'AC': 204,
            'CS': 2894322,
            'ECON': 205,
            'FE': 203,
            'MG': 200668,
        }

    def start_requests(self):
        for cat in self.target_categories:
            yield scrapy.Request(
                url=self.build_url(cat, index=0),
                callback=self.parse,
                meta={'category': cat, 'index': 0}
            )

    def build_url(self, cat, index):
        cat_id = self.category2id[cat]
        return f"https://api.ssrn.com/content/v1/bindings/{cat_id}/papers?index={index}&count=50&sort=0"

    def parse(self, response):
        data = xmltodict.parse(response.text)
        category = response.meta.get('category')
        index = response.meta.get('index')

        papers = data.get("PaperResultSet", {}).get("papers", {}).get("papers", [])

        # 处理日期
        approved_dates = []
        for paper in papers:
            approved_date = paper.get("approved_date", "").strip()
            if approved_date:
                approved_dates.append(datetime.datetime.strptime(approved_date, "%d %b %Y"))

        if min(approved_dates) > self.date:
            # 如果最早的批准日期都晚于目标日期，则爬取下一页
            yield scrapy.Request(
                url=self.build_url(category, index + 50),
                callback=self.parse,
                meta={'category': category, 'index': index + 50}
            )
        elif max(approved_dates) < self.date:
            # 如果最新的批准日期都早于目标日期，则不爬取
            return
        else:
            for paper in papers:
                paper['category'] = [category,]

                approved_date = paper.get("approved_date", "").strip()
                if approved_date != self.date_str:
                    continue

                detail_url = f"https://api.ssrn.com/papers/v1/papers/{paper['id']}"
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    meta={'paper': paper}
                )
            yield scrapy.Request(
                url=self.build_url(category, index + 50),
                callback=self.parse,
                meta={'category': category, 'index': index + 50}
            )

    def parse_detail(self, response):
        paper = response.meta['paper']
        detail = xmltodict.parse(response.text)
        detail = detail.get("PaperJson", {})
        paper['detail'] = detail
        yield paper
