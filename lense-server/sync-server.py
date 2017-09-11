from socket import *
import ast
import os
import thread
import subprocess
import MySQLdb

BUFF = 1024
HOST = '192.168.43.'# must be input parameter @TODO
PORT = 9898 # must be input parameter @TODO

#variables for accessign database
dbuser = ""
dbpasswd = ""

loc = os.getcwd()+"/"

#read config.txt file
with open(loc+"static/configs/config.txt") as f:
     details = f.read()
f.close()

for line in details.splitlines():
    line = line.split()
    if line == []:
        pass
    elif line[0] == "dbuser":
       dbuser = line[2]
    elif line[0] == "dbpasswd":
       dbpasswd = line[2]

def executer(cmd):
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out,err

def getDB(query,flag):
    global dbuser, dbpasswd
    try:
        db = MySQLdb.connect(host="localhost",user=dbuser,passwd=dbpasswd,db="lense")
        cur = db.cursor()
        if flag=="true":
          val = []
          for cmd in query.split(';'):
              print cmd
              cur.execute(cmd)
              print cur.fetchall()
              db.commit()
        else:
          cur.execute(query)
          val = cur.fetchall()

        #cur.execute(query)
        cur.close()
        db.close()

        return val
    except:
        pass


def handler(clientsock,addr):
    recv = ""
    while 1:
        temp = clientsock.recv(BUFF)
        if not temp: break

	recv += temp

    print repr(addr) + ' recv:' + repr(recv)

    clientsock.close()
    print addr, "- closed connection" 

    if recv != "pulse":
       recv = ast.literal_eval(recv)
       addr = str(addr[0])
       try:
           user = recv['user']
       except:
           user = recv['sys-user']

       row_in_CL = []

       for values in recv['lessons'].values():
           step = 1
           for val in values[5]:
            if val[1]!='':
               step+=1
           row_in_CL.append([user,'Y',values[0],str(step),'Y',values[4]])

       print user, row_in_CL

       cmd="select * from status where ip='"+addr+"'"

       rows = getDB(cmd,"false")

       present=[]
       modified=[]
       insert=[]
       delete=[]
       cmd=""
       rows_in_db=[]

       print "rows",rows
       if rows:
          for row in rows:
              row = row[1:]
              print row
 
              print row

              if row not in row_in_CL:
                 flag1=0
                 for line in row_in_CL:
                     if line[2] == row[2]:
                        flag1=1
                        break

                 if flag1:
                    values =""
                    if line[0]!=row[0]: values+="id='"+str(line[0])+"',"
                    if line[1]!=row[1]: values+="active='"+str(line[1])+"',"
                    if line[3]!=row[3]: values+="step='"+str(line[3])+"',"
                    if line[4]!=row[4]: values+="img_status='"+str(line[4])+"',"
                    if line[5]!=row[5]: values+="cont_status='"+str(line[5])+"',"

                    if values:
                       cmd+="UPDATE status SET "+values[:-1]+" WHERE ip='"+addr+"' AND img_name='"+str(line[2])+"';"
                 else:
                    cmd+="DELETE FROM status WHERE ip='"+addr+"' AND img_name='"+str(row[2])+"';"

              present.append(row[2])

       values=""
       for line in row_in_CL:
           if line[2] not in present:
              values+="('"+addr+"','"+"','".join(line)+"'),"

       if row_in_CL:
          if values:
             cmd+="INSERT INTO status VALUES "+values[:-1]+";"
       else:
	     #insert this dummy value if no client doesnt have any lesson at all
	     cmd+="INSERT INTO status VALUES ('"+addr+"','"+user+"','Y','default',1,'N','N');"


       print cmd
       if cmd:
          print "result",getDB(cmd,"true")


if __name__=='__main__':

    cmd = ['ifconfig']
    out1,out2 = executer(cmd)

    ips = {}
    flag = 0
    for line in out1.splitlines():
        if 'Link encap' in line:
           flag = line.split()[0]
        elif flag:
           line = line.split(':')
           ips[flag] = line[1].split(' ')[0]
           flag = 0

    if ips:
       while 1:
         print "\nAvailable network adapter to listen: "
         count = 1
         for ip in ips:
             print str(count)+". "+str(ip)+"   ("+str(ips[ip])+")"
             count=count+1
         choice = input("Select (1:"+str(count-1)+") : ")
         if choice >= 1 and choice <= count -1 and type(choice) is int:
            HOST = ips.values()[choice-1]
            break

    ADDR = (HOST, PORT)

    print ADDR
    serversock = socket(AF_INET, SOCK_STREAM)
    serversock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serversock.bind(ADDR)
    serversock.listen(25)
    while 1:
        print 'waiting for connection... listening on port', PORT
        clientsock, addr = serversock.accept()
        print '...connected from:', addr
        thread.start_new_thread(handler, (clientsock, addr))
