mkdir arkscraper
ssh-keygen
cat .ssh/id_rsa.pub
# copy shh-pubkey manually to git...
git clone git@github.com:Mahosaurus/arkscraper.git
cd arkscraper
sudo apt-get update
sudo apt install -yy python3-pip
pip3 install -r requirements.txt
EXPORT WEBHOOK=""
cd app
python3 app.py