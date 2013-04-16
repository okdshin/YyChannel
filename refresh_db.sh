rm yy_channel.db
. env/bin/activate
env/bin/python init_db.py
sudo rm -R uploaded_files
mkdir uploaded_files
sudo chmod 777 uploaded_files
sudo chmod 777 yy_channel.db

