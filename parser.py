import sys
from article_parser import Parser, check_url

if __name__ == '__main__':
    try:
        url = sys.argv[1]
        if not check_url(url, 1):
            print('Invalid url')
        else:
            parser = Parser()
            article = parser.parse(url)
            article.save()
    except IndexError:
        print('No url to parse')
