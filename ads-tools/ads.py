import os
import urllib

# from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers 
from google.appengine.api import images

import jinja2
import webapp2
import time
import webapp2_extras.appengine.auth.models as auth_models
from webapp2_extras.auth import security
from webapp2_extras.appengine import auth
from webapp2_extras.auth import sessions

from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class User(auth_models.User):
  def set_password(self, raw_password):
    """Sets the password for the current user

    :param raw_password:
        The raw password which will be hashed and stored
    """
    self.password = security.generate_password_hash(raw_password, length=12)

  @classmethod
  def get_by_auth_token(cls, user_id, token, subject='auth'):
    """Returns a user object based on a user ID and token.

    :param user_id:
        The user_id of the requesting user.
    :param token:
        The token string to be verified.
    :returns:
        A tuple ``(User, timestamp)``, with a user object and
        the token timestamp, or ``(None, None)`` if both were not found.
    """
    token_key = cls.token_model.get_key(user_id, subject, token)
    user_key = ndb.Key(cls, user_id)
    # Use get_multi() to save a RPC call.
    valid_token, user = ndb.get_multi([token_key, user_key])
    if valid_token and user:
        timestamp = int(time.mktime(valid_token.created.timetuple()))
        return user, timestamp

    return None, None

def company_key(company_name="default company"):
    """Constructs a Datastore key for a Company entity with company_name."""
    return ndb.Key('Company', company_name)


class Company(ndb.Model): 
    user = ndb.KeyProperty(kind=User)
    company_name = ndb.StringProperty()
    notes = ndb.TextProperty(indexed=False, repeated=True)
    address = ndb.StringProperty()

class Contact(ndb.Model): 
    company = ndb.KeyProperty(kind=Company)
    name = ndb.StringProperty()
    position = ndb.StringProperty()
    phonenumber = ndb.StringProperty()
    email = ndb.StringProperty()


class Advertisement(ndb.Model): 
    company = ndb.KeyProperty(kind=Company)
    date = ndb.DateTimeProperty(auto_now_add=True)
    picture = ndb.BlobProperty(default=None)
    pic_url = ndb.StringProperty()
    size = ndb.StringProperty()
    issues = ndb.IntegerProperty(repeated=True)
    cost = ndb.IntegerProperty()
    status = ndb.StringProperty(choices=['Unpaid','Complete','Processing','In Print'])
    description = ndb.TextProperty()

class WelcomePage(webapp2.RequestHandler):
    def get(self):
    #     if users.get_current_user():
    #         url2 = users.create_logout_url(self.request.uri)
    #         url2_linktext = 'Logout'
    #         url = '/main'
    #         url_linktext = 'Enter'
    #     else:
    #         url2= '/staff'
    #         url2_linktext='Login Staff'
    #         url = users.create_login_url(self.request.uri)
    #         url_linktext = 'Login Company'

        template_values = {
            'url': 'foo',
            'url_linktext': 'foo',
            'url2': 'foo',
            'url2_linktext': 'foo',
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))

# main page redirects here
class MainPage(webapp2.RequestHandler):
    def get(self):
        usr = users.get_current_user()
        company_query = Company.query(Company.user == usr)
        this_comp = company_query.fetch(1)
        # company info exists
        if this_comp and usr:
            ads_query = Advertisement.query(Advertisement.company==this_comp[0].key).order(-Advertisement.date)
            ads = ads_query.fetch(10)
            template_values = {
                  'ads': ads,
                  'url':users.create_logout_url(self.request.uri),
            }
            template = JINJA_ENVIRONMENT.get_template('company.html')
            self.response.write(template.render(template_values))
        if not this_comp:
            self.redirect('/contact')


def user_required(handler):
  """
    Decorator that checks if there's a user associated with the current session.
    Will also fail if there's no session present.
  """
  def check_login(self, *args, **kwargs):
    auth = self.auth
    if not auth.get_user_by_session():
      self.redirect(self.uri_for('login'), abort=True)
    else:
      return handler(self, *args, **kwargs)

  return check_login

