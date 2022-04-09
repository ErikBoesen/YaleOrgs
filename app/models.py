from app import app, db
from app.search import SearchableMixin
import jwt
import datetime
from sqlalchemy.sql import collate


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.String, primary_key=True)
    registered_on = db.Column(db.Integer)
    last_seen = db.Column(db.Integer)
    admin = db.Column(db.Boolean, default=False)

    keys = db.relationship('Key', cascade='all,delete', back_populates='user')

    def generate_token(self):
        """
        Generate auth token.
        :return: token and expiration timestamp.
        """
        now = int(datetime.datetime.utcnow().timestamp())
        payload = {
            'iat': now,
            'sub': self.id,
        }
        return jwt.encode(
            payload,
            app.config.get('SECRET_KEY'),
            algorithm='HS256'
        )

    def create_key(self, description, internal=False):
        """
        Generate new API key object.
        :param description: description to add to the key.
        :return: newly created key object associated with this user.
        """
        token = self.generate_token()
        key = Key(
            token=token,
            description=description,
            internal=internal,
            created_at=int(datetime.datetime.utcnow().timestamp())
        )
        key.approved = True
        self.keys.append(key)
        return key

    @staticmethod
    def from_token(token):
        """
        Decode/validate an auth token.
        :param token: token to decode.
        :return: User whose token this is, or None if token invalid/no user associated
        """
        try:
            key = Key.query.filter_by(token=token).first()
            if key is None or not key.approved:
                return None
            key.uses += 1
            key.last_used = int(datetime.datetime.utcnow().timestamp())
            payload = jwt.decode(token, app.config.get('SECRET_KEY'), algorithms=['HS256'])
            return User.query.get(payload['sub'])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            # Signature expired, or token otherwise invalid
            return None


class Organization(SearchableMixin, db.Model):
    __tablename__ = 'organization'
    __searchable__ = (
    )
    __filterable_identifiable__ = (
    )
    __filterable__ = (
    )
    __serializable__ = (
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Identifiers
    name = db.Column(db.String, nullable=False)

    """
    @staticmethod
    def search(criteria):
        print('Searching by criteria:')
        print(criteria)
        person_query = Person.query
        query = criteria.get('query')
        filters = criteria.get('filters')
        page = criteria.get('page')
        page_size = criteria.get('page_size')
        if query:
            person_query = Person.query_search(query)
        else:
            person_query = person_query.order_by(
                #collate(Person.last_name, 'NOCASE'),
                #collate(Person.first_name, 'NOCASE'),
                Person.last_name,
                Person.first_name,
            )
        if filters:
            for category in filters:
                if category not in (Person.__filterable_identifiable__ + Person.__filterable__):
                    return None
                if not isinstance(filters[category], list):
                    filters[category] = [filters[category]]
                person_query = person_query.filter(getattr(Person, category).in_(filters[category]))
        if page:
            people = person_query.paginate(page, page_size or app.config['PAGE_SIZE'], False).items
        else:
            people = person_query.all()
        return people
        """


class Key(db.Model):
    __tablename__ = 'key'
    __serializable__ = ('id', 'token', 'uses', 'description', 'created_at', 'last_used')
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, unique=True, nullable=False)
    uses = db.Column(db.Integer, default=0)
    description = db.Column(db.String, nullable=False)
    internal = db.Column(db.Boolean, default=False)
    approved = db.Column(db.Boolean, nullable=False)
    deleted = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.Integer)
    last_used = db.Column(db.Integer)

    user_id = db.Column(db.String, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='keys')
