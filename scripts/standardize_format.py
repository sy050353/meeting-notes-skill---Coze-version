#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议纪要文件格式标准化脚本
将所有历史纪要文件统一为 RULES.md 规定的标准格式

用法：
    python standardize_format.py --meeting-dir /path/to/会议纪要
    python standardize_format.py --meeting-dir /path/to/会议纪要 --year 2026 --no-backup
"""

import os
import re
import glob
import argparse
from datetime import datetime


def backup_files(meeting_dir, backup_dir):
    """备份原始文件"""
    os.makedirs(backup_dir, exist_ok=True)
    files = glob.glob(os.path.join(meeting_dir, '2026-*.md'))
    files = [f for f in files if os.path.dirname(f) == meeting_dir]
    for f in files:
        basename = os.path.basename(f)
        backup_path = os.path.join(backup_dir, basename)
        with open(f, 'r', encoding='utf-8') as src:
            content = src.read()
        with open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(content)
    print(f"已备份 {len(files)} 个文件到 {backup_dir}")

def parse_meeting_notes(content, filename):
    """解析会议纪要内容，返回结构化数据"""
    lines = content.split('\n')
    meetings = []
    current_meeting = None
    current_status = '已发送'  # 默认状态，历史文件大多已发送
    in_meeting = False
    current_points = []
    current_fo = None
    current_title = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 跳过文件标题
        if line.startswith('# ') and '会议纪要' in line:
            i += 1
            continue

        # 跳过空行和分隔符
        if not line or line == '---':
            i += 1
            continue

        # 跳过二级标题中的纯中文
        if line.startswith('## ') and any('\u4e00' <= c <= '\u9fff' for c in line):
            # 检查是否是状态标记
            status_match = re.search(r'\[(已发送|待发送|发送失败)\]', line)
            if status_match:
                # 如果之前有正在处理的会议，先保存
                if current_title:
                    meetings.append({
                        'title': current_title,
                        'status': current_status,
                        'points': current_points,
                        'fo': current_fo
                    })
                current_status = status_match.group(1)
                # 检查这一行是否还包含标题
                title_part = re.sub(r'##\s*', '', line)
                title_part = re.sub(r'\[(已发送|待发送|发送失败)\]\s*', '', title_part).strip()
                if title_part and '|' in title_part:
                    current_title = title_part
                    current_points = []
                    current_fo = None
                    in_meeting = True
                else:
                    current_title = None
                    in_meeting = False
            i += 1
            continue

        # 检测会议标题行（包含 | 和 w/ 或 w\）
        is_title = False
        if ('|' in line and ('w/' in line or 'w\\' in line)):
            is_title = True
        elif line.startswith('**') and line.endswith('**') and '|' in line:
            is_title = True
        elif line.startswith('### ') and '|' in line:
            is_title = True

        if is_title:
            # 保存之前的会议
            if current_title:
                meetings.append({
                    'title': current_title,
                    'status': current_status,
                    'points': current_points,
                    'fo': current_fo
                })

            # 提取标题和状态
            clean_line = line
            clean_line = re.sub(r'^\*\*|\*\*$', '', clean_line)
            clean_line = re.sub(r'^###\s*', '', clean_line)
            clean_line = re.sub(r'^##\s*', '', clean_line)

            # 提取状态
            status_match = re.search(r'\[(已发送|待发送|发送失败)\]', clean_line)
            if status_match:
                current_status = status_match.group(1)
                clean_line = re.sub(r'\[(已发送|待发送|发送失败)\]\s*', '', clean_line)

            current_title = clean_line.strip()
            current_points = []
            current_fo = None
            in_meeting = True
            i += 1
            continue

        # F/O 行
        if in_meeting and (line.startswith('F/O:') or line.startswith('**F/O:**') or line.startswith('- F/O:')):
            fo_text = re.sub(r'^(\*\*F/O:\*\*|F/O:|- F/O:)\s*', '', line).strip()
            current_fo = fo_text
            i += 1
            continue

        # 要点行
        if in_meeting and line.startswith('- '):
            point = line[2:].strip()
            current_points.append(point)
            i += 1
            continue

        # 其他内容行
        if in_meeting and line and not line.startswith('#'):
            if current_points:
                pass
            i += 1
            continue

        i += 1

    # 保存最后一个会议
    if current_title:
        meetings.append({
            'title': current_title,
            'status': current_status,
            'points': current_points,
            'fo': current_fo
        })

    return meetings

def clean_title(title):
    """清理标题，移除具体时间，统一格式"""
    title = re.sub(r'([A-Z][a-z]{2}\s+\d{1,2})\s+\d{1,2}:\d{2}', r'\1', title)

    def pad_date(match):
        month = match.group(1)
        day = int(match.group(2))
        return f"{month} {day:02d}"

    title = re.sub(r'([A-Z][a-z]{2})\s+(\d{1,2})(?=\s|\|)', pad_date, title)
    title = re.sub(r'(上午|下午|中午|晚上)', '', title)
    title = re.sub(r'\s+', ' ', title).strip()

    return title

def format_meeting(meeting):
    """将单个会议格式化为标准格式"""
    title = clean_title(meeting['title'])
    status = meeting['status']
    points = meeting['points']
    fo = meeting['fo'] or 'good for now'

    lines = []
    lines.append(f"## [{status}]")
    lines.append("")
    lines.append(f"**{title}**")
    for point in points:
        lines.append(f"- {point}")
    lines.append("")
    lines.append(f"F/O: {fo}")

    return '\n'.join(lines)

def standardize_file(filepath):
    """标准化单个文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    filename = os.path.basename(filepath)
    meetings = parse_meeting_notes(content, filename)

    if not meetings:
        print(f"  [跳过] {filename}: 未解析到会议内容")
        return False

    # 按状态分组：待发送在前，已发送在后
    pending = [m for m in meetings if m['status'] == '待发送']
    sent = [m for m in meetings if m['status'] == '已发送']
    failed = [m for m in meetings if m['status'] == '发送失败']

    ordered_meetings = pending + failed + sent

    # 生成标准化内容
    output_parts = []
    for meeting in ordered_meetings:
        output_parts.append(format_meeting(meeting))

    output = '\n\n'.join(output_parts) + '\n'

    # 写回文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"  [完成] {filename}: {len(meetings)} 条纪要 (待发:{len(pending)} 已发:{len(sent)} 失败:{len(failed)})")
    return True

