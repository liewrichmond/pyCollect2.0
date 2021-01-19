from __future__ import print_function
import pickle
import os.path
import datetime
import re
import base64
import json
from venmo_api import Client
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

months = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "July",
    8: "Aug",
    9: "Sept",
    10: "Oct",
    11: "Nov",
    12: "Dec"
}


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class Calculator():
    def __init__(self):
        self.creds = None
        self.service = None
        self.regexQuery = None
        self.connect_to_gmail()
        self.compile_regex()
        self.load_secrets()

    def load_secrets(self):
        if os.path.exists('secrets.json'):
            with open('secrets.json', 'rb') as secrets:
                variables = json.load(secrets)
                self.venmo_token = variables['venmoAccessToken']
                self.label_id = variables['labelId']
                self.tenants = variables['venmoUsernames']
        else:
            raise FileNotFoundError("secrets.json file not found!")


    def compile_regex(self):
        self.regexQuery = re.compile(r'([\$]+[\060-\071.]*)')

    def connect_to_gmail(self):
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('gmail', 'v1', credentials=self.creds)

    def get_past_month_date(self, year, month):
        if(month == 1):
            return datetime.date(year-1, 12, 1)
        else:
            return datetime.date(year, month, 1)

    def get_mail_messages(self,labels):
        today = datetime.date.today()
        searchDate= self.get_past_month_date(today.year, today.month)
        dateQuery = 'after:{searchDate}'.format(
            searchDate=str(searchDate).replace('-', '/'))
        utilities = self.service.users().labels().get(
            userId='me', id=self.label_id).execute()
        messages = self.service.users().messages().list(
            userId='me', labelIds=self.label_id, q=dateQuery).execute()
        return messages

    def get_dollar_amount(self, messages):
        total = 0
        for message in messages['messages']:
            reply = self.service.users().messages().get(
                userId='me', id=message['id'], format='raw').execute()
            msg_str = base64.urlsafe_b64decode(
                reply['raw'].encode("utf-8")).decode("utf-8")
            found = self.regexQuery.search(msg_str)
            amount = float(found.group(0).split('$')[-1])
            total += amount
        return total

    def get_utilities_total(self):
        # Call the Gmail API
        results = self.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        messages = self.get_mail_messages(labels)
        total = self.get_dollar_amount(messages)
        return total

    def send_request(self):
        venmo = Client(
            access_token=self.venmo_token)

        total = self.get_utilities_total()
        amountDue = total/(len(tenants)+1)
        today = datetime.date.today()
        prevMonth = self.get_past_month_date(today.year, today.month)
        requestNote = months[prevMonth.month] + " Utilities"

        for tenant in self.tenants:
            tenantUsername = venmo.user.search_for_users(query=tenant)[0]
            venmo.payment.request_money(
                amount=amountDue, note=requestNote, target_user=tenantUsername)

if __name__ == '__main__':
    calculator = Calculator()
    calculator.send_request()


