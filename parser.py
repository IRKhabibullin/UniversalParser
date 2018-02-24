# -*- coding: utf-8 -*-
import re

import requests
from lxml import etree

# TODO read from config and config format is .cfg
from lxml.html.clean import Cleaner

line_len = 80
stopwords = ['adv', 'comment', 'rule', 'footer', 'info', 'bar', 'nav', 'tag',
             'tabl', 'menu', 'login', 'sign', 'photo', 'side', 'other']
good_words = ['article', 'body', 'topic', 'content', 'story', 'post']
cleaner = Cleaner(style=True, links=False, meta=False)


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
    response = etree.HTML(requests.get(url).text)
    page_title = get_title(response)
    ps = response.xpath('//p|//h1')
    ps = filter_elements(ps)
    if url == urls[2]:
        print('asd')
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
        paragraphs.append(get_deep_text(p))
    return page_title, paragraphs


def filter_elements(elements):
    filtered = []
    for element in elements:
        parent = element.getparent()
        if parent is not None:
            if parent.tag not in ['div', 'h1', 'h2', 'p']:
                continue
        if not valid_tag(element):
            continue
        filtered.append(element)
    print('{} elements filtered to {}'.format(len(elements), len(filtered)))
    return filtered


def format_article(title, ps):
    formatted_article = split_by_len(title)
    formatted_article.append('\n\n')
    for p in ps:
        formatted_article += split_by_len(p)
        formatted_article.append('')
    formatted_article.append('\n\n--------------------------------------------')
    return formatted_article


def split_by_len(text):
    words = text.split()
    formatted_text = []
    line = ''
    for word in words:
        if len(word) > 400:
            word = '[очень_длинная_ссылка]'
        if len(line) + len(word) <= line_len - 1:
            line += ' ' + word if line else word
        else:
            if len(word) >= line_len:
                divided, line = split_large_word(line, word)
                formatted_text += divided
            else:
                formatted_text.append(line)
                line = word
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


def valid_tag(element):
    # like check for display:none and stuff
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
        parent = element.getparent()
        if parent is not None:
            return valid_tag(parent)
    except KeyError:
        pass
    return True


def check_url(url):
    try:
        requests.get(url)
    except Exception:
        return False
    return True


def get_deep_text(element):
    text = ''
    if element.text is not None:
        text += ' ' + element.text.strip()
    if element.tag == 'a':
        try:
            a_url = element.attrib['href']
            if check_url(a_url):
                text += ' [' + a_url + ']'
        except KeyError:
            print('href error:', element.attrib)
    for child in element.getchildren():
        text += get_deep_text(child)
    if element.tag == 'br':
        text += '\n'
    if element.tail is not None:
        text += ' ' + element.tail.strip()
    return text

if __name__ == '__main__':
    responses = []
    urls = ['https://lenta.ru/news/2018/02/17/loto/',
            'https://pikabu.ru/story/makhnemsya_ne_glyadya_5716361',
            'https://www.gazeta.ru/culture/photo/glavnoi_blondinke_37.shtml',
            'https://habrahabr.ru/sandbox/27705/',
            'https://stackoverflow.com/questions/4534438',
            'https://docs.python.org/3/library/multiprocessing.html',
            'https://macos.livejournal.com/1673260.html?media',
            'https://www.kinopoisk.ru/news/3117842/',
            'https://ria.ru/world/20180217/1514828882.html',
            'https://news.mail.ru/society/32594072/?frommail=1']
    for url in urls:
        print(url)
        for l in format_article(*parse(url)):
            print(l)
    # html_page = etree.HTML(requests.get(urls[3]).text)
    # divs = html_page.xpath('//div')
    # for d in divs:
    #     try:
    #         if d.attrib['class'] == 'post__text post__text-html js-mediator-article':
    #             get_deep_text(d)
    #     except Exception:
    #         pass
            # title_tags = ['h1', 'h2', 'a']
            # _titles = []
            # for r in urls:
            #     _titles.append(parse(r))

            # for url in urls:
            #     page_html = requests.get(url).text
            #     page_html = cleaner.clean_html(page_html)
            #     responses.append(etree.HTML(page_html))
            # page_titles = [[title.text for title in titles] for titles in
            #                [r.xpath('//title') for r in responses]]
            # ps = [r.xpath('//p|//a') for r in responses]
            # ps = [[p for p in p_list if p.getparent().tag in []] for p_list in ps]

            # no p: 2, 3
            # article_titles = [[r.xpath('//' + tag) for tag in title_tags] for r in
            #                   responses]
            # article_titles_flat = []
            # for article in article_titles:
            #     article_titles_flat.append(
            #         [item.text for sublist in article for item in sublist if
            #          item.text is not None])
            # probable_titles = []
            # for i in range(len(page_titles)):
            #     probable_titles.append([h for h in article_titles_flat[i] if
            #                             h in page_titles[i][0]])
            # # s.encode('raw-unicode-escape')
    print('oaed')
