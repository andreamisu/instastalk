import json
import codecs
import datetime
from os import supports_follow_symlinks
import os.path
import logging
import argparse
import pickle
from datetime import date


try:
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError,
        __version__ as client_version)
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError,
        __version__ as client_version)


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


def onlogin_callback(api, new_settings_file):
    cache_settings = api.settings
    with open(new_settings_file, 'w') as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        print('SAVED: {0!s}'.format(new_settings_file))


if __name__ == '__main__':

    print(r""" ▄█  ███▄▄▄▄      ▄████████     ███        ▄████████ 
███  ███▀▀▀██▄   ███    ███ ▀█████████▄   ███    ███ 
███▌ ███   ███   ███    █▀     ▀███▀▀██   ███    ███ 
███▌ ███   ███   ███            ███   ▀   ███    ███ 
███▌ ███   ███ ▀███████████     ███     ▀███████████ 
███  ███   ███          ███     ███       ███    ███ 
███  ███   ███    ▄█    ███     ███       ███    ███ 
█▀    ▀█   █▀   ▄████████▀     ▄████▀     ███    █▀  
                                                     """)

    print(r"""   ▄████████     ███        ▄████████  ▄█          ▄█   ▄█▄ 
  ███    ███ ▀█████████▄   ███    ███ ███         ███ ▄███▀ 
  ███    █▀     ▀███▀▀██   ███    ███ ███         ███▐██▀   
  ███            ███   ▀   ███    ███ ███        ▄█████▀    
▀███████████     ███     ▀███████████ ███       ▀▀█████▄    
         ███     ███       ███    ███ ███         ███▐██▄   
   ▄█    ███     ███       ███    ███ ███▌    ▄   ███ ▀███▄ 
 ▄████████▀     ▄████▀     ███    █▀  █████▄▄██   ███   ▀█▀ 
                                      ▀           ▀         """)

     logging.basicConfig()
     logger = logging.getLogger('instagram_private_api')
     logger.setLevel(logging.WARNING)

     # Example command:
     # python examples/savesettings_logincallback.py -u "yyy" -p "zzz" -settings "test_credentials.json"
     parser = argparse.ArgumentParser(description='login callback and save settings demo')
     parser.add_argument('-settings', '--settings', dest='settings_file_path', type=str, required=True)
     parser.add_argument('-u', '--username', dest='username', type=str, required=True)
     parser.add_argument('-p', '--password', dest='password', type=str, required=True)
     parser.add_argument('-s', '--stalk', dest='targer_user', type=str)
     parser.add_argument('-debug', '--debug', action='store_true')

     args = parser.parse_args()
     if args.debug:
         logger.setLevel(logging.DEBUG)

     print('Client version: {0!s}'.format(client_version))

     device_id = None
     try:

         settings_file = args.settings_file_path
         if not os.path.isfile(settings_file):
             # settings file does not exist
             print('Unable to find file: {0!s}'.format(settings_file))

             # login new
             api = Client(
                 args.username, args.password,
                 on_login=lambda x: onlogin_callback(x, args.settings_file_path))
         else:
             with open(settings_file) as file_data:
                 cached_settings = json.load(file_data, object_hook=from_json)
             print('Reusing settings: {0!s}'.format(settings_file))

             device_id = cached_settings.get('device_id')
             # reuse auth settings
             api = Client(
                 args.username, args.password,
                 settings=cached_settings)

     except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
         print('ClientCookieExpiredError/ClientLoginRequiredError: {0!s}'.format(e))

         # Login expired
         # Do relogin but use default ua, keys and such
         api = Client(
             args.username, args.password,
             device_id=device_id,
             on_login=lambda x: onlogin_callback(x, args.settings_file_path))

     except ClientLoginError as e:
         print('ClientLoginError {0!s}'.format(e))
         exit(9)
     except ClientError as e:
         print('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response))
         exit(9)
     except Exception as e:
         print('Unexpected Exception: {0!s}'.format(e))
         exit(99)

     # Show when login expires
     cookie_expiry = api.cookie_jar.auth_expires
     print('Cookie Expiry: {0!s}'.format(datetime.datetime.fromtimestamp(cookie_expiry).strftime('%Y-%m-%dT%H:%M:%SZ')))

     #try to load previous saved followers
     previousFollowers = []
     previousFollowing = []
     unfollowers = []
     followed = []
     followers = []
     follwers = []
     previously_checked = True
     try:
         with open(args.targer_user + "_following.txt", 'rb') as f:
             previousFollowing = pickle.load(f)
             print("User previously stalked! \n",)
     except Exception as e:
         logger.warning('First time stalking? no biggie x.\n')
         previously_checked = False

     try:
         with open(args.targer_user + "_followers.txt", 'rb') as f:
             previousFollowers = pickle.load(f)
     except Exception as e:
         previously_checked = False

     # Call the api
     uuid = api.generate_uuid()
     follower_count = 0
     followed_count = 0
     maxid = ""
     stalked_user_id = -1
     try:
         while 1:
             follwers = api.user_followers(api.authenticated_user_id, uuid, max_id=maxid)
             for x in follwers.get("users"):
                 username = x.get("username")
                 if(args.targer_user == username):
                     print("--------------------------------")
                     print("User found!!!")
                     stalked_user_id = x.get("pk")
                     break
             if(stalked_user_id != -1):
                 break
             maxid = follwers.get("next_max_id")
     except Exception as e:
         print("User didn't found :-((((( you should follow your stalking target to actually stalk sorry tho x goodbye")
         exit(1)

     print("checking its following")
     print(str(stalked_user_id))
     maxid = ""
     followed_max = api.user_detail_info(stalked_user_id).get("user_detail").get("user").get("following_count")
     try:
         while 1:
             print("--------------------------------")
             print("Following counted: " + str(followed_count))
             if(followed_count == followed_max):
                     break
             following = api.user_following(stalked_user_id, uuid, max_id=maxid)
             for x in following.get("users"):
                 if(followed_count == followed_max):
                     break
                 username = x.get("username")
                 print(str(username))
                 followed_count += 1
                 followed.append(username)
             maxid = following.get("next_max_id")
     except Exception as e:
         pass
     print("--------------------------------")
     print("checking its followers")
     maxid = ""
     followers_max = api.user_detail_info(stalked_user_id).get("user_detail").get("user").get("follower_count")
     try:
         while 1:
             print("--------------------------------")
             print("Follower counted: " + str(follower_count))
             if(follower_count == followers_max):
                     break
             follwers = api.user_followers(api.authenticated_user_id, uuid, max_id=maxid)
             for x in follwers.get("users"):
                 if(follower_count == followers_max):
                     break
                 username = x.get("username")
                 print(str(username))
                 follower_count += 1
                 followers.append(username)
             maxid = follwers.get("next_max_id")
     except Exception as e:
         pass


     user_unfollowed =[]
     user_followed = []
     user_unfollowing = []
     user_following = []
     #Check followers only if previous records are present
     if(previously_checked):
         print("\nChecking changes")

         for user in previousFollowers:
             if user not in followers:
                 user_unfollowed.append(user)
         print("--------------------------------")
         print("USER THAT UNFOLLOWED TARGET\n")
         if(len(user_unfollowed)>0):
             for x in user_unfollowed:
                 print(str(x))
         else:
             print("no one has been unfollowed. \n")


         for user in followers:
             if user not in previousFollowers:
                 user_followed.append(user)

         print("--------------------------------")       
         print("NEW USER THAT TARGET FOLLOWS\n")
         if(len(user_followed)>0):
             for x in user_followed:
                 print(str(x))
         else:
             print("no one has been followed. \n")


         for user in previousFollowing:
             if user not in followed:
                 user_unfollowing.append(user)

         print("--------------------------------")       
         print("USER THAT TARGET DOESN'T FOLLOW ANYMORE \n")
         if(len(user_unfollowing)>0):
             for x in user_unfollowing:
                 print(str(x))
         else:
             print("no one has been removed. \n")


         for user in followed:
             if user not in previousFollowing:
                 user_following.append(user)

         print("--------------------------------")       
         print("NEW USER THAT TARGET FOLLOW\n")
         if(len(user_following)>0):
             for x in user_following:
                 print(str(x))
         else:
             print("no one has been followed. \n")

         #Dump to file (for saving followers status)

         log_execution = open(args.targer_user + "_logs.txt", "a")

         log_execution.write("Checked: " + str(date.today().strftime("%B %d, %Y")) + "\n")
         log_execution.write("USER THAT UNFOLLOWED TARGET: \n")  
         for x in user_unfollowed:
             log_execution.write(str(x))
         log_execution.write("--------------------------------\n")

         log_execution.write("NEW USER THAT TARGET FOLLOWS\n")
         for x in user_followed:
             log_execution.write(str(x))
         log_execution.write("--------------------------------\n")

         log_execution.write("USER THAT TARGET DOESN'T FOLLOW ANYMORE \n")
         for x in user_unfollowing:
             log_execution.write(str(x))
         log_execution.write("--------------------------------\n")

         log_execution.write("NEW USER THAT TARGET FOLLOW\n")
         for x in user_following:
             log_execution.write(str(x))
         log_execution.write("--------------------------------\n")
         log_execution.close()

     print("Saving results...\n")
     with open(args.targer_user + "_following.txt",'wb') as f:
         pickle.dump(followed, f) 
     with open(args.targer_user + "_followers.txt",'wb') as f:
         pickle.dump(followers, f) 
     print("All done! bye x")