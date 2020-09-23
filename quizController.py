#! /usr/bin/python3
##########################################
# Web Streams quiz controller            #
# By: Chris Noble                        #
# Date: 19-Aug-2020                      #
# Revision Invormation                   #
# 05-Sep-2020 first working version      #
##########################################

from time import gmtime, strftime
import signal
import logging
import sys
import errno
import time
import json
import bottle
from bottle import run, template, request, post
from gevent.pywsgi import WSGIServer
#from gevent import monkey
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
from bottle import request, Bottle, abort

###################
# Control-C handler (or kill -SIGINT)
# Terminate program
def controlC_handler(sig, frame):
    logging.info('SIGINT received, terminating...')
    server.close()
    sys.exit(0)

signal.signal(signal.SIGINT, controlC_handler)


# Main program loop
###################
def main():
    global userlist
    global UserIP
    global server
    global TimeDiff
    global playLocked
    global statusConnectionActive

    playLocked = True
    statusConnectionActive = False

    #monkey.patch_all() # for gevent operations

    logging.basicConfig(filename='quizController.log',level=logging.INFO)
    #logging.basicConfig(level=logging.INFO)

    # A list of connected users
    userlist = {}

    # Configure Web Streams server interface
    ########################################
    myServer = Bottle()
    SockNumber = 9107 # Socket to listen on

    @myServer.route('/quizController')
    def handle_websocket():

        global playLocked

        UserIP = request.remote_addr

        wsock = request.environ.get('wsgi.websocket')
        if not wsock:
            abort(400, 'Expected WebSocket protocol')
        else:
            print("Conection active")

        while True:
            try:
                #logging.info("Next - get message")
                message = wsock.receive()
                if message is not None:
                  #logging.info("Got message: ", message)
                  msg = json.loads(message)
                  if msg["msgtype"] == "connect":
                      TimeStamp_A = time.monotonic_ns() # nanoseconds
                      wsock.send("ping")
                      logging.info("ping sent")
                  elif msg["msgtype"] == "pong":
                      logging.info("pong received")
                      TimeStamp_B = time.monotonic_ns() # nanoseconds
                      TimeDiff = (TimeStamp_B - TimeStamp_A)/2 # time per trip
                  elif msg["msgtype"] == "login":
                      wsock.send("Logout")
                    
                      UserName = msg["username"]
                      Password = msg["password"]
                      print("IP: ", UserIP, " logged in")
                      UserTimeStamp = msg["usertime"]
                      ServerTimeStamp = time.monotonic_ns()

                      userlist[UserName] = {"UserIP": UserIP, \
                           "UserTime": 9*10**16, \
                           "ServerTime": ServerTimeStamp, \
                           "UserPassword": Password, \
                           "TimeDiff": TimeDiff}

                      print("UserIP = ", \
                           userlist[UserName]["UserIP"])
                      logging.info("UserTime = %s", \
                           str(userlist[UserName]["UserTime"]))
                      logging.info("ServerTime = %s", \
                           str(userlist[UserName]["ServerTime"]))
                      logging.info("Password = %s", \
                           userlist[UserName]["UserPassword"])
                      logging.info("TimeDiff = %s", \
                           str(userlist[UserName]["TimeDiff"]))
                  elif msg["msgtype"] == "logout":
                    userlist.pop(msg["username"])
                    print("User: ", msg["username"], " logged out")
                    wsock.send("Login")
                  elif msg["msgtype"] == "play" and playLocked == False:
                      playLocked = True
                      UserName = msg["username"]
                      Password = msg["password"]
                      UserTimeStamp = msg["usertime"]
                      #userlist[UserName].UserTime = UserTimeStamp
                      ServerTimeStamp = time.monotonic_ns()

                      print("UserIP = ", \
                           userlist[UserName]["UserIP"])
                      logging.info("UserTime = %s", \
                           str(userlist[UserName]["UserTime"]))
                      logging.info("Password = %s", \
                           userlist[UserName]["UserPassword"])
                      logging.info("Current usertime = %s", \
                           str(msg["usertime"]))
                      logging.info("TimeDiff = %s", \
                           str(userlist[UserName]["TimeDiff"]))
                      logging.info("Current ServerTime = %s", \
                           str(ServerTimeStamp))
                      AdjustedTime = ServerTimeStamp - TimeDiff #\
                           #userlist[UserName]["TimeDiff"]
                      print("Current Adjusted time: ", AdjustedTime)
                      userlist[UserName]['UserTime'] = AdjustedTime 
                      wsock.send(str(round(AdjustedTime)))
                  elif msg["msgtype"] == "status":
                      if playLocked == True:
                        wsock.send("locked")
                      else:
                        wsock.send("unlocked")

            except WebSocketError:
                break

    @myServer.route('/quizController/status')
    def handle_status():
        print("Status connection")

        global playLocked
        global statusConnectionActive

        UserIP = request.remote_addr

        wsock = request.environ.get('wsgi.websocket')
        if not wsock:
            abort(400, 'Expected WebSocket protocol')
        elif statusConnectionActive == True:
            print("STATUS connection refused - already active")
            abort(409, 'Status connection already active')
        else:
            print("Status conection active")
            statusConnectionActive = True
            wsock.send(json.dumps(userlist))
            #playLocked = True

        while True:
          try:
            message = wsock.receive()
            if message is not None:
              msg = json.loads(message)
              if msg["msgtype"] == "reset":
                for U in userlist:
                  userlist[U]['UserTime'] = 9*10**16 
                wsock.send(json.dumps(userlist))
                playLocked = False
              elif msg["msgtype"] == "status":
                wsock.send(json.dumps(userlist))
                if playLocked == True:
                  wsock.send("Locked")
                else:
                  wsock.send("UnLocked")
                
          except WebSocketError:
            break




    server = WSGIServer(("0.0.0.0", SockNumber), myServer, \
                    handler_class=WebSocketHandler)

    print("Starting server on ", SockNumber, "...")
    server.serve_forever()


if __name__ == "__main__":
       main()
