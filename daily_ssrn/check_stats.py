#!/usr/bin/env python3
"""
检查Scrapy爬取统计信息的脚本 / Script to check Scrapy crawling statistics
用于获取去重检查的状态结果 / Used to get deduplication check status results

功能说明 / Features:
- 检查当日与昨日论文数据的重复情况 / Check duplication between today's and yesterday's paper data
- 删除重复论文条目，保留新内容 / Remove duplicate papers, keep new content
- 根据去重后的结果决定工作流是否继续 / Decide workflow continuation based on deduplication results
"""
import json
import sys
import os
import copy
from datetime import datetime, timedelta
import argparse


def load_papers_data(file_path):
    """
    从jsonl文件中加载完整的论文数据
    Load complete paper data from jsonl file
    
    Args:
        file_path (str): JSONL文件路径 / JSONL file path
        
    Returns:
        list: 论文数据列表 / List of paper data
        set: 论文ID集合 / Set of paper IDs
    """
    if not os.path.exists(file_path):
        return [], set()
    
    papers = []
    ids = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    papers.append(data)
                    ids.add(data.get('id', ''))
        return papers, ids
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return [], set()


def save_papers_data(papers, file_path):
    """
    保存论文数据到jsonl文件
    Save paper data to jsonl file
    
    Args:
        papers (list): 论文数据列表 / List of paper data
        file_path (str): 文件路径 / File path
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for paper in papers:
                f.write(json.dumps(paper, ensure_ascii=False) + '\n')
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}", file=sys.stderr)
        return False


def perform_deduplication(date):
    """
    执行多日去重：删除与历史多日重复的论文条目，保留新内容
    Perform deduplication over multiple past days
    
    Returns:
        str: 去重状态 / Deduplication status
             - "has_new_content": 有新内容 / Has new content
             - "no_new_content": 无新内容 / No new content  
             - "no_data": 无数据 / No data
             - "error": 处理错误 / Processing error
    """

    date_str = date
    date = datetime.strptime(date_str, "%Y-%m-%d")

    today_file = f"../data/{date_str}.jsonl"
    history_days = 7  # 向前追溯几天的数据进行对比

    if not os.path.exists(today_file):
        print("今日数据文件不存在 / Today's data file does not exist", file=sys.stderr)
        return "no_data"

    try:
        today_papers, today_ids = load_papers_data(today_file)
        print(f"今日论文总数: {len(today_papers)} / Today's total papers: {len(today_papers)}", file=sys.stderr)

        if not today_papers:
            return "no_data"

        # 收集历史多日 ID 集合
        history_ids = set()
        for i in range(1, history_days + 1):
            history_date_str = (date - timedelta(days=i)).strftime("%Y-%m-%d")
            history_file = f"../data/{history_date_str}.jsonl"
            _, past_ids = load_papers_data(history_file)
            history_ids.update(past_ids)

        print(f"历史{history_days}日去重库大小: {len(history_ids)} / History {history_days} days deduplication library size: {len(history_ids)}", file=sys.stderr)

        duplicate_ids = today_ids & history_ids

        if duplicate_ids:
            print(f"发现 {len(duplicate_ids)} 篇历史重复论文 / Found {len(duplicate_ids)} historical duplicate papers", file=sys.stderr)
            new_papers = [paper for paper in today_papers if paper.get('id', '') not in duplicate_ids]

            print(f"去重后剩余论文数: {len(new_papers)} / Remaining papers after deduplication: {len(new_papers)}", file=sys.stderr)

            if new_papers:
                if save_papers_data(new_papers, today_file):
                    print(f"已更新今日文件，移除 {len(duplicate_ids)} 篇重复论文 / Today's file updated, removed {len(duplicate_ids)} duplicate papers", file=sys.stderr)
                    return "has_new_content"
                else:
                    print("保存去重后的数据失败 / Failed to save deduplicated data", file=sys.stderr)
                    return "error"
            else:
                try:
                    os.remove(today_file)
                    print("所有论文均为重复内容，已删除今日文件 / All papers are duplicate content, today's file deleted", file=sys.stderr)
                except Exception as e:
                    print(f"删除文件失败: {e} / Failed to delete file: {e}", file=sys.stderr)
                return "no_new_content"
        else:
            print("所有内容均为新内容 / All content is new", file=sys.stderr)
            return "has_new_content"

    except Exception as e:
        print(f"去重处理失败: {e} / Deduplication processing failed: {e}", file=sys.stderr)
        return "error"


def perform_merge(date):
    '''
    执行单日去重，将不同类别下同一paper的条目合并为一个条目
    :return:
    '''
    date_str = date
    date = datetime.strptime(date_str, "%Y-%m-%d")

    today_file = f"../data/{date_str}.jsonl"

    if not os.path.exists(today_file):
        print("今日数据文件不存在 / Today's data file does not exist", file=sys.stderr)
        return "no_data"

    try:
        today_papers, today_ids = load_papers_data(today_file)
        print(f"今日论文总数: {len(today_papers)} / Today's total papers: {len(today_papers)}", file=sys.stderr)

        if not today_papers:
            return "no_data"

        merged = {}
        for item in today_papers:
            item_id = item['id']
            if item_id not in merged:
                # 创建副本并初始化 category 为列表
                merged[item_id] = copy.deepcopy(item)
            else:
                merged[item_id]['category'] += item.get('category', [])
        for v in merged.values():
            v['category'] = list(set(v['category']))
        result = list(merged.values())

        print(f"合并后论文数: {len(result)} / Merged papers count: {len(result)}", file=sys.stderr)
        if save_papers_data(result, today_file):
            print(f"已更新今日文件，合并重复条目 / Today's file updated, merged duplicate entries", file=sys.stderr)
            return "merge_success"
        else:
            print("保存合并后的数据失败 / Failed to save merged data", file=sys.stderr)
            return "error"
    except Exception as e:
        print(f"去重处理失败: {e} / Deduplication processing failed: {e}", file=sys.stderr)
        return "error"


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="jsonline data file")
    return parser.parse_args()


def main():
    """
    检查去重状态并返回相应的退出码
    Check deduplication status and return corresponding exit code
    
    退出码含义 / Exit code meanings:
    0: 有新内容，继续处理 / Has new content, continue processing
    1: 无新内容，停止工作流 / No new content, stop workflow
    2: 处理错误 / Processing error
    """
    # date = datetime.now().strftime("%Y-%m-%d")
    date = parse_args().date

    # 合并今日论文条目 / Merge today's paper entries
    print("正在执行今日论文条目合并... / Performing today's paper entries merge...", file=sys.stderr)
    merge_status = perform_merge(date)

    if merge_status == "merge_success":
        print("✅ 今日论文条目合并成功 / Today's paper entries merged successfully", file=sys.stderr)
    elif merge_status == "no_data":
        print("⏹️ 今日无数据，停止工作流 / No data today, stop workflow", file=sys.stderr)
        sys.exit(1)
    elif merge_status == "error":
        print("❌ 今日论文条目合并处理出错，停止工作流 / Today's paper entries merge processing error, stop workflow", file=sys.stderr)
        sys.exit(2)
    else:
        # 意外情况：未知状态 / Unexpected case: unknown status
        print("❌ 未知合并状态，停止工作流 / Unknown merge status, stop workflow", file=sys.stderr)
        sys.exit(2)

    # 执行去重处理 / Perform deduplication processing
    print("正在执行去重检查... / Performing intelligent deduplication check...", file=sys.stderr)
    dedup_status = perform_deduplication(date)
    
    if dedup_status == "has_new_content":
        print("✅ 去重完成，发现新内容，继续工作流 / Deduplication completed, new content found, continue workflow", file=sys.stderr)
        sys.exit(0)
    elif dedup_status == "no_new_content":
        print("⏹️ 去重完成，无新内容，停止工作流 / Deduplication completed, no new content, stop workflow", file=sys.stderr)
        sys.exit(1)
    elif dedup_status == "no_data":
        print("⏹️ 今日无数据，停止工作流 / No data today, stop workflow", file=sys.stderr)
        sys.exit(1)
    elif dedup_status == "error":
        print("❌ 去重处理出错，停止工作流 / Deduplication processing error, stop workflow", file=sys.stderr)
        sys.exit(2)
    else:
        # 意外情况：未知状态 / Unexpected case: unknown status
        print("❌ 未知去重状态，停止工作流 / Unknown deduplication status, stop workflow", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()