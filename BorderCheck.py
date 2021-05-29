#importing relevant libraries 

import json
from datetime import datetime
import pandas as pd
pd.set_option('display.max_columns', 30)

from sqlalchemy import create_engine, DateTime, Date
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bs4 import BeautifulSoup
import requests

#note: create MySQL database and update user, pw, db, localhost below with correct credentials. 

user = "root"
pw = "12345"
db = "covid"
localhost = "localhost"

engine = create_engine(f"mysql+pymysql://{user}:{pw}@{localhost}/{db}")

Base = declarative_base()
Base.metadata.bind = engine

class Api_obj(Base):
    __tablename__ = 'api_data'
    id = Column(Integer, primary_key=True)
    continent = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    population = Column(Integer)

    cases_new = Column(Integer)
    cases_active = Column(Integer)
    cases_critical = Column(Integer)
    cases_recovered = Column(Integer)
    cases_million_pop = Column(Integer)
    cases_total = Column(Integer)

    deaths_new = Column(Integer)
    deaths_million_pop = Column(Integer)
    deaths_total = Column(Integer)

    tests_million_pop = Column(Integer)
    tests_total = Column(Integer)

    day = Column(Date, nullable=True)
    time = Column(DateTime, nullable=True)
    created = Column(TIMESTAMP, nullable=False, server_default=func.now())

    def __init__(self, continent, country, population, cases_new, cases_active, cases_critical, cases_recovered,
                 cases_million_pop, cases_total, deaths_new, deaths_million_pop, deaths_total,
                 tests_million_pop, tests_total, day, time, created):
        self.continent = continent
        self.country = country
        self.population = population

        self.cases_new = cases_new
        self.cases_active = cases_active
        self.cases_critical = cases_critical
        self.cases_recovered = cases_recovered
        self.cases_million_pop = cases_million_pop
        self.cases_total = cases_total

        self.deaths_new = deaths_new
        self.deaths_million_pop = deaths_million_pop
        self.deaths_total = deaths_total

        self.tests_million_pop = tests_million_pop
        self.tests_total = tests_total

        self.day = day
        self.time = time
        self.created = created

Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
session = DBSession()

flag = True
while flag:
    try:
        url = "https://covid-193.p.rapidapi.com/statistics"
        api_country = input('Type a country: ')
        querystring = {"country": api_country}
        headers = {
            'x-rapidapi-key': "d26bad1974msh47ff50490e49ddbp12e94fjsn08f3485a7889",
            'x-rapidapi-host': "covid-193.p.rapidapi.com"
        }
        response = requests.request("GET", url, headers=headers, params=querystring)
        json_data = response.json()
        data_dict = json_data['response'][0]
        flag = False
    except IndexError:
        print('\nNo match, try again')


def flatten_dict(pyobj, keystring=''):
    if type(pyobj) == dict:
        keystring = keystring + '_' if keystring else keystring
        for k in pyobj:
            yield from flatten_dict(pyobj[k], keystring + str(k))
    else:
        yield keystring, pyobj

data_dict = dict(flatten_dict(data_dict))

continent = data_dict['continent']
country = data_dict['country']
population = data_dict['population']
cases_new = data_dict['cases_new']
cases_active = data_dict['cases_active']
cases_critical = data_dict['cases_critical']
cases_recovered = data_dict['cases_recovered']
cases_million_pop = data_dict['cases_1M_pop']
cases_total = data_dict['cases_total']
deaths_new = data_dict['deaths_new']
deaths_million_pop = data_dict['deaths_1M_pop']
deaths_total = data_dict['deaths_total']
tests_million_pop = data_dict['tests_1M_pop']
tests_total = data_dict['tests_total']
day = data_dict['day']
time = data_dict['time']
created = datetime.now()

search = Api_obj(continent, country, population, cases_new, cases_active, cases_critical, cases_recovered, cases_million_pop,
             cases_total, deaths_new, deaths_million_pop, deaths_total, tests_million_pop, tests_total, day, time, created)
session.add(search)
session.commit()

df = pd.DataFrame(data_dict, index=[0])


df = df.iloc[:, 1:15]
df.insert(5,'cases_active_%',(df['cases_active'] / df['population'].sum()) * 100)


#using beautiful soup to request and convert into soup
url = 'https://www.trip.com/travel-restrictions-covid-19'
response = requests.get(url)
soup = BeautifulSoup(response.content)

#finding each country and returning to a list
country_list = list(soup.find_all('div',attrs={'class':'country'}))

#compiling a dictionary to incorporate country name, border status, body of text
filtered_countries = []
for countries in country_list:
    name = countries.find_all("span",attrs={"class":"countryName"})[0].get_text()
    info = countries.find_all('div',attrs={'class':'content'})[0].get_text()
    if len(countries.find_all("span",attrs={"class":"countryStatusRed"})) > 0:
        filtered_countries.append({'country':name,'status': countries.find_all("span",attrs={"class":"countryStatusRed"})[0].get_text(),'info':info})
    elif len(countries.find_all("span",attrs={"class":"countryStatusYellow"})) > 0:
        filtered_countries.append({'country':name,'status': countries.find_all("span",attrs={"class":"countryStatusYellow"})[0].get_text(),'info':info})
    else:
        filtered_countries.append({'country':name,'status': countries.find_all("span",attrs={"class":"countryStatusGreen"})[0].get_text(),'info':info})

#converitng to a pd dataframe
restrictions_df = pd.DataFrame(filtered_countries)

df = pd.merge(df, restrictions_df, how="left", on=["country"])
status = list(df['status'])[0]

#printing country border information and statistics to user.

comment2 = f"border status: {status}. With a population of {population:,.0f}, {country} has now {cases_active:,.0f} active cases, {cases_active/population:%} of population."
print(comment2)
