#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议纪要月度索引生成脚本
生成按月的纪要目录索引，方便快速查找

用法：
    python generate_index.py --meeting-dir /path/to/会议纪要
    python generate_index.py --meeting-dir /path/to/会议纪要 --year 2026
"""

import os
import re
import glob
import argparse
from collections import defaultdict


def parse_meetings_from_file(filepath):
    """从标准化后的文件中提取会议信息"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    meetings = []
    current_status = None
    current_title = None

    lines = content.split('\n')
    for line in lines:
        line = line.strip()

        # 状态行
        status_match = re.match(r'## \[(已发送|待发送|发送失败)\]', line)
        if status_match:
            current_status = status_match.group(1)
            continue

        # 标题行
        title_match = re.match(r'\*\*(.+?)\*\*', line)
        if title_match and current_status:
            current_title = title_match.group(1)
            # 提取产品名（标题的第一个 | 之前的部分）
            product = current_title.split('|')[0].strip()
            # 提取参会方（w/ 之后的部分）
            contact = ''
            w_match = re.search(r'w/\s*(.+)', current_title)
            if w_match:
                contact = w_match.group(1).strip()

            meetings.append({
                'title': current_title,
                'status': current_status,
                'product': product,
                'contact': contact
            })

    return meetings

def generate_monthly_index(year_month, files):
    """生成单月索引"""
    all_meetings = []

    for f in sorted(files):
        date = os.path.basename(f).replace('.md', '')
        meetings = parse_meetings_from_file(f)
        for m in meetings:
            m['date'] = date
            all_meetings.append(m)

    # 生成索引内容
    lines = []
    lines.append(f"# {year_month} 会议纪要索引")
    lines.append("")
    lines.append(f"> 共 {len(all_meetings)} 条纪要，{len(files)} 个会议日")
    lines.append("")

    # 按日期分组
    lines.append("## 按日期")
    lines.append("")
    current_date = None
    for m in all_meetings:
        if m['date'] != current_date:
            current_date = m['date']
            lines.append(f"### {current_date}")
            lines.append("")
        status_icon = {'已发送': '✅', '待发送': '⏳', '发送失败': '❌'}.get(m['status'], '❓')
        lines.append(f"- {status_icon} **{m['product']}** — w/ {m['contact']}")
    lines.append("")

    # 按产品分组
    lines.append("## 按产品/主题")
    lines.append("")
    by_product = defaultdict(list)
    for m in all_meetings:
        product_key = m['product']
        # 处理一些常见变体
        if 'EMSX API' in product_key:
            product_key = 'EMSX API'
        elif 'EMSX' in product_key:
            product_key = 'EMSX'
        elif 'RFQE' in product_key:
            product_key = 'RFQE'
        elif 'RBLD' in product_key:
            product_key = 'RBLD'
        elif 'FIXNET' in product_key:
            product_key = 'FIXNET'
        elif 'BTCA' in product_key:
            product_key = 'BTCA'
        elif 'Tradebook' in product_key or 'TBK' in product_key or 'TRADE BOOK' in product_key:
            product_key = 'Tradebook'
        elif 'Oplus' in product_key:
            product_key = 'Oplus'

        by_product[product_key].append(m)

    for product in sorted(by_product.keys()):
        meetings = by_product[product]
        lines.append(f"### {product} ({len(meetings)} 条)")
        lines.append("")
        for m in meetings:
            status_icon = {'已发送': '✅', '待发送': '⏳', '发送失败': '❌'}.get(m['status'], '❓')
            lines.append(f"- {status_icon} {m['date']} — w/ {m['contact']}")
        lines.append("")

    # 按参会方分组
    lines.append("## 按参会方")
    lines.append("")
    by_contact = defaultdict(list)
    for m in all_meetings:
        contact = m['contact']
        # 简化参会方
        if 'PM' in contact and 'Market Maker' not in contact:
            contact_key = 'PM (基金经理)'
        elif 'Market Maker' in contact or 'MM' in contact:
            contact_key = 'Market Maker (做市商)'
        elif 'Trader' in contact or 'trader' in contact:
            contact_key = 'Trader (交易员)'
        elif 'IT' in contact:
            contact_key = 'IT Team'
        elif 'Operations' in contact or 'Ops' in contact:
            contact_key = 'Operations'
        elif 'Sales' in contact:
            contact_key = 'Sales'
        elif 'Compliance' in contact or 'compliance' in contact:
            contact_key = 'Compliance'
        else:
            contact_key = contact

        by_contact[contact_key].append(m)

    for contact in sorted(by_contact.keys()):
        meetings = by_contact[contact]
        lines.append(f"### {contact} ({len(meetings)} 条)")
        lines.append("")
        for m in meetings:
            status_icon = {'已发送': '✅', '待发送': '⏳', '发送失败': '❌'}.get(m['status'], '❓')
            lines.append(f"- {status_icon} {m['date']} — {m['product']}")
        lines.append("")

    return '\n'.join(lines) + '\n'

