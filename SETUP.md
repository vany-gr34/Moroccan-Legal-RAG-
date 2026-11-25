# STEP 01 : Create VENV and installtion deps

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt


# STEP 02 : Classify Pdf files

python src/ingestion/classifiers/pdf_classifier.py