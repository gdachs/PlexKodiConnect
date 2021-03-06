# -*- coding: utf-8 -*-

###############################################################################

# import json
import requests
import xml.etree.ElementTree as etree
# import logging

# import xbmc
import xbmcgui

import utils
import clientinfo

import PlexAPI

###############################################################################

# Disable requests logging
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
# logging.getLogger('requests').setLevel(logging.WARNING)

###############################################################################


@utils.logging
class DownloadUtils():

    # Borg - multiple instances, shared state
    _shared_state = {}
    clientInfo = clientinfo.ClientInfo()

    # Requests session
    s = None
    timeout = 30

    def __init__(self):

        self.__dict__ = self._shared_state

    def setUsername(self, username):
        # Reserved for userclient only
        self.username = username
        self.logMsg("Set username: %s" % username, 2)

    def setUserId(self, userId):
        # Reserved for userclient only
        self.userId = userId
        self.logMsg("Set userId: %s" % userId, 2)

    def setServer(self, server):
        # Reserved for userclient only
        self.server = server
        self.logMsg("Set server: %s" % server, 2)

    def setToken(self, token):
        # Reserved for userclient only
        self.token = token
        self.logMsg("Set token: xxxxxxx", 2)

    def setSSL(self, ssl, sslclient):
        # Reserved for userclient only
        self.sslverify = ssl
        self.sslclient = sslclient
        self.logMsg("Verify SSL host certificate: %s" % ssl, 2)
        self.logMsg("SSL client side certificate: %s" % sslclient, 2)


    def postCapabilities(self, deviceId):

        # Post settings to session
        url = "{server}/emby/Sessions/Capabilities/Full?format=json"
        data = {
            
            'PlayableMediaTypes': "Audio,Video",
            'SupportsMediaControl': True,
            'SupportedCommands': (
                
                "MoveUp,MoveDown,MoveLeft,MoveRight,Select,"
                "Back,ToggleContextMenu,ToggleFullscreen,ToggleOsdMenu,"
                "GoHome,PageUp,NextLetter,GoToSearch,"
                "GoToSettings,PageDown,PreviousLetter,TakeScreenshot,"
                "VolumeUp,VolumeDown,ToggleMute,SendString,DisplayMessage,"
                "SetAudioStreamIndex,SetSubtitleStreamIndex,"

                "Mute,Unmute,SetVolume,"
                "Play,Playstate,PlayNext"
            )
        }

        self.logMsg("Capabilities URL: %s" % url, 2)
        self.logMsg("Postdata: %s" % data, 2)

        self.downloadUrl(url, postBody=data, type="POST")
        self.logMsg("Posted capabilities to %s" % self.server, 2)

        # Attempt at getting sessionId
        url = "{server}/emby/Sessions?DeviceId=%s&format=json" % deviceId
        result = self.downloadUrl(url)
        try:
            sessionId = result[0]['Id']
        
        except (KeyError, TypeError):
            self.logMsg("Failed to retrieve sessionId.", 1)
        
        else:
            self.logMsg("Session: %s" % result, 2)
            self.logMsg("SessionId: %s" % sessionId, 1)
            utils.window('emby_sessionId', value=sessionId)
            
            # Post any permanent additional users
            # additionalUsers = utils.settings('additionalUsers')
            # if additionalUsers:
                
            #     additionalUsers = additionalUsers.split(',')
            #     self.logMsg(
            #         "List of permanent users added to the session: %s"
            #         % additionalUsers, 1)

            #     # Get the user list from server to get the userId
            #     url = "{server}/emby/Users?format=json"
            #     result = self.downloadUrl(url)

            #     for additional in additionalUsers:
            #         addUser = additional.decode('utf-8').lower()

            #         # Compare to server users to list of permanent additional users
            #         for user in result:
            #             username = user['Name'].lower()

            #             if username in addUser:
            #                 userId = user['Id']
            #                 url = (
            #                         "{server}/emby/Sessions/%s/Users/%s?format=json"
            #                         % (sessionId, userId)
            #                 )
            #                 self.downloadUrl(url, postBody={}, type="POST")


    def startSession(self):

        log = self.logMsg

        self.deviceId = self.clientInfo.getDeviceId()

        # User is identified from this point
        # Attach authenticated header to the session
        verify = False
        header = self.getHeader()

        # If user enabled host certificate verification
        try:
            verify = self.sslverify
            if self.sslclient is not None:
                verify = self.sslclient
        except:
            log("Could not load SSL settings.", 1)
        
        # Start session
        self.s = requests.Session()
        self.s.headers = header
        self.s.verify = verify
        # Retry connections to the server
        self.s.mount("http://", requests.adapters.HTTPAdapter(max_retries=1))
        self.s.mount("https://", requests.adapters.HTTPAdapter(max_retries=1))

        log("Requests session started on: %s" % self.server, 1)

    def stopSession(self):
        try:
            self.s.close()
        except:
            self.logMsg("Requests session could not be terminated.", 1)

    def getHeader(self, authenticate=True, options={}):
        plx = PlexAPI.PlexAPI()
        if authenticate:
            options['X-Plex-Token'] = self.token
            header = plx.getXArgsDeviceInfo(options=options)
        else:
            header = plx.getXArgsDeviceInfo(options=options)
        return header

    def downloadUrl(self, url, postBody=None, type="GET", parameters=None, authenticate=True, headerOptions={}):
        
        # self.logMsg("=== ENTER downloadUrl ===", 2)

        timeout = self.timeout
        default_link = ""

        try:
            # If user is authenticated
            if (authenticate):
                # Get requests session
                try: 
                    s = self.s
                    # Replace for the real values
                    url = url.replace("{server}", self.server)
                    url = url.replace("{UserId}", self.userId)
                    header = self.getHeader(options=headerOptions)
                    # Prepare request
                    if type == "GET":
                        r = s.get(url, json=postBody, params=parameters, timeout=timeout, headers=header)
                    elif type == "POST":
                        r = s.post(url, json=postBody, timeout=timeout, headers=header)
                    elif type == "DELETE":
                        r = s.delete(url, json=postBody, timeout=timeout, headers=header)
                    elif type == "OPTIONS":
                        r = s.options(url, json=postBody, timeout=timeout, headers=header)
                    # For Plex Companion
                    elif type == "POSTXML":
                        r = s.post(url, postBody, timeout=timeout, headers=header)
                    elif type == "PUT":
                        r = s.put(url, timeout=timeout, headers=header)
                
                except AttributeError:
                    # request session does not exists
                    self.logMsg("Request session does not exist: start one", 1)
                    # Get user information
                    self.userId = utils.window('currUserId')
                    self.server = utils.window('pms_server')
                    self.token = utils.window('pms_token')
                    header = self.getHeader(options=headerOptions)
                    verifyssl = False
                    cert = None

                    # IF user enables ssl verification
                    if utils.settings('sslverify') == "true":
                        verifyssl = True
                    if utils.settings('sslcert') != "None":
                        verifyssl = utils.settings('sslcert')

                    # Replace for the real values
                    url = url.replace("{server}", self.server)
                    url = url.replace("{UserId}", self.userId)

                    # Prepare request
                    if type == "GET":
                        r = requests.get(url,
                                        json=postBody,
                                        params=parameters,
                                        headers=header,
                                        timeout=timeout,
                                        verify=verifyssl)

                    elif type == "POST":
                        r = requests.post(url,
                                        json=postBody,
                                        headers=header,
                                        timeout=timeout,
                                        verify=verifyssl)

                    elif type == "DELETE":
                        r = requests.delete(url,
                                        json=postBody,
                                        headers=header,
                                        timeout=timeout,
                                        verify=verifyssl)

                    elif type == "OPTIONS":
                        r = requests.options(url,
                                        json=postBody,
                                        headers=header,
                                        timeout=timeout,
                                        cert=cert,
                                        verify=verifyssl)

                    elif type == "PUT":
                        r = requests.put(url,
                                        json=postBody,
                                        headers=header,
                                        timeout=timeout,
                                        cert=cert,
                                        verify=verifyssl)
            # If user is not authenticated
            elif not authenticate:

                header = self.getHeader(authenticate=False, options=headerOptions)

                # If user enables ssl verification
                try:
                    verifyssl = self.sslverify
                    if self.sslclient is not None:
                        verifyssl = self.sslclient
                except AttributeError:
                    if utils.settings('sslverify') == "true":
                        verifyssl = True
                    else:
                        verifyssl = False
                self.logMsg("Set SSL verification to: %s" % verifyssl, 2)
                
                # Prepare request
                if type == "GET":
                    r = requests.get(url,
                                    json=postBody,
                                    params=parameters,
                                    headers=header,
                                    timeout=timeout,
                                    verify=verifyssl)

                elif type == "POST":
                    r = requests.post(url,
                                    json=postBody,
                                    headers=header,
                                    timeout=timeout,
                                    verify=verifyssl)
        
                elif type == "PUT":
                    r = requests.put(url,
                                    json=postBody,
                                    headers=header,
                                    timeout=timeout,
                                    verify=verifyssl)
            ##### THE RESPONSE #####
            # self.logMsg(r.url, 2)
            if r.status_code == 204:
                # No body in the response
                # self.logMsg("====== 204 Success ======", 2)
                pass

            elif r.status_code == requests.codes.ok:
               
                try: 
                    # Allow for xml responses
                    r = etree.fromstring(r.content)
                    # self.logMsg("====== 200 Success ======", 2)
                    # self.logMsg("Received an XML response for: %s" % url, 2)

                    return r

                except:
                    try:
                        # UNICODE - JSON object
                        r = r.json()
                        # self.logMsg("====== 200 Success ======", 2)
                        # self.logMsg("Response: %s" % r, 2)
                        return r
                    except:
                        try:
                            if r.text == '' and r.status_code == 200:
                                # self.logMsg("====== 200 Success ======", 2)
                                # self.logMsg("Answer from PMS does not contain a body", 2)
                                pass
                            # self.logMsg("Unable to convert the response for: %s" % url, 2)
                            # self.logMsg("Content-type was: %s" % r.headers['content-type'], 2)
                        except:
                            self.logMsg("Unable to convert the response for: %s" % url, 2)
                            self.logMsg("Content-type was: %s" % r.headers['content-type'], 2)
            else:
                r.raise_for_status()
        
        ##### EXCEPTIONS #####

        except requests.exceptions.ConnectionError as e:
            # Make the addon aware of status
            if utils.window('emby_online') != "false":
                self.logMsg("Server unreachable at: %s" % url, -1)
                self.logMsg(e, 2)
                utils.window('emby_online', value="false")

        except requests.exceptions.ConnectTimeout as e:
            self.logMsg("Server timeout at: %s" % url, 0)
            self.logMsg(e, 1)

        except requests.exceptions.HTTPError as e:

            if r.status_code == 401:
                # Unauthorized
                status = utils.window('emby_serverStatus')

                if 'X-Application-Error-Code' in r.headers:
                    # Emby server errors
                    if r.headers['X-Application-Error-Code'] == "ParentalControl":
                        # Parental control - access restricted
                        self.logMsg('Setting emby_serverStatus to restricted')
                        utils.window('emby_serverStatus', value="restricted")
                        xbmcgui.Dialog().notification(
                                                heading=self.addonName,
                                                message="Access restricted.",
                                                icon=xbmcgui.NOTIFICATION_ERROR,
                                                time=5000)
                        return False
                    
                    elif r.headers['X-Application-Error-Code'] == "UnauthorizedAccessException":
                        # User tried to do something his emby account doesn't allow
                        pass

                elif status not in ("401", "Auth"):
                    # Tell userclient token has been revoked.
                    self.logMsg('Error 401 contacting %s' % url, 0)
                    self.logMsg('Setting emby_serverStatus to 401', 0)
                    utils.window('emby_serverStatus', value="401")
                    self.logMsg("HTTP Error: %s" % e, 0)
                    xbmcgui.Dialog().notification(
                                            heading=self.addonName,
                                            message="Error connecting: Unauthorized.",
                                            icon=xbmcgui.NOTIFICATION_ERROR)
                    return 401

            elif r.status_code in (301, 302):
                # Redirects
                pass
            elif r.status_code == 400:
                # Bad requests
                pass

        except requests.exceptions.SSLError as e:
            self.logMsg("Invalid SSL certificate for: %s" % url, 0)
            self.logMsg(e, 1)

        except requests.exceptions.RequestException as e:
            self.logMsg("Unknown error connecting to: %s" % url, 0)
            self.logMsg(e, 1)

        return default_link