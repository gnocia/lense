import os
import re
import ast
import sys
import json
import uuid
import MySQLdb
import functools
import threading
import subprocess
import unicodedata
import flask, flask.views

app = flask.Flask(__name__)
# Don't do this!
app.secret_key = "bacon"

#get app directory
loc = os.getcwd()+"/"

#variables for registry
registry = ""
regmail = ""
reguser = ""
regpas = ""

#variables for databse access
dbhost = ""
dbuser = ""
dbpasswd = ""

#read config.txt file
with open(loc+"static/configs/config.txt") as f:
     details = f.read()
f.close()

for line in details.splitlines():
    line = line.split()
    if line == []:
        pass
    elif line[0] == "registry":
       registry = line[2]
    elif line[0] == "regmail":
       regmail = line[2]
    elif line[0] == "reguser":
       reguser = line[2]
    elif line[0] == "regmail":
       regmail = line[2]
    elif line[0] == "regpas":
       regpas = line[2]
    elif line[0] == "dbhost":
       dbhost = line[2]
    elif line[0] == "dbuser":
       dbuser = line[2]
    elif line[0] == "dbpasswd":
       dbpasswd = line[2]

grps = []
radio1 = ''
radio2 = ''
search1 = ''
search2 = ''
dld = []
dld_lsn = []
output = []

def executer(cmd):
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out, err

def thread_executer(cmd):
  global dld
  print "in thread",cmd
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  out, err = p.communicate()
  temp=out.splitlines()[-2].split()[0]
  if temp=='Digest:':
     dld.remove(cmd[-1])

def downloader(cmd,image,info):
    global dld,loc

    dld.append(image)
    print "Downloading ",image

    out,err = executer(cmd)

    print "finished dld ",image
    if 'Digest' in out:
       try:
	 cmd = ['docker','tag',cmd[2],image]
         out,err = executer(cmd)
         try:
	   print loc+"static/lessons/"+image.replace('/','-')
           with open(loc+"static/lessons/"+image.replace('/','-'),'w') as f:
                f.write(info[0]+"\n"+info[1])
           f.close()
         except:
           print "error writing file -",image
       except:
         print "error renaming ",image
    else:
       print "failed downloading",image

    while image in dld : dld.remove(image)
    print "exiting ",image

def add_lesson(old_lesn,lesn,index,line,info):
    global dld,loc
    global dld_lsn

    flag = 1
    print "enter loop -  add_lesson"
    while flag:
        flag = 0
        for item in index:
            if item in dld:
               flag = 1
    print "exit loop - add_lesson"

    dld_lsn.remove(old_lesn)

    target = loc+'static/configs/lesson.txt'
    try:
        cmd=['grep','^'+lesn+' ',target]
        val,err = executer(cmd)
	
	#add or replace line in the configs/lesson.txt file
        if val:
	   print "Replacing line"
           cmd=['sed','-i','/^'+lesn+' /c '+line,target]
           val = executer(cmd)
        else:
	   print "Adding line"
	   with open(target, 'a') as f:
		f.write(line)
	   f.close()
	
	#add description about lesson in the static/lessons/ folder
	with open(loc+'static/lessons/'+lesn,'w') as f:
	     f.write(info[0]+'\n'+info[1])
	f.close()
    except:
        print "error writing file",lesn

def thread_executer_2(cmd,args):
  global dld
  print "in thread",cmd
  if args[0] == 'play':
     try:
        f = open(cmd[2],'w')
        f.write(args[1])
        f.close()
        f = open(cmd[3],'w')
        f.write(args[2])
        f.close()
     except:
        print "Error creating playbook ",cmd

  p = subprocess.Popen(cmd,shell=False,stdin=None,stdout=None,stderr=None,close_fds=True)
  print "out of process",cmd

def reader(fname):
    index=[]
    try:
      with open(fname) as f:
	 index = f.read().splitlines()
      f.close()
    except:
      pass

    return index

def db_ops(cmds,arg):
    global dbuser, dbpasswd, dbhost
    db = MySQLdb.connect(host=dbhost, 
                     user=dbuser,         
                     passwd=dbpasswd,  
                     db="lense")        
    cur = db.cursor()
    for cmd in cmds:
        cur.execute(cmd)
	result = cur.fetchall()

    #commit if arg = 1
    if arg == 1:
	db.commit()

    #return the results
    return result

    db.close()

