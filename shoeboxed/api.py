import string
import webbrowser
import random
import requests
import json
import hashlib, hmac, base64
import os.path
import sys
import datetime

from requests.auth import HTTPBasicAuth


CLIENT_ID = ''
CLIENT_SECRET = ''
OAUTH_SCOPE = 'https://id.shoeboxed.com/oauth/authorize/'
REDIRECT_URI = ''
AUTH_EXPIRE = 1800


def getSignature( token, secret ):
   "Returns HMAC of token using secret."
   signature = base64.b64encode(hmac.new(secret, token, digestmod=hashlib.sha256).digest())
   return signature

def getUser( access_token ):
   "Returns HMAC of token using secret."
   r = requests.get('https://api.shoeboxed.com/v2/user', headers={"Authorization":"Bearer " + access_token})
   j = json.loads(r.text)
   return j

def getCategories( access_token, accountID ):
   "Returns Categories."
   r = requests.get('https://api.shoeboxed.com/v2/accounts/' + accountID + '/categories', headers={"Authorization":"Bearer " + access_token})
   j = json.loads(r.text)
   return j

def getDocuments( access_token, accountID ):
   "Returns Documents."
   payload = {'limit': 3}
   r = requests.get('https://api.shoeboxed.com/v2/accounts/' + accountID + '/documents', params=payload, headers={"Authorization":"Bearer " + access_token})
   j = json.loads(r.text)
   return j

def getToken():
   "Returns Auth Token."
   dir_path = os.path.dirname(os.path.realpath(__file__))
   file_path = dir_path + "/authtoken.txt"
   if os.path.isfile(file_path):
      file_time = os.stat(file_path).st_mtime
      current_time = datetime.datetime.now().strftime('%s')
      file_age = float(current_time) - float(file_time)
      if file_age > AUTH_EXPIRE:
         os.remove(file_path)
      else:
         f = open(file_path, "r")
         access_token_j = json.loads(f.read())
         return access_token_j
   access_token_uri = "https://id.shoeboxed.com/oauth/token"
   state = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
   auth_uri = "https://id.shoeboxed.com/oauth/authorize?client_id=" + CLIENT_ID + "&response_type=code&scope=all&redirect_uri=" + REDIRECT_URI +"&state=" + state
   webbrowser.open(auth_uri)
   auth_code = raw_input('Enter the authentication code: ')
   payload = {'code': auth_code, 'grant_type': 'authorization_code', 'redirect_uri': REDIRECT_URI}
   access_token_r = requests.post(access_token_uri, data=payload, auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET))
   if int(access_token_r.status_code) == 200:
       file = open("authtoken.txt","w")
       file.write(access_token_r.text)
       file.close()
       access_token_j = json.loads(access_token_r.text)
       return access_token_j
   else:
      print "ERROR"
      print access_token_r.status_code
      print access_token_r.text
      sys.exit()

access_token_j = getToken()
j = getUser(access_token_j['access_token'])
accountID = j["accounts"][0]['id']
categories_j = getCategories(access_token_j['access_token'], accountID)
documents_j = getDocuments(access_token_j['access_token'], accountID)
print json.dumps(documents_j, indent=4, sort_keys=True)

