import configparser
import os

from fetch_script.icam import Icam
from fetch_script import pubmed


# fetchScript utils function
# -----------------------------------------------------
def get_pubmed_new_article_ids(icam, pubmed_id_list):
    print('looking for new articles')
    icam_ids = icam.get_articles_pubmed_ids()
    new_articles = list(set(pubmed_id_list) - set(icam_ids))
    return new_articles


# the actual job of the fetchScript
# -----------------------------------------------------------------
def fetch_articles_pubmed(icam, num_articles, search_term):
    new_articles_ids = get_pubmed_new_article_ids(icam, pubmed.get_ids_list(num_articles, search_term))
    new = len(new_articles_ids)
    print(new, 'new articles!')
    print('starting push!' if new else 'no new articles!')
    for entry in new_articles_ids:
        print(f'submitting pubmed id #{entry}')
        r = icam.post_new_articles(pubmed.get_single_article(entry), icam.get_srepo_id('pubmed'))
        # If we didn't get a 201 back, log the problem to console
        if r.status_code != 201:
            print('problem posting {}: {} | {}'.format(entry, r.status_code, r.json()))
    print('no more articles to push!' if new else '')


def main():
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

    gateway = config['ICAM']['gateway_location']
    gatewayOnline = 'https://api.dev.icam.org.pt/'
    user = config['ICAM']['user']
    password = config['ICAM']['password']

    num_articles = config.getint('PUBMED', 'num_articles')
    search_term = config['PUBMED']['search_term']

    icam = Icam(gatewayOnline, user, password)

    # UNCOMMENT HERE TO auto generate CategoryTrees and ArticleTypes
    # icam.post_new_articles(pubmed.get_single_article(32219428), icam.get_srepo_id('pubmed'))

    # fetch_articles_pubmed(icam, num_articles, search_term)
    # icam.clean_db()




if __name__ == '__main__':
    main()
