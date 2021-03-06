from app import app, db, celery
from app.models import Organization, Person, officerships

import requests
from bs4 import BeautifulSoup, Tag, NavigableString

DEBUG = False
ROOT = 'https://yaleconnect.yale.edu'

def get_soup(url, yaleconnect_cookie):
    r = requests.get(
        url,
        headers={'Cookie': yaleconnect_cookie}
    )
    return BeautifulSoup(r.text, 'html5lib')

@celery.task
def scrape(yaleconnect_cookie):
    # Store people into database

    print('Reading organizations list.')
    organizations_soup = get_soup(
        ROOT + ('/club_signup' if DEBUG else '/club_signup?view=all'),
        yaleconnect_cookie,
    ).find('div', {'class': 'content-cont'})
    rows = organizations_soup.find('ul', {'class': 'list-group'}).find_all('li', {'class': 'list-group-item'})
    # Remove header

    rows.pop(0)
    organization_ids = set()
    organizations = []
    for row in rows:
        header = row.find('h2', {'class': 'media-heading'})
        a = header.find('a')
        url = a['href']
        organization_id = int(url.replace(ROOT + '/student_community?club_id=', ''))
        name = a.text.strip()
        if organization_id in organization_ids:
            print(f'Already tracking {name}.')
            continue
        logo = row.find('img')['src']
        if 'Default_Group_Logo' in logo:
            logo = None
        else:
            logo = ROOT + logo
        organizations.append({
            'id': organization_id,
            'name': name,
            'logo': logo,
            'mission': '',
            'goals': '',
            'benefits': '',
            'officers': [],
        })
        organization_ids.add(organization_id)

    print(organizations)

    for i in range(len(organizations)):
        organization_id = organizations[i]['id']
        print('Parsing ' + organizations[i]['name'])
        about_soup = get_soup(f'{ROOT}/ajax_group_page_about?ax=1&club_id={organization_id}', yaleconnect_cookie).find('div', {'class': 'card-block'})
        current_header = None
        current_contact_property = None
        for child in about_soup.children:
            if child.name == 'h3':
                current_header = child.text
            else:
                if current_header == 'GENERAL':
                    if child.name == 'div':
                        text = child.text.strip()
                        if not text:
                            continue
                        prop, value = text.split(': ', 1)
                        prop = prop.lower().replace(' ', '_')
                        prop = {
                            'group_type': 'type',
                        }.get(prop, prop)
                        organizations[i][prop] = value
                elif current_header in ('MISSION', 'MEMBERSHIP BENEFITS', 'GOALS'):
                    if child.name == 'p':
                        prop = current_header.lower().replace(' ', '_')
                        prop = {
                            'membership_benefits': 'benefits',
                        }.get(prop, prop)
                        content = child.find_all(text=True, recursive=False)
                        text = '\n'.join([line.strip() for line in content])
                        organizations[i][prop] = (organizations[i][prop] + '\n' + text).strip()
                elif current_header == 'CONSTITUTION':
                    if child.name == 'p':
                        organizations[i]['constitution'] = ROOT + child.find('a')['href']
                elif current_header == 'CONTACT INFO':
                    if isinstance(child, Tag) and child.name == 'span' and child.get('class') is not None and 'mdi' in child['class']:
                        current_contact_property = child['class'][1].replace('mdi-', '')
                    else:
                        if isinstance(child, Tag):
                            text = child.text.strip()
                        else:
                            text = str(child).strip()
                        if text and current_contact_property:
                            if current_contact_property == 'email':
                                organizations[i]['email'] = text
                            elif current_contact_property in ('marker', 'map-marker'):
                                organizations[i]['address'] = '\n'.join([line.strip() for line in text.split('\n')])
                            elif current_contact_property == 'earth':
                                organizations[i]['website'] = text
                            elif current_contact_property == 'cellphone':
                                organizations[i]['phone'] = ''.join([char for char in text if text.isdigit()])
                            else:
                                print(f'Saw unrecognized contact property {current_contact_property} with value {text}.')
                elif current_header == 'OFFICERS':
                    if child.name == 'img':
                        officer = {}
                        officer['name'] = child['alt'].replace('Profile image for ', '')
                        ajax_path = child['onclick'].split('\'')[1]
                        officer['id'] = int(ajax_path.split('=')[-1])
                        profile_soup = get_soup(ROOT + ajax_path, yaleconnect_cookie)
                        email_li = profile_soup.find('li', {'class': 'mdi-email'})
                        if email_li:
                            officer['email'] = email_li.find('a')['href'].replace('mailto:', '')
                        organizations[i]['officers'].append(officer)
                elif current_header is None:
                    pass
                else:
                    print(f'Encountered unknown About header {current_header}.')

    print('Inserting new data.')
    print(organizations)
    db.session.query(officerships).delete()
    Person.query.delete()
    Organization.query.delete()
    for organization_dict in organizations:
        officers = organization_dict.pop('officers')
        organization = Organization(**organization_dict)
        db.session.add(organization)
        organization.officers[:] = []
        # Remove empty values
        organization_dict = {prop: value for prop, value in organization_dict.items() if value}
        for officer in officers:
            person = Person.query.get(officer['id'])
            if not person:
                person = Person(**officer)
                db.session.add(person)
            organization.officers.append(person)
    db.session.commit()
    print('Done.')
