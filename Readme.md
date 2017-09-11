# Lense 

Lense is a lightweight platform for cybersecurity education build on container technology that 
    - dramatically reduces resource requirements
    - provides predictable, appliance-like deployment
    - simplifies and automates the deployment process, and 
    - facilitates sharing among educators via an open, central repository

## 1. Installation
### 1.1 Admin Server
The server side requires Docker, Ansible and Python Flask for its functionality.
#### 1.1.1 Docker 
To get the latest version Docker, it needs to be installed from the official Docker repository.

First update the package database:
```sh
sudo apt-get update
```
Now install Docker. Add the GPG key for the official Docker repository to the system:
```sh
sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
```
Add the Docker repository to APT sources:
```sh
sudo apt-add-repository 'deb https://apt.dockerproject.org/repo ubuntu-xenial main'
```
Update the package database with the Docker packages from the newly added repo:
```sh
sudo apt-get update
```
Finally, install Docker:
```sh
sudo apt-get install -y docker-engine
```
Docker should now be installed, the daemon started, and the process enabled to start on boot. Check that it's running:
```sh
sudo systemctl status docker
```
The output should be similar to the following, showing that the service is active and running:
>docker.service - Docker Application Container Engine
>Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
>Active: active (running) since Sun 2016-05-01 06:53:52 CDT; 1 weeks 3 days ago
>Docs: https://docs.docker.com
>Main PID: 749 (docker)
    
By default, running the docker command requires root privileges — that is, you have to prefix the command with sudo. To avoid typing sudo whenever you run the docker command, add your username to the docker group:
```sh
sudo usermod -aG docker $username
```
Logout of the account and log back in to execute Docker commands without sudo
#### 1.1.2 Ansible
While there are many popular configuration management systems available for Linux systems, such as Chef and Puppet, these are often more complex than many people want or need. Ansible is a great alternative to these options because it has a much smaller overhead to get started. Ansible communicates over normal SSH channels in order to retrieve information from remote machines, issue commands, and copy files. Because of this, an Ansible system does not require any additional software to be installed on the client computers.

Easiest way to install Ansible for Ubuntu is to add the project's PPA (personal package archive) to the system.  Install the software-properties-common package, to work with PPAs easily.

```sh
sudo apt-get update
sudo apt-get install software-properties-common
```
Once the package is installed, we can add the Ansible PPA by typing the following command:
```sh
sudo apt-add-repository ppa:ansible/ansible
```
Refresh the system's package index and install Ansible:
```sh
sudo apt-get update
sudo apt-get install ansible
```
Disable host key checking in Ansible by uncommenting the below line in the configuration file - /etc/ansible/ansible.cfg :
```sh
host_key_checking = False
```
Ansible primarily communicates with client computers through SSH. While it certainly has the ability to handle password-based SSH authentication, SSH keys help keep things simple.For ansible to work, all client machines must have the passwordless access from machine configured as server.
    
To create create an RSA key-pair by typing:
```sh
ssh-keygen -t rsa
```
Specify the file location of the created key pair, a passphrase, and the passphrase confirmation. Press ENTER through all of these to accept the default values.

If SSH is not installed int the server, install it using the command
```sh
apt-get install openssh-server
```
Use ssh from the server to create a directory ~/.ssh for user 'lense' on the clients and registry machine

```sh
ssh lense@B mkdir -p /home/lense/.ssh
```
> Note: B is the IP address or hostname of the client machine 
> Make sure that user 'lense' exist in the client machine. Create it if it is not created already.

Finally append the server's public key to client's authorized_keys by executing the following command in the server
```sh
cat ~/.ssh/id_rsa.pub | ssh lense@B 'cat >> .ssh/authorized_keys'
```
Check if the server has passwordless access from the server by typing or by issuing an ansible command. Add the the ip address of the client and username, under a some group in a hostfile
```sh
[$user_group]
$ip_address ansible_ssh_user=lense 
```
Check with ansible command
```sh
ansible -i $hostfile -m ping $user_group
```
Successful access will give the following output
```sh
host1 | success >> {
"changed": false,
"ping": "pong"
}
```
#### 1.1.3 Python Flask
Install python and python pip packages required to install Pyhton Flask
```sh
apt-get install python python-pip
```
Install Flask using pip
```sh
pip install Flask
```
Download the project from Git and place the lense-server folder in the home directory of the server
```sh 
cp -r $download_location/lense-server ~/lense/
```

