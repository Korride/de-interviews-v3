# ML image (Question 3): extends the ETL image with CatBoost + scikit-learn.
FROM deals_etl:latest

COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt

COPY . .