def generate_master_index(monthly_indices):
    """生成总索引"""
    lines = []
    lines.append("# 会议纪要总索引")
    lines.append("")
    lines.append("> 按月份快速跳转")
    lines.append("")

    total_meetings = 0
    for year_month, count in sorted(monthly_indices.items(), reverse=True):
        lines.append(f"- [{year_month}](./{year_month}.md) — {count} 条纪要")
        total_meetings += count

    lines.append("")
    lines.append(f"**总计：{total_meetings} 条纪要，{len(monthly_indices)} 个月**")
    lines.append("")

    return '\n'.join(lines) + '\n'

def main():
    parser = argparse.ArgumentParser(description='生成会议纪要月度索引')
    parser.add_argument('--meeting-dir', required=True,
                        help='会议纪要数据目录路径')
    parser.add_argument('--year', default=None,
                        help='指定年份过滤（如 2026），不指定则处理所有年份')
    args = parser.parse_args()

    meeting_dir = args.meeting_dir
    index_dir = os.path.join(meeting_dir, '索引')

    print("=" * 60)
    print("生成会议纪要月度索引")
    print(f"数据目录: {meeting_dir}")
    print("=" * 60)

    # 创建索引目录
    os.makedirs(index_dir, exist_ok=True)

    # 获取所有纪要文件
    if args.year:
        pattern = os.path.join(meeting_dir, f'{args.year}-*.md')
    else:
        pattern = os.path.join(meeting_dir, '*.md')
    files = sorted(glob.glob(pattern))

    # 排除索引目录下的文件和非日期命名的文件
    files = [f for f in files if os.path.dirname(f) == meeting_dir
             and re.match(r'\d{4}-\d{2}-\d{2}\.md$', os.path.basename(f))]

    # 按月份分组
    by_month = defaultdict(list)
    for f in files:
        basename = os.path.basename(f)
        year_month = basename[:7]  # 2026-04
        by_month[year_month].append(f)

    print(f"\n共 {len(files)} 个文件，{len(by_month)} 个月")

    # 生成每月索引
    monthly_counts = {}
    for year_month in sorted(by_month.keys()):
        month_files = by_month[year_month]
        index_content = generate_monthly_index(year_month, month_files)

        index_path = os.path.join(index_dir, f'{year_month}.md')
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)

        # 统计会议数量
        count = sum(len(parse_meetings_from_file(f)) for f in month_files)
        monthly_counts[year_month] = count
        print(f"  {year_month}: {count} 条纪要 -> 索引已生成")

    # 生成总索引
    master_index = generate_master_index(monthly_counts)
    master_path = os.path.join(index_dir, 'README.md')
    with open(master_path, 'w', encoding='utf-8') as f:
        f.write(master_index)

    print(f"\n总索引已生成: {master_path}")
    print(f"完成! 索引文件都在 {index_dir}")

if __name__ == '__main__':
    main()
