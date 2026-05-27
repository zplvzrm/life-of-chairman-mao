#!/usr/bin/env python3
"""
切分《毛泽东传》各册 PDF，按章节保存。
页码说明：marked_start 为书中标记页码，actual = marked - first_marked + first_actual。
"""

from pathlib import Path
import pypdf

INPUT_DIR = Path('/Users/zhangpeng/Data/studies/datas/chairManMao/Selected-Works-of-MaoTseTung-master/毛泽东传')
OUTPUT_DIR = Path('/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东传/textin/pdf')

BOOKS = [
    {
        'file': '毛泽东传_第一册.pdf',
        'first_marked': 1,
        'first_actual': 8,
        'last_actual': 463,
        'chapters': [
            ('一、出乡关', 1),
            ('二、师范生', 16),
            ('三、五四大潮的洗礼', 43),
            ('四、建党初期的实干家', 72),
            ('五、在国民党内工作', 92),
            ('六、走向农民运动', 110),
            ('七、霹雳一声暴动', 138),
            ('八、上井冈山', 161),
            ('九、开辟赣南、闽西根据地', 193),
            ('十、反对本本主义', 218),
            ('十一、不打南昌打吉安', 227),
            ('十二、打破三次\u201c围剿\u201d', 242),
            ('十三、中华苏维埃政府主席（上）', 270),
            ('十四、中华苏维埃政府主席（下）', 304),
            ('十五、长征', 338),
            ('十六、奠基西北', 373),
            ('十七、西安事变前后', 406),
            ('十八、总结历史经验', 437),
        ],
    },
    {
        'file': '毛泽东传_第二册.pdf',
        'first_marked': 457,
        'first_actual': 4,
        'last_actual': 509,
        'chapters': [
            ('十九、全民族抗战的爆发', 457),
            ('二十、指导敌后抗战和《论持久战》', 481),
            ('二十一、从十二月会议到六中全会', 503),
            ('二十二、反磨擦斗争', 538),
            ('二十三、新民主主义的理论', 562),
            ('二十四、皖南事变前后', 580),
            ('二十五、建设边区，战胜困难', 609),
            ('二十六、整风运动(上)', 633),
            ('二十七、整风运动(下)', 661),
            ('二十八、联合政府的主张', 683),
            ('二十九、争取抗战的最后胜利', 707),
            ('三十、重庆谈判', 733),
            ('三十一、和战之间的抉择', 751),
            ('三十二、全面内战爆发以后', 775),
            ('三十三、迎接中国革命的新高潮', 795),
            ('三十四、转入战略进攻', 815),
            ('三十五、东移西柏坡', 847),
            ('三十六、决战前夕', 865),
            ('三十七、大决战的日日夜夜(上)', 882),
            ('三十八、大决战的日日夜夜(下)', 896),
            ('三十九、将革命进行到底', 921),
            ('四十、筹建新中国', 947),
        ],
    },
    {
        'file': '毛泽东传_第三册.pdf',
        'first_marked': 963,
        'first_actual': 4,
        'last_actual': 462,
        'chapters': [
            ('四十一、中国人从此站立起来了', 963, 0),
            ('四十二、第一次访苏', 990, 0),
            ('四十三、为恢复国民经济而斗争', 1021, 0),  # 无编号插页是四十三的第一页，offset 从四十四起算
            ('四十四、抗美援朝(上)', 1069, -1),
            ('四十五、抗美援朝(下)', 1117, 0),
            ('四十六、\u201c三反\u201d\u201c五反\u201d', 1165, 0),
            ('四十七、过渡时期总路线(上)', 1198, 0),
            ('四十八、过渡时期总路线(下)', 1231, -1),
            ('四十九、新中国第一部宪法', 1270, 0),
            ('五十、开辟中国农业合作化道路（上）', 1305, -2),
            ('五十一、开辟中国农业合作化道路（下）', 1348, -1),
            ('五十二、成功地实现赎买政策', 1382, -1),
        ],
    },
    {
        'file': '毛泽东传_第四册.pdf',
        'first_marked': 1431,
        'first_actual': 4,
        'last_actual': 418,
        'chapters': [
            ('五十三、《论十大关系》到八大（上）', 1431, 0),
            ('五十四、《论十大关系》到八大（下）', 1471, 0),
            ('五十五、创造一个和平的国际环境', 1509, -1),
            ('五十六、《关于正确处理人民内部矛盾的问题》和整风反右（上）', 1565, -1),
            ('五十七、《关于正确处理人民内部矛盾的问题》和整风反右（下）', 1627, 0),
            ('五十八、第二次访苏', 1688, 0),
            ('五十九、发动\u201c大跃进\u201d（上）', 1727, 0),
            ('六十、发动\u201c大跃进\u201d（下）', 1770, -1),
            ('六十一、炮击金门', 1811, -1),
        ],
    },
    {
        'file': '毛泽东传_第五册.pdf',
        'first_marked': 1851,
        'first_actual': 4,
        'last_actual': 414,
        'chapters': [
            ('六十二、纠\u201c左\u201d的努力(上)', 1851),
            ('六十三、纠\u201c左\u201d的努力(下)', 1891, -1),
            ('六十四、庐山会议', 1920),
            ('六十五、庐山会议后的一年四个月（上）', 1978),
            ('六十六、庐山会议后的一年四个月(下)', 2017),
            ('六十七、大兴调查研究之风(上)', 2070, -5),
            ('六十八、大兴调查研究之风(下)', 2114, -2),
            ('六十九、七千人大会到八届十中全会（上）', 2149, -1),
            ('七十、七千人大会到八届十中全会(下)', 2185),
            ('七十一、中苏论战', 2227, -3),
        ],
    },
    {
        'file': '毛泽东传_第六册.pdf',
        'first_marked': 2275,
        'first_actual': 4,
        'last_actual': 493,
        'chapters': [
            ('七十二、社会主义教育运动(上)', 2275),
            ('七十三、社会主义教育运动(下)', 2312),
            ('七十四、发动\u201c文化大革命\u201d', 2355),
            ('七十五、支持\u201c红卫兵运动\u201d', 2400),
            ('七十六、在\u201c全面夺权\u201d的日子里', 2430),
            ('七十七、八届十二中全会到九大', 2479),
            ('七十八、林彪事件', 2523),
            ('七十九、一九七二年的内政和外交', 2573),
            ('八十、十大前后', 2611),
            ('八十一、批评\u201c四人帮\u201d', 2647),
            ('八十二、支持全面整顿到\u201c反击右倾翻案风\u201d', 2687),
            ('八十三、临终的日子', 2730),
        ],
    },
]


