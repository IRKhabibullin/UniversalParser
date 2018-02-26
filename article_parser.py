# -*- coding: utf-8 -*-
import configparser
import os
import requests
from urllib.parse import urlparse
from lxml import etree
from lxml.html.clean import Cleaner

config = configparser.ConfigParser()
config.read('settings.cfg')


class Parser:
    def __init__(self):
        self.stopwords = [
            'adv', 'rule', 'footer', 'info', 'sidebar', 'categor', 'ban', 'nav',
            'tabl', 'menu', 'social', 'login', 'sign', 'other', 'board', 'more',
            'favorite', 'relat', 'rating', 'top-bar', 'panel', 'headline',
            'mobile',
            # weak stopwords
            'tag', 'photo', 'add', 'title', 'sub', 'comment', 'right']
        # good_words = ['article', 'body', 'topic', 'content', 'story', 'post']
        self.cleaner = Cleaner(links=False, style=True, inline_style=False)

    # поиск заголовка статьи
    def get_title(self, html):
        page_title = html.xpath("//meta[@property='og:title']/@content")
        # поиск через анализ аттрибутов DOM-элементов
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
        if not page_title:
            page_title = html.xpath('//title')[0].text
        else:
            page_title = page_title[0]
        return page_title

    # парсим url, возвращаем статью
    def parse(self, article_url):
        article = Article(article_url)
        html_text = requests.get(article_url).text
        page_title = self.get_title(etree.HTML(html_text))
        response = etree.HTML(self.cleaner.clean_html(html_text))
        is_article = response.xpath('//article')
        if is_article:
            response = is_article[0]
        ps = response.xpath('//p|//h1|//div')
        ps = self.filter_elements(ps)
        paragraphs = []
        for p in ps:
            if self.is_valid(p, True):
                t = self.get_text(p, ps)
                if t:
                    paragraphs.append(t)
        article.text = article.format_article(page_title, paragraphs)
        return article

    # отметаем невалидные элементы, рекурсивно проверяя их родительские элементы
    def filter_elements(self, elements):
        filtered = []
        for element in elements:
            parent = element.getparent()
            if parent is not None:
                if parent.tag not in ['div', 'h1', 'h2', 'p']:
                    continue
            if not self.is_valid(element, True):
                continue
            filtered.append(element)
        return filtered

    # проверка на валидность элемента
    def is_valid(self, element, deep=False):
        """
        :param element: DOM-element
        :param deep: если True, то проверка идет рекурсивно по всем родителям
        :return:
        """
        if element.tag in ['header', 'footer']:
            return False
        # если элемент невидим
        try:
            if 'display:none' in element.attrib['style'] or \
                            'display: none' in element.attrib['style']:
                return False
        except KeyError:
            pass
        # если в названии класса, или id есть стопслово
        try:
            if any(kw in element.attrib['class'] for kw in self.stopwords):
                return False
        except KeyError:
            pass
        try:
            if any(kw in element.attrib['id'] for kw in self.stopwords):
                return False
        except KeyError:
            pass
        if deep:
            try:
                parent = element.getparent()
                if parent is not None:
                    return self.is_valid(parent, True)
            except KeyError:
                pass
        return True

    # выделяем текст из элемента и его дочерних элементов
    def get_text(self, element, page_elements):
        """
        :param element: элемент, из которого выделяется текст
        :param page_elements: список всех валидных элементов. Здесь происходит
        проверка, чтобы дочерние элементы не оказались в списке
        :return:
        """
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
                pass
        for child in element.getchildren():
            if child.tag != 'div' and self.is_valid(child, False):
                if child not in page_elements:
                    text += self.get_text(child, page_elements)
        if element.tag == 'br':
            text += '\n'
        try:
            e_tail = element.tail.strip().replace('\n', ' ')
            if e_tail:
                text += ' ' + e_tail
        except AttributeError:
            pass
        return text


class Article:
    def __init__(self, url):
        self.url = url
        self.line_len = int(config['DEFAULT']['line_len'])
        self.save_path = config['DEFAULT']['save_path']
        self.text = 'There is no text yet'

    def format_article(self, title, ps):
        """
        :param title: заголовок
        :param ps: абзацы
        :return:
        """
        formatted_article = self.split_by_len(title)
        formatted_article.append('\n')
        for p in ps:
            formatted_article += self.split_by_len(p)
            formatted_article.append('')
        return formatted_article

    # разбиваем абзац на строки фиксированной длины
    def split_by_len(self, text):
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
                pass
            if len(line) + len(word) <= self.line_len - 1:
                line += (' ' if line else '') + word
            else:
                if len(word) >= self.line_len:
                    divided, line = self.split_large_word(line, word)
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

    # разделяем большую строку (чаще всего ссылку) на несколько строк
    def split_large_word(self, line, word):
        divided_word = []
        first_part_len = self.line_len - len(line) - 1
        if first_part_len < 3:
            first_part_len = 0
            divided_word.append(line)
            line = ''
        else:
            divided_word.append(
                line + (' ' if line else '') + word[:first_part_len])
        for w in [word[i:i + self.line_len] for i in
                  range(first_part_len, len(word), self.line_len)]:
            if len(w) > self.line_len - 3:
                divided_word.append(w)
            else:
                line = w
        return divided_word, line

    # сохраняем статью в файл
    def save(self):
        parsed = urlparse(self.url)
        path = parsed.path.strip('/').split('/')
        if '.' in path[-1]:
            tl_dom = path[-1].split('.')
            tl_dom[-1] = 'txt'
            path[-1] = '.'.join(tl_dom)
        else:
            path[-1] += '.txt'
        path = '|'.join([parsed.netloc] + path)
        full_path = os.path.join(self.save_path, path)
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
        with open(full_path, 'w+') as f:
            for line in self.text:
                f.write(line + '\n')
            f.write(
                '\n\n-------------------------------------------------------\n')
            f.write('Source url: {}\n'.format(self.url))


# проверка сслыки на валидность
def check_url(url, check_lvl=0):
    if not check_lvl:
        check_lvl = config['DEFAULT']['url_check_lvl']
    if check_lvl == 1:
        try:
            requests.get(url)
        except Exception:
            return False
    if check_lvl == 2:
        parsed = urlparse(url)
        if not (parsed.scheme and parsed.netloc):
            return False
    return True
