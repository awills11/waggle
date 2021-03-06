#!/usr/bin/env python2.7
from cloud_pika_connections import Consume, Connect, Send, CreateQueue
from waggle.common.messaging_d import *
import time
con = Connect()
CreateQueue(con, "command")
CreateQueue(con, "data")
CreateQueue(con, "malformed")
CreateQueue(con, "registration")
CreateQueue(con, "reply")

def Callback(ch, method, properties, body):
    global command_con
    global data_con
    global malformed_con
    global reply_con
    global registration_con
    try:
        a = Message.decode(body)
    except:
        print "Bad Message!"
        Send(con, "malformed", body)
        ch.basic_ack(delivery_tag = method.delivery_tag)
        return
    msg_type = int(a.header.message_type)
    if msg_type == ReplyPayload.PAYLOAD_ID:
        Send(con, "reply", body)
    elif msg_type == CommandPayload.PAYLOAD_ID:
        Send(con, "command", body)
    elif msg_type == RegistrationPayload.PAYLOAD_ID:
        Send(con, "registration", body)
    elif msg_type == DataPayload.PAYLOAD_ID:
        Send(con, "data", body)
    ch.basic_ack(delivery_tag = method.delivery_tag)

def run():
    Consume(Callback, 'cloud_entrance')

if __name__ == "__main__":
    run()
