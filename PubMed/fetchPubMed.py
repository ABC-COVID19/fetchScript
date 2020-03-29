import requests
import json
from lxml import html
import calendar
from itertools import chain
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
print(config['DEFAULT']['api_key'])
# Constants
# -------------------------------------------
MONTH_TO_NUM = {name: num for num, name in enumerate(calendar.month_abbr) if num}
API_ENDPOINT = config['DEFAULT']['api_endpoint']
REQUEST_HEADER = {
    "Content-Type": "application/json",
    'Authorization': config['DEFAULT']['api_key']
}


# Helper functions
# --------------------------
def get_date(date_element):
    """
    Utils function to generate a date string formatted yyyy-mm-dd.
    Also enforces month as int, i.e., 26 Mar 2020 becomes 2020-3-26

    :param date_element: A list of xml nodes
    :return: A formatted date string (yyyy-mm-dd) retrieved from the first xml node in the list
    """
    year, month, day = '', '', ''
    if date_element[0].find('year') is not None:
        year = date_element[0].find('year').text
    if date_element[0].find('month') is not None:
        month = date_element[0].find('month').text
        try:
            int(month)
        except ValueError:
            month = str(MONTH_TO_NUM[month])
        if len(month) == 1:
            month = '0' + month
    if date_element[0].find('day') is not None:
        day = date_element[0].find('day').text
    else:
        # todo: fix this
        day = '01'
    if len(str(day)) == 1:
        day = '0' + day
    return '{}-{}-{}'.format(year, month, day)


def stringify_children(node):
    """
    Utils function to print all text inside a tag, ignoring child tags
    If you stringify <printme> in:
    <printme> <child1> Text A </child1> Text outside children <child2> Text B </child2> </printme>
    The result is "Text A Text outside children Text B"

    Also Filters and removes possible Nones in texts and tails
    ref: http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml

    :param node: A xml node
    :return String with all the text inside the node and it's children
    """
    parts = (
            [node.text]
            + list(chain(*([c.text, c.tail] for c in node.getchildren())))
            + [node.tail]
    )
    return ''.join(filter(None, parts))


# Get ICAM stuff
# ----------------------------------------------------------------------
def get_icam_articles():
    """

    :return: a list with dicts representing each article on icam's DB
    """
    res = requests.get(url=API_ENDPOINT, headers=REQUEST_HEADER)
    return json.loads(res.content)


def get_icam_latest_pubmedid(article_list):
    try:
        return str(article_list[-1]['sourceID'])
    except KeyError:
        # this error happens when there is no sourceID field on the article list
        # todo: set this up in a better way
        raise Exception('Failed to retrieve IDs from ICAM')


def post_icam_new_articles(data):
    return requests.post(url=API_ENDPOINT, data=data, headers=REQUEST_HEADER)


# Get PubMed stuff
# ---------------------------------------------------------------------------------------------------
def get_pubmed_id_list(max_articles: int, search_term: str):
    """
    Gets a list of PubMed IDs for the latest articles matching the search term.

    :param max_articles: number of articles to retrieve.
    :param search_term: keyword to search in PubMed database.
    :return A list with the retrieved IDs
    """
    search_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={}&retmax={}' \
        .format(search_term, max_articles)
    reply = requests.get(search_url)
    tree = html.fromstring(reply.content)
    id_list = tree.xpath('//idlist')
    if id_list is not None:
        return [x.text for x in id_list[0]]
    else:
        return []


def get_pubmed_single_article(pubmed_id):
    """
    Parses a XML file representing a PubMed article to retrieve:
    - title
    - abstract
    - journal
    - doi
    - pubmed_pubdate
    - official_date
    - citation

    And returns a dict that can be converted to json for a POST via json.dumps()

    :param pubmed_id: The PubMed ID of the article you want
    :return A dict with all the data collected from the article
    """

    fetch_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={}&rettype=abstract' \
        .format(pubmed_id)
    page = requests.get(fetch_url)
    tree = html.fromstring(page.content)

    if tree.xpath('//articletitle'):
        title = ' '.join([title.text for title in tree.xpath('//articletitle')])
    elif tree.xpath('//booktitle'):
        title = ' '.join([title.text for title in tree.xpath('//booktitle')])
    else:
        title = 'No title available'

    abstract_tree = tree.xpath('//abstract/abstracttext')
    if abstract_tree:
        abstract = ' '.join([stringify_children(a).strip() for a in abstract_tree])
    else:
        abstract = 'No abstract available.'

    if tree.xpath('//article//title'):
        journal = ';'.join([t.text.strip() for t in tree.xpath('//article//title')])
    else:
        journal = ''

    pubmed_pubdate = tree.xpath('//pubmeddata//history//pubmedpubdate[@pubstatus="medline"]')
    if pubmed_pubdate:
        pubmed_pubdate_string = get_date(pubmed_pubdate)
    else:
        pubmed_pubdate = tree.xpath('//pubmeddata//history//pubmedpubdate')
        pubmed_pubdate_string = get_date(pubmed_pubdate)

    official_date = tree.xpath('//pubdate')
    if official_date:
        official_date_string = get_date(official_date)
    else:
        official_date_string = ''

    doi = ''
    article_ids = tree.xpath('//articleidlist//articleid')
    if len(article_ids) >= 1:
        for article_id in article_ids:
            if article_id.attrib.get('idtype') == 'doi':
                doi = article_id.text

    authors_tree = tree.xpath("//authorlist/author")
    authors = list()
    if authors_tree:
        for a in authors_tree:
            lastname = a.find("lastname").text if a.find("lastname") is not None else ''
            fullname = lastname.strip()
            if fullname == "":
                fullname = (
                    a.find("collectivename").text
                    if a.find("collectivename")
                    else ""
                )
            authors.append(fullname)

        if len(authors) == 1:
            authors_text = authors[0]
        elif len(authors) == 2:
            authors_text = "{} and {}".format(authors[0], authors[1])
        else:
            authors_text = "{}, et al".format(authors[0])
    else:
        authors_text = ''

    dict_out = {
        "citation": '{}. {}. {}'.format(authors_text, journal, official_date_string),
        "cntsource": {
            "id": 11,
            "itemName": "PubMed"
        },
        "doi": doi,
        "journal": journal,
        "officialPubDate": official_date_string,
        "pubmedDate": pubmed_pubdate_string,
        "reviewState": "Hold",
        "sourceAbstract": abstract,
        "sourceDate": pubmed_pubdate_string,
        "sourceID": tree.xpath('//pmid')[0].text,
        "sourceTitle": title
    }

    return dict_out


# fetchScript functions
# -----------------------------------------------------
def is_pubmed_new_articles(pubmed_id_list):
    icam_id = get_icam_latest_pubmedid(get_icam_articles())
    print('latest icam pubmedid: {}'.format(icam_id))
    print(pubmed_id_list)
    if icam_id in pubmed_id_list:
        return pubmed_id_list.index(icam_id)
    return -1


# the actual job of the fetchScript
# -----------------------------------------------------------------
max_articles = 10
search_term = 'covid+19'
pubmed_ids = get_pubmed_id_list(max_articles, search_term)
new_article_index = is_pubmed_new_articles(pubmed_ids)

if new_article_index == 0:
    print('No new articles')
else:
    print('{} new articles out of {}'
          .format(max_articles if new_article_index == -1 else new_article_index, max_articles))
    sublist = pubmed_ids[0:new_article_index]
    print(sublist)
    for pubmed_id in sublist:
        data = json.dumps(get_pubmed_single_article(pubmed_id))
        print(data)
        r = post_icam_new_articles(data)
        print(r.content)