class BaseHandler(webapp2.RequestHandler):
  @webapp2.cached_property
  def auth(self):
    """Shortcut to access the auth instance as a property."""
    return auth.get_auth()

  @webapp2.cached_property
  def user_info(self):
    """Shortcut to access a subset of the user attributes that are stored
    in the session.

    The list of attributes to store in the session is specified in
      config['webapp2_extras.auth']['user_attributes'].
    :returns
      A dictionary with most user information
    """
    return self.auth.get_user_by_session()

  @webapp2.cached_property
  def user(self):
    """Shortcut to access the current logged in user.

    Unlike user_info, it fetches information from the persistence layer and
    returns an instance of the underlying model.

    :returns
      The instance of the user model associated to the logged in user.
    """
    u = self.user_info
    return self.user_model.get_by_id(u['user_id']) if u else None

  @webapp2.cached_property
  def user_model(self):
    """Returns the implementation of the user model.

    It is consistent with config['webapp2_extras.auth']['user_model'], if set.
    """    
    return self.auth.store.user_model

  @webapp2.cached_property
  def session(self):
      """Shortcut to access the current session."""
      return self.session_store.get_session(backend="datastore")

  def render_template(self, view_filename, params=None):
    if not params:
      params = {}
    user = self.user_info
    params['user'] = user
    path = os.path.join(os.path.dirname(__file__), 'views', view_filename)
    self.response.out.write(template.render(path, params))

  def display_message(self, message):
    """Utility function to display a template with a simple message."""
    params = {
      'message': message
    }
    self.render_template('message.html', params)

  # this is needed for webapp2 sessions to work
  def dispatch(self):
      # Get a session store for this request.
      self.session_store = sessions.get_store(request=self.request)

      try:
          # Dispatch the request.
          webapp2.RequestHandler.dispatch(self)
      finally:
          # Save all sessions.
          self.session_store.save_sessions(self.response)

class MainHandler(BaseHandler):
  def get(self):
    self.render_template('home.html')

class SignupHandler(BaseHandler):
  def get(self):
    self.render_template('signup.html')

  def post(self):
    user_name = self.request.get('username')
    email = self.request.get('email')
    name = self.request.get('name')
    password = self.request.get('password')
    last_name = self.request.get('lastname')

    unique_properties = ['email_address']
    user_data = self.user_model.create_user(user_name,
      unique_properties,
      email_address=email, name=name, password_raw=password,
      last_name=last_name, verified=False)
    if not user_data[0]: #user_data is a tuple
      self.display_message('Unable to create user for email %s because of \
        duplicate keys %s' % (user_name, user_data[1]))
      return
    
    user = user_data[1]
    user_id = user.get_id()

    token = self.user_model.create_signup_token(user_id)

    verification_url = self.uri_for('verification', type='v', user_id=user_id,
      signup_token=token, _full=True)

    msg = 'Send an email to user in order to verify their address. \
          They will be able to do so by visiting <a href="{url}">{url}</a>'

    self.display_message(msg.format(url=verification_url))

class ForgotPasswordHandler(BaseHandler):
  def get(self):
    self._serve_page()

  def post(self):
    username = self.request.get('username')

    user = self.user_model.get_by_auth_id(username)
    if not user:
      logging.info('Could not find any user entry for username %s', username)
      self._serve_page(not_found=True)
      return

    user_id = user.get_id()
    token = self.user_model.create_signup_token(user_id)

    verification_url = self.uri_for('verification', type='p', user_id=user_id,
      signup_token=token, _full=True)

    msg = 'Send an email to user in order to reset their password. \
          They will be able to do so by visiting <a href="{url}">{url}</a>'

    self.display_message(msg.format(url=verification_url))
  
  def _serve_page(self, not_found=False):
    username = self.request.get('username')
    params = {
      'username': username,
      'not_found': not_found
    }
    self.render_template('forgot.html', params)


class VerificationHandler(BaseHandler):
  def get(self, *args, **kwargs):
    user = None
    user_id = kwargs['user_id']
    signup_token = kwargs['signup_token']
    verification_type = kwargs['type']

    # it should be something more concise like
    # self.auth.get_user_by_token(user_id, signup_token)
    # unfortunately the auth interface does not (yet) allow to manipulate
    # signup tokens concisely
    user, ts = self.user_model.get_by_auth_token(int(user_id), signup_token,
      'signup')

    if not user:
      logging.info('Could not find any user with id "%s" signup token "%s"',
        user_id, signup_token)
      self.abort(404)
    
    # store user data in the session
    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)

    if verification_type == 'v':
      # remove signup token, we don't want users to come back with an old link
      self.user_model.delete_signup_token(user.get_id(), signup_token)

      if not user.verified:
        user.verified = True
        user.put()

      self.display_message('User email address has been verified.')
      return
    elif verification_type == 'p':
      # supply user to the page
      params = {
        'user': user,
        'token': signup_token
      }
      self.render_template('resetpassword.html', params)
    else:
      logging.info('verification type not supported')
      self.abort(404)

