from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import urllib.parse
import json
from difflib import SequenceMatcher
import requests
from lxml import html
import sys
import os.path

# download the chrome driver from https://sites.google.com/a/chromium.org/chromedriver/downloads and put it in /usr/bin

class Film:
    def __init__(self, title, year, fwLink, orgTitle, rate=0, rateCount=0, duration=0, genre = "", userRate=0):
        self.title=title
        self.year = year
        self.rate = rate
        self.rateCount = rateCount
        self.fwLink = fwLink
        self.userRate = userRate
        self.orgTitle = orgTitle
        self.duration = duration
        self.genre = genre


class FilmwebScraper:
    def __init__(self, user, passwd):
        self.password = passwd
        self.username = user
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--window-size=1920x1080")
        self.driver = webdriver.Chrome(chrome_options=self.chrome_options)

    def login(self):
        try:
            self.driver.get("https://ssl.filmweb.pl/login")
            self.driver.find_element_by_name('j_username').send_keys(self.username)
            self.driver.find_element_by_name('j_password').send_keys(self.password)
            self.driver.find_element_by_xpath('//input[@type="submit"]').click()
        except:
            print("Error occurred during login")
            exit(1)

    def _getFilmsByTitle(self, title):
        _title = title.replace(" ", "+")
        result = requests.get("http://www.filmweb.pl/films/search?q=" + urllib.parse.quote_plus(_title))

        tree = html.fromstring(result.content)
        films = tree.xpath('//div[@class="filmPreview filmPreview--FILM Film"]')
        retFilms = []
        for film in films:
            retFilms.append(self.htmlObjToFilm(film))

        return retFilms

    def htmlObjToFilm(self, obj):
        try:
            title = obj.xpath('.//h3[@class="filmPreview__title"]/text()')[0]
            year = int(obj.xpath('.//span[@class="filmPreview__year"]/text()')[0])
            link = "http://filmweb.pl" + obj.xpath('.//a[@class="filmPreview__link"]/@href')[0]
        except IndexError:
            print("Cannot get title/year/link for some movie")
            return None

        try:
            orgTitle = obj.xpath('.//div[@class="filmPreview__originalTitle"]/text()')[0]
        except IndexError:
            orgTitle = title

        try :
            rate = obj.xpath('.//div[@class="filmPreview__rateBox rateBox "]/@data-rate')[0]
            rateCount= obj.xpath('.//div[@class="filmPreview__rateBox rateBox "]/@data-count')[0]
        except IndexError:
            rate = 0
            rateCount = 0

        try :
            duration = obj.xpath('.//div[@class="filmPreview__filmTime"]/@data-duration')[0]
            genre = obj.xpath('.//div[@class="filmPreview__info filmPreview__info--genres"]//a/text()')
        except IndexError:
            duration = 0
            genre = ""

        return Film(title, year, link, orgTitle, rate, rateCount, duration, genre)


    def getUserRate(self, film):
        try:
            self.driver.get(film.fwLink)
            film.userRate = self.driver.find_element_by_xpath('//div[@class="rateButtons rated"]').get_attribute("data-rate")
        except:
            film.userRate = 0
        return film.userRate

    def getFilmByTitle(self, title, year, alternativeTitle = ""):

        similarityRate = 0.8  # title similarity rate
        yearRange = 2  # allowed drift for film relase date (it may be different depending on a country)

        # get list of films related to 'title' from filmweb
        films = self._getFilmsByTitle(title)

        # search for the right film
        for film in films:
            if (film.year > year + yearRange or film.year < year - yearRange):
                continue

            refTitle = title.lower()
            _title = film.title.lower()
            _orgTitle = film.orgTitle.lower()
            if (SequenceMatcher(None, _title, refTitle).ratio() >= similarityRate ) or \
                    (SequenceMatcher(None, _orgTitle, refTitle).ratio() >= similarityRate ):
                return film

            if len(alternativeTitle)>0:
                alterTitle = alternativeTitle.lower()
                if (SequenceMatcher(None, _title, alterTitle).ratio() >= similarityRate) or \
                    (SequenceMatcher(None, _orgTitle, alterTitle).ratio() >= similarityRate ):
                    return film

        return None

    def logout(self):
        self.driver.close()

class ResultCsvWriter:
    def __init__(self, filename, sep=';'):
        self.fileName = filename
        self.file = open(self.fileName, 'w')
        self.separator = sep

    def addLine(self, values):
        line = ""
        for v in values:
            line = line + str(v) + self.separator

        self.file.write(line[0:len(line)-1] + '\n')

    def close(self):
        self.file.close()


def getFilmwebRates(nflixFilms, fwUsername, fwPasswd):
    resultFileName = 'filmwebRates.csv'
    resFile = ResultCsvWriter(resultFileName)
    # adding header to file
    resFile.addLine(["filmTitle", "year", "rate" , "rateCount","filmwebLink", "userRate", "genre", "duration"])

    scraper = FilmwebScraper(fwUsername, fwPasswd)
    scraper.login()

    data = json.load(open(nflixFilms))

    filmsCount = len(data['movies'])
    successfulCount = 0
    processedCount=0

    for nfFilm in data['movies']:
        if "plTitle" in nfFilm:
            resFilm = scraper.getFilmByTitle(nfFilm['enTitle'], int(nfFilm['year']), nfFilm['plTitle'])
        else:
            resFilm = scraper.getFilmByTitle(nfFilm['enTitle'], int(nfFilm['year']))

        if resFilm is None:
            print(" === Could not find film : " + nfFilm['enTitle'] + " " + nfFilm['year'])
        else:
            successfulCount = successfulCount + 1
            scraper.getUserRate(resFilm)
            resFile.addLine([nfFilm['enTitle'], resFilm.year, str(resFilm.rate).replace('.', ','),
                             resFilm.rateCount, '=HYPERLINK("'+resFilm.fwLink + '")', resFilm.userRate,
                            resFilm.genre, resFilm.duration])

        processedCount = processedCount+1
        print("Processing {} of {}".format(processedCount, filmsCount))
        if processedCount>20:
            break

    resFile.close()
    scraper.logout()

    print("Result: {}/{} successfully gained and saved to {}".format(successfulCount,filmsCount, resultFileName))

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Using: {} <nflixFilms.json> <filmwebUsername> <filmwebPasswd>".format(sys.argv[0]))
        exit(1)
    if os.path.exists(sys.argv[1]) == False:
        print("Could not find {} file".format(sys.argv[1]))
        exit(1)
    getFilmwebRates(sys.argv[1], sys.argv[2], sys.argv[3])
