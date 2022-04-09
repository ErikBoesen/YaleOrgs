"""
from app import app, db, celery
from app.models import Organization

from app.scraper import sources
from .cache import Cache
import json
import os


@celery.task
def scrape(yaleconnect_cookie):
    # Store people into database

    print('Inserting new data.')
    Organization.query.delete()
    for organization_dict in organizations:
        db.session.add(Organization(**organization_dict))
    db.session.commit()
    print('Done.')
    """

import requests
from bs4 import BeautifulSoup

yaleconnect_cookie = 'dtCookie=v_4_srv_6_sn_345D8D62EC5CF3008662D205540C82C2_perc_100000_ol_0_mul_1_app-3Aea7c4b59f27d43eb_1_app-3A1e70f254d6d57550_1; CG.SessionID=f44rgj4jlvc3psroe2d3yw4b-mwzfzfLk9IBpvv9mSae%2fJAizOr4%3d; cg_uid=1651934-bYlm4ZnwgHOMGvQdCu66jOzdvVGwKqHcx2oTVTJY8no='

DEBUG = True

def get_soup(url):
    r = requests.get(
        url,
        params={'view': 'all'} if not DEBUG else None,
        headers={'Cookie': yaleconnect_cookie}
    )
    return BeautifulSoup(r.text, 'html5lib')

groups_soup = get_soup('https://yaleconnect.yale.edu/club_signup').find('div', {'class': 'content-cont'})
rows = groups_soup.find('ul', {'class': 'list-group'}).find_all('li', {'class': 'list-group-item'})
# Remove header
rows.pop(0)
groups = []
for row in rows:
    header = row.find('h2', {'class': 'media-heading'})
    a = header.find('a')
    url = a['href']
    name = a.text.strip()
    print('Read URL ' + url)
    groups.append({
        'id': int(url.replace('https://yaleconnect.yale.edu/student_community?club_id=', '')),
        'name': name,
    })

print(groups)

for i in range(len(groups)):
    group_id = groups[i]['id']
    about_soup = get_soup(f'https://yaleconnect.yale.edu/ajax_group_page_about?ax=1&club_id={group_id}').find('div', {'class': 'card-block'})
    current_header = None
    for child in about_soup.children:
        if child.name == 'h3':
            current_header = child.text
        else:
            if current_header == 'GENERAL':
                if child.name == 'div':
                    text = child.text.strip()
                    if not text:
                        continue
                    prop, value = text.split(': ')
                    prop = prop.lower().replace(' ', '_')
                    prop = {
                        'group_type': 'type',
                    }.get(prop, prop)
                    groups[i][prop] = value
            elif current_header == 'MISSION':
                if child.name == 'p':
                    if groups[i].get('mission'):
                        groups[i]['mission'] += '\n'
                    else:
                        groups[i]['mission'] = ''
                    groups[i]['mission'] += text
            elif current_header == 'MEMBERSHIP BENEFITS':
                if child.name == 'p':
                    benefits = child.find_all(text=True, recursive=False)
                    groups[i]['membership_benefits'] = '\n'.join(benefits)
            elif current_header == 'GOALS':
                pass
            elif current_header == 'CONSTITUTION':
                pass
            elif current_header == 'CONTACT INFO':
                pass
            elif current_header == 'OFFICERS':
                pass
            elif current_header is None:
                pass
            else:
                print(f'Encountered unknown About header {current_header}.')
    break
