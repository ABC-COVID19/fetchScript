import requests
import json


class Icam:

    def __init__(self, gateway, user, password):

        self.auth_endpoint = gateway + 'api/authenticate'

        self.articles_endpoint = gateway + 'services/icamapi/api/articles'
        self.repos_endpoint = gateway + 'services/icamapi/api/source-repos'
        self.atypes_endpoint = gateway + 'services/icamapi/api/article-types'
        self.ctrees_endpoint = gateway + 'services/icamapi/api/category-trees'

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

    # Source Repos
    # ------------------------------------------------------------------------------------------------------------------
    def get_srepo_id(self, item_name):
        res = requests.get(self.repos_endpoint, headers=self.headers)
        repos = res.json()
        for elem in repos:
            if elem['itemName'] == item_name:
                return elem['id']

        print('No sourceRepo for {}! Creating...'.format(item_name))
        res = requests.post(self.repos_endpoint, data=json.dumps({'active': True, 'itemName': item_name}),
                            headers=self.headers)
        source_repo = res.json()
        print('Created sourceRepo ', source_repo)
        return source_repo['id']

    # Articles
    # ------------------------------------------------------------------------------------------------------------------
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
        return requests.post(url=self.articles_endpoint, data=json.dumps(article), headers=self.headers)

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

    # Article Types
    # ------------------------------------------------------------------------------------------------------------------
    def get_atypes(self):
        res = requests.get(url=self.atypes_endpoint, headers=self.headers)
        atypes = res.json()
        return atypes

    def get_atypes_ids(self):
        atypes = self.get_atypes()
        id_list = [elem['id'] for elem in atypes]
        print(id_list)
        return id_list

    def create_atypes(self):
        atypes = ['Meta-Análise', 'Revisão Sistemática', 'RCT', 'Estudo de Coorte', 'Estudo Caso-controlo',
                  'Estudo de Prevalência', 'Série de casos', 'Estudo de Caso',
                  'Estudo Experimental/Modelos Matemáticos', 'Revisão não sistemática', 'Editorial/Opinião/Comunicação']

        current_atypes = self.get_atypes()
        print(f'\ncurrent atypes: {current_atypes}')
        for title in atypes:
            if not any(d['itemName'] == title for d in current_atypes):
                print(f'atype: {title} does not exist, creating...')
                atype_dict = {
                    'active': True,
                    'itemName': title
                }
                res = requests.post(url=self.atypes_endpoint, data=json.dumps(atype_dict), headers=self.headers)
                print(f'response: {res.status_code}')
            else:
                print(f'atype: {title} already exists, skipping...')

    def delete_atype(self, atype_id):
        url = self.atypes_endpoint + '/{}'.format(atype_id)
        return requests.delete(url=url, headers=self.headers)

    def delete_all_atypes(self):
        print('deleting all atypes!')
        id_list = self.get_atypes_ids()
        for elem in id_list:
            r = self.delete_atype(elem)
            if r.status_code != 204:
                print('deleting {}: abnormal status {}'.format(elem, r.status_code))

    def reset_atypes(self):
        self.delete_all_atypes()
        self.create_atypes()

    # Category Trees
    # ------------------------------------------------------------------------------------------------------------------
    def get_ctrees(self):
        res = requests.get(url=self.ctrees_endpoint, headers=self.headers)
        ctrees = res.json()
        return ctrees

    def get_ctrees_ids(self):
        ctrees = self.get_ctrees()
        id_list = [elem['id'] for elem in ctrees]
        print(f'get_ctrees_ids: {id_list}')
        return id_list

    def create_ctrees(self):
        ctrees = {
            'Epidemiologia': [
                'Indicadores',
                'Previsões e Modelos Matemáticos',
                'Vias de Transmissão',
                'Características Infecciosas',
                'Sobrevivência do Vírus no Ambiente'
            ],
            'Etiologia e Fisiopatologia': [
                'Diferenças entre os Coronavírus',
                'Estrutura e Sequência Genética',
                'Mecanismos de Infeção',
                'Estadios da Doença'
            ],
            'Fatores de Risco': [
                'Género e Grupos Etários',
                'Comorbilidades',
                'Outros'
            ],
            'Clínica e Diagnóstico': [
                'Apresentação Clínica, Evolução e Doenças Associadas',
                'Testes Laboratoriais de Diagnóstico',
                'Imagiologia',
                'Outros Marcadores Laboratoriais'
            ],
            'Tratamento': [
                'Terapêutica de Suporte',
                'Oxigenoterapia, Suporte Ventilatório, Proning, ECMO',
                'Terapêuticas Experimentais e Ensaios Clínicos'
            ],
            'Prevenção': [
                'Meio Hospitalar e Cuidados de Saúde Primários',
                'Comunidade',
                'Vacinas'
            ],
            'Prognóstico': [
                'Marcadores Clínicos, Laboratoriais e Imagiológicos',
                'Imunidade',
                'Outros'
            ],
            'Populações Especiais': [
                'Imunossupressão',
                'Gravidez',
                'Pediatria'
            ],
            'destaques': []
        }

        current_ctrees = self.get_ctrees()
        print(f'\ncurrent ctrees: {current_ctrees}')
        created_ids_list = []
        for area in ctrees.keys():

            if not any(d['itemName'] == area for d in current_ctrees):
                print(f'\nctree area: {area} does not exist, creating...')
                atype_dict = {
                    'active': True,
                    'itemName': area,
                }
                res = requests.post(url=self.ctrees_endpoint, data=json.dumps(atype_dict), headers=self.headers)
                current_area_id = res.json()['id']
                created_ids_list.append(current_area_id)
                print(f'response {res.status_code}' if res.status_code == 201 else f'response {res.status_code}: {res.content}')

                if ctrees[area]:
                    print('\tgenerating children')
                    for child in ctrees[area]:
                        if not any(d['itemName'] == child for d in current_ctrees):
                            print(f'\tctree child: {child} does not exist, creating...')
                            child_dict = {
                                'active': True,
                                'itemName': child,
                                'parent': {'id': current_area_id}
                            }
                            res = requests.post(url=self.ctrees_endpoint, data=json.dumps(child_dict), headers=self.headers)
                            print(f'\tresponse {res.status_code}' if res.status_code == 201 else f'response {res.status_code}: {res.content}')
                            created_ids_list.append(res.json()['id'])
                        else:
                            print(f'\tctree: {child} already exists, skipping...')
            else:
                print(f'ctree: {area} already exists, skipping...')

    def delete_ctree(self, ctree_id):
        url = self.ctrees_endpoint + '/{}'.format(ctree_id)
        return requests.delete(url=url, headers=self.headers)

    def delete_all_ctrees(self):
        # todo: cant delete parent before child! this is broken
        print('deleting all ctrees!')
        ctrees_list = self.get_ctrees()
        # because of the eager fetch spaghetti meme, children also appear in the get request as top level entities
        # so we need to filter them out form the list so that we only try to delete them once
        # because there are only 2 levels, we can distinguish children because their 'parent' field wont be null!
        # https://github.com/ABC-COVID19/API-backend/issues/14
        # todo: remove this after backend is fixed!
        ctrees_list = [cat for cat in ctrees_list if cat['parent'] is None]
        for elem in ctrees_list:
            if 'children' in elem.keys():
                for child in elem['children']:
                    res = self.delete_ctree(child['id'])
                    print(f'\tdeleted {child["itemName"]} {res.status_code}' if res.status_code == 204 else f'problem with {child["itemName"]}: {res.status_code}: {res.content}')
                print('\tall children deleted, deleting parent next')

            res = self.delete_ctree(elem['id'])
            print(f'deleted {elem["itemName"]} {res.status_code}' if res.status_code == 204 else f'problem with {elem["itemName"]}: {res.status_code}: {res.content}')

    def reset_ctrees(self):
        self.delete_all_ctrees()
        self.create_ctrees()

    def ctrees_testhook(self):
        self.create_ctrees()
        self.create_atypes()
