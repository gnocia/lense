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

loc = os.getcwd()+"/"

#variables for database
dbuser = ""
dbpasswd = ""

#variables for registry
registry = ""
regmail = ""
reguser = ""
regpas = ""

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
    elif line[0] == "dbuser":
       dbuser = line[2]
    elif line[0] == "dbpasswd":
       dbpasswd = line[2]

grps = []
users = {'test':'bacon'}
radio1 = ''
radio2 = ''
search1 = ''
search2 = ''
dld = []
dld_lsn = []
output = []

############################################
#function to execute commands in a subprocess
############################################
def executer(cmd):
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out, err

############################################
#function to execute commands in a subprocess thread
############################################
def thread_executer(cmd):
  global dld
  print "in thread",cmd

  p = subprocess.Popen(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  out, err = p.communicate()
  temp=out.splitlines()[-2].split()[0]
  if temp=='Digest:':
     dld.remove(cmd[-1])

############################################
#function to download exercise or component
############################################
def downloader(cmd,image,info):
    global dld
    global loc

    #STEP 1
    #add component/image to downloading
    dld.append(image)
    print "Downloading ",cmd,image

    out,err = executer(cmd)

    print "finished dld ",image

    #STEP 2
    #after successful download, tag the image to required image/component name
    if 'Digest' in out:
       try:
	 cmd = ['docker','tag',cmd[2],image]
         out,err = executer(cmd)
         try:
	   #after tagging, save component description in lessons folder
	   print loc+"static/lessons/"+image.replace('/','-')
           with open(loc+"static/lessons/"+image.replace('/','-'),'w') as f:
                f.write(info[0]+"\n"+info[1])
           f.close()
         except:
           print "error writing file",image,info
       except:
         print "error renaming ",image
    else:
       print "failed downloading",image

    #remove all occurences of download request for image/componet from the download queue
    while image in dld : dld.remove(image)
    print "exiting ",image

############################################
#function to add exercise details and index file entries
############################################
def add_lesson(old_lesn,lesn,index,line,info):
    global dld
    global dld_lsn
    global loc

    flag = 1
    print "enter loop -  add_lesson",dld,dld_lsn,index

    #wait till all components are removed from the download queue
    while flag:
        flag = 0
        for item in index:
            if item in dld:
               flag = 1
    print "exit loop - add_lesson"

    dld_lsn.remove(old_lesn)

    target = loc+'static/configs/lesson.txt'
    try:
	#check if line for lesson exist
        cmd=['grep','^'+lesn+' ',target]
        val,err = executer(cmd)

	#replace/create new line for lessons as necessary
        if val:
           cmd=['sed','-i','/^'+lesn+' /c '+line,target]
	   out1,out2=executer(cmd)
        else:
	   with open(target,'a') as f:
	        f.write(line+"\n")
	   f.close()

	#finally, save lesson description to the lessons folder
	with open(loc+'static/lessons/'+lesn,'w') as f:
	     f.write(info[0]+'\n'+info[1])
	f.close()
    except:
        print "error writing file",lesn

############################################
# function to create execute playbook
############################################
def thread_executer_2(cmd,args):
  global dld
  print "in thread",cmd

  #check if it is an ansible adhoc command or playbook
  if args[0] == 'play':
     try:
	#create hostfile
        f = open(cmd[2],'w')
        f.write(args[1])
        f.close()
	#create playbook
        f = open(cmd[3],'w')
        f.write(args[2])
        f.close()
     except:
        print "Error creating playbook ",cmd
  
  p = subprocess.Popen(cmd,shell=False,stdin=None,stdout=None,stderr=None,close_fds=True)


############################################
# function to read a given filename and return contents as a list
############################################
def reader(fname):
    index=[]
    try:
      with open(fname) as f:
	 index = f.read().splitlines()
      f.close()
    except:
      pass

    return index

############################################
# function to return execution of a query in database
############################################
def db_ops(cmds,arg):

    global dbuser, dbpasswd

    #login to database
    db = MySQLdb.connect(host="localhost", 
                     user=dbuser,         
                     passwd=dbpasswd,  
                     db="lense")        
    cur = db.cursor()

    #execute each query
    for cmd in cmds:
        cur.execute(cmd)
	result = cur.fetchall()

    #commit if arg = 1
    if arg == 1:
	db.commit()

    #return the results
    return result

    db.close()


############################################
# Main class
############################################
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

	#acquire username and password from the form
        username = flask.request.form['username']
        passwd = flask.request.form['passwd']

        cmd = "SELECT * FROM users WHERE passwd='"+passwd+"' AND uname='"+username+"'"
	flag=db_ops([cmd],0)

        #if username and password is valid, load page
	if flag:
            flask.session['username'] = username
        else:
            flask.flash("Username doesn't exist or incorrect password")
        return flask.redirect(flask.url_for('bhome'))

#################################################
# function to make sure access to pages are granted only after valid authentication
#################################################
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
	print out1,out2

	print "asdasd"
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
        #global radio2, search2, dld
        #print flask.request.form
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

class Remote(flask.views.MethodView):
    @login_required
    def get(self):
	global output, radio1
	search1=dld=""
	var1=[]

	if radio1=="":
	   radio1="ping"

	flask.flash([radio1,search1,dld],'')

	out1,out2=executer(['ls','static/uploads/script'])
	flask.flash(out1,'script')

	out1,out2=executer(['ls','static/uploads/playbook'])
	flask.flash(out1,'playbook')

	out1, out2 = executer(['cat', 'static/configs/hosts'])
	for line in out1.splitlines():
	    if line != "" and line[0]=='[':
               var1.append(line[1:-1])
	flask.flash(var1,'group')

	flask.flash(output,'output')

        return flask.render_template('remote.html')
        
    @login_required
    def post(self):
        global radio1, search1, dld, output
	tgt=""
	cmd=[]

        result = flask.request.form['radio']
	print flask.request.form

	if result=='ping' or result=='service':
           tgt = flask.request.form['target']
	   if tgt=='all':
	      grp = 'all'
	   elif tgt=='group':
	      grp = flask.request.form['group']
	   elif tgt=='ip':
	      grp = flask.request.form['search1']

	if result=='ping':
	   output=[]
	   radio1='ping'
	   cmd = ['ansible','-i','static/configs/hosts',grp,'-m','ping']
	   out1,out2=executer(cmd)
	   #print cmd,out1

	   for line in out1.splitlines():
	       temp=line.split()
	       if '|' in temp:
    		  output.append([temp[0], temp[2]])

	elif result=='service':
           output=[]
	   radio1='service'
           cmd = ['ansible', '-b', '-i', 'static/configs/hosts', grp, 
                     '-m', 'service', '-a', 'name='+flask.request.form['service']+' state='+flask.request.form['status']]
           out1,out2=executer(cmd)
	   print cmd,out1

           for line in out1.splitlines():
               temp=line.split()
               if '|' in temp:
	   	  if temp[2]=='SUCCESS':
	     	     arg2=flask.request.form['status']
	   	  else:
	   	     arg2=temp[2]
                  output.append([temp[0], arg2])

	elif result=='script':
           tgt = flask.request.form['target']
	elif result=='play':
           tgt = flask.request.form['target']
	elif result=='cont':
	   print flask.request.form

        #flask.flash([result])

        return flask.redirect(flask.url_for('remote'))

class Cont(flask.views.MethodView):
    @login_required
    def get(self):

        cmd = ['ansible', '-b', '-i', 'static/configs/hosts', 'apache', 
               '-m', 'command', '-a', 'bash /home/lense/test.sh']

	out1, out2 = executer(cmd)

        flag=flag2=flag3=flag4=0
	temp=[]
	result=[]
	for line in out1.splitlines():
	    if 'SUCCESS' in line:
	       temp.append(line.split()[0])
               flag=1
	       flag2+=1
	    elif flag==1:
	       temp.append(ast.literal_eval(line))
	       result.append(temp)
	       flag=0
	       temp=[]
            elif 'UNREACHABLE' in line:
	       temp=[line.split()[0], {'images':['n/a'],'exited':['n/a']}]
               result.append(temp)
	       temp=[]
	       flag3+=1
	    
        summary=[flag2,flag3]
	result.append(summary)

	flask.flash(result,'group')
	
        return flask.render_template('cont.html')

    @login_required
    def post(self):
        print "asd"

class Manage(flask.views.MethodView):
    @login_required
    def get(self):
	result=temp=[]

        cmd = ['awk', '{print $1}', 'static/configs/hosts']
        out1, out2 = executer(cmd)

	for line in out1.splitlines():
	    if '[' in line:
	      if temp:
	         result.append(temp)
	      temp=[]
	      temp.append(line[1:-1])
	    else:
	      temp.append(line.split()[0])
	result.append(temp)

        #flash results of hosts file
	flask.flash(result,'hosts')

        cmd = ['ls', 'static/uploads/script/']
        out1, out2 = executer(cmd)

	result=[]
	for line in out1.splitlines():
	     temp=line.split('.')
	     temp2=[]
	     if 'sh' in temp:
	        temp2.append('shell')
	     elif 'py' in temp:
	        temp2.append('python')

	     temp2.append(temp[0])
	     result.append(temp2)	

        #flash lists of scripts
	flask.flash(result,'script')

        cmd = ['ls', 'static/uploads/playbook/']
        out1, out2 = executer(cmd)
	
	result=[]
	for line in out1.splitlines():
	     temp=line.split('.')
	     if 'yml' in temp:
	        result.append(temp[0])	

        #flash lists of scripts
	flask.flash(result,'playb')

        return flask.render_template('manage.html')

    @login_required
    def post(self):
        print "asd"

class cHome(flask.views.MethodView):
    @login_required
    def get(self):

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

	#print index3,index4
	index1={}
        temp2=[]
        cmd = ['docker', 'images']
        out1, out2 = executer(cmd)

	for line in out1.splitlines():
	   temp3 = []
	   flags = []
           image = ''
	   temp = line.split()
           if line.startswith('lesson'):

	      status=''
              cmd = ["docker","history","--no-trunc",temp[0]]
              temp2=executer(cmd)

              for step in temp2[0].splitlines():
                  if '"@STEP@' in step:
                     step = step.split()
		     image = step[0][0:12]
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

	#print "index",index1
        temp=[]
        index2={}
        fname='static/configs/lesson.txt'
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
		    fname='static/lessons/'+item[0]
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

		try:
		    temp3=index1[key.replace('-','/')]
		    if temp3[4]=='Y':
		       count1+=1
		    elif temp3[4]=='N':
		       count2+=1
		except:
		    temp3=[]

                index2[item[0]]['comps'][key.replace('-','/')]={'index':temp3,'desc':comp_desc,'status':[temp3[4]]}
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
        print index2

	flask.flash(index2,'lesson')

        return flask.render_template('chome.html')

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

        return flask.redirect(flask.url_for('chome'))

class Save(flask.views.MethodView):
    @login_required
    def get(self):
        print "asd"

    @login_required
    def post(self):
        request = flask.request.form;

	if request['submit'] == 'add-submit':
	   temp="["+str(request['add-inp'])+"]\n"
	   flag=0
	   for line in request['textarea'].splitlines():
	       line=line.strip()
	       if len(line.split('.'))==4 and ''.join(line.split('.')).isdigit() :
		  #print "Yes"
		  flag=1
		  temp+=str(line)+" ansible_ssh_user=lense\n"

	   if flag:
	      fname='static/configs/hosts'
	      f=open(fname,'a')
	      f.write(temp)
	      f.close()

	else:
	 ips = re.sub('\s+',' ',request['textarea']).split()
	
	 #read the hosts file
	 conts=''
	 fname='static/configs/hosts'
	 with open(fname) as f:
	      conts=f.read()
	 f.close()
	     
	 gpname=request['submit']
	
	 #make a dictionary with the new set of ips for group gpname
	 group={gpname:[]}
	 for ip in ips:
	     temp = ip.split('.')
	     if len(temp) == 4 and ''.join(temp).isdigit() :
 	        group[gpname].append(ip.strip()+" ansible_ssh_user=lense")
	     
	 #add remainder of the groups and corresponding ips , excluding gpname if it existed in the hosts file
	 for line in conts.splitlines():
	     if '[' in line:
                if gpname!=line[1:-1]:
	 	  group[line[1:-1]]=[]
	  	  grp=line[1:-1]
	        else:
	  	  grp=''
	     else:
	  	try:
	 	  group[grp].append(line.strip())
	 	except:
	 	  print "error in splitting host file or omitting ips", grp
		
	 print group

	 string=""
	 for grp in group:
	    string+='['+grp+']'+"\n"
	    for temp in group[grp]: 
	 	string+=temp+"\n"
	
	 print string
	 f=open(fname,'w')
	 f.write(string)
	 f.close()

        return flask.redirect(flask.url_for('manage'))

class bHome(flask.views.MethodView):
    @login_required
    def get(self):
        print "load-asd"

	#fetch information about status from DB
	temp = [[],[]]
	try:
	   cmd = "select * from status"
	   db_data = db_ops([cmd],0)
	   for line in db_data:
	       if line[2] == "Y":
	          temp[0].append(line[0])
	       else:
	          temp[1].append(line[0])
	except:
	   print "DB error"

	hosts = {'active':list(set(temp[0])),'inactive':list(set(temp[1]))}
	status = db_data

	#fetch information about hosts from DB
	temp = [[],{}]
	try:
	   cmd = "select * from hosts"
	   db_data = db_ops([cmd],0)
	   for line in db_data:
	       try:
	         if line[1] not in temp[0]:
		    temp[0].append(line[1])
	       except:
		    temp[0]=[line[1]]
	       try:
		 if line[1] not in temp[1][line[0]]:
	            temp[1][line[0]].append(line[1])
	       except:
	         temp[1][line[0]]=[line[1]]
	except:
	   pass

	groups = {'names':temp[0],'map':temp[1]}

	#fetch information from files
        temp = []
        temp3 = []
	descs = {}
	index = {}
	try:
           fname='static/configs/lesson.txt'
           with open(fname) as f:
                temp=f.read().splitlines()
	   f.close()
	   for line in temp:
	       temp2 = []
	       line = line.split()
	       index[line[0]]=line[1:]
	       for item in line:
		   try:
		       with open('static/lessons/'+item) as f:
                	    temp3=f.read().splitlines()
	   	       f.close()
		       #temp2.append(temp3[0])
		       temp2.extend([temp3[0],''.join(temp3[1:])])
		   except:
		       temp2.extend(['',''])
		       print "bHome: Error reading file ",item
	       descs[line[0]]=temp2	
	except:
	   print "Error in lesson file"

	#print "result",result
	#print "index",index
	#print "desc",descs

	result = {'status':status,'hosts':hosts,'groups':groups,'lesson':{'index':index,'desc':descs}}
	print json.dumps(result)

	flask.flash(result,'result')
	#555

        return flask.render_template('bhome.html')


    @login_required
    def post(self):
	#variables for registry
	global registry, regmail, reguser, regpas

        print "post-asd"
        request = flask.request.form;
	print request	

	lists= request.getlist('lsncheck')
	lesson = request['slc-lsn']
	action = request['act-submit']
	details = ast.literal_eval(request['details'])
	ip_map = {}
	for data in details[2]:
	    if data[0] not in ip_map:
	       ip_map[data[0]]=data[1]
	    
	print "-------------",ip_map    

	if lists:
	   #print "lists",lists
	   result = {}
	   for item in lists:
	       item = ast.literal_eval(item)
	       try:
	           result[item[0]].append(item[1])
	       except:
	           result[item[0]]=[item[1]]
	else:
	   lists= request.getlist('check')
	   result = {}
	   try:
	     #lesson = request['slc-lsn']
	     for lsn in details[1][lesson]:
		 result[lsn]=lists
	   except:
	     print "lesson not selected"

	print "result",result
	if result:
          common = "---\n- hosts: default\n  gather_facts: no\n  strategy: free\n  tasks:\n\n"

          for item in result:

            # prepare hostfile for playbook
            hosts = result[item]
            #hosts = ['192.168.43.214']
            hostfile = "[default]\n"
            image = item.replace('-','/')
	    dbcmd = "INSERT INTO status values "

            for host in hosts:
                hostfile+=host+" ansible_ssh_user=lense\n"
		try: temp=ip_map[host] 
		except: temp=""

	        dbcmd += "('"+host+"','"+temp+"','Y','"+image+"','1','N','N'),"

	    dbcmd=dbcmd[:-1]+';'
	    print dbcmd
            #prepare the ansible playbook

            if action == "download":
	       #template = "    - name: login to registry\n      command: docker login -u test -p user --email='unotest3@gmail.com' https://registry.cs.uno.edu\n    - name: pull images\n      command: docker pull registry.cs.uno.edu/"+image+":latest\n    - name: rename image\n      command: docker tag registry.cs.uno.edu/"+image+":latest "+image+"\n    - name: download desc file\n      copy:\n        src: ../lessons/"+image.replace('/','-')+"\n        dest: /home/lense/lense/static/lessons/"+image.replace('/','-')
	       template = "    - name: login to registry\n      command: docker login -u "+reguser+" -p "+regpas+" --email='"+regmail+"' https://"+registry+"\n    - name: pull images\n      command: docker pull "+registry+"/"+image+":latest\n    - name: rename image\n      command: docker tag "+registry+"/"+image+":latest "+image+"\n    - name: download desc file\n      copy:\n        src: ../lessons/"+image.replace('/','-')+"\n        dest: /home/lense/lense/static/lessons/"+image.replace('/','-')
	       #print db_ops([dbcmd],1)
            else:
	       template = "    - name: data container\n      docker: \n        name: "+item+"\n        image: "+image+"\n        state: "+action+"\n        stdin_open: yes"

            #prepapre commands and arguments for execution of playbook
            filename = uuid.uuid4().hex
            cmds = ['ansible-playbook','-i','static/exec/'+filename,'static/exec/'+filename+'.yml']
            args = ['play',hostfile,common+template]

	    #execute each playbook in a new thread
            thread_executer_2(cmds,args)

	  #end of execution of for loop

	  #begin download procedure for lesson
          #prepapre commands and arguments for execution of playbook
          if action == "download":
	     hostfile = "[default]\n"
	     temp = []
	     for line in result.values():
	         for host in line:
		     if host not in temp:
                        hostfile+=host+" ansible_ssh_user=lense\n"
		        temp.append(host)

             filename = uuid.uuid4().hex
	     line = lesson+" "+' '.join(details[1][lesson])
             cmds = ['ansible-playbook','-i','static/exec/'+filename,'static/exec/'+filename+'.yml']
	     template="    - name: download lesson file\n      copy:\n        src: ../lessons/"+lesson+"\n        dest: /home/lense/lense/static/lessons/"+lesson+"\n    - name: create/edit lesson\n      lineinfile:\n        dest: /home/lense/lense/static/configs/lesson.txt\n        regexp: '^"+lesson+" '\n        line: '"+line+"'"
             args = ['play',hostfile,common+template]

	     #execute each playbook in a new thread
             thread_executer_2(cmds,args)

        return flask.redirect(flask.url_for('bhome'))

class ajaxRequest(flask.views.MethodView):
    @login_required
    def get(self):
        print "asd"

    @login_required
    def post(self):
        try:
            result = {}
            group = []
            hosts = [[],[]]
            hostmap = {}
            index = {}

            try:
               #read index of all lessons downloaded
               fname='static/configs/lesson.txt'
               with open(fname) as f:
                    temp=f.read().splitlines()
               f.close()
               for line in temp:
                   line = line.split()
                   index[line[0]]={}
                   for key in line[1:]:
                       try:
                            #read desc file and get title for each component
                            fname='static/lessons/'+key
                            with open(fname) as f:
                                 index[line[0]][key]=f.read.splitlines()[0]
                            f.close()
                       except:
                            index[line[0]][key]='n/a'
            except:
               temp=[]
               print "ERROR - Error reading or processing lesson.txt"

	    
            if temp != []:
               try:
                   cmd = "SELECT * FROM status"
                   rows = db_ops([cmd],0)

                   for row in rows:
                        #["137.30.121.56", "user11", "Y", "lesson2/comp1", "1", "Y", "Y"]
                        #check if the host is active

                        comp=row[3].replace('/','-')
                        if row[2]=='Y':

                              if row[5]=='N':
                                 #case - image downloading
                                 result[row[0]+comp]=[row[1],'Status : Downloading','/static/images/dnld4.png']
                              elif row[5]=='Y' and row[6]=='Y':
                                 #case - image downloaded and container started
                                 result[row[0]+comp]=[row[1],'Status : Started','/static/images/green.png']
                              elif row[5]=='Y' and row[6]=='S':
                                 #case - image downloaded but container exited/stopped
                                 result[row[0]+comp]=[row[1],'Status : Suspended','/static/images/red.png']
                              elif row[5]=='Y' and row[6]=='N':
                                 #case - image downloade but container not started at all
                                 result[row[0]+comp]=[row[1],'Status : Stopped','/static/images/white.png']

                              hosts[0].append(row[0]);

                        else:
                              #result[row[0]+row[3]]=[row[1],'N']
                              hosts[1].append(row[0]);

                   #loop through IPs and create lesson stats for each
                   for host in set(hosts[0]):
                       hostmap[host]={}
                       for lesn in index:
                           hostmap[host][lesn]={}
                           for comp in index[lesn]:
                               try:
                                  hostmap[host][lesn][host+comp]=result[host+comp]
                               except:
                                  hostmap[host][lesn][host+comp]=['','Status : Component not downloaded','/static/images/dash.png']
                       
               except:
                   print "ERROR - Failed to read from database"


            results = {'result':hostmap,'active':[list(set(hosts[0])),list(set(hosts[1]))]}
	    
            print results
            return json.dumps(results)

        except:
            #add code to process page when there is no content or error 555
            pass

class Create(flask.views.MethodView):
    @login_required
    def get(self):

	#fetch information from files
        temp1=temp2=[]
	index1 = {'desc':{},'index':{},'xtra':{}}
	try:
           temp1=reader('static/configs/lesson.txt')
	   for line in temp1:
	       line = line.split()
	       index1['index'][line[0]]=line[1:]

	       #get details of lesson and components
	       for item in line:
		 try:
                     temp2=reader('static/lessons/'+item)
		     index1['desc'][item]=[temp2[0],'\n'.join(temp2[1:])]
		 except:
		     index1['desc'][item]=['','']

	   try:
		cmd = ['docker','images'] 
	        out1, out2 = executer(cmd)

	        for line in out1.splitlines():
	           temp3 = []
	           flags = []
	           temp = line.split()
	           if line.startswith('lesson'):
		      temp = temp[0].replace('/','-')
		      try:
			  #check if its already added
		          check = index1['desc'][temp]
		      except:
			  try:
			      temp2=reader('static/lessons/'+temp)
			      index1['xtra'][temp]=[temp2[0],' '.join(temp2[1:])]
		          except:
		              index1['xtra'][temp]=['','']
	   except:
		print "Create: error in getting image"

	except:
	   print "Error in lesson file"

	print index1
	flask.flash(index1,'result')

        return flask.render_template('create.html')

    @login_required
    def post(self):
	global registry,regmail,reguser,regpas

        request = flask.request.form;
	print request,"\n"	
	all_item=[]

	#check if request is for Syncing or Deleting
	if request['submit'] == 'Sync':
	  try:
	     #get details as if request came for lesson

	     #get details from the form
	     action = request['lsn']
	     desc = request['lsn_desc']     
	     name = request['lsn_name']     
	     title = request['lsn_title']     

	     #write details of the lesson to the lessons folder
	     try:
	        with open('static/lessons/'+name,'w') as f:
		  f.write(title+'\n'+format(desc))
	        f.close()
	     except:
		print "ERROR - failed to write to file in lessons folder"

	     print "1"
	     #get lesson name and components in format
	     text = request['lsn_text'].replace(',',' ').split()
	     all_item = [name]+text

	     print "+"+action+"+"

	     #check if description for lesson is being edited or created- perform corresponding action
	     if action == 'edit':

		#action- edit - find and replace the entry for the lesson in the lessons.txt file
		try:
		  cmd=['sed','-i','/^'+name+'/c '+name+' '+' '.join(text),'static/configs/lesson.txt']
		  print cmd
		  val = executer(cmd)
		except:
		  print "ERROR - failed making edits for "+name+" in lesson.txt"

	     else:

		#action- create - append the entry for lesson in the lessons.txt file
	        with open('static/configs/lesson.txt','a') as f:
		     f.write(name+' '+' '.join(text))
	        f.close()

	  except:
	    print "ERROR - in Syncing lesson"
	    #when failed, get details as if request came for component

	    try:

	       #get details from the form
	       action = request['comp']
	       name = request['comp_name']
	       all_item = [name]
	       title = request['comp_title']
	       desc = request['comp_desc']

	       #check if request is to create component or edit
	       if action == 'create':
		  try:

		      #actions to create component
		      print "create"

		      #get component name of the image from the request
		      base = request['slc-comp'].split('$@$')[0]

		      #create new component image from the base image
		      if name != base:
			 print "clone image"
		         cmd = ['docker','tag',base.replace('-','/'),name.replace('-','/')]
		         val = executer(cmd)

		      #create description file for the created component in lessons folder
		      with open('static/lessons/'+name,'w') as f:
			f.write(title+"\n"+desc)
		      f.close()
		      
		  except:
		      print "ERROR - failed to create/tag entry for "+name+" during edit"

	       else:

		  try:
		      #actions to edit component
		      print "edit"

		      #overwrite the description file for the component
		      with open('static/lessons/'+name,'w') as f:
			f.write(title+"\n"+desc)
		      f.close()
		      
		  except:
		      print "Sync: error in edit"
	       
	    except:
	       print "Error in Main Sync-Comp"


	  #once the component images and description files for lessons and components
	  #are created, they need to synced with the server 

	  print "update",all_item

	  count = 0
	  temp3 = ""

	  #create ansible-playbook for syncing the component images by pushing to registry
	  #conts = "---\n- hosts: 127.0.0.1\n  connection: local\n  tasks:\n\n    - name: login to registry\n      command: docker login -u test -p user --email='unotest3@gmail.com' https://registry.cs.uno.edu\n"
	  conts = "---\n- hosts: 127.0.0.1\n  connection: local\n  tasks:\n\n    - name: login to registry\n      command: docker login -u "+reguser+" -p "+regpas+" --email='"+regmail+"' https://"+registry+"\n"

	  if len(all_item) > 1:
	     temp3="        - { src: '../lessons/"+all_item[0]+"',dest: '/home/lense/lense/ngx/uploads/' }\n"
	     temp2 = 1
	  else:
	     temp2 = 0

	  for item in all_item[temp2:]:
		 print "--",item
		 val = item.replace('-','/')
	         #conts +="    - name: rename image\n      command: docker tag "+val+" registry.cs.uno.edu/"+val+":latest\n    - name: push images\n      command: docker push registry.cs.uno.edu/"+val+":latest\n"
	         conts +="    - name: rename image\n      command: docker tag "+val+" "+registry+"/"+val+":latest\n    - name: push images\n      command: docker push "+registry+"/"+val+":latest\n"
	         temp3 +="        - { src: '../lessons/"+item+"',dest: '/home/lense/lense/ngx/uploads/' }\n"


	         count += 1

	  #create a random filename
	  filename = uuid.uuid4().hex

	  #add index file to the list of files to be copied if a lesson is being synced
	  if temp2 == 1: 
             with open('static/exec/'+filename+'_index','w') as f:
                  f.write(' '.join(all_item))
             f.close()
	     temp3 +="        - { src: '"+filename+"_index',dest: '/home/lense/lense/ngx/uploads/"+all_item[0]+"_index' }\n"

	  #add all the files required to be copied into the playbook
	  conts+="\n- hosts: default\n  tasks:\n\n    - name: copy files\n      copy: src={{ item.src }} dest={{ item.dest }}\n      with_items:\n"+temp3

	  #code for updating with server
	  print count,"\n",conts

	  #create commands and arguments required to execute the playbook in registry
	  #hostfile = "[default]\nregistry.cs.uno.edu  ansible_ssh_user=lense"
	  hostfile = "[default]\n"+registry+"  ansible_ssh_user=lense"
          cmds = ['ansible-playbook','-i','static/exec/'+filename,'static/exec/'+filename+'.yml']
          args = ['play',hostfile,conts]

	  #execute the created playbook in a new thread
	  thread_executer_2(cmds,args)

	elif request['submit'] == 'Delete':
	    try:
	       #modify - replace with file operation
	       action = request['lsn']
	       name = request['lsn_name']     
	       cmd = ['sed','-i','/^'+name+' /d','static/configs/lesson.txt']
	       val = executer(cmd)
	       arg = 'static/lessons/'+name
	    except:
	       action = request['comp']
	       name = request['comp_name']     
	       cmd = ['sed','-i','s/'+name+'//','static/configs/lesson.txt']
	       val = executer(cmd)
	       cmd = ['sed','-i','/^lesson.. *$/d','static/configs/lesson.txt']
	       val = executer(cmd)
	       arg = 'static/lessons/'+name

	    cmd = ['rm','-f',arg]
	    val = executer(cmd)

        return flask.redirect(flask.url_for('create'))

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
app.add_url_rule('/repo/',
                 view_func=Repo.as_view('repo'),
                 methods=['GET', 'POST'])
app.add_url_rule('/remote/',
                 view_func=Remote.as_view('remote'),
                 methods=['GET', 'POST'])
app.add_url_rule('/cont/',
                 view_func=Cont.as_view('cont'),
                 methods=['GET', 'POST'])
app.add_url_rule('/manage/',
                 view_func=Manage.as_view('manage'),
                 methods=['GET', 'POST'])
app.add_url_rule('/chome/',
                 view_func=cHome.as_view('chome'),
                 methods=['GET', 'POST'])
app.add_url_rule('/bhome/',
                 view_func=bHome.as_view('bhome'),
                 methods=['GET', 'POST'])
app.add_url_rule('/save/',
                 view_func=Save.as_view('save'),
                 methods=['GET', 'POST'])
app.add_url_rule('/create/',
                 view_func=Create.as_view('create'),
                 methods=['GET', 'POST'])
app.add_url_rule('/ajaxrequest/',
                 view_func=ajaxRequest.as_view('ajaxrequest'),
                 methods=['GET', 'POST'])

app.debug = True
app.run(host='0.0.0.0')
