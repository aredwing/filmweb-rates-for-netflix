# filmweb-rates-for-netflix
Scripts for getting filmweb user rates for netflix content

To gain all netflix movies titles into JSON file invoke:
```
python3 ./getNflixFilms.py
```

You should find ```nfmovies.json``` file in current directory

To gain filmweb users rates for Netflix content type:
```
python3 ./getFilmwebRates.py nfmovies.json <filmwebUsername> <filmwebPasswd>
```
After processing (it may take up to 1h) you should find ```filmwebRates.csv``` file with final results.
