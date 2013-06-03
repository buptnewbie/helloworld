from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import * 
from PyQt4.QtCore import *

import socket, select
import threading
import time, struct

FLAG_FILE_TRANS     = 0xf000    # Transmit a block of the file
FLAG_FILE_REQUSET   = 0xff00    # Send this flag to request transmission of a file
FLAG_FILE_ACCEPT    = 0xfff0    # Send this flag to accept transmission
FLAG_FILE_REFUSE    = 0xff0f    # Send this flag to refuse transmission
FLAG_FILE_EOF       = 0xe0f0    # EOF flag for file transmission
FLAG_FILE_REOF      = 0xe0ff    # EOF flag for file received
FLAG_MSG            = 0x0000    # Received a text message
FLAG_FILE_RETRANS   = 0xf0ff    # Retransmission a file, but don't start from the beginning.

class tcpServer(threading.Thread):
    """
    Create a socket server to receive message and file from a socket client
    """
    def __init__(self, mainDlg = None, verbose = True):
        threading.Thread.__init__(self)
        self.verbose = verbose
        self.daemon = True
        self.host = ''
        self.port = 9999
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.saveFilePath = ''
        self.mainDlg = mainDlg

    def debugMsg(self, msg):
        # if self.mainDlg:
        #     self.mainDlg.textEdit.append(msg)
        if 0:
            pass
        else:
            print msg

    def setHost(self, host):
        self.host = host

    def setPort(self, port):
        self.port = port

    def run(self):
        self.debugMsg('this is run function')
        self.server.bind((self.host, self.port))
        self.debugMsg("I'm going to listen")
        self.server.listen(10)
        self.inputs = [self.server]
        while True:
            rs, ws, es = select.select(self.inputs, [], [])
            for r in rs:
                if r is self.server:
                    self.debugMsg('server')
                    c, addr = self.server.accept()
                    c.settimeout(5)
                    self.inputs.append(c)
                else:
                    self.debugMsg('socket')
                    try:
                        payload, address = r.recvfrom(1024)
                    except socket.timeout:
                        self.debugMsg('build a connection, but received no message')
                    (flag,), data = struct.unpack('!H', payload[0:2]), payload[2:]
                    print "flag = %x" % flag
                    if flag == FLAG_FILE_REQUSET:
                        threadrecvFile = threading.Thread(target=self.receiveFile, args=(r, data))
                        threadrecvFile.setDaemon(True)
                        self.inputs.remove(r)
                        threadrecvFile.start()

                    elif flag == FLAG_MSG:
                        if self.verbose:
                            plainText = "Received from device(%s): %s" % ('1', data.decode('utf8'))
                            self.debugMsg(plainText)
                        else:
                            plainText = "Received from device(%s): %s" % (address[0][-1], data.decode('utf8'))
                            self.emit(SIGNAL('textOutPut(QString)'), plainText)
                        r.close()
                        self.inputs.remove(r)
                    else:
                        print "Server end up with an error"

    def receiveFile(self, socketfile, FileName):
        self.saveFilePath = ''
        socketfile.settimeout(600)
        if self.verbose:
            self.saveFilePath = '/home/newbie/test/' + FileName
        else:
            self.emit(SIGNAL('saveFile(QString)'), FileName)
        while True:
            if self.saveFilePath:
                if self.saveFilePath == 'cancel':
                    break
                s = self.saveFilePath
                break
        if self.saveFilePath == 'cancel':
            self.debugMsg('Transmission canceled')
            if not self.verbose:
                self.emit(SIGNAL('finish()'))
            repeat = struct.pack('!H', FLAG_FILE_REFUSE)
            socketfile.send(repeat)
            socketfile.close()
            return
        repeat = struct.pack('!H', FLAG_FILE_ACCEPT)
        socketfile.send(repeat)
        self.debugMsg("send repeat")
        time.sleep(1e-2)#is this necessary
        s = self.saveFilePath
        with open(s, 'wb') as f:
            self.debugMsg("write file")
            data = ''                   #?????????
            while True:
                try:
                    payload, address  = socketfile.recvfrom(10240)
                except socket.timeout:
                    self.debugMsg('file transmission failed')
