# Deployment on Google Compute engine - Debian8(jessie)
This document describes the deployment of columbus on a Debian8 google cloud compute engine instance.

### Disk Conventions
Follow the below conventions for mounting the disks on the compute engine instances as columbus is configured to look for these paths.

  - /mnt/ldsk - local ssd disk
  - /mnt/pdsk - persistent ssd disk
  - /mnt/bdsk - google cloud storage bucket
  - /mnt/tdsk - google cloud storage staging bucket

### Mounting local and peristent disks
1. Check if the disks are mounted using the below command. If you see /dev/sdX other than boot disk then mounting was already done
    ```sh
    $ df -h
    ```
    
2. Check for the available disks
    ```sh
    $ ls -l /dev/disk/by-id/*
    ```
    
3. Create two directories to mount local and persistent(optional) disks
    ```sh
    $ sudo mkdir /mnt/ldsk
    $ sudo mkdir /mnt/pdsk
    ```
    
4. [Formatting the local disk](https://cloud.google.com/compute/docs/disks/local-ssd#formatindividual)
    ```sh
    $ sudo mkfs.ext4 -F /dev/disk/by-id/google-local-ssd-0
    ```
    
5. Mounting local disk
    ```sh
    $ sudo mount -o discard,defaults /dev/disk/by-id/google-local-ssd-0 /mnt/ldsk
    ```
    
6. Give all users write access 
    ```sh
    $ sudo chmod a+w /mnt/ldsk
    ```
    
7. Add the local SSD to the /etc/fstab file so that the device automatically mounts if the instance restarts.
    ```sh
    $ echo '/dev/disk/by-id/google-local-ssd-0 /mnt/ldsk ext4 discard,defaults 1 1' | sudo tee -a /etc/fstab
    ```
    
8. [Formatting persistent disk(Optional)](https://cloud.google.com/compute/docs/disks/add-persistent-disk#formatting):
    ```sh
    $ sudo mkfs.ext4 -F -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/disk/by-id/google-[DISK_NAME]
    ```
    
9. Mounting persistent disk (Optional)
    ```sh
    $ sudo mount -o discard,defaults /dev/disk/by-id/google-[DISK_NAME] /mnt/pdsk
    ```
    
10. Same steps as 6 and 7 but with persistent disk name.

### Mounting cloud storage as a disk
1. Install [gcsfuse](https://github.com/GoogleCloudPlatform/gcsfuse/blob/master/docs/installing.md) following the instructions below
    ```sh
	$ export GCSFUSE_REPO=gcsfuse-`lsb_release -c -s`
	$ echo "deb http://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
	$ curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
	$ sudo apt-get update
	$ sudo apt-get install gcsfuse
    ```
    
2. Create a storage bucket using the cloud console (say bucket1)
3. create a directory /mnt/bdsk to mount the bucket and give that directory write permissions
    ```sh
    $ sudo chmod a+w /mnt/bdsk
    ```
    
4. Mount the bucket
    ```sh
    $ gcsfuse --key-file=<service-account-private-key.json> bucket1 /mnt/bdsk
    ```

### Unmounting a disk
Use the following command to unmount a disk if needed. To unmount directories mounted using gcsfuse, use `fusermount` 
```sh
$ sudo umount <mounted directory name>
$ fusermount -u <mounted directory name>
```

### Installation
1. Install pip
    ```sh
    $ curl -O https://bootstrap.pypa.io/get-pip.py
    $ sudo python get-pip.py
    ```
    
2. Install virtualenv
    ```sh
    $ sudo pip install virtualenv
    ```
    
3. Install build-essentials
    ```sh
    $ sudo apt-get install build-essential
    ```
    
4. Install mysql-dev
    ```sh
    $ sudo apt-get install libmysqlclient-dev
    ```
    
5. Install python-dev
    ```sh
    $ sudo apt-get install python-dev
    ```
    
6. Install libssl-dev and libffi-dev
    ```sh
    $ sudo apt-get install libssl-dev libffi-dev
    ```
    
7. Install libxml and libxslt
    ```sh
    $ sudo apt-get install libxml2-dev libxslt-dev
    ```

8. create a directory for virtual env and change the owner to the user
    ```sh
    $ sudo mkdir /home/edf
    $ sudo chown johnsoncharles26 /home/edf
    ```
    
9. Create a virtual environment(you should be able to create without sudo otherwise navigate to /home/edf and try again)
    ```sh
    $ virtualenv --no-site-packages -p /usr/bin/python2.7 /home/edf/venv
    ```
    
10. Navigate to the virtual env and activate it. The prompt should change to (venv).
    ```sh
    $ cd /home/edf/venv
    $ source bin/activate
    ```
    
11. Create a file **requirements-local.txt** and paste the following in it or use the `requirements.txt` present in the distribution.
    ```sh
    cachetools==1.1.6
    Django==1.9.4
    earthengine-api==0.1.92
    geojson==1.3.2
    google-api-python-client==1.5.2
    oauth2client==3.0.0
    oauthlib==1.1.1
    requesocks==0.10.8
    requests==2.7.0
    simplejson==3.8.2
    MySQL-python==1.2.5
    pandas==0.16.2
    pyOpenSSL==16.0.0
    python-dateutil==2.4.2
    requests-oauthlib==0.6.1
    scikit-learn==0.16.1
    scilab2py==0.6
    scipy==0.16.0
    sympy==0.7.6
    XlsxWriter==0.7.3
    lxml==3.6.0
    pykml==0.1.0
    ```
    
12. Install all the requirements using the following command in (venv) prompt
    ```sh
    (venv) $ pip install -r requirements-local.txt
    ```
    
13. Deactivate virtualenv using the following command in venv prompt
    ```sh
    (venv) $ deactivate
    ```
    
14. Install and start apache outside virtual env
    ```sh
    $ sudo apt-get install apache2
    $ sudo apache2ctl start
    ```
    
15. Install mod-wsgi
    ```sh
    $ sudo apt-get install libapache2-mod-wsgi
    ```
    
16. Test mod-wsgi installation
    - Make a directory "test" in /home/edf/venv
        ```sh
        $ cd /home/edf/venv
        $ mkdir test
        ```
        
    - Create a file named "testapp.wsgi" in /home/edf/venv/test and paste the following contents in it
        ```python
        def application(environ, start_response):
    	    status = '200 OK'
    	    output = 'Hello World!'
    	    response_headers = [('Content-type', 'text/plain'),('Content-Length', str(len(output)))]
    	    start_response(status, response_headers)
    	    return [output]
        ```
        
    - Make note of the user and group of the directory /home/edf/venv
        ```sh
        $ ls -l /home/edf
        Output:
        drwxr-xr-x 8 johnsoncharles26 johnsoncharles26 4096 Jun 15 22:38 venv
        First occurence of johnsoncharles26 is user and the second occurence is group
        ```
        
    - Open the apache2 conf file:
        ```sh
        $ cd /etc/apache2
        $ sudo vi apache2.conf
        ```
        
    - Paste the following contents after the last `</Directory>` tag. You can look up the WSGIDaemonProcess documentation [here](http://modwsgi.readthedocs.io/en/develop/configuration-directives/WSGIDaemonProcess.html)
        ```apache
    	WSGIDaemonProcess columbus-daemon user=johnsoncharles26 group=johnsoncharles26 threads=25 python-path=/home/edf/venv/lib/python2.7/site-packages
    	WSGIProcessGroup columbus-daemon
    	WSGIScriptAlias /testapp "/home/edf/venv/test/testapp.wsgi"
    
    	<Directory /home/edf/venv/test>
    		AllowOverride none
    		Order deny,allow
    		Allow from all
    		Require all granted
    	</Directory>
    	```
    	
    - Restart the server. 
        ```sh
        $ sudo apache2ctl restart
        ```
        
    - Navigate to `compute-engine-instance-ip/testapp` in a browser. You should see Hello World!
    
### Deployment
If mod_wsgi installation was successful please follow the below steps to deploy columbus.

1. Copy the columbus source code to /home/edf/venv. Your directory structure should be as follows:
    ```
    /home/edf/venv/columbus
    ├─── apache
    ├─── columbus
    ├─── pyedf
    ├─── secured
    ├─── static
    ├─── templates
    ├─── manage.py
    ```
    
2. Note that the secured directory should contain the service account private key files and you should change the file names for the constants `EE_CREDENTIALS`, `BQ_CREDENTIALS`, `FT_CREDENTIALS`, and `CS_CREDENTIALS` in the settings file under columbus directory. If a single service account has access to all of the mentioned services, then use that file name for all these constants else use the file name for the service appropriate service. Note that for Fusion tables, the service account must have access to both fusion tables and google drive.
    ```python
    # service account credentials from Google dev console for Google Earth Engine
    EE_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
    # service account credentials from Google dev console for Google Bigquery
    BQ_CREDENTIALS = os.path.join(SECURED_DIR, 'earth-outreach-bigquery.json')
    # service account credentials from Google dev console for Google Cloud Storage
    CS_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
    # service account credentials from Google dev console for Google Fusion Tables and Google Drive
    FT_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
    ```
    
3. If you're folder names are different, update the same in **apache/django.wsgi** in the columbus distribution
4. Open the apache conf file and remove the changes you made to test wsgi installation
5. Add the following after the last `</Directory>` tag
    ```apache
    WSGIDaemonProcess columbus-daemon user=johnsoncharles26 group=johnsoncharles26 threads=25 python-path=/home/edf/venv/lib/python2.7/site-packages
    WSGIProcessGroup columbus-daemon
    
    Alias /static/ /home/edf/venv/columbus/static/ 
    
    <Directory /home/edf/venv/columbus/static>
        AllowOverride none
        Order deny,allow
        Allow from all
        Require all granted
    </Directory>
    
    WSGIScriptAlias / "/home/edf/venv/columbus/apache/django.wsgi"
    
    <Directory /home/edf/venv/columbus>
        AllowOverride none
        Order deny,allow
        Allow from all
        Require all granted
    </Directory>
    
    <Directory /home/edf/venv/columbus/apache>
        AllowOverride none
        Order deny,allow
        Allow from all
        Require all granted
    </Directory>
    ```
    
6. Save the file and restart the server. Navigate to the `compute-engine-instance-ip` in the browser and you should see the login page of the columbus.
7. If you wish to set up as a virtual host, you can add the following with appropriate changes.
	```apache
	<VirtualHost *:80>
	
		ServerName www.columbus.cs.colostate.edu
		ServerAlias columbus.cs.colostate.edu
		ServerAdmin jcharles@cs.colostate.edu
	
		DocumentRoot /home/edf/venv/columbus
	
		<Directory /home/edf/venv/columbus>
			AllowOverride none
			Order deny,allow
			Allow from all
			Require all granted
		</Directory>
	
		Alias /static/ /home/edf/venv/columbus/static/
	
		<Directory /home/edf/venv/columbus/static>
			AllowOverride none
			Order deny,allow
			Allow from all
			Require all granted
		</Directory>
	
		WSGIDaemonProcess columbus-daemon user=johnsoncharles26 group=johnsoncharles26 processes=3 threads=25 python-path=/home/edf/venv/lib/python2.7/site-packages
		WSGIProcessGroup columbus-daemon
	
		WSGIScriptAlias / "/home/edf/venv/columbus/apache/django.wsgi"	
		
		<Directory /home/edf/venv/columbus/apache>
			AllowOverride none
			Order deny,allow
			Allow from all
			Require all granted
		</Directory>
	
	</VirtualHost>
	```

### Troubleshooting
If there is any error on visiting the `compute-engine-instance-ip` in the browser, turn on the `DEBUG` constant as `DEBUG=True` in prod-settings and see what issue you're facing. If it's a mysql issue, check if you whitelisted `compute-engine-instance-ip` in the cloud sql instance.

### Version
1.0.0
