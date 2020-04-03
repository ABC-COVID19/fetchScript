# ICAM articles fetch script
[![Python 3.6+](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/downloads/release/python-3610/)

This python package gets new articles from PubMed and posts them to the ICAMApi Gateway!

## Setup

`pip install -r requirements.txt`

Requires a config.ini inside the package folder. The following example file is already included in the repo:
```ini
[ICAM]
# Where the gateway is running, with trailing backslash please!
gateway_location: http://localhost:8080/

# Using jHipster's JWT auth, gets token from user/pass
# Default user and password values for jHipster:
user: user
password: user

[PUBMED]
# Each run check PubMed's last xx articles
# Ex:   If set to 20 and there are 10 new articles since last checked, IDs will be compared
#       and the 10 new articles will be fetched. If there are 50 new articles, only 20 will
#       be fetched because we only looked at the 20 latest articles.
num_articles = 20
# Search term for PubMed API
search_term = covid+19
```

## Run
[![Python 3.6+](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/downloads/release/python-3610/)

`python -m fetch_script`

## Todo
- [x] Properly structure project
- [ ] Set up logger (currently just prints basic info to stdout)
- [ ] Implement get keywords from source repo
- [ ] Set up fetch from BioRxiv