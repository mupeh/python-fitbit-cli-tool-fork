# import matplotlib.pyplot as plt
import fitbit

# gather_keys_oauth2.py file needs to be in the same directory. 
# also needs to install cherrypy: https://pypi.org/project/CherryPy/
# pip install CherryPy
import gather_keys_oauth2 as Oauth2
import pandas as pd 
import datetime
import keys
import json
import os
import xml.etree.ElementTree as ET
import schedule
import time
import argparse

ROOT_PATH = '../fitbit_data'


def refresh_callback(token):
    """ Called when the OAuth token has been refreshed """
    f_data = {
        'access_token': token['access_token'],
        'refresh_token': token['refresh_token'],
        'expires_at': token['expires_at']
    }

    with open('access_token_cache_file.json', 'w') as outfile:
        json.dump(f_data, outfile)

def save_json_file(name, data, date):
    filename = str(date.strftime('%Y-%m-%d') + ".json")
    save_directory = os.path.join(ROOT_PATH, name)
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    path  = os.path.join(save_directory, filename)
    with open(path, 'w') as outfile:
        json.dump(data, outfile)

def get_tcx(logid):
    tcx = auth2_client.activity_tcx(log_id=logid)

    filename = str(logid) + ".tcx"

    direct = os.path.join(ROOT_PATH, 'tcx')
    if not os.path.exists(direct):
        os.makedirs(direct)
    path  = os.path.join(direct, filename)
    with open(path, 'w') as outfile:
        outfile.write(tcx.content.decode("utf-8"))

def get_data_for_date(date):

    data = auth2_client.get_sleep(date)
    save_json_file('sleep', data, date)

    data = auth2_client.activity_daily_summary(base_date=date.strftime('%Y-%m-%d'))
    save_json_file('activities', data, date)
    for activity in data['activities']:
        get_tcx(activity['logId'])

    supported_activities = ['heart', 'calories', 'distance', 'elevation', 'floors', 'steps']
    supported_detail     = ['1sec' ,  '1min'    , '1min'    , '1min'     , '1min'  , '1min']
    for i in range(len(supported_activities)):
        act = supported_activities[i]
        data = auth2_client.intraday_time_series('activities/' + act, base_date=date, detail_level=supported_detail[i])
        save_json_file(act, data, date)

    # to do: add active-zone-minutes, spo2 data, hrv data, breathing rate data also check out remaining usefull data (ie activity logs list)
    # https://dev.fitbit.com/build/reference/web-api/intraday/


def get_all_fitbit_data_yesterday():

    yesterday = datetime.datetime.today() - datetime.timedelta(days=1)

    get_data_for_date(yesterday)

    print('')
    print('Saved Heartrate/Steps/Sleep for: ' + str(yesterday))
    print('Waiting until: ' + polltime)
    time.sleep(5)


def get_oauth_client(with_refresh=True):

    VALID_USERNAME_PASSWORD_PAIRS, CLIENT_ID, CLIENT_SECRET = keys.get_keys()
    server=Oauth2.OAuth2Server(CLIENT_ID, CLIENT_SECRET)
    server.browser_authorize()

    ACCESS_TOKEN=str(server.fitbit.client.session.token['access_token'])
    REFRESH_TOKEN=str(server.fitbit.client.session.token['refresh_token'])

    if with_refresh:
        EXPIRES_AT=str(server.fitbit.client.session.token['expires_at'])
        refresh_callback(server.fitbit.client.session.token)
        with open('access_token_cache_file.json') as json_file:
            data = json.load(json_file)
            ACCESS_TOKEN = data['access_token']
            REFRESH_TOKEN = data['refresh_token']
            EXPIRES_AT = data['expires_at']

        auth2_client=fitbit.Fitbit(
            CLIENT_ID,
            CLIENT_SECRET,
            oauth2=True,
            expires_at=EXPIRES_AT,
            access_token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
            refresh_cb=refresh_callback
        )
        return auth2_client
    else:
        auth2_client=fitbit.Fitbit(
            CLIENT_ID,
            CLIENT_SECRET,
            oauth2=True,
            access_token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN
            )
        return auth2_client

if __name__ == '__main__':
    # argument parser for command line arguments
    parser = argparse.ArgumentParser(description='Fitbit API')
    # get bool for whether to use refresh token
    parser.add_argument('--auto', type=bool, default=False, help='Use refresh token')

    args = parser.parse_args()

    # get bool 
    if args.auto:
        auth2_client = get_oauth_client(with_refresh=True)
        polltime =  "10:00:00"
        schedule.every().day.at(polltime).do(get_all_fitbit_data_yesterday) 

        print('')
        print('Waiting until: ' + polltime)
        seconds = 0
        while True:
            schedule.run_pending()
            time.sleep(1)
            seconds += 1

            printstring = 'Hours since script start: %06.4f' % (seconds/3600)
            print(printstring, end='\r')
    else:
        auth2_client = get_oauth_client(with_refresh=False)

        begin = datetime.datetime(
            year = 2022, 
            month = 12, 
            day = 10
        )
        begin = datetime.datetime(
            year = 2023, 
            month = 4, 
            day = 16
        )
        end = datetime.datetime(
            year= 2023, 
            month = 6, 
            day=10
        )

        delta = end - begin
        # date_list = [datetime.datetime.today() - datetime.timedelta(days=x) for x in range(delta.days)]
        date_list = [end - datetime.timedelta(days=x) for x in range(delta.days)]

        for date in date_list:
            print(date)
            get_data_for_date(date)
