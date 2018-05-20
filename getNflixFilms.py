from lxml import html
import requests
import re
import json

def getPagesCount():
    url = 'https://www.nflix.pl/netflix-polska-lista-wszystkich-dostepnych-tytulow/'
    page = requests.get(url)

    tree = html.fromstring(page.content)
    pagesCount = tree.xpath('//td[@width="25%"]/b/a/text()')
    if(len(pagesCount) > 0):
        return int(pagesCount[0])
    return 0


def getMoviesList(pagesCount):
    years = []
    movies = []

    for i in range(1, pagesCount+1):
        print("Parsing " + str(i) + " / " + str(pagesCount))
        url = "https://www.nflix.pl/netflix-polska-lista-wszystkich-dostepnych-tytulow/?o=all_f&p=" + str(i)
        page = requests.get(url)

        # remove some invalid xml strings
        invalidStr = """<script async src="//pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>"""
        tmpContent = "" + page.content.decode("utf-8")
        validContent = tmpContent[0:tmpContent.find(invalidStr)] + tmpContent[tmpContent.find(invalidStr) + len(invalidStr):]
        validContent = validContent.replace("&raquo", "")

        # convert string into html tree
        tree = html.fromstring(validContent)

        year = tree.xpath('//td/center/text()')
        for y in year:
            mody=y.lstrip()
            if re.match(r'\([0-9]{4}\)', mody):
                years.append(mody[1:5])

        title = tree.xpath('//td/center/a/text()')
        for t in title:
            tStr = t.lstrip()
            if len(tStr) > 0 :
                movies.append(tStr)

    if len(movies) != len(years):
        print("Parsing error")
        exit(1)
    else:
        return movies,years

def saveResultsToFile(filename, movies, years):
    data = {}
    data['movies'] = []
    for i in range(0, len(years)):
        if (movies[i].find(" / ") > 0):
            titles = movies[i].split(' / ')
            data['movies'].append({"year": years[i], "plTitle": titles[1], "enTitle": titles[0]})
        else:
            data['movies'].append({"year": years[i], "enTitle": movies[i]})

    json_data = json.dumps(data, ensure_ascii=False,indent=4)
    file = open(filename, 'w')
    file.write(json_data)
    file.close()
    print("Successfully saved " +str(len(movies)) + " films to " + filename +" file")


if __name__ == "__main__":
    movies, years = getMoviesList(getPagesCount())
    saveResultsToFile('nfmovies.json', movies, years)
