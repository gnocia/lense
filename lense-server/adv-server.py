from time import sleep
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, gethostbyname, gethostname
import subprocess

def executer(cmd):
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out,err

PORT = 9999
MAGIC = "lense"

s = socket(AF_INET, SOCK_DGRAM) #create UDP socket
s.bind(('', 0))
s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1) #this is a broadcast socket

while 1:

    #out,err=executer(cmd)
    #if out:
    #   ip = out.splitlines()[1].split(':')[1].split()[0]

    #HOST = str(ip)

    try:
      data = MAGIC+"my_ip"
      s.sendto(data, ('<broadcast>', PORT))
      print "sent service announcement"
      sleep(5)
    except:
      print "network error"
