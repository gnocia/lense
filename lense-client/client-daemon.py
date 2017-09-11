import socket
import threading
import subprocess

gl_data = {}
host = ""
MAGIC="lense"
PORT = 9999
flag = 1

def executer(cmd):
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out, err

def sendUpdate(str):
   #connect to server
   #s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
   global host
   global MAGIC
   global PORT
   global flag
   port =9898

   try:
       s.connect((host,port))

       #send data
       s.send(str)

       #close connection
       s.close ()

       #return value for success
       return 1
   except:
       print "error"

       #listen to server broadcast
       if flag:
          flag = 0
          try:
              print "listening to server broadcast"
              #create UDP socket
              s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
              s.bind(('', PORT))

              while 1:
                print "wait"
                data, addr = s.recvfrom(1024) #wait for a packet
                if data.startswith(MAGIC):
                    print "got service announcement from", addr[0]
	            host=addr[0]
          	    flag = 1
	            break

          except:
              pass

       gl_data = []

       #return value for success
       return 0

def printit():
  threading.Timer(6.0, printit).start()
  global flag
  global gl_data
  data = {}

  #fetch system-account-user
  cmd = ['whoami']
  out1,out2 = executer(cmd)
  if out1:
     data['sys-user']=out1.split()[0]

  #fetch username
  cmd = ['cat','/tmp/.esnel']
  out1,out2 = executer(cmd)
  if out1:
     data['user']=out1.split()[0]

  if True:
        #---------------------------------
        #check for status of containers
        cmd = ['docker', 'ps', '-a']
        out1, out2 = executer(cmd)

        index3={}
        index4=[]
        tag = ""
        if out1:
           temp2=[]
           temp3=[]
           for line in out1.splitlines():
             if 'lesson' in line:
                  var1=line.split()
                  if var1[var1.index('ago')+1] == 'Up':
                     index3[var1[-1]]=[var1[1],'Y']
                  else:
                     index3[var1[-1]]=[var1[1],'S']
                  index4.append(var1[-1])

        #print index3,index4
        index1={}
        temp2=[]
        cmd = ['docker', 'images']
        out1, out2 = executer(cmd)

        for line in out1.splitlines():
           temp3 = []
           flags = []
           temp = line.split()
           if line.startswith('lesson'):

              status=''
              cmd = ["docker","history","--no-trunc",temp[0]]
              temp2 = executer(cmd)
	      image = []

              for step in temp2[0].splitlines():
                  if '"@STEP@' in step:
		     #extract image ID of steps in exercise
                     step = step.split()
                     image = step[0][0:7]#0:12 to get Image ID
                     temp1=[]
                     try:
			 #check if this image is currently up as a container
                         temp1=index3[temp[0].replace('/','-')]
                         if image == temp1[0] :
                           #print temp1
                           flags=temp1[1]
                         else:
                           temp1=['','']
                     except:
                        temp1=['','']

                     temp3.append([image,temp1[1],' '.join(step[step.index('"@STEP@')+1:-2])[:-1]])

              if image:
                 temp[2]=image

              if not flags:
                 try:
                     flags=index3[temp[0].replace('/','-')][1]
                 except:
                     flags='N'

              index1[temp[0]]=[temp[0],temp[1],temp[2],' '.join(temp[-2:]),flags,temp3[::-1]]

  data['lessons']=index1

  #decide to send data or pulse
  if data != gl_data:
     temp = str(data)
     if flag:
        temp = sendUpdate(temp)
        if temp:
           gl_data = data
  else:
     sendUpdate("pulse")

printit()
