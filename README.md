Business Board tool
======
web application to help business board members and advertisers keep a history of advertising interactions


Functionality
======
###Business
- Login using Google account authentication
- Upon entering the business home page, if no company attached to user, then will prompt to enter contact -information and company information
- Business home page contains links to logout, update contact info, place an order, and preview sizes (static image from Google for now)
- Home page also contains history of ads the company has placed in date order with all of their info
- Placing an order allows selection of all aspects like the current contract form. Companies can place multiple orders of ads and see them on their home page along with each ad’s status

###Business Board
- Enter the business home page (using dummy login), and see listing of ads by issue, unpaid, and company
- Edit company info by going to company profiles and then clicking on the company’s name
- View all of company’s history when go to profile page



Instructions
======
This is dependent on Google App Engine and Google Cloud Storage. Unzip file then:
### Run locally
 ./dev_appserver.py ads-tools/


Demo
======
coherent-server-503.appspot.com