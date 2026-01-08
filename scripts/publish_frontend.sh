mkdir -p docs/results/

# Export the notebook
uvx marimo export html-wasm --mode run --no-show-code \
  frontend/magical_athlete_analysis.py \
  -o docs

# Copy supporting files
cp frontend/magical_athlete_analysis.css docs/
cp -r results/*.parquet docs/results/