class SetPasswordHandler(BaseHandler):

  @user_required
  def post(self):
    password = self.request.get('password')
    old_token = self.request.get('t')

    if not password or password != self.request.get('confirm_password'):
      self.display_message('passwords do not match')
      return

    user = self.user
    user.set_password(password)
    user.put()

    # remove signup token, we don't want users to come back with an old link
    self.user_model.delete_signup_token(user.get_id(), old_token)
    
    self.display_message('Password updated')

class LoginHandler(BaseHandler):
  def get(self):
    self._serve_page()

  def post(self):
    username = self.request.get('username')
    password = self.request.get('password')
    try:
      u = self.auth.get_user_by_password(username, password, remember=True,
        save_session=True)
      self.redirect(self.uri_for('home'))
    except (InvalidAuthIdError, InvalidPasswordError) as e:
      logging.info('Login failed for user %s because of %s', username, type(e))
      self._serve_page(True)

  def _serve_page(self, failed=False):
    username = self.request.get('username')
    params = {
      'username': username,
      'failed': failed
    }
    self.render_template('login.html', params)

class LogoutHandler(BaseHandler):
  def get(self):
    self.auth.unset_session()
    self.redirect(self.uri_for('home'))

class AuthenticatedHandler(BaseHandler):
  @user_required
  def get(self):
    self.render_template('authenticated.html')


# form for filling out contact info
class ContactInfo(webapp2.RequestHandler):
    def get(self):
        current_user = users.get_current_user()
        if current_user:
            comp_query = Company.query(Company.user == current_user)
            this_comp = comp_query.fetch(1)
            if this_comp:
              this_comp = this_comp[0]
              this_contact= Contact.query(Contact.company == this_comp.key).fetch(5)[0]        
              template_values={
                  'company': this_comp.company_name,
                  'name': this_contact.name,
                  'position':this_contact.position,
                  'phonenumber':this_contact.phonenumber,
                  'email': this_contact.email,
                  'address': this_comp.address,
              }
            else:
              template_values={
              'company':"",
              'name': "",
              'position':"",
              'phonenumber':"",
              'email': "",
              'address': "",  
              }
            template = JINJA_ENVIRONMENT.get_template('contact.html')
            self.response.write(template.render(template_values))
        else:
            time.sleep(0.2)
            self.redirect('/')


    def post(self):
      company_name = self.request.get('company')
      name = self.request.get('name')
      this_comp = Company(user=users.get_current_user(), company_name=company_name, address=self.request.get('address'))
      this_comp.put()
      this_contact = Contact(company=this_comp.key, name=self.request.get('name'), position=self.request.get('position'), phonenumber=self.request.get('phonenumber'), email=self.request.get('email'))
      this_contact.put()
      time.sleep(0.2)
      self.redirect('/')


# order page redirects
class BuyAd(webapp2.RequestHandler):
    def get(self):
      comp_query = Company.query(Company.user == users.get_current_user())
      this_comp = comp_query.fetch(1)
      if this_comp:
        this_comp = this_comp[0]
        contact_query = Contact.query(Contact.company == this_comp.key)
        this_contact = contact_query.fetch(1)[0]
        template_values={
          'company_name': this_comp.company_name,
          'issues': [1, 2, 3, 4, 5],
          'name': this_contact.name,
        }
      template = JINJA_ENVIRONMENT.get_template('buyad.html')
      self.response.write(template.render(template_values))
      return

    def post(self):

        company_name = self.request.get('company_name',
                                          DEFAULT_COMPANY_NAME)
        comp_query = Company.query(Company.user == users.get_current_user())
        this_comp = comp_query.fetch(1)
        pic = self.request.get('img')
        if this_comp:
            this_comp = this_comp[0]
            this_ad = Advertisement(
                  company = this_comp.key,
                  picture = pic,
                  size = self.request.get('size'),
                  issues = [int(s) for s in self.request.get('issues', allow_multiple=True)],
                  cost = int(self.request.get('cost')),
                  status='Unpaid',
                  description = self.request.get('description'),
              )
            # this_ad.pic_url = images.get_serving_url(pic, size=100, crop=True),
            this_ad.put()
        time.sleep(0.1)
        self.redirect('/')