def filechecker():
    #check and create lessons.txt if doesnot exist already
    path="static/configs/lesson.txt"
    if not os.path.exists(path):
       print "asdad"
       fh = open(path, "w")
       fh.write(' ')
       fh.close()

class Main(flask.views.MethodView):
    def get(self):
        return flask.render_template('index.html')
    
    def post(self):
	flag = []
        if 'logout' in flask.request.form:
            flask.session.pop('username', None)
            return flask.redirect(flask.url_for('index'))
        required = ['username', 'passwd']
        for r in required:
            if r not in flask.request.form:
                flask.flash("Error: {0} is required.".format(r))
                return flask.redirect(flask.url_for('index'))
        username = flask.request.form['username']
        passwd = flask.request.form['passwd']

        cmd = "SELECT * FROM users WHERE passwd='"+passwd+"' AND uname='"+username+"'"
	flag=db_ops([cmd],0)

	#flag = 1

	#check if all files are available
	filechecker()

        #if username in users and users[username] == passwd:
	if flag:
            flask.session['username'] = username
	    with open('/tmp/.esnel','w') as f:
		 f.write(username)
            f.close()
        else:
            flask.flash("Username doesn't exist or incorrect password")
        return flask.redirect(flask.url_for('home'))

def login_required(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        if 'username' in flask.session:
            return method(*args, **kwargs)
        else:
            flask.flash("A login is required to proceed!")
            return flask.redirect(flask.url_for('index'))
    return wrapper

class Repo(flask.views.MethodView):
    @login_required
    def get(self):
        global dld_lsn
        global dld
        global registry,regmail,reguser,regpas

        #dld=['lesson3']
               
        cmd=['curl','https://'+reguser+':'+regpas+'@'+registry+'/v2/_catalog']
        out1, out2 = executer(cmd)

        temp = {'index':{},'lesns':{},'comps':{},'dld':dld,'dld_lsn':dld_lsn}
        try:
          images= ast.literal_eval(out1.splitlines()[0])['repositories']

          for image in images:
                #check if description for component exist and add it to temp
                #cmd=['curl','http://test:user@registry.cs.uno.edu/'+image.replace('/','-')]
                cmd=['curl','http://'+reguser+':'+regpas+'@'+registry+'/'+image.replace('/','-')]
                out1, out2 = executer(cmd)
         
                desc=out1.splitlines()
                if desc[0]!='<html>' and desc[0]!='':
                    temp['comps'][image]=[desc[0],'\n'.join(desc[1:])]

                    #check if description for lesson exist and add it to temp, if absent
                    image=image.split('/')[0]
                    try:
                        if temp['lesns'][image]:
                           pass
                    except:
                        #cmd=['curl','http://test:user@registry.cs.uno.edu/'+image]
                        cmd=['curl','http://'+reguser+':'+regpas+'@'+registry+'/'+image]
                        out1, out2 = executer(cmd)
                        desc=out1.splitlines()
                        if desc[0]!='<html>' and desc[0]!='':
                                temp['lesns'][image]=[desc[0],'\n'.join(desc[1:])]
       
                                #check if index for lesson exist and add to temp, if absent
                                try:
                                    if temp['index'][image]:
                                        pass
                                except:
                                    #cmd=['curl','http://test:user@registry.cs.uno.edu/'+image+'_index']
                                    cmd=['curl','http://'+reguser+':'+regpas+'@'+registry+'/'+image+'_index']
                                    out1, out2 = executer(cmd)
                                    desc=out1.splitlines()[0]
                                    if desc!='<html>' and desc!='':
                                       temp['index'][image]=desc
                        else:
                             temp['lesns'][image]=['n/a','n/a']
                else:
                    temp['comps'][image]=['n/a','n/a']
        except:
          print "some error in getting repo data"

        result = temp
        print result
        flask.flash(result)
             
        return flask.render_template('repo.html')

    @login_required
    def post(self):
        global dld_lsn
        global loc
        global registry,regmail,reguser,regpas

        flag = 0

        #login to the registry server
        #cmd = ['docker','login','-u','test','-p','user','--email="unotest3@gmail.com"','https://registry.cs.uno.edu']
        cmd = ['docker','login','-u',reguser,'-p',regpas,'--email="'+regmail+'"','https://'+registry]
        out1,out2=executer(cmd)

        try:
         request = flask.request.form['lesn']
         request = ast.literal_eval(request)
         lesn = request[0]
         cont = request[1]
         #info = cont['comps'][image]
         flag = 1
        except:
         request = flask.request.form['comp']
         request = ast.literal_eval(request)
         image = request[0]
         cont = request[1]
         info = cont['comps'][image]

         #download just the component image from the registry server in a thread
         cmd = ['docker','pull',registry+'/'+image]
         t = threading.Thread(name='child procs', target=downloader, args=[cmd,image,info])
         t.daemon = True
         t.start()

         #return to back to web page
         return flask.redirect(flask.url_for('repo'))

        #add code if lesson is to be saved under a new name
        new_lsn = lesn

        #add lesson to the download list for lessons
        dld_lsn.append(lesn)
        
        #print lesn,'\n', cont
        new_cont = []

        for comp in cont['index'][lesn].split()[1:]:
               print "loop main",comp

               image1 = comp.replace(lesn,new_lsn)
               image = image1.replace('-','/')
               new_cont.append(image1)

               #download image from the registry server in a thread
               cmd = ['docker','pull',registry+'/'+image]
               info = cont['comps'][image]
               t = threading.Thread(name='child procs', target=downloader, args=[cmd,image,info])
               t.daemon = True
               t.start()

        #get description from POST and other attributes required for the lesson
        desc = cont['lesns'][lesn]
        line = new_lsn+' '+' '.join(new_cont)
        index = new_cont

        t = threading.Thread(name='child procs', target=add_lesson, args=[lesn,new_lsn,index,line,desc])
        t.daemon = True
        t.start()

        return flask.redirect(flask.url_for('repo'))


class Home(flask.views.MethodView):
    @login_required
    def get(self):

	global loc 
	#index2 {'lesson1': {'status': 'Y', 'comps': {'lesson1/comp1': {'status': ['Y'], 'index': ['lesson1/comp1', 'latest', '252f198a8beb', 'ago 380MB', 'Y', []], 'desc': ['Web Server', 'LAMP server hosting a PHP webpage.']}}, 'desc': ['SQL Injection to Shell II', 'This exercise explains how you can, from a blind SQL injection, gain access to the administration console. Then once in the administration console, how you can run commands on the system. ']}}


	#check if all files are available
	filechecker()

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
           flag=0
           for line in out1.splitlines():
             if 'lesson' in line:
                  var1=line.split()
                  if var1[var1.index('ago')+1] == 'Up':
		     index3[var1[-1]]=[var1[1],'Y']
                  else:
		     index3[var1[-1]]=[var1[1],'S']
		  index4.append(var1[-1])

	print "Home",index3,index4
	index1={}
        temp2=[]

	#check downloaded images
        cmd = ['docker', 'images']
        out1, out2 = executer(cmd)

	for line in out1.splitlines():
	   temp3 = []
	   flags = []
	   temp = line.split()
           if line.startswith('lesson'):

	      status=''
	      #555 history command no longer gives you image id of intermediate containers
              cmd = ["docker","history","--no-trunc",temp[0]]
              temp2=executer(cmd)

	      image = []
	      flags = 0
              for step in temp2[0].splitlines():
                  if '"@STEP@' in step:
                     step = step.split()
		     image = step[0][0:3]
		     temp1=[]
		     try:
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

	print "index",index1
        temp=[]
        index2={}
        fname=loc+'static/configs/lesson.txt'
        with open(fname) as f:
             temp=f.read().splitlines()

        for item in temp:
	    count1 = count2 = 0
            item = item.split()
            index2[item[0]]={}
	    if True:
		#check files and add the lesson title and description
		try:
		    fbuf=[]
		    fname=loc+'static/lessons/'+item[0]
                    with open(fname) as f:
                         fbuf=f.read().splitlines()
		    index2[item[0]]['desc']=[fbuf[0],''.join(fbuf[1:])]
		except:
                    index2[item[0]]['desc']=['','']

                index2[item[0]]['comps']={}
                index2[item[0]]['status']=''

	    #print item,index2
            for key in item[1:]:
		#check files and add the component title and description
		print "--",key
		try:
		    fbuf=[]
		    fname='static/lessons/'+key
                    with open(fname) as f:
                         fbuf=f.read().splitlines()
		    comp_desc = [fbuf[0],''.join(fbuf[1:])]
		except:
		    comp_desc = ['','']

		ip = 'n/a'
		try:
		    temp3=index1[key.replace('-','/')]
		    if temp3[4]=='Y':
		       cmd = ['docker','inspect','--format','{{ .NetworkSettings.IPAddress}}',key]
		       ip,err = executer(cmd)
		       ip = ip.rstrip()
		       count1+=1
		    elif temp3[4]=='N':
		       count2+=1
		except:
		    temp3=[]

                index2[item[0]]['comps'][key.replace('-','/')]={'index':temp3,'desc':comp_desc,'status':[temp3[4]],'network':[ip]}
		#print key,comp_desc,temp3
		#print index2

	    print item[1:],count1,count2
	    if count1 == len(item[1:]):
               index2[item[0]]['status']='Y'
	    elif count2 == len(item[1:]) :
               index2[item[0]]['status']='N'
	    else:
               index2[item[0]]['status']='S'


	#print "new"
        #print index3
        #print index1
        print "index2",index2

	flask.flash(index2,'lesson')

        return flask.render_template('home.html')

    @login_required
    def post(self):
        request = flask.request.form
	result = {}
	temp1 = []
        temp2 = []
	print request

	try:
	  if request['start-all']:
	     print request['start-all']
	     try:
	         temp=ast.literal_eval(request['start-all'])
		 targets=temp.keys()
	     except:
		 pass

	     print targets
	     for cont in targets:
		 image = temp[cont]['index'][2]
                 print "starting container ",cont,image
                 cmd = ['docker', 'run', '-Pitd', '--name='+cont.replace('/','-'), image]
                 out1, out2 = executer(cmd)
	         print "out-",cont,out2
	except:
	 try:
	     if request['stop-all']:
		try:
	            temp=ast.literal_eval(request['stop-all'])
		    request=temp.keys()
		except:
	            request=[request['stop-all']]
                print "stop all containers ",request
	        for cont in request:
		    cont = cont.replace('/','-')
                    print "stopping container "+cont
                    cmd = ['docker', 'stop', cont]
                    out1, out2 = executer(cmd)
	 except:
	     try:
	         if request['reset-all']:
		    try:
		 	conts = ast.literal_eval(request['reset-all'])
			targets = conts.keys()
		    except:
			targets = [request['reset-all']]
	            for cont in targets:
                        print "resetting container ",cont
			try:
                           cmd = ['docker','rm','-f', cont.replace('/','-')]
                           out1, out2 = executer(cmd)
			except:
			   pass
	     except :
	       try:
		    if request['jump']:
			request = ast.literal_eval(request['jump'])
			key = request.keys()[0]
			target = request[key][0]
			print key,target
			try:
                           cmd = ['docker', 'rm','-f',key.replace('/','-')]
                           out1, out2 = executer(cmd)
			   print cmd
                           cmd = ['docker', 'run','-itd','-P','--name='+key.replace('/','-'),target]
			   print cmd
                           out1, out2 = executer(cmd)
			except:
			   print "error in jump - \n",out2
	       except:
		 try:
		    if request['restart-all']:
		       vals=[]
		       try:
			 conts = ast.literal_eval(request['restart-all'])
			 targets = conts.keys()
		       except:
			 targets = [request['restart-all']]

	               for cont in targets:
                           print "restarting container ",cont
		       	   try:
                              cmd = ['docker','restart', cont.replace('/','-')]
                              out1, out2 = executer(cmd)
		       	   except:
			     print "error restarting",cont
		 except:
		    try:
		        if request['connect']:
	                   temp=ast.literal_eval(request['connect'])
			   conts=temp[0].replace('/','-')
			   title=temp[0].split('-')[0]+' '+temp[1]
                           print "connect to container "+conts,title
		      	   try:
			       cmd='docker attach '+conts
           		       subprocess.Popen(['xterm','-T',title,'-e',cmd])
			   except:
			       print "error at xterm"
		    except:
		       e = sys.exc_info()[0]
		       print "Exception", e

        return flask.redirect(flask.url_for('home'))

class Custom(flask.views.MethodView):
    @login_required
    def get(self):
        print "asd"

    @login_required
    def post(self):
        print "asd"

app.add_url_rule('/',
                 view_func=Main.as_view('index'),
                 methods=["GET", "POST"])
app.add_url_rule('/home/',
                 view_func=Home.as_view('home'),
                 methods=['GET', 'POST'])
app.add_url_rule('/repo/',
                 view_func=Repo.as_view('repo'),
                 methods=['GET', 'POST'])

app.debug = True
app.run(host='0.0.0.0')