def main():
    parser = argparse.ArgumentParser(description='会议纪要文件格式标准化')
    parser.add_argument('--meeting-dir', required=True,
                        help='会议纪要数据目录路径')
    parser.add_argument('--year', default=None,
                        help='指定年份过滤（如 2026），不指定则处理所有年份')
    parser.add_argument('--no-backup', action='store_true',
                        help='跳过备份步骤')
    args = parser.parse_args()

    meeting_dir = args.meeting_dir
    backup_dir = os.path.join(meeting_dir, '备份_原始格式')

    print("=" * 60)
    print("会议纪要文件格式标准化")
    print(f"数据目录: {meeting_dir}")
    print("=" * 60)

    # 备份
    if not args.no_backup:
        print("\n[步骤1] 备份原始文件...")
        backup_files(meeting_dir, backup_dir)
    else:
        print("\n[步骤1] 跳过备份（--no-backup）")

    # 获取所有纪要文件
    if args.year:
        pattern = os.path.join(meeting_dir, f'{args.year}-*.md')
    else:
        pattern = os.path.join(meeting_dir, '2026-*.md')
    files = sorted(glob.glob(pattern))
    files = [f for f in files if os.path.dirname(f) == meeting_dir
             and re.match(r'\d{4}-\d{2}-\d{2}\.md$', os.path.basename(f))]
    print(f"\n[步骤2] 共找到 {len(files)} 个纪要文件")

    # 标准化
    print("\n[步骤3] 执行标准化...")
    success_count = 0
    skip_count = 0

    for f in files:
        if standardize_file(f):
            success_count += 1
        else:
            skip_count += 1

    print(f"\n完成: 成功 {success_count} 个, 跳过 {skip_count} 个")
    if not args.no_backup:
        print(f"  原始文件备份在: {backup_dir}")

if __name__ == '__main__':
    main()
