# First time
mkdir arkscraper
ssh-keygen
cat .ssh/id_rsa.pub
# copy shh-pubkey manually to git...
git clone git@github.com:Mahosaurus/arkscraper.git
cd arkscraper
sudo apt-get update
sudo apt install -yy python3-pip
pip3 install -r requirements.txt
export WEBHOOK=""
cd app
python3 app.py

# After that
sudo pkill -f python
cd arkscraper
git pull
cd app
python3 app.py