#### 1.1.4 MySQL
Install MySQL and change some of the less secure default options for things like remote root logins and sample users, using mysql_secure_installation
```sh
sudo apt-get install mysql-server 
sudo mysql_secure_installation
```
Install packages for python to access mysql database
```sh
apt-get install python-dev libmysqlclient-dev
pip install MySQL-python
```
Login to mysql using the root account with the password created for the user during the installlation
```sh
mysql -u root -p
```
Create database 'lense' and set up tables using the mysql dump file 'lense.sql' inside the ~/lense/static/configs folder
```sh
mysql> create database lense;
mysql> use lense;
mysql> source $directory/static/configs/lense.sql;
```
Create user 'lense' to access the database 'lense'
```sh
CREATE USER 'lense'@'localhost' IDENTIFIED BY '$password';
GRANT ALL PRIVILEGES ON lense. * TO 'lense'@'localhost';
FLUSH PRIVILEGES;
```
Logout of root account and log back in as user 'lense' to see the 'lense' database is accessible
```sh
mysql -u lense -p

#Inside the mysql shell
>mysql use lense;
```

Once inside the 'lense' database, create couple of users by inserting values into the table 'users'.
```sh
>mysql INSERT INTO users values ('random_uid','username','first_name','middle_name','last_name','','password','email_address');
```

> NOTE: This is the username and password that a user can use to login to the webapp.



 Note: Make sure curl is installed in the server
```sh
apt-get install curl
```



### 1.2 Registry Server
Docker needs to be installed in the registry server just like in section 1.1.1.
Other packages to be installed in the registry server
```sh
apt-get install curl openssh-server
```
Create user 'lense' in the registry server and give a password of your choice
```sh
adduser lense
```
Allow user 'lense' to have sudo access to install packages
```sh
sudo usermod -aG sudo lense
```
Allow user 'lense' to execute Docker commands without sudo access by executing the command
```sh
sudo usermod -aG docker lense
```

Login to user 'lense' and create directory for storing images and other files inside the home directory of user 'lense'
```sh
su lense
cd
mkdir -p ~/lense/ngx/uploads ~/lense/reg/ ~/lense/ngx/certs
```
Docker by default doesnot have any security for authenticating user access or encrypting the user-registry communication. Therefore, users are authenticated with a Nginx proxy and communications are encrypted with the help of self signed certificates. Since we'll be using Nginx to handle our security, we'll first install the apache2-utils package which contains the htpasswd utility that can easily generate password hashes for authenticating users in Nginx:
```sh
sudo apt-get -y install apache2-utils
```
Create the first user as follows, replacing USERNAME with the username you want to use:
```sh
cd ~/lense/ngx
htpasswd -c registry.password $USERNAME
```
The username and password will be created inside a plain-text file registry.password. If you want to add more users in the future, just re-run the above command without the -c option.

To create certificates, first change to the ~/lense/ngx/certs directory
```sh
cd ~/lense/ngx/certs
```
Generate a new root key:
```sh
openssl genrsa -out devdockerCA.key 2048
```
Generate a root certificate :
```sh
openssl req -x509 -new -nodes -key devdockerCA.key -days 10000 -out devdockerCA.crt
```
>Note: Enter the registry server's FQDN or hostname as the common name (Example: registry.cs.uno.edu)
>To change hostname type the following command in the terminal:
>$ sudo hostname registry.cs.uno.edu

Then generate a key for your server :
```sh
openssl genrsa -out domain.key 2048
```
Now we have to make a certificate signing request. Provide the assigned hostname for the registry server in the below command.
```sh
openssl req -new -key domain.key -out $hostname.csr
```
> Note: Enter the registry server’s FQDN or hostname as the common name (Example: registry.cs.uno.edu)
> Do not enter a challenge password. Redo the above step if you have created a password.