def marked_to_actual(marked: int, first_marked: int, first_actual: int) -> int:
    return marked - first_marked + first_actual


def split_book(book: dict):
    pdf_path = INPUT_DIR / book['file']
    if not pdf_path.exists():
        print(f'[跳过] 文件不存在: {pdf_path}')
        return

    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    print(f'\n处理: {book["file"]}  (共 {total_pages} 页)')

    chapters = book['chapters']
    first_marked = book['first_marked']
    first_actual = book['first_actual']
    last_actual = book['last_actual']

    extra_offset = 0
    for i, chapter in enumerate(chapters):
        name, marked_start = chapter[0], chapter[1]
        extra_offset += chapter[2] if len(chapter) > 2 else 0
        actual_start = marked_to_actual(marked_start, first_marked, first_actual) + extra_offset

        if i + 1 < len(chapters):
            next_chapter = chapters[i + 1]
            next_extra = extra_offset + (next_chapter[2] if len(next_chapter) > 2 else 0)
            actual_end = marked_to_actual(next_chapter[1], first_marked, first_actual) + next_extra - 1
        else:
            actual_end = last_actual

        page_start_0 = actual_start - 1
        page_end_0 = actual_end - 1

        if page_start_0 < 0 or page_end_0 >= total_pages or page_start_0 > page_end_0:
            print(f'  [错误] {name}: 页码越界 actual {actual_start}-{actual_end} (PDF共{total_pages}页)')
            continue

        writer = pypdf.PdfWriter()
        for p in range(page_start_0, page_end_0 + 1):
            writer.add_page(reader.pages[p])

        out_path = OUTPUT_DIR / f'{name}.pdf'
        with open(out_path, 'wb') as f:
            writer.write(f)

        page_count = actual_end - actual_start + 1
        print(f'  {name}: 实际页 {actual_start}-{actual_end} ({page_count}页) -> {out_path.name}')


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for book in BOOKS:
        split_book(book)
    print('\n全部完成！')


if __name__ == '__main__':
    main()
