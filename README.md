# vMon - vManage Monitor
Simple Python/Flask application to visualize Cisco SD-WAN information from multiple vManage servers
* multiple vmanage servers per user profile (quickly switch between vManage contexts like DEV/QA/PROD...)
* dashboard view with multi-fabric summary (single pane of glass)
* improved device/policy/template views (more insights with less clicks)
* improved handling of alarms (at least for me ;)
* dark theme (make your eyes a favor) 


Notes:
* Python version >= 3.10 (using new match statement here and there)
* Tested with vMnanage 20.6
* See /api for CRUD mappings between vMon API and vManage API (imported from vManage's OpenAPI definition)
* the application uses its own vManage object classes without any external dependency (see vmanage.py)
* Uses RQ for background tasks using Redis as broker
* Uses httpx with async/await for most API calls
* vManage tokens (JSESSIONID and CSRF) are cached in DB for re-use. Refresh is done automatically as needed.


Although the app is fully functional, a lot can be done to improve code quality and to add more functionalities.

## Screenshots

Settings
* Add new vmanage connections
![alt text](screenshots/settings.PNG)

Home screen
* Multi-fabric status
![alt text](screenshots/multi-fabric-view.PNG)

* Alarms
![alt text](screenshots/alarms.PNG)

* Tasks
![alt text](screenshots/task-details.PNG)

Device View
* Easily browse your devices
![alt text](screenshots/device-list.PNG)

Device Details
* Template values editor
![alt text](screenshots/device-values-editor.PNG)

* Real time data
![alt text](screenshots/device-realtime.PNG)

* Route table browser
![alt text](screenshots/device-route-table.PNG)

* BFD Sessions
![alt text](screenshots/device-bfd-topology.PNG)

Policy View
* Control Policy viewer
![alt text](screenshots/control-policy.PNG)

* Security Policy viewer
![alt text](screenshots/security-policy.PNG)

* Local Policy viewer
![alt text](screenshots/local-policy.PNG)

Template View
* Template stack viewer
![alt text](screenshots/template-view.PNG)

* Template values editor
![alt text](screenshots/template-values-editor.PNG)

List View
* List reference
![alt text](screenshots/list-reference.PNG)






## Quick recipe for Ubuntu 20.4 (also valid for WSL)
* install Ubuntu 20.4
* upgrade Ubuntu
```bash
sudo apt update && sudo apt upgrade -y
```
* install python 3.10
```bash
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.10
sudo apt install python3.10-venv
python3.10 -m pip install --upgrade pip
```
* clone vmon
```bash
GIT_SSL_NO_VERIFY=true git clone https://...
```
* prepare virtual environment
```bash
cd vmon-dev
python3.10 -m venv venv
. ./venv/bin/activate
pip3.10 install wheel
pip3.10 install -r requirements.txt
```
* launch app for development
```bash
cd vmon
export FLASK_APP="vmon"
export FLASK_ENV="development"
flask init-db
rq worker vmonJobs &
flask run
```
* launch app for production using gunicorn
```bash
cd vmon
export FLASK_APP="vmon"
export FLASK_ENV="production"
flask init-db
rq worker vmonJobs &
gunicorn --bind 0.0.0.0:5000 vmon:app --workers 10 --threads 1
```

## to create the env (Linux)
```bash
> python3 -m venv venv
> . ./venv/bin/activate
> pip install -r requirements.txt
```

## to create the env (Windows)
```bash
> python -m venv venv
> .\venv\Scripts\activate
> pip install -r requirements.txt
```

## to setup the dev environment (Linux)
```bash
export FLASK_APP=vmon
export FLASK_ENV=development
```

## to setup the dev environment (Windows CMD)
```bash
> set FLASK_APP=vmon
> set FLASK_ENV=development
```

## to setup the dev environment (Windows PowerShell)
```bash
> $env:FLASK_APP = "vmon"
> $env:FLASK_ENV = "development"
```

## to deploy as Python package
- create distribution file
```bash
> pip install wheel
> python setup.py bdist_wheel
```
> The WHL distribution file is generated in the dist/ subfolder.

- deploy the application (change WHL file name as needed)
> Copy the WHL file to another machine, set up a new virtualenv, then install the file with pip:
```bash
> pip install vmon-1.0.0-py3-none-any.whl
```

## to setup the production environment (Windows PowerShell)
```bash
> $env:FLASK_APP = "vmon"
> $env:FLASK_ENV = "production"
> $env:DATABASE_URL = "postgresql://user:password@hostname:port/database"
```

## to init the DB schema:
```bash
> cd vmon
> flask init-db
```
> when running the app in development mode, you can access
> /admin for a minimalistic interface to manage DB entries

## DB migrations:
Right after modifying the DB model (dev only):
```bash
flask db migrate
```
> make sure to review the new version under vmon/migrations/versions

Then to upgrade an existing DB to the new schema:
```bash
flask db upgrade
```
## to get some API information:
```bash
> cd vmon
> flask show-api --help
Usage: flask show-api [OPTIONS]

  Show API endpoints.

Options:
  -a, --all             Show API endpoints
  -n, --name TEXT       Show API endpoint by name
  -d, --dual            Show API endpoints with 2 or more required parameters
  -p, --parameter TEXT  Show API endpoints with specified parameter
  --help                Show this message and exit.
```

## to start the app using embedded Werkzeug webserver:
```bash
> cd vmon
> flask run
```

## to start the RQ worker:
> This assumes RedIS is reachable on localhost:6379
```bash
> cd vmon
> rq worker vmonJobs
```

## to serve the app using gunicorn and UNIX socket (Linux only):
./venv/bin/gunicorn --chdir vmon 'vmon:create_app()' -w 1 --threads 4 -b unix:vmon.sock -m 007


## to serve the app using gunicorn and TCP socket (Linux only):
./venv/bin/gunicorn --chdir vmon 'vmon:create_app()' -w 1 --threads 4

## to deploy as Docker container
> new deployment only: create a new PG-SQL database or leave as is to use SQLite
* modify variables in Dockerfile
> set DATABASE_URL environement variable if you use PG-SQL
* create and deploy the image
>* SQLite deployment only: run 'flask init-db' from the container
>* new PG-SQL deployment only: run 'flask init-db' from the container

## to deploy as systemd service using gunicorn (Linux)

- systemd unit file:
```bash
> cat /etc/systemd/system/vmon.service
[Unit]
Description=Gunicorn instance for vMon app
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/vmon
Environment="PATH=/var/www/vmon/venv/bin"
ExecStart="/var/www/vmon/gunicorn.sh"

[Install]
WantedBy=multi-user.target
```

## to host behind nginx

- create self signed certificate + DH params:
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/ssl/private/vmon.key -out /etc/ssl/certs/vmon.crt
openssl dhparam -out /etc/nginx/dhparam.pem 4096
```
> Note: Generating 4096 bytes long DH param will take some time but is more secure

- nginx config:
```bash
cat /etc/nginx/sites-available/vmon
server {
        listen 443 ssl;
        ssl_certificate /etc/ssl/certs/vmon.crt;
        ssl_certificate_key /etc/ssl/private/vmon.key;
        include snippets/ssl-params.conf;

        server_name vmon vmon.domain.com;

        location / {
                include proxy_params;
                proxy_pass http://unix:/var/www/vmon/vmon.sock;
        }
}

server {
        listen 80;

        return 302 https://$server_name$request_uri;
}
```
> change server_name & proxy_pass to fit your needs

- nginx ssl params:
```bash
cat /etc/nginx/snippets/ssl-params.conf
ssl_protocols TLSv1.2;
ssl_prefer_server_ciphers on;
ssl_dhparam /etc/nginx/dhparam.pem; # 
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
ssl_ecdh_curve secp384r1; # Requires nginx >= 1.1.0
ssl_session_timeout  10m;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off; # Requires nginx >= 1.5.9
ssl_stapling on; # Requires nginx >= 1.3.7
ssl_stapling_verify on; # Requires nginx => 1.3.7
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
```