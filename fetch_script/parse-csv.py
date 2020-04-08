import csv
from fetch_script import pubmed
from fetch_script.icam import Icam
import configparser
import os
import requests
import json

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

# gateway = config['ICAM']['gateway_location']
gateway = 'https://test.sknv.net/'
user = config['ICAM']['user']
password = config['ICAM']['password']

icam = Icam(gateway, user, password)

dry_run = True


def get_atype_id(atype):
    print('\t\t\tGenerating atype:')
    print('\t\t\t\t', atype)
    atype = atype.split(';')[0]
    cut = atype[:-len(atype) // 3]
    if 'RCT' in atype:
        cut = 'RCT'
    if 'Estudo de Coorte' in atype:
        cut = 'Estudo de Coorte'
    if 'Editorial/Opinião' in atype:
        cut = 'Editorial/Opinião'
    if 'Estudo de caso' in atype:
        cut = 'Estudo de caso'
    if 'Estudo de Prevalência' in atype:
        cut = 'Estudo de Prevalência'

    print('\t\t\t\t', cut)
    res = icam.get_atypes('?itemName.contains=' + cut)
    print('\t\t\t\t', res)
    if res:
        return res[0]['id']
    else:
        return 0


def get_ctrees_id(tema):
    print('\t\t\tGenerating cat:')
    print(f'\t\t\t\t{tema}')
    strip = tema.strip()[0]
    try:
        int(strip)
        print('\t\t\t\tIs INT!')
        return get_ctrees_id_int(tema)
    except ValueError:
        print('\t\t\t\tIs STR!')
        return get_ctrees_id_str(tema)


def get_ctrees_id_int(tema):
    chave_cat = ['Indicadores', 'Previsões e Modelos Matemáticos', 'Vias de Transmissão', 'Características Infecciosas',
                 'Sobrevivência do Vírus no Ambiente', 'Diferenças entre os Coronavírus',
                 'Estrutura e Sequência Genética', 'Mecanismos de Infeção', 'Estadios da Doença',
                 'Género e Grupos Etários', 'Comorbilidades', 'Outros',
                 'Apresentação Clínica, Evolução e Doenças Associadas', 'Testes Laboratoriais de Diagnóstico',
                 'Imagiologia', 'Outros Marcadores Laboratoriais', 'Terapêutica de Suporte',
                 'Oxigenoterapia, Suporte Ventilatório, Proning, ECMO', 'Terapêuticas Experimentais e Ensaios Clínicos',
                 'Meio Hospitalar e Cuidados de Saúde Primários', 'Comunidade', 'Vacinas',
                 'Marcadores Clínicos, Laboratoriais e Imagiológicos', 'Imunidade', 'Outros', 'Imunossupressão',
                 'Gravidez', 'Pediatria', 'Destaques']

    tlist = tema.replace(' ', '').split(';')
    endvalue = []
    print(f'\t\t\t\ttlist int: {tlist}')
    for t in tlist:
        res = icam.get_ctrees('?itemName.contains=' + chave_cat[int(t)])
        print(f'\t\t\t\tres: {res}')
        if res:
            endvalue.append({"id": res[0]['id']})
    return endvalue


def get_ctrees_id_str(tema):
    if ';' in tema:
        tlist = tema.split(';')
        print(f'\t\t\t\ttlist: {tlist}')
        endvalue = []
        for t in tlist:
            res = icam.get_ctrees('?itemName.contains=' + t.strip())
            print(f'\t\t\t\tres: {res}')
            if res:
                endvalue.append({"id": res[0]['id']})
        return endvalue
    else:
        res = icam.get_ctrees('?itemName.contains=' + tema)
        print(f'\t\t\t\tres: {res}')
        if res:
            return [{"id": res[0]['id']}]
        else:
            return []


def get_summary(ro: dict):
    if 'fullSummary' in ro.keys():
        return ro['fullSummary']

    compi = ''
    if 'objetivos' in ro.keys():
        compi += ro['objetivos']
    if 'metodos' in ro.keys():
        compi += '\n' + ro['metodos']
    if 'discussao' in ro.keys():
        compi += '\n' + ro['discussao']
    return compi


def get_keywords(ro: dict):
    if 'keywords' in ro.keys():
        # keywords = '|'.join([x.strip() for x in ro["keywords"].split(';') if not x.isspace()])
        keywords = ro["keywords"]  # filter via keyords.contains
        return keywords
    return 0


def do_the_post(ro: dict, pubmed_id):
    print(f'Checking if pubmed #{pubmed_id} exists: ')
    res = requests.get(url=icam.articles_endpoint + '?repoArticleId.equals=' + pubmed_id, headers=icam.headers)
    if res.json():
        adict = res.json()[0]
        print(f'\tFound article with id #{adict["id"]}')
    elif not dry_run:
        res = icam.post_new_articles(pubmed.get_single_article(pubmed_id), icam.get_srepo_id('pubmed'))
        adict = res.json()
        print(f'\tNo such article, posted with id #{adict["id"]}')
    else:
        adict = {"id": 0}
        print('\tDRY-RUN: no article')
        print(f'\tNo such article, posted with id #{adict["id"]}')

    if res.status_code == 201 or res.status_code == 200:
        article_id = adict['id']
        print('\tGenerating Revision...')

        # if successful lets try to post the revision
        revision = {
            "active": True,
            "article": {"id": article_id},
            "reviewState": "Accepted",
            "reviewedByPeer": True if 'Sim' in ro['reviewedByPeer'] else False,
            "reviewer": ro["reviewer"],
            "summary": get_summary(ro),
            "title": ro["title"]
        }

        keywords = get_keywords(ro)
        if keywords:
            revision['keywords'] = keywords

        if 'tema' in ro.keys():
            cat = get_ctrees_id(ro['tema'])
            print(f'\t\t\t\tcat: {cat}')
            if cat:
                revision["ctrees"] = cat

        atype = get_atype_id(ro['atype']) if (ro['atype'] and not ro['atype'].isspace()) else 0
        if atype:
            revision["atype"] = {"id": atype}

        if "returnNotes" in ro.keys():
            notes = ro['returnNotes']
            if notes and not notes.isspace():
                revision['returnNotes'] = ro["returnNotes"]

        kek = json.dumps(revision)
        print(f'\t\tRevision ready: {kek}')
        if not dry_run:
            res = requests.post(url=gateway + 'services/icamapi/api/revisions', data=kek, headers=icam.headers)
            print(
                f'\t\t Post response {res.status_code}: id #{res.json()["id"]}' if res.status_code == 201 else f'\t\tPost response {res.status_code}: {res.content}')
        else:
            print(f'\t\tDRY-RUN: sent \u21E7')
    else:
        print(f'\tArticle failed - {res.status_code}: {res.content}')
        print("\tWon't generate revision!")


# icam.ctrees_testhook()

with open('final07apr.csv', encoding='utf-8') as csv_file:
    if dry_run:
        print('------------------')
        print('|----DRY--RUN----|')
        print('------------------')

    # open file
    csv_reader = csv.reader(csv_file, delimiter='|', )

    # init vars
    line_count = 0
    # this stores the keys for the article dict
    title_row = []

    for row in csv_reader:
        # trim extra cells
        row = row[:22]
        if line_count == 0:
            title_row = row
            title_row[0] = 'id'
            line_count += 1

        # for each row not the title
        else:

            parsed_row = {}

            # for each row of the csv fill the dict with the elements
            for elem in title_row:
                parsed_row[elem] = row[title_row.index(elem)]
            with open('prows.txt', 'a', encoding='utf-8') as prows:
                prows.write(str(parsed_row))
                prows.write('\n')

            '''
            # if article has pubmed id
            if 'pubmedid' in parsed_row.keys():
                if parsed_row['pubmedid']:
                    do_the_post(parsed_row, parsed_row['pubmedid'])
                else:
                    print(f'no pubmed id on #{parsed_row["id"] if "id" in parsed_row.keys() else parsed_row}')
            else:
                print(f'no pubmed key on id #{parsed_row["id"] if "id" in parsed_row.keys() else parsed_row}')
            line_count += 1
            '''

    # out of the row loops
    print(f'Processed {line_count} lines.')

'''
gerar o article

fill these and give repo id to icam.post_new_articles
{
    'repoArticleId': 0,
    'reviewState': 0,
    'repoDate': 0,
    'articleTitle': 0,
    'articleAbstract': 0,
    'articleJournal': 0,
    'articleDate': 0,
    'articleDoi': 0,
    'fetchDate': 0,
    'citation': 0,
}

fill these and post!
Revision
{
    "active":true,
    "article":{"id":1},
    "atype":{"id":1},
    "ctrees":[
        {"id":140},
        {"id":142}
    ],
    "keywords":"asd|kek|",
    "returnNotes":"string",
    "reviewState":"Pending",
    "reviewedByPeer":true,
    "reviewer":"me",
    "summary":"striasdadsng",
    "title":"striaaaaaaaaaaaaaang"
}

'''
