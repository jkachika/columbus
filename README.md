<p align="center">
<img src="https://github.com/jkachika/columbus/blob/master/static/images/logo512.png" width="256">
</p>

# Columbus: A Cloud based Distributed Scientific Workflow Engine for Large Multi-Dimensional Spatiotemporal Datasets

Columbus is a workflow engine written in python 2.7. It supports execution of workflows that can be represented as a [Directed Acyclic Graph(DAG)](https://en.wikipedia.org/wiki/Directed_acyclic_graph). The fundamental elements of the engine include components, workflows, and combiners. A workflow is represented as a directed acyclic graph with nodes being components or combiners and edges represent the data flow. Key features of the system include:

* Creation/deletion of components, combiners, and workflows
* Sharing workflows with other users in the system
* Data source support for Google Bigquery, Google Drive, Galileo Spacetime 
* Creation of constraints for supported data sources
* Web-mapping visualizations for supported output types
* Charting visualizations for supported output types
* Dashboard showing Workflows and Users summary
* Sharing web-mapping visualizations
* Support for drawing geometries and saving them
* Support for importing Polygons from Google Fusion Tables
* Integrated data selection mechanism per workflow
* Downloading results for supported output types
* Administration panel to control distributed workers

For detailed application usage, click [here](https://github.com/jkachika/columbus/blob/master/USAGE.md). To understand the output types and script usage, click [here](https://github.com/jkachika/columbus-worker/blob/master/README.md). To see the full list of API calls that can be made in the scripts, click [here](https://jkachika.github.io/colorker/index.html). To understand the architecture, design details, and execution of workflows, refer the [publication](https://github.com/jkachika/columbus/blob/master/docs/columbus-ieee-scc-2017.pdf)*.

\* *Publication material is presented to ensure timely dissemination of scholarly and technical work. Copyright and all rights therein are retained by authors or by other copyright holders. All persons copying this information are expected to adhere to the terms and constraints invoked by each author's copyright. In most cases, these works may not be reposted without the explicit permission of the copyright holder*.

## Requirements
* Linux based OS (preferably Debian Jessie)
* Python 2.7
* Database (preferably MySQL)
* Google cloud storage (read-write access service account required)
* Storage systems (atleast one)
    * Google Bigquery (read access service account required)
    * Google Drive
    * [Galileo Spacetime](https://github.com/jkachika/galileo-spacetime)
* GIS Computations(atleast one)
    * Google Earth Engine (full-access service account required)
    * Any software stack installed on machines acting as workers
* Columbus Worker (included in the requires sub directory)
* Apache HTTP server

## Installation and Deployment
The section describes the installation of the application on Google cloud compute engine instance running Debian 8 and deployment to Apache HTTP Server using mod-wsgi. The steps assume that python 2.7 is installed on the machine and that database is MySQL.

1. Update apt-get
    ```sh
    $ sudo apt-get update
    ```
    
2. Install pip
    ```sh
    $ curl -O https://bootstrap.pypa.io/get-pip.py
    $ sudo python get-pip.py
    ```
    
3. Install virtualenv
    ```sh
    $ sudo pip install virtualenv
    ```
    
4. Install build-essentials
    ```sh
    $ sudo apt-get install build-essential
    ```
    
5. Install mysql-dev
    ```sh
    $ sudo apt-get install libmysqlclient-dev
    ```
    
6. Install python-dev
    ```sh
    $ sudo apt-get install python-dev
    ```
    
7. Install libssl-dev and libffi-dev
    ```sh
    $ sudo apt-get install libssl-dev libffi-dev
    ```
    
8. Install libxml and libxslt
    ```sh
    $ sudo apt-get install libxml2-dev libxslt-dev
    ```

9. create a directory for virtual env and change the owner to the user
    ```sh
    $ sudo mkdir /home/prod
    $ sudo chown $USER /home/prod
    ```

10. Create a virtual environment(you should be able to create without sudo otherwise navigate to `/home/prod` and try again)
    ```sh
    $ virtualenv --no-site-packages -p /usr/bin/python2.7 /home/prod/venv
    ```

11. Copy the columbus source code to `/home/prod/venv`. Your directory structure should be as follows:
    ```
    /home/prod/venv/columbus
    ├─── apache
    ├─── columbus
    ├─── pyedf
    ├─── requires
    ├─── secured
    ├─── static
    ├─── templates
    ├─── manage.py
    ├─── requirements.txt
    ```

12. Navigate to the virtual env and activate it. The prompt should change to (venv).
    ```sh
    $ cd /home/prod/venv
    $ source bin/activate
    (venv) /home/prod/venv$ pip install columbus/requires/columbusworker-0.1.0.tar.gz  
    ```

13. Install all the requirements using the following command in (venv) prompt
    ```sh
    (venv) $ cd /home/prod/venv/columbus
    (venv) $ pip install -r requirements.txt
    ```
    
14. Deactivate virtualenv using the following command in venv prompt
    ```sh
    (venv) $ deactivate
    ```
    
15. Install and start apache outside virtual env
    ```sh
    $ sudo apt-get install apache2
    $ sudo apache2ctl start
    ```
    
16. Install mod-wsgi
    ```sh
    $ sudo apt-get install libapache2-mod-wsgi
    ```
    
17. Test mod-wsgi installation
    1. Make a directory "test" in /home/prod/venv
        ```sh
        $ cd /home/prod/venv
        $ mkdir test
        ```
        
    2. Create a file named "testapp.wsgi" in /home/prod/venv/test and paste the following contents in it
        ```python
        def application(environ, start_response):
            status = '200 OK'
            output = 'Hello World!'
            response_headers = [('Content-type', 'text/plain'),('Content-Length', str(len(output)))]
            start_response(status, response_headers)
            return [output]
        ```
        
    3. Make note of the user and group of the directory /home/prod/venv
        ```sh
        $ ls -l /home/prod
        Output:
        drwxr-xr-x 8 johnsoncharles26 johnsoncharles26 4096 Jun 15 22:38 venv
        First occurence of johnsoncharles26 is the user and the second occurence is the group
        ```
        
    4. Open the apache2 conf file:
        ```sh
        $ cd /etc/apache2
        $ sudo vi apache2.conf
        ```
        
    5. Paste the following contents after the last `</Directory>` tag. You can look up the WSGIDaemonProcess documentation [here](http://modwsgi.readthedocs.io/en/develop/configuration-directives/WSGIDaemonProcess.html). Replace $USER with actual username.
    
        ```apache
        WSGIDaemonProcess columbus-daemon user=$USER group=$USER threads=25 python-path=/home/prod/venv/lib/python2.7/site-packages
        WSGIProcessGroup columbus-daemon
        WSGIScriptAlias /testapp "/home/pord/venv/test/testapp.wsgi"
    
        <Directory /home/prod/venv/test>
            AllowOverride none
            Order deny,allow
            Allow from all
            Require all granted
        </Directory>
        ```
    
    6. Restart the server. 
        ```sh
        $ sudo apache2ctl restart
        ```
        
    7. Navigate to `compute-engine-instance-ip/testapp` in a browser. You should see Hello World!
    
18. If using Galileo Spacetime, deploy the Galileo Webservice by following the instructions [here](https://github.com/jkachika/galileo-web-service). If you wish to deploy the service on the same host as the Columbus and would like to access it from the same domain, then:
    1. Enable mod_proxy
        ```sh
        $ sudo a2enmod proxy
        $ sudo apache2ctl restart
        $ sudo a2enmod proxy_http
        $ sudo apache2ctl restart        
        ```
 
    2. Make the following changes to your `apache2.conf` file.
        ```sh
        $ cd /etc/apache2
        $ sudo vi apache2.conf
        ```
        
        Assuming `columbus.xyz` as the domain at which Columbus would be deployed, `tomcat.columbus.xyz` as the domain at which the Galileo webservice would be accessed, and Galileo webservice is deployed on Tomcat on the port `8080`.
  
        ```apache
        <VirtualHost *:80>
            ServerName tomcat.columbus.xyz
            ProxyPass / http://www.columbus.xyz:8080/
            ProxyPassReverse / http://www.columbus.xyz:8080/
        </VirtualHost>
        ```

19. If mod_wsgi installation was successful please follow the steps listed in [application setup](#appsetup) and update the `columbus/prod_settings.py` and `apache/django.wsgi` files appropriately.

20. Finally, make the following changes to the `apache2.conf` file to deploy the Columbus application. Replace `$USER` with the actual username.
    
    ```apache
    <VirtualHost *:80>
 
        ServerName www.columbus.xyz
        ServerAlias columbus.xyz
        ServerAdmin username@columbus.xyz # User appropriate email address
    
        DocumentRoot /home/prod/venv/columbus
    
        <Directory /home/prod/venv/columbus>
            AllowOverride none
            Order deny,allow
            Allow from all
            Require all granted
        </Directory>
    
        Alias /static/ /home/prod/venv/columbus/static/
    
        <Directory /home/prod/venv/columbus/static>
            AllowOverride none
            Order deny,allow
            Allow from all
            Require all granted
        </Directory>
    
        WSGIDaemonProcess columbus-daemon user=$USER group=$USER processes=1 threads=1000 python-path=/home/prod/venv/lib/python2.7/site-packages
        WSGIProcessGroup columbus-daemon
    
        WSGIScriptAlias / "/home/prod/venv/columbus/apache/django.wsgi"
    
        <Directory /home/prod/venv/columbus/apache>
            AllowOverride none
            Order deny,allow
            Allow from all
            Require all granted
        </Directory>
        
    </VirtualHost>
    ```
    
21. Navigate to `www.columbus.xyz` and you should be able to access the Columbus application.


## <a name="appsetup"></a>Application Setup
This section lists the steps needed to setup the application. Instructions are also included as comments in the `prod_settings.py` file.

1. Open the `apache/django.wsgi` file in the distribution and make sure that the paths listed for the following are correct else update them appropriately.

    ```python
    site.addsitedir('/home/prod/venv/lib/python2.7/site-packages')
    
    sys.path.append('/home/prod/venv/columbus')
    sys.path.append('/home/prod/venv/columbus/columbus')
    
    activate_this = '/home/prod/venv/bin/activate_this.py'
    ```

2. Open the `columbus/prod_settings.py` file and make the following changes.
    
    1. If using Galileo Spacetime, update the following variable to point to the Galileo Webservice.
        ```python
        WEBSERVICE_HOST = 'http://tomcat.columbus.xyz/galileo-web-service'
        ```
        
    2. Update the supervisor port number if the default is already in use. This is the port on which Columbus master listens for workers to connect and communicate with them.
        ```python
        SUPERVISOR_PORT = 56789
        ```
        
    3. Update the container size per your requirements. The value is treated as in MB. This is the maximum memory allowed for any process to execute a Target of any workflow. Set this to an optimal value depending on your needs. When a target requires more memory than that is set here, the worker retries the Target by doubling the container size every time.
        ```python
        CONTAINER_SIZE_MB = 1024  # 1024 MB containers for any target
        ```
        
    4. Update the user directory path (without a trailing slash) where the serialization files or pickles are stored on both master and workers. This path must exist on both master and worker machines with read and write permissions to the user running the application.   
        ```python
        USER_DIRPATH = '/home/prod/storage'
        ```
        
    5. Update the Google cloud storage bucket name (without `gs://`) for fault tolerance and data transfers between master and workers. This is required for Columbus to execute workflows.
        ```python
        USER_GCSPATH = 'gcs-bucket-name'
        ```
        
    6. Update the temporary directory path (without trailing slash). This is the place where files are stored for temporary purposes such as while uploading data to the cloud or during the creation of fusion tables. Files will not be cleared by the application from this path, so create a system task to clear the files in this path periodically.
        ```python
        TEMP_DIRPATH = '/tmp'
        ```
        
    7. Place all the service account files in the directory named `secured` in the distribution. Service accounts are mandatory for Google cloud storage, Google fusion tables, and Google drive. Additionally, you would need to obtain a client secret file to allow the application to access end users Google drive. If you use Google Bigquery or Google Earth Engine, you would need service accounts to those.
    
        ```python
        # Place all the service account files in this directory
        SECURED_DIR = os.path.join(BASE_DIR, 'secured')
        
        # Do not change. Used for internal purposes.
        REQUIRES_DIR = os.path.join(BASE_DIR, 'requires')
        
        # service account credentials from Google dev console for Google Earth Engine. Required if GIS computations are
        # performed in the Targets.
        EE_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
        # service account credentials from Google dev console for Google Bigquery. Required if Bigquery serves as one of
        # the data source options.
        BQ_CREDENTIALS = os.path.join(SECURED_DIR, 'earth-outreach-bigquery.json')
        # service account credentials from Google dev console for Google Cloud Storage. Required for fault tolerance and data
        # transfers. The service account listed here must have full permissions to the bucket listed for the property
        # USER_GCSPATH above
        CS_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
        # service account credentials from Google dev console for Google Fusion Tables and Google Drive. Required to enable
        # web-mapping visualizations.
        FT_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-earth-engine.json')
        # client secret to gain access to end users google drive. Required to obtain permission to client's Google Drive if
        # the same is serving as one of the data source options.
        GD_CREDENTIALS = os.path.join(SECURED_DIR, 'columbus-client-secret.json')
        ```

    8. Update the list of worker host names. Hostnames should be fully qualified and master must be able to login to all those workers using passwordless SSH. 
        ```python
        # WORKERS CONFIGURATION
        WORKERS = [socket.getfqdn()]
        # default is ~/columbus. If specified path must be fully qualified
        WORKER_VIRTUAL_ENV = None
        # port number to SSH into the worker machines
        WORKER_SSH_PORT = 22
        # username to SSH into the worker machines
        WORKER_SSH_USER = 'johnsoncharles26'
        # password if any to SSH into the worker machines. If passwordless SSH is enabled and the private key has a passphrase
        # this must be that passphrase.
        WORKER_SSH_PASSWORD = None
        # fully qualified path for the priavte key file. if not specified ~/.ssh/id_rsa is tried
        WORKER_SSH_PRIVATE_KEY = None
        ```
        
    9. Update the scheduling strategy for the execution of workflows. It must be one of `local`, `remote`, `hybrid`. If you are unsure, use the defaults.
        ```python
        # Scheduler Configuration
        # learn about the scheduling strategies from the Columbus paper. If not sure, leave the defaults
        PIPELINE_SCHEDULING_STRATEGY = "hybrid"
        # waiting-running target ratio used only for hybrid scheduling strategy.
        # Default is 1, meaning targets are sent to the same worker as long as the number
        # of targets waiting is less than or equal to the number of running targets of any user
        HYBRID_SCHEDULING_WR_RATIO = 1
        ```
        
    10. Update the temporary or staging cloud storage bucket to use while communicating with Google Earth Engine. Required only if GEE will be used.
        ```python
        # Cloud Storage Bucket to use for temporary file storing while communicating with Google Earth Engine.
        # The service account key specified for EE_CREDENTIALS must have full access to this bucket.
        CS_TEMP_BUCKET = 'staging.columbus-csu.appspot.com'
        ```
        
    11. Update the `SECRET_KEY` for security purposes and remember to turn the `DEBUG` parameter to `False` after deploying the application successfully.
        ```python
        # SECURITY WARNING: keep the secret key used in production secret!
        # Change the key to something else after deployment
        SECRET_KEY = '3bg_5!omle5)+60!(qndj2!#yi+d%2oug2ydo(*^nup+9if0$k'
        # Remove the following debug params after successful deployment
        DEBUG = True
        ```
        
        
    12. Update the database information. If using Google cloud SQL, do not forget to whitelist the IP of the host that will access this database. 
        ```python
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql',  # assuming the database is MySQL
                'NAME': 'database-name',  # name of the database to use
                'USER': 'user-name',  # user name to use while connecting to the database
                'PASSWORD': 'password',  # password to use while connecting the database
                'HOST': 'mysql-ip-address',  # public IP of the database server
                'PORT': '3306'  # port number of the database server
            }
        }
        ```
        
    13. Update the list of domain names that point to this server
        ```python
        # list of domain names to which django server should serve. Must be specified when DEBUG = False
        ALLOWED_HOSTS = ['www.columbus.xyz', 'columbus.xyz']
        ```
        
    14. Update the time zone to the time zone of the server if `UTC` is not preferred.
        ```python
        # Internationalization
        # https://docs.djangoproject.com/en/1.8/topics/i18n/
        LANGUAGE_CODE = 'en-us'
        TIME_ZONE = 'UTC'
        USE_I18N = True
        USE_L10N = True
        USE_TZ = True
        ```
        
    15. Update email settings. The defaults assume that the SendGrid service is used.
        
        ```python
        # Change the admin name and email address
        ADMINS = [
            ('Johnson Kachikaran', 'jcharles@cs.colostate.edu'),
        ]
        
        # Refer to configuring sendgrid using Postfix on Google Compute Engine here
        # https://cloud.google.com/compute/docs/tutorials/sending-mail/using-sendgrid
        EMAIL_HOST = 'smtp.sendgrid.net'
        EMAIL_HOST_USER = 'sendgrid-username'
        EMAIL_HOST_PASSWORD = 'sendgrid-password'
        EMAIL_PORT = 2525
        EMAIL_USE_TLS = True
        
        # Use appropriate prefix to add to the subject line of all the emails sent from the application
        EMAIL_SUBJECT_PREFIX = '[Columbus] '
        # Email address of the sender to use while sending emails from the application.
        # Typically, noreply@columbus.xyz
        EMAIL_SENDER = 'Sender Name <senders email address including angular brackets>'
        
        # Change the manager name and email address
        MANAGERS = (
            ('Johnson Kachikaran', 'jcharles@cs.colostate.edu'),
        )
        
        SEND_BROKEN_LINK_EMAILS = True
        ```
        
    16. Update the logger settings to meet your needs. Default file sizes are 10MB and a maximum of 10 files are stored as backup
        ```python
        # Logger settings
        LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
                    'datefmt': "%d/%b/%Y %H:%M:%S"
                },
                'simple': {
                    'format': '%(levelname)s %(message)s'
                },
            },
            'handlers': {
                'pyedf_handler': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': os.path.join(BASE_DIR, 'pyedf.log'),
                    'maxBytes': 1024 * 1024 * 10,  # 10MB default
                    'backupCount': 10,
                    'formatter': 'verbose'
                },
                'django_handler': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': os.path.join(BASE_DIR, 'django.log'),
                    'maxBytes': 1024 * 1024 * 10,  # 10MB default
                    'backupCount': 10,
                    'formatter': 'verbose'
                }
            },
            'loggers': {
                'django': {
                    'handlers': ['django_handler'],
                    'propagate': True,
                    'level': 'ERROR',
                },
                'pyedf': {
                    'handlers': ['pyedf_handler'],
                    'level': 'INFO',
                },
            }
        }
        ```

3. Setup database and load the data.
    ```sh
    $ cd /home/prod/venv
    $ source bin/activate
    (venv) /home/prod/venv$ cd columbus
    (venv) /home/prod/venv/columbus$ python manage.py makemigrations
    (venv) /home/prod/venv/columbus$ python manage.py migrate
    (venv) /home/prod/venv/columbus$ python manage.py loaddata typemodel.json
    ```

4. Create a superuser to have administrator access to the Django admin portal. You can access the admin portal after successful deployment at `www.columbus.xyz/admin` assuming `columbus.xyz` is the domain name.
    ```sh
    (venv) /home/prod/venv/columbus$ python manage.py createsuperuser
    # Deactivate the virtual environment after creating the superuser
    (venv) /home/prod/venv/columbus$ deactivate
    ```


## LICENSE
Copyright (c) 2017 Johnson Kachikaran, Colorado State University

Licensed under MIT License (the "License"). The License is included in the software distribution and you may also view the same [here](https://github.com/jkachika/columbus/blob/master/LICENSE.txt).

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

