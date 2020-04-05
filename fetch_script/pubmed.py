import requests
from lxml import html
import calendar
from itertools import chain
import datetime

# Constants
# -------------------------------------------
MONTH_TO_NUM = {name: num for num, name in enumerate(calendar.month_abbr) if num}


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
        month = str(date_element[0].find('month').text)

    if date_element[0].find('day') is not None:
        day = date_element[0].find('day').text
    return year, month, day


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


# Get PubMed stuff
# ---------------------------------------------------------------------------------------------------
def get_ids_list(max_articles: int, search_term: str):
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
        return [int(x.text) for x in id_list[0]]
    else:
        return []


def get_single_article(pubmed_id):
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

    dict_out = {
        'repoArticleId': pubmed_id,  # Set PubMed ID
        'reviewState': 'Hold'  # Set the review state to Hold
    }

    # Set the rest of the repo fields

    # Get repoDate (PubMed publication date)
    # Prefer the MEDLINE entry date, else use whatever is available
    pubmed_pubdate = tree.xpath('//pubmeddata//history//pubmedpubdate[@pubstatus="medline"]')
    if pubmed_pubdate:
        y, m, d = get_date(pubmed_pubdate)
        dict_out['repoDate'] = '{}-{}-{}'.format(y, '0' + m if len(m) == 1 else m, '0' + d if len(d) == 1 else d)
    else:
        pubmed_pubdate = tree.xpath('//pubmeddata//history//pubmedpubdate')
        y, m, d = get_date(pubmed_pubdate)
        dict_out['repoDate'] = '{}-{}-{}'.format(y, m, d)

    # Get repoKeywords
    # todo: keywords

    # Set the article fields

    # Prepare to generate citation
    citation = ''

    # Get article authors for the citation
    authors_tree = tree.xpath("//authorlist/author")
    authors = []
    if authors_tree:
        # Only need 2 author names tops! [0:3] to check if 2+ for "et al" case
        for a in authors_tree[0:3]:
            name = a.find('lastname').text.strip() if a.find('lastname') is not None else ''
            if name == '':
                name = a.find('collectivename').text if a.find('collectivename') is not None else ''

            authors.append(name)

        if len(authors) == 1:
            authors_text = authors[0]
        elif len(authors) == 2:
            authors_text = "{} and {}".format(authors[0], authors[1])
        else:
            authors_text = "{}, et al".format(authors[0])

        citation += '{}.'.format(authors_text)

    # Get articleTitle
    if tree.xpath('//articletitle'):
        try:
            title = ' '.join([title.text for title in tree.xpath('//articletitle')])
            # If the title length exceeds 255, cut it and add '[...]' at the end
            if len(title) > 255:
                title = title[0:250] + '[...]'
            dict_out['articleTitle'] = title
        except Exception as e:
            # todo: logging!
            print('error processing title of {}: {}'.format(pubmed_id, e))

    # Get articleAbstract
    abstract_tree = tree.xpath('//abstract/abstracttext')
    if abstract_tree:
        dict_out['articleAbstract'] = ' '.join([stringify_children(a).strip() for a in abstract_tree])

    # Get articleJournal
    if tree.xpath('//article//title'):
        journal = ';'.join([t.text.strip() for t in tree.xpath('//article//title')])
        dict_out['articleJournal'] = journal
        citation += ' {}.'.format(journal)

    # Get articleDate (Official publication date - citation and reference purpose only)
    # todo: standardize d-Mon-yyyy
    official_date = tree.xpath('//pubdate')
    if official_date:
        y, m, d = get_date(official_date)
        date = '{}{}{}'.format(d + '-' if d else '', m + '-' if m else '', y)
        dict_out['articleDate'] = date
        citation += ' {}'.format(date)

    # Get articleDoi
    doi = tree.xpath('//articleidlist//articleid[@idtype="doi"]')
    if doi:
        dict_out['articleDoi'] = doi[0].text

    # Set the rest of our meta fields

    # Set fetchDate
    dict_out['fetchDate'] = str(datetime.date.today())

    # Set citation
    dict_out['citation'] = citation

    return dict_out
