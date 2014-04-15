import os
import urllib


from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers 
from google.appengine.api import images

import jinja2
import webapp2
import time


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


DEFAULT_COMPANY_NAME = 'default_company'

def company_key(company_name=DEFAULT_COMPANY_NAME):
    """Constructs a Datastore key for a Company entity with company_name."""
    return ndb.Key('Company', company_name)

class Company(ndb.Model): 
    user = ndb.UserProperty()
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

        if users.get_current_user():
            url2 = users.create_logout_url(self.request.uri)
            url2_linktext = 'Logout'
            url = '/main'
            url_linktext = 'Enter'
        else:
            url2= '/staff'
            url2_linktext='Login Staff'
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login Company'

        template_values = {
            'url': url,
            'url_linktext': url_linktext,
            'url2': url2,
            'url2_linktext': url2_linktext,
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


application = webapp2.WSGIApplication([
    ('/', WelcomePage),
    ('/order', BuyAd),
    ('/main', MainPage),
    ('/contact', ContactInfo),
    ('/info', AdInfo),
    ('/staff', StaffPage),
    ('/company_profile', CompanyProfile),
    ('/update_company', UpdateCompany),
    ('/images', GetImage)
], debug=True)