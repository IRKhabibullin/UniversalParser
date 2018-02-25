# -*- coding: utf-8 -*-
import re
from urllib.parse import urlparse

import requests
from lxml import etree

# TODO read from config and config format is .cfg
from lxml.html.clean import Cleaner

line_len = 80
stopwords = ['adv', 'rule', 'footer', 'info', 'sidebar', 'nav', 'tabl', 'menu',
             'favorite', 'login', 'sign', 'other', 'board', 'social', 'relat',
             'rating', 'ban', 'categor', 'more', 'top-bar', 'panel',
             'headline',
             # weak stopwords
             'tag', 'photo', 'add', 'title', 'sub', 'right', 'comment']
# good_words = ['article', 'body', 'topic', 'content', 'story', 'post']
cleaner = Cleaner(links=False, style=True, inline_style=False)


def get_title(html):
    page_title = html.xpath("//meta[@property='og:title']/@content")
    if not page_title:
        # page_titles = []
        # elems = html.xpath("//h1|//p|//div")
        # for elem in elems:
        #     try:
        #         if 'title' in elem.attrib['class']:
        #             if any(kw in elem.attrib['class'] for kw in
        #                    ['article', 'post', 'story', 'topic']):
        #                 page_titles.append(elem)
        #     except KeyError:
        #         pass
        page_title = html.xpath('//title')[0].text
    else:
        page_title = page_title[0]
    return page_title


def parse(url):
    html_text = requests.get(url).text
    page_title = get_title(etree.HTML(html_text))
    response = etree.HTML(cleaner.clean_html(html_text))
    article = response.xpath('//article')
    if article:
        print('article')
        response = article[0]
    ps = response.xpath('//p|//h1|//div')
    ps = filter_elements(ps)
    paragraphs = []
    for p in ps:
        # paragraph_text = ''
        # if p.text is not None:
        #     paragraph_text += p.text.strip()
        # for child in p.iterchildren():
        #     if child in ps:
        #         ps.remove(child)
        #     t = child.text
        #     if t is not None:
        #         paragraph_text += ' ' + t.strip()
        #     if child.tag == 'a':
        #         try:
        #             a_url = child.attrib['href']
        #             a_text = get_deep_text(child)
        #             if a_text:
        #                 paragraph_text += a_text
        #             if check_url(a_url):
        #                 paragraph_text += ' [' + a_url + ']'
        #         except KeyError:
        #             print('href error:', child.attrib)
        #     t = child.tail
        #     if t is not None:
        #         paragraph_text += ' ' + t.strip()
        # paragraphs.append(paragraph_text)
        if is_valid(p, True):
            t = get_text(p, ps, True)
            if t:
                paragraphs.append(t)
    return page_title, paragraphs


def filter_elements(elements):
    filtered = []
    for element in elements:
        parent = element.getparent()
        if parent is not None:
            if parent.tag not in ['div', 'h1', 'h2', 'p']:
                continue
        if not is_valid(element, True):
            continue
        filtered.append(element)
    print('{} elements filtered to {}'.format(len(elements), len(filtered)))
    return filtered


def format_article(title, ps):
    formatted_article = split_by_len(title)
    formatted_article.append('\n')
    for p in ps:
        formatted_article += split_by_len(p)
        formatted_article.append('')
    formatted_article.append('\n\n--------------------------------------------')
    return formatted_article


def split_by_len(text):
    words = text.split(' ')
    formatted_text = []
    line = ''
    for word in words:
        if not word:
            continue
        is_new_line = False
        if len(word) > 400:
            word = '[очень_длинная_ссылка]'
        try:
            if word[-1] == '\n':
                word = word.strip('\n')
                is_new_line = True
        except IndexError:
            print('index error', '|' + word + '|')
        if len(line) + len(word) <= line_len - 1:
            line += (' ' if line else '') + word
        else:
            if len(word) >= line_len:
                divided, line = split_large_word(line, word)
                formatted_text += divided
            else:
                formatted_text.append(line)
                line = word
        if is_new_line:
            formatted_text.append(line)
            line = ''
    if line:
        formatted_text.append(line)
    return formatted_text


def split_large_word(line, word):
    divided_word = []
    first_part_len = line_len - len(line) - 1
    if first_part_len < 3:
        first_part_len = 0
        divided_word.append(line)
        line = ''
    else:
        divided_word.append(
            line + (' ' if line else '') + word[:first_part_len])
    for w in [word[i:i + line_len] for i in
              range(first_part_len, len(word), line_len)]:
        if len(w) > line_len - 3:
            divided_word.append(w)
        else:
            line = w
    return divided_word, line


def is_valid(element, deep=False):
    try:
        if 'display:none' in element.attrib['style'] or \
                        'display: none' in element.attrib['style']:
            return False
    except KeyError:
        pass
    try:
        if any(kw in element.attrib['class'] for kw in stopwords):
            return False
    except KeyError:
        pass
    try:
        if any(kw in element.attrib['id'] for kw in stopwords):
            return False
    except KeyError:
        pass
    if deep:
        try:
            parent = element.getparent()
            if parent is not None:
                return is_valid(parent, True)
        except KeyError:
            pass
    return True


def check_url(url):
    try:
        requests.get(url)
    except Exception:
        return False
    return True


def get_text(element, page_elements, deep=False):
    text = ''
    try:
        e_text = element.text.strip().replace('\n', ' ')
        if e_text:
            text += ' ' + e_text
    except AttributeError:
        pass
    if element.tag == 'a':
        try:
            a_url = element.attrib['href']
            if check_url(a_url):
                text += ' [' + a_url + ']'
        except KeyError:
            print('href error:', element.attrib)
    if deep:
        for child in element.getchildren():
            if child.tag != 'div' and is_valid(child, False):
                if child not in page_elements:
                    text += get_text(child, page_elements, True)
    if element.tag == 'br':
        text += '\n'
    try:
        e_tail = element.tail.strip().replace('\n', ' ')
        if e_tail:
            text += ' ' + e_tail
    except AttributeError:
        pass
    return text


def save_article(url, article):
    parsed = urlparse(url)
    print(parsed)
    print(parsed.geturl())
    print(parsed.hostname)


if __name__ == '__main__':
    responses = []
    urls = [
            'https://lenta.ru/news/2018/02/17/loto/',
            'https://pikabu.ru/story/makhnemsya_ne_glyadya_5716361',
            'https://www.gazeta.ru/culture/photo/glavnoi_blondinke_37.shtml',
            'https://habrahabr.ru/sandbox/27705/',
            'https://stackoverflow.com/questions/4534438',
            'https://docs.python.org/3/library/multiprocessing.html',
            'https://macos.livejournal.com/1673260.html?media',
            'https://www.kinopoisk.ru/news/3117842/',
            'https://ria.ru/world/20180217/1514828882.html',
            'https://news.mail.ru/society/32594072/?frommail=1'
    ]
    # for url in urls:
    #     print(url)
    #     for l in format_article(*parse(url)):
    #         print(l)
    save_article(urls[2], format_article(*parse(urls[0])))
