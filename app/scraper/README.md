# Scraper
Our scraper crawls Yale's websites to obtain the data we provide.

## Running the scraper on your local machine
The scraper requires Redis as an additional dependency. On a Mac with Homebrew installed, you can get Redis with `brew install redis`. For other platforms, install Redis using [this guide](https://redis.io/topics/quickstart) or by googling "install redis [your platform]".

To run the scraper process locally (not necessary if you want to view the website without user data), first start the Celery task manager:
```sh
./celery.sh
```
In order to actually execute the scraper, visit [localhost:5000/scraper](http://localhost:5000/scraper) and fill in the fields. To retrieve the tokens you need, you'll want to use the developer tools ("inspect element") for your browser, specifically the Network tab, to view the headers on requests made to the Face Book and Directory. See below for more information on what headers to grab.

## Running the scraper on production
Visit [yaleorgs.com/scraper](https://yaleorgs.com/scraper) to view the scraper interface. Obtain the relevant tokens as detailed below.

If you are denied access to the scraper page, reach out to the team leader as you will probably need to be given admin privileges through the database in order to access this page.

Open the [YaleConnect](https://yaleconnect.yale.edu) and log in if you aren't already authenticated. In the developer tools, choose any request and grab the `Cookie` property in its entirety.

After you've inputted the requisite cookies, simply click "Run Scraper" and verify that the button turns green.
