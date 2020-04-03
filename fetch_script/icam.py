import requests
import json


class Icam:

    def __init__(self, gateway, user, password):
        self.articles_endpoint = gateway + 'services/icamapi/api/articles'
        self.repos_endpoint = gateway + 'services/icamapi/api/source-repos'
        self.auth_endpoint = gateway + 'api/authenticate'

        self.user = user
        self.password = password

        self.token = self.authenticate()

        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.token
        }

    def authenticate(self):
        data = json.dumps({
            'username': self.user,
            'password': self.password
        })
        res = requests.post(self.auth_endpoint, data=data, headers={'Content-Type': 'application/json'})
        return res.json()['id_token']

    def get_srepo_id(self, item_name):
        res = requests.get(self.repos_endpoint, headers=self.headers)
        repos = res.json()
        for elem in repos:
            if elem['itemName'] == item_name:
                return elem['id']

        print('No sourceRepo for pubmed! Creating...')
        res = requests.post(self.repos_endpoint, data=json.dumps({'active': True, 'itemName': item_name}),
                            headers=self.headers)
        source_repo = res.json()
        print('Created sourceRepo ', source_repo)
        return source_repo['id']

    def get_articles(self):
        """
        This function returns a list where every article on icam is represented as a dict.
        ICAM API request all articles replies based on pages, with links to the next, previous, first and last page.

        So we must get the links from the http header, add all articles on the current page to the final list, and
        move on to the next page. This is done until current_url matches the url for the last page.

        :return: a list with dicts representing each article on icam's DB
        """
        # Sets the current_url to the api endpoint
        current_url = self.articles_endpoint

        # Gets first page of articles and respective links
        res = requests.get(url=current_url, headers=self.headers)
        articles = res.json()

        # Only try this if there is a links header to avoid exceptions!
        if res.links:

            # Set our loop control variable
            is_last_page = False
            # Keep getting articles until we reach the last page
            while not is_last_page:
                # If there is a page after this one
                if 'next' in res.links.keys():

                    # Set current_url to the next page
                    current_url = res.links['next']['url']

                    # Update res and get articles from the new current_url
                    res = requests.get(url=current_url, headers=self.headers)
                    page_articles = res.json()

                    # Append the new articles to our global article list
                    articles += page_articles

                # If there is no next page, set control variable to exit loop
                else:
                    is_last_page = True
        return articles

    def get_articles_ids(self):
        articles = self.get_articles()
        id_list = [elem['id'] for elem in articles]
        return id_list

    def get_articles_pubmed_ids(self):
        articles = self.get_articles()
        if isinstance(articles, list):
            id_list = [elem['repoArticleId'] for elem in articles]
            return id_list
        return []

    def get_latest_pubmed_id(self):
        # This function is for a future optimization attempt where to find if there are new articles
        # on PubMed we look at just the last imported article's PubMed ID. WIP!

        # Send a first GET to obtain the links
        res = requests.get(url=self.articles_endpoint, headers=self.headers)

        if res.links:
            # Get the last page
            last_page = requests.get(url=res.links['last']['url'], headers=self.headers)
            # The last article to be imported is the last article of the last page!
            last = last_page.json().pop()
            return last['repoArticleId']
        return 0

    def post_new_articles(self, article, srepo_id):
        article['srepo'] = {'id': srepo_id}
        data = json.dumps(article)
        return requests.post(url=self.articles_endpoint, data=data, headers=self.headers)

    def delete_article(self, article_id):
        url = self.articles_endpoint + '/{}'.format(article_id)
        return requests.delete(url=url, headers=self.headers)

    def delete_all_articles(self):
        print('deleting all articles!')
        id_list = self.get_articles_ids()
        for elem in id_list:
            r = self.delete_article(elem)
            if r.status_code != 204:
                print('deleting {}: abnormal status {}'.format(elem, r.status_code))

    def find_duplicate_pubmed_ids(self):
        articles = self.get_articles()
        a = self.get_articles_pubmed_ids()
        dupes = []
        for elem in articles:
            if a.count(elem['repoArticleId']) > 1:
                dupes.append(elem['id'])
                articles.pop(articles.index(elem))
        return dupes
