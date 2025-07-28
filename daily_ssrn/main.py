from scrapy.cmdline import execute


if __name__ == "__main__":
    date = "2025-07-22"  # 目标日期
    execute([
        "scrapy", "crawl", "ssrn",
        "-o", f"../data/{date}.jsonl",
        "-a", f"DATE={date}"  # 整个参数作为一个字符串
    ])