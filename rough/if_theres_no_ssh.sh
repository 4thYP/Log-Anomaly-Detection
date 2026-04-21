cd ~/Log-Anomaly-Detection

git config --global --unset-all url."https://github.com/".insteadof 2>/dev/null || true
git config --local  --unset-all url."https://github.com/".insteadof 2>/dev/null || true

git remote remove origin
git remote add origin git@github.com:4thYP/Log-Anomaly-Detection.git

git remote set-url --push origin git@github.com:4thYP/Log-Anomaly-Detection.git

git remote -v