#add !!!!!
                # # try:
                # #     (flag,), data = struct.unpack('!H', payload[0:2]), payload[2:]   #how to ensure the last packetcan solve?
                # # except Exception, e:
                # #     print "EOF error:", repr(payload)
                # #     break
                # if flag == FLAG_FILE_EOF:
                if not len(payload):
                    # repeat = struct.pack('!H', FLAG_FILE_REOF)##is this necessory?  build another connection to transmit the flag?
                    self.debugMsg("file received successfully")
                    # f.write(payload)
                    # socketfile.send(repeat)
                    socketfile.close()
                    if not self.verbose:
                        self.emit(SIGNAL('finish()'))
                    break
                # elif flag == FLAG_FILE_TRANS:
                    # print 'data'
                # if data != payload:
                f.write(payload)
                    # data = payload
                # else:
                #     self.debugMsg("socket close")
                #     socketfile.close()
                #     break




class tcpClient(threading.Thread):
    def __init__(self, mainDlg = None, verbose = True):
        threading.Thread.__init__(self)
        self.verbose = verbose
        self.address = 'localhost'
        self.port = 9999
        self.readFilePath = ''
        self.mainDlg = mainDlg

    def setAddress(self, address):
        self.address = address

    def setPort(self, port):
        self.port = port

    def debugMsg(self, msg):
        # if self.mainDlg:
            # self.mainDlg.textEdit.append(msg)
        if 0:
            pass
        else:
            print msg

    def sendMessage(self, message):
        data = struct.pack('!H', FLAG_MSG) + message       #data have been transformed  data = str(self.plainTextEdit.toPlainText().toUtf8())
        sockm = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.debugMsg('I have connectted to the server')
        try:
            sockm.connect((self.address, self.port))
            print 'message connect'
            sockm.send(data)
            if  self.verbose:
                # self.textEdit.append("Send to device(%s): %s" % (address[-1], data[2:].decode('utf8')))
                print "sent"
            sockm.close()
        except socket.error:
            if self.verbose:
                # self.textEdit.append("message transmission failed, please try again")
                self.debugMsg("message transmission failed, please try again")
            sockm.close()

    def sendFile(self, FilePath):   #FilePath QSting?
        sockf = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockf.settimeout(600)
        try:
            sockf.connect((self.address, self.port))
        except socket.error:
            self.debugMsg("file transmission failed, please try again")
        # s = str(FilePath.toUtf8())   #not have been transformed!
        s = FilePath
        if s:
            with open(s, 'rb') as f: ##what this means?
                filename = s.split('/')[-1]
                data = struct.pack('!H', FLAG_FILE_REQUSET) + filename
                sockf.send(data)
        try:
            payload, address = sockf.recvfrom(1024)
        except socket.timeout:
            self.debugMsg('file transmission failed, please send again')
            sockf.close()
# what server should do?
        (flag,), data = struct.unpack('!H', payload[0:2]), payload[2:]
        print "0x%X" % flag
        if flag == FLAG_FILE_ACCEPT:
            BUFFSIZE = 1024
            if FilePath:
                s = FilePath
            else:
                # self.textEdit.append("File path error") # is this ok?
                return
            f = open(s, 'rb')
            self.debugMsg("accept open(s, 'rb')")
            while True:
                data = f.read(BUFFSIZE)
                if len(data) != BUFFSIZE:
                    # time.sleep(500e-3) #An important snoop
                    # data = struct.pack('!H', FLAG_FILE_EOF) + data
                    sockf.send(data)
                    if self.verbose:
                        print 'Send %s successfully' % s.split('/')[-1]
                    else:
                        self.textEdit.append("Send %s successfully!" % s.split('/')[-1])  #is this ok?
                    sockf.close()
                    break
                # data = struct.pack('!H', FLAG_FILE_TRANS) + data
                sockf.send(data)
                # time.sleep(1e-3)
        elif flag == FLAG_FILE_REFUSE:
            if self.verbose:
                # self.textEdit.append('Transmission has been canceled')  # is this ok?
                print "Transmission has been canceled"
            sockf.cloes()
            FilePath = ''
        else:
            print 'end up with an error'