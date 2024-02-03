import sys
import logging
logging.basicConfig(stream=sys.stderr)

sys.path.insert(0, '/var/www/html/flaskapp')
activate_this = '/var/www/html/flaskapp/venv/bin/activate_this.py'
exec(open(activate_this).read(), {'__file__': activate_this})


from app import app as application