class AdInfo(webapp2.RequestHandler):
    def get(self):
      comp_query = Company.query(Company.user == users.get_current_user())
      this_comp = comp_query.fetch(1)
      if this_comp:
        this_comp = this_comp[0]
        contact_query = Contact.query(Contact.company== this_comp.key)
        this_contact = contact_query.fetch(1)[0]
        template_values={
          'company_name': this_comp.company_name,
          'name': this_contact.name,
          'issues': [1, 2, 3, 4, 5],
        }
      template = JINJA_ENVIRONMENT.get_template('info.html')
      self.response.write(template.render(template_values))

class StaffPage(webapp2.RequestHandler):
    def get(self):
        all_ads=[]
        for x in xrange(1, 6):
            ads_query=Advertisement.query(Advertisement.issues.IN([x]))
            all_ads.append(ads_query.fetch())
        unpaid_query=Advertisement.query(Advertisement.status=='Unpaid')
        unpaid=unpaid_query.fetch()
        company_query=Company.query()
        companies = company_query.fetch()
        template_values={
            'all_ads': all_ads,
            'unpaid': unpaid,
            'companies':companies,
        }
        template = JINJA_ENVIRONMENT.get_template('staff.html')
        self.response.write(template.render(template_values))
        
class CompanyProfile(webapp2.RequestHandler):
    def post(self): 
        comp_query = Company.query(Company.company_name== self.request.get('company_name'))
        if comp_query.fetch():
            company = comp_query.fetch()[0]
            ads_query = Advertisement.query(Advertisement.company==company.key).order(-Advertisement.date)
            ads = ads_query.fetch()
            contact_query = Contact.query(Contact.company == company.key)
            contact = contact_query.fetch()[0]

            template_values={
                'ads':ads,
                'contact': contact,
                'company':company,
                'company_name': self.request.get('company_name'),
                'notes':company.notes,
            }
            template = JINJA_ENVIRONMENT.get_template('company_profile.html')
            self.response.write(template.render(template_values))

class UpdateCompany(webapp2.RequestHandler):
    def post(self):
        comp_query = Company.query(Company.company_name== self.request.get('company_name'))
        if comp_query.fetch():
            company = comp_query.fetch()[0]
            contact_query = Contact.query(Contact.company == company.key)
            company.address=self.request.get('address')
            company.notes=list(self.request.get('notes'))
            contact = contact_query.fetch()[0]
            template_values= {
                'contact':contact,
                'company':company
            }
            time.sleep(0.1)
            template = JINJA_ENVIRONMENT.get_template('update_company.html')
            self.response.write(template.render(template_values))
        else:
            comp_query = Company.query(Company.company_name== self.request.get('company'))
            company = comp_query.fetch()[0]
            contact_query = Contact.query(Contact.company == company.key) 
            contact = contact_query.fetch()[0]
            company.company_name = self.request.get('company')
            company.notes = [self.request.get('notes')]
            company.address = self.request.get('address')
            company.put()

            contact.name = self.request.get('name')
            contact.position = self.request.get('position')
            contact.phonenumber = self.request.get('phonenumber')
            contact.email = self.request.get('email')
            contact.put()

            contact.put()
            time.sleep(0.1)
            self.redirect('/staff#companies')

class GetImage(webapp2.RequestHandler):
    def get(self):
        company = self.request.get('company')
        ad = Advertisement.query(Advertisement.company==company)
        if (ad.pic_url and ad.picture):
            self.response.headers['Content-Type'] = 'image/jpeg'
            self.response.out.write(ad.picture)
        else:
            self.redirect('/images/lampoon.png')


config = {
  'webapp2_extras.auth': {
    'user_model': 'models.User',
    'user_attributes': ['name']
  },
  'webapp2_extras.sessions': {
    'secret_key': 'biz-board-tool'
  }
}
 

application = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/signup', SignupHandler),
    ('/<type:v|p>/<user_id:\d+>-<signup_token:.+>', VerificationHandler),
    ('/password', SetPasswordHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/forgot', ForgotPasswordHandler),
    ('/authenticated', AuthenticatedHandler),
    # ('/', WelcomePage),
    ('/order', BuyAd),
    ('/main', MainPage),
    ('/contact', ContactInfo),
    ('/info', AdInfo),
    ('/staff', StaffPage),
    ('/company_profile', CompanyProfile),
    ('/update_company', UpdateCompany),
    ('/images', GetImage)
], debug=True, config=config)