Sign the certificate request
```sh
openssl x509 -req -in $hostname.csr -CA devdockerCA.crt -CAkey devdockerCA.key -CAcreateserial -out domain.crt -days 10000
```
So now, we have created our certificates for encrypting communication. To create the Nginx server and Docker registry, we simply download and run the pre configured images of these available from the Docker's public registry. 

> Note: Download the 'registry.conf' file from 'registry-server' folder of this Github account and replace the 'servername.domain.com' in line number 7 of the registry.conf file to $hostname of the regsitry server. Save or copy this file into the '~/lense/ngx/' folder of the registry server.

Now to host the registry and nginx, simple execute the following commands in order

```sh
# start registry container
docker run -p 5000 --name registry -e REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY=/data -v ~/lense/reg/data:/data registry:2

# start nginx proxy container
docker run -p 443:443 -p 80:80 --link registry:registry -v ~/lense/ngx/:/etc/nginx/conf.d -v /tmp/lense/:/var/log/nginx/ --name nginx nginx
```
>Note: Always start the registry container before nginx container. Remove any running container fo the same name using 'docker rm -f $container_name' command

Registry and Nginx container will be downloaded from the Docker Hub repo automatically and started. The access and error logs for nginx will be available in directory '/tmp/lense/'. You can change this location by modifying it in the above command for starting nginx container.

Check status of the container using *docker ps -a* command. You should see the registry and nginx container up and running.

#### 1.2.2 Accessing the Registry
Since the certificates we just generated in the steps above, aren't verified by any known certificate authority. We need to tell all clients/servers that are going to be using this Docker registry that this is a legitimate certificate. Every client/server that needs to be access the Docker regsitry has to perform these two steps, below.

Copy the devdockerCA.crt from the registry server to the required machine using scp command or physical copy using removable media. Once copied, execute the following commands in the required client/server:
```sh
mkdir /usr/local/share/ca-certificates/docker-dev-cert
cp devdockerCA.crt /usr/local/share/ca-certificates/docker-dev-cert
update-ca-certificates
```
Restart the Docker daemon in the client/server so that it picks up the changes to our certificate store:
```sh
sudo service docker restart
```
Check if access can be made from the client/server machine using the login credentials with the following command:
```sh
docker login https://$registry_hostname
```

### 1.3 Clients
Docker and Flask needs to be installed inside the clients, just like in section 1.1.1 and 1.1.3 respectively. Copy the Additionally, for serverside ansible to control clientside docker components, docker-py package needs to be installed
```sh
sudo pip install docker-py
```
Install packages for ssh, and python to access mysql
```sh
sudo apt-get install openssh-server python-dev libmysqlclient-dev
sudo pip install MySQL-python
```
Install other required packages
```sh
sudo apt-get install xterm curl
```
Create user lense and login to it
```sh
sudo adduser lense
su lense
```
Place the contents of 'lense-client' from Github to /home/lense/lense/ folder of the client.

> Note: make sure that certificates for the registry server is placed inside all the clients as mentioned in Section 1.2.2

### 1.4. Running the Webapp

#### 1.4.1 Lense Server
To run server side webapp, browse to the lense directory and edit the 'config.txt' inside the ~/lense/static/configs/ folder and provide information in variables for registry and database access.

After all the information have been filled in the config.txt file, execute the following commands in separate terminals^M
```sh
python server.py
python adv-server.py
python sync-server.py
```

#### 1.4.2 Client Server
To run the client side webapp, login to user 'lense' and browse to the lense directory and edit the 'config.txt' inside the ~/lense/static/configs/ folder and provide information in variables for registry and database access.

After all the information have been filled in the config.txt file, execute the following commands in separate terminals
```sh
python client.py
python client-daemon.py
```

Once all the python script shave been run, you can access the webapp by typing in the Web_Browser 'localhost:5000'

 > Make sure that admin server has passwordless access to both clients and registry server. Also make sure clients and server have executed the procedures mentioned in Section 1.2.1, to accept the certificates for registry server. 
